#!/bin/bash

# Kubernetes Deployment Script for XGBoost Benchmark
# This script helps deploy and manage the XGBoost benchmark on Kubernetes

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 XGBoost Benchmark Kubernetes Deployment Script${NC}"
echo ""

# Function to check if kubectl is available
check_kubectl() {
    if ! command -v kubectl &> /dev/null; then
        echo -e "${RED}❌ kubectl is not installed or not in PATH${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ kubectl found${NC}"
}

# Function to check cluster connection
check_cluster() {
    if ! kubectl cluster-info &> /dev/null; then
        echo -e "${RED}❌ Cannot connect to Kubernetes cluster${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Connected to Kubernetes cluster${NC}"
    kubectl cluster-info | head -1
}

# Function to deploy the application
deploy() {
    echo -e "\n${YELLOW}📦 Deploying XGBoost Benchmark...${NC}"
    
    # Apply the Kubernetes manifests
    kubectl apply -f kubernetes-deployment.yaml
    
    echo -e "${GREEN}✅ Deployment applied successfully${NC}"
    
    # Wait for deployment to be ready
    echo -e "\n${YELLOW}⏳ Waiting for deployment to be ready...${NC}"
    kubectl wait --for=condition=available --timeout=300s deployment/xgboost-benchmark
    
    echo -e "${GREEN}✅ Deployment is ready!${NC}"
}

# Function to show deployment status
status() {
    echo -e "\n${BLUE}📊 Deployment Status:${NC}"
    kubectl get pods -l app=xgboost-benchmark
    kubectl get svc xgboost-benchmark-service
    kubectl get pvc xgboost-benchmark-pvc
}

# Function to show logs
logs() {
    echo -e "\n${BLUE}📋 Container Logs:${NC}"
    POD_NAME=$(kubectl get pods -l app=xgboost-benchmark -o jsonpath='{.items[0].metadata.name}')
    kubectl logs -f $POD_NAME
}

# Function to get benchmark data
get_data() {
    echo -e "\n${BLUE}📊 Extracting benchmark data...${NC}"
    POD_NAME=$(kubectl get pods -l app=xgboost-benchmark -o jsonpath='{.items[0].metadata.name}')
    
    echo "Copying training throughput data..."
    kubectl cp $POD_NAME:/app/training_throughput.csv ./training_throughput.csv 2>/dev/null || echo "Training data not yet available"
    
    echo "Copying inference throughput data..."
    kubectl cp $POD_NAME:/app/inference_throughput.csv ./inference_throughput.csv 2>/dev/null || echo "Inference data not yet available"
    
    echo "Copying logs..."
    kubectl cp $POD_NAME:/app/xgboost_performance.log ./xgboost_performance.log 2>/dev/null || echo "Log file not yet available"
    
    echo -e "${GREEN}✅ Data extraction completed${NC}"
    ls -la *.csv *.log 2>/dev/null || echo "No files found yet"
}

# Function to monitor benchmark
monitor() {
    echo -e "\n${BLUE}📈 Monitoring benchmark (press Ctrl+C to stop)...${NC}"
    POD_NAME=$(kubectl get pods -l app=xgboost-benchmark -o jsonpath='{.items[0].metadata.name}')
    
    while true; do
        echo -e "\n${YELLOW}=== $(date) ===${NC}"
        
        # Check if CSV files exist and show stats
        kubectl exec $POD_NAME -- sh -c '
            if [ -f /app/training_throughput.csv ]; then
                echo "Training iterations: $(tail -n +2 /app/training_throughput.csv | wc -l)"
                echo "Latest training throughput: $(tail -n 1 /app/training_throughput.csv | cut -d"," -f3) examples/sec"
            else
                echo "Training data not yet available"
            fi
            
            if [ -f /app/inference_throughput.csv ]; then
                echo "Inference iterations: $(tail -n +2 /app/inference_throughput.csv | wc -l)"
                echo "Latest inference throughput: $(tail -n 1 /app/inference_throughput.csv | cut -d"," -f3) examples/sec"
            else
                echo "Inference data not yet available"
            fi
        ' 2>/dev/null || echo "Pod not ready yet"
        
        # Show resource usage
        kubectl top pod $POD_NAME 2>/dev/null || echo "Metrics not available"
        
        sleep 60
    done
}

# Function to cleanup
cleanup() {
    echo -e "\n${YELLOW}🧹 Cleaning up deployment...${NC}"
    kubectl delete -f kubernetes-deployment.yaml
    echo -e "${GREEN}✅ Cleanup completed${NC}"
}

# Function to scale deployment
scale() {
    REPLICAS=${1:-1}
    echo -e "\n${YELLOW}📈 Scaling deployment to $REPLICAS replicas...${NC}"
    kubectl scale deployment xgboost-benchmark --replicas=$REPLICAS
    kubectl wait --for=condition=available --timeout=300s deployment/xgboost-benchmark
    echo -e "${GREEN}✅ Scaling completed${NC}"
}

# Main menu
case "${1:-}" in
    "deploy")
        check_kubectl
        check_cluster
        deploy
        status
        echo -e "\n${GREEN}🎉 XGBoost Benchmark deployed successfully!${NC}"
        echo -e "\n${BLUE}Next steps:${NC}"
        echo "  Monitor: ./k8s-deploy.sh monitor"
        echo "  Get data: ./k8s-deploy.sh get-data"
        echo "  View logs: ./k8s-deploy.sh logs"
        echo "  Cleanup: ./k8s-deploy.sh cleanup"
        ;;
    "status")
        check_kubectl
        status
        ;;
    "logs")
        check_kubectl
        logs
        ;;
    "get-data")
        check_kubectl
        get_data
        ;;
    "monitor")
        check_kubectl
        monitor
        ;;
    "scale")
        check_kubectl
        scale $2
        ;;
    "cleanup")
        check_kubectl
        cleanup
        ;;
    *)
        echo -e "${BLUE}XGBoost Benchmark Kubernetes Deployment${NC}"
        echo ""
        echo "Usage: $0 {deploy|status|logs|get-data|monitor|scale|cleanup}"
        echo ""
        echo "Commands:"
        echo "  deploy     - Deploy the XGBoost benchmark to Kubernetes"
        echo "  status     - Show deployment status"
        echo "  logs       - Show container logs (follow mode)"
        echo "  get-data   - Extract CSV and log files from the container"
        echo "  monitor    - Monitor benchmark progress in real-time"
        echo "  scale [n]  - Scale deployment to n replicas (default: 1)"
        echo "  cleanup    - Remove all deployed resources"
        echo ""
        echo "Examples:"
        echo "  $0 deploy          # Deploy the benchmark"
        echo "  $0 monitor         # Monitor benchmark progress"
        echo "  $0 get-data        # Download CSV files"
        echo "  $0 scale 3         # Scale to 3 replicas"
        echo "  $0 cleanup         # Remove everything"
        exit 1
        ;;
esac