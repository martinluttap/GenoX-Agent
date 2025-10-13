#!/bin/bash
# Example training script for Jasper

# Small scale training (good for testing)
python3 jasper_complete.py --mode train \
    --train_manifest "./librispeech_data/librispeech-train-clean-100-wav.json" \
    --val_manifest "./librispeech_data/librispeech-dev-clean-wav.json" \
    --epochs 10 \
    --batch_size 4 \
    --lr 0.01 \
    --save_dir checkpoints

echo "Training completed! Best model saved in checkpoints/best.pt"
