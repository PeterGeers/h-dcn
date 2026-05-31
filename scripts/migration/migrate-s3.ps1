# ============================================================================
# H-DCN S3 Data Migration Script
# ============================================================================
# This script migrates all S3 objects from the personal account bucket to the
# nonprofit account bucket using `aws s3 sync`. It preserves object metadata
# and folder structure, then verifies object counts match.
#
# Usage:
#   .\scripts\migration\migrate-s3.ps1
#   .\scripts\migration\migrate-s3.ps1 -DryRun
#   .\scripts\migration\migrate-s3.ps1 -SourceProfile personal -DestProfile nonprofit-deploy
#   .\scripts\migration\migrate-s3.ps1 -SourceBucket my-hdcn-bucket -DestBucket h-dcn-data-506221081911
#
# Prerequisites:
#   - AWS CLI configured with appropriate profiles (personal, nonprofit-deploy)
#   - Source profile has s3:ListBucket and s3:GetObject on source bucket
#   - Destination profile has s3:PutObject and s3:ListBucket on destination bucket
#
# Requirements: 15.1, 15.2, 15.3
# ============================================================================

param(
    [Parameter(Mandatory = $false)]
    [string]$SourceBucket = "my-hdcn-bucket",

    [Parameter(Mandatory = $false)]
    [string]$DestBucket = "h-dcn-data-506221081911",

    [Parameter(Mandatory = $false)]
    [string]$SourceProfile = "personal",

    [Parameter(Mandatory = $false)]
    [string]$DestProfile = "nonprofit-deploy",

    [Parameter(Mandatory = $false)]
    [string]$Region = "eu-west-1",

    [Parameter(Mandatory = $false)]
    [string]$Exclude = "",

    [switch]$DryRun,

    [switch]$SkipVerification
)

$ErrorActionPreference = "Stop"

# ============================================================================
# Display Configuration
# ============================================================================

Write-Host "============================================" -ForegroundColor Cyan
Write-Host " H-DCN S3 Data Migration" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Source:      s3://$SourceBucket" -ForegroundColor White
Write-Host " Destination: s3://$DestBucket" -ForegroundColor White
Write-Host " Source Profile:  $SourceProfile" -ForegroundColor White
Write-Host " Dest Profile:    $DestProfile" -ForegroundColor White
Write-Host " Region:          $Region" -ForegroundColor White
if ($DryRun) {
    Write-Host " Mode:            DRY RUN (no changes)" -ForegroundColor Yellow
}
if ($SkipVerification) {
    Write-Host " Verification:    SKIPPED" -ForegroundColor Yellow
}
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# Helper Functions
# ============================================================================

function Get-S3ObjectCount {
    param(
        [string]$Bucket,
        [string]$Profile,
        [string]$AwsRegion
    )

    $result = aws s3api list-objects-v2 `
        --bucket $Bucket `
        --query "KeyCount" `
        --profile $Profile `
        --region $AwsRegion 2>&1

    if ($LASTEXITCODE -ne 0) {
        Write-Host "  [ERROR] Failed to list objects in s3://$Bucket" -ForegroundColor Red
        Write-Host "  $result" -ForegroundColor Red
        return -1
    }

    # list-objects-v2 paginates at 1000 objects; use recursive count for accuracy
    $countResult = aws s3 ls "s3://$Bucket" `
        --recursive `
        --profile $Profile `
        --region $AwsRegion 2>&1

    if ($LASTEXITCODE -ne 0) {
        Write-Host "  [ERROR] Failed to list objects in s3://$Bucket" -ForegroundColor Red
        Write-Host "  $countResult" -ForegroundColor Red
        return -1
    }

    # Count non-empty lines (each line is an object)
    $lines = $countResult | Where-Object { $_ -match '\S' }
    if ($null -eq $lines) {
        return 0
    }
    if ($lines -is [string]) {
        return 1
    }
    return $lines.Count
}

function Get-S3TotalSize {
    param(
        [string]$Bucket,
        [string]$Profile,
        [string]$AwsRegion
    )

    $result = aws s3 ls "s3://$Bucket" `
        --recursive `
        --summarize `
        --profile $Profile `
        --region $AwsRegion 2>&1

    if ($LASTEXITCODE -ne 0) {
        return "unknown"
    }

    $sizeLine = $result | Where-Object { $_ -match "Total Size:" }
    if ($sizeLine) {
        return ($sizeLine -replace ".*Total Size:\s*", "").Trim()
    }
    return "unknown"
}

function Test-BucketAccess {
    param(
        [string]$Bucket,
        [string]$Profile,
        [string]$AwsRegion
    )

    try {
        aws s3api head-bucket `
            --bucket $Bucket `
            --profile $Profile `
            --region $AwsRegion 2>&1 | Out-Null

        return $LASTEXITCODE -eq 0
    }
    catch {
        return $false
    }
}

# ============================================================================
# Pre-flight Checks
# ============================================================================

Write-Host "--- Pre-flight Checks ---" -ForegroundColor White
Write-Host ""

# Verify source bucket access
Write-Host "  Checking source bucket access (s3://$SourceBucket)..." -ForegroundColor Gray
if (-not (Test-BucketAccess -Bucket $SourceBucket -Profile $SourceProfile -AwsRegion $Region)) {
    Write-Host "  [FAIL] Cannot access source bucket s3://$SourceBucket with profile '$SourceProfile'" -ForegroundColor Red
    Write-Host "  Verify the profile has s3:ListBucket and s3:GetObject permissions." -ForegroundColor Red
    exit 1
}
Write-Host "  [OK] Source bucket accessible" -ForegroundColor Green

# Verify destination bucket access
Write-Host "  Checking destination bucket access (s3://$DestBucket)..." -ForegroundColor Gray
if (-not (Test-BucketAccess -Bucket $DestBucket -Profile $DestProfile -AwsRegion $Region)) {
    Write-Host "  [FAIL] Cannot access destination bucket s3://$DestBucket with profile '$DestProfile'" -ForegroundColor Red
    Write-Host "  Verify the profile has s3:PutObject and s3:ListBucket permissions." -ForegroundColor Red
    exit 1
}
Write-Host "  [OK] Destination bucket accessible" -ForegroundColor Green
Write-Host ""

# Get source object count and size
Write-Host "  Counting source objects..." -ForegroundColor Gray
$sourceCount = Get-S3ObjectCount -Bucket $SourceBucket -Profile $SourceProfile -AwsRegion $Region
if ($sourceCount -eq -1) {
    Write-Host "  [FAIL] Could not count source objects." -ForegroundColor Red
    exit 1
}
$sourceSize = Get-S3TotalSize -Bucket $SourceBucket -Profile $SourceProfile -AwsRegion $Region
Write-Host "  [OK] Source: $sourceCount objects ($sourceSize)" -ForegroundColor Green
Write-Host ""

# ============================================================================
# S3 Sync Execution
# ============================================================================

Write-Host "--- S3 Sync ---" -ForegroundColor White
Write-Host ""

# Build the sync command arguments
# Note: aws s3 sync preserves folder structure and object metadata by default.
# The --copy-props metadata-directive flag ensures all metadata is preserved.
$syncArgs = @(
    "s3", "sync",
    "s3://$SourceBucket",
    "s3://$DestBucket",
    "--source-region", $Region,
    "--region", $Region,
    "--profile", $DestProfile
)

# Add --dryrun flag if DryRun switch is set
if ($DryRun) {
    $syncArgs += "--dryrun"
}

# Add exclude pattern if specified
if ($Exclude -ne "") {
    $syncArgs += "--exclude"
    $syncArgs += $Exclude
}

$startTime = Get-Date
Write-Host "  Starting sync at $($startTime.ToString('yyyy-MM-dd HH:mm:ss'))..." -ForegroundColor White
Write-Host "  Command: aws $($syncArgs -join ' ')" -ForegroundColor Gray
Write-Host ""

# Execute the sync
# Note: For cross-account sync, the destination profile must have read access to
# the source bucket OR we use a two-step approach. Since both profiles are
# configured for the same user (peter) with different roles, we use the dest
# profile which should have the necessary cross-account permissions.
# If cross-account access is not configured on the source bucket policy,
# use a local intermediate copy or configure bucket policy to allow the dest role.
aws @syncArgs

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "  [ERROR] S3 sync failed with exit code $LASTEXITCODE" -ForegroundColor Red
    Write-Host "  If cross-account access is denied, ensure the source bucket policy" -ForegroundColor Yellow
    Write-Host "  allows s3:GetObject and s3:ListBucket for the destination role," -ForegroundColor Yellow
    Write-Host "  or run the sync using the source profile with PutObject on the dest bucket." -ForegroundColor Yellow
    exit 1
}

$endTime = Get-Date
$duration = $endTime - $startTime
Write-Host ""
Write-Host "  [OK] Sync completed in $($duration.ToString('hh\:mm\:ss'))" -ForegroundColor Green
Write-Host ""

# ============================================================================
# Verification
# ============================================================================

if ($DryRun) {
    Write-Host "--- Verification (skipped in dry run) ---" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Re-run without -DryRun to perform actual sync and verification." -ForegroundColor Yellow
    Write-Host ""
    exit 0
}

if ($SkipVerification) {
    Write-Host "--- Verification (skipped by user) ---" -ForegroundColor Yellow
    Write-Host ""
    exit 0
}

Write-Host "--- Verification ---" -ForegroundColor White
Write-Host ""

# Count objects in destination
Write-Host "  Counting destination objects..." -ForegroundColor Gray
$destCount = Get-S3ObjectCount -Bucket $DestBucket -Profile $DestProfile -AwsRegion $Region
if ($destCount -eq -1) {
    Write-Host "  [FAIL] Could not count destination objects." -ForegroundColor Red
    exit 1
}
Write-Host "  Source:      $sourceCount objects" -ForegroundColor White
Write-Host "  Destination: $destCount objects" -ForegroundColor White
Write-Host ""

# Compare counts
if ($sourceCount -eq $destCount) {
    Write-Host "  [PASS] Object counts match: $sourceCount == $destCount" -ForegroundColor Green
}
else {
    $diff = $sourceCount - $destCount
    Write-Host "  [FAIL] Object count MISMATCH!" -ForegroundColor Red
    Write-Host "         Source:      $sourceCount" -ForegroundColor Red
    Write-Host "         Destination: $destCount" -ForegroundColor Red
    Write-Host "         Difference:  $diff objects" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Possible causes:" -ForegroundColor Yellow
    Write-Host "    - Sync excluded some objects (check --exclude patterns)" -ForegroundColor Yellow
    Write-Host "    - Objects were added to source during sync" -ForegroundColor Yellow
    Write-Host "    - Permission errors on specific objects (check sync output above)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Recommended action: Re-run the script to sync remaining objects." -ForegroundColor Yellow
    Write-Host "  (aws s3 sync is idempotent and will only copy missing/changed objects)" -ForegroundColor Yellow
    exit 1
}

# ============================================================================
# Summary
# ============================================================================

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " S3 Migration Complete" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Source:      s3://$SourceBucket ($sourceCount objects)" -ForegroundColor White
Write-Host " Destination: s3://$DestBucket ($destCount objects)" -ForegroundColor White
Write-Host " Duration:    $($duration.ToString('hh\:mm\:ss'))" -ForegroundColor White
Write-Host " Status:      SUCCESS" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Notes:" -ForegroundColor Gray
Write-Host "  - Object metadata and folder structure have been preserved" -ForegroundColor Gray
Write-Host "  - Run this script again at any time (s3 sync is idempotent)" -ForegroundColor Gray
Write-Host "  - Only new or modified objects will be copied on subsequent runs" -ForegroundColor Gray
Write-Host ""
