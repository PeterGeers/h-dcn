# Load configuration and secrets into environment variables
# Reads frontend/.env first (shared config), then overlays .secrets (actual secrets)
# Usage: . .\scripts\utilities\load-secrets.ps1

function Load-EnvFile($filePath, $label) {
    if (-not (Test-Path $filePath)) {
        return $false
    }

    Write-Host "Loading $label from $filePath..." -ForegroundColor Green

    Get-Content $filePath | ForEach-Object {
        if ($_ -match '^([^#][^=]+)=(.+)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()

            # Remove quotes if present
            $value = $value -replace '^"(.*)"$', '$1'

            # Set environment variable
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
            Write-Host "  $name = $($value.Substring(0, [Math]::Min(40, $value.Length)))..." -ForegroundColor Gray
        }
    }

    return $true
}

# 1. Load shared config from frontend/.env (Cognito pool ID, region, API URL, etc.)
$frontendEnv = "frontend/.env"
if (-not (Load-EnvFile $frontendEnv "shared config")) {
    Write-Warning "frontend/.env not found - shared config (pool IDs, region) will not be loaded"
}

# 2. Overlay actual secrets from .secrets (Google OAuth secret, Cognito client secret, etc.)
$secretsFile = ".secrets"
if (-not (Load-EnvFile $secretsFile "secrets")) {
    Write-Error "Secrets file not found: $secretsFile"
    Write-Host "Please copy .secrets.example to .secrets and fill in your values"
    exit 1
}

# 3. Map REACT_APP_ prefixed vars to non-prefixed equivalents for backend scripts
if ($env:REACT_APP_USER_POOL_ID -and -not $env:COGNITO_USER_POOL_ID) {
    [Environment]::SetEnvironmentVariable("COGNITO_USER_POOL_ID", $env:REACT_APP_USER_POOL_ID, "Process")
}
if ($env:REACT_APP_USER_POOL_WEB_CLIENT_ID -and -not $env:COGNITO_CLIENT_ID) {
    [Environment]::SetEnvironmentVariable("COGNITO_CLIENT_ID", $env:REACT_APP_USER_POOL_WEB_CLIENT_ID, "Process")
}
if ($env:REACT_APP_AWS_REGION -and -not $env:AWS_REGION) {
    [Environment]::SetEnvironmentVariable("AWS_REGION", $env:REACT_APP_AWS_REGION, "Process")
}

Write-Host ""
Write-Host "Configuration loaded successfully!" -ForegroundColor Green
Write-Host "  Source of truth for Cognito config: frontend/.env"
Write-Host "  Secrets overlay: .secrets"
Write-Host ""
Write-Host "Available variables:"
Write-Host "  `$env:COGNITO_USER_POOL_ID  = $env:COGNITO_USER_POOL_ID"
Write-Host "  `$env:COGNITO_CLIENT_ID     = $env:COGNITO_CLIENT_ID"
Write-Host "  `$env:AWS_REGION            = $env:AWS_REGION"
Write-Host "  `$env:GOOGLE_CLIENT_ID      (from .secrets)"
Write-Host "  `$env:GOOGLE_CLIENT_SECRET  (from .secrets)"