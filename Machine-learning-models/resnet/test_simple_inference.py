#!/usr/bin/env python3
"""
Simple test script to debug the inference hanging issue
"""

import time
import torch
import torch.nn as nn
import torchvision
import torchvision.transforms as transforms
import torchvision.models as models
from torch.utils.data import DataLoader
import logging

# Set up basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def test_basic_inference():
    """Test basic inference with minimal setup"""
    print("Starting basic inference test...")
    
    # Device
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    
    # Simple transform
    transform = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    
    # Load just a small subset
    print("Loading CIFAR-10...")
    testset = torchvision.datasets.CIFAR10(root='./data', train=False, download=False, transform=transform)
    
    # Very small batch size for testing
    testloader = DataLoader(testset, batch_size=1, shuffle=False, num_workers=0)
    print(f"Dataset loaded: {len(testset)} samples")
    
    # Load model
    print("Loading ResNet18...")
    model = models.resnet18(pretrained=True)
    model = model.to(device)
    model.eval()
    print("Model loaded")
    
    # Test just the first few batches
    print("Starting inference test (first 5 batches only)...")
    
    with torch.no_grad():
        for batch_idx, (inputs, targets) in enumerate(testloader):
            print(f"Processing batch {batch_idx}...")
            
            start_time = time.time()
            inputs = inputs.to(device)
            print(f"Data moved to device in {time.time() - start_time:.3f}s")
            
            start_time = time.time()
            outputs = model(inputs)
            inf_time = time.time() - start_time
            
            print(f"Inference completed in {inf_time:.3f}s, output shape: {outputs.shape}")
            
            if batch_idx >= 4:  # Test only first 5 batches
                print("Test completed successfully!")
                break
                
    return True

if __name__ == "__main__":
    try:
        test_basic_inference()
        print("All tests passed!")
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()