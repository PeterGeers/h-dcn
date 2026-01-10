# Build Docker container with explicit Docker manifest format for AWS Lambda
# This script uses docker save/load to ensure Docker format instead of OCI

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

Write-Host "Building Docker container with Docker manifest format..."
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
    
    # Create a simple Dockerfile
    @"
FROM public.ecr.aws/lambda/python:3.11

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY shared/ `${LAMBDA_TASK_ROOT}/shared/
COPY app.py `${LAMBDA_TASK_ROOT}/

CMD ["app.lambda_handler"]
"@ | Out-File -FilePath "$BuildDir/Dockerfile" -Encoding UTF8
    
    Set-Location $BuildDir
    
    # Build with legacy builder to ensure Docker format
    Write-Host "Building with legacy Docker builder..."
    $env:DOCKER_BUILDKIT = "0"
    docker build --platform linux/amd64 -t $ECRRepository .
    
    if ($LASTEXITCODE -ne 0) {
        throw "Docker build failed"
    }
    
    # Save and reload to ensure Docker format
    Write-Host "Converting to Docker format..."
    docker save $ECRRepository | docker load
    
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
    
    # Push the image to ECR with explicit Docker format
    Write-Host "Pushing image to ECR..."
    docker push $ImageUri
    
    if ($LASTEXITCODE -ne 0) {
        throw "Docker push failed"
    }
    
    Write-Host "✅ Container built and pushed successfully!"
    Write-Host "Image URI: $ImageUri"
    
    # Verify the image format
    Write-Host "Verifying image format..."
    $manifestType = aws ecr describe-images --repository-name $ECRRepository --region $Region --image-ids imageTag=$ImageTag --query 'imageDetails[0].imageManifestMediaType' --output text
    Write-Host "Manifest type: $manifestType"
    
    if ($manifestType -like "*docker*") {
        Write-Host "✅ Image is in Docker format - should work with Lambda"
    }
    else {
        Write-Host "⚠️ Image is still in OCI format - may have issues with Lambda"
    }
    
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