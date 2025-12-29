# Clear CloudFront Cache for H-DCN Distributions
# This will invalidate the cache to force fresh content delivery

Write-Host "=== Clearing CloudFront Cache ===" -ForegroundColor Green
Write-Host ""

# CloudFront Distribution IDs
$TEST_DISTRIBUTION_ID = "E2QTMDOE6H0R87"        # testportal.h-dcn.nl
$PROD_DISTRIBUTION_ID = "E1IRTDUTLXQU"          # de1irtdutlxqu.cloudfront.net (adjust if different)

Write-Host "Available distributions:" -ForegroundColor Yellow
Write-Host "1. Test Environment (testportal.h-dcn.nl) - $TEST_DISTRIBUTION_ID" -ForegroundColor White
Write-Host "2. Production Environment (de1irtdutlxqu.cloudfront.net) - $PROD_DISTRIBUTION_ID" -ForegroundColor White
Write-Host "3. Both distributions" -ForegroundColor White
Write-Host ""

$choice = Read-Host "Which cache would you like to clear? (1/2/3)"

switch ($choice) {
    "1" {
        Write-Host "Clearing TEST environment cache..." -ForegroundColor Yellow
        aws cloudfront create-invalidation --distribution-id $TEST_DISTRIBUTION_ID --paths "/*"
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Test environment cache cleared successfully!" -ForegroundColor Green
            Write-Host "Changes will be live at https://testportal.h-dcn.nl in 1-2 minutes" -ForegroundColor Cyan
        }
        else {
            Write-Host "❌ Failed to clear test environment cache" -ForegroundColor Red
        }
    }
    "2" {
        Write-Host "Clearing PRODUCTION environment cache..." -ForegroundColor Yellow
        aws cloudfront create-invalidation --distribution-id $PROD_DISTRIBUTION_ID --paths "/*"
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Production environment cache cleared successfully!" -ForegroundColor Green
            Write-Host "Changes will be live at https://de1irtdutlxqu.cloudfront.net in 1-2 minutes" -ForegroundColor Cyan
        }
        else {
            Write-Host "❌ Failed to clear production environment cache" -ForegroundColor Red
        }
    }
    "3" {
        Write-Host "Clearing BOTH environment caches..." -ForegroundColor Yellow
        
        Write-Host "Clearing test environment..." -ForegroundColor Cyan
        aws cloudfront create-invalidation --distribution-id $TEST_DISTRIBUTION_ID --paths "/*"
        $testResult = $LASTEXITCODE
        
        Write-Host "Clearing production environment..." -ForegroundColor Cyan
        aws cloudfront create-invalidation --distribution-id $PROD_DISTRIBUTION_ID --paths "/*"
        $prodResult = $LASTEXITCODE
        
        if ($testResult -eq 0 -and $prodResult -eq 0) {
            Write-Host "✅ Both environment caches cleared successfully!" -ForegroundColor Green
            Write-Host "Changes will be live in 1-2 minutes on both sites" -ForegroundColor Cyan
        }
        else {
            if ($testResult -ne 0) { Write-Host "❌ Failed to clear test environment cache" -ForegroundColor Red }
            if ($prodResult -ne 0) { Write-Host "❌ Failed to clear production environment cache" -ForegroundColor Red }
        }
    }
    default {
        Write-Host "Invalid choice. Please run the script again and choose 1, 2, or 3." -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "=== Cache Clear Complete ===" -ForegroundColor Green