from __future__ import absolute_import, division, print_function

import argparse
import glob
import logging
import os
import pickle
import random
import re
import shutil
import json

import numpy as np
import torch
from transformers import RobertaConfig, RobertaForSequenceClassification, RobertaForMaskedLM, RobertaTokenizer

logger = logging.getLogger(__name__)

class codebert(object):
    def __init__(self, model_type, model_path, device):
        self.model_type = model_type
        self.tokenizer = RobertaTokenizer.from_pretrained(model_path)
        if model_type == "mlm":
            self.model = RobertaForMaskedLM.from_pretrained(model_path)
        elif model_type == "cls":
            self.model = RobertaForSequenceClassification.from_pretrained(model_path, num_labels=104)
        self.block_size = 512
        self.device = device

    def tokenize(self, inputs, cut_and_pad=False, ret_id=False):
        rets = []
        if isinstance(inputs, str):
            inputs = [inputs]
        for sent in inputs:
            if cut_and_pad:
                tokens = self.tokenizer.tokenize(sent)[:self.block_size-2]
                tokens = [self.tokenizer.cls_token] + tokens + [self.tokenizer.sep_token]
                padding_length = self.block_size - len(tokens)
                tokens += [self.tokenizer.pad_token] * padding_length
            else:
                tokens = self.tokenizer.tokenize(sent)
                tokens = [self.tokenizer.cls_token] + tokens + [self.tokenizer.sep_token]
            if not ret_id:
                rets.append(tokens)
            else:
                ids = self.tokenizer.convert_tokens_to_ids(tokens)
                rets.append(ids)
        return rets

    def _run_batch(self, batch):
        self.model.eval()
        batch_max_length = batch.ne(self.tokenizer.pad_token_id).sum(-1).max().item()
        inputs = batch[:, :batch_max_length]
        inputs = inputs.to(self.device)
        with torch.no_grad():
            outputs = self.model(inputs, attention_mask=inputs.ne(self.tokenizer.pad_token_id))
            logits = outputs[0]
        return logits
    
    def run(self, inputs, batch_size=16):
        input_ids = self.tokenize(inputs, cut_and_pad=True, ret_id=True)
        outputs = None
        batch_num = (len(input_ids) - 1) // batch_size + 1
        for step in range(batch_num):
            batch = torch.tensor(input_ids[step*batch_size: (step+1)*batch_size])
            if outputs is None:
                outputs = self._run_batch(batch)
            else:
                outputs = torch.cat((outputs, self._run_batch(batch)), 0)
        return outputs


class codebert_mlm(codebert):
    def __init__(self, model_path, device):
        super().__init__("mlm", model_path, device)

class codebert_cls(codebert):
    def __init__(self, model_path, device):
        super().__init__("cls", model_path, device)


