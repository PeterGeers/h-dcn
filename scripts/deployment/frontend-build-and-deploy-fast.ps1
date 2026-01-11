# Fast Build and Deploy Script with Progress and Timing
# Enhanced with pre-deployment validation checks

# Bypass "more" prompts for long outputs
$env:AWS_PAGER = ""

# Start total timer
$totalStartTime = Get-Date

Write-Host ""
Write-Host "🔨 H-DCN Portal Build & Deploy" -ForegroundColor Cyan
Write-Host "==============================" -ForegroundColor Cyan
Write-Host ""

# ===== PRE-DEPLOYMENT VALIDATION =====
Write-Host "🔍 Pre-deployment validation..." -ForegroundColor Yellow

# Check 1: Environment Configuration
Write-Host "  ⚙️  Checking environment configuration..." -ForegroundColor Cyan
$envFile = 'frontend/.env'
if (Test-Path $envFile) {
    $envContent = Get-Content $envFile
    $apiBaseUrl = $envContent | Where-Object { $_ -match '^REACT_APP_API_BASE_URL=' }
    $userPoolId = $envContent | Where-Object { $_ -match '^REACT_APP_USER_POOL_ID=' }
    
    if ($apiBaseUrl -and $userPoolId) {
        Write-Host "     ✅ Environment configuration found" -ForegroundColor Green
        Write-Host "       API: $($apiBaseUrl -replace 'REACT_APP_API_BASE_URL=', '')" -ForegroundColor White
    }
    else {
        Write-Host "     ⚠️  Missing critical environment variables" -ForegroundColor Yellow
    }
}
else {
    Write-Host "     ❌ .env file not found!" -ForegroundColor Red
    exit 1
}

# Check 2: Critical Frontend Files Status
Write-Host "  📊 Checking critical frontend files..." -ForegroundColor Cyan
$criticalFiles = @(
    'frontend/.env',
    'frontend/src/utils/authHeaders.ts',
    'frontend/src/services/apiService.ts',
    'frontend/src/components/common/GroupAccessGuard.tsx'
)

$hasUncommittedChanges = $false
foreach ($file in $criticalFiles) {
    if (Test-Path $file) {
        $gitStatus = git status --porcelain $file 2>$null
        if ($gitStatus) {
            if (-not $hasUncommittedChanges) {
                Write-Host "     ⚠️  Uncommitted changes in critical files:" -ForegroundColor Yellow
                $hasUncommittedChanges = $true
            }
            Write-Host "       • $file" -ForegroundColor White
        }
    }
}

if (-not $hasUncommittedChanges) {
    Write-Host "     ✅ No uncommitted changes in critical files" -ForegroundColor Green
}

# Check 3: Recent Authentication Changes
Write-Host "  🔐 Checking recent authentication changes..." -ForegroundColor Cyan
$authFiles = @(
    'frontend/src/utils/authHeaders.ts',
    'frontend/src/services/apiService.ts'
)
$recentAuthChanges = git log --oneline -3 --since="1 hour ago" -- $authFiles 2>$null
if ($recentAuthChanges) {
    Write-Host "     ⚠️  Recent authentication changes (last hour):" -ForegroundColor Yellow
    $recentAuthChanges | ForEach-Object { Write-Host "       • $_" -ForegroundColor White }
}
else {
    Write-Host "     ✅ No recent authentication changes" -ForegroundColor Green
}

# Check 4: Node Modules Status
Write-Host "  📦 Checking dependencies..." -ForegroundColor Cyan
if (Test-Path 'frontend/node_modules') {
    $packageJson = Get-Content 'frontend/package.json' | ConvertFrom-Json
    $lockFile = if (Test-Path 'frontend/package-lock.json') { 'package-lock.json' } else { 'yarn.lock' }
    Write-Host "     ✅ Dependencies installed ($lockFile)" -ForegroundColor Green
}
else {
    Write-Host "     ⚠️  Node modules not found - will install during build" -ForegroundColor Yellow
}

# Check 5: Git Branch Info
Write-Host "  🌿 Current branch info..." -ForegroundColor Cyan
$currentBranch = git branch --show-current 2>$null
$lastCommit = git log -1 --oneline 2>$null
if ($currentBranch -and $lastCommit) {
    Write-Host "     Branch: $currentBranch" -ForegroundColor White
    Write-Host "     Last commit: $lastCommit" -ForegroundColor White
}
else {
    Write-Host "     ⚠️  Git information unavailable" -ForegroundColor Yellow
}

Write-Host "✅ Pre-deployment validation completed" -ForegroundColor Green
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