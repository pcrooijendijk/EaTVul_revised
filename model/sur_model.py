# -*- coding: utf-8 -*-
"""
Bi-LSTM model

"""

from keras.models import Model
from keras.layers import Input, Dense, Embedding, Bidirectional, LSTM, GlobalMaxPooling1D, merge, concatenate, CuDNNLSTM, Lambda
from keras.layers.core import Dropout, Permute, Reshape, Flatten, RepeatVector
import keras.backend as K




# if True, the attention vector is shared across the input_dimensions where the attention is applied.
#SINGLE_ATTENTION_VECTOR = False
SINGLE_ATTENTION_VECTOR = True

def attention_3d_block(inputs, TIME_STEPS):
    # inputs.shape = (batch_size, time_steps, input_dim)
    input_dim = int(inputs.shape[2])
    a = Permute((2, 1))(inputs)
    print(a)
    a = Reshape((input_dim, TIME_STEPS))(a) # this line is not useful. It's just to know which dimension is what.
    print(a)
    a = Dense(TIME_STEPS, activation='softmax')(a)
    print(a)
    if SINGLE_ATTENTION_VECTOR:
        a = Lambda(lambda x: K.mean(x, axis=1), name='dim_reduction')(a)
        print(a)
        a = RepeatVector(input_dim)(a)
        print(a)
    a_probs = Permute((2, 1), name='attention_vec')(a)
#   
    print('a_probs is')
    print(a_probs)
#        
#    output_attention_mul = merge([inputs, a_probs], name='attention_mul', mode='mul')
    output_attention_mul = concatenate([inputs, a_probs])
    print(output_attention_mul)
    return output_attention_mul


def BiLSTM_network(MAX_LEN, EMBEDDING_DIM, word_index, embedding_matrix, use_dropout=False):
    inputs = Input(shape=(MAX_LEN,))

    sharable_embedding = Embedding(len(word_index) + 1,
                               EMBEDDING_DIM,
                               weights=[embedding_matrix],
                               input_length=MAX_LEN,
                               trainable=False)(inputs)
    bilstm_1 = Bidirectional(CuDNNLSTM(64, return_sequences=True))(sharable_embedding)
    if use_dropout:
        droput_layer_1 = Dropout(0.5)(bilstm_1)
        bilstm_2 = Bidirectional(CuDNNLSTM(128, return_sequences=True))(droput_layer_1)
    else:
        bilstm_2 = Bidirectional(CuDNNLSTM(64, return_sequences=True))(bilstm_1)
    
    #gmp_layer = GlobalMaxPooling1D()(bilstm_2)
    
    """
    Replace the GlobalMaxPool layer with the attention layer.
    
    """
    atten_layer = attention_3d_block(bilstm_2, MAX_LEN)
    flatten_layer = Flatten()(atten_layer)
    
    if use_dropout:
        dropout_layer_2 = Dropout(0.5)(flatten_layer)
        dense_1 = Dense(64, activation='relu')(dropout_layer_2)
    else:
        dense_1 = Dense(64, activation='relu')(flatten_layer)
        
    dense_2 = Dense(32)(dense_1)
    dense_3 = Dense(1, activation='sigmoid')(dense_2)
    
    model = Model(inputs=inputs, outputs = dense_3, name='BiLSTM_network')

    
    return model