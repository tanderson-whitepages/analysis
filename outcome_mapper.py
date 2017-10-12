import pandas
import numpy
import csv
import sys
import math

outpath = sys.argv[1][:len(sys.argv[1])-4]+'_mapped_outcomes.csv'
print 'Opening the file...'
print ''
if sys.argv[1][-3:] == 'csv':
  df = pandas.read_csv(sys.argv[1])
elif sys.argv[1][-4:] == 'xlsx':
  df = pandas.read_excel(sys.argv[1])
else:
  print 'Please enter either a csv or xlsx file'
  sys.exit(1)
  
print 'Done!'
print ''

####################################################################################################
# GET USER INPUT TO FIGURE OUT GOOD/BAD, WHAT THE INITIAL DECISION WAS AND WHAT IS THE FINAL OUTCOME
headers = df.keys().tolist()

#Map Resolution Statuses to 1/0 "Is Bad" and 1/0 "Is Good"
resolutionHeader = None
resolutionSet = []
resolutionMapping = []
print 'Which column contains the order outcomes? (it\'s okay if chargebacks are in a separate column)'
for x in range(0,len(headers)):
  print str(x)+': '+headers[x]
i = raw_input('choose 0-'+str(len(headers))+'>')
resolutionHeader = headers[int(i)]
resolutionSet = df.get(resolutionHeader).unique()

fraudStatuses = []  
print ''
print 'Which of these values indicate fraud? (note, "nan" means blank value)'

for x in resolutionSet:
  print x
  
  foo = None
  while foo != '0' and foo != '1':
    foo = raw_input('enter 0 if this is non-fraud, 1 if it is fraud>')
    if foo == '1':
      resolutionMapping.append(dict([(resolutionHeader,x),('NonFraud',0)]))
    elif foo == '0':
      resolutionMapping.append(dict([(resolutionHeader,x),('NonFraud',1)]))
      
resDF = pandas.DataFrame.from_dict(resolutionMapping)
df = pandas.merge(df, resDF, on=resolutionHeader)

#find Chargeback data
print ''
print 'Which column contains chargeback data?'
cbHeader = None
resolutionSet = []
cbMapping = []
for x in range(0,len(headers)):
  print str(x)+': '+headers[x]
i = raw_input('choose 0-'+str(len(headers))+'>')
cbHeader = headers[int(i)]
cbSet = df.get(cbHeader).unique()

fraudStatuses = []  
print ''
print 'Which of these values indicates a chargeback? (note, "nan" means blank value)'

#sometimes chargeback data is like an ID or a dollar amount or something where you don't want to walk through all possible values
anynonnull = False
if len(cbSet) > 50:
  print 'Looks like this column has a ton of values. Is it fair to say a chargeback is anything w/o a null value here?'
  print 'enter y/n'
  foo = raw_input('>')
  if foo in 'yYTt1':
    anynonnull = True

if anynonnull:
  print '...assuming any non-null value in '+str(cbHeader)+' indicates a chargeback.'
  df['MissedFraud'] = numpy.where(pandas.isnull(df[cbHeader]),0,1)
else:
  for x in cbSet:
    print x
    
    foo = None
    while foo != '0' and foo != '1':
      foo = raw_input('enter 0 if this indicates not a chargeback, 1 if it is a chargeback>')
      if foo == '1':
        cbMapping.append(dict([(cbHeader,x),('MissedFraud',1)]))
      elif foo == '0':
        cbMapping.append(dict([(cbHeader,x),('MissedFraud',0)]))
        
  cbDF = pandas.DataFrame.from_dict(cbMapping)
  df = pandas.merge(df, cbDF, on=cbHeader)

#finalize NonFraud (cb fraud may not be included in the original data this was based on)
df['NonFraud'] = df['NonFraud'] & ~df['MissedFraud']
df['CaughtFraud'] = numpy.where((df['NonFraud']==0) & (df['MissedFraud']==0),1,0)

df['Master_Outcome'] = numpy.where(df['NonFraud'],'Good','Bad')
df['OverallStatus'] = numpy.where(df['NonFraud'],'NonFraud',numpy.where(df['CaughtFraud'],'CaughtFraud','MissedFraud'))

df.to_csv(outpath,index=False)
print ''

print 'All done! A new file has been written containing extra columns with resolution mapping: '+str(outpath)