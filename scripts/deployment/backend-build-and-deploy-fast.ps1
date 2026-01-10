#!/usr/bin/env pwsh

$startTime = Get-Date

Write-Host "🔨 H-DCN Backend Build & Deploy" -ForegroundColor Cyan
Write-Host "==============================" -ForegroundColor Cyan
Write-Host ""

# Change to backend directory
Set-Location backend

Write-Host "🔍 Validating SAM template..." -ForegroundColor Yellow
$validateStart = Get-Date
sam validate --template template.yaml --lint

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Template validation failed!" -ForegroundColor Red
    $validateTime = (Get-Date) - $validateStart
    Write-Host "⏱️ Validation time: $($validateTime.TotalSeconds.ToString('F1')) seconds" -ForegroundColor Yellow
    exit 1
}

$validateTime = (Get-Date) - $validateStart
Write-Host "✅ Template validation completed successfully" -ForegroundColor Green
Write-Host "⏱️ Validation time: $($validateTime.TotalSeconds.ToString('F1')) seconds" -ForegroundColor Yellow
Write-Host ""

# Build Docker containers for container-based functions
Write-Host "🐳 Building Docker containers..." -ForegroundColor Yellow
$dockerStart = Get-Date

# Build Parquet Generator container
Write-Host "  📊 Building Parquet Generator container..." -ForegroundColor Cyan
Set-Location "handler/generate_member_parquet"
& .\build-container.ps1

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker container build failed!" -ForegroundColor Red
    $dockerTime = (Get-Date) - $dockerStart
    Write-Host "⏱️ Docker build time: $($dockerTime.TotalSeconds.ToString('F1')) seconds" -ForegroundColor Yellow
    exit 1
}

Set-Location "../.."
$dockerTime = (Get-Date) - $dockerStart
Write-Host "✅ Docker containers built successfully" -ForegroundColor Green
Write-Host "⏱️ Docker build time: $($dockerTime.TotalSeconds.ToString('F1')) seconds" -ForegroundColor Yellow
Write-Host ""

Write-Host "📦 Building backend..." -ForegroundColor Yellow
$buildStart = Get-Date
sam build --parallel

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Build failed!" -ForegroundColor Red
    $buildTime = (Get-Date) - $buildStart
    Write-Host "⏱️ Build time: $($buildTime.TotalSeconds.ToString('F1')) seconds" -ForegroundColor Yellow
    exit 1
}

$buildTime = (Get-Date) - $buildStart
Write-Host "✅ Build completed successfully" -ForegroundColor Green
Write-Host "⏱️ Build time: $($buildTime.TotalSeconds.ToString('F1')) seconds" -ForegroundColor Yellow
Write-Host ""

Write-Host "🚀 Deploying backend..." -ForegroundColor Yellow
$deployStart = Get-Date
sam deploy --no-confirm-changeset --no-fail-on-empty-changeset --resolve-image-repos

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Deploy failed!" -ForegroundColor Red
    $deployTime = (Get-Date) - $deployStart
    Write-Host "⏱️ Deploy time: $($deployTime.TotalSeconds.ToString('F1')) seconds" -ForegroundColor Yellow
    exit 1
}

$deployTime = (Get-Date) - $deployStart
Write-Host "✅ SAM deployment completed successfully" -ForegroundColor Green
Write-Host "⏱️ Deploy time: $($deployTime.TotalSeconds.ToString('F1')) seconds" -ForegroundColor Yellow
Write-Host ""

# Update container-based Lambda functions with latest images
Write-Host "🔄 Updating container-based Lambda functions..." -ForegroundColor Yellow
$updateStart = Get-Date

# Get AWS account ID and region from SAM config
$accountId = aws sts get-caller-identity --query Account --output text
$region = "eu-west-1"  # From samconfig.toml

# Update Parquet Generator function
Write-Host "  📊 Updating GenerateMemberParquetFunction..." -ForegroundColor Cyan
$functionName = aws cloudformation describe-stacks --stack-name webshop-backend --region $region --query "Stacks[0].Outputs[?OutputKey=='GenerateMemberParquetFunctionName'].OutputValue" --output text 2>$null

if ([string]::IsNullOrEmpty($functionName)) {
    # Fallback: find function by pattern
    $functionName = aws lambda list-functions --region $region --query "Functions[?contains(FunctionName, 'GenerateMemberParquet')].FunctionName" --output text
}

if (![string]::IsNullOrEmpty($functionName)) {
    $imageUri = "${accountId}.dkr.ecr.${region}.amazonaws.com/hdcn-parquet-generator:latest"
    aws lambda update-function-code --region $region --function-name $functionName --image-uri $imageUri --no-cli-pager
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    ✅ Updated $functionName with latest container image" -ForegroundColor Green
    }
    else {
        Write-Host "    ⚠️ Failed to update $functionName - function may still work with previous image" -ForegroundColor Yellow
    }
}
else {
    Write-Host "    ⚠️ GenerateMemberParquetFunction not found - skipping container update" -ForegroundColor Yellow
}

$updateTime = (Get-Date) - $updateStart
Write-Host "✅ Lambda function updates completed" -ForegroundColor Green
Write-Host "⏱️ Update time: $($updateTime.TotalSeconds.ToString('F1')) seconds" -ForegroundColor Yellow
Write-Host ""

$totalTime = (Get-Date) - $startTime

Write-Host "✅ Backend deployment completed successfully" -ForegroundColor Green
Write-Host "⏱️ Total time: $($totalTime.TotalSeconds.ToString('F1')) seconds" -ForegroundColor Cyan
Write-Host ""
Write-Host "🎉 Backend Deploy Complete!" -ForegroundColor Green

# Return to root directory
Set-Location ..