# Test Current Frontend Implementation
# This will help us understand what's happening with the current setup

Write-Host "=== Frontend Implementation Analysis ===" -ForegroundColor Green
Write-Host ""

Write-Host "Current Issues Identified:" -ForegroundColor Yellow
Write-Host "1. OAuth Flow Mismatch:" -ForegroundColor Red
Write-Host "   - Frontend expects: implicit flow (tokens in URL #fragment)" -ForegroundColor White
Write-Host "   - Cognito configured: authorization_code flow (code in URL ?query)" -ForegroundColor White
Write-Host ""
Write-Host "2. Missing Route:" -ForegroundColor Red
Write-Host "   - OAuthCallback component exists but not routed" -ForegroundColor White
Write-Host "   - /auth/callback route missing in App.tsx" -ForegroundColor White
Write-Host ""
Write-Host "3. Configuration Mismatch:" -ForegroundColor Red
Write-Host "   - GoogleSignInButton uses response_type='token'" -ForegroundColor White
Write-Host "   - But Cognito is configured for response_type='code'" -ForegroundColor White
Write-Host ""

Write-Host "Testing Current Frontend Behavior..." -ForegroundColor Yellow
Write-Host ""

# Test 1: Check if /auth/callback route exists
Write-Host "Test 1: Testing /auth/callback route..." -ForegroundColor Cyan
$callbackTestUrl = "https://de1irtdutlxqu.cloudfront.net/auth/callback?test=1"
Write-Host "Opening: $callbackTestUrl" -ForegroundColor White
Write-Host "Expected: Should show 404 or default page (route doesn't exist)" -ForegroundColor White
Write-Host ""

Start-Process $callbackTestUrl

Write-Host "Press any key to continue to Test 2..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# Test 2: Test with implicit flow (what frontend expects)
Write-Host ""
Write-Host "Test 2: Testing with implicit flow (what frontend expects)..." -ForegroundColor Cyan

# First, let's temporarily change Cognito back to implicit flow for testing
Write-Host "Temporarily changing Cognito to implicit flow for testing..." -ForegroundColor Yellow

try {
    $result = aws cognito-idp update-user-pool-client --user-pool-id eu-west-1_OAT3oPCIm --client-id 6unl8mg5tbv5r727vc39d847vn --allowed-o-auth-flows "implicit" --allowed-o-auth-scopes "openid" "email" "profile" --callback-urls "http://localhost:3000/auth/callback" "https://de1irtdutlxqu.cloudfront.net/auth/callback" "https://testportal.h-dcn.nl/auth/callback" --logout-urls "http://localhost:3000/auth/logout" "https://de1irtdutlxqu.cloudfront.net/auth/logout" "https://testportal.h-dcn.nl/auth/logout" --allowed-o-auth-flows-user-pool-client --supported-identity-providers "COGNITO" "Google" --region eu-west-1 | ConvertFrom-Json
    
    Write-Host "✅ Temporarily changed to implicit flow" -ForegroundColor Green
    
    # Now test the implicit flow URL
    $implicitTestUrl = "https://h-dcn-auth-344561557829.auth.eu-west-1.amazoncognito.com/oauth2/authorize?response_type=token&client_id=6unl8mg5tbv5r727vc39d847vn&redirect_uri=https://de1irtdutlxqu.cloudfront.net/auth/callback&scope=openid+email+profile&identity_provider=Google"
    
    Write-Host ""
    Write-Host "Testing implicit flow URL:" -ForegroundColor Cyan
    Write-Host $implicitTestUrl -ForegroundColor White
    Write-Host ""
    Write-Host "Expected: Should redirect to /auth/callback with tokens in URL fragment (#)" -ForegroundColor White
    
    Start-Process $implicitTestUrl
    
    Write-Host ""
    Write-Host "Instructions:" -ForegroundColor Yellow
    Write-Host "1. Complete Google login" -ForegroundColor White
    Write-Host "2. Check if you get redirected to /auth/callback" -ForegroundColor White
    Write-Host "3. Check if URL contains #access_token= (not ?code=)" -ForegroundColor White
    Write-Host "4. Press F12 and check console for OAuthCallback component logs" -ForegroundColor White
    Write-Host ""
    
    Write-Host "Press any key when you've tested the implicit flow..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    
    # Change back to authorization_code flow
    Write-Host ""
    Write-Host "Changing back to authorization_code flow..." -ForegroundColor Yellow
    
    $result = aws cognito-idp update-user-pool-client --user-pool-id eu-west-1_OAT3oPCIm --client-id 6unl8mg5tbv5r727vc39d847vn --allowed-o-auth-flows "code" --allowed-o-auth-scopes "openid" "email" "profile" --callback-urls "http://localhost:3000/auth/callback" "https://de1irtdutlxqu.cloudfront.net/auth/callback" "https://testportal.h-dcn.nl/auth/callback" --logout-urls "http://localhost:3000/auth/logout" "https://de1irtdutlxqu.cloudfront.net/auth/logout" "https://testportal.h-dcn.nl/auth/logout" --allowed-o-auth-flows-user-pool-client --supported-identity-providers "COGNITO" "Google" --region eu-west-1 | ConvertFrom-Json
    
    Write-Host "✅ Changed back to authorization_code flow" -ForegroundColor Green
    
}
catch {
    Write-Host "❌ Error updating Cognito configuration: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== Test Results Summary ===" -ForegroundColor Green
Write-Host ""
Write-Host "What we need to fix:" -ForegroundColor Yellow
Write-Host "1. Add /auth/callback route to App.tsx" -ForegroundColor White
Write-Host "2. Update OAuthCallback component for authorization_code flow" -ForegroundColor White
Write-Host "3. Update GoogleSignInButton to use response_type='code'" -ForegroundColor White
Write-Host ""
Write-Host "Or alternatively:" -ForegroundColor Yellow
Write-Host "1. Keep implicit flow in Cognito (less secure)" -ForegroundColor White
Write-Host "2. Just add the missing route" -ForegroundColor White