# Safe Frontend Deployment Script
# This script syncs only frontend files without deleting user-uploaded content

# Bypass "more" prompts for long outputs
$env:AWS_PAGER = ""

Write-Host "🚀 Starting safe frontend deployment..." -ForegroundColor Green

# Build the frontend
Write-Host "📦 Building frontend..." -ForegroundColor Yellow
Set-Location "frontend"
npm run build

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Build failed!" -ForegroundColor Red
    exit 1
}

# Sync only specific frontend files (exclude user content directories)
Write-Host "☁️ Syncing frontend files to S3..." -ForegroundColor Yellow

# Sync static assets (CSS, JS, etc.)
aws s3 sync build/static/ s3://testportal-h-dcn-frontend/static/ --delete

# Sync root files (index.html, manifest, etc.) - but exclude user content and data files
aws s3 cp build/index.html s3://testportal-h-dcn-frontend/index.html
aws s3 cp build/asset-manifest.json s3://testportal-h-dcn-frontend/asset-manifest.json
# Note: parameters.json is NOT deployed here - it's data, not code, and lives in my-hdcn-bucket

# Sync debug/test files
aws s3 sync build/ s3://testportal-h-dcn-frontend/ --exclude "*" --include "*.html" --exclude "index.html"

# Sync other frontend assets
aws s3 sync build/ s3://testportal-h-dcn-frontend/ --exclude "*" --include "*.svg" --include "*.ico" --include "*.png" --include "*.jpg" --exclude "product-images/*" --exclude "imagesWebsite/*"

Write-Host "🔄 Invalidating CloudFront cache..." -ForegroundColor Yellow
aws cloudfront create-invalidation --distribution-id E2QTMDOE6H0R87 --paths "/*"

Write-Host "✅ Safe deployment completed!" -ForegroundColor Green
Write-Host "🌐 Site: https://de1irtdutlxqu.cloudfront.net" -ForegroundColor Cyan

Set-Location ".."