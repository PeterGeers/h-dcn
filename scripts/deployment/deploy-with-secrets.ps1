# Deploy backend with secrets from .secrets file
# Usage: .\scripts\deployment\deploy-with-secrets.ps1

Write-Host "H-DCN Backend Deployment with Secrets" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan

# Load secrets
. .\scripts\utilities\load-secrets.ps1

# Verify required secrets are loaded
$requiredSecrets = @("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET")
$missingSecrets = @()

foreach ($secret in $requiredSecrets) {
    if (-not [Environment]::GetEnvironmentVariable($secret, "Process")) {
        $missingSecrets += $secret
    }
}

if ($missingSecrets.Count -gt 0) {
    Write-Error "Missing required secrets: $($missingSecrets -join ', ')"
    Write-Host "Please check your .secrets file"
    exit 1
}

# Deploy with secrets
Write-Host "Deploying backend with Google OAuth configuration..." -ForegroundColor Yellow

Set-Location backend

sam deploy --parameter-overrides `
    GoogleClientId="$env:GOOGLE_CLIENT_ID" `
    GoogleClientSecret="$env:GOOGLE_CLIENT_SECRET" `
    --no-confirm-changeset

if ($LASTEXITCODE -eq 0) {
    Write-Host "Deployment successful!" -ForegroundColor Green
}
else {
    Write-Error "Deployment failed!"
    exit 1
}

Set-Location ..