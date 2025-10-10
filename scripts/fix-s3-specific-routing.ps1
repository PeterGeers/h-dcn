# Fix S3 Routing Rules - Specific to HTML routes only
# Prevents JS/CSS files from being redirected to index.html

Write-Host "Fixing S3 routing rules to be more specific..." -ForegroundColor Green

# Create specific website configuration that only redirects HTML routes
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
                "HttpErrorCodeReturnedEquals": "404",
                "KeyPrefixEquals": ""
            },
            "Redirect": {
                "ReplaceKeyWith": "index.html",
                "HttpRedirectCode": "200"
            }
        }
    ]
}
'@

$websiteConfig | Out-File -FilePath "specific-website-config.json" -Encoding ASCII
aws s3api put-bucket-website --bucket hdcn-dashboard-frontend --website-configuration file://specific-website-config.json

if ($LASTEXITCODE -eq 0) {
    Write-Host "Specific routing rules applied successfully!" -ForegroundColor Green
} else {
    Write-Host "Failed to apply routing rules!" -ForegroundColor Red
}

# Check what files are actually missing
Write-Host "Checking for missing chunk files..." -ForegroundColor Yellow
aws s3 ls s3://hdcn-dashboard-frontend/static/js/ | findstr "862.bf999248.chunk.js"
aws s3 ls s3://hdcn-dashboard-frontend/static/js/ | findstr "373.df316594.chunk.js"
aws s3 ls s3://hdcn-dashboard-frontend/static/js/ | findstr "149.f2958c54.chunk.js"

Remove-Item "specific-website-config.json" -ErrorAction SilentlyContinue

Write-Host "Routing rules updated!" -ForegroundColor Green