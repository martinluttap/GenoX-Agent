#!/bin/bash

# Docker build and push script for XGBoost benchmark container

# Configuration
IMAGE_NAME="xgboost-benchmark"
TAG="latest"
REGISTRY="sushruth13" # Set your registry here (e.g., "your-registry.com" or "docker.io/username")

# Full image name
if [ -n "$REGISTRY" ]; then
    FULL_IMAGE_NAME="$REGISTRY/$IMAGE_NAME:$TAG"
else
    FULL_IMAGE_NAME="$IMAGE_NAME:$TAG"
fi

echo "Building Docker image: $FULL_IMAGE_NAME"

# Build the Docker image
docker build -t "$FULL_IMAGE_NAME" .

# Check if build was successful
if [ $? -eq 0 ]; then
    echo "✅ Docker image built successfully: $FULL_IMAGE_NAME"
    
    # Ask if user wants to push
    if [ -n "$REGISTRY" ]; then
        read -p "Do you want to push the image to the registry? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "Pushing image to registry..."
            docker push "$FULL_IMAGE_NAME"
            
            if [ $? -eq 0 ]; then
                echo "✅ Image pushed successfully to registry"
            else
                echo "❌ Failed to push image to registry"
                exit 1
            fi
        fi
    else
        echo "ℹ️  No registry configured. Skipping push."
        echo "   To push to a registry, set the REGISTRY variable in this script."
    fi
    
    echo ""
    echo "🐳 Container Commands:"
    echo "   Run locally:        docker run --rm -it $FULL_IMAGE_NAME"
    echo "   Run in background:  docker run -d --name xgboost-benchmark $FULL_IMAGE_NAME"
    echo "   View logs:          docker logs -f xgboost-benchmark"
    echo "   Copy CSV files:     docker cp xgboost-benchmark:/app/training_throughput.csv ."
    echo "                       docker cp xgboost-benchmark:/app/inference_throughput.csv ."
    echo "   Stop container:     docker stop xgboost-benchmark"
    
else
    echo "❌ Docker image build failed"
    exit 1
fi