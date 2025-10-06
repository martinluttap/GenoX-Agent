#!/bin/bash

# ResNet Benchmark Docker Build and Push Script

# Configuration
IMAGE_NAME="resnet-benchmark"
TAG="latest"
REGISTRY="sushruth13" # Your Docker Hub username

echo "Building ResNet benchmark Docker image..."

# Build the Docker image with correct naming format
docker build -t ${REGISTRY}/${IMAGE_NAME}:${TAG} .

if [ $? -eq 0 ]; then
    echo "✅ Docker image built successfully: ${REGISTRY}/${IMAGE_NAME}:${TAG}"
    
    # Optional: Push to registry if REGISTRY is set
    if [ ! -z "$REGISTRY" ]; then
        echo "Logging in to Docker Hub..."
        echo "Please run 'docker login' first if not already logged in"
        echo "Pushing image to registry..."
        docker push ${REGISTRY}/${IMAGE_NAME}:${TAG}
        
        if [ $? -eq 0 ]; then
            echo "✅ Image pushed successfully to registry"
        else
            echo "❌ Failed to push image to registry"
            exit 1
        fi
    else
        echo "ℹ️  No registry specified. Image available locally only."
    fi
    
    echo "🚀 Ready to deploy with Kubernetes!"
    echo "   Run: kubectl apply -f kubernetes-deployment.yaml"
else
    echo "❌ Docker build failed"
    exit 1
fi