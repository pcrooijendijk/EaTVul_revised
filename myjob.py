from transformers import AutoTokenizer, AutoModel
import torch
import torch.nn as nn
import os

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

# Import dataset
from torch.utils.data import Dataset, DataLoader
import hashlib

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

# Initialize lists for samples and labels
samples = []
labels = []

# Directory containing the JSON files
json_directory = "train_data"

# Loop through each file in the directory
for filename in os.listdir(json_directory):
    if filename.endswith(".json"):  # Only process JSON files
        file_path = os.path.join(json_directory, filename)
        with open(file_path, "r") as f:
            for line in f:
                json_object = json.loads(line)
                samples.append(json_object['func'])
                labels.append(json_object['target'])

dataset = VulDeePeckerDataset(samples, labels, tokenizer)
print("Full data-set size:", len(dataset))

dataset = torch.utils.data.random_split(dataset, [0.8, 0.1, 0.1])
train_dataset = dataset[0]
test_dataset = dataset[1]
validation_dataset = dataset[2]
print("Train size:", len(train_dataset))
print("Test size:", len(test_dataset))
print("Validation size:", len(validation_dataset))

train_dataloader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
test_dataloader = DataLoader(test_dataset, batch_size=batch_size, shuffle=True)
validation_dataloader = DataLoader(validation_dataset, batch_size=batch_size, shuffle=True)

model = CodeBERTForVulnDetection(codebert_model)
optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=weight_decay)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = model.to(device)

from sklearn.metrics import confusion_matrix, accuracy_score, precision_score, recall_score, f1_score
from collections import namedtuple

# Evaluate model
def evaluate(dataloader):
  model.eval()

  all_labels = []
  all_predictions = []

  with torch.no_grad():
    for input_ids, attention_mask, labels in dataloader:
        # transfer to GPU if available
        input_ids = input_ids.to(device)
        attention_mask = attention_mask.to(device)
        labels = labels.to(device)

        # forward pass
        outputs = model.forward(input_ids, attention_mask)

        # find predictions and truths to calculate confusion matrix
        all_labels += torch.min(labels.cpu(), dim=1).indices.tolist()
        all_predictions += torch.min(outputs.cpu(), dim=1).indices.tolist()

  # evaluation scores
  cm = confusion_matrix(all_labels, all_predictions)
  accuracy = accuracy_score(all_labels, all_predictions)
  precision = precision_score(all_labels, all_predictions)
  recall = recall_score(all_labels, all_predictions)
  f1 = f1_score(all_labels, all_predictions)

  # Calculate false positive rate (FPR) and false negative rate (FNR)
  tn, fp, fn, tp = cm.ravel()
  fpr = fp / (fp + tn)
  fnr = fn / (fn + tp)

  # Create a named tuple to return values
  RetType = namedtuple("RetType", ["accuracy", "precision", "recall", "f1_score", "fpr", "fnr"])

  return RetType(accuracy, precision, recall, f1, fpr, fnr)

# Train the model
def train():
  output_dir = 'output'
  if not os.path.exists(output_dir):
    os.makedirs(output_dir)

  loss_values = []
  for epoch in range(num_epochs):
    model.train()

    loss_values.append([])
    batch_count = 0

    # iterate over batches
    for input_ids, attention_mask, labels in train_dataloader:
      # transfer to GPU if available
      input_ids = input_ids.to(device)
      attention_mask = attention_mask.to(device)
      labels = labels.to(device)

      # forward pass
      outputs = model.forward(input_ids, attention_mask)

      # calculate loss
      loss = model.loss_func(outputs, labels)

      # backpropagation
      optimizer.zero_grad()
      loss.backward()
      optimizer.step()

      # console info
      batch_count += 1
      loss_values[epoch].append(loss.item())

      print("\rEpoch: {}, Progress: {}/{};{:.2f}%, Loss Avg: {}, Current Batch Loss: {}".format(epoch + 1, batch_count * batch_size, len(train_dataset), ((batch_count*batch_size)/len(train_dataset))*100, sum(loss_values[epoch])/len(loss_values[epoch]), loss.item()), end="")

    # Evaluate epoch performance
    print("\nEvaluating Epoch Performance...", end="")
    eval_result = evaluate(test_dataloader)
    print("\rEpoch {} performance metrics:\nAccuracy: {:.4f}\nPrecision: {:.4f}\nRecall: {:.4f}\nF1 Score: {:.4f}\nFalse Positive Rate: {:.4f}\nFalse Negative Rate: {:.4f}".format(
        epoch + 1,
        eval_result.accuracy,
        eval_result.precision,
        eval_result.recall,
        eval_result.f1_score,
        eval_result.fpr,
        eval_result.fnr
    ))

    torch.save(model.state_dict(), os.path.join(output_dir, 'epoch{}_checkpoint.ckpt').format(epoch+1))

  # Plot Loss over time
  print("Done Training.")
  y_axis = []
  for l in loss_values:
    y_axis += l
  x_axis = list(range(1, len(y_axis) + 1, 1))

train()
