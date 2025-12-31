# Check SSL Certificate Validation Status
# Usage: .\scripts\utilities\check-ssl-validation.ps1

Write-Host "Checking SSL Certificate Validation Status" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$certificateArn = "arn:aws:acm:us-east-1:344561557829:certificate/803dbdc3-f3bd-4cda-98c3-860a45106533"
$validationRecord = "_f4a612b7a3ff5068a94cdcb4402bc673.testportal.h-dcn.nl"
$validationValue = "_e714de5b836592b25914830ab11ada97.jkddzztszm.acm-validations.aws"

Write-Host "1. Checking Certificate Status..." -ForegroundColor Yellow
$certStatus = aws acm describe-certificate --certificate-arn $certificateArn --region us-east-1 --query "Certificate.Status" --output text
Write-Host "   Certificate Status: $certStatus" -ForegroundColor $(if ($certStatus -eq "ISSUED") { "Green" } else { "Red" })

Write-Host "`n2. Checking DNS Validation Record..." -ForegroundColor Yellow
try {
    $dnsResult = nslookup -type=CNAME $validationRecord 8.8.8.8 2>$null
    if ($dnsResult -match $validationValue.Replace('.', '\.')) {
        Write-Host "   ✅ DNS Validation Record Found" -ForegroundColor Green
    }
    else {
        Write-Host "   ❌ DNS Validation Record Not Found" -ForegroundColor Red
        Write-Host "   Expected: $validationValue" -ForegroundColor Gray
    }
}
catch {
    Write-Host "   ❌ DNS Validation Record Not Found" -ForegroundColor Red
}

Write-Host "`n3. Checking Domain Resolution..." -ForegroundColor Yellow
try {
    $domainResult = nslookup testportal.h-dcn.nl 8.8.8.8 2>$null
    if ($domainResult -match "de1irtdutlxqu.cloudfront.net") {
        Write-Host "   ✅ Domain points to CloudFront" -ForegroundColor Green
    }
    elseif ($domainResult -match "squarespace") {
        Write-Host "   ⚠️  Domain still points to Squarespace" -ForegroundColor Yellow
    }
    else {
        Write-Host "   ❓ Domain points elsewhere" -ForegroundColor Gray
    }
}
catch {
    Write-Host "   ❌ Domain resolution failed" -ForegroundColor Red
}

Write-Host "`n4. Next Steps:" -ForegroundColor Cyan
if ($certStatus -eq "ISSUED") {
    Write-Host "   ✅ SSL Certificate is validated!" -ForegroundColor Green
    Write-Host "   📋 Ready to update CloudFront distribution" -ForegroundColor Yellow
    Write-Host "   📋 Ready to update DNS to point to CloudFront" -ForegroundColor Yellow
}
else {
    Write-Host "   ⏳ Waiting for SSL certificate validation" -ForegroundColor Yellow
    Write-Host "   📋 Ensure DNS validation record is correct in Squarespace" -ForegroundColor Gray
    Write-Host "   📋 DNS propagation can take up to 48 hours" -ForegroundColor Gray
}

Write-Host "`nRequired DNS Records:" -ForegroundColor Cyan
Write-Host "Validation Record:" -ForegroundColor Gray
Write-Host "  Name: $validationRecord" -ForegroundColor White
Write-Host "  Value: $validationValue" -ForegroundColor White
Write-Host "Domain Record (after validation):" -ForegroundColor Gray
Write-Host "  Name: testportal.h-dcn.nl" -ForegroundColor White
Write-Host "  Value: de1irtdutlxqu.cloudfront.net" -ForegroundColor White