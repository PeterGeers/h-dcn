#!/usr/bin/env pwsh

$startTime = Get-Date

Write-Host "🔨 H-DCN Backend Build & Deploy" -ForegroundColor Cyan
Write-Host "==============================" -ForegroundColor Cyan
Write-Host ""

# Change to backend directory
Set-Location backend

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
sam deploy --no-confirm-changeset --no-fail-on-empty-changeset

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Deploy failed!" -ForegroundColor Red
    $deployTime = (Get-Date) - $deployStart
    Write-Host "⏱️ Deploy time: $($deployTime.TotalSeconds.ToString('F1')) seconds" -ForegroundColor Yellow
    exit 1
}

$deployTime = (Get-Date) - $deployStart
$totalTime = (Get-Date) - $startTime

Write-Host "✅ Backend deployment completed successfully" -ForegroundColor Green
Write-Host "⏱️ Deploy time: $($deployTime.TotalSeconds.ToString('F1')) seconds" -ForegroundColor Yellow
Write-Host "⏱️ Total time: $($totalTime.TotalSeconds.ToString('F1')) seconds" -ForegroundColor Cyan
Write-Host ""
Write-Host "🎉 Backend Deploy Complete!" -ForegroundColor Green

# Return to root directory
Set-Location ..