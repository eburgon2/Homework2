import os
import sys
import pytz
import urllib3
import datetime
import numpy as np
import pandas as pd
import pyproj
from dataretrieval import nwis
pd.options.mode.chained_assignment = None

def getSNOTEL(SiteName, SiteID, StateAbb, StartDate, EndDate, OutputFolder):
    #Honestly until the website breaks I am not touching this 
    #the api changed and we need to pull the site id out - 3-1-2026
    site_id = SiteID.split('_')[0]
    url1 = 'https://wcc.sc.egov.usda.gov/reportGenerator/view_csv/customMultiTimeSeriesGroupByStationReport/daily/start_of_period/'
    #url2 = f'{SiteID}:{StateAbb}:SNTL%7Cid=%22%22%7Cname/'
    url2 = f'{site_id}:{StateAbb}:SNTL%7Cid=%22%22%7Cname/'
    url3 = f'{StartDate},{EndDate}/'
    url4 = 'WTEQ::value?fitToScreen=false'
    url = url1+url2+url3+url4
    print(f'Start retrieving data for {SiteName}, {SiteID} \n {url}')

    http = urllib3.PoolManager()
    response = http.request('GET', url)
    data = response.data.decode('utf-8')
    i=0
    for line in data.split("\n"):
        if line.startswith("#"):
            i=i+1
    data = data.split("\n")[i:]

    df = pd.DataFrame.from_dict(data) 
    df = df[0].str.split(',', expand=True)
    df.rename(columns={0:df[0][0], 
                        1:df[1][0]}, inplace=True)
    df.drop(0, inplace=True)
    df.dropna(inplace=True)
    df.reset_index(inplace=True, drop=True)
    df["Date"] = pd.to_datetime(df["Date"])
    df.rename(columns={df.columns[1]:'Snow Water Equivalent (m) Start of Day Values'}, inplace=True)
    df.iloc[:, 1:] = df.iloc[:, 1:].apply(lambda x: pd.to_numeric(x) * 0.0254)  # convert in to m
    df['Water_Year'] = pd.to_datetime(df['Date']).map(lambda x: x.year+1 if x.month>9 else x.year)

    #Save point
    df.to_csv(f'./{OutputFolder}/df_{SiteID}_{StateAbb}_SNTL.csv', index=False)


def convert_utc_to_local(state_abbr, df):
    state_timezones = {
    'AL': 'US/Central', 'AK': 'US/Alaska', 'AZ': 'US/Mountain', 'AR': 'US/Central',
    'CA': 'US/Pacific', 'CO': 'US/Mountain', 'CT': 'US/Eastern', 'DE': 'US/Eastern',
    'FL': 'US/Eastern', 'GA': 'US/Eastern', 'HI': 'US/Hawaii', 'ID': 'US/Mountain',
    'IL': 'US/Central', 'IN': 'US/Eastern', 'IA': 'US/Central', 'KS': 'US/Central',
    'KY': 'US/Eastern', 'LA': 'US/Central', 'ME': 'US/Eastern', 'MD': 'US/Eastern',
    'MA': 'US/Eastern', 'MI': 'US/Eastern', 'MN': 'US/Central', 'MS': 'US/Central',
    'MO': 'US/Central', 'MT': 'US/Mountain', 'NE': 'US/Central', 'NV': 'US/Pacific',
    'NH': 'US/Eastern', 'NJ': 'US/Eastern', 'NM': 'US/Mountain', 'NY': 'US/Eastern',
    'NC': 'US/Eastern', 'ND': 'US/Central', 'OH': 'US/Eastern', 'OK': 'US/Central',
    'OR': 'US/Pacific', 'PA': 'US/Eastern', 'RI': 'US/Eastern', 'SC': 'US/Eastern',
    'SD': 'US/Central', 'TN': 'US/Central', 'TX': 'US/Central', 'UT': 'US/Mountain',
    'VT': 'US/Eastern', 'VA': 'US/Eastern', 'WA': 'US/Pacific', 'WV': 'US/Eastern',
    'WI': 'US/Central', 'WY': 'US/Mountain'
    }

    # Extract the state abbreviation from the filename
    # state_abbr = os.path.basename(filename).split('_')[2]  
    timezone = state_timezones.get(state_abbr)

    if timezone:
        # Convert the 'Date' column to datetime
        df['Date'] = pd.to_datetime(df['Date'], utc=True)
        
        # Convert to local time zone
        local_tz = pytz.timezone(timezone)
        df['Date_Local'] = df['Date'].dt.tz_convert(local_tz)

         # Save the timezone-aware Date_Local column
        df['Date_Local'] = df['Date_Local'].astype(str)
        df['Date_Local'] = df['Date_Local'].apply(lambda x: datetime.datetime.strptime(x, '%Y-%m-%d %H:%M:%S%z'))
        df['Date_Local'] = df['Date_Local'].apply(lambda x: x.replace(tzinfo=None))

    else:
        print(f"Timezone for state abbreviation {state_abbr} not found.")
        
    return df


def get_usgs_streamflow(site_id, start_date="1980-01-01", end_date='2025-10-01'): #end date set later to be conservative with the assingment
    """
    Retrieves daily mean streamflow data from USGS NWIS.
    
    Parameters:
    site_id (str): The USGS station ID (e.g., '09380000')
    start_date (str): Beginning date in 'YYYY-MM-DD' format
    end_date (str): End date in 'YYYY-MM-DD' format
    """
    # Parameter code '00060' refers specifically to Discharge (streamflow) in cfs
    parameter_code = '00060'
    
    print(f"Retrieving data for Site: {site_id} from {start_date} to {end_date}...")
    
    try:
        # get_dv retrieves "Daily Values"
        # returns a DataFrame and a metadata object
        df, metadata = nwis.get_dv(
            sites=site_id, 
            start=start_date, 
            end=end_date, 
            parameterCd=parameter_code
        )
        
        # Clean up the column names for easier use
        # Usually, the flow data is in a column like '00060_Mean'
        df.rename(columns={f'{parameter_code}_00003': 'Streamflow_cfs'}, inplace=True)
        
        return df
        
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
    
 #Main Data Fetcher

#Everything below is kept just in case, I don't believe I actually used these but I don't want to delete and be wrong
#Temporal Reduction Wrapper (The "Outer" Function)
def wrap_make_daily(collection, start_date):
    def make_daily(day_offset):
        d = start_date.advance(day_offset, 'day')
        daily_images = collection.filterDate(d, d.advance(1, 'day'))
        
        return (daily_images.mean()
                .set('system:time_start', d.millis())
                .set('date', d.format('YYYY-MM-dd')))
    return make_daily
    
    
    
# Spatial Reduction Function
def get_all_metrics(image, basin_polygon):
    import ee
    ee.Authenticate()
    ee.Initialize()
    stats = image.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=basin_polygon,
        scale=12500,
        maxPixels=1e9
    )
    return ee.Feature(None, stats).set('date', image.date().format())
    

if __name__ == "__main__":
	SiteName = sys.argv[1]
	SiteID = sys.argv[2]
	StateAbb = sys.argv[3]
	StartDate = sys.argv[4]
	EndDate = sys.argv[5]
	OutputFolder = sys.argv[6]
	
