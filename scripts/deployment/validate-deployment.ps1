#!/usr/bin/env pwsh
# Comprehensive Deployment Validation Script
# GitLens-inspired checks for H-DCN project

param(
    [Parameter(Mandatory = $false)]
    [ValidateSet("backend", "frontend", "both")]
    [string]$Type = "both",
    
    [Parameter(Mandatory = $false)]
    [switch]$Fix,
    
    [Parameter(Mandatory = $false)]
    [switch]$Detailed
)

# Import shared validation functions
. "$PSScriptRoot/shared-validation.ps1"

Write-Host ""
Write-Host "🔍 H-DCN Deployment Validation" -ForegroundColor Cyan
Write-Host "==============================" -ForegroundColor Cyan
Write-Host ""

$overallStatus = $true

if ($Type -eq "backend" -or $Type -eq "both") {
    Write-Host "🔧 Backend Validation" -ForegroundColor Yellow
    Write-Host "--------------------" -ForegroundColor Yellow
    
    # AuthLayer Sync Check
    $mainFile = 'backend/shared/auth_utils.py'
    $layerFile = 'backend/layers/auth-layer/python/shared/auth_utils.py'
    
    if ((Test-Path $mainFile) -and (Test-Path $layerFile)) {
        $mainHash = Get-FileHash $mainFile
        $layerHash = Get-FileHash $layerFile
        
        if ($mainHash.Hash -eq $layerHash.Hash) {
            Write-Host "✅ AuthLayer files are synchronized" -ForegroundColor Green
        }
        else {
            Write-Host "❌ AuthLayer files are OUT OF SYNC!" -ForegroundColor Red
            $overallStatus = $false
            
            if ($Detailed) {
                Write-Host "   Main file: $mainFile" -ForegroundColor White
                Write-Host "   Layer file: $layerFile" -ForegroundColor White
                Write-Host "   Main hash: $($mainHash.Hash.Substring(0,16))..." -ForegroundColor Gray
                Write-Host "   Layer hash: $($layerHash.Hash.Substring(0,16))..." -ForegroundColor Gray
            }
            
            if ($Fix) {
                Write-Host "🔧 Auto-fixing: Syncing AuthLayer files..." -ForegroundColor Yellow
                Copy-Item $mainFile $layerFile -Force
                Write-Host "✅ AuthLayer files synchronized" -ForegroundColor Green
                $overallStatus = $true
            }
            else {
                Write-Host "💡 Run with -Fix to automatically sync files" -ForegroundColor Cyan
            }
        }
    }
    else {
        Write-Host "❌ AuthLayer files missing!" -ForegroundColor Red
        Write-Host "   Main file exists: $(Test-Path $mainFile)" -ForegroundColor White
        Write-Host "   Layer file exists: $(Test-Path $layerFile)" -ForegroundColor White
        $overallStatus = $false
    }
    
    # SAM Template Validation
    Write-Host ""
    Write-Host "📋 SAM Template Validation" -ForegroundColor Cyan
    if (Test-Path 'backend/template.yaml') {
        Push-Location backend
        $samValidation = sam validate --template template.yaml --lint 2>&1
        Pop-Location
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ SAM template is valid" -ForegroundColor Green
        }
        else {
            Write-Host "❌ SAM template validation failed" -ForegroundColor Red
            if ($Detailed) {
                Write-Host $samValidation -ForegroundColor Gray
            }
            $overallStatus = $false
        }
    }
    else {
        Write-Host "❌ SAM template not found" -ForegroundColor Red
        $overallStatus = $false
    }
    
    # Critical Backend Files
    Write-Host ""
    Write-Host "📊 Backend Critical Files Status" -ForegroundColor Cyan
    $backendFiles = @(
        'backend/template.yaml',
        'backend/samconfig.toml',
        'backend/shared/auth_utils.py',
        'backend/layers/auth-layer/python/shared/auth_utils.py'
    )
    
    $uncommittedFiles = @()
    foreach ($file in $backendFiles) {
        if (Test-Path $file) {
            $gitStatus = git status --porcelain $file 2>$null
            if ($gitStatus) {
                $uncommittedFiles += $file
            }
        }
    }
    
    if ($uncommittedFiles.Count -eq 0) {
        Write-Host "✅ No uncommitted changes in critical backend files" -ForegroundColor Green
    }
    else {
        Write-Host "⚠️  Uncommitted changes in critical files:" -ForegroundColor Yellow
        foreach ($file in $uncommittedFiles) {
            Write-Host "   • $file" -ForegroundColor White
        }
    }
    
    Write-Host ""
}

if ($Type -eq "frontend" -or $Type -eq "both") {
    Write-Host "🌐 Frontend Validation" -ForegroundColor Yellow
    Write-Host "---------------------" -ForegroundColor Yellow
    
    # Environment Configuration
    $envFile = 'frontend/.env'
    if (Test-Path $envFile) {
        $envContent = Get-Content $envFile
        $requiredVars = @(
            'REACT_APP_API_BASE_URL',
            'REACT_APP_USER_POOL_ID',
            'REACT_APP_USER_POOL_WEB_CLIENT_ID'
        )
        
        $missingVars = @()
        foreach ($var in $requiredVars) {
            $found = $envContent | Where-Object { $_ -match "^$var=" }
            if (-not $found) {
                $missingVars += $var
            }
        }
        
        if ($missingVars.Count -eq 0) {
            Write-Host "✅ Environment configuration complete" -ForegroundColor Green
            
            if ($Detailed) {
                $apiUrl = ($envContent | Where-Object { $_ -match '^REACT_APP_API_BASE_URL=' }) -replace 'REACT_APP_API_BASE_URL=', ''
                Write-Host "   API URL: $apiUrl" -ForegroundColor White
            }
        }
        else {
            Write-Host "❌ Missing environment variables:" -ForegroundColor Red
            foreach ($var in $missingVars) {
                Write-Host "   • $var" -ForegroundColor White
            }
            $overallStatus = $false
        }
    }
    else {
        Write-Host "❌ Environment file not found: $envFile" -ForegroundColor Red
        $overallStatus = $false
    }
    
    # Authentication Files
    Write-Host ""
    Write-Host "🔐 Authentication Files Check" -ForegroundColor Cyan
    $authFiles = @(
        'frontend/src/utils/authHeaders.ts',
        'frontend/src/services/apiService.ts',
        'frontend/src/components/common/GroupAccessGuard.tsx'
    )
    
    $missingAuthFiles = @()
    foreach ($file in $authFiles) {
        if (-not (Test-Path $file)) {
            $missingAuthFiles += $file
        }
    }
    
    if ($missingAuthFiles.Count -eq 0) {
        Write-Host "✅ All authentication files present" -ForegroundColor Green
    }
    else {
        Write-Host "❌ Missing authentication files:" -ForegroundColor Red
        foreach ($file in $missingAuthFiles) {
            Write-Host "   • $file" -ForegroundColor White
        }
        $overallStatus = $false
    }
    
    # Dependencies
    Write-Host ""
    Write-Host "📦 Dependencies Check" -ForegroundColor Cyan
    if (Test-Path 'frontend/node_modules') {
        Write-Host "✅ Node modules installed" -ForegroundColor Green
    }
    else {
        Write-Host "⚠️  Node modules not found" -ForegroundColor Yellow
        Write-Host "   Run 'npm install' in frontend directory" -ForegroundColor White
    }
    
    Write-Host ""
}

# Git Information
Write-Host "🌿 Git Status" -ForegroundColor Yellow
Write-Host "-------------" -ForegroundColor Yellow

$currentBranch = git branch --show-current 2>$null
$lastCommit = git log -1 --oneline 2>$null
$uncommittedCount = (git status --porcelain 2>$null | Measure-Object).Count

if ($currentBranch -and $lastCommit) {
    Write-Host "Branch: $currentBranch" -ForegroundColor White
    Write-Host "Last commit: $lastCommit" -ForegroundColor White
    
    if ($uncommittedCount -gt 0) {
        Write-Host "⚠️  $uncommittedCount uncommitted changes" -ForegroundColor Yellow
        
        if ($Detailed) {
            Write-Host "Uncommitted files:" -ForegroundColor Gray
            git status --porcelain | ForEach-Object { Write-Host "   $_" -ForegroundColor Gray }
        }
    }
    else {
        Write-Host "✅ Working directory clean" -ForegroundColor Green
    }
}
else {
    Write-Host "⚠️  Git information unavailable" -ForegroundColor Yellow
}

# Recent Changes
Write-Host ""
Write-Host "📈 Recent Changes (last 24 hours)" -ForegroundColor Yellow
Write-Host "----------------------------------" -ForegroundColor Yellow

$recentCommits = git log --oneline --since="24 hours ago" 2>$null
if ($recentCommits) {
    Write-Host "Recent commits:" -ForegroundColor White
    $recentCommits | Select-Object -First 5 | ForEach-Object { Write-Host "   • $_" -ForegroundColor White }
    
    if ($recentCommits.Count -gt 5) {
        Write-Host "   ... and $($recentCommits.Count - 5) more" -ForegroundColor Gray
    }
}
else {
    Write-Host "✅ No commits in the last 24 hours" -ForegroundColor Green
}

# Summary
Write-Host ""
Write-Host "📋 Validation Summary" -ForegroundColor Yellow
Write-Host "--------------------" -ForegroundColor Yellow

if ($overallStatus) {
    Write-Host "✅ All validations passed - Ready for deployment!" -ForegroundColor Green
    exit 0
}
else {
    Write-Host "❌ Some validations failed - Review issues before deployment" -ForegroundColor Red
    Write-Host ""
    Write-Host "💡 Tips:" -ForegroundColor Cyan
    Write-Host "   • Run with -Fix to auto-fix some issues" -ForegroundColor White
    Write-Host "   • Run with -Detailed for more information" -ForegroundColor White
    Write-Host "   • Check individual files mentioned above" -ForegroundColor White
    exit 1
}