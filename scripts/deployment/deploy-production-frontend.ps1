# Deploy Frontend to Production Environment
# Run this after building your React app

param(
    [string]$BuildPath = $null
)

$BUCKET_NAME = "testportal-h-dcn-frontend"  # Correct S3 bucket name
$CLOUDFRONT_DISTRIBUTION_ID = "E2QTMDOE6H0R87"  # Correct CloudFront distribution

Write-Host "Deploying frontend to PRODUCTION environment" -ForegroundColor Green

# Determine build path based on current location
if (-not $BuildPath) {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $rootDir = Split-Path -Parent (Split-Path -Parent $scriptDir)
    $BuildPath = Join-Path $rootDir "frontend\build"
}

# Check if build directory exists
if (-not (Test-Path $BuildPath)) {
    Write-Host "Build directory not found: $BuildPath" -ForegroundColor Red
    Write-Host "Run 'npm run build' in the frontend directory first" -ForegroundColor Yellow
    exit 1
}

# Deploy to S3
Write-Host "Uploading files to S3 bucket: $BUCKET_NAME" -ForegroundColor Yellow
aws s3 sync $BuildPath s3://$BUCKET_NAME --delete --cache-control "max-age=31536000" --exclude "*.html"
aws s3 sync $BuildPath s3://$BUCKET_NAME --delete --cache-control "max-age=0, no-cache, no-store, must-revalidate" --include "*.html"

# Invalidate CloudFront cache
Write-Host "Creating CloudFront invalidation" -ForegroundColor Yellow
aws cloudfront create-invalidation --distribution-id $CLOUDFRONT_DISTRIBUTION_ID --paths "/*"

Write-Host "Deployment complete! Changes will be live in 1-2 minutes." -ForegroundColor Green
Write-Host ""
Write-Host "Test your deployment at:" -ForegroundColor Cyan
Write-Host "  - https://testportal.h-dcn.nl" -ForegroundColor White
Write-Host "  - https://de1irtdutlxqu.cloudfront.net" -ForegroundColor White