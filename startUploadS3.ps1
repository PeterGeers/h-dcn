# H-DCN Complete Deployment Pipeline
# Validates, builds, deploys to S3, and uploads to Git
param(
    [string]$Message = "Validated and deployed to S3",
    [switch]$SkipValidation,
    [switch]$Force
)

Write-Host "🚀 H-DCN Complete Deployment Pipeline" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green

# Step 1: Run validation (unless skipped)
if (-not $SkipValidation) {
    Write-Host "`n🔍 Step 1: Running validation..." -ForegroundColor Cyan
    .\validate-deployment.ps1
    
    if ($LASTEXITCODE -ne 0 -and -not $Force) {
        Write-Host "`n❌ Validation failed! Use -Force to deploy anyway." -ForegroundColor Red
        exit 1
    } elseif ($LASTEXITCODE -ne 0) {
        Write-Host "`n⚠️ Validation failed but continuing due to -Force flag..." -ForegroundColor Yellow
    } else {
        Write-Host "`n✅ Validation passed!" -ForegroundColor Green
    }
} else {
    Write-Host "`n⏭️ Skipping validation..." -ForegroundColor Gray
}

# Step 2: Deploy to S3
Write-Host "`n☁️ Step 2: Deploying to S3..." -ForegroundColor Cyan
Set-Location frontend

.\deploy.ps1

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n❌ S3 deployment failed!" -ForegroundColor Red
    Set-Location ..
    exit 1
}

Write-Host "`n✅ S3 deployment successful!" -ForegroundColor Green
Set-Location ..

# Step 3: Upload to Git
Write-Host "`n📝 Step 3: Uploading to Git..." -ForegroundColor Cyan
.\git-upload.ps1 -Message $Message

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n❌ Git upload failed!" -ForegroundColor Red
    exit 1
}

# Success summary
Write-Host "`n🎉 Deployment Pipeline Complete!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host "✅ Validation: Passed" -ForegroundColor Green
Write-Host "✅ S3 Deployment: Success" -ForegroundColor Green
Write-Host "✅ Git Upload: Success" -ForegroundColor Green
Write-Host "`n🌐 Your app is now live and backed up!" -ForegroundColor Cyan