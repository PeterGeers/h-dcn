# Test script to check RP ID consistency between registration and authentication
$API_BASE = "https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod"
$TEST_EMAIL = "webmaster@h-dcn.nl"

Write-Host "Testing RP ID consistency..." -ForegroundColor Yellow

# Test with CloudFront origin (like your mobile device)
$headers = @{
    'Content-Type' = 'application/json'
    'Origin'       = 'https://d1irtdutlxqu.cloudfront.net'
}

Write-Host "`nTesting REGISTRATION with CloudFront origin..." -ForegroundColor Cyan
try {
    $regBody = @{ email = $TEST_EMAIL } | ConvertTo-Json
    $regResponse = Invoke-RestMethod -Uri "$API_BASE/auth/passkey/register/begin" -Method POST -Body $regBody -Headers $headers
    
    Write-Host "Registration RP ID: $($regResponse.rp.id)" -ForegroundColor Green
    Write-Host "Registration RP Name: $($regResponse.rp.name)" -ForegroundColor Green
}
catch {
    Write-Host "Registration test failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`nTesting AUTHENTICATION with CloudFront origin..." -ForegroundColor Cyan
try {
    $authBody = @{ 
        email       = $TEST_EMAIL
        crossDevice = $false 
    } | ConvertTo-Json
    $authResponse = Invoke-RestMethod -Uri "$API_BASE/auth/passkey/authenticate/begin" -Method POST -Body $authBody -Headers $headers
    
    Write-Host "Authentication challenge received" -ForegroundColor Green
    Write-Host "Authentication options: $($authResponse | ConvertTo-Json -Depth 3)" -ForegroundColor Green
}
catch {
    Write-Host "Authentication test failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n" -ForegroundColor Yellow
Write-Host "DIAGNOSIS:" -ForegroundColor Yellow
Write-Host "- Your mobile device is accessing via: d1irtdutlxqu.cloudfront.net" -ForegroundColor White
Write-Host "- The passkey was registered with RP ID from the registration call above" -ForegroundColor White
Write-Host "- For authentication to work, the client must use the SAME RP ID" -ForegroundColor White
Write-Host "- The error suggests the RP IDs don't match" -ForegroundColor White

Write-Host "`nSOLUTION:" -ForegroundColor Yellow
Write-Host "- The mobile debug tool should use the server-provided RP ID" -ForegroundColor White
Write-Host "- OR ensure consistent RP ID between registration and authentication" -ForegroundColor White