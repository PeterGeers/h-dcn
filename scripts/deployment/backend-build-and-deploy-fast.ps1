#!/usr/bin/env pwsh

$startTime = Get-Date

Write-Host "🔨 H-DCN Backend Build & Deploy" -ForegroundColor Cyan
Write-Host "==============================" -ForegroundColor Cyan
Write-Host ""

# ===== PRE-DEPLOYMENT VALIDATION =====
Write-Host "🔍 Pre-deployment validation..." -ForegroundColor Yellow

# Check 1: AuthLayer Synchronization
Write-Host "  📋 Checking AuthLayer synchronization..." -ForegroundColor Cyan
$mainFile = 'backend/shared/auth_utils.py'
$layerFile = 'backend/layers/auth-layer/python/shared/auth_utils.py'

if ((Test-Path $mainFile) -and (Test-Path $layerFile)) {
    $mainHash = Get-FileHash $mainFile
    $layerHash = Get-FileHash $layerFile
    if ($mainHash.Hash -eq $layerHash.Hash) {
        Write-Host "     ✅ AuthLayer files are synchronized" -ForegroundColor Green
    }
    else {
        Write-Host "     ❌ AuthLayer files are OUT OF SYNC!" -ForegroundColor Red
        Write-Host "     Main: $mainFile" -ForegroundColor White
        Write-Host "     Layer: $layerFile" -ForegroundColor White
        Write-Host "     This will cause 'Authentication not available' errors!" -ForegroundColor Red
        Write-Host ""
        Write-Host "     🔧 Auto-fixing: Syncing files..." -ForegroundColor Yellow
        Copy-Item $mainFile $layerFile -Force
        Write-Host "     ✅ AuthLayer files synchronized" -ForegroundColor Green
    }
}
else {
    Write-Host "     ❌ AuthLayer files missing!" -ForegroundColor Red
    exit 1
}

# Check 2: Critical Files Status
Write-Host "  📊 Checking critical files status..." -ForegroundColor Cyan

# Run all validation checks
Write-Host "  🔍 Running validation checks..." -ForegroundColor Cyan
python scripts/validate_all.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "     ❌ Validation checks FAILED!" -ForegroundColor Red
    Write-Host "     Fix validation errors before deploying" -ForegroundColor Red
    exit 1
}
Write-Host "     ✅ All validation checks passed" -ForegroundColor Green

$criticalFiles = @(
    'template.yaml',
    'samconfig.toml',
    'shared/auth_utils.py',
    'layers/auth-layer/python/shared/auth_utils.py'
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

# Check 3: Recent Changes Warning
Write-Host "  📈 Checking recent changes..." -ForegroundColor Cyan
$recentChanges = git log --oneline -5 --since="1 hour ago" -- $criticalFiles 2>$null
if ($recentChanges) {
    Write-Host "     ⚠️  Recent changes to critical files (last hour):" -ForegroundColor Yellow
    $recentChanges | ForEach-Object { Write-Host "       • $_" -ForegroundColor White }
}
else {
    Write-Host "     ✅ No recent changes to critical files" -ForegroundColor Green
}

# Check 4: Git Branch Info
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
sam deploy --no-confirm-changeset --no-fail-on-empty-changeset --resolve-image-repos --force-upload

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

$totalTime = (Get-Date) - $startTime

Write-Host "✅ Backend deployment completed successfully" -ForegroundColor Green
Write-Host "⏱️ Total time: $($totalTime.TotalSeconds.ToString('F1')) seconds" -ForegroundColor Cyan
Write-Host ""

# Return to root directory
Set-Location ..

# Run smoke tests against deployed backend
Write-Host "🔥 Running post-deployment smoke tests..." -ForegroundColor Yellow
Write-Host "Testing REAL deployed backend API..." -ForegroundColor Cyan

$smokeTestStart = Get-Date
node scripts/deployment/smoke-test-production.js

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Smoke tests FAILED!" -ForegroundColor Red
    Write-Host "⚠️  Backend deployment completed but API has issues" -ForegroundColor Yellow
    Write-Host "🔧 Check the test output above for details" -ForegroundColor Yellow
    Write-Host "💡 Common issues:" -ForegroundColor Cyan
    Write-Host "   - Lambda function errors (check CloudWatch logs)" -ForegroundColor White
    Write-Host "   - API Gateway misconfiguration" -ForegroundColor White
    Write-Host "   - Missing environment variables" -ForegroundColor White
    exit 1
}

$smokeTestTime = (Get-Date) - $smokeTestStart
Write-Host "✅ Smoke tests passed!" -ForegroundColor Green
Write-Host "⏱️ Smoke test time: $([math]::Round($smokeTestTime.TotalSeconds, 1)) seconds" -ForegroundColor Cyan
Write-Host ""
Write-Host "🎉 Backend Deploy Complete!" -ForegroundColor Green


# Auto-commit deployed changes (only runs if deployment succeeded)
Write-Host ""
$gitStatus = git status --porcelain
if ($gitStatus) {
    Write-Host "📝 Auto-committing deployed changes..." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Changed files:" -ForegroundColor Yellow
    git status --short
    Write-Host ""
    
    # Add all changes
    git add .
    
    # Create commit with timestamp
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $commitMessage = "Backend deployment - $timestamp"
    git commit -m $commitMessage --no-verify
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Changes committed successfully" -ForegroundColor Green
        Write-Host "💡 Don't forget to push: git push" -ForegroundColor Cyan
    }
    else {
        Write-Host "⚠️  Commit failed - please commit manually" -ForegroundColor Yellow
    }
}
else {
    Write-Host "✅ No uncommitted changes" -ForegroundColor Green
}
