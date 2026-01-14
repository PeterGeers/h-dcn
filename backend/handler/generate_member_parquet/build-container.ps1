# Build Docker container for GenerateMemberParquetFunction with proper Lambda compatibility
# This script sets up the build context and builds the container for AWS Lambda

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

Write-Host "Building Docker container for GenerateMemberParquetFunction..."
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
    Copy-Item "Dockerfile" "$BuildDir/"
    
    # Copy shared authentication utilities from auth layer
    Copy-Item "../../layers/auth-layer/python/shared" "$BuildDir/" -Recurse
    
    # Build the Docker image with proper platform for Lambda and force Docker format
    Write-Host "Building Docker image..."
    Set-Location $BuildDir
    
    # Set Docker to use legacy builder to avoid OCI format issues
    $env:DOCKER_BUILDKIT = "0"
    docker build --platform linux/amd64 -t $ECRRepository .
    
    if ($LASTEXITCODE -ne 0) {
        throw "Docker build failed"
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
    # Reset Docker buildkit
    Remove-Item Env:DOCKER_BUILDKIT -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Deploy the SAM template: sam deploy"
Write-Host "2. Test the function: POST /analytics/generate-parquet"