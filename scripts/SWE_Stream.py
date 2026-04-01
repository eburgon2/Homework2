import matplotlib.pyplot as plt
import matplotlib as mpl
import os
import pandas as pd
import numpy as np

def process_swe(sitedict):
    #empty dataframe we can concat to for all 3 SWE sites
    peaksites = pd.DataFrame()
    #loop over all three
    for site in sitedict.keys():
        test = sitedict[site].copy()

        #get index list for columns we will be maxing to find peak swer
        swe_cols_idx = [i for i, col in enumerate(test.columns) if '_SWE_in' in col]
        test.columns = test.columns.str.replace('_SWE_in', '', regex=False)#name changed to only include year for easy matching later
        columns = test.columns[swe_cols_idx[0]:swe_cols_idx[-1]+1]
        
        #store values to the data frame, make sure they are peak
        sitedf = pd.DataFrame({col: [test[col].max(skipna=True)] for col in columns})#taking max to only pull peak SWE
        #conbine sites while in the loop
        peaksites = pd.concat([peaksites,sitedf])

    #find average peak between the 3 sites 
    peakswe = pd.DataFrame([peaksites.mean(axis=0, skipna=True)]) #get mean for each site, assume this is basin SWE

    #clean up so we can use the column as datetime objects
    peakswe.index.name = 'Peak_Swe (in)'

    return peakswe

def Parity_Plot(peakswe,processed, watershed, AOI, plot = True):
    #month dictionary so we can name our subplots 
    monthdict = {1:("April",4),2:("May",5),3:("June",6),4:("July",7),5:("August",8),6:("September",9)}

    title = f'Parity Plots of Peak SWE and Volumetric Streamflow {watershed} Basin \n {AOI}'

    #create Figure
    fig, axs = plt.subplots(2,3, figsize = (14, 8))
    fig.suptitle(title)


    #Create years list for gradient map, letting me track historical values over time without manually making color list
    cmap = plt.cm.viridis
    years = sorted(list(peakswe.columns))
    colors = cmap(np.linspace(0.2, 1, len(years)))

    axs = axs.ravel()
    for i, key in enumerate(monthdict.keys()):
        #set a dataframe for the month loop
        df = processed[processed['M']== monthdict[key][1]]
        axs[i].set_title(f"Parity Plot for for {monthdict[key][0]}")

        #empty set for line of best fit  
        x_vals = []
        y_vals = []


        #Plot over years with the gradient as the colors 
        for n, col in enumerate(years):
            year_col = f"{col} Flow Volume (m^3)"
            if year_col in df.columns:
                x_val = peakswe[col].values[0]     #SWE
                y_val = df[year_col].sum()         #Volumetric flow
            
            axs[i].scatter(x_val,y_val, color=colors[n])
            #append values for fit-line
            x_vals.append(x_val)
            y_vals.append(y_val)

        #Create numpy array to make linear form line, then plot 
        x_vals = np.array(x_vals)
        y_vals = np.array(y_vals)
        m, b = np.polyfit(x_vals, y_vals, 1)
        x_line = np.linspace(min(x_vals), max(x_vals), 100)
        y_line = m * x_line + b
        axs[i].plot(x_line,y_line,color='red', linestyle='--', linewidth=2,label='Best Fit')
        axs[i].legend()

        axs[i].set_xlabel("Basin SWE (in)")
        axs[i].set_ylabel("Volumetric Streamflow (m^3)")
        #axs[i].set_xlim(0,20) #it is every other time that this is actually needed, I left it in incase the code breaks 

    #gradient map and legend
    norm = mpl.colors.Normalize(vmin=min(years), vmax=max(years))
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=axs,orientation='horizontal',aspect=40)
    cbar.set_label("Year")

    fig.subplots_adjust(bottom=0.3,wspace=0.4, hspace=0.5)
    plt.show()

    #Save point
    if plot == True:
        if not os.path.exists('Figures'):
            os.makedirs('Figures')
        fig.savefig(f"Figures/{watershed}_Parity_Plot.png",  dpi = 600, bbox_inches='tight')
