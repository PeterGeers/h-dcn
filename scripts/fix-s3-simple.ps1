# Remove problematic routing rules and use simple ErrorDocument approach
Write-Host "Removing problematic routing rules..." -ForegroundColor Green

# Simple S3 website configuration without routing rules
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

$websiteConfig | Out-File -FilePath "simple-website-config.json" -Encoding ASCII
aws s3api put-bucket-website --bucket hdcn-dashboard-frontend --website-configuration file://simple-website-config.json

# Clean up any HTML files that were created in wrong locations
Write-Host "Cleaning up incorrectly placed HTML files..." -ForegroundColor Yellow
aws s3 rm s3://hdcn-dashboard-frontend/members --recursive 2>$null
aws s3 rm s3://hdcn-dashboard-frontend/products --recursive 2>$null

# Do a fresh deployment to ensure all files are correct
Write-Host "Triggering fresh deployment..." -ForegroundColor Yellow
cd frontend
npm run build
aws s3 sync build/ s3://hdcn-dashboard-frontend --delete
cd ..

Remove-Item "simple-website-config.json" -ErrorAction SilentlyContinue

Write-Host "S3 configuration simplified and cleaned!" -ForegroundColor Green