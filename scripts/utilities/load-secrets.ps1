# Load secrets from .secrets file into environment variables
# Usage: . .\scripts\utilities\load-secrets.ps1

$secretsFile = ".secrets"

if (-not (Test-Path $secretsFile)) {
    Write-Error "Secrets file not found: $secretsFile"
    Write-Host "Please copy .secrets.example to .secrets and fill in your values"
    exit 1
}

Write-Host "Loading secrets from $secretsFile..." -ForegroundColor Green

Get-Content $secretsFile | ForEach-Object {
    if ($_ -match '^([^#][^=]+)=(.+)$') {
        $name = $matches[1].Trim()
        $value = $matches[2].Trim()
        
        # Remove quotes if present
        $value = $value -replace '^"(.*)"$', '$1'
        
        # Set environment variable
        [Environment]::SetEnvironmentVariable($name, $value, "Process")
        Write-Host "  $name = $value" -ForegroundColor Gray
    }
}

Write-Host "Secrets loaded successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "You can now use variables like:"
Write-Host "  `$env:GOOGLE_CLIENT_ID"
Write-Host "  `$env:GOOGLE_CLIENT_SECRET"
Write-Host "  `$env:COGNITO_USER_POOL_ID"