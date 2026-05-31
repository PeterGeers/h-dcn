#!/usr/bin/env pwsh
# ============================================================================
# H-DCN DynamoDB Migration Verification Script
# ============================================================================
# Compares row counts for all 7 DynamoDB tables between the source (personal)
# and destination (nonprofit) accounts. Halts and reports if any counts don't
# match.
#
# Usage:
#   .\scripts\migration\verify-dynamodb-migration.ps1
#   .\scripts\migration\verify-dynamodb-migration.ps1 -SourceProfile personal -TargetProfile nonprofit-deploy
#   .\scripts\migration\verify-dynamodb-migration.ps1 -Tables "Members","Payments"
#
# Prerequisites:
#   - AWS CLI v2 configured with appropriate profiles
#   - Source profile has permissions: dynamodb:Scan (or dynamodb:DescribeTable)
#   - Target profile has permissions: dynamodb:Scan (or dynamodb:DescribeTable)
#
# Requirements: 14.4, 14.5
# ============================================================================

param(
    [Parameter(Mandatory = $false)]
    [string]$SourceProfile = "personal",

    [Parameter(Mandatory = $false)]
    [string]$TargetProfile = "nonprofit-deploy",

    [Parameter(Mandatory = $false)]
    [string]$Region = "eu-west-1",

    [Parameter(Mandatory = $false)]
    [string]$SourceAccountId = "344561557829",

    [Parameter(Mandatory = $false)]
    [string]$TargetAccountId = "506221081911",

    [Parameter(Mandatory = $false)]
    [string[]]$Tables = @("Producten", "Members", "Payments", "Events", "Memberships", "Carts", "Orders"),

    [switch]$UseScan
)

$ErrorActionPreference = "Stop"

# ============================================================================
# Banner
# ============================================================================

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " H-DCN DynamoDB Migration Verification" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Source Account:  $SourceAccountId ($SourceProfile)" -ForegroundColor White
Write-Host " Target Account:  $TargetAccountId ($TargetProfile)" -ForegroundColor White
Write-Host " Region:          $Region" -ForegroundColor White
Write-Host " Tables:          $($Tables -join ', ')" -ForegroundColor White
if ($UseScan) {
    Write-Host " Count Method:    scan (accurate, slower)" -ForegroundColor White
}
else {
    Write-Host " Count Method:    describe-table (fast, eventually consistent)" -ForegroundColor White
}
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# Helper Functions
# ============================================================================

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "--- $Message ---" -ForegroundColor White
}

function Write-Success {
    param([string]$Message)
    Write-Host "  [PASS] $Message" -ForegroundColor Green
}

function Write-Info {
    param([string]$Message)
    Write-Host "  [INFO] $Message" -ForegroundColor Gray
}

function Write-Warn {
    param([string]$Message)
    Write-Host "  [WARN] $Message" -ForegroundColor Yellow
}

function Write-Err {
    param([string]$Message)
    Write-Host "  [FAIL] $Message" -ForegroundColor Red
}

function Invoke-AwsCli {
    param(
        [string[]]$Arguments,
        [string]$AwsProfile,
        [switch]$SuppressError
    )

    $allArgs = $Arguments + @("--profile", $AwsProfile, "--region", $Region, "--output", "json")
    $result = aws @allArgs 2>&1

    if ($LASTEXITCODE -ne 0) {
        if (-not $SuppressError) {
            Write-Err "AWS CLI command failed: aws $($Arguments -join ' ') --profile $AwsProfile"
            Write-Host "    $result" -ForegroundColor Red
        }
        return $null
    }

    if ($result) {
        return $result | ConvertFrom-Json
    }
    return $true
}

function Get-TableItemCount {
    param(
        [string]$TableName,
        [string]$AwsProfile,
        [bool]$Scan
    )

    if ($Scan) {
        # Use scan with SELECT COUNT for accurate count (consumes read capacity)
        $totalCount = 0
        $lastEvaluatedKey = $null

        do {
            $scanArgs = @("dynamodb", "scan", "--table-name", $TableName, "--select", "COUNT")
            if ($lastEvaluatedKey) {
                $keyJson = $lastEvaluatedKey | ConvertTo-Json -Compress
                $scanArgs += @("--exclusive-start-key", $keyJson)
            }

            $result = Invoke-AwsCli -Arguments $scanArgs -AwsProfile $AwsProfile
            if (-not $result) {
                return -1
            }

            $totalCount += $result.Count
            $lastEvaluatedKey = $result.LastEvaluatedKey
        } while ($null -ne $lastEvaluatedKey)

        return $totalCount
    }
    else {
        # Use describe-table for fast (but eventually consistent) count
        $result = Invoke-AwsCli -Arguments @("dynamodb", "describe-table", "--table-name", $TableName) -AwsProfile $AwsProfile
        if (-not $result) {
            return -1
        }
        return $result.Table.ItemCount
    }
}

# ============================================================================
# Pre-flight Checks
# ============================================================================

Write-Step "Pre-flight Checks"

# Verify source profile access
Write-Info "Verifying source profile ($SourceProfile)..."
$sourceIdentity = Invoke-AwsCli -Arguments @("sts", "get-caller-identity") -AwsProfile $SourceProfile
if (-not $sourceIdentity) {
    Write-Err "Cannot authenticate with source profile '$SourceProfile'. Check your AWS credentials."
    exit 1
}
if ($sourceIdentity.Account -ne $SourceAccountId) {
    Write-Err "Source profile returned account $($sourceIdentity.Account), expected $SourceAccountId"
    exit 1
}
Write-Success "Source profile authenticated: $($sourceIdentity.Arn)"

# Verify target profile access
Write-Info "Verifying target profile ($TargetProfile)..."
$targetIdentity = Invoke-AwsCli -Arguments @("sts", "get-caller-identity") -AwsProfile $TargetProfile
if (-not $targetIdentity) {
    Write-Err "Cannot authenticate with target profile '$TargetProfile'. Check your AWS credentials."
    exit 1
}
if ($targetIdentity.Account -ne $TargetAccountId) {
    Write-Err "Target profile returned account $($targetIdentity.Account), expected $TargetAccountId"
    exit 1
}
Write-Success "Target profile authenticated: $($targetIdentity.Arn)"

# ============================================================================
# Row Count Comparison
# ============================================================================

Write-Step "Comparing Row Counts"

if (-not $UseScan) {
    Write-Warn "Using describe-table ItemCount (eventually consistent, updated every ~6 hours)."
    Write-Warn "For exact counts, re-run with -UseScan (slower, consumes read capacity)."
    Write-Host ""
}

$results = @()
$hasFailure = $false

foreach ($table in $Tables) {
    Write-Info "Checking table: $table"

    # Get source count
    $sourceCount = Get-TableItemCount -TableName $table -AwsProfile $SourceProfile -Scan $UseScan
    if ($sourceCount -eq -1) {
        Write-Err "  Could not get item count for $table in source account"
        $hasFailure = $true
        $results += [PSCustomObject]@{
            Table       = $table
            Source      = "ERROR"
            Destination = "-"
            Status      = "ERROR"
        }
        continue
    }

    # Get target count
    $targetCount = Get-TableItemCount -TableName $table -AwsProfile $TargetProfile -Scan $UseScan
    if ($targetCount -eq -1) {
        Write-Err "  Could not get item count for $table in target account"
        $hasFailure = $true
        $results += [PSCustomObject]@{
            Table       = $table
            Source      = $sourceCount
            Destination = "ERROR"
            Status      = "ERROR"
        }
        continue
    }

    # Compare
    if ($sourceCount -eq $targetCount) {
        Write-Success "$table — $sourceCount items (match)"
        $results += [PSCustomObject]@{
            Table       = $table
            Source      = $sourceCount
            Destination = $targetCount
            Status      = "PASS"
        }
    }
    else {
        $diff = $sourceCount - $targetCount
        Write-Err "$table — Source: $sourceCount, Destination: $targetCount (difference: $diff)"
        $hasFailure = $true
        $results += [PSCustomObject]@{
            Table       = $table
            Source      = $sourceCount
            Destination = $targetCount
            Status      = "FAIL"
        }
    }
}

# ============================================================================
# Results Summary
# ============================================================================

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Verification Results" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Print results table
$headerFormat = "  {0,-15} {1,>10} {2,>12} {3,>8}"
$rowFormat = "  {0,-15} {1,>10} {2,>12} {3,>8}"

Write-Host ($headerFormat -f "Table", "Source", "Destination", "Status") -ForegroundColor White
Write-Host ("  " + ("-" * 50)) -ForegroundColor Gray

foreach ($row in $results) {
    $color = switch ($row.Status) {
        "PASS" { "Green" }
        "FAIL" { "Red" }
        "ERROR" { "Red" }
        default { "White" }
    }
    Write-Host ($rowFormat -f $row.Table, $row.Source, $row.Destination, $row.Status) -ForegroundColor $color
}

Write-Host ""

# ============================================================================
# Final Verdict
# ============================================================================

if ($hasFailure) {
    Write-Host "============================================" -ForegroundColor Red
    Write-Host " VERIFICATION FAILED" -ForegroundColor Red
    Write-Host "============================================" -ForegroundColor Red
    Write-Host ""
    Write-Host " One or more tables have mismatched row counts." -ForegroundColor Red
    Write-Host " Migration is HALTED. Do NOT proceed with DNS cutover." -ForegroundColor Red
    Write-Host ""
    Write-Host " Recommended actions:" -ForegroundColor Yellow
    Write-Host "   1. If using describe-table counts, re-run with -UseScan for exact counts" -ForegroundColor Yellow
    Write-Host "   2. Re-run the migration for affected tables:" -ForegroundColor Yellow
    Write-Host "      .\scripts\migration\migrate-dynamodb.ps1 -Tables `"<table>`"" -ForegroundColor Yellow
    Write-Host "   3. Check for import errors in the AWS Console (DynamoDB > Imports)" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}
else {
    Write-Host "============================================" -ForegroundColor Green
    Write-Host " VERIFICATION PASSED" -ForegroundColor Green
    Write-Host "============================================" -ForegroundColor Green
    Write-Host ""
    Write-Host " All $($Tables.Count) tables have matching row counts." -ForegroundColor Green
    Write-Host " Data migration verified successfully." -ForegroundColor Green
    Write-Host ""
    exit 0
}
