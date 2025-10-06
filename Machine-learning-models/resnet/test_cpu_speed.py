#!/usr/bin/env python3
"""
Ultra-lightweight CPU inference test using the smallest possible setup
"""

import time
import torch
import torch.nn as nn
import torchvision.transforms as transforms
import torchvision.models as models
import numpy as np

# CPU optimizations
torch.set_num_threads(1)
import os
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

class TinyResNet(nn.Module):
    """Extremely small ResNet-like model for testing"""
    def __init__(self, num_classes=10):
        super(TinyResNet, self).__init__()
        self.conv1 = nn.Conv2d(3, 16, kernel_size=3, stride=1, padding=1)
        self.bn1 = nn.BatchNorm2d(16)
        self.relu = nn.ReLU(inplace=True)
        
        self.conv2 = nn.Conv2d(16, 32, kernel_size=3, stride=2, padding=1)
        self.bn2 = nn.BatchNorm2d(32)
        
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(32, num_classes)
        
    def forward(self, x):
        x = self.relu(self.bn1(self.conv1(x)))
        x = self.relu(self.bn2(self.conv2(x)))
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.fc(x)
        return x

def test_tiny_model():
    """Test with an extremely small model"""
    print("Testing ultra-lightweight model for CPU inference...")
    
    device = torch.device('cpu')  # Force CPU
    print(f"Using device: {device}")
    
    # Create tiny model
    model = TinyResNet(num_classes=10)
    model.eval()
    print("Tiny model created")
    
    # Create some dummy data (very small)
    batch_size = 4
    num_batches = 20
    
    print(f"Testing with {num_batches} batches of size {batch_size}")
    
    total_time = 0
    total_examples = 0
    
    with torch.no_grad():
        for i in range(num_batches):
            print(f"Batch {i+1}/{num_batches}")
            
            # Create random input (small size: 32x32)
            inputs = torch.randn(batch_size, 3, 32, 32)
            
            start_time = time.time()
            outputs = model(inputs)
            end_time = time.time()
            
            batch_time = end_time - start_time
            total_time += batch_time
            total_examples += batch_size
            
            print(f"  Batch time: {batch_time:.4f}s, Output shape: {outputs.shape}")
    
    throughput = total_examples / total_time
    print(f"\nResults:")
    print(f"Total time: {total_time:.4f}s")
    print(f"Total examples: {total_examples}")
    print(f"Throughput: {throughput:.2f} examples/sec")
    
    return throughput

def test_resnet18_small():
    """Test ResNet18 with very small inputs"""
    print("\nTesting ResNet18 with tiny inputs...")
    
    device = torch.device('cpu')
    
    # Load ResNet18
    model = models.resnet18(pretrained=False)  # No pretrained to be faster
    model.eval()
    print("ResNet18 loaded (no pretrained weights)")
    
    batch_size = 2  # Very small batch
    num_batches = 5   # Just a few batches
    
    total_time = 0
    total_examples = 0
    
    with torch.no_grad():
        for i in range(num_batches):
            print(f"Batch {i+1}/{num_batches}")
            
            # Very small input size
            inputs = torch.randn(batch_size, 3, 64, 64)  # 64x64 instead of 224x224
            
            start_time = time.time()
            outputs = model(inputs)
            end_time = time.time()
            
            batch_time = end_time - start_time
            total_time += batch_time
            total_examples += batch_size
            
            print(f"  Batch time: {batch_time:.4f}s, Output shape: {outputs.shape}")
    
    throughput = total_examples / total_time
    print(f"\nResNet18 Results:")
    print(f"Total time: {total_time:.4f}s")
    print(f"Total examples: {total_examples}")
    print(f"Throughput: {throughput:.2f} examples/sec")
    
    return throughput

if __name__ == "__main__":
    print("CPU Inference Speed Test")
    print("=" * 40)
    
    # Test tiny custom model
    tiny_throughput = test_tiny_model()
    
    # Test ResNet18 with small inputs
    resnet_throughput = test_resnet18_small()
    
    print(f"\nComparison:")
    print(f"Tiny model: {tiny_throughput:.2f} examples/sec")
    print(f"ResNet18:   {resnet_throughput:.2f} examples/sec")