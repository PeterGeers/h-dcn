#!/usr/bin/env pwsh
# ============================================================================
# H-DCN Personal Account Final Backup Script
# ============================================================================
# Creates a final backup of all h-dcn data from the Personal Account to S3
# with 90-day retention. This is the safety net before decommissioning.
#
# This script exports all 7 DynamoDB tables and syncs the S3 bucket to a
# dedicated backup bucket with lifecycle rules for automatic deletion after
# 90 days.
#
# Usage:
#   .\scripts\decommission\backup-personal-account.ps1 -DryRun
#   .\scripts\decommission\backup-personal-account.ps1
#   .\scripts\decommission\backup-personal-account.ps1 -Profile personal -BackupBucket h-dcn-decommission-backup
#
# Prerequisites:
#   - AWS CLI v2 configured with personal profile
#   - Personal profile has permissions: dynamodb:ExportTableToPointInTime,
#     dynamodb:UpdateContinuousBackups, s3:CreateBucket, s3:PutObject,
#     s3:PutLifecycleConfiguration, s3:GetObject, s3:ListBucket
#   - PITR enabled on source tables (script will enable if not)
#
# Requirements: 21.4
# ============================================================================

param(
    [Parameter(Mandatory = $false)]
    [string]$Profile = "personal",

    [Parameter(Mandatory = $false)]
    [string]$Region = "eu-west-1",

    [Parameter(Mandatory = $false)]
    [string]$AccountId = "344561557829",

    [Parameter(Mandatory = $false)]
    [string]$BackupBucket = "h-dcn-decommission-backup",

    [Parameter(Mandatory = $false)]
    [string]$SourceBucket = "my-hdcn-bucket",

    [Parameter(Mandatory = $false)]
    [string[]]$Tables = @("Producten", "Members", "Payments", "Events", "Memberships", "Carts", "Orders"),

    [Parameter(Mandatory = $false)]
    [int]$RetentionDays = 90,

    [Parameter(Mandatory = $false)]
    [int]$PollIntervalSeconds = 30,

    [Parameter(Mandatory = $false)]
    [int]$MaxWaitMinutes = 60,

    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$startTime = Get-Date

# ============================================================================
# Banner
# ============================================================================

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " H-DCN Personal Account Final Backup" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Account:        $AccountId ($Profile)" -ForegroundColor White
Write-Host " Region:         $Region" -ForegroundColor White
Write-Host " Backup Bucket:  $BackupBucket" -ForegroundColor White
Write-Host " Source Bucket:  $SourceBucket" -ForegroundColor White
Write-Host " Tables:         $($Tables -join ', ')" -ForegroundColor White
Write-Host " Retention:      $RetentionDays days" -ForegroundColor White
if ($DryRun) {
    Write-Host " Mode:           DRY RUN (no changes)" -ForegroundColor Yellow
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
    Write-Host "  [OK] $Message" -ForegroundColor Green
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
        [switch]$SuppressError
    )

    $allArgs = $Arguments + @("--profile", $Profile, "--region", $Region, "--output", "json")
    $result = aws @allArgs 2>&1

    if ($LASTEXITCODE -ne 0) {
        if (-not $SuppressError) {
            Write-Err "AWS CLI command failed: aws $($Arguments -join ' ')"
            Write-Host "    $result" -ForegroundColor Red
        }
        return $null
    }

    if ($result) {
        return $result | ConvertFrom-Json
    }
    return $true
}

# ============================================================================
# Pre-flight Checks
# ============================================================================

Write-Step "Pre-flight Checks"

# Verify profile access
Write-Info "Verifying profile ($Profile)..."
$identity = Invoke-AwsCli -Arguments @("sts", "get-caller-identity")
if (-not $identity) {
    Write-Err "Cannot authenticate with profile '$Profile'. Check your AWS credentials."
    exit 1
}
if ($identity.Account -ne $AccountId) {
    Write-Err "Profile returned account $($identity.Account), expected $AccountId"
    exit 1
}
Write-Success "Authenticated: $($identity.Arn)"

# Verify source tables exist
Write-Info "Verifying source tables..."
$missingTables = @()
foreach ($table in $Tables) {
    $result = Invoke-AwsCli -Arguments @("dynamodb", "describe-table", "--table-name", $table) -SuppressError
    if (-not $result) {
        $missingTables += $table
    }
}
if ($missingTables.Count -gt 0) {
    Write-Warn "Tables not found (may already be deleted): $($missingTables -join ', ')"
    $Tables = $Tables | Where-Object { $_ -notin $missingTables }
    if ($Tables.Count -eq 0) {
        Write-Err "No tables to backup. Exiting."
        exit 1
    }
}
Write-Success "Found $($Tables.Count) tables to backup"

# Verify source S3 bucket
Write-Info "Verifying source bucket ($SourceBucket)..."
$bucketCheck = Invoke-AwsCli -Arguments @("s3api", "head-bucket", "--bucket", $SourceBucket) -SuppressError
if (-not $bucketCheck) {
    Write-Warn "Source bucket '$SourceBucket' not accessible. S3 backup will be skipped."
    $skipS3 = $true
}
else {
    Write-Success "Source bucket accessible"
    $skipS3 = $false
}

if ($DryRun) {
    Write-Host ""
    Write-Host "  DRY RUN - Pre-flight checks complete. Showing planned actions." -ForegroundColor Yellow
}

# ============================================================================
# Phase 1: Create/Verify Backup Bucket with Lifecycle
# ============================================================================

Write-Step "Phase 1: Create Backup Bucket with $RetentionDays-Day Lifecycle"

$bucketExists = Invoke-AwsCli -Arguments @("s3api", "head-bucket", "--bucket", $BackupBucket) -SuppressError

if ($bucketExists) {
    Write-Success "Backup bucket already exists: $BackupBucket"
}
else {
    if ($DryRun) {
        Write-Warn "[DRY RUN] Would create bucket: $BackupBucket"
    }
    else {
        Write-Info "Creating backup bucket: $BackupBucket..."
        $createResult = Invoke-AwsCli -Arguments @(
            "s3api", "create-bucket",
            "--bucket", $BackupBucket,
            "--create-bucket-configuration", "LocationConstraint=$Region"
        )
        if (-not $createResult) {
            Write-Err "Failed to create backup bucket"
            exit 1
        }
        Write-Success "Created backup bucket: $BackupBucket"
    }
}

# Configure lifecycle rule for automatic deletion after retention period
if ($DryRun) {
    Write-Warn "[DRY RUN] Would configure $RetentionDays-day lifecycle rule on $BackupBucket"
}
else {
    Write-Info "Configuring $RetentionDays-day lifecycle rule..."

    $lifecycleJson = @{
        Rules = @(
            @{
                ID                          = "auto-delete-after-$RetentionDays-days"
                Status                      = "Enabled"
                Filter                      = @{ Prefix = "" }
                Expiration                  = @{ Days = $RetentionDays }
                NoncurrentVersionExpiration = @{ NoncurrentDays = $RetentionDays }
            }
        )
    } | ConvertTo-Json -Depth 5 -Compress

    $lifecycleFile = Join-Path $env:TEMP "h-dcn-backup-lifecycle.json"
    $lifecycleJson | Out-File -FilePath $lifecycleFile -Encoding utf8 -Force

    $lifecycleResult = Invoke-AwsCli -Arguments @(
        "s3api", "put-bucket-lifecycle-configuration",
        "--bucket", $BackupBucket,
        "--lifecycle-configuration", "file://$lifecycleFile"
    )

    Remove-Item -Force $lifecycleFile -ErrorAction SilentlyContinue

    if ($lifecycleResult) {
        Write-Success "Lifecycle rule configured: objects expire after $RetentionDays days"
    }
    else {
        Write-Warn "Could not set lifecycle rule. Set manually in AWS Console."
    }
}

# ============================================================================
# Phase 2: Export DynamoDB Tables
# ============================================================================

Write-Step "Phase 2: Export DynamoDB Tables to Backup Bucket"

$exportTimestamp = Get-Date -Format "yyyy-MM-dd-HHmmss"
$exportArns = @{}

foreach ($table in $Tables) {
    # Ensure PITR is enabled
    $pitrResult = Invoke-AwsCli -Arguments @("dynamodb", "describe-continuous-backups", "--table-name", $table)
    $pitrEnabled = $pitrResult -and $pitrResult.ContinuousBackupsDescription.PointInTimeRecoveryDescription.PointInTimeRecoveryStatus -eq "ENABLED"

    if (-not $pitrEnabled) {
        if ($DryRun) {
            Write-Warn "[DRY RUN] Would enable PITR on: $table"
        }
        else {
            Write-Info "Enabling PITR on $table..."
            Invoke-AwsCli -Arguments @(
                "dynamodb", "update-continuous-backups",
                "--table-name", $table,
                "--point-in-time-recovery-specification", "PointInTimeRecoveryEnabled=true"
            ) | Out-Null
        }
    }

    $tableArn = (Invoke-AwsCli -Arguments @("dynamodb", "describe-table", "--table-name", $table)).Table.TableArn
    $s3Prefix = "dynamodb/$table/$exportTimestamp"

    if ($DryRun) {
        Write-Warn "[DRY RUN] Would export $table to s3://$BackupBucket/$s3Prefix"
        continue
    }

    Write-Info "Exporting $table to s3://$BackupBucket/$s3Prefix..."

    $exportResult = Invoke-AwsCli -Arguments @(
        "dynamodb", "export-table-to-point-in-time",
        "--table-arn", $tableArn,
        "--s3-bucket", $BackupBucket,
        "--s3-prefix", $s3Prefix,
        "--export-format", "DYNAMODB_JSON"
    )

    if (-not $exportResult) {
        Write-Err "Failed to start export for $table"
        exit 1
    }

    $exportArns[$table] = $exportResult.ExportDescription.ExportArn
    Write-Info "Export started: $($exportResult.ExportDescription.ExportArn)"
}

# Wait for exports to complete
if (-not $DryRun -and $exportArns.Count -gt 0) {
    Write-Host ""
    Write-Info "Waiting for exports to complete (polling every ${PollIntervalSeconds}s, max ${MaxWaitMinutes}min)..."

    $waitStart = Get-Date
    $maxWait = New-TimeSpan -Minutes $MaxWaitMinutes
    $pendingExports = @{} + $exportArns

    while ($pendingExports.Count -gt 0) {
        $elapsed = (Get-Date) - $waitStart
        if ($elapsed -gt $maxWait) {
            Write-Err "Export timeout exceeded ($MaxWaitMinutes minutes). Pending: $($pendingExports.Keys -join ', ')"
            exit 1
        }

        Start-Sleep -Seconds $PollIntervalSeconds

        $completedThisRound = @()
        foreach ($entry in $pendingExports.GetEnumerator()) {
            $tableName = $entry.Key
            $arn = $entry.Value

            $status = Invoke-AwsCli -Arguments @("dynamodb", "describe-export", "--export-arn", $arn)
            if ($status) {
                $exportStatus = $status.ExportDescription.ExportStatus
                if ($exportStatus -eq "COMPLETED") {
                    Write-Success "$tableName export completed"
                    $completedThisRound += $tableName
                }
                elseif ($exportStatus -eq "FAILED") {
                    Write-Err "$tableName export FAILED: $($status.ExportDescription.FailureMessage)"
                    exit 1
                }
                else {
                    Write-Info "${tableName}: $exportStatus (elapsed: $([math]::Round($elapsed.TotalMinutes, 1))min)"
                }
            }
        }

        foreach ($completed in $completedThisRound) {
            $pendingExports.Remove($completed)
        }
    }

    Write-Success "All DynamoDB table exports completed"
}

# ============================================================================
# Phase 3: Sync S3 Bucket to Backup
# ============================================================================

if (-not $skipS3) {
    Write-Step "Phase 3: Sync S3 Bucket to Backup"

    $s3BackupPrefix = "s3-data/"

    if ($DryRun) {
        Write-Warn "[DRY RUN] Would sync s3://$SourceBucket → s3://$BackupBucket/$s3BackupPrefix"
    }
    else {
        Write-Info "Syncing s3://$SourceBucket → s3://$BackupBucket/$s3BackupPrefix..."

        aws s3 sync "s3://$SourceBucket" "s3://$BackupBucket/$s3BackupPrefix" `
            --profile $Profile `
            --region $Region

        if ($LASTEXITCODE -ne 0) {
            Write-Err "S3 sync failed"
            exit 1
        }

        Write-Success "S3 bucket synced to backup"
    }
}
else {
    Write-Step "Phase 3: SKIPPED (source bucket not accessible)"
}

# ============================================================================
# Summary
# ============================================================================

$totalTime = (Get-Date) - $startTime

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Final Backup Complete" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Duration:       $([math]::Round($totalTime.TotalMinutes, 1)) minutes" -ForegroundColor White
Write-Host " Backup Bucket:  s3://$BackupBucket" -ForegroundColor White
Write-Host " DynamoDB:       $($Tables.Count) tables exported" -ForegroundColor White
if (-not $skipS3) {
    Write-Host " S3 Data:        Synced from $SourceBucket" -ForegroundColor White
}
Write-Host " Retention:      $RetentionDays days (auto-delete)" -ForegroundColor White
Write-Host ""

if ($DryRun) {
    Write-Host " This was a DRY RUN. No changes were made." -ForegroundColor Yellow
    Write-Host " Remove -DryRun to execute the backup." -ForegroundColor Yellow
}
else {
    Write-Host " Backup is complete. Data will be automatically deleted" -ForegroundColor Green
    Write-Host " after $RetentionDays days via S3 lifecycle rule." -ForegroundColor Green
    Write-Host ""
    Write-Host " Next step: Run cleanup-personal-account.ps1 to remove h-dcn resources." -ForegroundColor Gray
}

Write-Host ""
