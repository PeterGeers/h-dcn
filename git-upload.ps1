# Git Upload Script for H-DCN Repository
param(
    [string]$Message = "Update: $(Get-Date -Format 'yyyy-MM-dd HH:mm')",
    [switch]$Initial
)

Write-Host "🚀 H-DCN Git Upload Script" -ForegroundColor Green
Write-Host "Repository: h-dcn" -ForegroundColor Cyan

# Check if git is initialized
if (-not (Test-Path ".git")) {
    Write-Host "📁 Initializing Git repository..." -ForegroundColor Yellow
    git init
    git branch -M main
}

# Check if remote exists
$remoteExists = git remote get-url origin 2>$null
if (-not $remoteExists) {
    Write-Host "🔗 Adding GitHub remote..." -ForegroundColor Yellow
    $username = gh api user --jq .login
    git remote add origin "https://github.com/$username/h-dcn.git"
    Write-Host "Remote added: https://github.com/$username/h-dcn.git" -ForegroundColor Green
}

# Add all files
Write-Host "📦 Adding files..." -ForegroundColor Yellow
git add .

# Check if there are changes to commit
$status = git status --porcelain
if (-not $status) {
    Write-Host "✅ No changes to commit" -ForegroundColor Green
    exit 0
}

# Commit changes
Write-Host "💾 Committing changes..." -ForegroundColor Yellow
if ($Initial) {
    git commit -m "Initial commit: H-DCN Dashboard with mobile responsive improvements

Features:
- Mobile responsive tables with horizontal scroll
- Compact dropdown filters
- ProductCard with size selection
- Security fixes (XSS, hardcoded credentials)
- Lazy loading components
- AWS S3 deployment ready"
} else {
    git commit -m $Message
}

# Push to GitHub
Write-Host "⬆️ Pushing to GitHub..." -ForegroundColor Yellow
try {
    git push -u origin main
    Write-Host "✅ Successfully uploaded to GitHub!" -ForegroundColor Green
    
    # Get repository URL
    $username = gh api user --jq .login
    $repoUrl = "https://github.com/$username/h-dcn"
    Write-Host "🌐 Repository URL: $repoUrl" -ForegroundColor Cyan
    
} catch {
    Write-Host "❌ Push failed. Trying to pull first..." -ForegroundColor Red
    git pull origin main --allow-unrelated-histories
    git push -u origin main
    Write-Host "✅ Successfully uploaded after merge!" -ForegroundColor Green
}

Write-Host ""
Write-Host "🎉 Upload complete!" -ForegroundColor Green