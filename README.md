# importkml
Import KML files provided by the export of the SAE INEO in Python in PostGIS database (only multilines). 
Use the name of the file to find the transportation lines and the date of the schedule. The name of the file must be : 
Orleans_1_PT4_20190920

_1_ for the name of the line
_20190920 for the date of the calendar

Convert the xml file in kml file with correct encoding.

# Installation 

Install GDAL modules (preferred with Linux machine or docker > osgeo/gdal:alpine-normal-latest )
Install PostGIS database (preferred with Linux machine or docker  mdillon/postgis)
Install dependencies :

`pip/pip3 install -r requirements.txt`

# Usage  

Launch the command : 

`python test-read-kml.py --pg="PG:dbname='import_kml' host='db' port='5432' user='***' password='***'" --dir="location of the directory with xml files" --create`


| Option        | Description           | 
| ------------- |:-------------:| 
|--dir| Directory of the files with XML provideb by INEO SAE|
|--pg| Datasource  |
|--create|create the table in postGis (or destroy the current table **be careful**)|


# Example of the use with a docker machine : 

`docker run -it -v /Users/pierrelagarde/Documents/Personnel/code/importKML/src:/app --net importkml_default --link importkml_postgres_1:db  osgeo/gdal:alpine-normal-latest sh`

`cd app`

`python test-read-kml.py --pg="PG:dbname='import_kml' host='db' port='5432' user='***' password='***'" --dir="location of the directory with xml files" --create`