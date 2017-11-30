import pandas
import numpy
import csv
import sys
import math

signalspath = sys.argv[1][:len(sys.argv[1])-4]+'_signals_report.csv'
solutionpath = sys.argv[1][:len(sys.argv[1])-4]+'_solution.csv'
scoreColumnPath = sys.argv[1][:len(sys.argv[1])-4]+'_newScore.csv'

print('Opening the file...')
print('')
if sys.argv[1][-3:] == 'csv':
	df = pandas.read_csv(sys.argv[1])
elif sys.argv[1][-4:] == 'xlsx':
	df = pandas.read_excel(sys.argv[1])
else:
	print('Please enter either a csv or xlsx file')
	sys.exit(1)
	
print('Done!')
print('')

headers = df.keys().tolist()
nonWPPHeaders = headers[0:headers.index('Error')]+headers[headers.index('Confidence Score')+1:]

#################################################################################################
# INITIAL CLEANUP OF DATA
#add in bucketing columns for numeric fields

#this script expects outcomes to already have been mapped, through outcome_mapper.py
missing = []
requiredFields = ['OverallStatus']
for r in requiredFields:
	if r not in df.columns:
		missing.append(r)
if len(missing)>0:
	print('Your file is expected to contain the following columns (you may need to run through outcome_mapper.py first): '+str(missing))
	sys.exit(1)
	
#add new cols for caughtfraud, missedfraud, nonfraud if not there already
if 'NonFraud' not in df.columns:
	df['NonFraud'] = numpy.where(df['OverallStatus']=='NonFraud',1,0)
if 'CaughtFraud' not in df.columns:
	df['CaughtFraud'] = numpy.where(df['OverallStatus']=='CaughtFraud',1,0)
if 'MissedFraud' not in df.columns:
	df['MissedFraud'] = numpy.where(df['OverallStatus']=='MissedFraud',1,0)
	
try:
	df['Confidence Score Bucket 1'] = pandas.cut(df['Confidence Score'], bins=[-1,199,399,501], labels=['0-199','200-399','400-500'])
	df['Confidence Score Bucket 2'] = pandas.cut(df['Confidence Score'], bins=[-1,99,449,501], labels=['0-99','200-449','450-500'])
	df['Confidence Score Bucket 3'] = pandas.cut(df['Confidence Score'], bins=[-1,49,474,501], labels=['0-49','200-474','475-500'])
except:
	print('Warning: "Confidence Score" header not found in file')
	pass

try:
	df['Email First Seen Bucket 1'] = pandas.cut(df['Email First Seen Days'], bins=[-1,1,365,1824,99999], labels=['Never','< 1 year','1-4 years','5+ years'])
	df['Email First Seen Bucket 2'] = pandas.cut(df['Email First Seen Days'], bins=[-1,365,1824,99999], labels=['< 1 year','1-4 years','5+ years'])
except:
	print('Warning: "Email First Seen Days" header not found in file')
	pass

try:
	df['IP to Address Bucket'] = pandas.cut(df['IP Distance From Address'], bins=[0,9,99,999,99999], labels=['<10 miles','10-99 miles','100-999 miles','1000+ miles'])
except:
	print('Warning: "IP Distance From Address" header not found in file')
	pass
	
try:
	df['IP to Phone Bucket'] = pandas.cut(df['IP Distance From Phone'], bins=[0,9,99,999,99999], labels=['<10 miles','10-99 miles','100-999 miles','1000+ miles'])
except:
	print('Warning: "IP Distance From Phone" header not found in file')
	pass



#find the accertify score
print('')
print('Which column contains the Accertify score?')
for x in range(0,len(nonWPPHeaders)):
	print(str(x)+': '+nonWPPHeaders[x])
i = input('choose 0-'+str(len(nonWPPHeaders))+'>')
accertifyScoreHeader = nonWPPHeaders[int(i)]


#find the dollar amounts
amtHeader = None
print('')
print('Which column contains the dollar amounts?')
for x in range(0,len(nonWPPHeaders)):
	print(str(x)+': '+nonWPPHeaders[x])
i = input('choose 0-'+str(len(nonWPPHeaders))+'>')
amtHeader = nonWPPHeaders[int(i)]


#figure out rejects
print('')
rejectThreshold = None
print('At what threshold are orders rejected? (enter nothing if there is no auto-reject threshold)')
while(True):
	try:
		rejectThreshold = input('>')
		if rejectThreshold == '':
			rejectThreshold = None
			break
		rejectThreshold = int(rejectThreshold)
		break
	except:
		print('...please try that again')

if rejectThreshold is not None:
	df['Rejected'] = df[accertifyScoreHeader]>=rejectThreshold	
else:
	df['Rejected'] = False
print('')


#figure out reviews
print('')
reviewThreshold = None
print('At what threshold are orders reviewed? (enter nothing if there is no review threshold)')
while(True):
	try:
		reviewThreshold = input('>')
		if reviewThreshold == '':
			reviewThreshold = None
			break
		reviewThreshold = int(reviewThreshold)
		break
	except:
		print('...please try that again')

if reviewThreshold is not None:
	if rejectThreshold is not None:
		df['Reviewed'] = (df[accertifyScoreHeader]>=reviewThreshold) & (df[accertifyScoreHeader]<rejectThreshold)
	else:
		df['Reviewed'] = df[accertifyScoreHeader]>=reviewThreshold		
else:
	df['Reviewed'] = False
print('')

#figure out review cost
reviewCost = 3
print('What is the cost of review (enter a number, e.g. 2.5 if review cost is $2.50)')
while(True):
	try:
		reviewCost = input('>')
		if reviewCost == '':
			reviewCost = None
			break
		reviewCost = float(reviewCost)
		break
	except:
		print('...please try that again')

#################################################################################################
# PRINT OUT FILE BREAKDOWN
#Calculate total orders, total good and total bad
print('Calculating total reviews, total good and bad orders...')
totalRecords = len(df.index)
totalReviews = df['Reviewed'].sum()
totalRejects = df['Rejected'].sum()
totalNonFraud = df['NonFraud'].sum()
totalCaughtFraud = df['CaughtFraud'].sum()
totalMissedFraud = df['MissedFraud'].sum()

print('')
print('Current review rate looks to be '+str(math.floor(10000.0*totalReviews/float(totalRecords))/100.0)+'%. What is the max review rate we should tolerate?\n (e.g. enter 0.125 for 12.5%, or enter nothing if you don\'t want to set any limit)')
maxReviews = None
maxReviewRate = None
while(True):
	try:
		maxReviewRate = input('>')
		if maxReviewRate == '':
			maxReviewRate = None
			break
		maxReviewRate = float(maxReviewRate)
		break
	except:
		print('...please try that again')
if maxReviewRate is not None:
	maxReviews = math.floor(float(totalRecords)*maxReviewRate)

print('')
print('Current chargeback rate looks to be '+str(math.floor(100000.0*totalMissedFraud/float(totalRecords))/1000.0)+'%. What is the max CB rate we should tolerate?\n (e.g. enter 0.0050 for 0.50%, or enter nothing if you don\'t want to set any limit)')
maxCBs = None
maxCBRate = None
while(True):
	try:
		maxCBRate = input('>')
		if maxCBRate == '':
			maxCBRate = None
			break
		maxCBRate = float(maxCBRate)
		break
	except:
		print('...please try that again')
if maxCBRate is not None:
	maxCBs = math.floor(float(totalRecords)*maxCBRate)
	
print('')
print('max Reviews = '+str(maxReviews))
print('max Chargebacks = '+str(maxCBs))
print('')
	
	
#################################################################################################
# STARTING SIGNAL ANALYSIS WORK HERE
fullCols = df.columns.tolist()
idcCols = fullCols[fullCols.index('Error'):(fullCols.index('Confidence Score')+1)]
#make sure we include the extra bucket fields we've added
for field in ['Confidence Score Bucket 1','Confidence Score Bucket 2','Confidence Score Bucket 3','Email First Seen Bucket 1','Email First Seen Bucket 2','IP to Address Bucket','IP to Phone Bucket']:
	if field in fullCols:
		idcCols.append(field)

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
		#don't build rules around null values, diagnostics, or warnings
		if str(u) != 'nan' and 'Diagnostic' not in field and 'Warning' not in field:
			allKeyValuePairs.append(field+'|'+str(u))	

#calculate coverage, fraud likelihood, and WoE for all fields
print('Calculating fraud chance, WoE, etc. for all signals...')

ColSignal = []
ColTotal = []
ColNonFraud = []
ColCaughtFraud = []
ColMissedFraud = []
ColPctOfTotal = []
ColPctAreFraud = []
ColPctOfNonFraud = []
ColPctOfCaughtFraud = []
ColPctOfMissedFraud = []
ColWoE = []
ColIV = []

for kvi in allKeyValuePairs:
	ColSignal.append(kvi)
	
	kv = kvi.split('|')

	field = kv[0]
	value = kv[1]

	present = (df[field].astype(str) == str(value))
	thisNonFraud = numpy.multiply(present,df['NonFraud'])
	thisCaughtFraud = numpy.multiply(present,df['CaughtFraud'])
	thisMissedFraud = numpy.multiply(present,df['MissedFraud'])
	pctOfBad = max(thisCaughtFraud.sum()+thisMissedFraud.sum(),1)/float(max(totalCaughtFraud+totalMissedFraud,1))
	pctOfGood = max(thisNonFraud.sum(),1)/float(max(totalNonFraud,1))
	
	ColTotal.append(present.sum())
	ColNonFraud.append(thisNonFraud.sum())
	ColCaughtFraud.append(thisCaughtFraud.sum())
	ColMissedFraud.append(thisMissedFraud.sum())
	ColPctOfTotal.append(present.sum()/float(totalRecords))
	ColPctAreFraud.append((thisCaughtFraud.sum()+thisMissedFraud.sum())/float(present.sum()))
	ColPctOfNonFraud.append(thisNonFraud.sum()/float(totalNonFraud))
	ColPctOfCaughtFraud.append(thisCaughtFraud.sum()/float(totalCaughtFraud))
	ColPctOfMissedFraud.append(thisMissedFraud.sum()/float(totalMissedFraud))
	ColWoE.append(math.log(pctOfBad/float(pctOfGood)))
	ColIV.append(math.log(pctOfBad/float(pctOfGood))*(pctOfBad-pctOfGood))

signalsDF = pandas.DataFrame(data={'Signal':ColSignal,'# Orders':ColTotal,'# NonFraud':ColNonFraud,'# CaughtFraud':ColCaughtFraud,'# MissedFraud':ColMissedFraud,'% are Fraud':ColPctAreFraud,'% of NonFraud':ColPctOfNonFraud,'% of CaughtFraud':ColPctOfCaughtFraud,'% of MissedFraud':ColPctOfMissedFraud,'WoE':ColWoE,'IV':ColIV})
signalsDF = signalsDF[['Signal','# Orders','# NonFraud','# CaughtFraud','# MissedFraud','% are Fraud','% of NonFraud','% of CaughtFraud','% of MissedFraud','WoE','IV']]
signalsDF = signalsDF.sort_values(by=['IV'],ascending=[False])
signalsDF.to_csv(signalspath,index=False)	

print('Done! See '+str(signalspath))
print('')
print('Now identifying redundant signals...')

#work through top signals, discarding any that are redundant with other better signals, until we've identified the top 10 best non-redundant ones
topSignalsDF = signalsDF.iloc[[0]]
topFound = 1
currIndex = 0
while (currIndex < (len(signalsDF.index)-1)) and (len(topSignalsDF.index) < 20):
	currIndex += 1
	#what does it mean to be redundant? take this signal, and walk through all the previous top signals we've identified. For each, see what the overlap is. If there is >90% overlap
	#with any other better signal, then ignore this one
	thisSignal = signalsDF.iloc[[currIndex]]['Signal'].values[0]
	thisField = thisSignal.split('|')[0]
	thisValue = thisSignal.split('|')[1]
	thisPresent = (df[thisField].astype(str) == str(thisValue))
	redundant = False
	for x in range(0,currIndex):
		prevSignal = signalsDF.iloc[[x]]['Signal'].values[0]
		prevField = prevSignal.split('|')[0]
		prevValue = prevSignal.split('|')[1]
		prevPresent = (df[prevField].astype(str) == str(prevValue))
		combined = thisPresent & prevPresent
		if (combined.sum() / max(thisPresent.sum(),prevPresent.sum())) >= 0.9:
			print(str(thisSignal)+' found to be redundant with '+str(prevSignal))
			redundant = True
			break
	if redundant == False:
		topSignalsDF = topSignalsDF.append(signalsDF.iloc[[currIndex]],ignore_index=True)



print('')
print('Done! Top signals:')
print(topSignalsDF[['Signal','# Orders','% are Fraud']])

print('')
print('We will now walk through top signals, and you can choose which you want to build rules around.')
print('')

done = False
RulesChosen = pandas.DataFrame()
signalIndex = -1
while not done:
	signalIndex += 1
	print(topSignalsDF[['Signal','# Orders','% are Fraud']].iloc[[signalIndex]])
	gotinput = False
	while not gotinput:
		user_input = input('Build a rule for this? (enter y/n, or q if you have selected all the rules you want)\n>')
		gotinput = True
		if user_input != '' and user_input in 'yY':
			RulesChosen = RulesChosen.append(topSignalsDF.iloc[[signalIndex]],ignore_index=True)
		elif user_input != '' and user_input in 'qQ':
			done = True
		elif user_input == '' or user_input not in 'Nn':
			gotinput = False
			print('...please try that again')
	print('')
	if signalIndex >= len(topSignalsDF.index)-1:
		done = True

#sort by WoE in order to group positive and negative together for readability
RulesChosen = RulesChosen.sort_values(by=['WoE'],ascending=[True])
print('')
print('You have chosen the following data signals to build rules for:')
print(RulesChosen[['Signal','# Orders','% are Fraud']])

print('')
print('Now we\'ll get rolling on what the best rules are for these...')
print('')

dollarLimitOptions = [0,50,100,200]#we'll treat 0 as no limit
weightOptions = [0,25,50,75,100,125,150,200,250,300,350,400,450,500,600,700,800,900,1000,1200,1400,1600,1800,2000,3000,4000,5000,6000,8000,10000]

numRules = len(RulesChosen.index)
ruleDollarLimits = numpy.zeros(numRules).tolist()
ruleWeights = numpy.zeros(numRules).tolist()

#we're going to walk through the rules and for each one figure out what the optimal dollar limit and weight is.
#we will apply these as we go, so when we evaluate rule #3 for example, it won't be from a clean slate but
#will already have rule #1 and rule #2 applied. Once we're done, we will loop back over all the rules, as
#maybe the initial settings we came up with for #1 are no longer the best now that other rules have been applied

for iteration in range(0,2):
	for ruleIndex in range(0,numRules):
		if iteration == 0:
			print('looking at rule #'+str(ruleIndex+1))
		else:
			print('looking at rule #'+str(ruleIndex+1)+' again')
		bestSavings = 0
		bestDollarLimit = 0
		bestWeight = 0
		#figure out the new score coming from all other rules, then we'll see what works best for this rule
		baseNewScore = df[accertifyScoreHeader].copy()
		for r in range(0,numRules):
			if r == ruleIndex:
				continue
			signal = RulesChosen.iloc[[r]]['Signal'].values[0]
			field = signal.split('|')[0]
			value = signal.split('|')[1]
			ruleTripped = (df[field].astype(str) == str(value))
			if RulesChosen.iloc[[r]]['WoE'].values[0] < 0:#positive rule, low dollar
				if ruleDollarLimits[r] == 0:
					baseNewScore = baseNewScore + numpy.multiply(ruleTripped,-1*ruleWeights[r])
				else:
					baseNewScore = baseNewScore + numpy.multiply(numpy.multiply(ruleTripped,df[amtHeader]<=ruleDollarLimits[r]),-1*ruleWeights[r])
			else:#negative rule, high dollar
				if ruleDollarLimits[r] == 0:
					baseNewScore = baseNewScore + numpy.multiply(ruleTripped,ruleWeights[r])
				else:
					baseNewScore = baseNewScore + numpy.multiply(numpy.multiply(ruleTripped,df[amtHeader]>=ruleDollarLimits[r]),ruleWeights[r])
		for dollarLimit in dollarLimitOptions:
			for weight in weightOptions:
				signal = RulesChosen.iloc[[ruleIndex]]['Signal'].values[0]
				field = signal.split('|')[0]
				value = signal.split('|')[1]
				ruleTripped = (df[field].astype(str) == str(value))
				#if this is a negative rule, we need to track review cost and fraud savings, whereas if
				#this is a positive rule, we need to track review savings and fraud cost
				newScore = baseNewScore.copy()
				if RulesChosen.iloc[[ruleIndex]]['WoE'].values[0] < 0:#positive rule
					if dollarLimit == 0:
						newScore = newScore + numpy.multiply(ruleTripped,-1*weight)
					else:
						newScore = newScore + numpy.multiply(numpy.multiply(ruleTripped,df[amtHeader]<=dollarLimit),-1*weight)
				else: #negative rule
					if dollarLimit == 0:
						newScore = newScore + numpy.multiply(ruleTripped,weight)
					else:
						newScore = newScore + numpy.multiply(numpy.multiply(ruleTripped,df[amtHeader]>=dollarLimit),weight)
				#now see how newScore performs
				reviewSavings = 0
				fraudSavings = 0
				insultSavings = 0#sort of a misnomer as this will never be positive, only zero or negative
				totalReviews = (newScore >= reviewThreshold).sum()
				totalCBs = (df['OverallStatus']=='MissedFraud').sum()
				if rejectThreshold is not None:
					ReviewToReject = (df[accertifyScoreHeader]>=reviewThreshold) & (df[accertifyScoreHeader]<rejectThreshold) & (newScore>=rejectThreshold)
					AcceptToReject = (df[accertifyScoreHeader]<reviewThreshold) & (newScore>=rejectThreshold)
					RejectToReview = (df[accertifyScoreHeader]>=rejectThreshold) & (newScore<rejectThreshold) & (newScore>=reviewThreshold)
					RejectToAccept = (df[accertifyScoreHeader]>=rejectThreshold) & (newScore<reviewThreshold)
					reviewSavings += (ReviewToReject.sum() - RejectToReview.sum())*reviewCost
					fraudSavings += (numpy.multiply(numpy.multiply(ReviewToReject,df['MissedFraud']),df[amtHeader]).sum() + numpy.multiply(numpy.multiply(AcceptToReject,df['MissedFraud']),df[amtHeader]).sum() - numpy.multiply(RejectToAccept,df[amtHeader]).sum())
					insultSavings += (0 - numpy.multiply(numpy.multiply(ReviewToReject,df['NonFraud']),df[amtHeader]).sum() - numpy.multiply(numpy.multiply(AcceptToReject,df['NonFraud']),df[amtHeader]).sum())
					totalReviews -= (newScore >= rejectThreshold).sum()
					totalCBs -= (numpy.multiply(ReviewToReject,df['MissedFraud']).sum() + numpy.multiply(AcceptToReject,df['MissedFraud']).sum() - RejectToAccept.sum())
					
				ReviewToAccept = (df[accertifyScoreHeader]>=reviewThreshold) & (newScore<reviewThreshold)
				AcceptToReview = (df[accertifyScoreHeader]<reviewThreshold) & (newScore>=reviewThreshold)
				reviewSavings += (ReviewToAccept.sum() - AcceptToReview.sum())*reviewCost
				fraudSavings += (numpy.multiply(numpy.multiply(AcceptToReview,df['MissedFraud']),df[amtHeader]).sum() - numpy.multiply(numpy.multiply(ReviewToAccept,df['CaughtFraud']),df[amtHeader]).sum())
				totalCBs -=	(numpy.multiply(AcceptToReview,df['MissedFraud']).sum() - numpy.multiply(ReviewToAccept,df['CaughtFraud']).sum())
					
				totalSavings = reviewSavings + fraudSavings + insultSavings
				if (totalSavings > bestSavings) and ((maxReviews is None) or (totalReviews <= maxReviews)) and ((maxCBs is None) or (totalCBs <= maxCBs)):
					#print 'best so far has savings '+str(totalSavings)+' using weight '+str(weight)+' and dollar limit '+str(dollarLimit)
					bestSavings = totalSavings
					bestDollarLimit = dollarLimit
					bestWeight = weight
		#done, now set the best stuff
		ruleDollarLimits[ruleIndex] = bestDollarLimit
		ruleWeights[ruleIndex] = bestWeight

#aaaall done, now calculate overall results and print this shit out
newScore = df[accertifyScoreHeader].copy()
for r in range(0,numRules):
	signal = RulesChosen.iloc[[r]]['Signal'].values[0]
	field = signal.split('|')[0]
	value = signal.split('|')[1]
	ruleTripped = (df[field].astype(str) == str(value))
	if RulesChosen.iloc[[r]]['WoE'].values[0] < 0:#positive rule, low dollar
		if ruleDollarLimits[r] == 0:
			newScore = newScore + numpy.multiply(ruleTripped,-1*ruleWeights[r])
			df[str(signal)+' (no dollar limit)'] = ruleTripped
		else:
			newScore = newScore + numpy.multiply(numpy.multiply(ruleTripped,df[amtHeader]<=ruleDollarLimits[r]),-1*ruleWeights[r])
			df[str(signal)+' (and <= '+str(ruleDollarLimits[r])+')'] = numpy.multiply(ruleTripped,df[amtHeader]<=ruleDollarLimits[r])
	else:#negative rule, high dollar
		if ruleDollarLimits[r] == 0:
			newScore = newScore + numpy.multiply(ruleTripped,ruleWeights[r])
			df[str(signal)+' (no dollar limit)'] = ruleTripped
		else:
			newScore = newScore + numpy.multiply(numpy.multiply(ruleTripped,df[amtHeader]>=ruleDollarLimits[r]),ruleWeights[r])
			df[str(signal)+' (and >= '+str(ruleDollarLimits[r])+')'] = numpy.multiply(ruleTripped,df[amtHeader]>=ruleDollarLimits[r])
reviewSavings = 0
fraudSavings = 0
insultSavings = 0#sort of a misnomer as this will never be positive, only zero or negative
if rejectThreshold is not None:
	ReviewToReject = (df[accertifyScoreHeader]>=reviewThreshold) & (df[accertifyScoreHeader]<rejectThreshold) & (newScore>=rejectThreshold)
	AcceptToReject = (df[accertifyScoreHeader]<reviewThreshold) & (newScore>=rejectThreshold)
	RejectToReview = (df[accertifyScoreHeader]>=rejectThreshold) & (newScore<rejectThreshold) & (newScore>=reviewThreshold)
	RejectToAccept = (df[accertifyScoreHeader]>=rejectThreshold) & (newScore<reviewThreshold)
	reviewSavings += (ReviewToReject.sum() - RejectToReview.sum())*reviewCost
	fraudSavings += (numpy.multiply(numpy.multiply(ReviewToReject,df['MissedFraud']),df[amtHeader]).sum() + numpy.multiply(numpy.multiply(AcceptToReject,df['MissedFraud']),df[amtHeader]).sum() - numpy.multiply(RejectToAccept,df[amtHeader]).sum())
	insultSavings += (0 - numpy.multiply(numpy.multiply(ReviewToReject,df['NonFraud']),df[amtHeader]).sum() - numpy.multiply(numpy.multiply(AcceptToReject,df['NonFraud']),df[amtHeader]).sum())
	
if reviewThreshold is not None:
	ReviewToAccept = (df[accertifyScoreHeader]>=reviewThreshold) & (newScore<reviewThreshold)
	AcceptToReview = (df[accertifyScoreHeader]<reviewThreshold) & (newScore>=reviewThreshold)
	reviewSavings += (ReviewToAccept.sum() - AcceptToReview.sum())*reviewCost
	fraudSavings += (numpy.multiply(numpy.multiply(AcceptToReview,df['MissedFraud']),df[amtHeader]).sum() - numpy.multiply(numpy.multiply(ReviewToAccept,df['CaughtFraud']),df[amtHeader]).sum())
	
totalSavings = reviewSavings + fraudSavings + insultSavings

print('Done!')
print('')
print('Total Savings: '+str(totalSavings))
print('Review Savings: '+str(reviewSavings))
print('Fraud Savings: '+str(fraudSavings))
NEG1OR1 = numpy.where(RulesChosen['WoE'] < 0,-1,1)
finalRuleWeights = numpy.multiply(ruleWeights,NEG1OR1)
GTELTE = numpy.where(RulesChosen['WoE'] < 0,"<=",">=")
finalDollarLimits = numpy.core.defchararray.add(GTELTE,numpy.array(ruleDollarLimits).astype(str))

solutionDF = pandas.DataFrame(data={'Signal':RulesChosen['Signal'].tolist(),'Dollar limit':finalDollarLimits,'Weight':finalRuleWeights})
print(solutionDF)

print('')
print('Now we\'re going to look at different score ranges and dollar limits to call Whitepages on, and how that impacts things.')
print('')
df['newScore'] = newScore

df.to_csv(scoreColumnPath)