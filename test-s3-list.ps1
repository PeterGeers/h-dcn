# Test S3 File Manager List Function
$apiUrl = "https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod/s3/files"

Write-Host "🗂️ Testing S3 File Manager List Function..." -ForegroundColor Yellow

$headers = @{
    "X-Enhanced-Groups" = "hdcnAdmins"
}

# Test 1: List all files recursively
Write-Host "`n📋 Test 1: List all files (recursive)..." -ForegroundColor Green
try {
    $listUrl = "$apiUrl" + "?bucketName=my-hdcn-bucket&recursive=true"
    $response = Invoke-RestMethod -Uri $listUrl -Method GET -Headers $headers
    
    Write-Host "✅ Recursive list successful!" -ForegroundColor Green
    Write-Host "📊 Found $($response.counts.files) files and $($response.counts.folders) folders" -ForegroundColor Cyan
    
    # Show first few files
    if ($response.files.Count -gt 0) {
        Write-Host "`n📄 First 5 files:" -ForegroundColor White
        $response.files | Select-Object -First 5 | ForEach-Object {
            $sizeKB = [math]::Round($_.size / 1024, 2)
            Write-Host "  📄 $($_.key) ($sizeKB KB)" -ForegroundColor Gray
        }
    }
}
catch {
    Write-Host "❌ Recursive list failed!" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 2: List files by folder (non-recursive)
Write-Host "`n📁 Test 2: List root level (non-recursive)..." -ForegroundColor Green
try {
    $listUrl = "$apiUrl" + "?bucketName=my-hdcn-bucket&recursive=false"
    $response = Invoke-RestMethod -Uri $listUrl -Method GET -Headers $headers
    
    Write-Host "✅ Non-recursive list successful!" -ForegroundColor Green
    Write-Host "📊 Found $($response.counts.files) files and $($response.counts.folders) folders at root level" -ForegroundColor Cyan
    
    # Show folders
    if ($response.folders.Count -gt 0) {
        Write-Host "`n📁 Folders:" -ForegroundColor White
        $response.folders | ForEach-Object {
            Write-Host "  📁 $($_.name)/" -ForegroundColor Yellow
        }
    }
    
    # Show root files
    if ($response.files.Count -gt 0) {
        Write-Host "`n📄 Root files:" -ForegroundColor White
        $response.files | ForEach-Object {
            $sizeKB = [math]::Round($_.size / 1024, 2)
            Write-Host "  📄 $($_.name) ($sizeKB KB)" -ForegroundColor Gray
        }
    }
}
catch {
    Write-Host "❌ Non-recursive list failed!" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: List specific folder
Write-Host "`n🖼️ Test 3: List product-images folder..." -ForegroundColor Green
try {
    $listUrl = "$apiUrl" + "?bucketName=my-hdcn-bucket&prefix=product-images/&recursive=true"
    $response = Invoke-RestMethod -Uri $listUrl -Method GET -Headers $headers
    
    Write-Host "✅ Product images list successful!" -ForegroundColor Green
    Write-Host "📊 Found $($response.counts.files) image files" -ForegroundColor Cyan
    
    # Show image files
    if ($response.files.Count -gt 0) {
        Write-Host "`n🖼️ Image files:" -ForegroundColor White
        $response.files | Select-Object -First 10 | ForEach-Object {
            $sizeKB = [math]::Round($_.size / 1024, 2)
            Write-Host "  🖼️ $($_.name) ($sizeKB KB)" -ForegroundColor Gray
        }
        
        if ($response.files.Count -gt 10) {
            Write-Host "  ... and $($response.files.Count - 10) more files" -ForegroundColor Gray
        }
    }
}
catch {
    Write-Host "❌ Product images list failed!" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 4: Search for specific file type
Write-Host "`n🔍 Test 4: Look for JSON files..." -ForegroundColor Green
try {
    $listUrl = "$apiUrl" + "?bucketName=my-hdcn-bucket&recursive=true"
    $response = Invoke-RestMethod -Uri $listUrl -Method GET -Headers $headers
    
    $jsonFiles = $response.files | Where-Object { $_.extension -eq "json" }
    
    Write-Host "✅ JSON file search successful!" -ForegroundColor Green
    Write-Host "📊 Found $($jsonFiles.Count) JSON files" -ForegroundColor Cyan
    
    if ($jsonFiles.Count -gt 0) {
        Write-Host "`n📄 JSON files:" -ForegroundColor White
        $jsonFiles | ForEach-Object {
            $sizeKB = [math]::Round($_.size / 1024, 2)
            Write-Host "  📄 $($_.key) ($sizeKB KB)" -ForegroundColor Gray
        }
    }
}
catch {
    Write-Host "❌ JSON file search failed!" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n🎯 List function testing completed!" -ForegroundColor Yellow