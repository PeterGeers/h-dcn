# S3 Recovery Options Check
# Checks for versioning, delete markers, and recovery possibilities

# Bypass "more" prompts for long outputs
$env:AWS_PAGER = ""

Write-Host "🔍 Checking S3 recovery options for my-hdcn-bucket..." -ForegroundColor Yellow

# Check bucket versioning status
Write-Host "`n📋 Checking bucket versioning..." -ForegroundColor Cyan
try {
    $versioning = aws s3api get-bucket-versioning --bucket my-hdcn-bucket | ConvertFrom-Json
    if ($versioning.Status) {
        Write-Host "✅ Versioning Status: $($versioning.Status)" -ForegroundColor Green
    }
    else {
        Write-Host "⚠️  Versioning: Not enabled" -ForegroundColor Yellow
        Write-Host "   💡 Recommendation: Enable versioning for future protection" -ForegroundColor Blue
    }
}
catch {
    Write-Host "❌ Error checking versioning: $($_.Exception.Message)" -ForegroundColor Red
}

# Check for any object versions in product-images
Write-Host "`n🔍 Checking for object versions in product-images/..." -ForegroundColor Cyan
try {
    $versions = aws s3api list-object-versions --bucket my-hdcn-bucket --prefix product-images/ | ConvertFrom-Json
    
    if ($versions.Versions -and $versions.Versions.Count -gt 0) {
        Write-Host "✅ Found $($versions.Versions.Count) object versions!" -ForegroundColor Green
        foreach ($version in $versions.Versions) {
            Write-Host "  📄 $($version.Key) - $($version.LastModified)" -ForegroundColor White
        }
    }
    else {
        Write-Host "❌ No object versions found" -ForegroundColor Red
    }
    
    if ($versions.DeleteMarkers -and $versions.DeleteMarkers.Count -gt 0) {
        Write-Host "🗑️  Found $($versions.DeleteMarkers.Count) delete markers!" -ForegroundColor Yellow
        foreach ($marker in $versions.DeleteMarkers) {
            Write-Host "  🗑️  $($marker.Key) - deleted on $($marker.LastModified)" -ForegroundColor Yellow
        }
    }
}
catch {
    Write-Host "❌ Error checking versions: $($_.Exception.Message)" -ForegroundColor Red
}

# Check current bucket contents
Write-Host "`n📂 Current bucket contents..." -ForegroundColor Cyan
try {
    $objects = aws s3 ls s3://my-hdcn-bucket/ --recursive
    if ($objects) {
        Write-Host "📁 Current files in bucket:" -ForegroundColor White
        Write-Host $objects
    }
    else {
        Write-Host "📭 Bucket appears to be empty or only contains folders" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "❌ Error listing bucket contents: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n💡 Recovery Recommendations:" -ForegroundColor Blue
Write-Host "1. If versioning was enabled before deletion, versions might be recoverable" -ForegroundColor White
Write-Host "2. Check AWS CloudTrail logs for deletion events" -ForegroundColor White
Write-Host "3. Contact AWS support if this is a critical data loss" -ForegroundColor White
Write-Host "4. Enable versioning immediately to prevent future data loss" -ForegroundColor White
Write-Host "5. Implement regular backups to separate location" -ForegroundColor White

Write-Host "`n🎯 Next Steps:" -ForegroundColor Green
Write-Host "1. Enable S3 versioning: aws s3api put-bucket-versioning --bucket my-hdcn-bucket --versioning-configuration Status=Enabled" -ForegroundColor Gray
Write-Host "2. Set up lifecycle policies for version management" -ForegroundColor Gray
Write-Host "3. Implement cross-region backup strategy" -ForegroundColor Gray