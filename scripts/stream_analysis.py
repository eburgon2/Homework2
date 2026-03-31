import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.dates as mdates
import os
import pandas as pd
import datetime as dt


def process_stream(streamflow, WYOI):
    
    years = pd.to_datetime(streamflow['Date']).dt.year.unique()

    yearsSited = pd.DataFrame()

    for y in years:
        cols =['M', 'D', 'Flow Volume (m^3)']

        wydf = streamflow[pd.to_datetime(streamflow['Date']).dt.year == y]
        wydf['M'] = pd.to_datetime(streamflow['Date']).dt.month
        wydf['D'] = pd.to_datetime(streamflow['Date']).dt.day
    
        #change NaN to 0, most NaN values are from low to 0 SWE measurements
        wydf['Flow Volume (m^3)'] = wydf['Flow Volume (m^3)'].fillna(0)
        wydf = wydf[cols]
        wydf.rename(columns = {'Flow Volume (m^3)':f"{y} Flow Volume (m^3)"}, inplace=True)
        wydf.reset_index(inplace=True, drop=True)
        yearsSited[f"{y} Flow Volume (m^3)"] = wydf[f"{y} Flow Volume (m^3)"]
    
        if len(wydf) == 365:
            try:
                yearsSited.insert(0,'M',wydf['M'])
                yearsSited.insert(1,'D',wydf['D'])
            except:
                pass
    
    #remove outer months
    months = [1,2,3,11,12]
    yearsSited = yearsSited[~yearsSited['M'].isin(months)]
    
    # #remove M/D to calculate row min, mean, median, max tiers
    df = yearsSited.copy()

    #drop the water year of interest to calculate the min, mean, median, max flow volume for each day of the water year across all other years of data available
    print(f"Dropping {WYOI} from the calculations of the min, mean, median, max Flow Volume for each day of the water year across all other years of data available")
    try:
        WYOIdrop = f"{WYOI} Flow Volume (m^3)"
        coldrop = ['M', 'D', WYOIdrop]
        yearsSited = yearsSited.drop(columns = coldrop)
    except:
        print(f"{WYOI} not found in the data, not dropping any columns")
   
    df['min'] = yearsSited.min(axis=1)
    df['Q10'] = yearsSited.quantile(0.10, axis=1)
    df['Q25'] = yearsSited.quantile(0.25, axis=1)
    df['mean'] = yearsSited.mean(axis=1)
    df['median'] = yearsSited.median(axis=1)
    df['Q75'] = yearsSited.quantile(0.75, axis=1)
    df['Q90'] = yearsSited.quantile(0.90, axis=1)
    df['max'] = yearsSited.max(axis=1)

    # Convert to datetime format
    df['date'] = pd.to_datetime(dict(year = 2023, month = df['M'], day = df['D']))
    
    # Format the date
    df['M-D'] = df['date'].dt.strftime('%m-%d')
    #df.set_index('M-D', inplace=True)
    df['M-D'] = pd.to_datetime(df['M-D'],format='%m-%d')
    df.set_index(df['date'], inplace=True)
    return df


def StreamPlots(processed, WY, watershed, AOI, DOI,plot = True):
    
    monthdict = {1:("April",4),2:("May",5),3:("June",6),4:("July",7),5:("August",8),6:("September",9)}

    title = f'Historical Discharge Volume Analysis of {watershed} Basin \n {AOI}'

    fig, axs = plt.subplots(2, 3, figsize = (14, 10))
    fig.suptitle(title)
    opacity = 0.25
    WYOI = f"{WY} Flow Volume (m^3)"

    axs = axs.ravel()
    for i, key in enumerate(monthdict.keys()):
        df = processed[processed['M']== monthdict[key][1]]

        axs[i].set_title(f"Streamflow Volume for {monthdict[key][0]}")
        #check dataframe for respective water year
        if f"{WY} Flow Volume (m^3)" in df.columns:
            #key swe lines on SNOTEL plot
            axs[i].plot(df.index, df['max'], color = 'slateblue', label = 'Max')
            axs[i].plot(df.index, df['median'], color = 'green', label = 'Median')
            axs[i].plot(df.index, df['min'], color = 'red', label = 'Min')
            axs[i].plot(df.index, df['mean'], color = 'orange', label = 'Mean')
            
            #Fill between Quantiles
            axs[i].fill_between(df.index, df['max'], df['Q90'], color = 'slateblue', alpha = opacity, label = 'Q90')
            axs[i].fill_between(df.index, df['Q90'], df['Q75'], color = 'cyan', alpha = opacity, label = 'Q75')
            axs[i].fill_between(df.index, df['Q75'], df['Q25'], color = 'green', alpha = opacity)
            axs[i].fill_between(df.index, df['Q25'], df['Q10'], color = 'yellow', alpha = opacity, label = 'Q25')
            axs[i].fill_between(df.index, df['Q10'], df['min'], color = 'red', alpha = opacity, label = 'Q10')
            
            #identify max for legend per plot
            max_val = df["max"].max()
            max_id = df['max'].idxmax()
            axs[i].scatter(max_id, max_val, color='purple')
            props = dict(boxstyle='round', facecolor='white', alpha=0.5)
            
            #Plot year & day of interest for comparison
            axs[i].plot(df[WYOI], color = 'black', label = f"WY {WY}")
            axs[i].axvline(DOI, color='black', linestyle='--')

            #Get stats for comparison 
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
            axs[i].text(0.05, 0.90, f"DOI: {WY}-{DOI} \n % of median - {medperc}%  \n % of median peak - {medpercPeak}% \n Peak WY Volumetric Flowrate Date: {WYpeakday}  \n Days from Median Peak - {QDiff_day} \n Hist. Peak: {max_val:.0f} m^3",
                        transform=axs[i].transAxes,fontsize=10,verticalalignment='top',bbox=props)
            
            #Set axis labels
            axs[i].xaxis.set_major_locator(ticker.MaxNLocator(4))
            axs[i].xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
            axs[i].tick_params(labelrotation=45)
            handles, labels = axs[i].get_legend_handles_labels()

        else:
            axs[i].annotate('No Data', xy=(0.45, 0.45), xytext=(0.45, 0.45))

    # Set axis labels
        axs[i].set_xlabel('Date')
        axs[i].set_ylabel('Flow Volume (cubic meters)')

 
    fig.subplots_adjust( hspace=0.5,wspace=0.5)        
    fig.legend(handles, labels,loc='lower center',ncol=8, bbox_to_anchor=(.5, -.05))
    plt.show()

    if plot == True:
        if not os.path.exists('Figures'):
            os.makedirs('Figures')
        fig.savefig(f"Figures/{watershed}_{WY}_sstreamflowanalysis.png",  dpi = 600, bbox_inches='tight')


def SWE_Stream_Comparison(processed,catchmentswe, WY, watershed, AOI,plot = True):
    
    monthdict = {1:("April",4),2:("May",5),3:("June",6),4:("July",7),5:("August",8),6:("September",9)}

    title = f'Historical Discharge Volume Analysis of {watershed} Basin \n {AOI}'

    fig, axs = plt.subplots(2, 3, figsize = (14, 10))
    fig.suptitle(title)
    opacity = 0.25
    WYOI = f"{WY} Flow Volume (m^3)"

    axs = axs.ravel()
    for i, key in enumerate(monthdict.keys()):
        df = processed[processed['M']== monthdict[key][1]]
        catchment = catchmentswe[catchmentswe.index.month == monthdict[key][1]].copy()
        #Plot SWE Peak line from Catchment summary to show historical peak SWE

        #Plot streamflow values as scatterplots to match the Parity Plot Requirement
        axs[i].set_title(f"Streamflow Volume for {monthdict[key][0]}")
        #check dataframe for respective water year
        if f"{WY} Flow Volume (m^3)" in df.columns:
            #key swe lines on SNOTEL plot
            axs[i].scatter(df.index, df['max'], color = 'slateblue', label = 'Max')
            axs[i].scatter(df.index,df['median'], color = 'green', label = 'Median')
            axs[i].scatter(df.index,df['min'], color = 'red', label = 'Min')
            # axs[i].scatter(df.index,df['Q90'], color = 'blue', label = 'Q90')
            # axs[i].scatter(df.index,df['Q75'], color = 'cyan',label = 'Q75')
            # axs[i].scatter(df.index,df['Q25'], color = 'orange', label = 'Q25')
            # axs[i].scatter(df.index,df['Q10'], color = 'yellow', label = 'Q10')

            axs[i].xaxis.set_major_locator(ticker.MaxNLocator(4))
            axs[i].xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
            axs[i].tick_params(labelrotation=45)
            handles, labels = axs[i].get_legend_handles_labels()

        else:
            axs[i].annotate('No Data', xy=(0.45, 0.45), xytext=(0.45, 0.45))

    # Set axis labels
        axs[i].set_xlabel('Date')
        axs[i].set_ylabel('Flow Volume (cubic meters)')

        ax2 = axs[i].twinx()
        ax2.plot(catchment.index,catchment['max'],color='black',label='Peak SWE')
        ax2.set_ylabel('SWE (inches)')
 
    fig.subplots_adjust( hspace=0.5,wspace=0.5)        
    fig.legend(handles, labels,loc='lower center',ncol=8, bbox_to_anchor=(.5, -.05))
    plt.show()

    if plot == True:
        if not os.path.exists('Figures'):
            os.makedirs('Figures')
        fig.savefig(f"Figures/{watershed}_comparison.png",  dpi = 600, bbox_inches='tight')