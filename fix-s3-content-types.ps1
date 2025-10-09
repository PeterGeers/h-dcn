# Fix S3 Content Types and Routing
Write-Host "Fixing S3 Content Types and Routing..." -ForegroundColor Green

# Set correct content type for index.html
Write-Host "Setting correct content type for index.html..." -ForegroundColor Yellow
aws s3 cp s3://hdcn-dashboard-frontend/index.html s3://hdcn-dashboard-frontend/index.html --metadata-directive REPLACE --content-type "text/html" --cache-control "no-cache, no-store, must-revalidate"

# Set correct content types for CSS and JS files
Write-Host "Setting content types for static assets..." -ForegroundColor Yellow
aws s3 cp s3://hdcn-dashboard-frontend/static/ s3://hdcn-dashboard-frontend/static/ --recursive --metadata-directive REPLACE --exclude "*" --include "*.css" --content-type "text/css"
aws s3 cp s3://hdcn-dashboard-frontend/static/ s3://hdcn-dashboard-frontend/static/ --recursive --metadata-directive REPLACE --exclude "*" --include "*.js" --content-type "application/javascript"

# Configure S3 website hosting
Write-Host "Configuring S3 website hosting..." -ForegroundColor Yellow
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
Remove-Item "website-config.json" -ErrorAction SilentlyContinue

Write-Host "S3 content types and routing fixed!" -ForegroundColor Green
Write-Host "Website: http://hdcn-dashboard-frontend.s3-website-eu-west-1.amazonaws.com" -ForegroundColor Cyan