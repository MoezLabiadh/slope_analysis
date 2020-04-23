# -*- coding: utf-8 -*-
"""
This script takes a raster (slope) as input and perform the following manipulations:
    - Clip the raster using a polygon shapefile.
    - Reclassify the slope raster to predefined ranges.
    - Calculate of aera (ha) of each slope Class, OR
    
    - Vectorize the final raster output.
    - Calculate Areas for each slope class.
"""
import os
import rasterio
import rasterio.mask
import numpy as np
import geopandas as gpd
from osgeo import gdal, ogr, osr

# Create script variables
Workspace = 'C:/..../data'
slope_raster = os.path.join (Workspace, 'Slope' , 'sheep_creek_slopePercent.tif') 
AOI =  os.path.join (Workspace, 'AOI' , 'AOI.shp') 

#Clip the slope raster to the AOI extent
 ##Make a new folder for the clipped raster
Masked_dir = os.path.join (Workspace, 'Masked')
if not os.path.exists(Masked_dir):
    os.makedirs (Masked_dir)
else:
    pass

 ##Clip the raster and save in the new folder     
print('Clipping in progress...')

AOI_gpd = gpd.read_file (AOI) #Read the shp as geopandas geodataframe
with rasterio.open(slope_raster) as src:
    out_image, out_transform = rasterio.mask.mask(src, AOI_gpd.geometry,crop=True)
    out_meta = src.meta.copy()
    out_meta.update({"driver": "GTiff",
                 "height": out_image.shape[1],
                 "width": out_image.shape[2],
                 "transform": out_transform})

out_ras = os.path.join (Masked_dir , os.path.basename (AOI)[:-4]+'_slope.tif')      
with rasterio.open(out_ras, "w", **out_meta) as dest:
    dest.write(out_image)

print ("Raster clipped") 

# Reclassify the clipped slope raster 
 ##Make a new folder for the reclassified raster
Reclass_dir = os.path.join (Workspace, 'Reclass')
if not os.path.exists(Reclass_dir):
    os.makedirs (Reclass_dir)
else:
    pass

 ## retrieve the masked raster
for file in os.listdir(Masked_dir):
    if file.endswith("_slope.tif"):
        masked_raster = os.path.join(Masked_dir, file)

print ("Reclassification in progress....") 
with rasterio.open(masked_raster) as src:    
    ## Read raster as numpy array
    array_in = src.read()
    profile = src.profile
    ## Reclassify
    array_out= array_in.copy()
    array_out[np.where((0 <= array_in) & (array_in <= 20))] = 1 #slopes < 20%
    array_out[np.where((20 < array_in) & (array_in <= 45)) ] = 2 #slopes from 20 to 45%
    array_out[np.where((45 < array_in) & (array_in <= 70)) ] = 3 #slopes from 45 to 70%
    array_out[np.where((70 < array_in) & (array_in <= 80)) ] = 4 #slopes from 70 to 80%
    array_out[np.where(array_in > 80)] = 5 #slopes >  80%
    
reclass_raster = os.path.join (Workspace, Reclass_dir, os.path.basename (masked_raster)[:-4]+'_reclass.tif') # output image  
with rasterio.open(reclass_raster, 'w', **profile) as dst:
    dst.write(array_out)
    crs = src.crs
print ("Raster reclassified")

# Calculate the area of each Slope Class
for file in os.listdir(Reclass_dir):
    if file.endswith("_reclass.tif"):
        reclass_raster = os.path.join(Reclass_dir, file)

raster =  rasterio.open (reclass_raster)
array_raster = raster.read()

 ## Retrieve the pixel size and caluclate the Pixel Area
pixelSizeX, pixelSizeY  = raster.res
pixelArea = pixelSizeX * pixelSizeY 

 ## Calculate the area in hectares for each Class 
Area_class_1 = (np.count_nonzero(array_raster == 1) * pixelArea) / 10000
Area_class_2 = (np.count_nonzero(array_raster == 2) * pixelArea) / 10000
Area_class_3 = (np.count_nonzero(array_raster == 3) * pixelArea) / 10000
Area_class_4 = (np.count_nonzero(array_raster == 4) * pixelArea) / 10000
Area_class_5 = (np.count_nonzero(array_raster == 5) * pixelArea) / 10000

print (Area_class_1)
print (Area_class_2)
print (Area_class_3)
print (Area_class_4)
print (Area_class_5)

'''
# Vectorize the raster
Vector_dir = os.path.join (Workspace, 'Vector')
if not os.path.exists(Vector_dir):
    os.makedirs (Vector_dir)
else:
    pass

print ("Vectorizing raster...in progress") 
dst_layername = os.path.join (Workspace, 'Vector', os.path.basename (reclass_raster)[:-4]+'_vector')
src_ds = gdal.Open(reclass_raster)
srcband = src_ds.GetRasterBand(1)
drv = ogr.GetDriverByName("ESRI Shapefile")
dst_ds = drv.CreateDataSource( dst_layername + ".shp")

spat_ref = osr.SpatialReference() #extract spatial ref from input raster
proj = src_ds.GetProjectionRef() #extract spatial ref from input raster
spat_ref.ImportFromWkt(proj) #extract spatial ref from input raster

dst_layer = dst_ds.CreateLayer(dst_layername, spat_ref, ogr.wkbPolygon) #assign spatial ref to output vector
newField = ogr.FieldDefn('gridcode', ogr.OFTInteger)
dst_layer.CreateField(newField)
gdal.Polygonize(srcband, None, dst_layer, 0, [], callback=None)
del src_ds, srcband, drv, dst_ds, dst_layer

print ("Raster vectorized")

# Add Area (ha) field, dissolve and aggregate areas
slope_class_vector = gpd.read_file(dst_layername + ".shp")
print ("Calculating area_ha field...in progress") 
slope_class_vector["area_ha"] = slope_class_vector['geometry'].area/ 10000
slope_class_vector = slope_class_vector[['gridcode', 'geometry' , 'area_ha']]
print ("Dissolving and agregating areas...in progress") 
slope_class_vector_dissolve = slope_class_vector.dissolve(by='gridcode' , aggfunc = 'sum')
slope_class_vector_dissolve.to_file(os.path.join (Workspace, 'Vector', os.path.basename (dst_layername)+'_dissolve.shp'))
#os.remove(dst_layername + ".shp")
'''

print ("Process Completed")
