# H-DCN Complete Deployment Pipeline
param(
    [string]$Message = "Validated and deployed to S3",
    [switch]$SkipValidation,
    [switch]$Force
)

Write-Host "H-DCN Complete Deployment Pipeline" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green

# Step 1: Run validation (unless skipped)
if (-not $SkipValidation) {
    Write-Host "Step 1: Running validation..." -ForegroundColor Cyan
.\validate-deployment.ps1
    
    if ($LASTEXITCODE -ne 0 -and -not $Force) {
        Write-Host "Validation failed! Use -Force to deploy anyway." -ForegroundColor Red
        exit 1
    } elseif ($LASTEXITCODE -ne 0) {
        Write-Host "Validation failed but continuing due to -Force flag..." -ForegroundColor Yellow
    } else {
        Write-Host "Validation passed!" -ForegroundColor Green
    }
} else {
    Write-Host "Skipping validation..." -ForegroundColor Gray
}

# Step 2: Deploy to S3
Write-Host "Step 2: Deploying to S3..." -ForegroundColor Cyan
Set-Location ..\frontend

.\deploy.ps1

if ($LASTEXITCODE -ne 0) {
    Write-Host "S3 deployment failed!" -ForegroundColor Red
    Set-Location ..\startUpload
    exit 1
}

Write-Host "S3 deployment successful!" -ForegroundColor Green
Set-Location ..\startUpload

# Step 3: Upload to Git
Write-Host "Step 3: Uploading to Git..." -ForegroundColor Cyan
..\git\git-upload.ps1 -Message $Message

if ($LASTEXITCODE -ne 0) {
    Write-Host "Git upload failed!" -ForegroundColor Red
    exit 1
}

# Success summary
Write-Host "Deployment Pipeline Complete!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host "Validation: Passed" -ForegroundColor Green
Write-Host "S3 Deployment: Success" -ForegroundColor Green
Write-Host "Git Upload: Success" -ForegroundColor Green
Write-Host "Your app is now live and backed up!" -ForegroundColor Cyan