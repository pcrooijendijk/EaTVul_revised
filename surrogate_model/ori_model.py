# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
import torch
import torch.nn as nn
import torch
from torch.autograd import Variable
import copy
from torch.nn import CrossEntropyLoss, MSELoss

    
    
class Model(nn.Module):   
    def __init__(self, encoder,config,tokenizer,args):
        super(Model, self).__init__()
        self.encoder = encoder
        self.config=config
        self.tokenizer=tokenizer
        self.args=args
        feature_size = self.config.hidden_size
        self.logit_fc = nn.Linear(feature_size, 1)
    

    def forward(self, input_ids=None, labels=None):
        attention_mask = input_ids.ne(0)
        # Assuming the encoder is outputting a tensor shaped [batch_size, sequence_length, feature_size]
        # outputs = self.encoder(input_ids, attention_mask=input_ids.ne(1))[0]
        outputs = self.encoder(input_ids, attention_mask=attention_mask)


        # Apply pooling operation to retrieve a single feature vector for each input in the batch
        pooled_output = outputs.hidden_states[-1].mean(dim=1)  # global mean pooling; you can also use other pooling strategies

        # Logistic regression on pooled features to obtain logits
        # Assuming `self.logit_fc` is a linear layer defined in the model's `__init__` method
        logits = self.logit_fc(pooled_output)

        # Compute probabilities using sigmoid since its binary classification
        prob = torch.sigmoid(logits)

        if labels is not None:
            labels = labels.float()  # Convert labels to float for loss computation
            labels = labels.view(-1, 1)  # Reshape to match the logits' shape for broadcasting
            loss_fct = nn.BCEWithLogitsLoss()  # Using the built-in loss function which is more stable
            loss = loss_fct(logits, labels)  # Compute the loss between logits and labels

            return loss, prob
        else:
            return prob
        
 
