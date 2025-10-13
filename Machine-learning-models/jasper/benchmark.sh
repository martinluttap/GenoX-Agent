#!/bin/bash
# Benchmark script for performance testing

echo "Running Jasper benchmarks..."

# Test different batch sizes
for batch_size in 1 2 4 8; do
    echo "Testing batch size: $batch_size"
    python3 jasper_complete.py --mode train \
        --train_manifest "./librispeech_data/librispeech-train-clean-100-wav.json" \
        --epochs 1 \
        --batch_size $batch_size \
        --save_dir "benchmark_checkpoints_bs$batch_size"
done

echo "Benchmark completed!"
