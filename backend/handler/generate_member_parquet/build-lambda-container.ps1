# Build Docker container for AWS Lambda with proper format compatibility
# This script forces Docker manifest format instead of OCI format

param(
    [string]$Region = "eu-west-1",
    [string]$AccountId = "",
    [string]$ImageTag = "latest"
)

# Get AWS account ID if not provided
if ([string]::IsNullOrEmpty($AccountId)) {
    Write-Host "Getting AWS account ID..."
    $AccountId = aws sts get-caller-identity --query Account --output text
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to get AWS account ID. Make sure AWS CLI is configured."
        exit 1
    }
}

$ECRRepository = "hdcn-parquet-generator"
$ImageUri = "${AccountId}.dkr.ecr.${Region}.amazonaws.com/${ECRRepository}:${ImageTag}"

Write-Host "Building Lambda-compatible Docker container..."
Write-Host "Region: $Region"
Write-Host "Account ID: $AccountId"
Write-Host "Image URI: $ImageUri"

# Create temporary build directory
$BuildDir = "build-temp"
if (Test-Path $BuildDir) {
    Remove-Item -Recurse -Force $BuildDir
}
New-Item -ItemType Directory -Path $BuildDir | Out-Null

try {
    # Copy function files
    Write-Host "Setting up build context..."
    Copy-Item "app.py" "$BuildDir/"
    Copy-Item "requirements.txt" "$BuildDir/"
    Copy-Item "../../shared" "$BuildDir/" -Recurse
    
    # Create a Lambda-optimized Dockerfile
    Write-Host "Creating Lambda-optimized Dockerfile..."
    @"
FROM public.ecr.aws/lambda/python:3.11

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy shared authentication utilities
COPY shared/ `${LAMBDA_TASK_ROOT}/shared/

# Copy function code
COPY app.py `${LAMBDA_TASK_ROOT}/

# Command to run the Lambda function
CMD ["app.lambda_handler"]
"@ | Out-File -FilePath "$BuildDir/Dockerfile" -Encoding UTF8
    
    Set-Location $BuildDir
    
    # Try using docker buildx with explicit output format
    Write-Host "Building with docker buildx for Lambda compatibility..."
    
    # Create a new builder instance that supports Docker format
    docker buildx create --name lambda-builder --use --bootstrap 2>$null
    
    # Build with explicit Docker manifest format
    docker buildx build `
        --platform linux/amd64 `
        --output type=docker `
        --tag $ECRRepository `
        .
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Buildx failed, trying with legacy builder..."
        
        # Fallback to legacy builder
        $env:DOCKER_BUILDKIT = "0"
        docker build --platform linux/amd64 -t $ECRRepository .
        
        if ($LASTEXITCODE -ne 0) {
            throw "Docker build failed"
        }
    }
    
    # Tag the image for ECR
    docker tag "${ECRRepository}:latest" $ImageUri
    
    if ($LASTEXITCODE -ne 0) {
        throw "Docker tag failed"
    }
    
    Write-Host "✅ Docker image built successfully: $ImageUri"
    
    # Check if ECR repository exists, create if not
    Write-Host "Checking ECR repository..."
    aws ecr describe-repositories --repository-names $ECRRepository --region $Region 2>$null
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Creating ECR repository: $ECRRepository"
        aws ecr create-repository --repository-name $ECRRepository --region $Region
        
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to create ECR repository"
        }
    }
    
    # Get ECR login token and login to Docker
    Write-Host "Logging in to ECR..."
    aws ecr get-login-password --region $Region | docker login --username AWS --password-stdin "${AccountId}.dkr.ecr.${Region}.amazonaws.com"
    
    if ($LASTEXITCODE -ne 0) {
        throw "ECR login failed"
    }
    
    # Push the image to ECR
    Write-Host "Pushing image to ECR..."
    docker push $ImageUri
    
    if ($LASTEXITCODE -ne 0) {
        throw "Docker push failed"
    }
    
    Write-Host "✅ Container built and pushed successfully!"
    Write-Host "Image URI: $ImageUri"
    
    # Verify the image format
    Write-Host "Verifying image format..."
    aws ecr describe-images --repository-name $ECRRepository --region $Region --image-ids imageTag=$ImageTag --query 'imageDetails[0].imageManifestMediaType' --output text
    
}
catch {
    Write-Error "Build failed: $_"
    exit 1
}
finally {
    # Clean up
    Set-Location ..
    if (Test-Path $BuildDir) {
        Remove-Item -Recurse -Force $BuildDir
    }
    # Clean up builder
    docker buildx rm lambda-builder 2>$null
    # Reset Docker buildkit
    Remove-Item Env:DOCKER_BUILDKIT -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Deploy the SAM template: sam deploy"
Write-Host "2. Test the function: POST /analytics/generate-parquet"