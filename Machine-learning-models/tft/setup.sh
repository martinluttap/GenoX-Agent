#!/bin/bash
#
# Complete Setup Script for Temporal Fusion Transformer (TFT)
# Downloads data, installs dependencies, and sets up the environment
#

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
DATA_DIR="./data"
DATASET="electricity"  # electricity, traffic, all
PYTHON_CMD="python3"
SKIP_DEPS=false
SKIP_DATA=false
TEST_SETUP=false

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "\n${BLUE}================================${NC}"
    echo -e "${BLUE} $1${NC}"
    echo -e "${BLUE}================================${NC}\n"
}

# Function to check if command exists
check_command() {
    if command -v "$1" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Function to install Python dependencies
install_dependencies() {
    print_header "Installing Python Dependencies"
    
    # Check if pip is available
    if ! check_command pip3 && ! check_command pip; then
        print_error "pip not found. Please install pip first."
        exit 1
    fi
    
    local pip_cmd="pip3"
    if ! check_command pip3; then
        pip_cmd="pip"
    fi
    
    # Create requirements.txt if it doesn't exist
    if [ ! -f "requirements.txt" ]; then
        print_status "Creating requirements.txt..."
        cat > requirements.txt << 'EOF'
# Core dependencies
torch>=1.9.0
numpy>=1.19.0

# Data processing
pandas>=1.3.0
scikit-learn>=0.24.0

# Utilities
tqdm>=4.60.0
requests>=2.25.0

# Optional but recommended
matplotlib>=3.3.0
seaborn>=0.11.0
jupyter>=1.0.0
EOF
    fi
    
    print_status "Installing Python packages..."
    $pip_cmd install -r requirements.txt
    
    # Verify installations
    print_status "Verifying installations..."
    $PYTHON_CMD -c "
import torch
import pandas as pd
import numpy as np
import sklearn
import tqdm
import requests
print('✓ All dependencies installed successfully!')
print(f'PyTorch version: {torch.__version__}')
print(f'Pandas version: {pd.__version__}')
print(f'NumPy version: {np.__version__}')
"
    
    print_success "Dependencies installed successfully!"
}

# Function to download dataset
download_dataset() {
    print_header "Downloading TFT Datasets"
    
    print_status "Dataset will be downloaded to: $DATA_DIR"
    print_status "Dataset(s): $DATASET"
    
    # Create data directory
    mkdir -p "$DATA_DIR"
    
    # Download and preprocess
    case $DATASET in
        "electricity")
            print_status "Downloading electricity dataset..."
            $PYTHON_CMD download_datasets.py \
                --dataset electricity \
                --data_dir "$DATA_DIR" \
                --verify
            ;;
        "traffic")
            print_status "Downloading traffic dataset..."
            $PYTHON_CMD download_datasets.py \
                --dataset traffic \
                --data_dir "$DATA_DIR" \
                --verify
            ;;
        "all")
            print_status "Downloading both datasets..."
            $PYTHON_CMD download_datasets.py \
                --dataset all \
                --data_dir "$DATA_DIR" \
                --verify
            ;;
        *)
            print_error "Unknown dataset: $DATASET"
            exit 1
            ;;
    esac
    
    print_success "Dataset download completed!"
}

# Function to test the setup
test_setup() {
    print_header "Testing TFT Setup"
    
    print_status "Running basic model test..."
    $PYTHON_CMD tft_complete.py --mode test
    
    # Test with real data if available
    if [ -d "$DATA_DIR/processed/electricity" ] && [ -f "$DATA_DIR/processed/electricity/train.csv" ]; then
        print_status "Testing with electricity data..."
        
        # Quick training test (1 epoch)
        $PYTHON_CMD tft_complete.py --mode train \
            --dataset electricity \
            --data_path "$DATA_DIR/processed/electricity" \
            --epochs 1 \
            --batch_size 32 \
            --save_dir "test_checkpoints"
        
        # Test inference if checkpoint exists
        if [ -f "test_checkpoints/epoch_1.pt" ]; then
            print_status "Testing inference..."
            $PYTHON_CMD tft_complete.py --mode inference \
                --checkpoint "test_checkpoints/epoch_1.pt" \
                --data "$DATA_DIR/processed/electricity/test.csv" \
                --scalers "$DATA_DIR/processed/electricity/scalers.pkl" \
                --encoders "$DATA_DIR/processed/electricity/encoders.pkl"
        fi
    elif [ -d "$DATA_DIR/processed/traffic" ] && [ -f "$DATA_DIR/processed/traffic/train.csv" ]; then
        print_status "Testing with traffic data..."
        
        # Quick training test (1 epoch)
        $PYTHON_CMD tft_complete.py --mode train \
            --dataset traffic \
            --data_path "$DATA_DIR/processed/traffic" \
            --epochs 1 \
            --batch_size 32 \
            --save_dir "test_checkpoints"
        
        # Test inference if checkpoint exists
        if [ -f "test_checkpoints/epoch_1.pt" ]; then
            print_status "Testing inference..."
            $PYTHON_CMD tft_complete.py --mode inference \
                --checkpoint "test_checkpoints/epoch_1.pt" \
                --data "$DATA_DIR/processed/traffic/test.csv" \
                --scalers "$DATA_DIR/processed/traffic/scalers.pkl" \
                --encoders "$DATA_DIR/processed/traffic/encoders.pkl"
        fi
    fi
    
    print_success "Setup test completed!"
}

# Function to create example scripts
create_examples() {
    print_header "Creating Example Scripts"
    
    # Training example for electricity
    cat > train_electricity.sh << EOF
#!/bin/bash
# Example training script for TFT on electricity dataset

# Full training
python3 tft_complete.py --mode train \\
    --dataset electricity \\
    --data_path "$DATA_DIR/processed/electricity" \\
    --epochs 25 \\
    --batch_size 64 \\
    --lr 1e-3 \\
    --save_dir checkpoints/electricity

echo "Training completed! Best model saved in checkpoints/electricity/best.pt"
EOF

    # Training example for traffic
    cat > train_traffic.sh << EOF
#!/bin/bash
# Example training script for TFT on traffic dataset

# Full training
python3 tft_complete.py --mode train \\
    --dataset traffic \\
    --data_path "$DATA_DIR/processed/traffic" \\
    --epochs 25 \\
    --batch_size 64 \\
    --lr 1e-3 \\
    --save_dir checkpoints/traffic

echo "Training completed! Best model saved in checkpoints/traffic/best.pt"
EOF

    # Inference example
    cat > inference_example.sh << EOF
#!/bin/bash
# Example inference script for TFT

# Check arguments
if [ \$# -eq 0 ]; then
    echo "Usage: \$0 <dataset> [checkpoint_path]"
    echo "  dataset: electricity or traffic"
    echo "  checkpoint_path: optional, defaults to checkpoints/<dataset>/best.pt"
    exit 1
fi

DATASET=\$1
CHECKPOINT=\${2:-"checkpoints/\$DATASET/best.pt"}

# Make sure checkpoint exists
if [ ! -f "\$CHECKPOINT" ]; then
    echo "Checkpoint not found: \$CHECKPOINT"
    echo "Run train_\${DATASET}.sh first."
    exit 1
fi

# Run inference
echo "Running inference on \$DATASET dataset..."
python3 tft_complete.py --mode inference \\
    --checkpoint "\$CHECKPOINT" \\
    --data "$DATA_DIR/processed/\$DATASET/test.csv" \\
    --scalers "$DATA_DIR/processed/\$DATASET/scalers.pkl" \\
    --encoders "$DATA_DIR/processed/\$DATASET/encoders.pkl" \\
    --save_predictions \\
    --results "results/\$DATASET"

echo "Inference completed! Results saved in results/\$DATASET/"
EOF

    # Benchmark script
    cat > benchmark.sh << EOF
#!/bin/bash
# Benchmark script for performance testing

echo "Running TFT benchmarks..."

# Test different batch sizes on electricity dataset
for batch_size in 16 32 64 128; do
    echo "Testing batch size: \$batch_size"
    python3 tft_complete.py --mode train \\
        --dataset electricity \\
        --data_path "$DATA_DIR/processed/electricity" \\
        --epochs 1 \\
        --batch_size \$batch_size \\
        --save_dir "benchmark_checkpoints_bs\$batch_size"
done

echo "Benchmark completed!"
EOF

    # Make scripts executable
    chmod +x train_electricity.sh train_traffic.sh inference_example.sh benchmark.sh
    
    print_success "Example scripts created!"
    print_status "  - train_electricity.sh: Training on electricity dataset"
    print_status "  - train_traffic.sh: Training on traffic dataset"
    print_status "  - inference_example.sh: Inference example"
    print_status "  - benchmark.sh: Performance benchmarking"
}

# Function to display usage
usage() {
    cat << EOF
TFT (Temporal Fusion Transformer) Setup Script

USAGE:
    $0 [OPTIONS]

OPTIONS:
    --data-dir DIR      Directory for datasets (default: ./data)
    --dataset DATASET   Dataset to download: electricity, traffic, or all (default: electricity)
    --python CMD        Python command to use (default: python3)
    --skip-deps        Skip dependency installation
    --skip-data        Skip data download
    --test             Run setup tests after installation
    --help             Show this help message

EXAMPLES:
    # Basic setup with electricity dataset
    $0

    # Setup with both datasets
    $0 --dataset all --data-dir /data/tft

    # Setup for traffic only
    $0 --dataset traffic --skip-deps

    # Quick test setup
    $0 --dataset electricity --test

DATASET OPTIONS:
    electricity    Electricity consumption dataset (370 clients)
    traffic        Traffic volume dataset (963 sensors)
    all           Both datasets
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --data-dir)
            DATA_DIR="$2"
            shift 2
            ;;
        --dataset)
            DATASET="$2"
            shift 2
            ;;
        --python)
            PYTHON_CMD="$2"
            shift 2
            ;;
        --skip-deps)
            SKIP_DEPS=true
            shift
            ;;
        --skip-data)
            SKIP_DATA=true
            shift
            ;;
        --test)
            TEST_SETUP=true
            shift
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Main setup process
main() {
    print_header "TFT (Temporal Fusion Transformer) Setup"
    
    print_status "Setup configuration:"
    print_status "  Data directory: $DATA_DIR"
    print_status "  Dataset: $DATASET"
    print_status "  Python command: $PYTHON_CMD"
    print_status "  Skip dependencies: $SKIP_DEPS"
    print_status "  Skip data download: $SKIP_DATA"
    print_status "  Run tests: $TEST_SETUP"
    
    # Check if Python is available
    if ! check_command "$PYTHON_CMD"; then
        print_error "Python command not found: $PYTHON_CMD"
        print_error "Please install Python or specify correct command with --python"
        exit 1
    fi
    
    # Check if required scripts exist
    if [ ! -f "tft_complete.py" ]; then
        print_error "tft_complete.py not found in current directory"
        exit 1
    fi
    
    if [ ! -f "download_datasets.py" ]; then
        print_error "download_datasets.py not found in current directory"
        exit 1
    fi
    
    # Install dependencies
    if [ "$SKIP_DEPS" = false ]; then
        install_dependencies
    else
        print_warning "Skipping dependency installation"
    fi
    
    # Download dataset
    if [ "$SKIP_DATA" = false ]; then
        download_dataset
    else
        print_warning "Skipping data download"
    fi
    
    # Create example scripts
    create_examples
    
    # Test setup
    if [ "$TEST_SETUP" = true ]; then
        test_setup
    fi
    
    # Final instructions
    print_header "Setup Complete!"
    
    echo -e "${GREEN}TFT (Temporal Fusion Transformer) is ready to use!${NC}\n"
    
    echo "Quick Start:"
    echo "  1. Basic model test:        python3 tft_complete.py --mode test"
    echo "  2. Train on electricity:    ./train_electricity.sh"
    echo "  3. Train on traffic:        ./train_traffic.sh"
    echo "  4. Run inference:           ./inference_example.sh electricity"
    echo "  5. Performance benchmark:   ./benchmark.sh"
    echo
    
    if [ -d "$DATA_DIR/processed" ]; then
        echo "Available datasets:"
        ls -la "$DATA_DIR/processed/" 2>/dev/null || echo "  No processed datasets found"
    fi
    
    echo
    echo "For more options, see:"
    echo "  python3 tft_complete.py --help"
    echo "  python3 download_datasets.py --help"
    
    print_success "Setup completed successfully!"
}

# Run main function
main