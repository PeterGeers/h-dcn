# End-to-End Validation Script for H-DCN Dashboard
param(
    [switch]$SkipBuild,
    [switch]$Verbose
)

Write-Host "🔍 H-DCN End-to-End Validation" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Green

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

# 1. Check Prerequisites
Write-Host "`n📋 Checking Prerequisites..." -ForegroundColor Cyan

# Check Node.js
try {
    $nodeVersion = node --version
    Log-Success "Node.js installed: $nodeVersion"
}
catch {
    Add-Error "Node.js not found. Install Node.js 18+"
}

# Check npm
try {
    $npmVersion = npm --version
    Log-Success "npm installed: $npmVersion"
}
catch {
    Add-Error "npm not found"
}

# Check AWS CLI
try {
    $awsVersion = aws --version
    Log-Success "AWS CLI installed: $awsVersion"
}
catch {
    Add-Warning "AWS CLI not found. Deployment may fail"
}

# 2. Check Environment Configuration
Write-Host "`n🔧 Checking Environment Configuration..." -ForegroundColor Cyan

$envFile = "frontend\.env"
if (Test-Path $envFile) {
    Log-Success ".env file exists"
    
    $envContent = Get-Content $envFile
    $requiredVars = @(
        "REACT_APP_AWS_REGION",
        "REACT_APP_USER_POOL_ID", 
        "REACT_APP_USER_POOL_WEB_CLIENT_ID",
        "REACT_APP_API_BASE_URL"
    )
    
    foreach ($var in $requiredVars) {
        if ($envContent -match "^$var=.+") {
            Log-Success "$var configured"
        }
        else {
            Add-Error "$var missing or empty in .env"
        }
    }
}
else {
    Add-Error ".env file missing in frontend directory"
}

# 3. Check Dependencies
Write-Host "`n📦 Checking Dependencies..." -ForegroundColor Cyan

Set-Location frontend

if (Test-Path "node_modules") {
    Log-Success "node_modules exists"
}
else {
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    npm install
    if ($LASTEXITCODE -eq 0) {
        Log-Success "Dependencies installed"
    }
    else {
        Add-Error "Failed to install dependencies"
    }
}

# Check for vulnerabilities
Write-Host "Checking for security vulnerabilities..." -ForegroundColor Yellow
$auditResult = npm audit --audit-level=high 2>&1
if ($LASTEXITCODE -eq 0) {
    Log-Success "No high/critical vulnerabilities found"
}
else {
    Add-Warning "Security vulnerabilities detected. Run 'npm audit fix'"
}

# 4. Build Test
if (-not $SkipBuild) {
    Write-Host "`n🔨 Testing Build Process..." -ForegroundColor Cyan
    
    # Clean previous build
    if (Test-Path "build") {
        Remove-Item -Recurse -Force build
    }
    
    # Test build
    Write-Host "Building application..." -ForegroundColor Yellow
    $env:GENERATE_SOURCEMAP = "false"
    npm run build
    
    if ($LASTEXITCODE -eq 0 -and (Test-Path "build")) {
        Log-Success "Build completed successfully"
        
        # Check build size
        $buildSize = (Get-ChildItem -Recurse build | Measure-Object -Property Length -Sum).Sum / 1MB
        if ($buildSize -lt 50) {
            Log-Success "Build size: $([math]::Round($buildSize, 2)) MB (Good)"
        }
        else {
            Add-Warning "Build size: $([math]::Round($buildSize, 2)) MB (Large - consider optimization)"
        }
    }
    else {
        Add-Error "Build failed"
    }
}
else {
    Write-Host "⏭️ Skipping build test" -ForegroundColor Gray
}

# 5. Code Quality Checks
Write-Host "`n🔍 Code Quality Checks..." -ForegroundColor Cyan

# Check for common issues in key files
$keyFiles = @(
    "src\App.tsx",
    "src\pages\Dashboard.tsx",
    "src\modules\members\MemberAdminPage.tsx",
    "src\modules\webshop\WebshopPage.tsx"
)

foreach ($file in $keyFiles) {
    if (Test-Path $file) {
        $content = Get-Content $file -Raw
        
        # Check for console.log (should be minimal in production)
        $consoleLogs = ($content | Select-String "console\.log" -AllMatches).Matches.Count
        if ($consoleLogs -gt 5) {
            Add-Warning "$file has $consoleLogs console.log statements"
        }
        
        # Check for hardcoded URLs
        if ($content -match "https://[^'`"]*\.amazonaws\.com") {
            Add-Warning "$file contains hardcoded AWS URLs"
        }
        
        Log-Success "$file validated"
    }
    else {
        Add-Error "$file missing"
    }
}

# 6. Check Git Status
Write-Host "`n📝 Checking Git Status..." -ForegroundColor Cyan
Set-Location ..

$gitStatus = git status --porcelain 2>$null
if ($gitStatus) {
    Add-Warning "Uncommitted changes detected. Consider committing before deployment"
    if ($Verbose) {
        Write-Host "Uncommitted files:" -ForegroundColor Yellow
        git status --short
    }
}
else {
    Log-Success "Git working directory clean"
}

# 8. Role Migration Validation
Write-Host "`n🔄 Validating Role Migration..." -ForegroundColor Cyan

# Check for deprecated role references in key files
$deprecatedRoles = @("hdcnAdmins", "Members_CRUD_All", "Products_CRUD_All", "Events_CRUD_All", "Members_Read_All", "Products_Read_All", "Events_Read_All")
$keyDeploymentFiles = @(
    "test-s3-list.ps1",
    "test-s3-api.ps1", 
    "cleanup-s3-bucket.ps1"
)

foreach ($file in $keyDeploymentFiles) {
    if (Test-Path $file) {
        $content = Get-Content $file -Raw
        $foundDeprecated = $false
        
        foreach ($role in $deprecatedRoles) {
            if ($content -match $role) {
                Add-Error "Deprecated role '$role' found in $file"
                $foundDeprecated = $true
            }
        }
        
        if (-not $foundDeprecated) {
            Log-Success "$file uses current role structure"
        }
    }
}

# Check that current roles are being used
$currentRoles = @("System_User_Management", "Members_CRUD", "Members_Read", "Products_CRUD", "Products_Read")
$foundCurrentRoles = $false

foreach ($file in $keyDeploymentFiles) {
    if (Test-Path $file) {
        $content = Get-Content $file -Raw
        foreach ($role in $currentRoles) {
            if ($content -match $role) {
                $foundCurrentRoles = $true
                break
            }
        }
    }
}

if ($foundCurrentRoles) {
    Log-Success "Deployment scripts use current role structure"
}
else {
    Add-Warning "No current role structure found in deployment scripts"
}

# 9. AWS Connectivity Test
Write-Host "`n☁️ Testing AWS Connectivity..." -ForegroundColor Cyan

try {
    $s3Test = aws s3 ls s3://hdcn-dashboard-frontend 2>&1
    if ($LASTEXITCODE -eq 0) {
        Log-Success "S3 bucket accessible"
    }
    else {
        Add-Warning "Cannot access S3 bucket. Check AWS credentials"
    }
}
catch {
    Add-Warning "AWS CLI test failed"
}

# 10. Final Report
Write-Host "`n📊 Validation Summary" -ForegroundColor Cyan
Write-Host "===================" -ForegroundColor Cyan

if ($errors.Count -eq 0 -and $warnings.Count -eq 0) {
    Write-Host "🎉 ALL CHECKS PASSED! Ready for deployment." -ForegroundColor Green
    $exitCode = 0
}
elseif ($errors.Count -eq 0) {
    Write-Host "✅ No critical errors found." -ForegroundColor Green
    Write-Host "⚠️ $($warnings.Count) warning(s) detected:" -ForegroundColor Yellow
    foreach ($warning in $warnings) {
        Write-Host "   • $warning" -ForegroundColor Yellow
    }
    Write-Host "`n💡 Deployment can proceed, but consider addressing warnings." -ForegroundColor Cyan
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
    Write-Host "   1. Run: .\git-upload.ps1 -Message 'Pre-deployment validation passed'" -ForegroundColor White
    Write-Host "   2. Run: cd frontend && .\deploy.ps1" -ForegroundColor White
}
else {
    Write-Host "   1. Fix the errors listed above" -ForegroundColor White
    Write-Host "   2. Re-run: .\validate-deployment.ps1" -ForegroundColor White
}

exit $exitCode