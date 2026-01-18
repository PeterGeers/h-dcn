# Test script for GET /api/members endpoint
# This script tests the regional filtering API in development

$apiUrl = "https://qsdq51d2r3.execute-api.eu-west-1.amazonaws.com/dev/api/members"

Write-Host "Testing Member Regional Filtering API" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Test 1: No authentication (should return 401)
Write-Host "Test 1: No authentication (expecting 401)..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri $apiUrl -Method GET -ErrorAction Stop
    Write-Host "  Status: $($response.StatusCode)" -ForegroundColor Green
    Write-Host "  Body: $($response.Content)" -ForegroundColor Gray
}
catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    $body = $_.ErrorDetails.Message
    Write-Host "  Status: $statusCode" -ForegroundColor $(if ($statusCode -eq 401) { "Green" } else { "Red" })
    Write-Host "  Body: $body" -ForegroundColor Gray
}
Write-Host ""

# Test 2: Invalid JWT token (should return 401)
Write-Host "Test 2: Invalid JWT token (expecting 401)..." -ForegroundColor Yellow
$headers = @{
    "Authorization"     = "Bearer INVALID_TOKEN"
    "X-Enhanced-Groups" = "hdcnLeden"
}
try {
    $response = Invoke-WebRequest -Uri $apiUrl -Method GET -Headers $headers -ErrorAction Stop
    Write-Host "  Status: $($response.StatusCode)" -ForegroundColor Green
    Write-Host "  Body: $($response.Content)" -ForegroundColor Gray
}
catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    $body = $_.ErrorDetails.Message
    Write-Host "  Status: $statusCode" -ForegroundColor $(if ($statusCode -eq 401) { "Green" } else { "Red" })
    Write-Host "  Body: $body" -ForegroundColor Gray
}
Write-Host ""

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Basic connectivity tests complete!" -ForegroundColor Green
Write-Host ""
Write-Host "To test with a real JWT token:" -ForegroundColor Cyan
Write-Host "1. Log in to the H-DCN application" -ForegroundColor White
Write-Host "2. Get your JWT token from browser DevTools (localStorage or sessionStorage)" -ForegroundColor White
Write-Host "3. Run this command with your token:" -ForegroundColor White
Write-Host ""
Write-Host '$headers = @{' -ForegroundColor Gray
Write-Host '    "Authorization" = "Bearer YOUR_ACTUAL_JWT_TOKEN"' -ForegroundColor Gray
Write-Host '    "X-Enhanced-Groups" = "Members_Read,Regio_Utrecht"' -ForegroundColor Gray
Write-Host '}' -ForegroundColor Gray
Write-Host '$response = Invoke-RestMethod -Uri "' + $apiUrl + '" -Method GET -Headers $headers' -ForegroundColor Gray
Write-Host '$response | ConvertTo-Json -Depth 5' -ForegroundColor Gray
Write-Host ""
