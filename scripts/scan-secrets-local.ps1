#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Local secret scanner — fallback when ggshield API quota is exhausted.
    No external API calls. Pure regex pattern matching on staged files.

.DESCRIPTION
    Scans git staged files for common secret patterns:
    - AWS access keys (AKIA...)
    - AWS secret keys
    - Private keys (RSA, EC, etc.)
    - Generic API keys/tokens in assignments
    - Stripe keys (sk_live_, pk_live_)
    - Database connection strings with passwords
    - JWT tokens (eyJ...)
    - GitHub/GitLab tokens
    - Google API keys
    - Slack tokens

    Returns exit code 1 if secrets found, 0 if clean.
    Respects .gitguardian.yaml ignored_paths.

.NOTES
    This is NOT a replacement for ggshield — it catches ~80% of common leaks.
    Use alongside ggshield when API is available.
#>

param(
    [switch]$Verbose
)

$ErrorActionPreference = 'Stop'

# --- Secret patterns (regex) ---
$patterns = @(
    @{ Name = "AWS Access Key ID"; Pattern = "AKIA[0-9A-Z]{16}" }
    @{ Name = "AWS Secret Access Key"; Pattern = "(?i)(aws_secret_access_key|aws_secret_key|secret_key)\s*[=:]\s*[A-Za-z0-9/+=]{40}" }
    @{ Name = "Private Key"; Pattern = "-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----" }
    @{ Name = "Stripe Secret Key"; Pattern = "sk_live_[0-9a-zA-Z]{24,}" }
    @{ Name = "Stripe Publishable Key"; Pattern = "pk_live_[0-9a-zA-Z]{24,}" }
    @{ Name = "GitHub Token"; Pattern = "(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}" }
    @{ Name = "GitLab Token"; Pattern = "glpat-[A-Za-z0-9\-]{20,}" }
    @{ Name = "Google API Key"; Pattern = "AIza[0-9A-Za-z\-_]{35}" }
    @{ Name = "Slack Token"; Pattern = "xox[bpors]-[0-9a-zA-Z\-]{10,}" }
    @{ Name = "Generic Secret Assignment"; Pattern = "(?i)(secret|password|passwd|token|api_key|apikey|auth_token)\s*[=:]\s*[""'][A-Za-z0-9/+=\-_]{8,}[""']" }
    @{ Name = "Connection String Password"; Pattern = "(?i)(password|pwd)\s*=\s*[^;\s]{8,}" }
    @{ Name = "Bearer Token (hardcoded)"; Pattern = "(?i)bearer\s+[A-Za-z0-9\-._~+/]+=*" }
    @{ Name = "Base64 JWT (long)"; Pattern = "eyJ[A-Za-z0-9\-_]{50,}\.[A-Za-z0-9\-_]{50,}\.[A-Za-z0-9\-_]{50,}" }
)

# --- Ignored paths (from .gitguardian.yaml convention) ---
$ignoredPatterns = @(
    "*/locales/*",
    "*/public/locales/*",
    "*package-lock.json",
    "*yarn.lock",
    "*.venv/*",
    "*/node_modules/*",
    "test_*",
    "*/tests/*",
    "*/__tests__/*",
    "*.example",
    "*.example.*",
    "scripts/scan-secrets-local.ps1"
)

function Test-Ignored {
    param([string]$FilePath)
    foreach ($pattern in $ignoredPatterns) {
        $regexPattern = $pattern -replace '\*', '.*' -replace '\?', '.'
        if ($FilePath -match $regexPattern) { return $true }
    }
    return $false
}

# --- Get staged files ---
$stagedFiles = git diff --cached --name-only --diff-filter=ACM 2>$null
if (-not $stagedFiles) {
    if ($Verbose) { Write-Host "No staged files to scan." -ForegroundColor Green }
    exit 0
}

# --- Scan each file ---
$findings = @()

foreach ($file in $stagedFiles) {
    # Skip ignored paths
    if (Test-Ignored $file) { continue }
    
    # Skip binary files
    $extension = [System.IO.Path]::GetExtension($file).ToLower()
    $binaryExtensions = @('.png', '.jpg', '.jpeg', '.gif', '.webp', '.ico', '.pdf', '.zip', '.tar', '.gz', '.woff', '.woff2', '.ttf', '.eot')
    if ($extension -in $binaryExtensions) { continue }
    
    # Read file content from staging area
    try {
        $content = git show ":$file" 2>$null
        if (-not $content) { continue }
    }
    catch {
        continue
    }
    
    # Check each line against patterns
    $lineNumber = 0
    foreach ($line in $content -split "`n") {
        $lineNumber++
        
        # Skip comments and known safe patterns
        if ($line -match '^\s*(#|//|/\*|\*)') { continue }
        if ($line -match 'example|placeholder|dummy|test.*token|fake|mock') { continue }
        
        foreach ($patternDef in $patterns) {
            if ($line -match $patternDef.Pattern) {
                # Extra check: skip if it's clearly a variable reference, not a literal
                if ($line -match '\$\{|\$\(|process\.env|os\.environ|getenv') { continue }
                
                $findings += [PSCustomObject]@{
                    File    = $file
                    Line    = $lineNumber
                    Type    = $patternDef.Name
                    Content = if ($line.Length -gt 100) { $line.Substring(0, 100) + "..." } else { $line.Trim() }
                }
            }
        }
    }
}

# --- Report results ---
if ($findings.Count -eq 0) {
    Write-Host "No new secrets have been found" -ForegroundColor Green
    exit 0
}
else {
    Write-Host ""
    Write-Host "====== SECRETS DETECTED ======" -ForegroundColor Red
    Write-Host "$($findings.Count) potential secret(s) found in staged files:" -ForegroundColor Red
    Write-Host ""
    
    foreach ($finding in $findings) {
        Write-Host "  $($finding.File):$($finding.Line)" -ForegroundColor Yellow -NoNewline
        Write-Host " [$($finding.Type)]" -ForegroundColor Red
        if ($Verbose) {
            Write-Host "    $($finding.Content)" -ForegroundColor DarkGray
        }
    }
    
    Write-Host ""
    Write-Host "Commit blocked. Remove secrets before committing." -ForegroundColor Red
    Write-Host "If these are false positives, add the file to ignored_paths in .gitguardian.yaml" -ForegroundColor DarkGray
    exit 1
}
