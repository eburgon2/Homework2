import pandas as pd
import os



def clean_nwis_dataframe(df):
    #This was used before sending the final data to the discharge file
    """
    Cleans an NWIS Daily Values (DV) DataFrame:
    - Converts index to datetime (date only)
    - Renames '00060_Mean' to 'flow_cfs'
    - Removes any extra '00060_Mean_cd' (qualification code) columns
    """
    # 1. Ensure the index is datetime and strip H:M:S
    df.index = pd.to_datetime(df.index).date
    df.index = pd.to_datetime(df.index)
    
    # 2. Rename the flow column
    # USGS usually names this '00060_Mean' for Daily Values
    if '00060_Mean' in df.columns:
        df.rename(columns={'00060_Mean': 'flow_cfs'}, inplace=True)
    
    # 3. Remove the '00060_Mean_cd' column (the metadata/quality code)
    if '00060_Mean_cd' in df.columns:
        df.drop(columns=['00060_Mean_cd'], inplace=True)
        
    return df


def processSNOTEL(site, stateab, WYOI):
    print(site) #for tracking which loop the background is on 

    sitedf = pd.read_csv(f"files/SNOTEL/df_{site}_{stateab}_SNTL.csv")

    WYs = sitedf['Water_Year'].unique() #isolate water years

    WYsitedf = pd.DataFrame()

    for WY in WYs:
        cols =['M', 'D', 'Snow Water Equivalent (m) Start of Day Values']

        #get water year of interest
        wydf = sitedf[sitedf['Water_Year']==WY]
        wydf['M'] = pd.to_datetime(sitedf['Date']).dt.month
        wydf['D'] = pd.to_datetime(sitedf['Date']).dt.day

        #change NaN to 0, most NaN values are from low to 0 SWE measurements, otherwise it breaks
        wydf['Snow Water Equivalent (m) Start of Day Values'] = wydf['Snow Water Equivalent (m) Start of Day Values'].fillna(0)
        wydf = wydf[cols]
        wydf.rename(columns = {'Snow Water Equivalent (m) Start of Day Values':f"{WY}_SWE_m"}, inplace=True)
        wydf.reset_index(inplace=True, drop=True)
        WYsitedf[f"{WY}_SWE_in"] = wydf[f"{WY}_SWE_m"]*39.3701 #converting m to inches (standard for snotel)

        if len(wydf) == 365:
            try:
                WYsitedf.insert(0,'M',wydf['M'])
                WYsitedf.insert(1,'D',wydf['D'])
            except:
                pass

    #remove M/D to calculate row min, mean, median, max tiers
    df = WYsitedf.copy()
    #drop the water year of interest from WYsitedf to calculate the min, mean, median, max SWE for each day of the water year across all other years of data available for that site
    
    print(f"Dropping {WYOI} from the calculations of the min, mean, median, max SWE for each day of the water year across all other years of data available for that site")
    try:
        WYOIdrop = f"{WYOI}_SWE_in"
        coldrop = ['M', 'D', WYOIdrop]
        WYsitedf = WYsitedf.drop(columns = coldrop)
    except:
        print(f"{WYOI} not found in the data, not dropping any columns")
    
    
    #historical analysis columns 
    df['min'] = WYsitedf.min(axis=1)
    df['Q10'] = WYsitedf.quantile(0.10, axis=1)
    df['Q25'] = WYsitedf.quantile(0.25, axis=1)
    df['mean'] = WYsitedf.mean(axis=1)
    df['median'] = WYsitedf.median(axis=1)
    df['Q75'] = WYsitedf.quantile(0.75, axis=1)
    df['Q90'] = WYsitedf.quantile(0.90, axis=1)
    df['max'] = WYsitedf.max(axis=1)

    # Convert to datetime format
    df['date'] = pd.to_datetime(dict(year = 2023, month = df['M'], day = df['D'])) 

    # Format the date
    df['M-D'] = df['date'].dt.strftime('%m-%d')
    df.set_index('M-D', inplace=True)

    return df
