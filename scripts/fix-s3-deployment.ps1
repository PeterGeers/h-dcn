# Fix S3 Deployment Issues
Write-Host "🔧 Fixing S3 Deployment Issues..." -ForegroundColor Yellow

# Step 1: Clean build and redeploy
Write-Host "1. Creating clean build..." -ForegroundColor Cyan
Set-Location frontend

# Clean everything
Remove-Item -Recurse -Force build -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force node_modules -ErrorAction SilentlyContinue

# Fresh install and build
npm install
$env:GENERATE_SOURCEMAP = "false"
npm run build

# Step 2: Clear S3 bucket completely
Write-Host "2. Clearing S3 bucket..." -ForegroundColor Cyan
aws s3 rm s3://hdcn-dashboard-frontend --recursive

# Step 3: Upload with proper settings
Write-Host "3. Uploading with proper configuration..." -ForegroundColor Cyan
aws s3 sync build/ s3://hdcn-dashboard-frontend --delete

# Step 4: Configure S3 for React Router
Write-Host "4. Configuring S3 for React Router..." -ForegroundColor Cyan

# Create error document configuration
$errorConfig = @"
{
    "ErrorDocument": {
        "Key": "index.html"
    },
    "IndexDocument": {
        "Suffix": "index.html"
    }
}
"@

$errorConfig | Out-File -FilePath "website-config.json" -Encoding UTF8

# Apply website configuration
aws s3api put-bucket-website --bucket hdcn-dashboard-frontend --website-configuration file://website-config.json

# Clean up temp file
Remove-Item "website-config.json"

Write-Host "✅ S3 deployment fixed!" -ForegroundColor Green
Write-Host "🌐 URL: http://hdcn-dashboard-frontend.s3-website-eu-west-1.amazonaws.com" -ForegroundColor Cyan

Set-Location ..