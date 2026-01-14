#!/usr/bin/env pwsh
# Full Stack Deployment Script
# Deploys backend, frontend, and runs smoke tests

param(
    [switch]$SkipBackend,
    [switch]$SkipFrontend,
    [switch]$SkipTests,
    [string]$GitMessage = "Full stack deployment"
)

$ErrorActionPreference = "Stop"
$startTime = Get-Date

Write-Host ""
Write-Host "🚀 H-DCN Full Stack Deployment" -ForegroundColor Cyan
Write-Host "==============================" -ForegroundColor Cyan
Write-Host "⏱️  Started at: $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor Gray
Write-Host ""

$deploymentSteps = @()

# Step 1: Deploy Backend
if (-not $SkipBackend) {
    Write-Host "📦 Step 1: Deploying Backend..." -ForegroundColor Yellow
    Write-Host "================================" -ForegroundColor Yellow
    Write-Host "⏱️  Started at: $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor Gray
    Write-Host ""
    
    $backendStart = Get-Date
    & "$PSScriptRoot\backend-build-and-deploy-fast.ps1"
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Backend deployment failed!" -ForegroundColor Red
        $backendTime = (Get-Date) - $backendStart
        Write-Host "⏱️  Failed after: $([math]::Round($backendTime.TotalSeconds, 1)) seconds" -ForegroundColor Red
        exit 1
    }
    
    $backendTime = (Get-Date) - $backendStart
    $deploymentSteps += "Backend: $([math]::Round($backendTime.TotalSeconds, 1))s"
    Write-Host "✅ Backend completed in $([math]::Round($backendTime.TotalSeconds, 1)) seconds" -ForegroundColor Green
    Write-Host ""
}
else {
    Write-Host "⏭️  Skipping backend deployment" -ForegroundColor Gray
    Write-Host ""
}

# Step 2: Deploy Frontend
if (-not $SkipFrontend) {
    Write-Host "🎨 Step 2: Deploying Frontend..." -ForegroundColor Yellow
    Write-Host "================================" -ForegroundColor Yellow
    Write-Host "⏱️  Started at: $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor Gray
    Write-Host ""
    
    $frontendStart = Get-Date
    & "$PSScriptRoot\frontend-build-and-deploy-fast.ps1"
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Frontend deployment failed!" -ForegroundColor Red
        $frontendTime = (Get-Date) - $frontendStart
        Write-Host "⏱️  Failed after: $([math]::Round($frontendTime.TotalSeconds, 1)) seconds" -ForegroundColor Red
        exit 1
    }
    
    $frontendTime = (Get-Date) - $frontendStart
    $deploymentSteps += "Frontend: $([math]::Round($frontendTime.TotalSeconds, 1))s"
    Write-Host "✅ Frontend completed in $([math]::Round($frontendTime.TotalSeconds, 1)) seconds" -ForegroundColor Green
    Write-Host ""
}
else {
    Write-Host "⏭️  Skipping frontend deployment" -ForegroundColor Gray
    Write-Host ""
}

# Step 3: Run Full Smoke Tests (if not already run by individual scripts)
if (-not $SkipTests -and ($SkipBackend -or $SkipFrontend)) {
    Write-Host "🔥 Step 3: Running Full Stack Smoke Tests..." -ForegroundColor Yellow
    Write-Host "=============================================" -ForegroundColor Yellow
    Write-Host "⏱️  Started at: $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor Gray
    Write-Host ""
    
    $testStart = Get-Date
    node "$PSScriptRoot\smoke-test-production.js"
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Smoke tests failed!" -ForegroundColor Red
        Write-Host "⚠️  Deployment completed but application has issues" -ForegroundColor Yellow
        $testTime = (Get-Date) - $testStart
        Write-Host "⏱️  Failed after: $([math]::Round($testTime.TotalSeconds, 1)) seconds" -ForegroundColor Red
        exit 1
    }
    
    $testTime = (Get-Date) - $testStart
    $deploymentSteps += "Smoke Tests: $([math]::Round($testTime.TotalSeconds, 1))s"
    Write-Host "✅ Smoke tests completed in $([math]::Round($testTime.TotalSeconds, 1)) seconds" -ForegroundColor Green
    Write-Host ""
}

# Step 4: Git Commit (optional)
if ($GitMessage) {
    Write-Host "📝 Step 4: Committing to Git..." -ForegroundColor Yellow
    Write-Host "================================" -ForegroundColor Yellow
    Write-Host "⏱️  Started at: $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor Gray
    Write-Host ""
    
    $gitStart = Get-Date
    
    # Check if there are changes to commit
    $gitStatus = git status --porcelain 2>$null
    if ($gitStatus) {
        git add -A
        git commit -m $GitMessage
        git push
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Changes committed and pushed" -ForegroundColor Green
        }
        else {
            Write-Host "⚠️  Git push failed (changes committed locally)" -ForegroundColor Yellow
        }
    }
    else {
        Write-Host "ℹ️  No changes to commit" -ForegroundColor Cyan
    }
    
    $gitTime = (Get-Date) - $gitStart
    $deploymentSteps += "Git: $([math]::Round($gitTime.TotalSeconds, 1))s"
    Write-Host "✅ Git operations completed in $([math]::Round($gitTime.TotalSeconds, 1)) seconds" -ForegroundColor Green
    Write-Host ""
}

# Final Summary
$totalTime = (Get-Date) - $startTime
$endTime = Get-Date

Write-Host ""
Write-Host "🎉 Full Stack Deployment Complete!" -ForegroundColor Green
Write-Host "===================================" -ForegroundColor Green
Write-Host ""
Write-Host "📊 Deployment Summary:" -ForegroundColor Cyan
foreach ($step in $deploymentSteps) {
    Write-Host "   ✅ $step" -ForegroundColor White
}
Write-Host ""
Write-Host "⏱️  Timing Details:" -ForegroundColor Cyan
Write-Host "   Started:  $($startTime.ToString('HH:mm:ss'))" -ForegroundColor White
Write-Host "   Finished: $($endTime.ToString('HH:mm:ss'))" -ForegroundColor White
Write-Host "   Duration: $([math]::Round($totalTime.TotalMinutes, 1)) minutes ($([math]::Round($totalTime.TotalSeconds, 1)) seconds)" -ForegroundColor White
Write-Host ""
Write-Host "🌐 Application URLs:" -ForegroundColor Cyan
Write-Host "   Frontend: https://de1irtdutlxqu.cloudfront.net" -ForegroundColor White
Write-Host "   API: https://7fd6dxzhu7.execute-api.eu-west-1.amazonaws.com/dev" -ForegroundColor White
Write-Host ""
Write-Host "✨ Your application is live and tested!" -ForegroundColor Green
