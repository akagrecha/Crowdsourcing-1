import os
import re
import math
import pathlib
import random
from typing import Optional, Dict
from tqdm import tqdm
import json
from collections import defaultdict

import torch
from torch.utils.data import Dataset
import transformers
from torch.nn.utils.rnn import pad_sequence
from torch.utils.data import DataLoader


device = 'cuda:0' if torch.cuda.is_available() else 'cpu'

class WorkerDataset(Dataset):
    """Dataset for supervised fine-tuning."""

    def __init__(self, data_path, tokenizer, evidence_llm=[], evalmode=False, task="halueval", split=1.0):
        super(WorkerDataset, self).__init__()
        with open(data_path) as fin:
            self.data = json.load(fin)
        self.tokenizer = tokenizer
        self.evidence_llm = evidence_llm
        self.evalmode = evalmode
        self.task = task

        if split < 1.0:
            portion = int(len(self.data) * split)
            if self.evalmode:
                self.data = self.data[portion:] if portion > 0 else self.data[:portion]
            else:
                self.data = self.data[:portion] if portion > 0 else self.data[portion:]

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx) -> Dict[str, torch.Tensor]:
        return self.preprocessing(self.data[idx])

    def preprocessing(self, data):
        datasamples = []
        labels = []
        for llm in self.evidence_llm:
            datasample = []
            for cllm in self.evidence_llm:
                if cllm != llm:
                    datasample.append(data[cllm][0])
            datasamples.append(datasample)
            if self.evalmode:
                if self.task == "halueval":
                    labels.append(1 if data['ref'] == 'yes' else 0)
                elif self.task == "crosscheck":
                    labels.append(data['ref'])
            else:
                labels.append(data[llm][0])
        if self.task == "halueval":
            input_str = "Query: {}\nResponse: {}\nIs there any non-factual or hallucinated information in the response?".format(data["query"], data["response"])
        elif self.task == "crosscheck":
            input_str = "Passage: {}\nIs there any non-factual or hallucinated information in the passage?".format(data["query"])
        prompt_inputs = self.tokenizer(input_str, return_tensors="pt")["input_ids"][0]
        return prompt_inputs, torch.tensor(datasamples), torch.tensor(labels)


def collate_fn(batch):
    input_ids, workers, labels = zip(*batch)
    input_ids = pad_sequence(input_ids, batch_first=True, padding_value=0).to(device)
    attn_mask = input_ids != 0
    inputs = {"input_ids": input_ids, "attention_mask": attn_mask}
    workers = torch.stack(workers).to(device)
    labels = torch.stack(labels).to(device)
    return inputs, workers, labels
