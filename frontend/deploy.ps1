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

# Deploy to S3 with proper content types and cache headers
Write-Host "☁️ Uploading to S3 bucket hdcn-dashboard-frontend..." -ForegroundColor Yellow
# Upload all files first
aws s3 sync build/ s3://hdcn-dashboard-frontend --delete
# Fix content-type for index.html specifically
aws s3 cp s3://hdcn-dashboard-frontend/index.html s3://hdcn-dashboard-frontend/index.html --metadata-directive REPLACE --content-type "text/html" --cache-control "no-cache, no-store, must-revalidate"

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ S3 upload failed!" -ForegroundColor Red
    exit 1
}

# Configure S3 for React Router (SPA) with advanced routing rules
Write-Host "🔧 Configuring S3 for React Router with routing rules..." -ForegroundColor Yellow
$websiteConfig = @'
{
    "IndexDocument": {
        "Suffix": "index.html"
    },
    "ErrorDocument": {
        "Key": "index.html"
    },
    "RoutingRules": [
        {
            "Condition": {
                "HttpErrorCodeReturnedEquals": "404"
            },
            "Redirect": {
                "ReplaceKeyWith": "index.html"
            }
        }
    ]
}
'@

$websiteConfig | Out-File -FilePath "temp-website-config.json" -Encoding ASCII
aws s3api put-bucket-website --bucket hdcn-dashboard-frontend --website-configuration file://temp-website-config.json

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ S3 website configuration failed!" -ForegroundColor Red
    Remove-Item "temp-website-config.json" -ErrorAction SilentlyContinue
    exit 1
}

Remove-Item "temp-website-config.json" -ErrorAction SilentlyContinue

# Set proper cache headers for index.html to prevent routing issues
Write-Host "🔄 Setting cache headers for SPA routing..." -ForegroundColor Yellow
aws s3 cp s3://hdcn-dashboard-frontend/index.html s3://hdcn-dashboard-frontend/index.html --metadata-directive REPLACE --cache-control "no-cache, no-store, must-revalidate"



Write-Host "✅ Deployment completed successfully!" -ForegroundColor Green
Write-Host "🌐 Website URL: http://hdcn-dashboard-frontend.s3-website-eu-west-1.amazonaws.com" -ForegroundColor Cyan