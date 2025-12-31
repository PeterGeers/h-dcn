# Fix Product Image URLs Script
# Updates database product image URLs to use the restored simple filenames

# Bypass "more" prompts for long outputs
$env:AWS_PAGER = ""

Write-Host "🔧 Fixing product image URLs..." -ForegroundColor Yellow

# Mapping of product IDs to their correct simple image filenames
$imageMapping = @{
    "G1"    = "G1.jpg"
    "G2"    = "G2.jpg" 
    "G3"    = "G3.jpg"
    "G4"    = "G4.jpg"
    "G8"    = "G8.jpg"
    "G9"    = "G9.jpg"
    "G10"   = "G10.jpg"
    "G12"   = "G12.jpg"
    "G13"   = "G13.jpg"
    "G15"   = "G15.jpg"
    "BS-U"  = "BS-U.jpg"
    "DA-D"  = "DA-D.jpg"
    "DA-H"  = "DA-H.jpg"
    "DB-D"  = "DB-D.jpg"
    "DB-H"  = "DB-H.jpg"
    "RC-H"  = "RC-H.jpg"
    "SD"    = "SD.jpg"
    "SH"    = "SH.jpg"
    "TD"    = "TD.jpg"
    "TD-60" = "TD-60.jpg"
    "TH"    = "TH.jpg"
    "TH-60" = "TH-60.jpg"
    "TH-65" = "TH-65.jpg"
}

$baseUrl = "https://my-hdcn-bucket.s3.eu-west-1.amazonaws.com/product-images"
$apiBase = "https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod"

$updatedCount = 0
$errorCount = 0

foreach ($productId in $imageMapping.Keys) {
    $filename = $imageMapping[$productId]
    $newImageUrl = "$baseUrl/$filename"
    
    Write-Host "Updating product $productId -> $filename" -ForegroundColor Cyan
    
    # Create update payload
    $updateData = @{
        image  = $newImageUrl
        images = @($newImageUrl)
    } | ConvertTo-Json -Depth 3
    
    try {
        # Update the product
        $response = Invoke-RestMethod -Uri "$apiBase/update-product/$productId" -Method PUT -Body $updateData -ContentType "application/json"
        Write-Host "  ✅ Updated $productId" -ForegroundColor Green
        $updatedCount++
    }
    catch {
        Write-Host "  ❌ Failed to update $productId : $($_.Exception.Message)" -ForegroundColor Red
        $errorCount++
    }
    
    Start-Sleep -Milliseconds 200  # Small delay to avoid overwhelming the API
}

Write-Host ""
Write-Host "📊 Update Summary:" -ForegroundColor Yellow
Write-Host "  ✅ Successfully updated: $updatedCount products" -ForegroundColor Green
Write-Host "  ❌ Failed updates: $errorCount products" -ForegroundColor Red
Write-Host ""
Write-Host "🎯 Product images should now display correctly in the webshop!" -ForegroundColor Green