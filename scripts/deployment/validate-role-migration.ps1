# Role Migration Validation Script
# Validates that deployment scripts work with new role structure only

param(
    [switch]$Verbose
)

Write-Host "🔍 Role Migration Deployment Validation" -ForegroundColor Green
Write-Host "=======================================" -ForegroundColor Green

$errors = @()
$warnings = @()

# Function to add error
function Add-Error($message) {
    $script:errors += $message
    Write-Host "❌ ERROR: $message" -ForegroundColor Red
}

# Function to add warning
function Add-Warning($message) {
    $script:warnings += $message
    Write-Host "⚠️ WARNING: $message" -ForegroundColor Yellow
}

# Function to log success
function Log-Success($message) {
    Write-Host "✅ $message" -ForegroundColor Green
}

# 1. Check for deprecated role references in deployment scripts
Write-Host "`n📋 Checking for deprecated role references..." -ForegroundColor Cyan

$deploymentScripts = @(
    "test-s3-list.ps1",
    "test-s3-api.ps1", 
    "cleanup-s3-bucket.ps1",
    "startUpload/startUploadS3.ps1",
    "scripts/deployment/frontend-build-and-deploy-fast.ps1",
    "scripts/deployment/frontend-build-and-deploy-safe.ps1",
    "scripts/deployment/backend-build-and-deploy-fast.ps1"
    # Note: Excluding validation scripts as they legitimately contain deprecated role names for checking
)

$deprecatedRoles = @("hdcnAdmins", "Members_CRUD_All", "Products_CRUD_All", "Events_CRUD_All", "Members_Read_All", "Products_Read_All", "Events_Read_All")

foreach ($script in $deploymentScripts) {
    if (Test-Path $script) {
        $content = Get-Content $script -Raw
        $foundDeprecated = $false
        
        foreach ($role in $deprecatedRoles) {
            if ($content -match $role) {
                Add-Error "Deprecated role '$role' found in $script"
                $foundDeprecated = $true
            }
        }
        
        if (-not $foundDeprecated) {
            Log-Success "$script - No deprecated roles found"
        }
    }
    else {
        Add-Warning "Deployment script not found: $script"
    }
}

# 2. Check for current role structure usage
Write-Host "`n🔧 Checking for current role structure usage..." -ForegroundColor Cyan

$currentRoles = @("System_User_Management", "Members_CRUD", "Members_Read", "Products_CRUD", "Products_Read", "Events_CRUD", "Events_Read", "Regio_All")

$scriptsWithCurrentRoles = 0
foreach ($script in $deploymentScripts) {
    if (Test-Path $script) {
        $content = Get-Content $script -Raw
        $foundCurrent = $false
        
        foreach ($role in $currentRoles) {
            if ($content -match $role) {
                $foundCurrent = $true
                break
            }
        }
        
        if ($foundCurrent) {
            Log-Success "$script - Uses current role structure"
            $scriptsWithCurrentRoles++
        }
    }
}

if ($scriptsWithCurrentRoles -eq 0) {
    Add-Warning "No deployment scripts found using current role structure"
}

# 3. Validate SAM template doesn't reference old roles
Write-Host "`n📦 Checking SAM template..." -ForegroundColor Cyan

$samTemplate = "backend/template.yaml"
if (Test-Path $samTemplate) {
    $content = Get-Content $samTemplate -Raw
    $foundDeprecated = $false
    
    foreach ($role in $deprecatedRoles) {
        if ($content -match $role) {
            Add-Error "Deprecated role '$role' found in SAM template"
            $foundDeprecated = $true
        }
    }
    
    if (-not $foundDeprecated) {
        Log-Success "SAM template - No deprecated roles found"
    }
}
else {
    Add-Warning "SAM template not found: $samTemplate"
}

# 4. Check environment configuration files
Write-Host "`n🔧 Checking environment configuration..." -ForegroundColor Cyan

$envFiles = @(
    "frontend/.env",
    "frontend/.env.example"
)

foreach ($envFile in $envFiles) {
    if (Test-Path $envFile) {
        $content = Get-Content $envFile -Raw
        $foundDeprecated = $false
        
        foreach ($role in $deprecatedRoles) {
            if ($content -match $role) {
                Add-Error "Deprecated role '$role' found in $envFile"
                $foundDeprecated = $true
            }
        }
        
        if (-not $foundDeprecated) {
            Log-Success "$envFile - No deprecated roles found"
        }
    }
    else {
        Add-Warning "Environment file not found: $envFile"
    }
}

# 5. Check for hardcoded role references in configuration
Write-Host "`n📄 Checking configuration files..." -ForegroundColor Cyan

$configFiles = @(
    "frontend/public/parameters.json"
)

foreach ($configFile in $configFiles) {
    if (Test-Path $configFile) {
        $content = Get-Content $configFile -Raw
        $foundDeprecated = $false
        
        foreach ($role in $deprecatedRoles) {
            if ($content -match $role) {
                Add-Error "Deprecated role '$role' found in $configFile"
                $foundDeprecated = $true
            }
        }
        
        if (-not $foundDeprecated) {
            Log-Success "$configFile - No deprecated roles found"
        }
    }
    else {
        Add-Warning "Configuration file not found: $configFile"
    }
}

# 6. Validate deployment process compatibility
Write-Host "`n🚀 Checking deployment process compatibility..." -ForegroundColor Cyan

# Check if AWS CLI is available for deployment
try {
    $awsVersion = aws --version
    Log-Success "AWS CLI available for deployment: $awsVersion"
}
catch {
    Add-Error "AWS CLI not found - required for deployment"
}

# Check if SAM CLI is available for backend deployment
try {
    $samVersion = sam --version
    Log-Success "SAM CLI available for backend deployment: $samVersion"
}
catch {
    Add-Warning "SAM CLI not found - backend deployment may fail"
}

# Check if Node.js is available for frontend build
try {
    $nodeVersion = node --version
    Log-Success "Node.js available for frontend build: $nodeVersion"
}
catch {
    Add-Error "Node.js not found - frontend build will fail"
}

# 7. Final Report
Write-Host "`n📊 Role Migration Validation Summary" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan

if ($errors.Count -eq 0 -and $warnings.Count -eq 0) {
    Write-Host "🎉 ALL CHECKS PASSED! Deployment scripts are ready for new role structure." -ForegroundColor Green
    $exitCode = 0
}
elseif ($errors.Count -eq 0) {
    Write-Host "✅ No critical errors found." -ForegroundColor Green
    Write-Host "⚠️ $($warnings.Count) warning(s) detected:" -ForegroundColor Yellow
    foreach ($warning in $warnings) {
        Write-Host "   • $warning" -ForegroundColor Yellow
    }
    Write-Host "`n💡 Deployment can proceed with new role structure." -ForegroundColor Cyan
    $exitCode = 0
}
else {
    Write-Host "❌ $($errors.Count) error(s) found:" -ForegroundColor Red
    foreach ($error in $errors) {
        Write-Host "   • $error" -ForegroundColor Red
    }
    if ($warnings.Count -gt 0) {
        Write-Host "`n⚠️ $($warnings.Count) warning(s):" -ForegroundColor Yellow
        foreach ($warning in $warnings) {
            Write-Host "   • $warning" -ForegroundColor Yellow
        }
    }
    Write-Host "`n🚫 Fix errors before deployment!" -ForegroundColor Red
    $exitCode = 1
}

Write-Host "`n🚀 Next Steps:" -ForegroundColor Cyan
if ($exitCode -eq 0) {
    Write-Host "   1. Deployment scripts are compatible with new role structure" -ForegroundColor White
    Write-Host "   2. Run normal deployment: .\startUpload\startUploadS3.ps1" -ForegroundColor White
    Write-Host "   3. Backend deployment: .\scripts\deployment\backend-build-and-deploy-fast.ps1" -ForegroundColor White
}
else {
    Write-Host "   1. Fix the errors listed above" -ForegroundColor White
    Write-Host "   2. Re-run: .\scripts\deployment\validate-role-migration.ps1" -ForegroundColor White
}

Write-Host "`n📋 Role Structure Summary:" -ForegroundColor Cyan
Write-Host "   ✅ Current Roles: Members_CRUD, Members_Read, Products_CRUD, Products_Read, Events_CRUD, Events_Read" -ForegroundColor Green
Write-Host "   ✅ Regional Roles: Regio_All, Regio_Utrecht, Regio_Limburg, etc." -ForegroundColor Green
Write-Host "   ✅ System Roles: System_User_Management, Webshop_Management" -ForegroundColor Green
Write-Host "   ❌ Deprecated: hdcnAdmins, *_All roles (except Regio_All)" -ForegroundColor Red

exit $exitCode