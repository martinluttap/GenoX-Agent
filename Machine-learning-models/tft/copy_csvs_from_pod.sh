#!/bin/bash
# Script to copy all CSV files from a Kubernetes pod (by app label) to a local folder

APP_LABEL="tft-model-benchmark"
NAMESPACE="default" # Change if your pod is in a different namespace
LOCAL_DEST="benchmark_results"
POD=$(kubectl get pods -n $NAMESPACE -l app=$APP_LABEL -o jsonpath='{.items[0].metadata.name}')

if [ -z "$POD" ]; then
  echo "No pod found with label app=$APP_LABEL in namespace $NAMESPACE."
  exit 1
fi

mkdir -p "$LOCAL_DEST"

# Copy all CSV files from /app/checkpoints in the pod to local folder
kubectl cp $NAMESPACE/$POD:/app/checkpoints "$LOCAL_DEST"

# Optionally, filter only CSV files locally
find "$LOCAL_DEST" -type f ! -name '*.csv' -delete

echo "All CSV files from pod $POD have been copied to $LOCAL_DEST."
