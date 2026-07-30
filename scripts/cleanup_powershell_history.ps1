# cleanup_powershell_history.ps1
# One-time cleanup: removes lines matching secret patterns from PowerShell history file.
# Feature: risk-management
# Requirements: 3.5, 3.6
#
# Usage: .\scripts\cleanup_powershell_history.ps1
# Always creates a backup before modifying the history file.

$ErrorActionPreference = 'Stop'

# --- Secret patterns (same as AddToHistoryHandler in $PROFILE) ---
$secretPatterns = @(
    'AKIA[0-9A-Z]{16}'
    'BEGIN\s+(RSA|DSA|EC|OPENSSH)?\s*PRIVATE\s+KEY'
    'sk_live_[0-9a-zA-Z]+'
    'pk_live_[0-9a-zA-Z]+'
    '(live|test)_[0-9a-zA-Z]{20,}'
    'ghp_[0-9a-zA-Z]{36,}'
    'glpat-[0-9a-zA-Z\-]{20,}'
    'AIza[0-9A-Za-z\-_]{35}'
    'xox[bpors]-[0-9a-zA-Z\-]+'
    'Bearer\s+[A-Za-z0-9\-._~+/]+=*'
)
$pattern = ($secretPatterns -join '|')

# --- Get history file path ---
$histPath = (Get-PSReadLineOption).HistorySavePath

if (-not (Test-Path $histPath)) {
    Write-Host "History file not found: $histPath" -ForegroundColor Yellow
    Write-Host "Nothing to clean up (0 lines removed)."
    exit 0
}

# --- Check if file is empty ---
$lines = $null
$retryCount = 0

try {
    $lines = Get-Content $histPath
}
catch [System.IO.IOException] {
    # File might be locked by another PowerShell session — retry once after 1s
    Write-Host "History file is locked, retrying in 1 second..." -ForegroundColor Yellow
    Start-Sleep -Seconds 1
    try {
        $lines = Get-Content $histPath
    }
    catch {
        Write-Host "ERROR: Could not read history file (still locked): $histPath" -ForegroundColor Red
        Write-Host "Close other PowerShell sessions and try again."
        exit 1
    }
}

if ($null -eq $lines -or $lines.Count -eq 0) {
    Write-Host "History file is empty (0 lines removed)."
    exit 0
}

# --- Create backup ---
$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$backupPath = "$histPath.backup.$timestamp"
Copy-Item $histPath $backupPath
Write-Host "Backup created: $backupPath" -ForegroundColor Green

# --- Filter out secret-containing lines ---
$clean = $lines | Where-Object { $_ -notmatch $pattern }
$removedCount = $lines.Count - $clean.Count

# --- Write cleaned history ---
if ($removedCount -gt 0) {
    $clean | Set-Content $histPath
    Write-Host "Removed $removedCount lines containing secrets." -ForegroundColor Cyan
}
else {
    Write-Host "No secrets found in history (0 lines removed)." -ForegroundColor Green
}

Write-Host "Total lines before: $($lines.Count)"
Write-Host "Total lines after:  $($clean.Count)"
