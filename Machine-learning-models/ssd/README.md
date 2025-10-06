# SSD (Single Shot Detector) Object Detection Benchmark

This directory contains a comprehensive Single Shot Detector implementation for benchmarking training and inference throughput in object detection tasks.

## Overview

The SSD benchmark provides:
- **Training throughput measurement**: Records performance metrics during model training
- **Inference throughput measurement**: Records performance metrics during model inference
- **Synthetic dataset generation**: Creates synthetic object detection data to avoid large downloads
- **Comprehensive logging**: Saves detailed metrics to CSV files for analysis
- **Multiple deployment options**: Local execution, Docker containers, and Kubernetes deployment

## Features

### Core Functionality
- ✅ SSD300 with VGG16 backbone (using torchvision)
- ✅ Synthetic object detection dataset (configurable size and complexity)
- ✅ Real-time throughput monitoring
- ✅ Memory usage tracking
- ✅ Batch size optimization testing
- ✅ Continuous benchmarking modes
- ✅ Graceful shutdown handling

### Output Metrics
- **Training metrics**: Loss, throughput, learning rate, memory usage per batch
- **Inference metrics**: Throughput, confidence scores, memory usage per iteration
- **System metrics**: CPU/GPU utilization, memory consumption
- **Timing metrics**: Per-batch and per-iteration timing data

## Quick Start

### Prerequisites
```bash
# Install dependencies
pip install -r requirements.txt

# Or install manually:
pip install torch torchvision numpy pillow psutil
```

### Basic Usage

1. **Run both training and inference** (default):
   ```bash
   python ssd-infernce.py
   ```

2. **Training only**:
   ```bash
   python ssd-infernce.py train
   ```

3. **Inference only**:
   ```bash
   python ssd-infernce.py inference
   ```

4. **Test the implementation**:
   ```bash
   python test_ssd.py
   ```

## Output Files

### CSV Files Generated

#### `ssd_training_throughput.csv`
Training performance metrics with the following columns:
- `timestamp`: ISO format timestamp
- `epoch`: Training epoch number
- `batch_idx`: Batch index within epoch
- `training_time_sec`: Time to process the batch (seconds)
- `training_throughput_examples_per_sec`: Training throughput
- `batch_size`: Number of examples in the batch
- `loss`: Training loss value
- `device`: Device used (CPU/CUDA)
- `lr`: Current learning rate
- `memory_usage_mb`: Memory usage in MB

#### `ssd_inference_throughput.csv`
Inference performance metrics with the following columns:
- `timestamp`: ISO format timestamp
- `iteration`: Inference iteration number
- `inference_time_sec`: Time for inference (seconds)
- `inference_throughput_examples_per_sec`: Inference throughput
- `num_examples`: Number of examples processed
- `avg_confidence`: Average confidence score of detections
- `batch_size`: Batch size used for inference
- `device`: Device used (CPU/CUDA)
- `memory_usage_mb`: Memory usage in MB

#### `ssd_benchmark.log`
Detailed log file with:
- Initialization messages
- Progress updates
- Error messages
- Performance summaries

## Docker Deployment

### Build and Run Locally
```bash
# Build the image
./build_local.sh

# Run with default settings (both training and inference)
docker run --rm -it -v $(pwd):/app/output ssd-benchmark:latest

# Run inference only
docker run --rm -it ssd-benchmark:latest python ssd-infernce.py inference

# Run training only
docker run --rm -it ssd-benchmark:latest python ssd-infernce.py train
```

### Build and Push to Registry
```bash
# Edit build_and_push.sh to set your registry
vim build_and_push.sh

# Build and push
./build_and_push.sh v1.0
```

## Kubernetes Deployment

### Deploy to Cluster
```bash
# Edit kubernetes-deployment.yaml to set your image registry
vim kubernetes-deployment.yaml

# Deploy
./k8s-deploy.sh deploy

# Check status
./k8s-deploy.sh status

# View logs
./k8s-deploy.sh logs

# Clean up
./k8s-deploy.sh delete
```

## Configuration Options

### Dataset Configuration
The synthetic dataset can be configured by modifying the following parameters in the code:

```python
# In setup_datasets() function
num_samples=1000,      # Number of synthetic samples
image_size=(300, 300), # Image dimensions
num_classes=20,        # Number of object classes
batch_size=4          # Batch size for training/inference
```

### Model Configuration
```python
# In SSDModel class
num_classes=91,        # Number of classes (COCO format)
pretrained=False,      # Use pretrained weights
lr=0.001,             # Learning rate
momentum=0.9,         # SGD momentum
weight_decay=0.0005   # Weight decay
```

### Benchmark Configuration
```python
# Training benchmark
num_epochs=3,         # Number of training epochs
batch_size=4,         # Training batch size
num_samples=500       # Dataset size

# Inference benchmark
duration_seconds=60,  # Continuous inference duration
report_interval=10    # Progress report interval
```

## Performance Analysis

### Export Results
```bash
# Export CSV files and create summary
./export.sh

# Export to specific directory
./export.sh /path/to/results/
```

### Analyze Results with Python
```python
import pandas as pd
import matplotlib.pyplot as plt

# Load training data
train_df = pd.read_csv('ssd_training_throughput.csv')

# Plot training throughput over time
plt.figure(figsize=(12, 6))
plt.plot(train_df['batch_idx'], train_df['training_throughput_examples_per_sec'])
plt.xlabel('Batch Index')
plt.ylabel('Training Throughput (examples/sec)')
plt.title('SSD Training Throughput Over Time')
plt.show()

# Load inference data
inf_df = pd.read_csv('ssd_inference_throughput.csv')

# Calculate statistics
print(f"Average inference throughput: {inf_df['inference_throughput_examples_per_sec'].mean():.2f} examples/sec")
print(f"Peak inference throughput: {inf_df['inference_throughput_examples_per_sec'].max():.2f} examples/sec")
print(f"Average confidence: {inf_df['avg_confidence'].mean():.3f}")
```

## Benchmarking Modes

### 1. Training Benchmark
- Measures training throughput per batch
- Records loss progression
- Tracks memory usage during training
- Monitors learning rate changes

### 2. Inference Benchmark
- **Continuous mode**: Runs inference for specified duration
- **Batch size testing**: Tests different batch sizes for optimal performance
- **Single iteration**: One-time inference measurement

### 3. Full Benchmark
Runs both training and inference benchmarks sequentially, providing comprehensive performance analysis.

## Troubleshooting

### Common Issues

1. **Memory errors**: Reduce batch size or image resolution
2. **Slow performance**: Ensure appropriate device selection (CPU/GPU)
3. **Import errors**: Install all dependencies from `requirements.txt`

### Performance Optimization

1. **For CPU**: Use smaller batch sizes (1-4)
2. **For GPU**: Use larger batch sizes (8-32)
3. **For faster testing**: Reduce `num_samples` in dataset configuration
4. **For memory constraints**: Reduce image size in dataset configuration

### Log Analysis
```bash
# Check for errors
grep -i error ssd_benchmark.log

# Monitor progress
tail -f ssd_benchmark.log

# Check final results
tail -20 ssd_benchmark.log
```

## Architecture

### File Structure
```
ssd/
├── ssd-infernce.py              # Main benchmark implementation
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Container definition
├── kubernetes-deployment.yaml   # K8s deployment config
├── build_local.sh              # Local Docker build script
├── build_and_push.sh           # Registry push script
├── k8s-deploy.sh               # Kubernetes deployment script
├── export.sh                   # Results export script
├── test_ssd.py                 # Unit tests
└── README.md                   # This file
```

### Key Components

1. **SSDModel**: PyTorch SSD implementation with training/inference methods
2. **SyntheticObjectDetectionDataset**: Generates synthetic detection data
3. **SSDInferenceBenchmark**: Comprehensive inference benchmarking suite
4. **CSV Logging**: Real-time performance data collection
5. **Resource Monitoring**: Memory and system resource tracking

## Examples

### Example Training Output
```
2025-10-06 14:30:15 - INFO - Starting SSD training benchmark on cpu
2025-10-06 14:30:16 - INFO - Epoch 1, Batch 0: Loss = 2.3456, Throughput = 8.45 examples/sec
2025-10-06 14:30:18 - INFO - Epoch 1, Batch 10: Loss = 2.1234, Throughput = 9.12 examples/sec
```

### Example Inference Output
```
2025-10-06 14:35:20 - INFO - Inference iteration 1: Throughput = 15.67 examples/sec, Avg Confidence = 0.342
2025-10-06 14:35:22 - INFO - Inference iteration 2: Throughput = 16.23 examples/sec, Avg Confidence = 0.356
```

### Example CSV Data
```csv
timestamp,iteration,inference_time_sec,inference_throughput_examples_per_sec,num_examples,avg_confidence,batch_size,device,memory_usage_mb
2025-10-06T14:35:20.123456,1,0.64,15.67,10,0.342,2,cpu,245.6
2025-10-06T14:35:22.234567,2,0.62,16.23,10,0.356,2,cpu,247.1
```

## Contributing

To extend or modify the benchmark:

1. **Add new metrics**: Modify the CSV logging functions
2. **Change model architecture**: Update the `SSDModel` class
3. **Add new datasets**: Implement new dataset classes
4. **Extend benchmarks**: Add methods to `SSDInferenceBenchmark`

## License

This implementation is part of the 2024-biosys-ec-elasticcontainer project for research purposes.

## References

- [SSD: Single Shot MultiBox Detector](https://arxiv.org/abs/1512.02325)
- [PyTorch Torchvision Detection Models](https://pytorch.org/vision/stable/models.html#object-detection)
- [COCO Dataset](https://cocodataset.org/)