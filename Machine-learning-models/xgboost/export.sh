#!/bin/bash
# export-csv.sh

NAMESPACE=${1:-default}
POD_LABEL=${2:-"app=xgboost-benchmark"}  # Adjust based on your pod labels
OUTPUT_DIR="./exported-csv"

mkdir -p $OUTPUT_DIR

# Get all pods with the specified label
PODS=$(kubectl get pods -l $POD_LABEL -n $NAMESPACE -o jsonpath='{.items[*].metadata.name}')

for POD in $PODS; do
    echo "Exporting CSV files from pod: $POD"
    
    # Create directory for this pod
    POD_DIR="$OUTPUT_DIR/$POD"
    mkdir -p $POD_DIR
    
    # Copy CSV files (ignore errors if files don't exist)
    kubectl cp $NAMESPACE/$POD:training_throughput.csv $POD_DIR/training_throughput.csv 2>/dev/null || echo "No training_throughput.csv in $POD"
    kubectl cp $NAMESPACE/$POD:inference_throughput.csv $POD_DIR/inference_throughput.csv 2>/dev/null || echo "No inference_throughput.csv in $POD"
    
    echo "Files exported to: $POD_DIR"
done