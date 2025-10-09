# H-DCN Dashboard Deployment Script
# Builds and deploys React app to S3

Write-Host "🚀 Starting H-DCN Dashboard deployment..." -ForegroundColor Green

# Build the React application
Write-Host "📦 Building React application..." -ForegroundColor Yellow
npm run build

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Build failed!" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Build completed successfully!" -ForegroundColor Green

# Deploy to S3
Write-Host "☁️ Uploading to S3 bucket hdcn-dashboard-frontend..." -ForegroundColor Yellow
aws s3 sync build/ s3://hdcn-dashboard-frontend --delete

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ S3 upload failed!" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Deployment completed successfully!" -ForegroundColor Green
Write-Host "🌐 Website URL: http://hdcn-dashboard-frontend.s3-website-eu-west-1.amazonaws.com" -ForegroundColor Cyan