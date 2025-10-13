#!/bin/bash
# Example inference script for TFT

# Check arguments
if [ $# -eq 0 ]; then
    echo "Usage: $0 <dataset> [checkpoint_path]"
    echo "  dataset: electricity or traffic"
    echo "  checkpoint_path: optional, defaults to checkpoints/<dataset>/best.pt"
    exit 1
fi

DATASET=$1
CHECKPOINT=${2:-"checkpoints/$DATASET/best.pt"}

# Make sure checkpoint exists
if [ ! -f "$CHECKPOINT" ]; then
    echo "Checkpoint not found: $CHECKPOINT"
    echo "Run train_${DATASET}.sh first."
    exit 1
fi

# Run inference
echo "Running inference on $DATASET dataset..."
python3 tft_complete.py --mode inference \
    --checkpoint "$CHECKPOINT" \
    --data "./data/processed/$DATASET/test.csv" \
    --scalers "./data/processed/$DATASET/scalers.pkl" \
    --encoders "./data/processed/$DATASET/encoders.pkl" \
    --save_predictions \
    --results "results/$DATASET"

echo "Inference completed! Results saved in results/$DATASET/"
