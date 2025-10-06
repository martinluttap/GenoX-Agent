#!/bin/bash

# Deploy SSD benchmark to Kubernetes
# Usage: ./k8s-deploy.sh [action]
# Actions: deploy, delete, status

ACTION=${1:-deploy}

case $ACTION in
    deploy)
        echo "Deploying SSD benchmark to Kubernetes..."
        kubectl apply -f kubernetes-deployment.yaml
        echo "Deployment submitted. Check status with:"
        echo "  kubectl get pods -l app=ssd-benchmark"
        echo "  kubectl logs -l app=ssd-benchmark -f"
        ;;
    delete)
        echo "Deleting SSD benchmark from Kubernetes..."
        kubectl delete -f kubernetes-deployment.yaml
        ;;
    status)
        echo "SSD Benchmark Status:"
        kubectl get pods -l app=ssd-benchmark
        kubectl get services -l app=ssd-benchmark
        ;;
    logs)
        echo "Getting logs from SSD benchmark..."
        kubectl logs -l app=ssd-benchmark -f
        ;;
    *)
        echo "Usage: $0 [deploy|delete|status|logs]"
        exit 1
        ;;
esac