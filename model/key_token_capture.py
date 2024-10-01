import numpy as np
import pandas as pd
from keras import backend as K


def ListToCSV(list_to_csv, path):
    df = pd.DataFrame(list_to_csv)
    df.to_csv(path, index=False)

def visualize_attention(test_seq, i,
    model,
    id2wrd, # word_index.
    n):
    """
    Visualize that in the i th sequence, the top n words that the model pays attention to. 
    We first do a forward pass and get the output of the LSTM layer.
    THen we apply the function of the Attention layer and get the weights.
    Finally we obtain and print the words of the input sequence 
    that have these weights.


    """
    
    id2wrd = dict((v, k) for k, v in id2wrd.items()) # Exchange key with values.

    get_layer_output = K.function([model.layers[0].input, K.learning_phase()], [model.layers[4].output])
    out = get_layer_output([test_seq, ])[0]  # test mode

    att_w = model.layers[5].get_weights() # The attention layer is the sixth layer.

    eij = np.tanh(np.dot(out[i], att_w[0]))
#    print("1 eij is ............")
#    print(eij)
    ListToCSV(eij, 'eij.csv') =
    ai = np.exp(eij)
#    print("1 ai is ............")
#    print(ai)
    ListToCSV(ai, 'ai.csv') =
    weights = ai/np.sum(ai)
#    print("1 weights is ............")
#    print(weights)
    ListToCSV(weights, '1weights.csv') 
    weights = np.sum(weights,axis=1)
#    print("2 weights is ............")
#    print(weights)
    ListToCSV(weights, '2weights.csv') 
    topKeys = np.argpartition(weights,-n)[-n:]

    print (' '.join([id2wrd[wrd_id] for wrd_id in test_seq[i] if wrd_id != 0.]))
    print ('--------------------------Attentive Words start: --------------------------------------')
    
    for k in test_seq[i][topKeys]:
        if k != 0.:
            print (id2wrd[k])
    print ('--------------------------Attentive Words end: --------------------------------------')
    
    return

def printAttentionWords(test_set_x, test_set_y, model, word_index, num_word_pay_atten):
    
    vul_index = []
    
    for index, item in enumerate(test_set_y):
#        print(item)
        if item == 1:
#            print('item1')
#            print(item)
            vul_index.append(index)
#            print(vul_index)
#            print(index)
    
    # Only visualize the vulnerable sequences. 
    for item in vul_index:
#        print('item2')
#        print(item)
        visualize_attention(test_set_x, item, model, word_index, num_word_pay_atten)

#printAttentionWords(test_set_x, test_set_y, best_model, word_index, 20)
