#!/bin/bash
# Example inference script for Jasper

# Make sure you have a trained model
if [ ! -f "checkpoints/best.pt" ]; then
    echo "No trained model found. Run train_example.sh first."
    exit 1
fi

# Single file inference
echo "Testing single file inference..."
python3 jasper_complete.py --mode inference \
    --checkpoint checkpoints/best.pt \
    --audio_file "$1"

# Batch inference on test set
echo "Running batch inference on test set..."
python3 jasper_complete.py --mode inference \
    --checkpoint checkpoints/best.pt \
    --manifest "./librispeech_data/librispeech-test-clean-wav.json"
