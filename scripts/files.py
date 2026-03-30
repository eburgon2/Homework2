from __future__ import annotations
from pathlib import Path
import dataretrieval.nwis as nwis
import datetime
import geopandas as gpd
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pynhd as nhd
from pynhd import NLDI, NHDPlusHR, WaterData
import py3dep
import pygeohydro as gh
from pathlib import Path
import networkx as nx
import xarray as xr
import xrspatial
import os
from scripts import maps, data, dataprocessing, SNOTEL_Analyzer

nldi = NLDI()

def basinFile(basin, basinname, station):
    if not os.path.exists('files'):
        os.makedirs('files/Basin')
    basin.to_file(f"files/Basin/{basinname}.shp")
    print('done')

    site_feature = nldi.getfeature_byid("nwissite", f"USGS-{station}")
    upstream_network = nldi.navigate_byid(
    "nwissite", f"USGS-{station}", "upstreamMain", "flowlines", distance=9999
    )

    return site_feature, upstream_network

def snotelFile(geometry, state):
    all_stations_gdf = gpd.read_file('https://raw.githubusercontent.com/egagli/snotel_ccss_stations/main/all_stations.geojson').set_index('code')
    all_stations_gdf = all_stations_gdf[all_stations_gdf['csvData']==True]
    gdf_in_bbox = all_stations_gdf[all_stations_gdf.geometry.within(geometry)]
    gdf_in_bbox.reset_index(drop=False, inplace=True)
    gdf_in_bbox['beginDate'] = [datetime.datetime.strftime(gdf_in_bbox['beginDate'][i], "%Y-%m-%d") for i in np.arange(0,len(gdf_in_bbox),1)]
    gdf_in_bbox['endDate'] = [datetime.datetime.strftime(gdf_in_bbox['endDate'][i], "%Y-%m-%d") for i in np.arange(0,len(gdf_in_bbox),1)]

    OutputFolder = 'files/SNOTEL'
    if not os.path.exists(OutputFolder):
        os.makedirs(OutputFolder)

    for i in gdf_in_bbox.index:
        data.getSNOTEL(gdf_in_bbox.name[i], gdf_in_bbox.code[i],state, gdf_in_bbox.beginDate[i], gdf_in_bbox.endDate[i], OutputFolder)
    
    return gdf_in_bbox

def dischargeFile(station):
    streamflow = data.get_usgs_streamflow(station)
    cleaned = dataprocessing.clean_nwis_dataframe(streamflow)
    cleaned.index.name = "Date"

    cleaned['flow_cfs'] = cleaned['flow_cfs'] * 0.0283168
    cleaned.rename(columns={'flow_cfs': 'flow_cms'}, inplace=True)

    OutputFolder = 'files/NWIS'
    if not os.path.exists(OutputFolder):
        os.makedirs(OutputFolder)
    cleaned.to_csv(f'{OutputFolder}/streamflow_{station}.csv')

    return cleaned