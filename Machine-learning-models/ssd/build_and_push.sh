#!/bin/bash

# Build and push SSD Docker image
# Usage: ./build_and_push.sh [tag]

TAG=${1:-latest}
IMAGE_NAME="ssd-benchmark"
REGISTRY="sushruth13"  # Replace with your actual registry

echo "Building SSD Docker image with PyTorch base image..."
echo "Using PyTorch base image with pre-installed ML dependencies for faster builds..."
docker build -t $IMAGE_NAME:$TAG .

if [ $? -eq 0 ]; then
    echo "Build successful! Tagging for registry..."
    docker tag $IMAGE_NAME:$TAG $REGISTRY/$IMAGE_NAME:$TAG
    
    echo "Pushing to registry..."
    docker push $REGISTRY/$IMAGE_NAME:$TAG
    
    echo "Image pushed successfully: $REGISTRY/$IMAGE_NAME:$TAG"
else
    echo "Build failed!"
    exit 1
fi