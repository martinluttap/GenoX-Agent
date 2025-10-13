#!/bin/bash

# Script to copy throughput and inference CSV files from Jasper benchmark containers in Kubernetes

set -e

# Configuration
NAMESPACE="${NAMESPACE:-default}"
APP_LABEL="app=jasper-benchmark"
LOCAL_RESULTS_DIR="./benchmark-results"
CONTAINER_NAME=""  # Use default container

# CSV files to copy from container
CSV_FILES=(
    "inference_throughput.csv"
    "training_throughput.csv"
)

echo "=== Jasper Benchmark Results Collector ==="
echo "Namespace: $NAMESPACE"
echo "App Label: $APP_LABEL"
echo "Local Results Dir: $LOCAL_RESULTS_DIR"
echo ""

# Create local results directory
mkdir -p "$LOCAL_RESULTS_DIR"

# Get all jasper benchmark pods
echo "Finding Jasper benchmark pods..."
PODS=$(kubectl get pods -n "$NAMESPACE" -l "$APP_LABEL" -o jsonpath='{.items[*].metadata.name}')

if [ -z "$PODS" ]; then
    echo "❌ No Jasper benchmark pods found with label: $APP_LABEL"
    echo "Available pods:"
    kubectl get pods -n "$NAMESPACE" --no-headers
    exit 1
fi

echo "Found pods: $PODS"
echo ""

# Copy CSV files from each pod
for POD in $PODS; do
    echo "📊 Processing pod: $POD"
    
    # Check if pod is running
    POD_STATUS=$(kubectl get pod "$POD" -n "$NAMESPACE" -o jsonpath='{.status.phase}')
    echo "  Status: $POD_STATUS"
    
    if [ "$POD_STATUS" != "Running" ]; then
        echo "  ⚠️  Pod not running, skipping..."
        continue
    fi
    
    # Create pod-specific directory
    POD_DIR="$LOCAL_RESULTS_DIR/$POD"
    mkdir -p "$POD_DIR"
    
    # Copy each CSV file
    for CSV_FILE in "${CSV_FILES[@]}"; do
        echo "  📄 Copying $CSV_FILE..."
        
        # Check if file exists in container
        if kubectl exec -n "$NAMESPACE" "$POD" -- test -f "/app/$CSV_FILE" 2>/dev/null; then
            # Copy the file
            kubectl cp -n "$NAMESPACE" "$POD:/app/$CSV_FILE" "$POD_DIR/$CSV_FILE"
            
            # Check file size and show preview
            if [ -f "$POD_DIR/$CSV_FILE" ]; then
                FILE_SIZE=$(wc -c < "$POD_DIR/$CSV_FILE")
                LINE_COUNT=$(wc -l < "$POD_DIR/$CSV_FILE")
                echo "    ✅ Copied successfully ($FILE_SIZE bytes, $LINE_COUNT lines)"
                
                # Show first few lines if file has content
                if [ "$LINE_COUNT" -gt 1 ]; then
                    echo "    Preview:"
                    head -3 "$POD_DIR/$CSV_FILE" | sed 's/^/      /'
                fi
            else
                echo "    ❌ Copy failed"
            fi
        else
            echo "    ⚠️  File $CSV_FILE not found in container"
        fi
    done
    
    # Copy any other CSV files that might exist
    echo "  🔍 Looking for additional CSV files..."
    ADDITIONAL_CSV=$(kubectl exec -n "$NAMESPACE" "$POD" -- find /app -name "*.csv" -type f 2>/dev/null || true)
    
    if [ -n "$ADDITIONAL_CSV" ]; then
        echo "  Found additional CSV files:"
        echo "$ADDITIONAL_CSV" | while read -r csv_path; do
            if [ -n "$csv_path" ]; then
                csv_name=$(basename "$csv_path")
                echo "    📄 Copying $csv_name..."
                kubectl cp -n "$NAMESPACE" "$POD:$csv_path" "$POD_DIR/$csv_name" 2>/dev/null && \
                    echo "      ✅ Copied successfully" || \
                    echo "      ❌ Copy failed"
            fi
        done
    else
        echo "    No additional CSV files found"
    fi
    
    echo ""
done

# Summary
echo "=== Summary ==="
echo "Results copied to: $LOCAL_RESULTS_DIR"
echo "Directory structure:"
find "$LOCAL_RESULTS_DIR" -name "*.csv" -type f -exec ls -lh {} \; | sed 's/^/  /'

echo ""
echo "To view results:"
echo "  ls -la $LOCAL_RESULTS_DIR/*/"
echo "  cat $LOCAL_RESULTS_DIR/*/throughput_results.csv"

# Optional: Combine all results into a single summary
echo ""
echo "🔄 Creating combined summary..."
SUMMARY_FILE="$LOCAL_RESULTS_DIR/combined_summary.csv"

# Combine throughput results
if ls "$LOCAL_RESULTS_DIR"/*/throughput_results.csv >/dev/null 2>&1; then
    echo "timestamp,pod_name,mode,throughput,metric" > "$SUMMARY_FILE"
    
    for result_file in "$LOCAL_RESULTS_DIR"/*/throughput_results.csv; do
        pod_name=$(basename "$(dirname "$result_file")")
        tail -n +2 "$result_file" | sed "s/^/$(date -Iseconds),$pod_name,/" >> "$SUMMARY_FILE"
    done
    
    echo "✅ Combined summary created: $SUMMARY_FILE"
    echo "Summary preview:"
    head -5 "$SUMMARY_FILE" | sed 's/^/  /'
else
    echo "⚠️  No throughput_results.csv files found to combine"
fi

echo ""
echo "✅ Results collection complete!"