#!/bin/bash
# Build and push Docker image for TFT model
set -e

IMAGE_NAME="tft-model-benchmark:latest"
REPO="sushruth13" # Change to your Docker Hub repo

# Build the Docker image
DOCKER_BUILDKIT=1 docker build -t $REPO/$IMAGE_NAME .

echo "Docker image built: $IMAGE_NAME"

docker tag $IMAGE_NAME $REPO

echo "Pushing image to $REPO..."
docker push $REPO

echo "Done."
