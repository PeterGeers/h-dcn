<#
.SYNOPSIS
    Runs both backend (pytest) and frontend (Jest) test suites.

.DESCRIPTION
    Executes backend and frontend tests in sequence, always running both suites
    regardless of individual failures. Prints a summary table and exits 0 only
    if both suites pass.

.PARAMETER Coverage
    When specified, adds coverage flags to both test suites:
    - Backend: --cov=handler --cov-report=term-missing
    - Frontend: --coverage

.EXAMPLE
    .\run-tests.ps1
    .\run-tests.ps1 -Coverage
#>

[CmdletBinding()]
param(
    [switch]$Coverage
)

$ErrorActionPreference = 'Continue'
$projectRoot = $PSScriptRoot

# --- Backend Tests ---
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host " Running Backend Tests (pytest)" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$backendArgs = @("tests/", "--tb=short")
if ($Coverage) {
    $backendArgs += "--cov=handler"
    $backendArgs += "--cov-report=term-missing"
}

Push-Location (Join-Path $projectRoot "backend")
try {
    & pytest @backendArgs
    $backendExitCode = $LASTEXITCODE
} finally {
    Pop-Location
}

# --- Frontend Tests ---
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host " Running Frontend Tests (Jest)" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$frontendArgs = @("test", "--", "--watchAll=false")
if ($Coverage) {
    $frontendArgs += "--coverage"
}

Push-Location (Join-Path $projectRoot "frontend")
try {
    & npm @frontendArgs
    $frontendExitCode = $LASTEXITCODE
} finally {
    Pop-Location
}

# --- Summary ---
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host " Test Summary" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$backendResult = if ($backendExitCode -eq 0) { "passed" } else { "FAILED" }
$frontendResult = if ($frontendExitCode -eq 0) { "passed" } else { "FAILED" }

$backendColor = if ($backendExitCode -eq 0) { "Green" } else { "Red" }
$frontendColor = if ($frontendExitCode -eq 0) { "Green" } else { "Red" }

Write-Host ("{0,-12} {1,-10} {2}" -f "Suite", "Result", "Exit Code")
Write-Host ("{0,-12} {1,-10} {2}" -f "-----", "------", "---------")
Write-Host ("{0,-12} " -f "Backend") -NoNewline
Write-Host ("{0,-10} " -f $backendResult) -ForegroundColor $backendColor -NoNewline
Write-Host $backendExitCode
Write-Host ("{0,-12} " -f "Frontend") -NoNewline
Write-Host ("{0,-10} " -f $frontendResult) -ForegroundColor $frontendColor -NoNewline
Write-Host $frontendExitCode

Write-Host ""

# Exit 0 only if both suites pass
if ($backendExitCode -eq 0 -and $frontendExitCode -eq 0) {
    Write-Host "All tests passed!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "One or more test suites failed." -ForegroundColor Red
    exit 1
}
