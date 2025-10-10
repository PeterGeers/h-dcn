# Fix S3 React Router Issues
# Ensures proper S3 website configuration for SPA routing

Write-Host "🔧 Fixing S3 React Router Configuration..." -ForegroundColor Green

# Check if bucket exists and is accessible
Write-Host "📋 Checking S3 bucket access..." -ForegroundColor Yellow
aws s3 ls s3://hdcn-dashboard-frontend/ --summarize

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Cannot access S3 bucket!" -ForegroundColor Red
    exit 1
}

# Configure S3 website hosting with proper error document
Write-Host "🌐 Configuring S3 website hosting..." -ForegroundColor Yellow
$websiteConfig = @'
{
    "IndexDocument": {
        "Suffix": "index.html"
    },
    "ErrorDocument": {
        "Key": "index.html"
    }
}
'@

$websiteConfig | Out-File -FilePath "website-config.json" -Encoding ASCII
aws s3api put-bucket-website --bucket hdcn-dashboard-frontend --website-configuration file://website-config.json

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to configure S3 website!" -ForegroundColor Red
    Remove-Item "website-config.json" -ErrorAction SilentlyContinue
    exit 1
}

# Set no-cache headers on index.html to prevent routing issues
Write-Host "🔄 Setting cache headers on index.html..." -ForegroundColor Yellow
aws s3 cp s3://hdcn-dashboard-frontend/index.html s3://hdcn-dashboard-frontend/index.html --metadata-directive REPLACE --cache-control "no-cache, no-store, must-revalidate"

# Verify configuration
Write-Host "✅ Verifying website configuration..." -ForegroundColor Yellow
aws s3api get-bucket-website --bucket hdcn-dashboard-frontend

# Test the routing
Write-Host "🧪 Testing routing endpoints..." -ForegroundColor Yellow
$testUrls = @(
    "http://hdcn-dashboard-frontend.s3-website-eu-west-1.amazonaws.com/",
    "http://hdcn-dashboard-frontend.s3-website-eu-west-1.amazonaws.com/members",
    "http://hdcn-dashboard-frontend.s3-website-eu-west-1.amazonaws.com/products"
)

foreach ($url in $testUrls) {
    Write-Host "Testing: $url" -ForegroundColor Gray
    try {
        $response = Invoke-WebRequest -Uri $url -Method Head -TimeoutSec 10 -ErrorAction Stop
        Write-Host "  ✅ Status: $($response.StatusCode)" -ForegroundColor Green
    } catch {
        Write-Host "  ❌ Error: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Remove-Item "website-config.json" -ErrorAction SilentlyContinue

Write-Host "`n🎉 S3 routing configuration complete!" -ForegroundColor Green
Write-Host "🌐 Website: http://hdcn-dashboard-frontend.s3-website-eu-west-1.amazonaws.com" -ForegroundColor Cyan