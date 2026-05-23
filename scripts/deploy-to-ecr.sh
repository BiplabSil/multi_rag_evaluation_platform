#!/bin/bash

# deploy-to-ecr.sh
# Script to manually build and deploy Docker image to AWS ECR

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install it first."
    exit 1
fi

# Default values - update these as needed
REGION=${AWS_DEFAULT_REGION:-us-east-1}
ECR_REPOSITORY_URI=${ECR_REPOSITORY_URI:-""}
IMAGE_TAG=${IMAGE_TAG:-"manual-$(date +%Y%m%d-%H%M%S)"}

# Check if ECR repository URI is provided
if [ -z "$ECR_REPOSITORY_URI" ]; then
    echo "Please set ECR_REPOSITORY_URI environment variable"
    echo "Example: export ECR_REPOSITORY_URI=123456789012.dkr.ecr.us-east-1.amazonaws.com/my-repo"
    exit 1
fi

echo "Building and deploying to ECR..."
echo "Repository: $ECR_REPOSITORY_URI"
echo "Tag: $IMAGE_TAG"
echo "Region: $REGION"

# Get AWS account ID from ECR URI
ACCOUNT_ID=$(echo $ECR_REPOSITORY_URI | cut -d'.' -f1)
REPO_NAME=$(echo $ECR_REPOSITORY_URI | cut -d'/' -f2)

# Login to ECR
echo "Logging in to Amazon ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# Build the Docker image
echo "Building Docker image..."
docker build -f docker/Dockerfile -t $ECR_REPOSITORY_URI:$IMAGE_TAG .

# Tag the image as latest
echo "Tagging image as latest..."
docker tag $ECR_REPOSITORY_URI:$IMAGE_TAG $ECR_REPOSITORY_URI:latest

# Push the image
echo "Pushing image to ECR..."
docker push $ECR_REPOSITORY_URI:$IMAGE_TAG
docker push $ECR_REPOSITORY_URI:latest

echo "Deployment complete!"
echo "Image URI: $ECR_REPOSITORY_URI:$IMAGE_TAG"