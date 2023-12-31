#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import json
import torch
import argparse
import torchvision
import torch.nn as nn
from einops import repeat
import torch.optim as optim
from einops.layers.torch import Rearrange
import torchvision.transforms as transforms

sys.path.append(".")

from src.cnn import *
from src.vit_model import *

parser = argparse.ArgumentParser(add_help=True)

parser.add_argument("--zipfile", type=str, default="../result/data_1/UNITV_Training.zip")
parser.add_argument("--batch_size", type=int, default=2)
parser.add_argument("--num_epochs", type=int, default=10)
parser.add_argument("--size", type=int, default=512)
parser.add_argument("--learning_rate", type=float, default=0.01)

args = parser.parse_args()

BATCH_SIZE = args.batch_size
SIZE = 512
NUM_EPOCHS = args.num_epochs

class OwnDataset(Dataset):
    def __init__(self, train_df, input_size, phase='train',transform=None):
        super().__init__()
        self.train_df = train_df
        image_paths = train_df["path"].to_list()
        self.input_size = input_size
        self.len = len(image_paths)
        self.transform = transform
        self.phase = phase

    def __len__(self):
        return self.len

    def __getitem__(self, index):
        image_path = self.train_df["path"].to_list()[index]
        
        image = Image.open(image_path)
        image = image.resize((32, 32))
        image = np.array(image).astype(np.float32).transpose(2, 1, 0) # Dataloader で使うために転置する
        label = self.train_df["label"].apply(lambda x : int(x)).to_list()[index]
        return image, label


if __name__ == "__main__":
    data_df = load_zip(args.zipfile)

    image_dataset = OwnDataset(data_df, (SIZE, SIZE))
    train_dataset, test_dataset = torch.utils.data.random_split( image_dataset, [int(len(image_dataset))-20, 20])

    assert len(train_dataset)%BATCH_SIZE == 0 and len(test_dataset)%BATCH_SIZE == 0
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=2, pin_memory=True)
    test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=2, pin_memory=True)

    train_loader = DeviceDataLoader(train_loader, batch_size=BATCH_SIZE, shuffle=True, num_workers=2, pin_memory=True)
    test_loader = DeviceDataLoader(test_loader, batch_size=BATCH_SIZE, shuffle=True, num_workers=2, pin_memory=True)


    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(device)

    params = {}

    params["IMAGE_SIZE"] = 32
    params["PATCH_SIZE"] = 4
    params["N_CLASSES"] = 4
    params["DIM"] = 128
    params["DEPTH"] = 3
    params["N_HEADS"] = 4
    params["MLP_DIM"] = 128

    with open(f"{os.path.dirname(args.zipfile)}/params.json", mode="w") as f:
        json.dump(params, f, indent=4)

    net = ViT(
        image_size=params["IMAGE_SIZE"],
        patch_size=params["PATCH_SIZE"],
        n_classes=params["N_CLASSES"],
        dim=params["DIM"],
        depth=params["DEPTH"],
        n_heads=params["N_HEADS"],
        mlp_dim = params["MLP_DIM"]
    ).to(device)

    print(net)

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.SGD(net.parameters(), lr=0.01, momentum=0.9)

    epochs = 10
    for epoch in range(0, epochs):
        epoch_train_loss = 0
        epoch_train_acc = 0
        epoch_test_loss = 0
        epoch_test_acc = 0

        net.train()
        for data in train_loader:
            inputs, labels = data[0].to(device), data[1].to(device)
            print(inputs)
            print(labels)
            optimizer.zero_grad()

            outputs = net(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            epoch_train_loss += loss.item()/len(train_loader)
            acc = (outputs.argmax(dim=1) == labels).float().mean()
            epoch_train_acc += acc/len(train_loader)

            del inputs
            del outputs
            del loss

        net.eval()
        with torch.no_grad():
            for data in test_loader:
                inputs, labels = data[0].to(device), data[1].to(device)
                outputs = net(inputs)
                loss = criterion(outputs, labels)
                epoch_test_loss += loss.item()/len(test_loader)
                test_acc = (outputs.argmax(dim=1) == labels).float().mean()
                epoch_test_acc += test_acc/len(test_loader)

        print(f'Epoch {epoch+1} : train acc. {epoch_train_acc:.2f} train loss {epoch_train_loss:.2f}')
        print(f'Epoch {epoch+1} : test acc. {epoch_test_acc:.2f} test loss {epoch_test_loss:.2f}')
    
    torch.save(net.to('cpu').state_dict(), f"{os.path.dirname(args.zipfile)}/model.pth")