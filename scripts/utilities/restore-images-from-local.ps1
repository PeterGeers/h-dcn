# Restore Images from Local Backup
# Uploads recovered images from restoreLost folder to S3 bucket

# Bypass "more" prompts for long outputs
$env:AWS_PAGER = ""

Write-Host "🔄 Restoring images from local backup..." -ForegroundColor Yellow

# Check if restoreLost folder exists
if (-not (Test-Path "restoreLost")) {
    Write-Host "❌ Error: restoreLost folder not found!" -ForegroundColor Red
    Write-Host "   Make sure the restoreLost folder exists in the current directory." -ForegroundColor Yellow
    exit 1
}

# Restore product images
Write-Host "`n📸 Restoring product images..." -ForegroundColor Cyan
$productImagesPath = "restoreLost/images"
$uploadedCount = 0
$errorCount = 0

if (Test-Path $productImagesPath) {
    $imageFiles = Get-ChildItem -Path $productImagesPath -Filter "*.jpg"
    
    Write-Host "Found $($imageFiles.Count) product images to restore" -ForegroundColor White
    
    foreach ($imageFile in $imageFiles) {
        $fileName = $imageFile.Name
        Write-Host "  📤 Uploading $fileName..." -ForegroundColor Gray
        
        try {
            aws s3 cp $imageFile.FullName s3://my-hdcn-bucket/product-images/$fileName
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "    ✅ $fileName uploaded successfully" -ForegroundColor Green
                $uploadedCount++
            }
            else {
                Write-Host "    ❌ Failed to upload $fileName" -ForegroundColor Red
                $errorCount++
            }
        }
        catch {
            Write-Host "    ❌ Error uploading $fileName : $($_.Exception.Message)" -ForegroundColor Red
            $errorCount++
        }
    }
}
else {
    Write-Host "⚠️  Product images folder not found: $productImagesPath" -ForegroundColor Yellow
}

# Restore website images (logo, icons)
Write-Host "`n🖼️  Restoring website images..." -ForegroundColor Cyan
$websiteImages = @("hdcnFavico.png", "info-icon-orange.svg")

foreach ($imageName in $websiteImages) {
    $imagePath = "restoreLost/$imageName"
    
    if (Test-Path $imagePath) {
        Write-Host "  📤 Uploading $imageName..." -ForegroundColor Gray
        
        try {
            aws s3 cp $imagePath s3://my-hdcn-bucket/imagesWebsite/$imageName
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "    ✅ $imageName uploaded successfully" -ForegroundColor Green
                $uploadedCount++
            }
            else {
                Write-Host "    ❌ Failed to upload $imageName" -ForegroundColor Red
                $errorCount++
            }
        }
        catch {
            Write-Host "    ❌ Error uploading $imageName : $($_.Exception.Message)" -ForegroundColor Red
            $errorCount++
        }
    }
    else {
        Write-Host "  ⚠️  $imageName not found in restoreLost folder" -ForegroundColor Yellow
    }
}

# Summary
Write-Host "`n📊 Restoration Summary:" -ForegroundColor Yellow
Write-Host "  ✅ Successfully uploaded: $uploadedCount files" -ForegroundColor Green
Write-Host "  ❌ Failed uploads: $errorCount files" -ForegroundColor Red

if ($uploadedCount -gt 0) {
    Write-Host "`n🎯 Next Steps:" -ForegroundColor Blue
    Write-Host "1. Verify images are displaying in the webshop" -ForegroundColor White
    Write-Host "2. Run fix-product-image-urls.ps1 if needed" -ForegroundColor White
    Write-Host "3. Enable S3 versioning to prevent future data loss" -ForegroundColor White
    
    Write-Host "`n✅ Image restoration completed!" -ForegroundColor Green
}
else {
    Write-Host "`n❌ No images were successfully uploaded. Please check the errors above." -ForegroundColor Red
}

# Verify uploads
Write-Host "`n🔍 Verifying uploads..." -ForegroundColor Cyan
try {
    Write-Host "📂 Product images in S3:" -ForegroundColor White
    aws s3 ls s3://my-hdcn-bucket/product-images/
    
    Write-Host "`n📂 Website images in S3:" -ForegroundColor White
    aws s3 ls s3://my-hdcn-bucket/imagesWebsite/
}
catch {
    Write-Host "⚠️  Could not verify uploads: $($_.Exception.Message)" -ForegroundColor Yellow
}