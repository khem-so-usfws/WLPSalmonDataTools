#!/usr/bin/env python
# coding: utf-8

# In[1]:


### WLP_Salmon_Spawning_Survey_DataJoinSummary_v1.py
### Version: 5/10/2022
### Author: Khem So, khem_so@fws.gov, (503) 231-6839
### Abstract: This Python 3 script pulls data from the Willapa NWR salmon spawning survey ArcGIS Online feature service and performs joins and merges to result in a combined Excel dataset.


# In[2]:


import arcpy
import pandas as pd
from arcgis import GIS
import time, os, fnmatch, shutil


# In[3]:


arcpy.AddMessage("Starting...")

### ArcGIS Online stores date-time information in UTC by default. This function uses the pytz package to convert time zones and can be used to convert from UTC ("UTC") to localized time. For example, localized "US/Pacific" is either Pacific Standard Time UTC-8 or Pacific Daylight Time UTC-7 depending upon time of year.
from datetime import datetime
from pytz import timezone
def change_timezone_of_field(df, source_date_time_field, new_date_time_field_suffix, source_timezone, new_timezone):
    """Returns the values in *source_date_time_field* with its timezone converted to a new timezone within a new field *new_date_time_field*
    : param df: The name of the spatially enabled or pandas DataFrame containing datetime fields
    : param source_date_time_field: The name of the datetime field whose timezone is to be changed
    : param new_date_time_field_suffix: Suffix appended to the end of the name of the source datetime field. This is used to create the new date time field name.
    : param source_timezone: The name of the source timezone
    : param new_timezone: The name of the converted timezone. For possible values, see https://gist.github.com/heyalexej/8bf688fd67d7199be4a1682b3eec7568
    """
    # Define the source timezone in the source_date_time_field
    df[source_date_time_field] = df[source_date_time_field].dt.tz_localize(source_timezone)
    # Define the name of the new date time field
    new_date_time_field = source_date_time_field + new_date_time_field_suffix
    # Convert the datetime in the source_date_time_field to the new timezone in a new field called new_date_time_field
    df[new_date_time_field] = df[source_date_time_field].dt.tz_convert(new_timezone)


# In[4]:


### This function converts Python datetime64 fields to %m/%d/%Y %H:%M:%S %Z%z format
def archive_dt_field(df):
    """Selects fields with data types of 'datetime64[ns, UTC]','datetime64[ns, US/Pacific]' and converts to %m/%d/%Y %H:%M:%S %Z%z format for archiving to Excel
    : param df: The name of the spatially enabled or pandas DataFrame containing datetime fields
    """
    archive_dt_field_list = df.select_dtypes(include=['datetime64[ns, UTC]','datetime64[ns, US/Pacific]'])
    for col in archive_dt_field_list:
        df[col] = df[col].dt.strftime('%m/%d/%Y %H:%M:%S %Z%z')


# In[5]:


### Allow authentication via login to U.S. Fish & Wildlife Service ArcGIS Online account via ArcGIS Pro
gis = GIS("pro")


# In[6]:


### Enter year of interest
# uncomment next line to use ArcGIS interface, otherwise hard coding year
year = arcpy.GetParameterAsText(0)
# year = "2021"


# In[7]:


### Enter path for local file saving
# uncomment next line to use ArcGIS interface, otherwise hard coding out_workspace
out_workspace = arcpy.GetParameterAsText(1)
# out_workspace = "C:/Users/kso/Desktop/"


# In[8]:


### Create timestamp for file naming
t = time.localtime()
timestamp = time.strftime('%Y-%m-%d_%H%M', t)


# In[9]:


### Paths to ArcGIS Online data
# To populate Service ItemId, go to Feature Service webpage and in bottom right corner, click on the View link.
# Current Feature Service webpage: https://fws.maps.arcgis.com/home/item.html?id=758626eec0fc4bc1a72b4e4c9bd1023c
ServiceItemID = gis.content.get("758626eec0fc4bc1a72b4e4c9bd1023c")

### There are separate methods for pulling spatial versus non-spatial data into Python. Spatial layers will become Spatially Enabled DataFrame objects. Non-spatial data will become regular pandas DataFrame objects.
## Define variables pointing to spatial layers
MetadataLyr = ServiceItemID.layers[0]
LiveFishLyr = ServiceItemID.layers[1]
CarcassLyr = ServiceItemID.layers[2]
## Create Spatially Enabled DataFrame objects
sedfMetadata = pd.DataFrame.spatial.from_layer(MetadataLyr)
sedfLiveFishLocation = pd.DataFrame.spatial.from_layer(LiveFishLyr)
sedfCarcassLocation = pd.DataFrame.spatial.from_layer(CarcassLyr)

## Define variables point to non-spatial (tabular) data
Observer = r"https://services.arcgis.com/QVENGdaPbd4LUkLV/arcgis/rest/services/service_c555c76424ca452d8dab8de4f8c25000/FeatureServer/3"

## Convert AGOL table to NumPy Array and then to pandas DataFrames
naObserver = arcpy.da.TableToNumPyArray(Observer,["objectid","globalid","strFirstName","strLastName","parentglobalid","CreationDate","Creator","EditDate","Editor"])
dfObserver = pd.DataFrame(naObserver)

arcpy.AddMessage("Downloaded data from ArcGIS Online...")


# In[10]:


### Use change_timezone_of_field function to convert all datetime fields in dataframe from UTC to Pacific within new field with _Pacific suffix
for col in sedfMetadata.columns:
     if sedfMetadata[col].dtype == 'datetime64[ns]':
         change_timezone_of_field(sedfMetadata, col, "_Pacific", "UTC", "US/Pacific")

for col in sedfLiveFishLocation.columns:
     if sedfLiveFishLocation[col].dtype == 'datetime64[ns]':
         change_timezone_of_field(sedfLiveFishLocation, col, "_Pacific", "UTC", "US/Pacific")

for col in sedfCarcassLocation.columns:
     if sedfCarcassLocation[col].dtype == 'datetime64[ns]':
         change_timezone_of_field(sedfCarcassLocation, col, "_Pacific", "UTC", "US/Pacific")

for col in dfObserver.columns:
     if dfObserver[col].dtype == 'datetime64[ns]':
         change_timezone_of_field(dfObserver, col, "_Pacific", "UTC", "US/Pacific")


# In[11]:


### Filter sedfMetadata by single year
sedfMetadataYYYY = sedfMetadata[sedfMetadata["dtmDate"].dt.strftime('%Y') == year]


# In[12]:


### Export raw data frames as backup
## Use archive_dt_field function to convert Python date time into format Excel can read more easily
archive_dt_field(sedfMetadata)
archive_dt_field(sedfLiveFishLocation)
archive_dt_field(sedfCarcassLocation)
archive_dt_field(dfObserver)

## Create export paths for backup and writes to Excel spreadsheet
writer = pd.ExcelWriter(os.path.join(out_workspace,('WLP_Salmon_Spawning_Survey_BKUP_' + timestamp + '.xlsx')))
sedfMetadata.to_excel(writer, 'Metadata', index=False)
sedfLiveFishLocation.to_excel(writer, 'Live Fish', index=False)
sedfCarcassLocation.to_excel(writer, 'Carcasses', index=False)
dfObserver.to_excel(writer, 'Observers', index=False)
writer.save()

arcpy.AddMessage("Exported raw data as Excel spreadsheet for backup...")


# In[13]:


### Create dfObserver2 data frame with concatenated surveyor names grouped by parentglobalid
## Clean up names
dfObserver["strFirstName"] = dfObserver["strFirstName"].str.strip()
dfObserver["strLastName"] = dfObserver["strLastName"].str.strip()

## Process dfObserver to get single concatenated field for full name
dfObserver["strFullName"] = dfObserver["strFirstName"] + " " + dfObserver["strLastName"]

## Process dfObserver to remove curly brackets to allow for join based on GUID
dfObserver = dfObserver.replace("{","", regex=True)
dfObserver = dfObserver.replace("}","", regex=True)

## Process dfObserver to get concatenated list of full surveyor names by survey
dfObserver2 = dfObserver[["parentglobalid", "strFullName"]]
dfObserver2 = dfObserver2.groupby("parentglobalid").agg({"strFullName": ', '.join})


# In[14]:


### Join sedfMetadataYYYY with dfObserver
dfMetadataObserver = pd.merge(sedfMetadataYYYY,dfObserver2, how="left", left_on="globalid", right_on="parentglobalid")


# In[15]:


### Manipulate date/time fields in dfMetadataObserver
## Strip time from dtmDate_Pacific
dfMetadataObserver["dtmDate_Pacific"] = dfMetadataObserver["dtmDate_Pacific"].dt.strftime('%m/%d/%Y')

## Calculate total survey time
dfMetadataObserver["dtmManualTimeStart_dt"] = dfMetadataObserver["dtmDate_Pacific"] + " " + dfMetadataObserver["dtmManualTimeStart"]
dfMetadataObserver["dtmManualTimeStart_dt"] = pd.to_datetime(dfMetadataObserver["dtmManualTimeStart_dt"],format="%m/%d/%Y %H:%M")

dfMetadataObserver["dtmManualTimeEnd_dt"] = dfMetadataObserver["dtmDate_Pacific"] + " " + dfMetadataObserver["dtmManualTimeEnd"]
dfMetadataObserver["dtmManualTimeEnd_dt"] = pd.to_datetime(dfMetadataObserver["dtmManualTimeEnd_dt"],format="%m/%d/%Y %H:%M")

dfMetadataObserver["dtmManualTimeTotal"] = dfMetadataObserver["dtmManualTimeEnd_dt"] - dfMetadataObserver["dtmManualTimeStart_dt"]

dfMetadataObserver["dtmManualTimeTotal"] = (dfMetadataObserver["dtmManualTimeTotal"]).astype(str)


# In[16]:


### Reset dfMetadataObserver in desired order and drop unneeded fields
dfMetadataObserver = dfMetadataObserver[["globalid", "strStream", "dtmDate_Pacific", "strFullName", "strTideStart", "strWeather", "dtmManualTimeStart", "dtmManualTimeTurn", "dtmManualTimeEnd", "dtmManualTimeTotal", "strStreamFlow", "strViewingConditions", "strViewingConditionsComments", "ysnLiveFish", "ysnCarcasses", "strComments", "CreationDate_Pacific"]]


# In[17]:


### Join dfMetadataObserver with sedfLiveFishLocation
dfMetadataObserverLiveFish = pd.merge(dfMetadataObserver,sedfLiveFishLocation, how="inner", left_on="globalid", right_on="parentglobalid")

## Reset dfMetadataObserverLiveFish in desired order and drop unneeded fields
dfMetadataObserverLiveFish = dfMetadataObserverLiveFish[['globalid_x', 'strStream', 'dtmDate_Pacific', 'ysnLiveFish', 'globalid_y', 'strLiveSpecies', 'strLiveSex', 'ysnPairs', 'ysnReddBuilding', 'intNumRedds', 'strLiveFishRedd', 'strReddID', 'SHAPE', 'CreationDate_Pacific_x']]
## Define dfMetadataObserverLiveFish sort order
dfMetadataObserverLiveFish = dfMetadataObserverLiveFish.sort_values(by=["strStream", "dtmDate_Pacific"])


# In[18]:


### Join dfMetadataObserver with sedfCarcassLocation
dfMetadataObserverCarcasses = pd.merge(dfMetadataObserver,sedfCarcassLocation, how="inner", left_on="globalid", right_on="parentglobalid")
## Reset dfMetadataObserverCarcasses in desired order and drop unneeded fields
dfMetadataObserverCarcasses = dfMetadataObserverCarcasses[['globalid_x', 'strStream', 'dtmDate_Pacific', 'ysnCarcasses', 'globalid_y', 'strCarcassSpecies', 'strCarcassSex', 'strDecomposedFresh', 'intNumCarcasses', 'ysnCountedLast', 'SHAPE', 'CreationDate_Pacific_x']]
## Define dfMetadataObserverCarcasses sort order
dfMetadataObserverCarcasses = dfMetadataObserverCarcasses.sort_values(by=["strStream", "dtmDate_Pacific"])


# In[19]:


### Live fish data entered prior to 11/5/2021 are in different format so before/after data frames needed
dfMetadataObserverLiveFish_before20211105 = dfMetadataObserverLiveFish[(dfMetadataObserverLiveFish['CreationDate_Pacific_x'] < "11/05/2021")]
dfMetadataObserverLiveFish_after20211105 = dfMetadataObserverLiveFish[(dfMetadataObserverLiveFish['CreationDate_Pacific_x'] >= "11/05/2021")]

dfMetadataObserverLiveFish_before20211105 = dfMetadataObserverLiveFish_before20211105.copy()
dfMetadataObserverLiveFish_after20211105 = dfMetadataObserverLiveFish_after20211105.copy()


# In[20]:


### Create fields for counting live fish entered before 11/5/2021
dfMetadataObserverLiveFish_before20211105.loc[dfMetadataObserverLiveFish_before20211105['ysnReddBuilding'] == "yes", ['intReddBuilding']] = 1
dfMetadataObserverLiveFish_before20211105.loc[dfMetadataObserverLiveFish_before20211105['ysnPairs'] == "yes", ['dblPairs']] = 0.5
dfMetadataObserverLiveFish_before20211105.loc[dfMetadataObserverLiveFish_before20211105['strLiveSex'] == "M", ['intMales']] = 1
dfMetadataObserverLiveFish_before20211105.loc[dfMetadataObserverLiveFish_before20211105['strLiveSex'] == "F", ['intFemales']] = 1
dfMetadataObserverLiveFish_before20211105.loc[dfMetadataObserverLiveFish_before20211105['strLiveSex'] == "Unk", ['intUnknown']] = 1

## Group by GUID, stream, date, and species; sum the numeric fields
dfLiveFishSummary1 = dfMetadataObserverLiveFish_before20211105.groupby(['globalid_x', 'strLiveSpecies'], as_index=False).sum()

## Create field for sum of live fish
dfLiveFishSummary1['intLiveFish'] = dfLiveFishSummary1[['intMales', 'intFemales', 'intUnknown']].sum(axis=1)


# In[21]:


### Create fields for counting live fish entered after 11/5/2021
dfMetadataObserverLiveFish_after20211105.loc[dfMetadataObserverLiveFish_after20211105['ysnReddBuilding'] == "yes", ['intReddBuilding']] = 1
dfMetadataObserverLiveFish_after20211105.loc[dfMetadataObserverLiveFish_after20211105['ysnPairs'] == "yes", ['dblPairs']] = 1
dfMetadataObserverLiveFish_after20211105.loc[dfMetadataObserverLiveFish_after20211105['ysnPairs'] == "yes", ['intMales']] = 1
dfMetadataObserverLiveFish_after20211105.loc[dfMetadataObserverLiveFish_after20211105['ysnPairs'] == "yes", ['intFemales']] = 1
dfMetadataObserverLiveFish_after20211105.loc[dfMetadataObserverLiveFish_after20211105['strLiveSex'] == "M", ['intMales']] = 1
dfMetadataObserverLiveFish_after20211105.loc[dfMetadataObserverLiveFish_after20211105['strLiveSex'] == "F", ['intFemales']] = 1
dfMetadataObserverLiveFish_after20211105.loc[dfMetadataObserverLiveFish_after20211105['strLiveSex'] == "Unk", ['intUnknown']] = 1
dfMetadataObserverLiveFish_after20211105.loc[((dfMetadataObserverLiveFish_after20211105['strLiveFishRedd'] == "Live Fish and Redd") | (dfMetadataObserverLiveFish_after20211105['strLiveFishRedd'] == "Redd")), ['intNumRedds']] = 1

## Group by GUID, stream, date, and species; sum the numeric fields
dfLiveFishSummary2 = dfMetadataObserverLiveFish_after20211105.groupby(['globalid_x', 'strLiveSpecies'], as_index=False).sum()

## Create field for sum of live fish
dfLiveFishSummary2['intLiveFish'] = dfLiveFishSummary2[['intMales', 'intFemales', 'intUnknown']].sum(axis=1)


# In[22]:


### Combine live fish data from before and after 11/5/2021
dfLiveFishSummary = pd.concat([dfLiveFishSummary1, dfLiveFishSummary2])


# In[23]:


### Testing live fish summary
dfLiveFishSummary_test1 = dfMetadataObserverLiveFish_before20211105.groupby(['globalid_x', 'strStream', 'dtmDate_Pacific', 'strLiveSpecies']).sum()
dfLiveFishSummary_test1['intLiveFish'] = dfLiveFishSummary_test1[['intMales', 'intFemales', 'intUnknown']].sum(axis=1)
dfLiveFishSummary_test2 = dfMetadataObserverLiveFish_after20211105.groupby(['globalid_x', 'strStream', 'dtmDate_Pacific','strLiveSpecies']).sum()
dfLiveFishSummary_test2['intLiveFish'] = dfLiveFishSummary_test2[['intMales', 'intFemales', 'intUnknown']].sum(axis=1)
dfLiveFishSummary_test = pd.concat([dfLiveFishSummary_test1, dfLiveFishSummary_test2])
dfLiveFishSummary_test = dfLiveFishSummary_test[['intLiveFish', 'intMales', 'intFemales', 'intUnknown', 'dblPairs', 'intReddBuilding', 'intNumRedds']]
dfLiveFishSummary_test = dfLiveFishSummary_test.sort_values(by=["strStream", "dtmDate_Pacific"])
dfLiveFishSummary_test

arcpy.AddMessage("Completed live fish summary...")


# In[ ]:


### Create fields for counting carcasses
## Assume that null ysnCountedLast is 'yes' if strDecomposedFresh is 'Decomposed'
## Assume that null ysnCountedLast is 'no' if strDecomposedFresh is 'Fresh'
# yes OR null and decomposed
dfMetadataObserverCarcasses.loc[dfMetadataObserverCarcasses['ysnCountedLast'] == "yes", ['intCountedLast']] = dfMetadataObserverCarcasses['intNumCarcasses']
dfMetadataObserverCarcasses.loc[(dfMetadataObserverCarcasses['ysnCountedLast'].isna()) & (dfMetadataObserverCarcasses['strDecomposedFresh'] == "Decomposed"), ['intCountedLast']] = dfMetadataObserverCarcasses['intNumCarcasses']

# no OR null and fresh
dfMetadataObserverCarcasses.loc[(dfMetadataObserverCarcasses['strCarcassSex'] == "M") & ((dfMetadataObserverCarcasses['ysnCountedLast'] == "no") |  ((dfMetadataObserverCarcasses['ysnCountedLast'].isna()) &  (dfMetadataObserverCarcasses['strDecomposedFresh'] == "Fresh"))) , ['intNewMales']] = dfMetadataObserverCarcasses['intNumCarcasses']
dfMetadataObserverCarcasses.loc[(dfMetadataObserverCarcasses['strCarcassSex'] == "F") & ((dfMetadataObserverCarcasses['ysnCountedLast'] == "no") |  ((dfMetadataObserverCarcasses['ysnCountedLast'].isna()) &  (dfMetadataObserverCarcasses['strDecomposedFresh'] == "Fresh"))) , ['intNewFemales']] = dfMetadataObserverCarcasses['intNumCarcasses']
dfMetadataObserverCarcasses.loc[(dfMetadataObserverCarcasses['strCarcassSex'] == "J") & ((dfMetadataObserverCarcasses['ysnCountedLast'] == "no") |  ((dfMetadataObserverCarcasses['ysnCountedLast'].isna()) &  (dfMetadataObserverCarcasses['strDecomposedFresh'] == "Fresh"))) , ['intNewJuveniles']] = dfMetadataObserverCarcasses['intNumCarcasses']
dfMetadataObserverCarcasses.loc[(dfMetadataObserverCarcasses['strCarcassSex'] == "Unk") & ((dfMetadataObserverCarcasses['ysnCountedLast'] == "no") |  ((dfMetadataObserverCarcasses['ysnCountedLast'].isna()) &  (dfMetadataObserverCarcasses['strDecomposedFresh'] == "Fresh"))) , ['intNewUnknown']] = dfMetadataObserverCarcasses['intNumCarcasses']

## Group by GUID, stream, date, and species; sum the numeric fields; add field for new carcasses
dfCarcassSummary = dfMetadataObserverCarcasses.groupby(by=['globalid_x', 'strCarcassSpecies'],  axis=0, level=None, as_index=False).sum()
dfCarcassSummary['intNewNumCarcasses'] = dfCarcassSummary['intNumCarcasses'] - dfCarcassSummary['intCountedLast']


# In[ ]:


### Testing carcasses summary
dfCarcassSummary_test = dfMetadataObserverCarcasses.groupby(by=['globalid_x', 'strStream', 'dtmDate_Pacific', 'strCarcassSpecies'],  axis=0, level=None).sum()
dfCarcassSummary_test['intNewNumCarcasses'] = dfCarcassSummary_test['intNumCarcasses'] - dfCarcassSummary_test['intCountedLast']
dfCarcassSummary_test = dfCarcassSummary_test.sort_values(by=["strStream", "dtmDate_Pacific"])
dfCarcassSummary_test

arcpy.AddMessage("Completed carcass summary...")


# In[ ]:


### Copy dfMetadataObserver as start of summary data frames
dfSummary = dfMetadataObserver.copy()
# Calculate zeroes
dfSummary.loc[dfSummary['ysnLiveFish'] == "no", ['intLiveFish']] = 0
dfSummary.loc[dfSummary['ysnCarcasses'] == "no", ['intCarcasses']] = 0
# Join
dfLiveFishSummary = pd.merge(dfSummary,dfLiveFishSummary, how="left", left_on="globalid", right_on="globalid_x")
dfCarcassSummary = pd.merge(dfSummary,dfCarcassSummary, how="left", left_on="globalid", right_on="globalid_x")


# In[ ]:


### Cleanup dfLiveFishSummary
dfLiveFishSummary.loc[(dfLiveFishSummary["intLiveFish_x"].isna()), 'intLiveFish_x'] = 0
dfLiveFishSummary.loc[(dfLiveFishSummary["intLiveFish_y"].isna()), 'intLiveFish_y'] = 0
dfLiveFishSummary["intLiveFish"] = dfLiveFishSummary["intLiveFish_x"] + dfLiveFishSummary["intLiveFish_y"]
dfLiveFishSummary = dfLiveFishSummary[['globalid', 'strStream', 'dtmDate_Pacific', 'strFullName', 'strTideStart', 'strWeather', 'dtmManualTimeStart', 'dtmManualTimeTurn', 'dtmManualTimeEnd', 'dtmManualTimeTotal', 'strStreamFlow', 'strViewingConditions', 'strViewingConditionsComments', 'ysnLiveFish', 'strLiveSpecies', 'intLiveFish', 'intMales', 'intFemales', 'intUnknown', 'intReddBuilding', 'dblPairs', 'intNumRedds', 'strComments']]
dfLiveFishSummary = dfLiveFishSummary.sort_values(by=["strStream", "dtmDate_Pacific"])


# In[ ]:


### Cleanup dfCarcassSummary
dfCarcassSummary.loc[(dfCarcassSummary["intCarcasses"].isna()), 'intCarcasses'] = 0
dfCarcassSummary.loc[(dfCarcassSummary["intNumCarcasses"].isna()), 'intNumCarcasses'] = 0
dfCarcassSummary["intTotalCarcasses"] = dfCarcassSummary["intCarcasses"] + dfCarcassSummary["intNumCarcasses"]
dfCarcassSummary = dfCarcassSummary[['globalid', 'strStream', 'dtmDate_Pacific', 'strFullName', 'strTideStart', 'strWeather', 'dtmManualTimeStart', 'dtmManualTimeTurn', 'dtmManualTimeEnd', 'dtmManualTimeTotal', 'strStreamFlow', 'strViewingConditions', 'strViewingConditionsComments', 'ysnCarcasses', 'strCarcassSpecies', 'intTotalCarcasses', 'intCountedLast', 'intNewNumCarcasses', 'intNewMales', 'intNewFemales', 'intNewJuveniles', 'intNewUnknown', 'strComments']]
dfCarcassSummary = dfCarcassSummary.sort_values(by=["strStream", "dtmDate_Pacific"])


# In[ ]:


### Export data frames
## Use archive_dt_field function to convert Python date time into format Excel can read more easily
archive_dt_field(dfMetadataObserver)
archive_dt_field(dfMetadataObserverLiveFish)
archive_dt_field(dfMetadataObserverCarcasses)
archive_dt_field(dfLiveFishSummary)
archive_dt_field(dfCarcassSummary)
    
## Create export paths for backup and writes to Excel spreadsheet
writer = pd.ExcelWriter(os.path.join(out_workspace,('WLP_Salmon_Spawning_Survey_' + year + '_' + timestamp + '.xlsx')))
dfMetadataObserver.to_excel(writer, 'Metadata', index=False)
dfMetadataObserverLiveFish.to_excel(writer, 'Live Fish', index=False)
dfMetadataObserverCarcasses.to_excel(writer, 'Carcasses', index=False)
dfLiveFishSummary.to_excel(writer, 'Live Fish Summary', index=False)
dfCarcassSummary.to_excel(writer, 'Carcass Summary', index=False)
writer.save()

arcpy.AddMessage("Summary data exported to Excel spreadsheet.")

