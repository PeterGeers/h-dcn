# Test S3 File Manager API
$apiUrl = "https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod/s3/files"

# Test data - simple JSON object
$testData = @{
    "test"      = "This is a test file"
    "timestamp" = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    "geslacht"  = @("Man", "Vrouw", "X")
}

# Upload request body
$uploadBody = @{
    "bucketName"   = "my-hdcn-bucket"
    "fileKey"      = "test-parameters.json"
    "fileData"     = $testData
    "contentType"  = "application/json"
    "cacheControl" = "no-cache"
} | ConvertTo-Json -Depth 10

Write-Host "🧪 Testing S3 File Manager API..." -ForegroundColor Yellow
Write-Host "📍 API URL: $apiUrl" -ForegroundColor Cyan

# Test 1: Upload file
Write-Host "`n📤 Test 1: Upload file..." -ForegroundColor Green
try {
    $headers = @{
        "Content-Type"      = "application/json"
        "X-Enhanced-Groups" = "hdcnAdmins"
    }
    
    $response = Invoke-RestMethod -Uri $apiUrl -Method POST -Body $uploadBody -Headers $headers
    Write-Host "✅ Upload successful!" -ForegroundColor Green
    Write-Host "Response: $($response | ConvertTo-Json -Depth 3)" -ForegroundColor White
}
catch {
    Write-Host "❌ Upload failed!" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "Response Body: $responseBody" -ForegroundColor Red
    }
}

# Test 2: List files
Write-Host "`n📋 Test 2: List files..." -ForegroundColor Green
try {
    $listUrl = "$apiUrl" + "?bucketName=my-hdcn-bucket&prefix=test-"
    $headers = @{
        "X-Enhanced-Groups" = "hdcnAdmins"
    }
    
    $response = Invoke-RestMethod -Uri $listUrl -Method GET -Headers $headers
    Write-Host "✅ List successful!" -ForegroundColor Green
    Write-Host "Response: $($response | ConvertTo-Json -Depth 3)" -ForegroundColor White
}
catch {
    Write-Host "❌ List failed!" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "Response Body: $responseBody" -ForegroundColor Red
    }
}

# Test 3: Delete file
Write-Host "`n🗑️ Test 3: Delete file..." -ForegroundColor Green
try {
    $deleteBody = @{
        "bucketName" = "my-hdcn-bucket"
        "fileKey"    = "test-parameters.json"
    } | ConvertTo-Json
    
    $headers = @{
        "Content-Type"      = "application/json"
        "X-Enhanced-Groups" = "hdcnAdmins"
    }
    
    $response = Invoke-RestMethod -Uri $apiUrl -Method DELETE -Body $deleteBody -Headers $headers
    Write-Host "✅ Delete successful!" -ForegroundColor Green
    Write-Host "Response: $($response | ConvertTo-Json -Depth 3)" -ForegroundColor White
}
catch {
    Write-Host "❌ Delete failed!" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "Response Body: $responseBody" -ForegroundColor Red
    }
}

Write-Host "`n🎯 API testing completed!" -ForegroundColor Yellow