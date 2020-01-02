from osgeo import ogr,osr
import sys, os
import datetime
from tabulate import tabulate
import codecs
import glob
import chardet
import logging
import getopt

from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
ogr.UseExceptions()

def extractLineDate(filename):
    logging.info("Name of the file %s" % filename )
    splitFileName = filename.split("_")
    line = splitFileName[1]
    dateText = splitFileName[3].split(".")[0]
    date = datetime.datetime.strptime(dateText,'%Y%m%d')
    return line,date

def extractDataFromFile(daKmlfile):
    
    lineOfFile, dateOfFile = extractLineDate(os.path.basename(daKmlfile))
    driver = ogr.GetDriverByName('KML')
    try:
        dataSource = driver.Open(daKmlfile)
    except Exception as e:
        logging.error(e)

    if dataSource is None:
        logging.error('Could not open %s' % (daKmlfile))
    else:
        logging.info('Opened %s' % (daKmlfile))

        data_records=[]
        for kml_lyr in dataSource:
            layerName = kml_lyr.GetName()
            lyr_def = kml_lyr.GetGeomType()
        
            if lyr_def == ogr.wkbLineString or lyr_def == ogr.wkbMultiLineString:
                layerTypeGeom = ogr.GeometryTypeToName(kml_lyr.GetGeomType())
                featureCount = kml_lyr.GetFeatureCount()
                logging.info("Number of features in %s: %d" % (layerName,featureCount))
                for feat in kml_lyr:
                    data_values = {}
                    record = feat.items()
                    data_values['geom'] = feat.GetGeometryRef().ExportToWkt()
                    data_values['name'] = record['Name']
                    data_values['description'] = record['Description']
                    data_values['layer'] = layerName
                    data_values['line'] = lineOfFile
                    data_values['date'] = dateOfFile 
                    data_records.append(data_values)
        return data_records


def createTableImport(pg_ds):
    table_name = 'lines_sae'
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    pg_layer = pg_ds.CreateLayer(table_name, srs = srs, geom_type=ogr.wkbLineString, options = [
                'GEOMETRY_NAME=the_geom',
                'OVERWRITE=YES', 
                'SCHEMA=public',
                ])

    fd_def = ogr.FieldDefn('name', ogr.OFTString)
    pg_layer.CreateField(fd_def)
    fd_def = ogr.FieldDefn('description', ogr.OFTString)
    pg_layer.CreateField(fd_def)
    fd_def = ogr.FieldDefn('layer', ogr.OFTString)
    pg_layer.CreateField(fd_def)
    fd_def = ogr.FieldDefn('line', ogr.OFTString)
    pg_layer.CreateField(fd_def)
    fd_def = ogr.FieldDefn('date', ogr.OFTDate)
    pg_layer.CreateField(fd_def)
    logging.info('Table %s created.' % table_name)

    
    table_name = 'lines_sae_aggr'
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    pg_layer = pg_ds.CreateLayer(table_name, srs = srs, geom_type=ogr.wkbLineString, options = [
                'GEOMETRY_NAME=the_geom',
                'OVERWRITE=YES', 
                'SCHEMA=public',
                ])

    fd_def = ogr.FieldDefn('layer', ogr.OFTString)
    pg_layer.CreateField(fd_def)
    fd_def = ogr.FieldDefn('line', ogr.OFTString)
    pg_layer.CreateField(fd_def)
    fd_def = ogr.FieldDefn('date', ogr.OFTDate)
    pg_layer.CreateField(fd_def)
    
    #add unique key
    # too many issues with the data geometry quality
    #pg_ds.ExecuteSQL("alter table lines_sae_aggr ADD unique (layer,date,line)")

    logging.info('Table %s created.' % table_name)
    
    return True

def addDataInPostGres(data,pg_ds):
    table_name = 'lines_sae'
    pg_layer = pg_ds.GetLayer(table_name)
    featureDefn = pg_layer.GetLayerDefn()
    
    for data_value in data:
        feature = ogr.Feature(featureDefn)
        polyline = ogr.CreateGeometryFromWkt(data_value['geom'])
        feature.SetField('name', data_value['name'])
        feature.SetField('description', data_value['description'])
        feature.SetField('layer', data_value['layer'])
        feature.SetField('line', data_value['line'])
        feature.SetField('date', data_value['date'].strftime("%Y-%m-%d"))
        feature.SetGeometry(polyline)
        pg_layer.CreateFeature(feature)
    
    return True


def convertFileToUtf8AndKml(filename,destDir=False,simulation=False):
    name, ext = os.path.splitext(filename)
    if destDir:
        name = destDir + os.path.basename(name)
    newfilename = name + '.kml'

    if not simulation:
        with open(filename, 'rb') as f:
            content_bytes = f.read()
        detected = chardet.detect(content_bytes)
        encoding = detected['encoding']
        logging.debug(f"{filename}: detected as {encoding}.")
        content_text = content_bytes.decode(encoding)
        with codecs.open(newfilename, 'w+', 'utf-8') as f:
            f.write(content_text)
    
    return newfilename

def main(argv):  
    CREATED_TABLE = False
    try:                                
        opts, args = getopt.getopt(argv, "d:g:c", ["dir=", "pg=","create"]) 
    except getopt.GetoptError:                      
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-d", "--dir"): 
            originalDir = arg +'/*.xml'
            destKmlDir = arg + "_utf8" + "/"
            #create directory if required
            try:
                os.mkdir(destKmlDir)
            except:
                logging.info("directory exists")
        elif opt in ("-g", "--pg"):
            stringPG = arg
        elif opt in ("-c", "--create"):
            CREATED_TABLE = True

    driver = ogr.GetDriverByName('PostgreSQL')
    pg_ds = driver.Open(stringPG) # "PG:dbname='import_kml' host='db' port='5432' user='***' password='***'"
    if pg_ds is None:
        logging.error('Could not open the database')
    if CREATED_TABLE:
        logging.info("Creation of the table in PostGis réalisé ? %r" % createTableImport(pg_ds))
    
    
    allFilesInRep = glob.glob(originalDir)
    
    
    allFilesKml = []
    # convert in UTF8
    logging.info("Conversion UTF8 des fichiers")
    for originalXmlfile in tqdm(allFilesInRep):
        allFilesKml.append(convertFileToUtf8AndKml(originalXmlfile,destDir=destKmlDir,simulation=False))

    #import in PostGis
    logging.info("Import des fichiers en BD")
    for Kmlfile in tqdm(allFilesKml):
        data_records= extractDataFromFile(Kmlfile)  
        logging.info("File %s has been added in PostGres ? %r" % (Kmlfile, addDataInPostGres(data_records,pg_ds)))          

    #create aggr table
    data_update = pg_ds.ExecuteSQL("insert into lines_sae_aggr(layer,line,date,the_geom) select layer,line, date,  (st_dump(st_linemerge(st_union(the_geom)))).geom from lines_sae group by line, date, layer order by line,date")
    logging.info("Actualisation de la table d'aggrégation ? %r" % data_update)

if __name__ == "__main__":
    main(sys.argv[1:])