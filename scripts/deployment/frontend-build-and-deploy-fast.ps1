# Fast Build and Deploy Script with Progress and Timing
# Builds and deploys with visual progress indicators and timing information

# Bypass "more" prompts for long outputs
$env:AWS_PAGER = ""

# Start total timer
$totalStartTime = Get-Date

Write-Host ""
Write-Host "🔨 H-DCN Portal Build & Deploy" -ForegroundColor Cyan
Write-Host "==============================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Build
Write-Host "📦 Building React application..." -ForegroundColor Yellow
Write-Progress -Activity "Building Application" -Status "Running npm run build..." -PercentComplete 20

$buildStartTime = Get-Date
Set-Location frontend
$buildOutput = npm run build 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Progress -Activity "Build and Deploy" -Completed
    Write-Host "❌ Build failed" -ForegroundColor Red
    Write-Host $buildOutput
    exit 1
}

$buildEndTime = Get-Date
$buildDuration = ($buildEndTime - $buildStartTime).TotalSeconds

Write-Progress -Activity "Building Application" -Status "Build completed successfully" -PercentComplete 50
Write-Host "✅ Build completed successfully" -ForegroundColor Green
Write-Host "⏱️ Build time: $([math]::Round($buildDuration, 1)) seconds" -ForegroundColor Cyan

# Return to root directory
Set-Location ..

Write-Progress -Activity "Build and Deploy" -Status "Starting deployment..." -PercentComplete 60

# Step 2: Deploy
Write-Host ""
Write-Host "🚀 Starting deployment..." -ForegroundColor Yellow

$deployStartTime = Get-Date

Write-Progress -Activity "Build and Deploy" -Status "Syncing static assets..." -PercentComplete 70

# Sync static assets (CSS, JS, etc.)
aws s3 sync frontend/build/static/ s3://testportal-h-dcn-frontend/static/ --delete

Write-Progress -Activity "Build and Deploy" -Status "Syncing root files..." -PercentComplete 80

# Sync root files (index.html, manifest, etc.)
aws s3 cp frontend/build/index.html s3://testportal-h-dcn-frontend/index.html
aws s3 cp frontend/build/asset-manifest.json s3://testportal-h-dcn-frontend/asset-manifest.json

# Sync debug/test files
aws s3 sync frontend/build/ s3://testportal-h-dcn-frontend/ --exclude "*" --include "*.html" --exclude "index.html"

# Sync other frontend assets
aws s3 sync frontend/build/ s3://testportal-h-dcn-frontend/ --exclude "*" --include "*.svg" --include "*.ico" --include "*.png" --include "*.jpg" --exclude "product-images/*" --exclude "imagesWebsite/*"

Write-Progress -Activity "Build and Deploy" -Status "Invalidating CloudFront cache..." -PercentComplete 90

Write-Host "🔄 Invalidating CloudFront cache..." -ForegroundColor Yellow
aws cloudfront create-invalidation --distribution-id E2QTMDOE6H0R87 --paths "/*"

$deployEndTime = Get-Date
$deployDuration = ($deployEndTime - $deployStartTime).TotalSeconds

Write-Progress -Activity "Build and Deploy" -Status "Deployment completed" -PercentComplete 100

Write-Host "✅ Frontend deployment completed successfully" -ForegroundColor Green
Write-Host "⏱️ Deploy time: $([math]::Round($deployDuration, 1)) seconds" -ForegroundColor Cyan

Write-Progress -Activity "Build and Deploy" -Completed

$totalEndTime = Get-Date
$totalDuration = ($totalEndTime - $totalStartTime).TotalSeconds

Write-Host "⏱️ Total time: $([math]::Round($totalDuration, 1)) seconds" -ForegroundColor Cyan
Write-Host ""
Write-Host "🎉 Frontend Build and Deploy Complete!" -ForegroundColor Green
Write-Host "🌐 Site: https://de1irtdutlxqu.cloudfront.net" -ForegroundColor Cyan