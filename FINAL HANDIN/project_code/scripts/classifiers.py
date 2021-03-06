import csv
import random
import sys
import argparse
import numpy as np
from sklearn import tree
from sklearn import ensemble
from sklearn import cross_validation
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.cross_validation import StratifiedShuffleSplit
from sklearn.grid_search import GridSearchCV

def extractData(datapath):
	with open(datapath, 'rb') as fid:
		reader = csv.reader(fid, delimiter='|')
		reader.next()  # skip past first line
		good_inds = [1, 2, 3, 4, 5, 6, 12, 14, 19, 22, 25, 32, 36]
		price_ind = 13
		cheapX = []
		cheapY = []
		expX = []
		expY = []
		for row in reader:
			if row[price_ind] == 'n/a':
				continue
			feat = []
			for i in good_inds:
				curr_val = row[i]
				if i == 1:  # stars
					if curr_val == 'n/a':
						curr_val = 0
					else:
						if float(curr_val) > 3.0:
							curr_val = 1
						else:
							curr_val = 0
				elif i == 6:  # noise
					if curr_val in ['loud', 'very_loud']:
						curr_val = 1
					else:
						curr_val = 0
				elif i == 14:  # attire
					if curr_val in ['formal', 'dressy']:
						curr_val = 1
					else:
						curr_val = 0
				elif i == 36:  # alcohol
					if curr_val in ['beer_and_wine', 'full_bar']:
						curr_val = 1
					else:
						curr_val = 0
				else:
					assert curr_val in ['n/a', 'True', 'False']
					if curr_val == 'True':
						curr_val = 1
					else:
						curr_val = 0
				feat.append(curr_val)
			price = row[price_ind]
			price = int(price)
			if price > 2:
				expX.append(feat)
				expY.append(1)
			else:
				cheapX.append(feat)
				cheapY.append(0)
	assert len(cheapX) == len(cheapY)
	assert len(expX) == len(expY)
	return cheapX, cheapY, expX, expY

def shuffleListPairs(X, Y):
	XY = zip(X, Y)
	random.shuffle(XY)
	return extractXY(XY)

def extractXY(XY):
	X = [i for i, j in XY]
	Y = [j for i, j in XY]
	return X, Y

def getUndersampledSets(smallX, smallY, bigX, bigY):
	bigTrainXY = random.sample(zip(bigX, bigY), len(smallY))
	bigTrainX, bigTrainY = extractXY(bigTrainXY)
	X = bigTrainX + smallX
	Y = bigTrainY + smallY
	return shuffleListPairs(X, Y)

def classifyWithUndersampling(clf, smallX, smallY, bigX, bigY, iter_weight = 3):
	len_small = len(smallY)
	len_big = len(bigY)
	num_iter = int(float(len_big) / len_small) * iter_weight  # scale num_iter with big/small ratio
	accuracies = []
	# Undersample and obtain average score num_iter times, and then average together the average scores
	print 'Undersampling... (will sample/train/test %d cheap and %d expensive %d times)' % (len_small, len_small, num_iter)
	sys.stdout.flush()
	for _ in range(num_iter):
		X, Y = getUndersampledSets(smallX, smallY, bigX, bigY)
		scores = cross_validation.cross_val_score(clf, X, Y, cv=10)
		accuracies.append(scores.mean())
	accuracies = np.array(accuracies)
	print 'Finished!'
	print 'Accuracy: %0.2f%% (+/- %0.2f%%)' % (accuracies.mean()*100, accuracies.std()*2*100)

def generateDotFileWithUndersampling(clf, smallX, smallY, bigX, bigY):
	X, Y = getUndersampledSets(smallX, smallY, bigX, bigY)
	clf = clf.fit(X, Y)
	with open('../dt_graphic_representation/DT_undersampled.dot', 'w') as f:
		tree.export_graphviz(clf, out_file=f)
	print 'Generated dot file'

def parseArgs():
	parser = argparse.ArgumentParser()
	parser.add_argument('-classifier', required=True, help='dt or rf')
	parser.add_argument('-gendot', default=False, help='generate dot file')
	opts = parser.parse_args()
	classifier = opts.classifier
	gendot = opts.gendot
	if classifier not in ['dt', 'rf', 'svm']:
		print 'Invalid classifier.'
		sys.exit(0)
	if gendot and classifier in ['rf', 'svm']:
		print 'gendot incompatible with', classifier
		sys.exit(0)
	return classifier, gendot

def getSVMParams(smallX, smallY, bigX, bigY):
	X, y = getUndersampledSets(smallX, smallY, bigX, bigY)
	X = np.array(X).astype('float64')
	y = np.array(y).astype('float64')
	scaler = StandardScaler()
	X = scaler.fit_transform(X)
	C_range = np.logspace(-2, 10, 13)
	gamma_range = np.logspace(-9, 3, 13)
	param_grid = dict(gamma=gamma_range, C=C_range)
	cv = StratifiedShuffleSplit(y, n_iter=5, test_size=0.2, random_state=42)
	print 'processing...'
	grid = GridSearchCV(SVC(), param_grid=param_grid, cv=cv)
	grid.fit(X, y)
	print grid.best_params_, grid.best_score_
	return grid.best_params_, grid.best_score_

def main():
	classifier, gendot = parseArgs()
	cheapX, cheapY, expX, expY = extractData('../cleaned_data/attributes_all.txt')
	print 'Num cheap restaurants:', len(cheapY)
	print 'Num expensive restaurants:', len(expY)
	if classifier == 'dt':
		clf = tree.DecisionTreeClassifier(max_depth=3)
		classifyWithUndersampling(clf, expX, expY, cheapX, cheapY)
		if gendot:
			generateDotFileWithUndersampling(clf, expX, expY, cheapX, cheapY)
	elif classifier == 'rf':
		clf = ensemble.RandomForestClassifier(max_depth=3)
		classifyWithUndersampling(clf, expX, expY, cheapX, cheapY)
	elif classifier == 'svm':
		# C was obtained using the computationally expensive function getSVMParams
		# The default gamma value of 'auto' was found to be optimal
		C = 0.10000000000000001
		clf = SVC(C=C)
		classifyWithUndersampling(clf, expX, expY, cheapX, cheapY)

if __name__ == '__main__':
	main()
