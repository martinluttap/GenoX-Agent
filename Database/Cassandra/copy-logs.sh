#!/bin/bash

# Script to copy logs from Cassandra stress test pod to local directory
# Usage: ./copy-logs.sh [local-destination-folder]

set -e  # Exit on any error

# Configuration
POD_LABEL="app=cassandra-stress-test"
POD_LOGS_PATH="/logs"
DEFAULT_LOCAL_DIR="./pod-logs"

# Get local destination directory (use argument or default)
LOCAL_DIR="${1:-$DEFAULT_LOCAL_DIR}"

# Create timestamp for unique folder naming
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DESTINATION_DIR="${LOCAL_DIR}_${TIMESTAMP}"

echo "=================================="
echo "Cassandra Stress Test Log Copier"
echo "=================================="
echo "Pod Label: $POD_LABEL"
echo "Source Path: $POD_LOGS_PATH"
echo "Destination: $DESTINATION_DIR"
echo "=================================="

# Find pod using label selector
echo "Finding pod with label: $POD_LABEL"
POD_NAME=$(kubectl get pods -l "$POD_LABEL" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -z "$POD_NAME" ]; then
    echo "Error: No pod found with label '$POD_LABEL'!"
    echo "Available pods:"
    kubectl get pods
    exit 1
fi

echo "Found pod: $POD_NAME"

# Check if pod exists and is running
echo "Checking pod status..."
if ! kubectl get pod "$POD_NAME" &>/dev/null; then
    echo "Error: Pod '$POD_NAME' not found!"
    echo "Available pods with label $POD_LABEL:"
    kubectl get pods -l "$POD_LABEL"
    exit 1
fi

POD_STATUS=$(kubectl get pod "$POD_NAME" -o jsonpath='{.status.phase}')
if [ "$POD_STATUS" != "Running" ]; then
    echo "Error: Pod '$POD_NAME' is not running (status: $POD_STATUS)"
    exit 1
fi

echo "✓ Pod is running"

# Create local destination directory
echo "Creating local destination directory: $DESTINATION_DIR"
mkdir -p "$DESTINATION_DIR"

# Check if /logs directory exists in the pod
echo "Checking if /logs directory exists in pod..."
if ! kubectl exec "$POD_NAME" -- test -d "$POD_LOGS_PATH"; then
    echo "Error: Directory '$POD_LOGS_PATH' does not exist in pod '$POD_NAME'"
    echo "Available directories in pod root:"
    kubectl exec "$POD_NAME" -- ls -la /
    exit 1
fi

echo "✓ /logs directory found in pod"

# List contents of /logs directory
echo "Contents of $POD_LOGS_PATH in pod:"
kubectl exec "$POD_NAME" -- ls -la "$POD_LOGS_PATH"
echo ""

# Copy all files from /logs directory
echo "Copying files from pod:$POD_LOGS_PATH to $DESTINATION_DIR..."

# Use kubectl cp to copy the entire logs directory
if kubectl cp "$POD_NAME:$POD_LOGS_PATH" "$DESTINATION_DIR"; then
    echo "✓ Successfully copied logs to $DESTINATION_DIR"
    
    # Show what was copied
    echo ""
    echo "Copied files:"
    find "$DESTINATION_DIR" -type f -exec ls -lh {} \; | head -20
    
    # Count total files and size
    TOTAL_FILES=$(find "$DESTINATION_DIR" -type f | wc -l)
    TOTAL_SIZE=$(du -sh "$DESTINATION_DIR" | cut -f1)
    
    echo ""
    echo "Summary:"
    echo "- Total files copied: $TOTAL_FILES"
    echo "- Total size: $TOTAL_SIZE"
    echo "- Destination: $DESTINATION_DIR"
    
else
    echo "Error: Failed to copy logs from pod"
    exit 1
fi

echo ""
echo "Log copy completed successfully!"
echo "You can find your logs in: $DESTINATION_DIR"