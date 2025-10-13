#!/bin/bash
# Benchmark script for performance testing

echo "Running TFT benchmarks..."

# Test different batch sizes on electricity dataset
for batch_size in 16 32 64 128; do
    echo "Testing batch size: $batch_size"
    python3 tft_complete.py --mode train \
        --dataset electricity \
        --data_path "./data/processed/electricity" \
        --epochs 1 \
        --batch_size $batch_size \
        --save_dir "benchmark_checkpoints_bs$batch_size"
done

echo "Benchmark completed!"
