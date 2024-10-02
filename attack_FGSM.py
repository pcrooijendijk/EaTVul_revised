from transformers import Trainer
import torch
import torch.nn.functional as F
import torchattacks
from dataset import get_dataset, balance_dataset, train_val_test_split

class AdversarialTrainer(Trainer):
    def __init__(self, attack, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attack = attack  # Instance of torchattacks.FGSM or other attacks

    def training_step(self, model, inputs):
        model.train()
        inputs = self._prepare_inputs(inputs)

        # Forward pass on clean inputs
        outputs = model(**inputs)
        loss = outputs.loss
        loss.backward()

        # Generate adversarial examples
        adv_inputs = self.attack(inputs['input_ids'], inputs['labels'])

        # Zero gradients before adversarial pass
        model.zero_grad()

        # Forward pass on adversarial inputs
        adv_outputs = model(inputs_embeds=adv_inputs['inputs_embeds'], attention_mask=inputs['attention_mask'])
        adv_loss = adv_outputs.loss
        adv_loss.backward()

        # Combine losses
        total_loss = loss + adv_loss

        # Update model parameters
        self.optimizer.step()
        self.lr_scheduler.step()
        self.optimizer.zero_grad()

        return total_loss.detach()


def get_fgsm_attack(model, epsilon=0.01):
    """
    Initializes the FGSM attack.

    Args:
        model (nn.Module): The model to attack.
        epsilon (float): Perturbation magnitude.

    Returns:
        torchattacks.FGSM: Configured FGSM attack instance.
    """
    attack = torchattacks.FGSM(model, eps=epsilon)
    return attack


class FGSMEmbedding(torchattacks.FGSM):
    def __call__(self, inputs, labels):
        # Extract embeddings
        inputs_embeds = self.model.get_input_embeddings()(inputs)
        # inputs_embeds.requires_grad = True

        # Forward pass with embeddings
        outputs = self.model(inputs_embeds=inputs_embeds, attention_mask=(inputs != 0))
        loss = self.loss_fn(outputs.logits, labels)
        loss.backward()

        # Generate perturbations
        perturbation = self.epsilon * inputs_embeds.grad.sign()

        # Create adversarial embeddings
        adv_inputs_embeds = inputs_embeds + perturbation

        return {'inputs_embeds': adv_inputs_embeds.detach(), 'attention_mask': (inputs != 0)}

from transformers import BertTokenizerFast
import torch
import json
from torch.utils.data import Dataset

class CodeVulnerabilityDataset(Dataset):
    def __init__(self, json_path, tokenizer, max_length=50):
        with open(json_path, 'r') as f:
            self.data = json.load(f)
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        code = self.data[idx]['code']
        label = self.data[idx]['label']
        encoding = self.tokenizer(code, truncation=True, padding='max_length', max_length=self.max_length, return_tensors='pt')
        return {
            'input_ids': encoding['input_ids'].squeeze(),  # Remove batch dimension
            'attention_mask': encoding['attention_mask'].squeeze(),
            'labels': torch.tensor(label, dtype=torch.long)
        }

from transformers import BertForSequenceClassification, TrainingArguments
from sklearn.metrics import accuracy_score

def compute_metrics(p):
    """
    This function computes the accuracy of a model's predictions.
    The accuracy is calculated as the number of correct predictions divided by the total number of predictions.
    """
    accuracy = accuracy_score(p.label_ids, p.predictions.argmax(-1))

    return {
        "accuracy": accuracy,
    }

# Load the dataset
dataset = get_dataset("data/asterisk_ast_train.json")

# Balance the dataset so that we have an equal number of vulnerable and non-vulnerable samples
dataset = balance_dataset(dataset)

# Split the dataset into train, validation, and test sets
train_dataset, val_dataset, test_dataset = train_val_test_split(dataset) # Train on benign source code
adv_test_dataset = get_dataset("data/asterisk_ast_test_ADV.json")

# Load the model
model = BertForSequenceClassification.from_pretrained('google/bert_uncased_L-2_H-128_A-2',
                                                      num_labels=2)

# Initialize FGSM attack
epsilon = 0.01
fgsm_attack = FGSMEmbedding(model, eps=epsilon)

# Define training arguments
training_args = TrainingArguments(
    output_dir='./results',
    num_train_epochs=5,
    per_device_train_batch_size=8,
    per_device_eval_batch_size=16,
    evaluation_strategy='epoch',
    save_strategy='epoch',
    logging_dir='./logs',
    logging_steps=10,
    load_best_model_at_end=True,
    metric_for_best_model='accuracy'
)

# Initialize the AdversarialTrainer
trainer = AdversarialTrainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=val_dataset,
    compute_metrics=compute_metrics,
    attack=fgsm_attack
)

# Start training
trainer.train()

# Evaluate on test set
test_results = trainer.evaluate(test_dataset)
print(f"Test Accuracy: {test_results['eval_accuracy']}")
