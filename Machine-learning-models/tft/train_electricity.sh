#!/bin/bash
# Example training script for TFT on electricity dataset

# Full training
python3 tft_complete.py --mode train \
    --dataset electricity \
    --data_path "./data/processed/electricity" \
    --epochs 25 \
    --batch_size 64 \
    --lr 1e-3 \
    --save_dir checkpoints/electricity

echo "Training completed! Best model saved in checkpoints/electricity/best.pt"
