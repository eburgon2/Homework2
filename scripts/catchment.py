from __future__ import annotations
from pathlib import Path
import dataretrieval.nwis as nwis
import geopandas as gpd
import numpy as np
import pandas as pd
import pynhd as nhd
from pynhd import NLDI, NHDPlusHR, WaterData
import py3dep
import pygeohydro as gh
import networkx as nx
import xarray as xr
import xrspatial
import os
from scripts import maps, data, dataprocessing, SNOTEL_Analyzer, files
nldi = NLDI()


def nldi_info(station,navigation,source):
    flow = nldi.navigate_byid(
        fsource="nwissite",
        fid=f"USGS-{station}",
        navigation=navigation,
        source=source,
        distance=1000,
    )
    return flow

def active(all_stations):
    station_ids = all_stations['identifier'].str.replace('USGS-', '').tolist()
    inventory_df, metadata = nwis.get_info(sites=station_ids, seriesCatalogOutput=True)
    discharge_info = inventory_df[inventory_df['parm_cd'] == '00060']
    df = discharge_info[['site_no', 'station_nm', 'begin_date', 'end_date']]
    df = df.drop_duplicates(subset='site_no', keep='first').reset_index(drop=True)
    st_active = df[df['end_date'] > '2025-10-01'] #end date conservative to ensure DOI is included
    active_station_ids = st_active['site_no'].tolist()
    active_station_ids = ['USGS-' + id for id in active_station_ids]
    st_active = all_stations[all_stations['identifier'].isin(active_station_ids)]

    return st_active

def slope(flw_trib):
    vaa = nhd.nhdplus_vaa("input_data/nhdplus_vaa.parquet")
    flw_trib["comid"] = pd.to_numeric(flw_trib.nhdplus_comid)
    slope = gpd.GeoDataFrame(
        pd.merge(flw_trib, vaa[["comid", "slope"]], left_on="comid", right_on="comid"),
        crs=flw_trib.crs,
    )
    slope[slope.slope < 0] = np.nan
    return slope

def DEM(geometry,station):
    topo = py3dep.get_map(["DEM", "Slope Degrees"], geometry, 90, geo_crs=4326, crs=5070) # Get the DEM and slope for the basin geometry at 90m resolution, reproject to 5070, and convert slope from degrees to m/m
    dem = py3dep.get_dem(geometry, 30) # Get the DEM for the basin geometry at 30m resolution
    dem = dem.rio.reproject(5070) # Reproject the DEM to match the CRS of the slope and the flowlines
    slope = py3dep.deg2mpm(xrspatial.slope(dem)) # Calculate slope in m/m from the DEM using xrspatial, which handles the spatial resolution and units correctly
    topo = xr.merge([dem, slope]) # Merge the DEM and slope into a single xarray dataset

    if not os.path.exists('files/DEM'):
        os.makedirs('files/DEM')
    
    dem.rio.to_raster(Path("files/DEM", f"dem_{station}.tif"))
    return topo

def basin_dataframe(topo, geometry, basinname, basin, station):
    ave_basin_elevation = topo.elevation.mean().values
    min_basin_elevation = topo.elevation.min().values
    max_basin_elevation = topo.elevation.max().values

    ave_basin_slope = topo.slope.mean().values
    gs = gpd.GeoSeries([geometry], crs="EPSG:4326")
    gs_meters = gs.to_crs(epsg=3857)

    # Calculate area (returns square meters)
    area_m2 = gs_meters.area.iloc[0]
    area_km2 = area_m2 / 1_000_000

    basin_info = pd.DataFrame({
        "Basin_Name": [basinname],
        "station_id": [station],
        "Average_Elevation_m": [ave_basin_elevation],
        "Minimum_Elevation_m": [min_basin_elevation],
        "Maximum_Elevation_m": [max_basin_elevation],
        "Average_Slope": [ave_basin_slope],
        "Area_km2": [area_km2],
    })

    gdf = gpd.GeoDataFrame(index=[0], crs="EPSG:4326", geometry=[geometry])
    nlcd_data = gh.nlcd_bygeom(gdf)

    station_ids = [station]
    geometry = NLDI().get_basins(station)
    basin_info.index = station_ids
    return basin_info
