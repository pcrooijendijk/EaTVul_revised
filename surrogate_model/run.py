from sklearn.svm import SVC
import json
from sklearn.feature_extraction.text import CountVectorizer
import torch
import logging
import random
import numpy as np
import os
from ori_model import Model
from torch.utils.data import DataLoader, Dataset, RandomSampler, SequentialSampler
from collections import defaultdict
from tqdm import tqdm
from torch.utils.data.distributed import DistributedSampler
import torch.nn.functional as F

from transformers import (WEIGHTS_NAME, AdamW, get_linear_schedule_with_warmup,
                          BertConfig, BertForMaskedLM, BertTokenizer,
                          GPT2Config, GPT2LMHeadModel, GPT2Tokenizer,
                          OpenAIGPTConfig, OpenAIGPTLMHeadModel, OpenAIGPTTokenizer,
                          RobertaConfig, RobertaForSequenceClassification, RobertaTokenizer,
                          DistilBertConfig, DistilBertForMaskedLM, DistilBertTokenizer)

MODEL_CLASSES = {
    'gpt2': (GPT2Config, GPT2LMHeadModel, GPT2Tokenizer),
    'openai-gpt': (OpenAIGPTConfig, OpenAIGPTLMHeadModel, OpenAIGPTTokenizer),
    'bert': (BertConfig, BertForMaskedLM, BertTokenizer),
    'roberta': (RobertaConfig, RobertaForSequenceClassification, RobertaTokenizer),
    'distilbert': (DistilBertConfig, DistilBertForMaskedLM, DistilBertTokenizer)
}

class TextDataset(Dataset):
    def __init__(self, tokenizer, block_size, file_path=None):
        self.examples = []
        self.ids_list = []
        with open(file_path) as f:
            for line in f:
                js=json.loads(line.strip())
                input_feature, ids_dict = convert_examples_to_features(js,tokenizer,block_size)
                self.examples.append(input_feature)
                self.ids_list.append(ids_dict)
        if 'train' in file_path:
            for idx, example in enumerate(self.examples[:3]):
                    logger.info("*** Example ***")
                    logger.info("idx: {}".format(idx))
                    logger.info("label: {}".format(example.label))
                    logger.info("input_tokens: {}".format([x.replace('\u0120','_') for x in example.input_tokens]))
                    logger.info("input_ids: {}".format(' '.join(map(str, example.input_ids))))

        output_file_name = file_path + "_ids.json"
        with open(output_file_name, 'w') as f:
            for data in self.ids_list:
                line = json.dumps(data)
                f.write(line+'\n')

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, i):       
        return torch.tensor(self.examples[i].input_ids),torch.tensor(self.examples[i].label)

class InputFeatures(object):
    """A single training/test features for a example."""
    def __init__(self,
                 input_tokens,
                 input_ids,
                 idx,
                 label,

    ):
        self.input_tokens = input_tokens
        self.input_ids = input_ids
        self.idx=str(idx)
        self.label=label

def convert_examples_to_features(js,tokenizer,block_size):
    #source
    ids_dict = defaultdict()
    code=' '.join(js['func'].split())
    code_tokens=tokenizer.tokenize(code)[:block_size-2]
    source_tokens =[tokenizer.cls_token]+code_tokens+[tokenizer.sep_token]
    source_ids =  tokenizer.convert_tokens_to_ids(source_tokens)
    padding_length = block_size - len(source_ids)
    source_ids+=[tokenizer.pad_token_id]*padding_length
    ids_dict['project'] = js['project']
    ids_dict['ids'] = source_ids
    ids_dict['idx'] = js['idx']
    ids_dict['labels'] = js['target']
    return InputFeatures(source_tokens,source_ids,js['idx'],js['target']), ids_dict

def get_support_vector_idx(sample_vec, sample_label):
    vectorizer = CountVectorizer()
    sample_vec = vectorizer.fit_transform(sample_vec).toarray()

    svclassifier = SVC(kernel='rbf')
    svclassifier.fit(sample_vec, sample_label)
    sv_idx = svclassifier.support_

    return sv_idx

def set_seed(seed=42):
    random.seed(seed)
    os.environ['PYHTONHASHSEED'] = str(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.backends.cudnn.deterministic = True

def train(
    train_dataset,
    model,
    tokenizer,
    per_gpu_train_batch_size,
    n_gpu,
    local_rank,
    weight_decay,
    learning_rate,
    adam_epsilon,
    epoch,
    gradient_accumulation_steps,
    device,
    fp16,
    fp16_opt_level,
    max_grad_norm,
    start_step,
    start_epoch,
    output_dir,
    logging_steps,
    save_steps,
    evaluate_during_training
):
    """Train the model without using args."""
    # Determine batch size
    train_batch_size = per_gpu_train_batch_size * max(1, n_gpu)
    # Set up the DataLoader for our training set
    train_sampler = RandomSampler(train_dataset) if local_rank == -1 else DistributedSampler(train_dataset)
    train_dataloader = DataLoader(
        train_dataset,
        sampler=train_sampler,
        batch_size=train_batch_size,
        num_workers=4,
        pin_memory=True
    )
    # Determine total number of optimization steps
    max_steps = epoch * len(train_dataloader)
    save_steps = len(train_dataloader)
    warmup_steps = len(train_dataloader)
    logging_steps = len(train_dataloader)
    num_train_epochs = epoch
    model.to(device)

    # Set up the optimizer and the learning rate scheduler
    no_decay = ['bias', 'LayerNorm.weight']
    optimizer_grouped_parameters = [
        {
            'params': [p for n, p in model.named_parameters() if not any(nd in n for nd in no_decay)],
            'weight_decay': weight_decay
        },
        {
            'params': [p for n, p in model.named_parameters() if any(nd in n for nd in no_decay)],
            'weight_decay': 0.0
        }
    ]
    optimizer = AdamW(optimizer_grouped_parameters, lr=learning_rate, eps=adam_epsilon)
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=warmup_steps,
        num_training_steps=max_steps
    )
    
    # Initialize mixed precision training
    if fp16:
        try:
            from apex import amp
        except ImportError as e:
            raise ImportError("Please install apex from https://www.github.com/nvidia/apex to use fp16 training.")
        model, optimizer = amp.initialize(model, optimizer, opt_level=fp16_opt_level)

    # Set up our model for parallel computing
    if n_gpu > 1:
        model = torch.nn.DataParallel(model)
    
    if local_rank != -1:
        model = torch.nn.parallel.DistributedDataParallel(
            model,
            device_ids=[local_rank],
            output_device=local_rank,
            find_unused_parameters=True
        )

    # Create the output directory if needed
    if local_rank in [-1, 0]:
        os.makedirs(output_dir, exist_ok=True)

    # Keep track of our performance and loss for logging
    tr_loss = 0.0
    global_step = start_step
    best_acc = 0.0
    model.zero_grad()
    
    # Train over all epochs
    for idx in range(start_epoch, int(num_train_epochs)):
        model.train()
        bar = tqdm(train_dataloader, total=len(train_dataloader))

        for step, batch in enumerate(bar):
            # Forward pass
            inputs = batch[0].to(device)
            labels = batch[1].to(device)
            outputs = model(inputs, labels=labels)
            loss = outputs.loss

            # Backward pass
            if n_gpu > 1:
                loss = loss.mean()  # average on multi-gpu parallel training
            if gradient_accumulation_steps > 1:
                loss = loss / gradient_accumulation_steps

            if fp16:
                with amp.scale_loss(loss, optimizer) as scaled_loss:
                    scaled_loss.backward()
            else:
                loss.backward()
            
            tr_loss += loss.item()
            if (step + 1) % gradient_accumulation_steps == 0:
                if fp16:
                    torch.nn.utils.clip_grad_norm_(amp.master_params(optimizer), max_grad_norm)
                else:
                    torch.nn.utils.clip_grad_norm_(model.parameters(), max_grad_norm)
                optimizer.step()
                scheduler.step()  # Update learning rate schedule
                model.zero_grad()
                global_step += 1

            # Log metrics and save model
            if local_rank in [-1, 0]:
                if logging_steps > 0 and global_step % logging_steps == 0:
                    # Log metrics
                    
                    if local_rank == -1 and evaluate_during_training:  # Only evaluate when single GPU otherwise metrics may not average well
                        results = evaluate(model, tokenizer,eval_when_training=True)
                        for key, value in results.items():
                            logger.info("  %s = %s", key, round(value,4))                    
                        # Save model checkpoint
                        
                    if results['eval_acc']>best_acc:
                        best_acc=results['eval_acc']
                        logger.info("  "+"*"*20)  
                        logger.info("  Best acc:%s",round(best_acc,4))
                        logger.info("  "+"*"*20)                          
                        
                        checkpoint_prefix = 'checkpoint-best-acc'
                        output_dir = os.path.join(args.output_dir, '{}'.format(checkpoint_prefix))                        
                        if not os.path.exists(output_dir):
                            os.makedirs(output_dir)                        
                        model_to_save = model.module if hasattr(model,'module') else model
                        output_dir = os.path.join(output_dir, '{}'.format('model.bin')) 
                        torch.save(model_to_save.state_dict(), output_dir)
                        logger.info("Saving model checkpoint to %s", output_dir)

def evaluate(
    model,
    tokenizer,
    eval_data_file,
    output_dir,
    device,
    n_gpu,
    local_rank,
    per_gpu_eval_batch_size
):
    # Loop to handle MNLI double evaluation (matched, mis-matched)
    eval_output_dir = output_dir

    eval_dataset = TextDataset(tokenizer, eval_data_file, block_size=512)  # Assuming `block_size` or similar arg needed

    if not os.path.exists(eval_output_dir) and local_rank in [-1, 0]:
        os.makedirs(eval_output_dir)

    eval_batch_size = per_gpu_eval_batch_size * max(1, n_gpu)
    # Note that DistributedSampler samples randomly
    eval_sampler = SequentialSampler(eval_dataset) if local_rank == -1 else DistributedSampler(eval_dataset)
    eval_dataloader = DataLoader(
        eval_dataset, 
        sampler=eval_sampler, 
        batch_size=eval_batch_size, 
        num_workers=4, 
        pin_memory=True
    )

    # multi-gpu evaluate
    if n_gpu > 1:
        model = torch.nn.DataParallel(model)

    # Evaluate!
    logger.info("***** Running evaluation *****")
    logger.info("  Num examples = %d", len(eval_dataset))
    logger.info("  Batch size = %d", eval_batch_size)
    
    eval_loss = 0.0
    nb_eval_steps = 0
    model.eval()
    logits = [] 
    labels = []
    for batch in eval_dataloader:
        inputs = batch[0].to(device)
        label = batch[1].to(device)
        with torch.no_grad():
            lm_loss, logit = model(inputs, labels=label)
            eval_loss += lm_loss.mean().item()
            logits.append(logit.cpu().numpy())
            labels.append(label.cpu().numpy())
        nb_eval_steps += 1

    logits = np.concatenate(logits, 0)
    labels = np.concatenate(labels, 0)
    preds = logits[:, 0] > 0.5  # Assuming binary classification
    eval_acc = np.mean(labels == preds)
    eval_loss = eval_loss / nb_eval_steps
    perplexity = torch.tensor(eval_loss)

    result = {
        "eval_loss": float(perplexity),
        "eval_acc": round(eval_acc, 4),
    }
    
    # Reset model to a single GPU after evaluation
    if n_gpu > 1:
        model = model.module if hasattr(model, 'module') else model

    return result

file_path = 'dataset/file/data/asterisk_ast_train.json'

# Initialize an empty list to hold all the JSON objects
json_objects = []

# Open the file and read line by line
with open(file_path, 'r') as file:
    for line in file:
        try:
            # Parse each line as a JSON objecte
            json_object = json.loads(line)
            # Append the parsed JSON object to our list
            json_objects.append(json_object)
        except json.JSONDecodeError as error:
            # Handle possible JSON decoding error
            print(f"Error parsing JSON: {error.msg}")
            continue

samples = []
labels = []
for object in json_objects: 
    samples.append(object['func'])
    labels.append(object['target'])

sv_idx = get_support_vector_idx(samples, labels)

# data = {
#     "array_data": sv_idx.tolist()
# }

# with open('training/training.json', 'w') as file: 
#     json.dump(data, file, indent=4)
# print(sv_idx)

local_rank = -1

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
logger = logging.getLogger(__name__)

# Setup logging
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(name)s -   %(message)s',
                    datefmt='%m/%d/%Y %H:%M:%S',
                    level=logging.INFO if local_rank in [-1, 0] else logging.WARN)
logger.warning("Process rank: %s, device: %s, n_gpu: %s, distributed training: %s, 16-bits training: %s",
                -1, device, 1, True)


# Set seed
set_seed()

output_dir = '/media/sf_internship/EaTVul/output'
train_data_file = 'training/training.json'

start_epoch = 0
start_step = 0
block_size = -1
do_train = True

model_type = 'bert'
config_name = 'bert-base-uncased'
tokenizer_name = 'bert-base-uncased'

config_class, model_class, tokenizer_class = MODEL_CLASSES[model_type]
config = config_class.from_pretrained(config_name)
config.num_labels=1
tokenizer = tokenizer_class.from_pretrained(tokenizer_name)

if block_size <= 0:
    block_size = tokenizer.max_len_single_sentence  # Our input block size will be the max possible for the model
block_size = min(block_size, tokenizer.max_len_single_sentence)
model = model_class(config)

model=Model(model,config,tokenizer,None)
if local_rank == 0:
    torch.distributed.barrier()  # End of barrier to make sure only the first process in distributed training download model & vocab

logger.info("Training/evaluation parameters %s")

# Training
if do_train:
    if local_rank not in [-1, 0]:
        torch.distributed.barrier()  # Barrier to make sure only the first process in distributed training process the dataset, and the others will use the cache
    train_dataset = TextDataset(tokenizer, block_size, train_data_file)
    if local_rank == 0:
        torch.distributed.barrier()

    trainer = train(
    train_dataset=train_data_file,
    model=model,
    tokenizer=tokenizer,
    per_gpu_train_batch_size=8,
    n_gpu=torch.cuda.device_count(),
    local_rank=-1,  # set to -1 if not using distributed training
    weight_decay=0.01,
    learning_rate=2e-5,
    adam_epsilon=1e-8,
    epoch=3,
    gradient_accumulation_steps=1,
    device=torch.device("cuda" if torch.cuda.is_available() else "cpu"),
    fp16=False,
    fp16_opt_level='O1',
    max_grad_norm=1.0,
    start_step=0,
    start_epoch=0,
    output_dir='./model_output',
    logging_steps=50,
    save_steps=100,
    evaluate_during_training=True
)

# Evaluation
results = {}
# if args.do_eval and args.local_rank in [-1, 0]:
#         checkpoint_prefix = 'checkpoint-best-acc/model.bin'
#         output_dir = os.path.join(args.output_dir, '{}'.format(checkpoint_prefix))  
#         model.load_state_dict(torch.load(output_dir))      
#         model.to(args.device)
#         result=evaluate(args, model, tokenizer)
#         logger.info("***** Eval results *****")
#         for key in sorted(result.keys()):
#             logger.info("  %s = %s", key, str(round(result[key],4)))
        
# if args.do_test and args.local_rank in [-1, 0]:
#         checkpoint_prefix = 'checkpoint-best-acc/model.bin'
#         output_dir = os.path.join(args.output_dir, '{}'.format(checkpoint_prefix))  
#         model.load_state_dict(torch.load(output_dir))                  
#         model.to(args.device)
#         test(args, model, tokenizer)
