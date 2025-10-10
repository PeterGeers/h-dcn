# Fix S3 Content Types
aws s3 cp s3://hdcn-dashboard-frontend/index.html s3://hdcn-dashboard-frontend/index.html --metadata-directive REPLACE --content-type "text/html" --cache-control "no-cache, no-store, must-revalidate"
Write-Host "Content-type fixed for index.html" -ForegroundColor Green