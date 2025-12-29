# Clear CloudFront Cache for H-DCN Frontend
# There's only one CloudFront distribution serving both domains

Write-Host "=== Clearing CloudFront Cache ===" -ForegroundColor Green
Write-Host ""

# The single CloudFront distribution ID
$DISTRIBUTION_ID = "E2QTMDOE6H0R87"

Write-Host "CloudFront Distribution: $DISTRIBUTION_ID" -ForegroundColor Yellow
Write-Host "Serves both:" -ForegroundColor Yellow
Write-Host "  - https://de1irtdutlxqu.cloudfront.net (primary)" -ForegroundColor White
Write-Host "  - https://testportal.h-dcn.nl (CNAME)" -ForegroundColor White
Write-Host ""

Write-Host "Clearing cache for all content..." -ForegroundColor Yellow

try {
    $result = aws cloudfront create-invalidation --distribution-id $DISTRIBUTION_ID --paths "/*" | ConvertFrom-Json
    
    Write-Host "✅ Cache invalidation created successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Invalidation Details:" -ForegroundColor Cyan
    Write-Host "  ID: $($result.Invalidation.Id)" -ForegroundColor White
    Write-Host "  Status: $($result.Invalidation.Status)" -ForegroundColor White
    Write-Host "  Created: $($result.Invalidation.CreateTime)" -ForegroundColor White
    Write-Host ""
    Write-Host "Changes will be live in 1-2 minutes on both URLs:" -ForegroundColor Green
    Write-Host "  - https://de1irtdutlxqu.cloudfront.net" -ForegroundColor Cyan
    Write-Host "  - https://testportal.h-dcn.nl" -ForegroundColor Cyan
    
}
catch {
    Write-Host "❌ Failed to clear cache: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== Cache Clear Complete ===" -ForegroundColor Green