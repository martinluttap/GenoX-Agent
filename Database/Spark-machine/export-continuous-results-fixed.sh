#!/bin/bash

# Export Spark Continuous Results Script
# Exports the single CSV and text files from the running Spark pod

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="${1:-default}"
EXPORT_DIR="./spark-continuous-export_$(date +%Y%m%d_%H%M%S)"

# Logging functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" >&2
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

# Main script
main() {
    log "Starting Spark continuous results export..."
    info "Namespace: $NAMESPACE"
    
    # Find Spark pod
    log "Finding Spark pod in namespace: $NAMESPACE"
    POD_NAME=$(kubectl get pods -n $NAMESPACE -l app=spark-wikipedia -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    
    if [ -z "$POD_NAME" ]; then
        error "No Spark pod found in namespace $NAMESPACE"
        error "Make sure the Spark deployment is running:"
        error "  kubectl get pods -n $NAMESPACE -l app=spark-wikipedia"
        exit 1
    fi
    
    info "Found Spark pod: $POD_NAME"
    
    # Create export directory
    log "Creating export directory: $EXPORT_DIR"
    mkdir -p "$EXPORT_DIR/output"
    
    # Copy files
    log "Copying files from /output directory..."
    FILES_COPIED=0
    
    # Copy continuous-throughput.csv
    log "Copying continuous-throughput.csv..."
    KUBECTL_OUTPUT=$(kubectl cp "$NAMESPACE/$POD_NAME:/output/continuous-throughput.csv" "$EXPORT_DIR/output/continuous-throughput.csv" 2>&1)
    KUBECTL_EXIT=$?
    
    if [ $KUBECTL_EXIT -eq 0 ] && [ -f "$EXPORT_DIR/output/continuous-throughput.csv" ]; then
        SIZE=$(du -h "$EXPORT_DIR/output/continuous-throughput.csv" | cut -f1)
        LINES=$(wc -l < "$EXPORT_DIR/output/continuous-throughput.csv")
        info "✓ continuous-throughput.csv copied ($SIZE, $LINES lines)"
        FILES_COPIED=$((FILES_COPIED + 1))
    else
        warning "✗ Could not copy continuous-throughput.csv"
        if [[ ! "$KUBECTL_OUTPUT" =~ "tar: Removing leading" ]]; then
            warning "Error: $KUBECTL_OUTPUT"
        fi
    fi
    
    # Copy continuous-results.txt
    log "Copying continuous-results.txt..."
    KUBECTL_OUTPUT=$(kubectl cp "$NAMESPACE/$POD_NAME:/output/continuous-results.txt" "$EXPORT_DIR/output/continuous-results.txt" 2>&1)
    KUBECTL_EXIT=$?
    
    if [ $KUBECTL_EXIT -eq 0 ] && [ -f "$EXPORT_DIR/output/continuous-results.txt" ]; then
        SIZE=$(du -h "$EXPORT_DIR/output/continuous-results.txt" | cut -f1)
        LINES=$(wc -l < "$EXPORT_DIR/output/continuous-results.txt")
        info "✓ continuous-results.txt copied ($SIZE, $LINES lines)"
        FILES_COPIED=$((FILES_COPIED + 1))
    else
        warning "✗ Could not copy continuous-results.txt"
        if [[ ! "$KUBECTL_OUTPUT" =~ "tar: Removing leading" ]]; then
            warning "Error: $KUBECTL_OUTPUT"
        fi
    fi
    
    # Check for additional files
    log "Checking for additional files..."
    ADDITIONAL_FILES=$(kubectl exec $POD_NAME -n $NAMESPACE -- find /output -type f -name "*.csv" -o -name "*.txt" -o -name "*.log" 2>/dev/null | grep -v "continuous-" || true)
    
    if [ -n "$ADDITIONAL_FILES" ]; then
        info "Found additional files:"
        echo "$ADDITIONAL_FILES"
        
        echo "$ADDITIONAL_FILES" | while read filepath; do
            if [ -n "$filepath" ]; then
                filename=$(basename "$filepath")
                log "Copying additional file: $filename"
                kubectl_output=$(kubectl cp "$NAMESPACE/$POD_NAME:$filepath" "$EXPORT_DIR/output/$filename" 2>&1)
                if [ $? -eq 0 ] && [ -f "$EXPORT_DIR/output/$filename" ]; then
                    info "✓ $filename copied"
                else
                    warning "✗ Could not copy $filename"
                fi
            fi
        done
    fi
    
    # Export pod logs
    log "Exporting pod logs..."
    if kubectl logs $POD_NAME -n $NAMESPACE > "$EXPORT_DIR/pod-logs.txt" 2>&1; then
        LINES=$(wc -l < "$EXPORT_DIR/pod-logs.txt")
        info "✓ pod-logs.txt exported ($LINES lines)"
    else
        warning "✗ Could not export pod logs"
    fi
    
    # Create summary
    log "Creating export summary..."
    cat > "$EXPORT_DIR/export-summary.txt" << EOF
Spark Continuous Results Export Summary
======================================
Export Date: $(date)
Namespace: $NAMESPACE
Pod Name: $POD_NAME
Export Directory: $EXPORT_DIR

Files Copied: $FILES_COPIED

Directory Structure:
$(find "$EXPORT_DIR" -type f -exec ls -lh {} \; | sed 's|'$EXPORT_DIR'|.|g')
EOF

    # Add file previews
    if [ -f "$EXPORT_DIR/output/continuous-throughput.csv" ]; then
        echo "" >> "$EXPORT_DIR/export-summary.txt"
        echo "Throughput Data Preview (last 10 entries):" >> "$EXPORT_DIR/export-summary.txt"
        tail -n 10 "$EXPORT_DIR/output/continuous-throughput.csv" >> "$EXPORT_DIR/export-summary.txt"
    fi
    
    if [ -f "$EXPORT_DIR/output/continuous-results.txt" ]; then
        echo "" >> "$EXPORT_DIR/export-summary.txt"
        echo "Results Summary (last 20 lines):" >> "$EXPORT_DIR/export-summary.txt"
        tail -n 20 "$EXPORT_DIR/output/continuous-results.txt" >> "$EXPORT_DIR/export-summary.txt"
    fi
    
    # Show results
    log "Export completed successfully!"
    echo ""
    echo "📂 Export Directory: $EXPORT_DIR"
    echo "📊 Files exported:"
    find "$EXPORT_DIR" -type f -exec ls -lh {} \; | sed "s|$EXPORT_DIR|.|g"
    
    echo ""
    if [ -f "$EXPORT_DIR/output/continuous-throughput.csv" ] && [ -s "$EXPORT_DIR/output/continuous-throughput.csv" ]; then
        echo "📈 Latest Throughput Data (last 5 entries):"
        tail -n 6 "$EXPORT_DIR/output/continuous-throughput.csv" | column -t -s ','
    else
        warning "No throughput data available"
    fi
    
    echo ""
    if [ $FILES_COPIED -gt 0 ]; then
        info "Export successful! Files are in: $EXPORT_DIR/output/"
    else
        error "No files were copied!"
        exit 1
    fi
}

# Run main function
main "$@"