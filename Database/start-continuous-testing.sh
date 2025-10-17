#!/bin/bash

# Wrapper script for continuous Cassandra stress testing
# Usage: ./start-continuous-testing.sh [quick|normal|intensive|custom]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STRESS_SCRIPT="$SCRIPT_DIR/continuous-stress-export.sh"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[$(date '+%H:%M:%S')]${NC} $1"
}

# Function to run stress testing with specific configuration
run_stress_testing() {
    local config=$1
    
    case $config in
        "quick")
            log "Starting QUICK stress testing (5 iterations, 2-minute intervals)"
            export INTERVAL_MINUTES=2
            export MAX_ITERATIONS=5
            export STRESS_OPERATIONS=10000
            ;;
        "normal")
            log "Starting NORMAL stress testing (20 iterations, 5-minute intervals)"
            export INTERVAL_MINUTES=5
            export MAX_ITERATIONS=20
            export STRESS_OPERATIONS=50000
            ;;
        "intensive")
            log "Starting INTENSIVE stress testing (100 iterations, 10-minute intervals)"
            export INTERVAL_MINUTES=10
            export MAX_ITERATIONS=100
            export STRESS_OPERATIONS=100000
            ;;
        "infinite")
            log "Starting INFINITE stress testing (continuous, 15-minute intervals)"
            export INTERVAL_MINUTES=15
            export MAX_ITERATIONS=999999
            export STRESS_OPERATIONS=50000
            ;;
        *)
            log "Using configuration from stress-test-config.env"
            ;;
    esac
    
    # Load additional config if exists
    if [ -f "$SCRIPT_DIR/stress-test-config.env" ]; then
        source "$SCRIPT_DIR/stress-test-config.env"
    fi
    
    # Start the stress testing
    "$STRESS_SCRIPT"
}

# Function to show current status
show_status() {
    log "Checking current stress testing status..."
    
    # Check if there are running jobs
    local running_jobs=$(kubectl get jobs -l app=cassandra-stress-test --no-headers 2>/dev/null | wc -l)
    if [ "$running_jobs" -gt 0 ]; then
        success "Active stress test jobs found:"
        kubectl get jobs -l app=cassandra-stress-test
        echo ""
        kubectl get pods -l app=cassandra-stress-test
    else
        log "No active stress test jobs found"
    fi
    
    # Check export directory
    if [ -d "./cassandra-stress-exports" ]; then
        local export_count=$(find ./cassandra-stress-exports -maxdepth 1 -type d -name "stress-test-*" | wc -l)
        success "Found $export_count exported stress test results"
        
        if [ -f "./cassandra-stress-exports/continuous-throughput-data.csv" ]; then
            log "Latest throughput results:"
            tail -5 "./cassandra-stress-exports/continuous-throughput-data.csv"
        fi
    fi
}

# Function to stop all stress testing
stop_stress_testing() {
    log "Stopping all stress testing..."
    
    # Kill any running continuous-stress-export.sh processes
    pkill -f "continuous-stress-export.sh" || true
    
    # Delete Kubernetes jobs
    kubectl delete job cassandra-stress-test --ignore-not-found=true
    
    success "Stress testing stopped"
}

# Function to view latest results
view_results() {
    if [ -f "./cassandra-stress-exports/continuous-throughput-data.csv" ]; then
        log "=== Latest Throughput Results ==="
        echo "iteration,timestamp,write_throughput,read_throughput,write_p99_lat,read_p99_lat"
        tail -10 "./cassandra-stress-exports/continuous-throughput-data.csv"
        echo ""
        
        # Show latest detailed results if available
        local latest_export=$(find ./cassandra-stress-exports -maxdepth 1 -type d -name "stress-test-*" | sort | tail -1)
        if [ -n "$latest_export" ] && [ -f "$latest_export/throughput-summary.log" ]; then
            log "=== Latest Detailed Results ==="
            cat "$latest_export/throughput-summary.log"
        fi
    else
        warning "No stress test results found yet"
    fi
}

# Help function
show_help() {
    cat << EOF
Cassandra Continuous Stress Testing Script
==========================================

Usage: $0 [COMMAND]

Commands:
  quick       Run quick stress test (5 iterations, 2-min intervals)
  normal      Run normal stress test (20 iterations, 5-min intervals)  
  intensive   Run intensive stress test (100 iterations, 10-min intervals)
  infinite    Run infinite stress test (continuous, 15-min intervals)
  
  status      Show current stress testing status
  stop        Stop all stress testing
  results     View latest results
  help        Show this help message

Examples:
  $0 quick                    # Quick 10-minute test
  $0 normal                   # 1.5-hour test  
  $0 intensive               # 16-hour test
  $0 infinite                # Continuous testing
  
  $0 status                  # Check what's running
  $0 results                 # View latest results
  $0 stop                    # Stop everything

Configuration:
  Edit stress-test-config.env to customize default settings
  
Results:
  Exported to: ./cassandra-stress-exports/
  CSV summary: ./cassandra-stress-exports/continuous-throughput-data.csv

EOF
}

# Main execution
case ${1:-help} in
    "quick"|"normal"|"intensive"|"infinite"|"custom")
        run_stress_testing "$1"
        ;;
    "status")
        show_status
        ;;
    "stop")
        stop_stress_testing
        ;;
    "results")
        view_results
        ;;
    "help"|*)
        show_help
        ;;
esac