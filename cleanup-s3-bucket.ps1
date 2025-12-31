# Clean up my-hdcn-bucket - Remove frontend files that don't belong
$apiUrl = "https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod/s3/files"

Write-Host "🧹 Cleaning up my-hdcn-bucket..." -ForegroundColor Yellow

$headers = @{
    "Content-Type"      = "application/json"
    "X-Enhanced-Groups" = "hdcnAdmins"
}

# Files and folders to remove (frontend build artifacts that don't belong in data bucket)
$itemsToRemove = @(
    "index.html",
    "asset-manifest.json",
    "static/",
    "debug.html",
    "mobile-passkey-debug.html",
    "oauth-handler.html", 
    "passkey-test.html",
    "simple-oauth-test.html"
)

Write-Host "📋 Items to remove:" -ForegroundColor Cyan
$itemsToRemove | ForEach-Object {
    Write-Host "  🗑️ $_" -ForegroundColor Gray
}

Write-Host "`n⚠️ This will permanently delete these files from my-hdcn-bucket" -ForegroundColor Yellow
$confirm = Read-Host "Continue? (y/N)"

if ($confirm -ne "y" -and $confirm -ne "Y") {
    Write-Host "❌ Cleanup cancelled" -ForegroundColor Red
    exit
}

# First, get list of all files to see what we're working with
Write-Host "`n📋 Getting current bucket contents..." -ForegroundColor Green
try {
    $listUrl = "$apiUrl" + "?bucketName=my-hdcn-bucket&recursive=true"
    $response = Invoke-RestMethod -Uri $listUrl -Method GET -Headers @{"X-Enhanced-Groups" = "hdcnAdmins" }
    
    Write-Host "📊 Current bucket contains $($response.counts.files) files" -ForegroundColor Cyan
}
catch {
    Write-Host "❌ Failed to list bucket contents!" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    exit
}

# Delete individual files
$filesToDelete = @("index.html", "asset-manifest.json", "debug.html", "mobile-passkey-debug.html", "oauth-handler.html", "passkey-test.html", "simple-oauth-test.html")

foreach ($file in $filesToDelete) {
    Write-Host "`n🗑️ Deleting file: $file" -ForegroundColor Yellow
    
    try {
        $deleteBody = @{
            "bucketName" = "my-hdcn-bucket"
            "fileKey"    = $file
        } | ConvertTo-Json
        
        $response = Invoke-RestMethod -Uri $apiUrl -Method DELETE -Body $deleteBody -Headers $headers
        Write-Host "✅ Deleted: $file" -ForegroundColor Green
    }
    catch {
        Write-Host "⚠️ Could not delete $file (may not exist): $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

# Delete all files in static/ folder
Write-Host "`n🗑️ Deleting static/ folder contents..." -ForegroundColor Yellow

try {
    # Get all files in static folder
    $listUrl = "$apiUrl" + "?bucketName=my-hdcn-bucket&prefix=static/&recursive=true"
    $staticResponse = Invoke-RestMethod -Uri $listUrl -Method GET -Headers @{"X-Enhanced-Groups" = "hdcnAdmins" }
    
    if ($staticResponse.files.Count -gt 0) {
        Write-Host "📊 Found $($staticResponse.files.Count) files in static/ folder" -ForegroundColor Cyan
        
        foreach ($file in $staticResponse.files) {
            Write-Host "  🗑️ Deleting: $($file.key)" -ForegroundColor Gray
            
            try {
                $deleteBody = @{
                    "bucketName" = "my-hdcn-bucket"
                    "fileKey"    = $file.key
                } | ConvertTo-Json
                
                $response = Invoke-RestMethod -Uri $apiUrl -Method DELETE -Body $deleteBody -Headers $headers
                Write-Host "    ✅ Deleted" -ForegroundColor Green
            }
            catch {
                Write-Host "    ❌ Failed: $($_.Exception.Message)" -ForegroundColor Red
            }
        }
    }
    else {
        Write-Host "📂 No files found in static/ folder" -ForegroundColor Gray
    }
}
catch {
    Write-Host "⚠️ Could not list static/ folder: $($_.Exception.Message)" -ForegroundColor Yellow
}

# Show final bucket contents
Write-Host "`n📋 Final bucket contents..." -ForegroundColor Green
try {
    $listUrl = "$apiUrl" + "?bucketName=my-hdcn-bucket&recursive=false"
    $finalResponse = Invoke-RestMethod -Uri $listUrl -Method GET -Headers @{"X-Enhanced-Groups" = "hdcnAdmins" }
    
    Write-Host "✅ Cleanup completed!" -ForegroundColor Green
    Write-Host "📊 Bucket now contains:" -ForegroundColor Cyan
    Write-Host "  📁 $($finalResponse.counts.folders) folders" -ForegroundColor White
    Write-Host "  📄 $($finalResponse.counts.files) root files" -ForegroundColor White
    
    if ($finalResponse.folders.Count -gt 0) {
        Write-Host "`n📁 Remaining folders:" -ForegroundColor White
        $finalResponse.folders | ForEach-Object {
            Write-Host "  📁 $($_.name)/" -ForegroundColor Yellow
        }
    }
    
    if ($finalResponse.files.Count -gt 0) {
        Write-Host "`n📄 Remaining root files:" -ForegroundColor White
        $finalResponse.files | ForEach-Object {
            $sizeKB = [math]::Round($_.size / 1024, 2)
            Write-Host "  📄 $($_.name) ($sizeKB KB)" -ForegroundColor Gray
        }
    }
}
catch {
    Write-Host "❌ Failed to get final bucket contents!" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n🎯 Bucket cleanup completed!" -ForegroundColor Yellow
Write-Host "💡 The my-hdcn-bucket should now only contain:" -ForegroundColor Blue
Write-Host "   📄 parameters.json (configuration data)" -ForegroundColor Blue
Write-Host "   📁 imagesWebsite/ (logos, favicons)" -ForegroundColor Blue  
Write-Host "   📁 product-images/ (product photos)" -ForegroundColor Blue