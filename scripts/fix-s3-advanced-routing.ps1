# Advanced S3 React Router Fix
# Uses routing rules to handle SPA routing properly

Write-Host "Applying advanced S3 routing rules for React SPA..." -ForegroundColor Green

# Create advanced website configuration with routing rules
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

$websiteConfig | Out-File -FilePath "advanced-website-config.json" -Encoding ASCII
aws s3api put-bucket-website --bucket hdcn-dashboard-frontend --website-configuration file://advanced-website-config.json

if ($LASTEXITCODE -eq 0) {
    Write-Host "Advanced routing rules applied successfully!" -ForegroundColor Green
} else {
    Write-Host "Failed to apply routing rules!" -ForegroundColor Red
}

# Verify the configuration
Write-Host "Verifying configuration..." -ForegroundColor Yellow
aws s3api get-bucket-website --bucket hdcn-dashboard-frontend

Remove-Item "advanced-website-config.json" -ErrorAction SilentlyContinue

Write-Host "Advanced S3 routing configuration complete!" -ForegroundColor Green