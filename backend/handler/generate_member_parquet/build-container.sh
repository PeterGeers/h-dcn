#!/bin/bash

# Build Docker container for GenerateMemberParquetFunction with proper Lambda compatibility
# This script sets up the build context and builds the container for AWS Lambda

set -e

REGION=${1:-"eu-west-1"}
ACCOUNT_ID=${2:-""}
IMAGE_TAG=${3:-"latest"}

# Get AWS account ID if not provided
if [ -z "$ACCOUNT_ID" ]; then
    echo "Getting AWS account ID..."
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    if [ $? -ne 0 ]; then
        echo "Error: Failed to get AWS account ID. Make sure AWS CLI is configured."
        exit 1
    fi
fi

ECR_REPOSITORY="hdcn-parquet-generator"
IMAGE_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPOSITORY}:${IMAGE_TAG}"

echo "Building Docker container for GenerateMemberParquetFunction..."
echo "Region: $REGION"
echo "Account ID: $ACCOUNT_ID"
echo "Image URI: $IMAGE_URI"

# Create temporary build directory
BUILD_DIR="build-temp"
if [ -d "$BUILD_DIR" ]; then
    rm -rf "$BUILD_DIR"
fi
mkdir "$BUILD_DIR"

cleanup() {
    cd ..
    if [ -d "$BUILD_DIR" ]; then
        rm -rf "$BUILD_DIR"
    fi
}

trap cleanup EXIT

# Copy function files
echo "Setting up build context..."
cp app.py "$BUILD_DIR/"
cp requirements.txt "$BUILD_DIR/"
cp Dockerfile "$BUILD_DIR/"

# Copy shared authentication utilities
cp -r ../../shared "$BUILD_DIR/"

# Build the Docker image with proper platform for Lambda
echo "Building Docker image..."
cd "$BUILD_DIR"

docker build --platform linux/amd64 -t "$ECR_REPOSITORY" .

# Tag the image for ECR
docker tag "${ECR_REPOSITORY}:latest" "$IMAGE_URI"

echo "✅ Docker image built successfully: $IMAGE_URI"

# Check if ECR repository exists, create if not
echo "Checking ECR repository..."
if ! aws ecr describe-repositories --repository-names "$ECR_REPOSITORY" --region "$REGION" >/dev/null 2>&1; then
    echo "Creating ECR repository: $ECR_REPOSITORY"
    aws ecr create-repository --repository-name "$ECR_REPOSITORY" --region "$REGION"
fi

# Get ECR login token and login to Docker
echo "Logging in to ECR..."
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

# Push the image to ECR
echo "Pushing image to ECR..."
docker push "$IMAGE_URI"

echo "✅ Container built and pushed successfully!"
echo "Image URI: $IMAGE_URI"
echo ""
echo "Next steps:"
echo "1. Deploy the SAM template: sam deploy"
echo "2. Test the function: POST /analytics/generate-parquet"