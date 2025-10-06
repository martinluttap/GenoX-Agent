import time
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision
import torchvision.transforms as transforms
from torchvision.models import detection
from torch.utils.data import DataLoader, Dataset
import numpy as np
import logging
import os
import csv
from datetime import datetime
import signal
import sys
from PIL import Image
import json
import requests
from io import BytesIO
import random
import threading
import queue
from collections import deque
import psutil

# CPU optimizations - use all available cores
import multiprocessing

# Respect environment variables if set, otherwise use all cores
def get_optimal_thread_count():
    """Get optimal thread count, respecting environment variables"""
    omp_threads = os.environ.get('OMP_NUM_THREADS')
    if omp_threads and omp_threads != '0':
        return int(omp_threads)
    
    # If set to 0 or not set, use all available cores
    return multiprocessing.cpu_count()

num_cores = get_optimal_thread_count()
print(f"Using {num_cores} CPU threads for optimization")

# Set threading for PyTorch and linear algebra libraries
torch.set_num_threads(num_cores)
# Only set environment variables if they're not already set to 0 (use all)
if os.environ.get('OMP_NUM_THREADS', '0') == '0':
    os.environ['OMP_NUM_THREADS'] = str(num_cores)
if os.environ.get('MKL_NUM_THREADS', '0') == '0':
    os.environ['MKL_NUM_THREADS'] = str(num_cores)

# Enable parallel processing optimizations
torch.set_grad_enabled(True)
if hasattr(torch, 'use_deterministic_algorithms'):
    torch.use_deterministic_algorithms(False)  # Allow non-deterministic for better performance

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
    filename="ssd_benchmark.log",
    filemode="a"
)

logger = logging.getLogger(__name__)

# Also log to console
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(console_handler)

# ------------------------
# CSV files for logging
# ------------------------
training_csv = "ssd_training_throughput.csv"
inference_csv = "ssd_inference_throughput.csv"

def initialize_csv_files():
    """Initialize CSV files with headers if they don't exist"""
    if not os.path.exists(training_csv):
        with open(training_csv, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'epoch', 'batch_idx', 'training_time_sec', 
                           'training_throughput_examples_per_sec', 'batch_size', 'loss', 
                           'device', 'lr', 'memory_usage_mb'])

    if not os.path.exists(inference_csv):
        with open(inference_csv, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'iteration', 'inference_time_sec', 
                           'inference_throughput_examples_per_sec', 'num_examples', 
                           'avg_confidence', 'batch_size', 'device', 'memory_usage_mb'])

def log_training_throughput(timestamp, epoch, batch_idx, train_time, throughput, 
                          batch_size, loss, device, lr, memory_usage):
    """Log training throughput to CSV"""
    with open(training_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, epoch, batch_idx, train_time, throughput, 
                        batch_size, loss, device, lr, memory_usage])

def log_inference_throughput(timestamp, iteration, inf_time, throughput, num_examples, 
                           avg_confidence, batch_size, device, memory_usage):
    """Log inference throughput to CSV"""
    with open(inference_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, iteration, inf_time, throughput, num_examples, 
                        avg_confidence, batch_size, device, memory_usage])

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

# ------------------------
# Synthetic Dataset for SSD Training/Testing
# ------------------------
class SyntheticObjectDetectionDataset(Dataset):
    """Synthetic dataset for object detection to avoid large downloads"""
    
    def __init__(self, num_samples=1000, image_size=(300, 300), num_classes=20, transform=None):
        self.num_samples = num_samples
        self.image_size = image_size
        self.num_classes = num_classes
        self.transform = transform
        
    def __len__(self):
        return self.num_samples
    
    def __getitem__(self, idx):
        # Generate synthetic image more efficiently
        # Use normal distribution centered around 0.5 for more realistic images
        image = torch.randn(3, self.image_size[0], self.image_size[1]) * 0.2 + 0.5
        image = torch.clamp(image, 0, 1)
        
        # Generate synthetic bounding boxes and labels (fewer boxes for faster processing)
        num_boxes = random.randint(1, 3)  # Reduced from 1-5 to 1-3
        boxes = []
        labels = []
        
        # Pre-calculate some values to avoid repeated computations
        width, height = self.image_size
        
        for _ in range(num_boxes):
            # Generate boxes more efficiently
            x1 = random.uniform(0, 0.6) * width
            y1 = random.uniform(0, 0.6) * height
            box_width = random.uniform(0.15, 0.35) * width
            box_height = random.uniform(0.15, 0.35) * height
            
            x2 = min(x1 + box_width, width)
            y2 = min(y1 + box_height, height)
            
            boxes.append([x1, y1, x2, y2])
            labels.append(random.randint(1, self.num_classes))
        
        boxes = torch.tensor(boxes, dtype=torch.float32)
        labels = torch.tensor(labels, dtype=torch.int64)
        
        # Create target dict as expected by torchvision detection models
        target = {
            'boxes': boxes,
            'labels': labels
        }
        
        if self.transform:
            # Convert tensor to PIL Image for transforms
            image_pil = transforms.ToPILImage()(image)
            image = self.transform(image_pil)
        
        return image, target

# ------------------------
# SSD Model Setup
# ------------------------
class SSDModel:
    def __init__(self, device, num_classes=91, pretrained=False):
        self.device = device
        self.num_classes = num_classes
        
        logger.info(f"Initializing SSD model on {device}")
        
        # Use torchvision's SSD model
        if pretrained:
            logger.info("Loading pre-trained SSD MobileNet model...")
            self.model = detection.ssd300_vgg16(pretrained=True, num_classes=num_classes)
        else:
            logger.info("Loading SSD MobileNet model without pretrained weights...")
            self.model = detection.ssd300_vgg16(pretrained=False, num_classes=num_classes)
        
        self.model = self.model.to(device)
        
        # Setup optimizer with higher learning rate for faster convergence
        self.optimizer = torch.optim.SGD(
            self.model.parameters(), 
            lr=0.01,  # Increased from 0.001 for faster training
            momentum=0.9, 
            weight_decay=0.0001  # Reduced weight decay
        )
        
        # Setup learning rate scheduler
        self.scheduler = torch.optim.lr_scheduler.StepLR(self.optimizer, step_size=3, gamma=0.1)
        
        logger.info("SSD model initialized successfully")
    
    def train_epoch(self, dataloader, epoch):
        """Train the model for one epoch"""
        self.model.train()
        
        epoch_loss = 0.0
        epoch_samples = 0
        batch_times = []
        
        logger.info(f"Starting training epoch {epoch}")
        
        for batch_idx, (images, targets) in enumerate(dataloader):
            if not running:
                break
                
            batch_start_time = time.time()
            
            # Move data to device
            images = [img.to(self.device) for img in images]
            targets = [{k: v.to(self.device) for k, v in t.items()} for t in targets]
            
            # Zero gradients
            self.optimizer.zero_grad()
            
            # Forward pass
            loss_dict = self.model(images, targets)
            losses = sum(loss for loss in loss_dict.values())
            
            # Backward pass
            losses.backward()
            self.optimizer.step()
            
            batch_end_time = time.time()
            batch_time = batch_end_time - batch_start_time
            batch_throughput = len(images) / batch_time
            
            epoch_loss += losses.item()
            epoch_samples += len(images)
            batch_times.append(batch_time)
            
            # Log batch metrics
            timestamp = datetime.now().isoformat()
            current_lr = self.optimizer.param_groups[0]['lr']
            memory_usage = get_memory_usage()
            
            log_training_throughput(
                timestamp, epoch, batch_idx, batch_time, batch_throughput,
                len(images), losses.item(), str(self.device), current_lr, memory_usage
            )
            
            if batch_idx % 5 == 0:  # Report more frequently for better feedback
                logger.info(f"Epoch {epoch}, Batch {batch_idx}: Loss = {losses.item():.4f}, "
                           f"Throughput = {batch_throughput:.2f} examples/sec, "
                           f"Processed {epoch_samples} samples")
        
        self.scheduler.step()
        
        avg_loss = epoch_loss / len(dataloader)
        avg_throughput = epoch_samples / sum(batch_times) if batch_times else 0
        
        logger.info(f"Epoch {epoch} completed: Avg Loss = {avg_loss:.4f}, "
                   f"Avg Throughput = {avg_throughput:.2f} examples/sec")
        
        return avg_loss, avg_throughput
    
    def inference_iteration(self, dataloader, iteration):
        """Run one inference iteration"""
        self.model.eval()
        
        total_samples = 0
        total_confidence = 0.0
        confidence_count = 0
        
        iteration_start_time = time.time()
        
        with torch.no_grad():
            for batch_idx, (images, targets) in enumerate(dataloader):
                if not running:
                    break
                
                # Move images to device
                images = [img.to(self.device) for img in images]
                
                # Run inference
                outputs = self.model(images)
                
                # Calculate average confidence scores
                for output in outputs:
                    if 'scores' in output and len(output['scores']) > 0:
                        total_confidence += output['scores'].mean().item()
                        confidence_count += 1
                
                total_samples += len(images)
                
                # Break early for smaller test sets
                if batch_idx > 50:  # Limit inference batches
                    break
        
        inference_time = time.time() - iteration_start_time
        throughput = total_samples / inference_time if inference_time > 0 else 0
        avg_confidence = total_confidence / confidence_count if confidence_count > 0 else 0
        
        # Log inference metrics
        timestamp = datetime.now().isoformat()
        memory_usage = get_memory_usage()
        batch_size = dataloader.batch_size
        
        log_inference_throughput(
            timestamp, iteration, inference_time, throughput, total_samples,
            avg_confidence, batch_size, str(self.device), memory_usage
        )
        
        logger.info(f"Inference iteration {iteration}: Throughput = {throughput:.2f} examples/sec, "
                   f"Avg Confidence = {avg_confidence:.3f}")
        
        return throughput, avg_confidence

# ------------------------
# Dataset Setup
# ------------------------
def setup_datasets(batch_size=None, num_samples=1000):
    """Setup training and test datasets with optimized batch sizes"""
    logger.info("Setting up synthetic object detection datasets...")
    num_cores = multiprocessing.cpu_count()
    # Auto-determine optimal batch size based on available cores if not specified
    if batch_size is None:
        #num_cores = multiprocessing.cpu_count()
        # Scale batch size with number of cores, but cap it for memory reasons
        batch_size = min(max(num_cores * 2, 8), 32)
        logger.info(f"Auto-selected batch size: {batch_size} (based on {num_cores} CPU cores)")
    
    # Use smaller image size for faster processing on CPU but still effective
    transform = transforms.Compose([
        transforms.Resize((224, 224)),  # Reduced from 300x300 for faster processing
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    # Create synthetic datasets
    train_dataset = SyntheticObjectDetectionDataset(
        num_samples=num_samples, 
        image_size=(224, 224),  # Reduced image size
        transform=transform
    )
    
    test_dataset = SyntheticObjectDetectionDataset(
        num_samples=min(500, num_samples//3),  # Increased test set size
        image_size=(224, 224), 
        transform=transform
    )
    
    # Custom collate function for object detection
    def collate_fn(batch):
        return tuple(zip(*batch))
    
    # Enable multiprocessing with optimal number of workers
    num_workers = min(num_cores, 8)  # Cap at 8 to avoid too many processes
    
    # Create data loaders with multiprocessing enabled
    train_loader = DataLoader(
        train_dataset, 
        batch_size=batch_size, 
        shuffle=True, 
        num_workers=num_workers,
        collate_fn=collate_fn,
        pin_memory=False,  # CPU only, no need for pinned memory
        prefetch_factor=2,  # Prefetch batches for better performance
        persistent_workers=True if num_workers > 0 else False
    )
    
    test_loader = DataLoader(
        test_dataset, 
        batch_size=batch_size, 
        shuffle=False, 
        num_workers=num_workers,
        collate_fn=collate_fn,
        pin_memory=False,
        prefetch_factor=2,
        persistent_workers=True if num_workers > 0 else False
    )
    
    logger.info(f"Datasets created - Train: {len(train_dataset)}, Test: {len(test_dataset)}")
    logger.info(f"Batch size: {batch_size}")
    
    return train_loader, test_loader

# ------------------------
# Benchmark Functions
# ------------------------
class SSDInferenceBenchmark:
    def __init__(self, model_path=None, device=None):
        """Initialize SSD benchmark"""
        self.device = device or torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = None
        self.test_loader = None
        self.throughput_history = deque(maxlen=100)
        
        logger.info(f"Initializing SSD Benchmark on {self.device}")
        
        # Setup datasets with optimized batch size
        _, self.test_loader = setup_datasets(batch_size=None, num_samples=400)
        
        # Load or create model
        self.model = SSDModel(self.device, pretrained=False)
        
        if model_path and os.path.exists(model_path):
            logger.info(f"Loading model from {model_path}")
            self.model.model.load_state_dict(torch.load(model_path, map_location=self.device))
        
    def continuous_inference_benchmark(self, duration_seconds=None, report_interval=10):
        """Run continuous inference benchmark - if duration_seconds is None, runs forever"""
        if duration_seconds is None:
            logger.info("Starting CONTINUOUS INFERENCE (runs forever until stopped)...")
            logger.info("Press Ctrl+C to stop gracefully")
            infinite_mode = True
        else:
            logger.info(f"Starting continuous inference for {duration_seconds} seconds...")
            infinite_mode = False
        
        start_time = time.time()
        end_time = start_time + duration_seconds if duration_seconds else float('inf')
        
        iteration = 1
        total_throughput = 0
        last_report = start_time
        
        try:
            while (time.time() < end_time or infinite_mode) and running:
                throughput, avg_confidence = self.model.inference_iteration(self.test_loader, iteration)
                
                total_throughput += throughput
                self.throughput_history.append(throughput)
                
                # Report progress
                current_time = time.time()
                if current_time - last_report >= report_interval:
                    elapsed = current_time - start_time
                    avg_throughput = total_throughput / iteration
                    
                    if infinite_mode:
                        logger.info(f"🔄 Continuous Inference - Iteration {iteration}: "
                                   f"Avg throughput: {avg_throughput:.2f} examples/sec, "
                                   f"Latest: {throughput:.2f} examples/sec, "
                                   f"Uptime: {elapsed/60:.1f} mins")
                    else:
                        logger.info(f"Progress: {elapsed:.1f}s elapsed, Avg throughput: {avg_throughput:.2f} examples/sec")
                    
                    last_report = current_time
                
                iteration += 1
                
                # In infinite mode, add a smaller pause to maintain high throughput
                if infinite_mode:
                    time.sleep(0.01)  # Very small pause for infinite mode
                else:
                    time.sleep(0.1)  # Standard pause for timed mode
                    
        except KeyboardInterrupt:
            logger.info("\n🛑 Continuous inference stopped by user (Ctrl+C)")
        
        total_time = time.time() - start_time
        final_avg_throughput = total_throughput / (iteration - 1) if iteration > 1 else 0
        
        logger.info(f"\n📊 Continuous inference session ended:")
        logger.info(f"  Total time: {total_time/60:.1f} minutes ({total_time:.1f} seconds)")
        logger.info(f"  Total iterations: {iteration - 1}")
        logger.info(f"  Average throughput: {final_avg_throughput:.2f} examples/sec")
        if len(self.throughput_history) > 0:
            recent_avg = sum(list(self.throughput_history)[-10:]) / min(10, len(self.throughput_history))
            logger.info(f"  Recent throughput (last 10): {recent_avg:.2f} examples/sec")
        
        return {
            'total_time': total_time,
            'iterations': iteration - 1,
            'avg_throughput': final_avg_throughput,
            'throughput_history': list(self.throughput_history),
            'infinite_mode': infinite_mode
        }
    
    def batch_size_benchmark(self, batch_sizes=None, num_iterations=5):
        if batch_sizes is None:
            # Test a range of batch sizes suitable for CPU
            num_cores = multiprocessing.cpu_count()
            batch_sizes = [1, 2, 4, 8, min(16, num_cores*2), min(32, num_cores*4)]
        """Test inference performance across different batch sizes"""
        logger.info("Starting batch size benchmark...")
        results = {}
        
        for batch_size in batch_sizes:
            logger.info(f"Testing batch size: {batch_size}")
            
            # Create new dataloader with specific batch size
            _, test_loader = setup_datasets(batch_size=batch_size, num_samples=100)
            
            throughputs = []
            
            for i in range(num_iterations):
                throughput, _ = self.model.inference_iteration(test_loader, f"batch_{batch_size}_{i}")
                throughputs.append(throughput)
            
            results[batch_size] = {
                'avg_throughput': np.mean(throughputs),
                'std_throughput': np.std(throughputs),
                'min_throughput': np.min(throughputs),
                'max_throughput': np.max(throughputs)
            }
            
            logger.info(f"Batch size {batch_size}: {results[batch_size]['avg_throughput']:.2f} ± {results[batch_size]['std_throughput']:.2f} examples/sec")
        
        return results

# ------------------------
# Training Function
# ------------------------
def run_training_benchmark(num_epochs=3, batch_size=None, num_samples=1000):
    """Run training benchmark with optimized settings"""
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    logger.info(f"Starting SSD training benchmark on {device}")
    logger.info(f"Available CPU cores: {multiprocessing.cpu_count()}")
    
    # Setup datasets with auto-optimized batch size if not specified
    train_loader, test_loader = setup_datasets(batch_size=batch_size, num_samples=num_samples)
    logger.info(f"Using batch size: {train_loader.batch_size}")
    logger.info(f"Using {train_loader.num_workers} data loader workers")
    
    # Initialize model
    ssd_model = SSDModel(device, pretrained=False)
    
    # Training loop
    for epoch in range(num_epochs):
        if not running:
            break
            
        logger.info(f"\n{'='*50}")
        logger.info(f"EPOCH {epoch + 1}/{num_epochs}")
        logger.info(f"{'='*50}")
        
        avg_loss, avg_throughput = ssd_model.train_epoch(train_loader, epoch + 1)
        
        logger.info(f"Epoch {epoch + 1} Summary:")
        logger.info(f"  Average Loss: {avg_loss:.4f}")
        logger.info(f"  Average Throughput: {avg_throughput:.2f} examples/sec")
    
    # Save trained model
    model_path = "ssd_trained_model.pth"
    torch.save(ssd_model.model.state_dict(), model_path)
    logger.info(f"Model saved to {model_path}")
    
    return ssd_model, model_path

# ------------------------
# Main Function
# ------------------------
def main():
    """Main execution function"""
    global running
    
    import sys
    
    # Parse command line arguments FIRST
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode in ["--help", "-h", "help"]:
            print("SSD Object Detection Benchmark")
            print("=" * 50)
            print("Usage: python ssd-infernce.py [mode]")
            print("")
            print("Available modes:")
            print("  (default)        : Training → Continuous Inference Forever")
            print("  train-only       : Training only, then stop")
            print("  inference-only   : Continuous inference only (no training)")
            print("  batch-test      : Test different batch sizes")
            print("  help            : Show this help message")
            print("")
            print("Default behavior: Runs training first, then continuous inference until stopped")
            return
    else:
        mode = "default"  # Default: training → continuous inference
    
    logger.info("=" * 60)
    logger.info("SSD OBJECT DETECTION BENCHMARK")
    logger.info("=" * 60)
    
    # Show selected mode
    mode_descriptions = {
        "default": "Training → Continuous Inference Forever",
        "train-only": "Training Only",
        "inference-only": "Continuous Inference Only",
        "batch-test": "Batch Size Testing"
    }
    
    selected_mode = mode_descriptions.get(mode, f"Custom Mode: {mode}")
    logger.info(f"🎯 Selected Mode: {selected_mode}")
    
    if mode == "default":
        logger.info("⚠️  WARNING: Continuous inference will run FOREVER until you stop it!")
        logger.info("   Use Ctrl+C to stop gracefully")
    
    # Log system information for performance analysis
    num_cores = multiprocessing.cpu_count()
    logger.info(f"\n💻 System Information:")
    logger.info(f"  CPU cores: {num_cores}")
    logger.info(f"  PyTorch threads: {torch.get_num_threads()}")
    logger.info(f"  OMP threads: {os.environ.get('OMP_NUM_THREADS', 'default')}")
    logger.info(f"  MKL threads: {os.environ.get('MKL_NUM_THREADS', 'default')}")
    logger.info(f"  Device: {'CUDA' if torch.cuda.is_available() else 'CPU'}")
    
    # Initialize CSV files
    initialize_csv_files()
    
    try:
        if mode == "inference-only":
            logger.info("\n" + "="*40)
            logger.info("INFERENCE ONLY MODE")
            logger.info("="*40)
            
            # Initialize inference benchmark without training
            benchmark = SSDInferenceBenchmark(model_path=None)
            
            # Run continuous inference forever
            logger.info("\nStarting continuous inference (runs forever)...")
            continuous_results = benchmark.continuous_inference_benchmark(
                duration_seconds=None,  # Run forever
                report_interval=30      # Report every 30 seconds
            )
            
        elif mode == "train-only":
            logger.info("\n" + "="*40)
            logger.info("TRAINING ONLY MODE")
            logger.info("="*40)
            
            # Run training benchmark only
            trained_model, model_path = run_training_benchmark(
                num_epochs=2, 
                batch_size=None,  # Auto-determine optimal batch size
                num_samples=800   # Increased dataset size
            )
            
            logger.info("Training benchmark completed!")
            
        elif mode == "batch-test":
            logger.info("\n" + "="*40)
            logger.info("BATCH SIZE TESTING MODE")
            logger.info("="*40)
            
            # Initialize inference benchmark
            benchmark = SSDInferenceBenchmark(model_path=None)
            
            # Run batch size benchmark only
            logger.info("Testing different batch sizes...")
            batch_results = benchmark.batch_size_benchmark()
            
            logger.info("Batch size testing completed!")
            
        else:  # Default mode: train → continuous inference
            logger.info("\n" + "="*40)
            logger.info("TRAINING → CONTINUOUS INFERENCE MODE")
            logger.info("="*40)
            
            # Step 1: Run training
            logger.info("🏋️  STEP 1: TRAINING")
            logger.info("-" * 30)
            trained_model, model_path = run_training_benchmark(
                num_epochs=2, 
                batch_size=None,  # Auto-determine optimal batch size
                num_samples=800   # Increased dataset size
            )
            
            logger.info("✅ Training completed! Starting continuous inference...")
            
            # Step 2: Initialize inference with trained model
            logger.info("\n🔄 STEP 2: CONTINUOUS INFERENCE (FOREVER)")
            logger.info("-" * 30)
            benchmark = SSDInferenceBenchmark(model_path=model_path)
            
            # Step 3: Run continuous inference forever
            logger.info("Starting infinite inference loop...")
            logger.info("This will run until you stop the process (Ctrl+C)")
            time.sleep(2)  # Give user time to read
            
            continuous_results = benchmark.continuous_inference_benchmark(
                duration_seconds=None,  # Run forever
                report_interval=30      # Report every 30 seconds
            )
        
        logger.info("\n" + "="*60)
        logger.info("BENCHMARK SESSION ENDED")
        logger.info("="*60)
        logger.info(f"📊 Training data saved to: {training_csv}")
        logger.info(f"📊 Inference data saved to: {inference_csv}")
        logger.info(f"📊 Logs saved to: ssd_benchmark.log")
        
    except KeyboardInterrupt:
        logger.info("\nBenchmark interrupted by user")
    except Exception as e:
        logger.error(f"Error during benchmark: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        logger.info("Benchmark finished.")

if __name__ == "__main__":
    main()