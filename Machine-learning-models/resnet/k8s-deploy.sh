#!/bin/bash

# Kubernetes deployment script for ResNet benchmark

echo "Deploying ResNet benchmark to Kubernetes..."

# Apply the deployment
kubectl apply -f kubernetes-deployment.yaml

if [ $? -eq 0 ]; then
    echo "✅ Deployment applied successfully"
    
    echo "Checking deployment status..."
    kubectl get deployment resnet-benchmark
    
    echo ""
    echo "Checking pods..."
    kubectl get pods -l app=resnet-benchmark
    
    echo ""
    echo "📋 Useful commands:"
    echo "   Check logs: kubectl logs -l app=resnet-benchmark -f"
    echo "   Get pod details: kubectl describe pods -l app=resnet-benchmark"
    echo "   Scale deployment: kubectl scale deployment resnet-benchmark --replicas=3"
    echo "   Delete deployment: kubectl delete -f kubernetes-deployment.yaml"
else
    echo "❌ Failed to apply deployment"
    exit 1
fi