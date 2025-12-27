# Deploy Frontend to Test Environment
# Run this after building your React app

param(
    [string]$BuildPath = "frontend/build"
)

$BUCKET_NAME = "testportal-h-dcn-frontend"
$CLOUDFRONT_DISTRIBUTION_ID = "E2QTMDOE6H0R87"

Write-Host "Deploying frontend to test environment" -ForegroundColor Green

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
if ($CLOUDFRONT_DISTRIBUTION_ID -ne "REPLACE_WITH_YOUR_DISTRIBUTION_ID") {
    Write-Host "Creating CloudFront invalidation" -ForegroundColor Yellow
    aws cloudfront create-invalidation --distribution-id $CLOUDFRONT_DISTRIBUTION_ID --paths "/*"
    Write-Host "Deployment complete! Changes will be live in 1-2 minutes." -ForegroundColor Green
} else {
    Write-Host "Update CLOUDFRONT_DISTRIBUTION_ID in this script to enable cache invalidation" -ForegroundColor Yellow
    Write-Host "Deployment complete! Changes may take up to 24 hours without cache invalidation." -ForegroundColor Green
}

Write-Host ""
Write-Host "Test your deployment at: https://testportal.h-dcn.nl" -ForegroundColor Cyan