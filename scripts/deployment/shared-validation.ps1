# Shared Validation Functions for H-DCN Deployment Scripts
# GitLens-inspired pre-deployment checks

function Test-AuthLayerSync {
    param(
        [string]$MainFile = 'backend/shared/auth_utils.py',
        [string]$LayerFile = 'backend/layers/auth-layer/python/shared/auth_utils.py'
    )
    
    Write-Host "  📋 Checking AuthLayer synchronization..." -ForegroundColor Cyan
    
    if ((Test-Path $MainFile) -and (Test-Path $LayerFile)) {
        $mainHash = Get-FileHash $MainFile
        $layerHash = Get-FileHash $LayerFile
        
        if ($mainHash.Hash -eq $layerHash.Hash) {
            Write-Host "     ✅ AuthLayer files are synchronized" -ForegroundColor Green
            return $true
        }
        else {
            Write-Host "     ❌ AuthLayer files are OUT OF SYNC!" -ForegroundColor Red
            Write-Host "     Main: $MainFile" -ForegroundColor White
            Write-Host "     Layer: $LayerFile" -ForegroundColor White
            Write-Host "     This will cause 'Authentication not available' errors!" -ForegroundColor Red
            
            # Auto-fix option
            $response = Read-Host "     🔧 Auto-sync files? (y/N)"
            if ($response -eq 'y' -or $response -eq 'Y') {
                Copy-Item $MainFile $LayerFile -Force
                Write-Host "     ✅ AuthLayer files synchronized" -ForegroundColor Green
                return $true
            }
            else {
                Write-Host "     ⚠️  Continuing with out-of-sync files (not recommended)" -ForegroundColor Yellow
                return $false
            }
        }
    }
    else {
        Write-Host "     ❌ AuthLayer files missing!" -ForegroundColor Red
        Write-Host "       Main file exists: $(Test-Path $MainFile)" -ForegroundColor White
        Write-Host "       Layer file exists: $(Test-Path $LayerFile)" -ForegroundColor White
        return $false
    }
}

function Test-CriticalFilesStatus {
    param(
        [string[]]$Files
    )
    
    Write-Host "  📊 Checking critical files status..." -ForegroundColor Cyan
    
    $hasUncommittedChanges = $false
    $modifiedFiles = @()
    
    foreach ($file in $Files) {
        if (Test-Path $file) {
            $gitStatus = git status --porcelain $file 2>$null
            if ($gitStatus) {
                $hasUncommittedChanges = $true
                $modifiedFiles += $file
            }
        }
    }
    
    if ($hasUncommittedChanges) {
        Write-Host "     ⚠️  Uncommitted changes in critical files:" -ForegroundColor Yellow
        foreach ($file in $modifiedFiles) {
            Write-Host "       • $file" -ForegroundColor White
        }
        return $false
    }
    else {
        Write-Host "     ✅ No uncommitted changes in critical files" -ForegroundColor Green
        return $true
    }
}

function Show-RecentChanges {
    param(
        [string[]]$Files,
        [string]$TimeFrame = "1 hour ago"
    )
    
    Write-Host "  📈 Checking recent changes..." -ForegroundColor Cyan
    
    $recentChanges = git log --oneline -5 --since=$TimeFrame -- $Files 2>$null
    if ($recentChanges) {
        Write-Host "     ⚠️  Recent changes to critical files (since $TimeFrame):" -ForegroundColor Yellow
        $recentChanges | ForEach-Object { Write-Host "       • $_" -ForegroundColor White }
        return $true
    }
    else {
        Write-Host "     ✅ No recent changes to critical files" -ForegroundColor Green
        return $false
    }
}

function Show-GitInfo {
    Write-Host "  🌿 Current branch info..." -ForegroundColor Cyan
    
    $currentBranch = git branch --show-current 2>$null
    $lastCommit = git log -1 --oneline 2>$null
    $uncommittedCount = (git status --porcelain 2>$null | Measure-Object).Count
    
    if ($currentBranch -and $lastCommit) {
        Write-Host "     Branch: $currentBranch" -ForegroundColor White
        Write-Host "     Last commit: $lastCommit" -ForegroundColor White
        
        if ($uncommittedCount -gt 0) {
            Write-Host "     ⚠️  $uncommittedCount uncommitted changes" -ForegroundColor Yellow
        }
        else {
            Write-Host "     ✅ Working directory clean" -ForegroundColor Green
        }
    }
    else {
        Write-Host "     ⚠️  Git information unavailable" -ForegroundColor Yellow
    }
}

function Test-EnvironmentConfig {
    param(
        [string]$EnvFile = 'frontend/.env'
    )
    
    Write-Host "  ⚙️  Checking environment configuration..." -ForegroundColor Cyan
    
    if (Test-Path $EnvFile) {
        $envContent = Get-Content $EnvFile
        $apiBaseUrl = $envContent | Where-Object { $_ -match '^REACT_APP_API_BASE_URL=' }
        $userPoolId = $envContent | Where-Object { $_ -match '^REACT_APP_USER_POOL_ID=' }
        
        if ($apiBaseUrl -and $userPoolId) {
            Write-Host "     ✅ Environment configuration found" -ForegroundColor Green
            $apiUrl = $apiBaseUrl -replace 'REACT_APP_API_BASE_URL=', ''
            Write-Host "       API: $apiUrl" -ForegroundColor White
            return $true
        }
        else {
            Write-Host "     ⚠️  Missing critical environment variables" -ForegroundColor Yellow
            if (-not $apiBaseUrl) { Write-Host "       Missing: REACT_APP_API_BASE_URL" -ForegroundColor White }
            if (-not $userPoolId) { Write-Host "       Missing: REACT_APP_USER_POOL_ID" -ForegroundColor White }
            return $false
        }
    }
    else {
        Write-Host "     ❌ .env file not found: $EnvFile" -ForegroundColor Red
        return $false
    }
}

function Invoke-PreDeploymentValidation {
    param(
        [string]$Type = "backend", # "backend" or "frontend"
        [switch]$Interactive = $true
    )
    
    Write-Host "🔍 Pre-deployment validation ($Type)..." -ForegroundColor Yellow
    
    $validationPassed = $true
    
    # Common validations
    Show-GitInfo
    
    if ($Type -eq "backend") {
        # Backend-specific validations
        $authSyncOk = Test-AuthLayerSync
        if (-not $authSyncOk) { $validationPassed = $false }
        
        $criticalFiles = @(
            'backend/template.yaml',
            'backend/samconfig.toml',
            'backend/shared/auth_utils.py',
            'backend/layers/auth-layer/python/shared/auth_utils.py'
        )
        
        Test-CriticalFilesStatus -Files $criticalFiles
        Show-RecentChanges -Files $criticalFiles
        
    }
    elseif ($Type -eq "frontend") {
        # Frontend-specific validations
        $envOk = Test-EnvironmentConfig
        if (-not $envOk) { $validationPassed = $false }
        
        $criticalFiles = @(
            'frontend/.env',
            'frontend/src/utils/authHeaders.ts',
            'frontend/src/services/apiService.ts',
            'frontend/src/components/common/GroupAccessGuard.tsx'
        )
        
        Test-CriticalFilesStatus -Files $criticalFiles
        Show-RecentChanges -Files $criticalFiles
        
        # Check dependencies
        Write-Host "  📦 Checking dependencies..." -ForegroundColor Cyan
        if (Test-Path 'frontend/node_modules') {
            Write-Host "     ✅ Dependencies installed" -ForegroundColor Green
        }
        else {
            Write-Host "     ⚠️  Node modules not found - will install during build" -ForegroundColor Yellow
        }
    }
    
    if ($validationPassed) {
        Write-Host "✅ Pre-deployment validation completed successfully" -ForegroundColor Green
    }
    else {
        Write-Host "⚠️  Pre-deployment validation completed with warnings" -ForegroundColor Yellow
        
        if ($Interactive) {
            $response = Read-Host "Continue with deployment? (y/N)"
            if ($response -ne 'y' -and $response -ne 'Y') {
                Write-Host "❌ Deployment cancelled by user" -ForegroundColor Red
                exit 1
            }
        }
    }
    
    Write-Host ""
    return $validationPassed
}

# Functions are available for dot-sourcing