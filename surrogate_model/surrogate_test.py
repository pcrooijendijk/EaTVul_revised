# -*- coding: utf-8 -*-


from random import randrange
import os
import csv
import pickle
import numpy as np
import pandas as pd

from keras.layers import Input
from keras.models import load_model, Model

from keras.preprocessing.sequence import pad_sequences
from sklearn.manifold import TSNE


from sklearn.metrics import classification_report
from sklearn.metrics import confusion_matrix
from key_token_capture import printAttentionWords
import datetime
import keras.backend as K
#import utils
starttime = datetime.datetime.now() #long running #do something other

LOSS_FUNCTION = 'binary_crossentropy'
OPTIMIZER = 'adamax'

MAX_LEN = 200
EMBEDDING_DIM = 100
BATCH_SIZE = 64

working_dir = '/content/'


model_saved_path = working_dir + 'models/'
#model_saved_path = working_dir 

model_name = 'SAVE_BEST_MODEL'

model = load_model(model_saved_path + model_name, custom_objects={"K": K})


model.compile(loss= LOSS_FUNCTION,
              optimizer=OPTIMIZER,
              metrics=['accuracy'])

print ("The model has been loaded: ")
print (model.summary())

def LoadSavedData(path):
    with open(path, 'rb') as f:
        loaded_data = pickle.load(f)
    return loaded_data

def ListToCSV(list_to_csv, path):
    df = pd.DataFrame(list_to_csv)
    df.to_csv(path, index=False)

test_set_x = LoadSavedData(working_dir + 'test_set_x.pickle')
test_set_y = LoadSavedData(working_dir + 'test_set_y.pickle')

print (test_set_x.shape) 

tokenizer = LoadSavedData(working_dir + 'binary_tokenizer.pickle')
word_index = tokenizer.word_index


print ("max_len ", MAX_LEN)
print('Pad sequences (samples x time)')

probs = model.predict(test_set_x, batch_size = BATCH_SIZE, verbose=1)

with open(working_dir + 'probs.pickle', 'wb') as handle:
    #pickle.dump(tokenizer, handle, protocol=pickle.HIGHEST_PROTOCOL)
    pickle.dump(probs, handle, protocol=2)

ListToCSV(probs.tolist(), 'prob_sur_model.csv')

predicted_classes = []

for item in probs:
    if item[0] > 0.5:
        predicted_classes.append(1)
    else:
        predicted_classes.append(0)

ListToCSV(predicted_classes, 'classes_assembly.csv')

test_accuracy = np.mean(np.equal(test_set_y, predicted_classes))

test_set_y = np.asarray(test_set_y)

print ("Surrogate Model classification result: ")

target_names = ["Non-vulnerable","Vulnerable"] #non-vulnerable->0, vulnerable->1
print (confusion_matrix(test_set_y, predicted_classes, labels=[0,1]))   
print ("\r\n")
print ("\r\n")
print (classification_report(test_set_y, predicted_classes, target_names=target_names))
endtime = datetime.datetime.now()
print((endtime - starttime).seconds)

#printAttentionWords(test_set_x, test_set_y, model, word_index, 20)