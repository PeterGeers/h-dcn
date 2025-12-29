# Test H-DCN Authentication API
$API_BASE = "https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod"

Write-Host "Testing H-DCN Authentication API..." -ForegroundColor Green

# Test 1: Create Account
Write-Host "`n1. Testing Account Creation..." -ForegroundColor Yellow
$createBody = @{
    email       = "test@example.com"
    given_name  = "Test"
    family_name = "User"
} | ConvertTo-Json

try {
    $createResponse = Invoke-RestMethod -Uri "$API_BASE/auth/signup" -Method POST -Body $createBody -ContentType "application/json"
    Write-Host "✅ Account Creation SUCCESS:" -ForegroundColor Green
    $createResponse | ConvertTo-Json -Depth 3
}
catch {
    Write-Host "❌ Account Creation ERROR:" -ForegroundColor Red
    $_.Exception.Message
    if ($_.Exception.Response) {
        $_.Exception.Response.StatusCode
    }
}

# Test 2: Try Authentication (should fail - no passkey)
Write-Host "`n2. Testing Authentication (should fail)..." -ForegroundColor Yellow
$authBody = @{
    email = "test@example.com"
} | ConvertTo-Json

try {
    $authResponse = Invoke-RestMethod -Uri "$API_BASE/auth/passkey/authenticate/begin" -Method POST -Body $authBody -ContentType "application/json"
    Write-Host "✅ Authentication Response:" -ForegroundColor Green
    $authResponse | ConvertTo-Json -Depth 3
}
catch {
    Write-Host "❌ Authentication ERROR (Expected):" -ForegroundColor Yellow
    $_.Exception.Message
    if ($_.Exception.Response) {
        Write-Host "Status Code:" $_.Exception.Response.StatusCode
    }
}

# Test 3: Try Passkey Registration
Write-Host "`n3. Testing Passkey Registration..." -ForegroundColor Yellow
$passkeyBody = @{
    email = "test@example.com"
} | ConvertTo-Json

try {
    $passkeyResponse = Invoke-RestMethod -Uri "$API_BASE/auth/passkey/register/begin" -Method POST -Body $passkeyBody -ContentType "application/json"
    Write-Host "✅ Passkey Registration SUCCESS:" -ForegroundColor Green
    $passkeyResponse | ConvertTo-Json -Depth 3
}
catch {
    Write-Host "❌ Passkey Registration ERROR:" -ForegroundColor Red
    $_.Exception.Message
    if ($_.Exception.Response) {
        Write-Host "Status Code:" $_.Exception.Response.StatusCode
    }
}

Write-Host "`nTest completed!" -ForegroundColor Green