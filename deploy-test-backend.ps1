# Deploy Backend to Test Environment with correct WebAuthn RP ID
# This script deploys the backend with the CloudFront domain as WebAuthn RP ID

param(
    [string]$WebAuthnRPID = "de1irtdutlxqu.cloudfront.net"
)

Write-Host "Deploying backend for test environment..." -ForegroundColor Green
Write-Host "WebAuthn RP ID: $WebAuthnRPID" -ForegroundColor Yellow

# Navigate to backend directory
Set-Location backend

# Deploy with SAM
sam deploy --parameter-overrides "Environment=test WebAuthnRPID=$WebAuthnRPID" --no-confirm-changeset

Write-Host "Backend deployment complete!" -ForegroundColor Green
Write-Host "WebAuthn RP ID is now set to: $WebAuthnRPID" -ForegroundColor Cyan

# Return to root directory
Set-Location ..