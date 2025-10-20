#!/bin/bash

# Spark Wikipedia Deployment and Monitoring Script
# This script deploys Spark job, monitors execution, and exports logs

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="default"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOYMENT_FILE="$SCRIPT_DIR/spark-wikipedia-deployment.yaml"

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

# Function to check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    if ! command -v kubectl &> /dev/null; then
        error "kubectl is not installed or not in PATH"
        exit 1
    fi
    
    if ! kubectl cluster-info &> /dev/null; then
        error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    if [ ! -f "$DEPLOYMENT_FILE" ]; then
        error "Deployment file not found: $DEPLOYMENT_FILE"
        exit 1
    fi
    
    info "All prerequisites satisfied"
}

# Function to clean up existing resources
cleanup_existing() {
    log "Cleaning up any existing Spark resources..."
    
    # Delete existing job (ignore errors if not found)
    kubectl delete job spark-wikipedia-job -n $NAMESPACE --ignore-not-found=true
    
    # Delete existing configmap (ignore errors if not found)
    kubectl delete configmap spark-wikipedia-config -n $NAMESPACE --ignore-not-found=true
    
    # Wait a bit for cleanup
    sleep 5
    
    info "Cleanup completed"
}

# Function to deploy resources
deploy_resources() {
    log "Deploying Spark Wikipedia analysis job..."
    
    kubectl apply -f "$DEPLOYMENT_FILE" -n $NAMESPACE
    
    info "Resources deployed successfully"
}

# Function to get pod name
get_spark_pod() {
    local pod_name=""
    for i in {1..60}; do
        pod_name=$(kubectl get pods -n $NAMESPACE -l app=spark-wikipedia -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
        if [ -n "$pod_name" ]; then
            echo "$pod_name"
            return 0
        fi
        sleep 5
    done
    return 1
}

# Function to monitor Spark job
monitor_spark_job() {
    log "Monitoring Spark job progress..."
    
    # Get Spark pod name
    local spark_pod=$(get_spark_pod)
    
    if [ -z "$spark_pod" ]; then
        error "Spark pod not found after waiting"
        return 1
    fi
    
    info "Found Spark pod: $spark_pod"
    
    # Wait for pod to be running
    info "Waiting for Spark pod to be running..."
    kubectl wait --for=condition=ready pod/$spark_pod -n $NAMESPACE --timeout=300s || {
        warning "Spark pod readiness check failed, but continuing to monitor..."
    }
    
    # Stream logs
    log "Streaming Spark job logs..."
    kubectl logs -f $spark_pod -n $NAMESPACE || true
    
    # Monitor job completion
    info "Monitoring Spark job completion..."
    local start_time=$(date +%s)
    local timeout=1800  # 30 minutes timeout
    
    while true; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        
        if [ $elapsed -gt $timeout ]; then
            error "Spark job timed out after $timeout seconds"
            return 1
        fi
        
        # Check job status
        local job_status=$(kubectl get job spark-wikipedia-job -n $NAMESPACE -o jsonpath='{.status.conditions[0].type}' 2>/dev/null)
        
        if [ "$job_status" = "Complete" ]; then
            log "Spark job completed successfully!"
            break
        elif [ "$job_status" = "Failed" ]; then
            error "Spark job failed"
            kubectl describe job spark-wikipedia-job -n $NAMESPACE
            return 1
        fi
        
        # Show progress
        local active=$(kubectl get job spark-wikipedia-job -n $NAMESPACE -o jsonpath='{.status.active}' 2>/dev/null)
        if [ "$active" = "1" ]; then
            echo "Spark job still running... (elapsed: ${elapsed}s)"
        fi
        
        sleep 10
    done
    
    return 0
}

# Function to export results
export_results() {
    log "Exporting results..."
    
    local spark_pod=$(get_spark_pod)
    if [ -z "$spark_pod" ]; then
        error "Cannot find Spark pod for export"
        return 1
    fi
    
    # Create export directory
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local export_dir="$SCRIPT_DIR/spark-logs_${timestamp}"
    mkdir -p "$export_dir"
    
    info "Export directory: $export_dir"
    
    # Copy throughput data
    log "Copying throughput data..."
    kubectl cp "$NAMESPACE/$spark_pod:/output/throughput-data.csv" "$export_dir/throughput-data.csv" 2>/dev/null || {
        warning "Could not copy throughput-data.csv"
    }
    
    # Copy detailed results
    log "Copying detailed results..."
    kubectl cp "$NAMESPACE/$spark_pod:/output/wikipedia-results.txt" "$export_dir/wikipedia-results.txt" 2>/dev/null || {
        warning "Could not copy wikipedia-results.txt"
    }
    
    # Export pod logs
    log "Exporting pod logs..."
    kubectl logs $spark_pod -n $NAMESPACE > "$export_dir/spark-job.log" 2>&1 || {
        warning "Could not export pod logs"
    }
    
    # Export job description
    log "Exporting job description..."
    kubectl describe job spark-wikipedia-job -n $NAMESPACE > "$export_dir/job-description.txt" 2>&1 || {
        warning "Could not export job description"
    }
    
    # Create summary
    log "Creating summary..."
    cat > "$export_dir/summary.txt" << EOF
Spark Wikipedia Network Analysis - Export Summary
==================================================
Export Date: $(date)
Namespace: $NAMESPACE
Pod Name: $spark_pod

Files Exported:
$(ls -lh "$export_dir")

EOF
    
    # Display throughput data if available
    if [ -f "$export_dir/throughput-data.csv" ]; then
        echo "" >> "$export_dir/summary.txt"
        echo "Throughput Data Preview:" >> "$export_dir/summary.txt"
        cat "$export_dir/throughput-data.csv" >> "$export_dir/summary.txt"
    fi
    
    log "Results exported to: $export_dir"
    
    # Display summary
    if [ -f "$export_dir/throughput-data.csv" ]; then
        echo ""
        log "Throughput Data:"
        cat "$export_dir/throughput-data.csv"
    fi
    
    return 0
}

# Function to show final status
show_final_status() {
    log "Showing final deployment status..."
    
    echo ""
    echo "=== SPARK JOB STATUS ==="
    kubectl get job spark-wikipedia-job -n $NAMESPACE -o wide || true
    kubectl get pods -l app=spark-wikipedia -n $NAMESPACE -o wide || true
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Deploy Spark Wikipedia analysis job and export results"
    echo ""
    echo "Options:"
    echo "  -n, --namespace NAMESPACE    Kubernetes namespace (default: default)"
    echo "  --no-cleanup                 Skip cleanup of existing resources"
    echo "  --no-export                  Skip automatic results export"
    echo "  -h, --help                   Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                           # Deploy with default settings"
    echo "  $0 -n my-namespace           # Deploy to specific namespace"
}

# Main function
main() {
    local skip_cleanup=false
    local skip_export=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -n|--namespace)
                NAMESPACE="$2"
                shift 2
                ;;
            --no-cleanup)
                skip_cleanup=true
                shift
                ;;
            --no-export)
                skip_export=true
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    log "Starting Spark Wikipedia deployment and monitoring..."
    info "Namespace: $NAMESPACE"
    info "Skip cleanup: $skip_cleanup"
    info "Skip export: $skip_export"
    
    # Check prerequisites
    check_prerequisites
    
    # Cleanup existing resources if requested
    if [ "$skip_cleanup" = false ]; then
        cleanup_existing
    fi
    
    # Deploy resources
    deploy_resources
    
    # Monitor Spark job
    if ! monitor_spark_job; then
        error "Spark job monitoring failed"
        show_final_status
        
        # Try to export results even on failure
        if [ "$skip_export" = false ]; then
            warning "Attempting to export results despite failure..."
            export_results || true
        fi
        
        exit 1
    fi
    
    # Export results automatically if requested
    if [ "$skip_export" = false ]; then
        export_results
    fi
    
    # Show final status
    show_final_status
    
    log "Spark Wikipedia deployment and monitoring completed successfully!"
    
    if [ "$skip_export" = true ]; then
        echo ""
        info "To export results manually, extract files from pod using:"
        info "kubectl cp <namespace>/<pod-name>:/output/throughput-data.csv ./throughput-data.csv"
    fi
}

# Run main function with all arguments
main "$@"
