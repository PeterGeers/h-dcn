#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Setup GitGuardian security for any project
.DESCRIPTION
    Installs ggshield, configures GitGuardian, and sets up pre-commit hooks
    Can be used across multiple projects
.EXAMPLE
    .\setup-security.ps1
#>

param(
    [string]$ProjectType = "general",
    [switch]$SkipInstall
)

Write-Host "🔒 Setting up GitGuardian Security" -ForegroundColor Green

# Install ggshield if not skipped
if (-not $SkipInstall) {
    Write-Host "📦 Installing ggshield..." -ForegroundColor Yellow
    pip install ggshield
    
    Write-Host "🔑 Authenticating with GitGuardian..." -ForegroundColor Yellow
    ggshield auth login
}

# Create .gitguardian.yaml based on project type
$config = @"
# GitGuardian configuration
version: 2

paths_ignore:
  - "node_modules/**"
  - "build/**"
  - "dist/**"
  - ".aws-sam/**"
  - ".venv/**"
  - "**/*.log"
  - ".git/**"
"@

# Add project-specific exclusions
switch ($ProjectType) {
    "aws-serverless" {
        $config += @"

  - "backend/.aws-sam/**"
  - "frontend/build/**"
  - "frontend/package-lock.json"
"@
    }
    "react" {
        $config += @"

  - "public/**"
  - "package-lock.json"
  - "yarn.lock"
"@
    }
    "python" {
        $config += @"

  - "__pycache__/**"
  - "*.pyc"
  - ".pytest_cache/**"
"@
    }
}

$config += @"

secret:
  show_secrets: false
  ignore_known_secrets: true

exit_zero: false
"@

# Write configuration file
$config | Out-File -FilePath ".gitguardian.yaml" -Encoding UTF8
Write-Host "✅ Created .gitguardian.yaml" -ForegroundColor Green

# Install pre-commit hook
Write-Host "🪝 Installing pre-commit hook..." -ForegroundColor Yellow
ggshield install --mode local

# Test the setup
Write-Host "🧪 Testing configuration..." -ForegroundColor Yellow
$scanResult = ggshield secret scan repo . 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Security setup complete!" -ForegroundColor Green
    Write-Host "🛡️  Your project is now protected against secret leaks" -ForegroundColor Cyan
}
else {
    Write-Host "⚠️  Setup completed but scan found issues:" -ForegroundColor Yellow
    Write-Host $scanResult
}

Write-Host "`n📋 Next steps:" -ForegroundColor Blue
Write-Host "  • Share this script with your team"
Write-Host "  • Run 'ggshield secret scan repo .' to scan existing code"
Write-Host "  • Commits will now be automatically scanned"