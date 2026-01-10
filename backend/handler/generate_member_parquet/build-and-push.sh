#!/bin/bash

# Build and push Docker container for GenerateMemberParquetFunction
# Usage: ./build-and-push.sh [region] [account-id]

REGION=${1:-eu-west-1}
ACCOUNT_ID=${2:-$(aws sts get-caller-identity --query Account --output text)}
REPOSITORY_NAME="hdcn-parquet-generator"
IMAGE_TAG="latest"

echo "Building Docker image for parquet generation function..."
echo "Region: $REGION"
echo "Account ID: $ACCOUNT_ID"
echo "Repository: $REPOSITORY_NAME"

# Create ECR repository if it doesn't exist
echo "Creating ECR repository if it doesn't exist..."
aws ecr describe-repositories --repository-names $REPOSITORY_NAME --region $REGION 2>/dev/null || \
aws ecr create-repository --repository-name $REPOSITORY_NAME --region $REGION

# Get login token and login to ECR
echo "Logging in to ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# Build the Docker image
echo "Building Docker image..."
docker build -t $REPOSITORY_NAME:$IMAGE_TAG .

# Tag the image for ECR
echo "Tagging image for ECR..."
docker tag $REPOSITORY_NAME:$IMAGE_TAG $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPOSITORY_NAME:$IMAGE_TAG

# Push the image to ECR
echo "Pushing image to ECR..."
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPOSITORY_NAME:$IMAGE_TAG

echo "Docker image pushed successfully!"
echo "Image URI: $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPOSITORY_NAME:$IMAGE_TAG"