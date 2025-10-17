#!/bin/bash

# Cassandra YCSB Deployment and Monitoring Script
# This script deploys Cassandra and YCSB, monitors the execution, and exports logs

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
DEPLOYMENT_FILE="$SCRIPT_DIR/cassandra-ycsb-deployment.yaml"
EXPORT_SCRIPT="$SCRIPT_DIR/export-cassandra-ycsb-logs.sh"

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
    
    if [ ! -f "$EXPORT_SCRIPT" ]; then
        error "Export script not found: $EXPORT_SCRIPT"
        exit 1
    fi
    
    if [ ! -x "$EXPORT_SCRIPT" ]; then
        warning "Export script is not executable, making it executable..."
        chmod +x "$EXPORT_SCRIPT"
    fi
    
    info "All prerequisites satisfied"
}

# Function to clean up existing resources
cleanup_existing() {
    log "Cleaning up any existing Cassandra/YCSB resources..."
    
    # Delete existing job (ignore errors if not found)
    kubectl delete job ycsb-benchmark -n $NAMESPACE --ignore-not-found=true
    
    # Delete existing deployment (ignore errors if not found)
    kubectl delete deployment cassandra -n $NAMESPACE --ignore-not-found=true
    
    # Delete existing service (ignore errors if not found)
    kubectl delete service cassandra-service -n $NAMESPACE --ignore-not-found=true
    
    # Delete existing configmap (ignore errors if not found)
    kubectl delete configmap ycsb-workloads -n $NAMESPACE --ignore-not-found=true
    
    # Wait a bit for cleanup
    sleep 10
    
    info "Cleanup completed"
}

# Function to deploy resources
deploy_resources() {
    log "Deploying Cassandra and YCSB resources..."
    
    kubectl apply -f "$DEPLOYMENT_FILE" -n $NAMESPACE
    
    info "Resources deployed successfully"
}

# Function to monitor deployment
monitor_deployment() {
    log "Monitoring deployment progress..."
    
    # Wait for Cassandra to be ready
    info "Waiting for Cassandra deployment to be ready..."
    kubectl wait --for=condition=available deployment/cassandra -n $NAMESPACE --timeout=300s || {
        error "Cassandra deployment failed to become ready"
        return 1
    }
    
    # Wait for Cassandra pod to be ready
    info "Waiting for Cassandra pod to be ready..."
    kubectl wait --for=condition=ready pod -l app=cassandra -n $NAMESPACE --timeout=300s || {
        error "Cassandra pod failed to become ready"
        return 1
    }
    
    info "Cassandra is ready"
    
    # Wait for YCSB job to start
    info "Waiting for YCSB job to start..."
    for i in {1..30}; do
        if kubectl get job ycsb-benchmark -n $NAMESPACE &> /dev/null; then
            info "YCSB job started"
            break
        fi
        sleep 10
    done
    
    return 0
}

# Function to monitor YCSB progress
monitor_ycsb() {
    log "Monitoring YCSB benchmark progress..."
    
    # Get YCSB pod name
    local ycsb_pod=""
    for i in {1..60}; do
        ycsb_pod=$(kubectl get pods -n $NAMESPACE -l app=ycsb-benchmark -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
        if [ -n "$ycsb_pod" ]; then
            info "Found YCSB pod: $ycsb_pod"
            break
        fi
        echo "Waiting for YCSB pod to be created... (attempt $i/60)"
        sleep 10
    done
    
    if [ -z "$ycsb_pod" ]; then
        error "YCSB pod not found after waiting"
        return 1
    fi
    
    # Wait for pod to be running
    info "Waiting for YCSB pod to be running..."
    kubectl wait --for=condition=ready pod/$ycsb_pod -n $NAMESPACE --timeout=300s || {
        warning "YCSB pod readiness check failed, but continuing to monitor..."
    }
    
    # Monitor job completion
    info "Monitoring YCSB job completion..."
    local start_time=$(date +%s)
    local timeout=3600  # 1 hour timeout
    
    while true; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        
        if [ $elapsed -gt $timeout ]; then
            error "YCSB job timed out after $timeout seconds"
            return 1
        fi
        
        # Check job status
        local job_status=$(kubectl get job ycsb-benchmark -n $NAMESPACE -o jsonpath='{.status.conditions[0].type}' 2>/dev/null)
        
        if [ "$job_status" = "Complete" ]; then
            log "YCSB job completed successfully!"
            break
        elif [ "$job_status" = "Failed" ]; then
            error "YCSB job failed"
            kubectl describe job ycsb-benchmark -n $NAMESPACE
            return 1
        fi
        
        # Show progress
        local active=$(kubectl get job ycsb-benchmark -n $NAMESPACE -o jsonpath='{.status.active}' 2>/dev/null)
        if [ "$active" = "1" ]; then
            echo "YCSB job still running... (elapsed: ${elapsed}s)"
        fi
        
        sleep 30
    done
    
    return 0
}

# Function to export logs automatically
auto_export_logs() {
    log "Automatically exporting logs..."
    
    # Wait a bit for any final log writes
    sleep 30
    
    # Run the export script
    if "$EXPORT_SCRIPT" -n $NAMESPACE -c; then
        log "Logs exported successfully"
    else
        error "Failed to export logs"
        return 1
    fi
}

# Function to show final status
show_final_status() {
    log "Showing final deployment status..."
    
    echo ""
    echo "=== CASSANDRA STATUS ==="
    kubectl get deployment cassandra -n $NAMESPACE -o wide || true
    kubectl get pods -l app=cassandra -n $NAMESPACE -o wide || true
    
    echo ""
    echo "=== YCSB JOB STATUS ==="
    kubectl get job ycsb-benchmark -n $NAMESPACE -o wide || true
    kubectl get pods -l app=ycsb-benchmark -n $NAMESPACE -o wide || true
    
    echo ""
    echo "=== SERVICES ==="
    kubectl get svc -l app=cassandra -n $NAMESPACE || true
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Deploy Cassandra with YCSB benchmark and export logs"
    echo ""
    echo "Options:"
    echo "  -n, --namespace NAMESPACE    Kubernetes namespace (default: default)"
    echo "  --no-cleanup                 Skip cleanup of existing resources"
    echo "  --no-export                  Skip automatic log export"
    echo "  -h, --help                   Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                           # Deploy with default settings"
    echo "  $0 -n my-namespace           # Deploy to specific namespace"
    echo "  $0 --no-cleanup              # Deploy without cleaning up existing resources"
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
    
    log "Starting Cassandra YCSB deployment and monitoring..."
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
    
    # Monitor deployment
    if ! monitor_deployment; then
        error "Deployment monitoring failed"
        show_final_status
        exit 1
    fi
    
    # Monitor YCSB benchmark
    if ! monitor_ycsb; then
        error "YCSB monitoring failed"
        show_final_status
        exit 1
    fi
    
    # Export logs automatically if requested
    if [ "$skip_export" = false ]; then
        auto_export_logs
    fi
    
    # Show final status
    show_final_status
    
    log "Cassandra YCSB deployment and monitoring completed successfully!"
    
    if [ "$skip_export" = true ]; then
        echo ""
        info "To export logs manually, run:"
        info "$EXPORT_SCRIPT -n $NAMESPACE -c"
    fi
}

# Run main function with all arguments
main "$@"