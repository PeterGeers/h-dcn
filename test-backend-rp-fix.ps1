# Test script to verify the backend RP field fix
# This script tests the passkey registration endpoint to ensure it returns the RP field

$API_BASE = "https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod"
$TEST_EMAIL = "webmaster@h-dcn.nl"

Write-Host "Testing passkey registration endpoint for RP field..." -ForegroundColor Yellow

try {
    # Test registration begin endpoint
    $body = @{
        email = $TEST_EMAIL
    } | ConvertTo-Json

    $headers = @{
        'Content-Type' = 'application/json'
        'Origin' = 'https://testportal.h-dcn.nl'  # Test with testportal origin
    }

    Write-Host "Calling registration begin endpoint..." -ForegroundColor Cyan
    $response = Invoke-RestMethod -Uri "$API_BASE/auth/passkey/register/begin" -Method POST -Body $body -Headers $headers

    Write-Host "Response received:" -ForegroundColor Green
    $response | ConvertTo-Json -Depth 10 | Write-Host

    # Check if RP field is present
    if ($response.rp) {
        Write-Host "✅ SUCCESS: RP field is present" -ForegroundColor Green
        Write-Host "   RP Name: $($response.rp.name)" -ForegroundColor Green
        Write-Host "   RP ID: $($response.rp.id)" -ForegroundColor Green
        
        # Validate RP ID matches expected pattern
        if ($response.rp.id -match "testportal|cloudfront|portal\.h-dcn\.nl") {
            Write-Host "✅ RP ID looks correct for the origin" -ForegroundColor Green
        } else {
            Write-Host "⚠️  WARNING: RP ID might not match origin" -ForegroundColor Yellow
        }
    } else {
        Write-Host "❌ FAILED: RP field is missing from response" -ForegroundColor Red
        exit 1
    }

    # Check other required fields
    $requiredFields = @('challenge', 'user', 'pubKeyCredParams', 'authenticatorSelection', 'timeout', 'attestation')
    foreach ($field in $requiredFields) {
        if ($response.$field) {
            Write-Host "✅ $field is present" -ForegroundColor Green
        } else {
            Write-Host "❌ $field is missing" -ForegroundColor Red
        }
    }

    Write-Host "`n🎉 Backend RP field fix appears to be working!" -ForegroundColor Green

} catch {
    Write-Host "❌ Error testing backend: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Response: $($_.Exception.Response)" -ForegroundColor Red
    exit 1
}