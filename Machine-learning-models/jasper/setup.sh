#!/bin/bash
"""
Complete Setup Script for Jasper Speech Recognition
Downloads data, installs dependencies, and sets up the environment
"""

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
DATA_DIR="./librispeech_data"
SUBSET="minimal"  # minimal, inference_only, all
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
torchaudio>=0.9.0
numpy>=1.19.0

# Audio processing
librosa>=0.8.0
soundfile>=0.10.0

# Data handling
pyyaml>=5.4.0
tqdm>=4.60.0

# Optional but recommended
matplotlib>=3.3.0
scipy>=1.6.0
EOF
    fi
    
    print_status "Installing Python packages..."
    $pip_cmd install -r requirements.txt
    
    # Verify installations
    print_status "Verifying installations..."
    $PYTHON_CMD -c "
import torch
import torchaudio
import librosa
import soundfile
import yaml
import numpy as np
print('✓ All dependencies installed successfully!')
print(f'PyTorch version: {torch.__version__}')
print(f'Torchaudio version: {torchaudio.__version__}')
print(f'Librosa version: {librosa.__version__}')
"
    
    print_success "Dependencies installed successfully!"
}

# Function to download dataset
download_dataset() {
    print_header "Downloading LibriSpeech Dataset"
    
    print_status "Dataset will be downloaded to: $DATA_DIR"
    print_status "Subset: $SUBSET"
    
    # Create data directory
    mkdir -p "$DATA_DIR"
    
    # Download and preprocess
    case $SUBSET in
        "minimal")
            print_status "Downloading minimal dataset (train-clean-100 + dev-clean)..."
            $PYTHON_CMD download_librispeech.py \
                --data_dir "$DATA_DIR" \
                --minimal \
                --verify
            ;;
        "inference_only")
            print_status "Downloading inference datasets (dev + test sets)..."
            $PYTHON_CMD download_librispeech.py \
                --data_dir "$DATA_DIR" \
                --inference_only \
                --verify
            ;;
        "all")
            print_status "Downloading complete LibriSpeech dataset..."
            $PYTHON_CMD download_librispeech.py \
                --data_dir "$DATA_DIR" \
                --all \
                --verify
            ;;
        *)
            print_status "Downloading custom subsets: $SUBSET"
            $PYTHON_CMD download_librispeech.py \
                --data_dir "$DATA_DIR" \
                --subsets "$SUBSET" \
                --verify
            ;;
    esac
    
    print_success "Dataset download completed!"
}

# Function to test the setup
test_setup() {
    print_header "Testing Jasper Setup"
    
    print_status "Running basic model test..."
    $PYTHON_CMD jasper_complete.py --mode test
    
    if [ -d "$DATA_DIR" ] && [ -f "$DATA_DIR/librispeech-train-clean-100-wav.json" ]; then
        print_status "Testing with real data..."
        
        # Quick training test (1 epoch)
        $PYTHON_CMD jasper_complete.py --mode train \
            --train_manifest "$DATA_DIR/librispeech-train-clean-100-wav.json" \
            --val_manifest "$DATA_DIR/librispeech-dev-clean-wav.json" \
            --epochs 1 \
            --batch_size 2 \
            --save_dir "test_checkpoints"
        
        # Test inference if checkpoint exists
        if [ -f "test_checkpoints/epoch_1.pt" ]; then
            print_status "Testing inference..."
            
            # Create a test audio file from dataset
            $PYTHON_CMD -c "
import json
import os
with open('$DATA_DIR/librispeech-dev-clean-wav.json', 'r') as f:
    entry = json.loads(f.readline())
    test_audio = os.path.join('$DATA_DIR', entry['audio_filepath'])
    print(f'Testing with: {test_audio}')
"
            
            # Get first audio file for testing
            test_audio=$(python3 -c "
import json
import os
with open('$DATA_DIR/librispeech-dev-clean-wav.json', 'r') as f:
    entry = json.loads(f.readline())
    print(os.path.join('$DATA_DIR', entry['audio_filepath']))
")
            
            if [ -f "$test_audio" ]; then
                $PYTHON_CMD jasper_complete.py --mode inference \
                    --checkpoint "test_checkpoints/epoch_1.pt" \
                    --audio_file "$test_audio"
            fi
        fi
    fi
    
    print_success "Setup test completed!"
}

# Function to create example scripts
create_examples() {
    print_header "Creating Example Scripts"
    
    # Training example
    cat > train_example.sh << EOF
#!/bin/bash
# Example training script for Jasper

# Small scale training (good for testing)
python3 jasper_complete.py --mode train \\
    --train_manifest "$DATA_DIR/librispeech-train-clean-100-wav.json" \\
    --val_manifest "$DATA_DIR/librispeech-dev-clean-wav.json" \\
    --epochs 10 \\
    --batch_size 4 \\
    --lr 0.01 \\
    --save_dir checkpoints

echo "Training completed! Best model saved in checkpoints/best.pt"
EOF

    # Inference example
    cat > inference_example.sh << EOF
#!/bin/bash
# Example inference script for Jasper

# Make sure you have a trained model
if [ ! -f "checkpoints/best.pt" ]; then
    echo "No trained model found. Run train_example.sh first."
    exit 1
fi

# Single file inference
echo "Testing single file inference..."
python3 jasper_complete.py --mode inference \\
    --checkpoint checkpoints/best.pt \\
    --audio_file "\$1"

# Batch inference on test set
echo "Running batch inference on test set..."
python3 jasper_complete.py --mode inference \\
    --checkpoint checkpoints/best.pt \\
    --manifest "$DATA_DIR/librispeech-test-clean-wav.json"
EOF

    # Benchmark script
    cat > benchmark.sh << EOF
#!/bin/bash
# Benchmark script for performance testing

echo "Running Jasper benchmarks..."

# Test different batch sizes
for batch_size in 1 2 4 8; do
    echo "Testing batch size: \$batch_size"
    python3 jasper_complete.py --mode train \\
        --train_manifest "$DATA_DIR/librispeech-train-clean-100-wav.json" \\
        --epochs 1 \\
        --batch_size \$batch_size \\
        --save_dir "benchmark_checkpoints_bs\$batch_size"
done

echo "Benchmark completed!"
EOF

    # Make scripts executable
    chmod +x train_example.sh inference_example.sh benchmark.sh
    
    print_success "Example scripts created!"
    print_status "  - train_example.sh: Basic training example"
    print_status "  - inference_example.sh: Inference example"  
    print_status "  - benchmark.sh: Performance benchmarking"
}

# Function to display usage
usage() {
    cat << EOF
Jasper Speech Recognition Setup Script

USAGE:
    $0 [OPTIONS]

OPTIONS:
    --data-dir DIR      Directory for LibriSpeech data (default: ./librispeech_data)
    --subset SUBSET     Dataset subset to download: minimal, inference_only, all, or custom
                       (default: minimal)
    --python CMD        Python command to use (default: python3)
    --skip-deps        Skip dependency installation
    --skip-data        Skip data download
    --test             Run setup tests after installation
    --help             Show this help message

EXAMPLES:
    # Basic setup with minimal dataset
    $0

    # Setup with complete dataset
    $0 --subset all --data-dir /data/librispeech

    # Setup for inference only
    $0 --subset inference_only --skip-deps

    # Custom subset
    $0 --subset "train-clean-100,dev-clean,test-clean"

SUBSET OPTIONS:
    minimal         train-clean-100 + dev-clean (recommended for testing)
    inference_only  dev-clean, dev-other, test-clean, test-other
    all            Complete LibriSpeech dataset (~100GB)
    custom         Comma-separated list of specific subsets
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --data-dir)
            DATA_DIR="$2"
            shift 2
            ;;
        --subset)
            SUBSET="$2"
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
    print_header "Jasper Speech Recognition Setup"
    
    print_status "Setup configuration:"
    print_status "  Data directory: $DATA_DIR"
    print_status "  Dataset subset: $SUBSET"
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
    if [ ! -f "jasper_complete.py" ]; then
        print_error "jasper_complete.py not found in current directory"
        exit 1
    fi
    
    if [ ! -f "download_librispeech.py" ]; then
        print_error "download_librispeech.py not found in current directory"
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
    
    echo -e "${GREEN}Jasper Speech Recognition is ready to use!${NC}\n"
    
    echo "Quick Start:"
    echo "  1. Basic model test:       python3 jasper_complete.py --mode test"
    echo "  2. Start training:        ./train_example.sh"
    echo "  3. Run inference:         ./inference_example.sh <audio_file>"
    echo "  4. Performance benchmark: ./benchmark.sh"
    echo
    
    if [ -d "$DATA_DIR" ]; then
        echo "Dataset files:"
        ls -la "$DATA_DIR"/*.json 2>/dev/null || echo "  No manifest files found"
    fi
    
    echo
    echo "For more options, see:"
    echo "  python3 jasper_complete.py --help"
    echo "  python3 download_librispeech.py --help"
    
    print_success "Setup completed successfully!"
}

# Run main function
main