import torch
import os
from transformers import AutoTokenizer, AutoModel
from sklearn.metrics import confusion_matrix, accuracy_score, precision_score, recall_score, f1_score
from collections import namedtuple
from torch.utils.data import DataLoader
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import hashlib
import json 

tokenizer = AutoTokenizer.from_pretrained("microsoft/codebert-base")
codebert_model = AutoModel.from_pretrained("microsoft/codebert-base")

batch_size = 8
num_epochs = 10
learning_rate = 1e-5
weight_decay = 0.05
class_weights = torch.tensor([1.9, 0.68])

# Create the classification head
class CodeBERTForVulnDetection(nn.Module):
  def __init__(self, codebert):
    super(CodeBERTForVulnDetection, self).__init__()

    self.codebert = codebert
    self.dropout1 = nn.Dropout(p=0.2)
    self.linear1 = nn.Linear(768, 3072)
    self.tanh = nn.Tanh()
    self.dropout2 = nn.Dropout(p=0.2)
    self.linear2 = nn.Linear(3072, 3072)
    self.classifier = nn.Linear(3072, 2)

    self.loss_func = nn.BCEWithLogitsLoss(weight=class_weights)

  def forward(self, input_ids, attention_mask):
    # codeBERT output pooled
    output = self.codebert(input_ids = input_ids, attention_mask = attention_mask)
    output = torch.mean(output.last_hidden_state, 1)

    # classification head (https://arxiv.org/pdf/2204.03214.pdf, Table 4)
    output = self.dropout1(output)
    output = self.linear1(output)
    output = self.tanh(output)
    output = self.dropout2(output)
    output = self.linear2(output)
    output = self.classifier(output)

    return output

# remove duplicates and conflicting labels
def clean_data(text_samples, labels):
  hashmap = {}
  blacklist = []

  for i in range(len(text_samples)):
    sample_digest = hashlib.sha256(text_samples[i].encode('utf-8')).hexdigest()

    if hashmap.get(sample_digest) == None:
      hashmap[sample_digest] = (labels[i], i)
    else:
      if hashmap[sample_digest][0] != labels[i] and (sample_digest not in blacklist):
        blacklist.append(sample_digest)

  for blacklisted_sample in blacklist:
    hashmap.pop(blacklisted_sample)

  values = hashmap.values()

  cleaned_samples = [text_samples[val[1]] for val in values]
  cleaned_labels = [labels[val[1]] for val in values]

  return cleaned_samples, cleaned_labels

class VulDeePeckerDataset(Dataset):
  def __init__(self, samples, labels, tokenizer):
    self.tokenizer = tokenizer
    self.samples = samples
    self.labels = labels

    # Clean Data
    self.samples, self.labels = clean_data(self.samples, self.labels)

    # Tokenize samples
    self.samples = self.tokenizer(self.samples, padding=True, truncation=True, return_tensors='pt', max_length=512)

  def __len__(self):
    return len(self.labels)

  def __getitem__(self, idx):
    label = torch.tensor([self.labels[idx], 1 - self.labels[idx]], dtype=torch.float32)
    return self.samples["input_ids"][idx].squeeze(), self.samples["attention_mask"][idx].squeeze(), label
  
import json 
print("Loading dataset...")
samples = []
labels = []

with open("cwe119_ast_test_ADV.json", "r") as f: 
  for line in f: 
    json_object = json.loads(line)
    samples.append(json_object['func'])
    labels.append(json_object['target'])

# Load model architecture
model = CodeBERTForVulnDetection(codebert_model)
optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=weight_decay)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = model.to(device)

# Load the test dataset
test_dataset = VulDeePeckerDataset(samples, labels, tokenizer)
test_dataloader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)

# Define evaluation function
# Evaluate model
def evaluate(dataloader, model):
    model.eval()
    all_labels = []
    all_predictions = []

    with torch.no_grad():
        for input_ids, attention_mask, labels in dataloader:
            input_ids = input_ids.to(device)
            attention_mask = attention_mask.to(device)
            labels = labels.to(device)

            outputs = model.forward(input_ids, attention_mask)
            all_labels += torch.min(labels.cpu(), dim=1).indices.tolist()
            all_predictions += torch.min(outputs.cpu(), dim=1).indices.tolist()

    cm = confusion_matrix(all_labels, all_predictions)
    accuracy = accuracy_score(all_labels, all_predictions)
    precision = precision_score(all_labels, all_predictions, zero_division=1)  # Adjust here
    recall = recall_score(all_labels, all_predictions)
    f1 = f1_score(all_labels, all_predictions)

    tn, fp, fn, tp = cm.ravel()
    fpr = fp / (fp + tn)
    fnr = fn / (fn + tp)

    RetType = namedtuple("RetType", ["accuracy", "precision", "recall", "f1_score", "fpr", "fnr"])
    return RetType(accuracy, precision, recall, f1, fpr, fnr)


# Specify the checkpoint to load
checkpoint_path = '/vol/csedu-nobackup/project/prooijendijk/output/epoch10_checkpoint.ckpt'

# Load checkpoint
model.load_state_dict(torch.load(checkpoint_path))
model.to(device)

# Run evaluation
results = evaluate(test_dataloader, model)
print(f"Test Results:\nAccuracy: {results.accuracy}\nPrecision: {results.precision}\nRecall: {results.recall}\nF1 Score: {results.f1_score}")
print(f"Confusion Matrix:\n{results.confusion_matrix}")
