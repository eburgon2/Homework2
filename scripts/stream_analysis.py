import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.dates as mdates
import os
import pandas as pd
import datetime as dt


def process_stream(streamflow, WYOI):
    #reset index so I can match up date-time 
    streamflow.reset_index(inplace=True)
    years = pd.to_datetime(streamflow['Date']).dt.year.unique()

    yearsSited = pd.DataFrame()

    #loop over the years to obtain flow data
    for y in years:
        cols =['M', 'D', 'flow_cms']

        #columns for date, month, day 
        wydf = streamflow[pd.to_datetime(streamflow['Date']).dt.year == y]
        wydf['M'] = pd.to_datetime(streamflow['Date']).dt.month
        wydf['D'] = pd.to_datetime(streamflow['Date']).dt.day
        
        #change NaN to 0, most NaN values are from low to 0 SWE measurements so we don't want a type error later
        wydf['flow_cms'] = wydf['flow_cms'].fillna(0)

        #Reset columns to match index
        wydf = wydf[cols]
        wydf.rename(columns = {'flow_cms':f"{y} Flow (cms)"}, inplace=True)
        wydf.reset_index(inplace=True, drop=True)
        yearsSited[f"{y} Flow Volume (m^3)"] = wydf[f"{y} Flow (cms)"]*60*60*40 #convert to day-volume flow 

        #Make sure dates follow MM-DD
        if len(wydf) == 365:
            try:
                yearsSited.insert(0,'M',wydf['M'])
                yearsSited.insert(1,'D',wydf['D'])
            except:
                pass

    #remove outer months, we will only need April-September later 
    months = [1,2,3,11,12]
    yearsSited = yearsSited[~yearsSited['M'].isin(months)]

    #remove M/D to calculate row min, mean, median, max tiers
    df = yearsSited.copy()

    #drop the water year of interest to calculate the min, mean, median, max flow volume for each day of the water year across all other years of data available
    print(f"Dropping {WYOI} from the calculations of the min, mean, median, max Flow Volume for each day of the water year across all other years of data available")
    try:
        WYOIdrop = f"{WYOI} Flow (cms)"
        coldrop = ['M', 'D', WYOIdrop]
        yearsSited = yearsSited.drop(columns = coldrop)
    except:
        pass 

    #data columns for historical analysis 
    df['min'] = yearsSited.min(axis=1)
    df['Q10'] = yearsSited.quantile(0.10, axis=1)
    df['Q25'] = yearsSited.quantile(0.25, axis=1)
    df['mean'] = yearsSited.mean(axis=1)
    df['median'] = yearsSited.median(axis=1)
    df['Q75'] = yearsSited.quantile(0.75, axis=1)
    df['Q90'] = yearsSited.quantile(0.90, axis=1)
    df['max'] = yearsSited.max(axis=1)

    # Convert to datetime format
    df['Date'] = pd.to_datetime(dict(year = 2023, month = df['M'], day = df['D']))

    # Format the date and index
    df['M-D'] = df['Date'].dt.strftime('%m-%d')
    df.set_index(df['Date'], inplace=True)
    return df


def StreamPlots(processed, WY, watershed, AOI, DOI,plot = True):
    #Set dictionary for months so we can get names 
    monthdict = {1:("April",4),2:("May",5),3:("June",6),4:("July",7),5:("August",8),6:("September",9)}

    title = f'Historical Discharge Volume Analysis of {watershed} Basin \n {AOI}'

    #make the figure 
    fig, axs = plt.subplots(2, 3, figsize = (14, 8))
    fig.suptitle(title)
    opacity = 0.25
    WYOI = f"{WY} Flow Volume (m^3)"

    axs = axs.ravel()
    #loop over the months since each subplot represents one
    for i, key in enumerate(monthdict.keys()):
        df = processed[processed['M']== monthdict[key][1]] #create datframe for only the month we are targetting

        axs[i].set_title(f"Streamflow Cumulative Volume for {monthdict[key][0]}")

        #check dataframe for respective water year
        if f"{WY} Flow Volume (m^3)" in df.columns:
            #key swe lines on plot for volumetric flow 
            axs[i].plot(df.index, df['max'].cumsum(), color = 'slateblue', label = 'Max',linewidth=2)
            axs[i].plot(df.index, df['median'].cumsum(), color = 'green', label = 'Median',linewidth=2)
            axs[i].plot(df.index, df['min'].cumsum(), color = 'red', label = 'Min',linewidth=2)
            axs[i].plot(df.index, df['mean'].cumsum(), color = 'orange', label = 'Mean',linewidth=2)
            
            #Fill between Quantiles for visual aid
            axs[i].fill_between(df.index, df['max'].cumsum(), df['Q90'].cumsum(), color = 'slateblue', alpha = opacity, label = 'Q90')
            axs[i].fill_between(df.index, df['Q90'].cumsum(), df['Q75'].cumsum(), color = 'cyan', alpha = opacity, label = 'Q75')
            axs[i].fill_between(df.index, df['Q75'].cumsum(), df['Q25'].cumsum(), color = 'green', alpha = opacity)
            axs[i].fill_between(df.index, df['Q25'].cumsum(), df['Q10'].cumsum(), color = 'yellow', alpha = opacity, label = 'Q25')
            axs[i].fill_between(df.index, df['Q10'].cumsum(), df['min'].cumsum(), color = 'red', alpha = opacity, label = 'Q10')
            
            #Plot year of interest for comparison, increased thickness
            axs[i].plot(df[WYOI].cumsum(), color = 'black', label = f"WY {WY}",linewidth=2)

            #Get stats for comparison for only April Graph since our DOI is only on that one (04-01-2025)
            if  monthdict[key][1] == 4:
                df.set_index('M-D',inplace=True)
                mpeak = max(df['median'])
                mpeakday = f"{WY}-{df.index[df['median']==mpeak][0]}"
                WYpeak = max(df[WYOI])
                WYpeakday = f"{WY}-{df.index[df[WYOI]==WYpeak][0]}"
                doivalue = df.loc[DOI, WYOI] if DOI in df.index else None
                doimed = df.loc[DOI, 'median'] if DOI in df.index else None
                QDiff_day = (pd.to_datetime(WYpeakday)-pd.to_datetime(mpeakday)).days
                medpercPeak = round(doivalue/mpeak *100, 0)
                medperc = round(doivalue/doimed *100, 0)
                
                #Create box with max point and DOI
                props = dict(boxstyle='round', facecolor='white', alpha=0.5)
                axs[i].text(0.05, 0.90, f"DOI: {WY}-{DOI} \n % of median - {medperc}%  \n % of median peak - {medpercPeak}% \n Peak WY Flowrate Date: {WYpeakday}  \n Days from Median Peak - {QDiff_day}",
                            transform=axs[i].transAxes,fontsize=8,verticalalignment='top',bbox=props)
                
            #Set axis labels
            axs[i].xaxis.set_major_locator(ticker.MaxNLocator(4))
            axs[i].xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
            axs[i].tick_params(labelrotation=45)
            handles, labels = axs[i].get_legend_handles_labels()

        else:
            axs[i].annotate('No Data', xy=(0.45, 0.45), xytext=(0.45, 0.45))

    # Set axis labels
        axs[i].set_xlabel('Date')
        axs[i].set_ylabel('Cumulative Volume (cubic meters)')

    #size/format subplots and legens
    fig.subplots_adjust( hspace=0.5,wspace=0.5)        
    fig.legend(handles, labels,loc='lower center',ncol=8, bbox_to_anchor=(.5, -.05))
    plt.show()

    #save point
    if plot == True:
        if not os.path.exists('Figures'):
            os.makedirs('Figures')
        fig.savefig(f"Figures/{watershed}_{WY}_sstreamflowanalysis.png",  dpi = 600, bbox_inches='tight')