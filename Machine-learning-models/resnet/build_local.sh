#!/bin/bash

# ResNet Benchmark Docker Build Script (Local Only)

# Configuration
IMAGE_NAME="resnet-benchmark"
TAG="latest"

echo "Building ResNet benchmark Docker image locally..."

# Build the Docker image
docker build -t ${IMAGE_NAME}:${TAG} .

if [ $? -eq 0 ]; then
    echo "✅ Docker image built successfully: ${IMAGE_NAME}:${TAG}"
    echo "🚀 Ready to deploy with Kubernetes!"
    echo "   Run: kubectl apply -f kubernetes-deployment-local.yaml"
else
    echo "❌ Docker build failed"
    exit 1
fi