#!/bin/bash

# Cassandra Continuous Stress Test and Export Script
# This script runs stress tests and exports results continuously

set -e

# Configuration
EXPORT_DIR="./cassandra-stress-exports"
NAMESPACE="default"
STRESS_TEST_YAML="./Cassandra/cassandra-stress-test.yaml"
LOG_FILE="./cassandra-continuous-test.log"
INTERVAL_SECONDS=300
MAX_ITERATIONS=2

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS:${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

# Function to check if Cassandra is healthy
check_cassandra_health() {
    log "Checking Cassandra cluster health..."
    
    local healthy_pods=$(kubectl get pods -l app=cassandra --no-headers | grep "Running" | wc -l)
    local total_pods=$(kubectl get pods -l app=cassandra --no-headers | wc -l)
    
    if [ "$healthy_pods" -eq "$total_pods" ] && [ "$total_pods" -gt 0 ]; then
        success "Cassandra cluster healthy: $healthy_pods/$total_pods pods running"
        return 0
    else
        error "Cassandra cluster unhealthy: $healthy_pods/$total_pods pods running"
        return 1
    fi
}

# Function to run stress test
run_stress_test() {
    local iteration=$1
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local test_name="stress-test-${iteration}-${timestamp}"
    
    log "Starting stress test iteration $iteration (${test_name})"
    
    # Clean up any existing stress test jobs
    kubectl delete job cassandra-stress-test --ignore-not-found=true
    sleep 5
    
    # Deploy new stress test
    kubectl apply -f "$STRESS_TEST_YAML"
    
    # Wait for pod to be ready
    log "Waiting for stress test pod to be ready..."
    local max_wait=300  # 5 minutes
    local wait_time=0
    
    while [ $wait_time -lt $max_wait ]; do
        local pod_status=$(kubectl get pods -l app=cassandra-stress-test --no-headers 2>/dev/null | awk '{print $3}' || echo "NotFound")
        
        if [ "$pod_status" = "Running" ]; then
            success "Stress test pod is running"
            break
        elif [ "$pod_status" = "Failed" ] || [ "$pod_status" = "Error" ]; then
            error "Stress test pod failed to start"
            return 1
        fi
        
        sleep 10
        wait_time=$((wait_time + 10))
        log "Waiting for pod... (${wait_time}s/${max_wait}s)"
    done
    
    if [ $wait_time -ge $max_wait ]; then
        error "Timeout waiting for stress test pod to start"
        return 1
    fi
    
    # Get pod name
    local pod_name=$(kubectl get pods -l app=cassandra-stress-test --no-headers | awk '{print $1}')
    
    # Wait for stress test to complete
    log "Waiting for stress test to complete..."
    max_wait=600  # 10 minutes
    wait_time=0
    
    while [ $wait_time -lt $max_wait ]; do
        local job_status=$(kubectl get job cassandra-stress-test --no-headers 2>/dev/null | awk '{print $2}' || echo "NotFound")
        
        if [[ "$job_status" == *"1/1"* ]]; then
            success "Stress test completed successfully"
            break
        elif [[ "$job_status" == *"0/1"* ]]; then
            # Check if it failed
            local pod_status=$(kubectl get pods -l app=cassandra-stress-test --no-headers | awk '{print $3}')
            if [ "$pod_status" = "Failed" ] || [ "$pod_status" = "Error" ]; then
                error "Stress test failed"
                return 1
            fi
        fi
        
        sleep 15
        wait_time=$((wait_time + 15))
        log "Stress test running... (${wait_time}s/${max_wait}s)"
    done
    
    if [ $wait_time -ge $max_wait ]; then
        error "Timeout waiting for stress test to complete"
        return 1
    fi
    
    # Export results
    export_stress_results "$iteration" "$timestamp" "$pod_name"
    
    return 0
}

# Function to export stress test results
export_stress_results() {
    local iteration=$1
    local timestamp=$2
    local pod_name=$3
    local export_subdir="${EXPORT_DIR}/stress-test-${iteration}-${timestamp}"
    
    log "Exporting stress test results to $export_subdir"
    
    mkdir -p "$export_subdir"
    
    # Export stress test logs
    kubectl exec "$pod_name" -- ls -la /logs/ > "${export_subdir}/file-list.txt" 2>/dev/null || true
    
    # Export individual log files
    for log_file in stress-write.log stress-read.log stress-test-results.log throughput-data.csv; do
        if kubectl exec "$pod_name" -- test -f "/logs/$log_file" 2>/dev/null; then
            kubectl exec "$pod_name" -- cat "/logs/$log_file" > "${export_subdir}/$log_file"
            success "Exported $log_file"
        else
            warning "Log file $log_file not found"
        fi
    done
    
    # Parse and create summary
    create_throughput_summary "$export_subdir" "$iteration" "$timestamp"
    
    # Export pod logs for debugging
    kubectl logs "$pod_name" > "${export_subdir}/pod-logs.txt" 2>/dev/null || true
    
    # Export Cassandra status
    export_cassandra_status "$export_subdir"
    
    success "Results exported to $export_subdir"
}

# Function to create throughput summary
create_throughput_summary() {
    local export_dir=$1
    local iteration=$2
    local timestamp=$3
    
    local write_log="${export_dir}/stress-write.log"
    local read_log="${export_dir}/stress-read.log"
    local summary_file="${export_dir}/throughput-summary.log"
    
    cat > "$summary_file" << EOF
# Cassandra Stress Test Results - Iteration $iteration
# Generated: $(date)
# Timestamp: $timestamp

[TEST_INFO]
iteration=$iteration
timestamp=$timestamp
test_date=$(date '+%Y-%m-%d %H:%M:%S')

EOF
    
    # Parse write results
    if [ -f "$write_log" ]; then
        local write_throughput=$(grep "Op rate" "$write_log" | grep -o '[0-9,]*' | head -1 | tr -d ',')
        local write_mean_lat=$(grep "Latency mean" "$write_log" | grep -o '[0-9.]*' | head -1)
        local write_p95_lat=$(grep "Latency 95th percentile" "$write_log" | grep -o '[0-9.]*' | head -1)
        local write_p99_lat=$(grep "Latency 99th percentile" "$write_log" | grep -o '[0-9.]*' | head -1)
        
        cat >> "$summary_file" << EOF
[WRITE_PERFORMANCE]
throughput_ops_sec=$write_throughput
mean_latency_ms=$write_mean_lat
p95_latency_ms=$write_p95_lat
p99_latency_ms=$write_p99_lat

EOF
    fi
    
    # Parse read results
    if [ -f "$read_log" ]; then
        local read_throughput=$(grep "Op rate" "$read_log" | grep -o '[0-9,]*' | head -1 | tr -d ',')
        local read_mean_lat=$(grep "Latency mean" "$read_log" | grep -o '[0-9.]*' | head -1)
        local read_p95_lat=$(grep "Latency 95th percentile" "$read_log" | grep -o '[0-9.]*' | head -1)
        local read_p99_lat=$(grep "Latency 99th percentile" "$read_log" | grep -o '[0-9.]*' | head -1)
        
        cat >> "$summary_file" << EOF
[READ_PERFORMANCE]
throughput_ops_sec=$read_throughput
mean_latency_ms=$read_mean_lat
p95_latency_ms=$read_p95_lat
p99_latency_ms=$read_p99_lat

EOF
    fi
    
    # Create CSV entry
    local csv_file="${EXPORT_DIR}/continuous-throughput-data.csv"
    
    if [ ! -f "$csv_file" ]; then
        echo "iteration,timestamp,write_throughput,read_throughput,write_p99_lat,read_p99_lat" > "$csv_file"
    fi
    
    local write_throughput=$(grep "throughput_ops_sec=" "$summary_file" | head -1 | cut -d'=' -f2)
    local read_throughput=$(grep "throughput_ops_sec=" "$summary_file" | tail -1 | cut -d'=' -f2)
    local write_p99=$(grep "p99_latency_ms=" "$summary_file" | head -1 | cut -d'=' -f2)
    local read_p99=$(grep "p99_latency_ms=" "$summary_file" | tail -1 | cut -d'=' -f2)
    
    echo "$iteration,$timestamp,$write_throughput,$read_throughput,$write_p99,$read_p99" >> "$csv_file"
}

# Function to export Cassandra status
export_cassandra_status() {
    local export_dir=$1
    
    log "Exporting Cassandra cluster status..."
    
    # Get pod status
    kubectl get pods -l app=cassandra -o wide > "${export_dir}/cassandra-pods.txt" 2>/dev/null || true
    
    # Get service status
    kubectl get svc cassandra-service -o yaml > "${export_dir}/cassandra-service.yaml" 2>/dev/null || true
    
    # Get nodetool status from first Cassandra pod
    local cassandra_pod=$(kubectl get pods -l app=cassandra --no-headers | head -1 | awk '{print $1}')
    if [ -n "$cassandra_pod" ]; then
        kubectl exec "$cassandra_pod" -- nodetool status > "${export_dir}/nodetool-status.txt" 2>/dev/null || true
        kubectl exec "$cassandra_pod" -- nodetool info > "${export_dir}/nodetool-info.txt" 2>/dev/null || true
    fi
}

# Function to cleanup old exports (keep last 10)
cleanup_old_exports() {
    if [ -d "$EXPORT_DIR" ]; then
        local export_count=$(find "$EXPORT_DIR" -maxdepth 1 -type d -name "stress-test-*" | wc -l)
        if [ "$export_count" -gt 10 ]; then
            log "Cleaning up old exports (keeping last 10)..."
            find "$EXPORT_DIR" -maxdepth 1 -type d -name "stress-test-*" | sort | head -n $((export_count - 10)) | xargs rm -rf
        fi
    fi
}

# Main execution loop
main() {
    log "Starting Cassandra Continuous Stress Test and Export Script"
    log "Export directory: $EXPORT_DIR"
    log "Test interval: $INTERVAL_SECONDS seconds"
    log "Max iterations: $MAX_ITERATIONS"
    
    # Create export directory
    mkdir -p "$EXPORT_DIR"
    
    # Initialize CSV file
    local csv_file="${EXPORT_DIR}/continuous-throughput-data.csv"
    if [ ! -f "$csv_file" ]; then
        echo "iteration,timestamp,write_throughput,read_throughput,write_p99_lat,read_p99_lat" > "$csv_file"
    fi
    
    local iteration=1
    
    while [ $iteration -le $MAX_ITERATIONS ]; do
        log "=== Starting iteration $iteration/$MAX_ITERATIONS ==="
        
        # Check Cassandra health
        if ! check_cassandra_health; then
            error "Cassandra cluster is unhealthy, skipping iteration $iteration"
            sleep 60
            continue
        fi
        
        # Run stress test
        if run_stress_test "$iteration"; then
            success "Iteration $iteration completed successfully"
        else
            error "Iteration $iteration failed"
        fi
        
        # Cleanup old exports
        cleanup_old_exports
        
        # Show current summary
        log "Current throughput summary:"
        tail -5 "$csv_file" | while read line; do
            log "  $line"
        done
        
        iteration=$((iteration + 1))
        
        if [ $iteration -le $MAX_ITERATIONS ]; then
            log "Waiting $INTERVAL_SECONDS seconds before next iteration..."
            sleep $INTERVAL_SECONDS
        fi
    done
    
    success "Continuous stress testing completed after $MAX_ITERATIONS iterations"
    log "Final results available in: $EXPORT_DIR/continuous-throughput-data.csv"
}

# Signal handlers
cleanup() {
    log "Received interrupt signal, cleaning up..."
    kubectl delete job cassandra-stress-test --ignore-not-found=true
    exit 0
}

trap cleanup INT TERM

# Check dependencies
command -v kubectl >/dev/null 2>&1 || { error "kubectl is required but not installed. Aborting."; exit 1; }

# Check if stress test YAML exists
if [ ! -f "$STRESS_TEST_YAML" ]; then
    error "Stress test YAML file not found: $STRESS_TEST_YAML"
    exit 1
fi

# Start main execution
main "$@"