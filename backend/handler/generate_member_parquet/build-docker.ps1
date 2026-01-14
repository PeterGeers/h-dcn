# Build Docker container for GenerateMemberParquetFunction with proper build context
# Usage: .\build-docker.ps1 [region] [account-id]

param(
    [string]$Region = "eu-west-1",
    [string]$AccountId = ""
)

$REPOSITORY_NAME = "hdcn-parquet-generator"
$IMAGE_TAG = "latest"

# Get account ID if not provided
if ([string]::IsNullOrEmpty($AccountId)) {
    $AccountId = (aws sts get-caller-identity --query Account --output text)
}

Write-Host "Building Docker image for parquet generation function..." -ForegroundColor Green
Write-Host "Region: $Region"
Write-Host "Account ID: $AccountId"
Write-Host "Repository: $REPOSITORY_NAME"

# Create temporary build directory
$buildDir = "docker-build-temp"
if (Test-Path $buildDir) {
    Remove-Item -Recurse -Force $buildDir
}
New-Item -ItemType Directory -Path $buildDir

try {
    # Copy function files
    Copy-Item "app.py" "$buildDir/"
    Copy-Item "requirements.txt" "$buildDir/"
    
    # Copy auth layer
    $authLayerSource = "../../layers/auth-layer/python"
    $authLayerDest = "$buildDir/auth-layer"
    Copy-Item -Recurse $authLayerSource $authLayerDest
    
    # Create Dockerfile in build directory
    $dockerfileContent = @"
FROM public.ecr.aws/lambda/python:3.11

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy auth layer (shared authentication utilities)
COPY auth-layer/ /opt/python/

# Copy Lambda function code
COPY app.py `${LAMBDA_TASK_ROOT}

# Set Python path to include auth layer
ENV PYTHONPATH="`${LAMBDA_TASK_ROOT}:/opt/python"

# Set the CMD to your handler
CMD ["app.lambda_handler"]
"@
    
    Set-Content -Path "$buildDir/Dockerfile" -Value $dockerfileContent
    
    # Create ECR repository if it doesn't exist
    Write-Host "Creating ECR repository if it doesn't exist..." -ForegroundColor Yellow
    $repoExists = aws ecr describe-repositories --repository-names $REPOSITORY_NAME --region $Region 2>$null
    if (-not $repoExists) {
        aws ecr create-repository --repository-name $REPOSITORY_NAME --region $Region
    }
    
    # Get login token and login to ECR
    Write-Host "Logging in to ECR..." -ForegroundColor Yellow
    $loginToken = aws ecr get-login-password --region $Region
    $loginToken | docker login --username AWS --password-stdin "$AccountId.dkr.ecr.$Region.amazonaws.com"
    
    # Build the Docker image
    Write-Host "Building Docker image..." -ForegroundColor Yellow
    Push-Location $buildDir
    docker build -t "${REPOSITORY_NAME}:${IMAGE_TAG}" .
    Pop-Location
    
    # Tag the image for ECR
    Write-Host "Tagging image for ECR..." -ForegroundColor Yellow
    docker tag "${REPOSITORY_NAME}:${IMAGE_TAG}" "$AccountId.dkr.ecr.$Region.amazonaws.com/${REPOSITORY_NAME}:${IMAGE_TAG}"
    
    # Push the image to ECR
    Write-Host "Pushing image to ECR..." -ForegroundColor Yellow
    docker push "$AccountId.dkr.ecr.$Region.amazonaws.com/${REPOSITORY_NAME}:${IMAGE_TAG}"
    
    Write-Host "Docker image pushed successfully!" -ForegroundColor Green
    Write-Host "Image URI: $AccountId.dkr.ecr.$Region.amazonaws.com/${REPOSITORY_NAME}:${IMAGE_TAG}" -ForegroundColor Cyan
    
}
finally {
    # Clean up build directory
    if (Test-Path $buildDir) {
        Remove-Item -Recurse -Force $buildDir
    }
}