from __future__ import annotations
from pathlib import Path
import datetime
import geopandas as gpd
import numpy as np
from pynhd import NLDI
import os
from scripts import data, dataprocessing

nldi = NLDI()

def basinFile(basin, basinname, station):
    #make file to store data for basin
    if not os.path.exists('files/Basin'):
        os.makedirs('files/Basin')

    basin.to_file(f"files/Basin/{basinname}.shp")
    print('done')

    #pull through nwis to get site features and stream networks
    site_feature = nldi.getfeature_byid("nwissite", f"USGS-{station}")
    upstream_network = nldi.navigate_byid(
    "nwissite", f"USGS-{station}", "upstreamMain", "flowlines", distance=9999
    )

    return site_feature, upstream_network

def snotelFile(geometry, state):
   #Pull data from csv files
    all_stations_gdf = gpd.read_file('https://raw.githubusercontent.com/egagli/snotel_ccss_stations/main/all_stations.geojson').set_index('code')
    all_stations_gdf = all_stations_gdf[all_stations_gdf['csvData']==True]
    gdf_in_bbox = all_stations_gdf[all_stations_gdf.geometry.within(geometry)]
    
    #organize index to match datetime for other dataframes later
    gdf_in_bbox.reset_index(drop=False, inplace=True)
    gdf_in_bbox['beginDate'] = [datetime.datetime.strftime(gdf_in_bbox['beginDate'][i], "%Y-%m-%d") for i in np.arange(0,len(gdf_in_bbox),1)]
    gdf_in_bbox['endDate'] = [datetime.datetime.strftime(gdf_in_bbox['endDate'][i], "%Y-%m-%d") for i in np.arange(0,len(gdf_in_bbox),1)]

    #Set storage point
    OutputFolder = 'files/SNOTEL'
    if not os.path.exists(OutputFolder):
        os.makedirs(OutputFolder)

    #grab snotel data
    for i in gdf_in_bbox.index:
        data.getSNOTEL(gdf_in_bbox.name[i], gdf_in_bbox.code[i],state, gdf_in_bbox.beginDate[i], gdf_in_bbox.endDate[i], OutputFolder)
    
    return gdf_in_bbox

def dischargeFile(station):
    #Pull USGS for stream gauge site
    streamflow = data.get_usgs_streamflow(station)

    #Cleaning data to meet project requirements 
    cleaned = dataprocessing.clean_nwis_dataframe(streamflow)
    cleaned.index.name = "Date"

    #Convert into cms
    cleaned['flow_cfs'] = cleaned['flow_cfs'] * 0.0283168
    cleaned.rename(columns={'flow_cfs': 'flow_cms'}, inplace=True)

    #storage point
    OutputFolder = 'files/NWIS'
    if not os.path.exists(OutputFolder):
        os.makedirs(OutputFolder)
    cleaned.to_csv(f'{OutputFolder}/streamflow_{station}.csv')

    return cleaned