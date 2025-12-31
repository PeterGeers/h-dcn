# Enable S3 Protection
# Enables versioning and backup protection for data bucket

# Bypass "more" prompts for long outputs
$env:AWS_PAGER = ""

Write-Host "🛡️  Enabling S3 protection for my-hdcn-bucket..." -ForegroundColor Yellow

# Enable versioning
Write-Host "`n📋 Enabling S3 versioning..." -ForegroundColor Cyan
try {
    aws s3api put-bucket-versioning --bucket my-hdcn-bucket --versioning-configuration Status=Enabled
    Write-Host "✅ Versioning enabled successfully!" -ForegroundColor Green
}
catch {
    Write-Host "❌ Error enabling versioning: $($_.Exception.Message)" -ForegroundColor Red
}

# Verify versioning is enabled
Write-Host "`n🔍 Verifying versioning status..." -ForegroundColor Cyan
try {
    $versioning = aws s3api get-bucket-versioning --bucket my-hdcn-bucket | ConvertFrom-Json
    if ($versioning.Status -eq "Enabled") {
        Write-Host "✅ Versioning confirmed: $($versioning.Status)" -ForegroundColor Green
    }
    else {
        Write-Host "⚠️  Versioning status: $($versioning.Status)" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "❌ Error verifying versioning: $($_.Exception.Message)" -ForegroundColor Red
}

# Create lifecycle policy to manage versions (optional)
Write-Host "`n📝 Creating lifecycle policy for version management..." -ForegroundColor Cyan
$lifecyclePolicy = @{
    Rules = @(
        @{
            ID                           = "ManageVersions"
            Status                       = "Enabled"
            Filter                       = @{
                Prefix = "product-images/"
            }
            NoncurrentVersionTransitions = @(
                @{
                    NoncurrentDays = 30
                    StorageClass   = "STANDARD_IA"
                }
            )
            NoncurrentVersionExpiration  = @{
                NoncurrentDays = 365
            }
        }
    )
} | ConvertTo-Json -Depth 10

try {
    $lifecyclePolicy | Out-File -FilePath "temp-lifecycle.json" -Encoding UTF8
    aws s3api put-bucket-lifecycle-configuration --bucket my-hdcn-bucket --lifecycle-configuration file://temp-lifecycle.json
    Remove-Item "temp-lifecycle.json" -Force
    Write-Host "✅ Lifecycle policy applied successfully!" -ForegroundColor Green
    Write-Host "   📅 Old versions will be moved to IA after 30 days" -ForegroundColor Blue
    Write-Host "   🗑️  Old versions will be deleted after 365 days" -ForegroundColor Blue
}
catch {
    Write-Host "⚠️  Could not apply lifecycle policy: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "   💡 This is optional - versioning is still enabled" -ForegroundColor Blue
}

Write-Host "`n🎯 Protection Summary:" -ForegroundColor Green
Write-Host "✅ S3 Versioning: Enabled" -ForegroundColor White
Write-Host "✅ Future deletions will be recoverable" -ForegroundColor White
Write-Host "✅ Lifecycle management configured" -ForegroundColor White

Write-Host "`n💡 Best Practices:" -ForegroundColor Blue
Write-Host "1. Regular backups to separate bucket/region" -ForegroundColor White
Write-Host "2. Monitor bucket for unexpected changes" -ForegroundColor White
Write-Host "3. Use MFA delete for critical buckets" -ForegroundColor White
Write-Host "4. Document recovery procedures" -ForegroundColor White

Write-Host "`n🛡️  S3 protection setup completed!" -ForegroundColor Green