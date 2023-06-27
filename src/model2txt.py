#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import onnx
import torch
import argparse
import torchvision
import numpy as np
import torch.nn as nn
from einops import repeat
import torch.optim as optim
from einops.layers.torch import Rearrange
import torchvision.transforms as transforms

sys.path.append('.')

from src.vit_model import *

parser = argparse.ArgumentParser(add_help=True)

parser.add_argument("--model", type=str, default="../result/data_1/model.pth")

args = parser.parse_args()

import torch.onnx 

#Function to Convert to ONNX 
def Convert_ONNX(model, filename, input_size = (3, 32, 32)): 

    # set the model to inference mode 
    model.eval() 

    # Let's create a dummy input tensor  
    dummy_input = torch.randn(1, *input_size, requires_grad=True)  

    # Export the model   
    torch.onnx.export(model,         # model being run 
         dummy_input,       # model input (or a tuple for multiple inputs) 
         filename,       # where to save the model  
         export_params=True,  # store the trained parameter weights inside the model file 
         opset_version=10,    # the ONNX version to export the model to 
         do_constant_folding=True,  # whether to execute constant folding for optimization 
         input_names = ['modelInput'],   # the model's input names 
         output_names = ['modelOutput'], # the model's output names 
         dynamic_axes={'modelInput' : {0 : 'batch_size'},    # variable length axes 
                                'modelOutput' : {0 : 'batch_size'}}) 
    print(" ") 
    print('Model has been converted to ONNX')

if __name__ == "__main__":
    net = ViT(
        image_size=32,
        patch_size=4,
        n_classes=10,
        dim=256,
        depth=3,
        n_heads=4,
        mlp_dim = 256
    ).to('cpu')
    print(args.model)
    net.load_state_dict(torch.load(args.model, map_location=torch.device('cpu')))
    print(net)

    Convert_ONNX(net, f"{os.path.dirname(args.model)}/model.onnx")

    onnx_model = onnx.load(f"{os.path.dirname(args.model)}/model.onnx")
    onnx.checker.check_model(onnx_model)
    