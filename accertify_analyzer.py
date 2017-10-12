import pandas
import numpy
import csv
import sys
import math

fullsignalspath = sys.argv[1][:len(sys.argv[1])-4]+'_full_signals_report.csv'
solutionpath = sys.argv[1][:len(sys.argv[1])-4]+'_solution.csv'

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

#################################################################################################
# INITIAL CLEANUP OF DATA
#add in bucketing columns for numeric fields
try:
	df['Confidence Score Big Bucket'] = pandas.cut(df['Confidence Score'], bins=[-1,199,399,501], labels=['0-199','200-399','400-500'])
	df['Confidence Score Big Bucket'] = pandas.cut(df['Confidence Score'], bins=[-1,99,449,501], labels=['0-99','200-449','450-500'])
	df['Confidence Score Big Bucket'] = pandas.cut(df['Confidence Score'], bins=[-1,49,474,501], labels=['0-49','200-474','475-500'])
except:
	print 'Warning: "Confidence Score" header not found in file'
	pass

try:
	df['Email First Seen Bucket 1'] = pandas.cut(df['Email First Seen Days'], bins=[-1,1,365,1824,99999], labels=['Never','< 1 year','1-4 years','5+ years'])
	df['Email First Seen Bucket 2'] = pandas.cut(df['Email First Seen Days'], bins=[-1,365,1824,99999], labels=['< 1 year','1-4 years','5+ years'])
except:
	print 'Warning: "Email First Seen Days" header not found in file'
	pass

try:
	df['IP to Address Bucket'] = pandas.cut(df['IP Distance From Address'], bins=[0,9,99,999,99999], labels=['<10 miles','10-99 miles','100-999 miles','1000+ miles'])
except:
	print 'Warning: "IP Distance From Address" header not found in file'
	pass
	
try:
	df['IP to Phone Bucket'] = pandas.cut(df['IP Distance From Phone'], bins=[0,9,99,999,99999], labels=['<10 miles','10-99 miles','100-999 miles','1000+ miles'])
except:
	print 'Warning: "IP Distance From Phone" header not found in file'
	pass

print ''
####################################################################################################
# GET USER INPUT TO FIGURE OUT GOOD/BAD, WHAT THE INITIAL DECISION WAS AND WHAT IS THE FINAL OUTCOME
headers = df.keys().tolist()
#we're going to ask the user for which column contains the score, the outcome, etc., and we don't 
#want to inundate them with all the wpp fields they won't need to look at
nonWPPHeaders = headers[0:headers.index('Error')]


#Map Resolution Statuses to 1/0 "Is Bad" and 1/0 "Is Good"
resolutionHeader = None
resolutionSet = []
resolutionMapping = []
print 'Which column contains the order outcomes? (it\'s okay if chargebacks are in a separate column)'
for x in range(0,len(nonWPPHeaders)):
	print str(x)+': '+nonWPPHeaders[x]
i = raw_input('choose 0-'+str(len(nonWPPHeaders))+'>')
resolutionHeader = nonWPPHeaders[int(i)]
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
			resolutionMapping.append(dict([(resolutionHeader,x),('Fraud',1)]))
		elif foo == '0':
			resolutionMapping.append(dict([(resolutionHeader,x),('Fraud',0)]))
			
resDF = pandas.DataFrame.from_dict(resolutionMapping)
df = pandas.merge(df, resDF, on=resolutionHeader)

#find Chargeback data
print ''
print 'Which column contains chargeback data?'
cbHeader = None
resolutionSet = []
cbMapping = []
for x in range(0,len(nonWPPHeaders)):
	print str(x)+': '+nonWPPHeaders[x]
i = raw_input('choose 0-'+str(len(nonWPPHeaders))+'>')
cbHeader = nonWPPHeaders[int(i)]
cbSet = df.get(cbHeader).unique()

fraudStatuses = []	
print ''
print 'Which of these values indicates a chargeback? (note, "nan" means blank value)'

for x in cbSet:
	print x
	
	foo = None
	while foo != '0' and foo != '1':
		foo = raw_input('enter 0 if this indicates not a chargeback, 1 if it is a chargeback>')
		if foo == '1':
			cbMapping.append(dict([(cbHeader,x),('Is CB',1)]))
		elif foo == '0':
			cbMapping.append(dict([(cbHeader,x),('Is CB',0)]))
			
cbDF = pandas.DataFrame.from_dict(cbMapping)
df = pandas.merge(df, cbDF, on=cbHeader)

#finalize is-bad (cb fraud may not be included in resolution statuses), and define is-good
df['Fraud'] = numpy.maximum(df['Fraud'],df['Is CB'])
df['NonFraud'] = abs(-1+df['Fraud'])

#find the accertify score
print ''
print 'Which column contains the Accertify score?'
for x in range(0,len(nonWPPHeaders)):
	print str(x)+': '+nonWPPHeaders[x]
i = raw_input('choose 0-'+str(len(nonWPPHeaders))+'>')
accertifyScoreHeader = nonWPPHeaders[int(i)]


#find the dollar amounts
amtHeader = None
print ''
print 'Which column contains the dollar amounts?'
for x in range(0,len(nonWPPHeaders)):
	print str(x)+': '+nonWPPHeaders[x]
i = raw_input('choose 0-'+str(len(nonWPPHeaders))+'>')
amtHeader = nonWPPHeaders[int(i)]

#figure out reviews
print ''
print 'At what threshold are orders reviewed? (enter nothing if there is no review threshold)'
while(True):
	try:
		reviewThreshold = raw_input('>')
		if reviewThreshold == '':
			reviewThreshold = None
			break
		reviewThreshold = int(reviewThreshold)
		break
	except:
		print '...please try that again'

df['Reviewed'] = df[accertifyScoreHeader]>=reviewThreshold			
print ''

#figure out review cost
print ''
reviewCost = 3
print 'What is the cost of review (enter a number, e.g. 2.5 if review cost is $2.50)'
while(True):
	try:
		reviewCost = raw_input('>')
		if reviewCost == '':
			reviewCost = None
			break
		reviewCost = float(reviewCost)
		break
	except:
		print '...please try that again'

#################################################################################################
# PRINT OUT FILE BREAKDOWN
#Calculate total orders, total good and total bad
print 'Calculating total reviews, total good and bad orders...'
df['Is Reviewed'] = df[accertifyScoreHeader] >= reviewThreshold
totalRecords = len(df.index)
df['Is Bad'] = df['Fraud'] + df['Is CB']
totalBads = df['Is Bad'].sum()
totalGoods = df['NonFraud'].sum()

print ''
print 'Current review rate looks to be '+str(math.floor(10000.0*df['Is Reviewed'].sum()/float(totalRecords))/100.0)+'%. What is the max review rate we should tolerate?\n (e.g. enter 0.125 for 12.5%, or enter nothing if you don\'t want to set any limit)'
maxReviews = None
maxReviewRate = None
while(True):
	try:
		maxReviewRate = raw_input('>')
		if maxReviewRate == '':
			maxReviewRate = None
			break
		maxReviewRate = float(maxReviewRate)
		break
	except:
		print '...please try that again'
if maxReviewRate is not None:
	maxReviews = math.floor(float(totalRecords)*maxReviewRate)

print ''
print 'Current chargeback rate looks to be '+str(math.floor(100000.0*float(numpy.multiply(df['Is CB'],df[amtHeader]).sum())/float(df[amtHeader].sum()))/1000.0)+'%. What is the max CB rate we should tolerate?\n (e.g. enter 0.0050 for 0.50%, or enter nothing if you don\'t want to set any limit)'
maxCBDollars = None
maxCBRate = None
while(True):
	try:
		maxCBRate = raw_input('>')
		if maxCBRate == '':
			maxCBRate = None
			break
		maxCBRate = float(maxCBRate)
		break
	except:
		print '...please try that again'
if maxCBRate is not None:
	maxCBDollars = math.floor(float(df[amtHeader].sum())*maxCBRate)
	
print ''
print 'max Reviews = '+str(maxReviews)
print 'max CB dollars = '+str(maxCBDollars)
print ''
	
print 'Working...'
	
#################################################################################################
# STARTING SIGNAL ANALYSIS WORK HERE
fullCols = df.columns.tolist()
idcCols = fullCols[fullCols.index('Error'):fullCols.index('Fraud')]

#at the end of this, we don't want to pitch rules for redundant data elements. If two data elements
#have too much overlap, then we'll just choose whichever one of them has higher IV. To start with,
#we'll calculate the similarity of each data element against each other data element.

allKeyValuePairs = []
for field in idcCols:
	uniques = df.get(field).unique()
	#if more than 10 unique values, skip it
	if len(uniques) > 10:
		continue
	for u in uniques:
		allKeyValuePairs.append(field+'|'+str(u))
	

#calculate coverage, fraud likelihood, and WoE for all fields

print 'Calculating fraud chance, WoE, etc. for all signals'

FeatureMatrix = numpy.ones((totalRecords,1))
FeatureData = numpy.zeros((1,9))#this initial zero row will be deleted later

for kvi in range(0,len(allKeyValuePairs)):
	print 'evaluating '+str(allKeyValuePairs[kvi])
	kv = allKeyValuePairs[kvi].split('|')

	field = kv[0]
	value = kv[1]
		
	try:
		foo = numpy.matrix((df[field].astype(str) == str(value)).values).transpose()
	except:
		print 'error looking at field "'+str(field)+'" value "'+str(value)+'"'
		continue
		
	FeatureMatrix = numpy.hstack((FeatureMatrix, foo))
	
	#df2 is temporary dataframe containing only rows that match this feature
	df2 = df.loc[df[field].astype(str) == str(value)]
		
	NewFeatureDataRow = []
	NewFeatureDataRow.append(field)#0, field
	NewFeatureDataRow.append(value)#1, value
	NewFeatureDataRow.append(len(df2.index)/float(totalRecords))#2, % of records
	NewFeatureDataRow.append(df2['Is Bad'].sum()/float(len(df2.index)))#3, pct bad
	NewFeatureDataRow.append(max(0.0001,df2['Is Bad'].sum())/float(totalBads))#4, pct of bads
	NewFeatureDataRow.append(max(0.0001,df2['NonFraud'].sum())/float(totalGoods))#5, pct of goods
	NewFeatureDataRow.append(numpy.log(NewFeatureDataRow[4]/float(NewFeatureDataRow[5])))#6, WoE
	NewFeatureDataRow.append(numpy.maximum(0.001,(NewFeatureDataRow[4]-NewFeatureDataRow[5])*NewFeatureDataRow[6]).astype(float))#7, IV
	NewFeatureDataRow.append(kvi)#8, original feature ID
	
	FeatureData = numpy.vstack((FeatureData,NewFeatureDataRow))

#delete original first row, which was just a placeholder
FeatureData = numpy.delete(FeatureData, (0), axis=0)
#sort the whole thing by IV descending (IV is column #7)
FeatureData[FeatureData[:,7].argsort()][::-1]

#up next is to trim out features that are redundant with other features. We will remove any feature X where there exists another
#feature Y such that:
#	- X's IV < Y's IV
#	- X's abs(WoE) < Y's abs(WoE)
#	- X's WoE and Y's WoE have the same sign
#	- ((# rows where both X and Y present) / min(# rows X is present, # rows Y is present)) >= 0.9

#at the same time, we'll look at creating combinations of features. If they are not redundant, and they each have the same WoE sign, then
#try combining them. If the IV of combined is greater than either's IV, then add this as a new combined feature
print ''
print 'Now looking for redundant signals. This may take a while. Do you want to limit to only looking at the top X signals?'
print 'If so, enter how many signals we should consider, or enter nothing to look at them all:'
signalsToConsider = None
while(True):
	try:
		signalsToConsider = raw_input('>')
		if signalsToConsider == '':
			signalsToConsider = None
			break
		signalsToConsider = int(signalsToConsider)
		break
	except:
		print '...please try that again'

if signalsToConsider is None:
	signalsToConsider = len(allKeyValuePairs)

print ''
redundant = []
newFeatures = []
pctDone = '0%'
for x in range (0,len(allKeyValuePairs)):
	pctDone1 = str(math.floor((x/float(len(allKeyValuePairs)))*20)*5)+'%'
	if pctDone1 != pctDone:
		pctDone = pctDone1
		print pctDone+' done'
	#initialize as not redundant
	redundant.append([0])
	#skip if done
	if x > signalsToConsider:
		continue
	for y in range(0, x-1):
		both = numpy.count_nonzero(numpy.multiply(FeatureMatrix[:,x],FeatureMatrix[:,y]))
		xCount = numpy.count_nonzero(FeatureMatrix[:,x] == 1)
		yCount = numpy.count_nonzero(FeatureMatrix[:,y] == 1)
		if (both/float(min(xCount,yCount))) >= 0.9 and abs(eval(FeatureData[x][6])) <= abs(eval(FeatureData[y][6])) and eval(FeatureData[x][7]) <= eval(FeatureData[y][7]) and (eval(FeatureData[x][6]) * eval(FeatureData[y][6])) > 0:
			#print str(FeatureData[x][0])+', '+str(FeatureData[x][1])+' found to be redundant with '+str(FeatureData[y][0])+', '+str(FeatureData[y][1])
			redundant[x] = [1]
			break
				
FeatureData = numpy.hstack((FeatureData,redundant))

#build dataframe around this
FeatureDF = pandas.DataFrame(data=FeatureData).sort_values(by=[9,7],ascending=[True,False])
print ''
FeatureDF.to_csv(fullsignalspath, index=False, header=['Field','Value','% of Orders','% Bad','% of Bads','% of Goods','WoE','IV','OG ID','Is Redundant'])
print 'Full signals report written to: '+fullsignalspath	
print ''

FeatureDF.columns = ['Field','Value','% of Orders','% Bad','% of Bads','% of Goods','WoE','IV','OG ID','Is Redundant']

##################################################################################################
# STARTING RULE ANALYSIS WORK HERE

#	Error		How far away each transaction is from its ideal score, weighted by the $ impact (m-by-1):
#				 (CFraud+MFraud).*RevDist.*Amt + Goods.*AccDist*revCost
# 				 Values here will be negative if score should be higher, or positive if score should be lower
#	alpha		Some very small number we'll use to adjust score weights
#	WeightD		Weight delta, how much we should adjust the weights based on the error we found
#				 ((-1*Error*alpha)' * Feats)' yields n-by-1
#				We never want to modify og score, so need to set WeightD[0]=0
#
# At the end of all this, we update weights using Weights = Weights + WeightD

#m is the number of txns
m = totalRecords
#n is the number of features
n = 10

NonFraud = numpy.matrix(df['NonFraud'].as_matrix()).transpose()
#CFraud is a m-by-1 boolean matrix of whether an order is caught fraud
NonCBFraud = numpy.matrix((df['Fraud'] & ~df['Is CB']).as_matrix()).transpose()
#MFraud is a m-by-1 boolean matrix of whether an order is missed fraud
CBFraud = numpy.matrix(df['Is CB'].as_matrix()).transpose()
#Amt is a m-by-1 matrix of dollar amounts
Amt = numpy.matrix(df[amtHeader].as_matrix()).transpose()
#Score0 is a m-by-1 matrix of current Accertify score
Score0 = numpy.matrix(df[accertifyScoreHeader].as_matrix()).transpose()

#Feats will be an m-by-(n+1) boolean matrix of whether each feature is present in each order,
#plus an initial column containing the current score
Feats = numpy.ones((totalRecords,1))
Feats[:,0] = df[accertifyScoreHeader].values
for f in FeatureDF[0:10].as_matrix():
	field = f[0]
	value = f[1]
	foo = numpy.matrix((df[field].astype(str) == str(value)).values).transpose()
	Feats = numpy.hstack((Feats, foo))
	
pandas.DataFrame(data=Feats).to_csv('feature_matrix.csv')

#Weights is an (n+1)-by-1 matrix of the weight for each feature, plus an initial 1
#since we always want to include the current score (Weights will be ultimately multipled by Feats)
Weights = numpy.zeros((n+1,1))
Weights[0][0] = 1


#Rev0 is an m-by-1 boolean matrix of whether the order was originally reviewed
Rev0 = Score0 >= reviewThreshold

#alpha is a very small number used to control weight updates
alpha = 0.01

##################################################################
#setup complete, following should be calculated for each iteration

#for each feature
Rev1 = Rev0.copy()
CBFraud1 = CBFraud.copy()
NonCBFraud1 = NonCBFraud.copy()

CBDollars1 = numpy.multiply(CBFraud1,Amt).sum()

Score1 = Score0.copy()

for f in range(0,n):
	print ''
	#if negative signal
	if float(FeatureDF.iloc[f].get('WoE')) > 0:
		print 'Negative signal: '+str(FeatureDF.iloc[f]['Field'])+', '+str(FeatureDF.iloc[f]['Value'])
		
		PosWeights = [25,50,75,100,125,150,175,200,250,300,350,400,450,500,600,700,800,900,1000,1200,1400,1600,1800,2000,3000,4000,5000,6000,8000,10000]

		bestWeight = 0
		bestImpact = 0
		
		for p in PosWeights:
			Weights[f+1][0] = p
			
			#Score2 is an m-by-1 matrix containing the new score, after our data is applied
			Score2 = numpy.dot(Feats,Weights)
			#Rev2 is an m-by-1 boolean matrix of whether the order is now reviwed after our data is applied
			Rev2 = Score2 >= reviewThreshold
			#ToRev is m-by-1 boolean array indicating whether order was moved to review
			ToRev = ~Rev1 & Rev2

			#Impact is an assessment of how much $ we are saving or costing with our solution
			#first part is chargeback savings, dollar amounts of missed fraud we move into review
			Impact = numpy.multiply(numpy.multiply(ToRev,CBFraud1),Amt)
			#second part is cost of extra reviews
			Impact = Impact - ToRev*reviewCost
			totalImpact = Impact.sum()
			
			if totalImpact > bestImpact and (maxReviews is None or maxReviews >= Rev2.sum()):					
				bestWeight = p
				bestImpact = totalImpact
		
		print 'Best weight we found is '+str(bestWeight)+' for '+str(FeatureDF.iloc[f]['Field'])
		print '$ impact for this rule is: '+str(bestImpact)
			
	else:
		print 'Positive signal: '+str(FeatureDF.iloc[f]['Field'])+', '+str(FeatureDF.iloc[f]['Value'])
		
		NegWeights = [-25,-50,-75,-100,-125,-150,-175,-200,-250,-300,-350,-400,-450,-500,-600,-700,-800,-900,-1000,-1200,-1400,-1600,-1800,-2000,-3000,-4000,-5000,-6000,-8000,-10000]
		
		bestWeight = 0
		bestImpact = 0
		
		for p in NegWeights:
			Weights[f+1][0] = p
			
			#Score2 is an m-by-1 matrix containing the new score, after our data is applied
			Score2 = numpy.dot(Feats,Weights)
			#Rev1 is an m-by-1 boolean matrix of whether the order is now reviwed after our data is applied
			Rev2 = Score2 >= reviewThreshold
			#ToAcc is m-by-1 boolean array indicating whether order was moved to accept
			ToAcc = ~Rev2 & Rev1
		
			#Impact is an assessment of how much $ we are saving or costing with our solution
			#first part is cost of fraud we move into accept
			Impact = numpy.multiply(numpy.multiply(ToAcc,NonCBFraud1),-1*Amt)
			#second part is savings of orders we move out of review
			Impact = Impact + ToAcc*reviewCost
			totalImpact = Impact.sum()
			if totalImpact > bestImpact and (maxCBDollars is None or maxCBDollars >= (CBDollars1+numpy.multiply(numpy.multiply(ToAcc,NonCBFraud1),Amt)).sum()):
				bestWeight = p
				bestImpact = totalImpact
		
		print 'Best weight we found is '+str(bestWeight)+' for '+str(FeatureDF.iloc[f]['Field'])
		print '$ impact for this rule is: '+str(bestImpact)
	
	#Now we're going to apply that weight and recalculate the state of things.
	#CBFraud we move to review should now be counted as NonCBFraud
	#NonCBFraud we move into accept should now be counted as CBFraud
	
	Weights[f+1][0] = bestWeight
	Rev1 = Score1 >= reviewThreshold
	Score2 = numpy.dot(Feats,Weights)
	Rev2 = Score2 >= reviewThreshold
	
	ToAcc = Rev1 & ~Rev2
	ToRev = ~Rev1 & Rev2
	CBFraud2 = (CBFraud1 & ~numpy.multiply(CBFraud1,ToRev)) | numpy.multiply(NonCBFraud1,ToAcc)
	NonCBFraud2 = (NonCBFraud1 & ~numpy.multiply(NonCBFraud1,ToAcc)) | numpy.multiply(CBFraud1,ToRev)
	
	Rev1 = Rev2.copy()
	CBFraud1 = CBFraud2.copy()
	NonCBFraud1 = NonCBFraud2.copy()
	Score1 = Score2.copy()
	
#now we're all done, we'll print weights and stuff

Score1 = numpy.dot(Feats,Weights)
Rev1 = Score1 >= reviewThreshold
ToAcc = Rev0 & ~Rev1
ToRev = ~Rev0 & Rev1

#first part is chargeback savings, dollar amounts of missed fraud we move into review
Impact = numpy.multiply(numpy.multiply(ToRev,CBFraud),Amt)
#second part is cost of extra reviews
Impact = Impact - numpy.multiply(ToRev,reviewCost)
#third part is cost of fraud we move into accept
Impact = Impact - numpy.multiply(numpy.multiply(ToAcc,NonCBFraud),Amt)
#fourth part is savings of orders we move out of review
Impact = Impact + numpy.multiply(ToAcc,reviewCost)
totalImpact = Impact.sum()

Solution = pandas.DataFrame(data={'Field':FeatureDF.iloc[0:10]['Field'],'Value':FeatureDF.iloc[0:10]['Value'],'Weight':Weights[1:,0]})
			
print 'Solution:'
print Solution
print ''
print 'Total Impact: $'+str(totalImpact)
print '  orders moved into review: '+str(ToRev.sum())+', costing $'+str((ToRev*reviewCost).sum())
print '  orders moved into accept: '+str(ToAcc.sum())+', saving $'+str((ToAcc*reviewCost).sum())
print '  Caught fraud moved into accept: '+str(numpy.multiply(ToAcc,NonCBFraud).sum())+', costing $'+str(numpy.multiply(numpy.multiply(ToAcc,NonCBFraud),Amt).sum())
print '  CBs moved into review: '+str(numpy.multiply(ToRev,CBFraud).sum())+', saving $'+str(numpy.multiply(numpy.multiply(ToRev,CBFraud),Amt).sum())

Solution.to_csv(solutionpath)
	
