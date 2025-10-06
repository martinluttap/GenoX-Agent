import time
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision
import torchvision.transforms as transforms
import torchvision.models as models
from torch.utils.data import DataLoader
import numpy as np
import logging
import os
import csv
from datetime import datetime
import signal
import sys

# CPU optimizations
torch.set_num_threads(1)  # Often faster for CPU inference
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

# ------------------------
# Global variables for graceful shutdown
# ------------------------
running = True

def signal_handler(sig, frame):
    global running
    print("\nReceived shutdown signal. Stopping gracefully...")
    logging.info("Received shutdown signal. Stopping gracefully...")
    running = False

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ------------------------
# Logging setup
# ------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    filename="resnet_inference_only.log",
    filemode="a"
)

# ------------------------
# CSV file for inference throughput logging
# ------------------------
inference_csv = "resnet_inference_throughput.csv"

def initialize_csv_file():
    """Initialize CSV file with headers if it doesn't exist"""
    if not os.path.exists(inference_csv):
        with open(inference_csv, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'iteration', 'inference_time_sec', 'inference_throughput_examples_per_sec', 
                           'num_examples', 'accuracy', 'batch_size', 'device'])

def log_inference_throughput(timestamp, iteration, inf_time, throughput, num_examples, accuracy, batch_size, device):
    """Log inference throughput to CSV"""
    with open(inference_csv, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, iteration, inf_time, throughput, num_examples, accuracy, batch_size, device])

# ------------------------
# Pre-trained Model Setup
# ------------------------
def load_pretrained_model(device, use_pretrained=False):
    """Load a ResNet model optimized for CPU"""
    if use_pretrained:
        print("Loading pre-trained ResNet18 model (CPU optimized)...")
        logging.info("Loading pre-trained ResNet18 model (CPU optimized)...")
        model = models.resnet18(pretrained=True)
    else:
        print("Loading ResNet18 model without pretrained weights (faster loading)...")
        logging.info("Loading ResNet18 model without pretrained weights (faster loading)...")
        model = models.resnet18(pretrained=False)
    
    model = model.to(device)
    model.eval()  # Set to evaluation mode
    
    # CPU optimizations
    if device.type == 'cpu':
        print("Applying CPU optimizations...")
        logging.info("CPU optimizations applied (single thread)")
    
    print("ResNet18 model loaded successfully!")
    logging.info("ResNet18 model loaded successfully!")
    
    return model

# ------------------------
# Dataset and Model Setup
# ------------------------
def setup_dataset():
    """Setup ImageNet validation dataset for inference"""
    print("Setting up dataset for ResNet inference...")
    logging.info("Setting up dataset for ResNet inference...")
    
    # Device configuration
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    logging.info(f"Using device: {device}")
    
    # Smaller image size for faster CPU inference (instead of 224x224)
    # This will be faster but less accurate since model was trained on 224x224
    transform = transforms.Compose([
        transforms.Resize(128),  # Much smaller than standard 256
        transforms.CenterCrop(112),  # Much smaller than standard 224
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    
    # Use CIFAR-10 as a substitute dataset (will be resized to 112x112 for faster CPU inference)
    print("Downloading/Loading CIFAR-10 dataset (will be resized for ImageNet-trained model)...")
    testset = torchvision.datasets.CIFAR10(root='./data', train=False, download=True, transform=transform)
    
    # Very small batch size for CPU inference (CPU works better with smaller batches)
    batch_size = 4 if device.type == 'cpu' else 32  # Even smaller batch for CPU
    testloader = DataLoader(testset, batch_size=batch_size, shuffle=False, num_workers=0)  # No multiprocessing to avoid shared memory issues
    
    print(f"Dataset loaded - Total test samples: {len(testset)}, Batch size: {testloader.batch_size}")
    print(f"Image size: 112x112 (reduced from 224x224 for faster CPU inference)")
    logging.info(f"Dataset loaded - Total test samples: {len(testset)}, Batch size: {testloader.batch_size}")
    logging.info(f"Using reduced image size 112x112 for faster CPU inference")
    
    print("Dataset loaded successfully!")
    logging.info("Dataset loaded successfully!")
    
    return testloader, device

# No training function needed - using pre-trained model

def run_inference_iteration(model, testloader, device, iteration, timeout_seconds=120):
    """Run one inference iteration and return throughput metrics"""
    logging.info(f"Starting inference iteration {iteration}...")
    print(f"Starting inference iteration {iteration}...")
    
    model.eval()
    total_examples = 0
    
    # Overall timeout for the entire iteration
    iteration_start_time = time.time()
    
    # For pre-trained ImageNet model on CIFAR-10, we'll just measure throughput
    # Note: Accuracy won't be meaningful since the classes don't match
    
    # Measure inference throughput
    start_inf = time.time()
    
    with torch.no_grad():
        batch_start_time = time.time()
        for batch_idx, (inputs, targets) in enumerate(testloader):
            if not running:
                return None
            
            # Check for overall iteration timeout
            current_time = time.time()
            if current_time - iteration_start_time > timeout_seconds:
                logging.error(f"Iteration {iteration} timeout after {timeout_seconds} seconds, breaking...")
                print(f"Iteration {iteration} timeout after {timeout_seconds} seconds, breaking...")
                break
            
            # Check for timeout on individual batches (should not take more than 30 seconds per batch)
            if current_time - batch_start_time > 30:
                logging.error(f"Batch {batch_idx} timeout after 30 seconds, breaking...")
                print(f"Batch {batch_idx} timeout after 30 seconds, breaking...")
                break
            
            # Add debug logging every few batches
            if batch_idx % 10 == 0:
                logging.info(f"Processing batch {batch_idx}, total examples so far: {total_examples}")
                print(f"Processing batch {batch_idx}, total examples so far: {total_examples}")
                
            inputs = inputs.to(device)
            outputs = model(inputs)  # Just run inference, don't evaluate accuracy
            total_examples += inputs.size(0)
            
            # Reset batch timer for next batch
            batch_start_time = time.time()
            
            # Add a small check to prevent infinite loops
            if batch_idx > 200:  # Reasonable limit for CIFAR-10 test set
                logging.warning(f"Breaking early at batch {batch_idx} to prevent hanging")
                break
    
    end_inf = time.time()
    
    if not running:
        return None
    
    inf_time = end_inf - start_inf
    inf_throughput = total_examples / inf_time
    
    timestamp = datetime.now().isoformat()
    
    logging.info(f"Inference iteration {iteration} completed")
    logging.info(f"Inference time: {inf_time:.2f} sec")
    logging.info(f"Inference throughput: {inf_throughput:.2f} examples/sec")
    
    print(f"Iteration {iteration} - Throughput: {inf_throughput:.2f} examples/sec, Time: {inf_time:.2f}s")
    
    # Log to CSV (accuracy set to N/A since we're using mismatched dataset/model)
    batch_size = testloader.batch_size
    log_inference_throughput(timestamp, iteration, inf_time, inf_throughput, total_examples, "N/A", batch_size, str(device))
    
    return inf_throughput

def main():
    """Main execution loop"""
    global running
    
    print("Starting ResNet continuous inference benchmark...")
    logging.info("Starting ResNet continuous inference benchmark...")
    
    # Step 1: Initialize CSV file
    initialize_csv_file()
    
    # Step 2: Setup dataset
    testloader, device = setup_dataset()
    
    # Step 3: Load model (no training needed)
    # Use pretrained=False for faster loading on CPU
    use_pretrained = False  # Set to True if you need pretrained weights
    model = load_pretrained_model(device, use_pretrained=use_pretrained)
    
    print(f"Starting continuous inference on CIFAR-10 test set with pre-trained ResNet18...")
    logging.info(f"Starting continuous inference on CIFAR-10 test set with pre-trained ResNet18")
    
    # Step 4: Continuous inference loop
    iteration = 1
    total_throughput = 0
    
    while running:
        try:
            # Run inference with timeout
            throughput = run_inference_iteration(model, testloader, device, iteration, timeout_seconds=120)
            
            if throughput is None:  # Stopped gracefully
                break
                
            total_throughput += throughput
            avg_throughput = total_throughput / iteration
            
            if iteration % 10 == 0:  # Print summary every 10 iterations
                print(f"--- After {iteration} iterations ---")
                print(f"Average Throughput: {avg_throughput:.2f} examples/sec")
                print(f"Latest Throughput: {throughput:.2f} examples/sec")
            
            iteration += 1
            
            # Small pause between iterations
            time.sleep(0.1)
            
        except KeyboardInterrupt:
            print("\nKeyboard interrupt received. Stopping...")
            break
        except Exception as e:
            logging.error(f"Error in iteration {iteration}: {str(e)}")
            print(f"Error in iteration {iteration}: {str(e)}")
            time.sleep(5)  # Wait before retrying
    
    if iteration > 1:
        final_avg = total_throughput / (iteration - 1)
        print(f"\nFinal Results:")
        print(f"Total iterations: {iteration - 1}")
        print(f"Average throughput: {final_avg:.2f} examples/sec")
    
    print(f"ResNet inference benchmark stopped. Data saved to {inference_csv}")
    logging.info("ResNet inference benchmark stopped. Data saved to CSV file.")

if __name__ == "__main__":
    main()