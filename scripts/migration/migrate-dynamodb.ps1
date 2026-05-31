#!/usr/bin/env pwsh
# ============================================================================
# H-DCN DynamoDB Data Migration Script
# ============================================================================
# Migrates DynamoDB table data from the Personal Account to the Nonprofit Account
# using PITR export → S3 cross-account copy → DynamoDB import.
#
# This script is idempotent and safe to re-run. Each step checks current state
# before taking action.
#
# Usage:
#   .\scripts\migration\migrate-dynamodb.ps1 -DryRun
#   .\scripts\migration\migrate-dynamodb.ps1 -SourceProfile personal -TargetProfile nonprofit-deploy
#   .\scripts\migration\migrate-dynamodb.ps1 -Tables "Members","Payments"
#
# Prerequisites:
#   - AWS CLI v2 configured with appropriate profiles
#   - Source profile has permissions: dynamodb:ExportTableToPointInTime, dynamodb:UpdateContinuousBackups, s3:PutObject
#   - Target profile has permissions: dynamodb:ImportTable, s3:GetObject, s3:PutObject
#   - Source S3 bucket exists for PITR exports
#   - Target S3 bucket exists for import data
#
# Requirements: 14.1, 14.2, 14.3
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
    [string]$SourceExportBucket = "h-dcn-dynamodb-exports-$SourceAccountId",

    [Parameter(Mandatory = $false)]
    [string]$TargetImportBucket = "h-dcn-dynamodb-imports-$TargetAccountId",

    [Parameter(Mandatory = $false)]
    [string[]]$Tables = @("Producten", "Members", "Payments", "Events", "Memberships", "Carts", "Orders"),

    [Parameter(Mandatory = $false)]
    [int]$PollIntervalSeconds = 30,

    [Parameter(Mandatory = $false)]
    [int]$MaxWaitMinutes = 60,

    [switch]$DryRun,

    [switch]$SkipPitrEnable,

    [switch]$SkipExport,

    [switch]$SkipCopy,

    [switch]$SkipImport
)

$ErrorActionPreference = "Stop"
$startTime = Get-Date

# ============================================================================
# Banner
# ============================================================================

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " H-DCN DynamoDB Data Migration" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Source Account:  $SourceAccountId ($SourceProfile)" -ForegroundColor White
Write-Host " Target Account:  $TargetAccountId ($TargetProfile)" -ForegroundColor White
Write-Host " Region:          $Region" -ForegroundColor White
Write-Host " Tables:          $($Tables -join ', ')" -ForegroundColor White
Write-Host " Export Bucket:   $SourceExportBucket" -ForegroundColor White
Write-Host " Import Bucket:   $TargetImportBucket" -ForegroundColor White
if ($DryRun) {
    Write-Host " Mode:            DRY RUN (no changes)" -ForegroundColor Yellow
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
    Write-Host "  ✅ $Message" -ForegroundColor Green
}

function Write-Info {
    param([string]$Message)
    Write-Host "  ℹ️  $Message" -ForegroundColor Gray
}

function Write-Warn {
    param([string]$Message)
    Write-Host "  ⚠️  $Message" -ForegroundColor Yellow
}

function Write-Err {
    param([string]$Message)
    Write-Host "  ❌ $Message" -ForegroundColor Red
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

function Get-TableArn {
    param([string]$TableName, [string]$AwsProfile)
    
    $result = Invoke-AwsCli -Arguments @("dynamodb", "describe-table", "--table-name", $TableName) -AwsProfile $AwsProfile
    if ($result) {
        return $result.Table.TableArn
    }
    return $null
}

function Test-PitrEnabled {
    param([string]$TableName, [string]$AwsProfile)

    $result = Invoke-AwsCli -Arguments @("dynamodb", "describe-continuous-backups", "--table-name", $TableName) -AwsProfile $AwsProfile
    if ($result) {
        return $result.ContinuousBackupsDescription.PointInTimeRecoveryDescription.PointInTimeRecoveryStatus -eq "ENABLED"
    }
    return $false
}

function Test-S3BucketExists {
    param([string]$BucketName, [string]$AwsProfile)

    $result = Invoke-AwsCli -Arguments @("s3api", "head-bucket", "--bucket", $BucketName) -AwsProfile $AwsProfile -SuppressError
    return ($null -ne $result)
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

# Verify source tables exist
Write-Info "Verifying source tables exist..."
$missingTables = @()
foreach ($table in $Tables) {
    $arn = Get-TableArn -TableName $table -AwsProfile $SourceProfile
    if (-not $arn) {
        $missingTables += $table
    }
}
if ($missingTables.Count -gt 0) {
    Write-Err "Source tables not found: $($missingTables -join ', ')"
    exit 1
}
Write-Success "All $($Tables.Count) source tables exist"

# Verify S3 buckets
Write-Info "Verifying S3 export bucket ($SourceExportBucket)..."
if (-not (Test-S3BucketExists -BucketName $SourceExportBucket -AwsProfile $SourceProfile)) {
    if ($DryRun) {
        Write-Warn "Export bucket '$SourceExportBucket' does not exist (would need to be created)"
    }
    else {
        Write-Warn "Export bucket '$SourceExportBucket' does not exist. Creating..."
        Invoke-AwsCli -Arguments @("s3api", "create-bucket", "--bucket", $SourceExportBucket, "--create-bucket-configuration", "LocationConstraint=$Region") -AwsProfile $SourceProfile
        if ($LASTEXITCODE -ne 0) {
            Write-Err "Failed to create export bucket"
            exit 1
        }
        Write-Success "Created export bucket: $SourceExportBucket"
    }
}
else {
    Write-Success "Export bucket exists: $SourceExportBucket"
}

Write-Info "Verifying S3 import bucket ($TargetImportBucket)..."
if (-not (Test-S3BucketExists -BucketName $TargetImportBucket -AwsProfile $TargetProfile)) {
    if ($DryRun) {
        Write-Warn "Import bucket '$TargetImportBucket' does not exist (would need to be created)"
    }
    else {
        Write-Warn "Import bucket '$TargetImportBucket' does not exist. Creating..."
        Invoke-AwsCli -Arguments @("s3api", "create-bucket", "--bucket", $TargetImportBucket, "--create-bucket-configuration", "LocationConstraint=$Region") -AwsProfile $TargetProfile
        if ($LASTEXITCODE -ne 0) {
            Write-Err "Failed to create import bucket"
            exit 1
        }
        Write-Success "Created import bucket: $TargetImportBucket"
    }
}
else {
    Write-Success "Import bucket exists: $TargetImportBucket"
}

if ($DryRun) {
    Write-Host ""
    Write-Host "  🏁 DRY RUN - Pre-flight checks complete. Showing planned actions below." -ForegroundColor Yellow
}

# ============================================================================
# Phase 1: Enable PITR on Source Tables
# ============================================================================

if (-not $SkipPitrEnable) {
    Write-Step "Phase 1: Enable Point-in-Time Recovery (PITR) on Source Tables"

    foreach ($table in $Tables) {
        $pitrEnabled = Test-PitrEnabled -TableName $table -AwsProfile $SourceProfile

        if ($pitrEnabled) {
            Write-Success "$table - PITR already enabled"
        }
        else {
            if ($DryRun) {
                Write-Warn "[DRY RUN] Would enable PITR on: $table"
            }
            else {
                Write-Info "Enabling PITR on: $table..."
                $result = Invoke-AwsCli -Arguments @(
                    "dynamodb", "update-continuous-backups",
                    "--table-name", $table,
                    "--point-in-time-recovery-specification", "PointInTimeRecoveryEnabled=true"
                ) -AwsProfile $SourceProfile

                if ($result) {
                    Write-Success "$table - PITR enabled"
                }
                else {
                    Write-Err "Failed to enable PITR on $table"
                    exit 1
                }
            }
        }
    }
}
else {
    Write-Step "Phase 1: SKIPPED (SkipPitrEnable flag set)"
}

# ============================================================================
# Phase 2: Export Tables to S3 via PITR
# ============================================================================

if (-not $SkipExport) {
    Write-Step "Phase 2: Export Tables to S3 via Point-in-Time Recovery"

    $exportArns = @{}
    $exportTimestamp = Get-Date -Format "yyyy-MM-dd-HHmmss"

    foreach ($table in $Tables) {
        $tableArn = Get-TableArn -TableName $table -AwsProfile $SourceProfile
        $s3Prefix = "exports/$table/$exportTimestamp"

        if ($DryRun) {
            Write-Warn "[DRY RUN] Would export $table to s3://$SourceExportBucket/$s3Prefix"
            continue
        }

        Write-Info "Starting export for: $table → s3://$SourceExportBucket/$s3Prefix"

        $exportResult = Invoke-AwsCli -Arguments @(
            "dynamodb", "export-table-to-point-in-time",
            "--table-arn", $tableArn,
            "--s3-bucket", $SourceExportBucket,
            "--s3-prefix", $s3Prefix,
            "--export-format", "DYNAMODB_JSON"
        ) -AwsProfile $SourceProfile

        if (-not $exportResult) {
            Write-Err "Failed to start export for $table"
            exit 1
        }

        $exportArn = $exportResult.ExportDescription.ExportArn
        $exportArns[$table] = $exportArn
        Write-Info "Export started: $exportArn"
    }

    # Wait for all exports to complete
    if (-not $DryRun -and $exportArns.Count -gt 0) {
        Write-Host ""
        Write-Info "Waiting for exports to complete (polling every ${PollIntervalSeconds}s, max ${MaxWaitMinutes}min)..."

        $waitStart = Get-Date
        $maxWait = New-TimeSpan -Minutes $MaxWaitMinutes
        $pendingExports = @{} + $exportArns  # Clone

        while ($pendingExports.Count -gt 0) {
            $elapsed = (Get-Date) - $waitStart
            if ($elapsed -gt $maxWait) {
                Write-Err "Export timeout exceeded `($($MaxWaitMinutes) minutes`). Pending: $($pendingExports.Keys -join ', ')"
                Write-Err "You can re-run this script with -SkipPitrEnable -SkipExport to resume from the copy phase."
                exit 1
            }

            Start-Sleep -Seconds $PollIntervalSeconds

            $completedThisRound = @()
            foreach ($entry in $pendingExports.GetEnumerator()) {
                $tableName = $entry.Key
                $arn = $entry.Value

                $status = Invoke-AwsCli -Arguments @(
                    "dynamodb", "describe-export",
                    "--export-arn", $arn
                ) -AwsProfile $SourceProfile

                if ($status) {
                    $exportStatus = $status.ExportDescription.ExportStatus
                    if ($exportStatus -eq "COMPLETED") {
                        Write-Success "$tableName export completed"
                        $completedThisRound += $tableName
                    }
                    elseif ($exportStatus -eq "FAILED") {
                        $failureReason = $status.ExportDescription.FailureMessage
                        Write-Err "$tableName export FAILED: $failureReason"
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

        Write-Success "All table exports completed successfully"
    }
}
else {
    Write-Step "Phase 2: SKIPPED (SkipExport flag set)"
}

# ============================================================================
# Phase 3: Copy Exported Data from Source S3 to Target S3
# ============================================================================

if (-not $SkipCopy) {
    Write-Step "Phase 3: Copy Exported Data to Nonprofit Account S3"

    Write-Info "Copying from s3://$SourceExportBucket to s3://$TargetImportBucket"
    Write-Info "This uses the source profile to read and target profile to write."
    Write-Host ""

    foreach ($table in $Tables) {
        $sourcePrefix = "exports/$table/"
        $targetPrefix = "imports/$table/"

        if ($DryRun) {
            Write-Warn "[DRY RUN] Would copy s3://$SourceExportBucket/$sourcePrefix → s3://$TargetImportBucket/$targetPrefix"
            continue
        }

        Write-Info "Copying $table data..."

        # Step 1: Download from source to local temp
        $tempDir = Join-Path $env:TEMP "h-dcn-migration" $table
        if (Test-Path $tempDir) {
            Remove-Item -Recurse -Force $tempDir
        }
        New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

        Write-Info "  Downloading from source bucket..."
        aws s3 sync "s3://$SourceExportBucket/$sourcePrefix" $tempDir --profile $SourceProfile --region $Region 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Err "Failed to download $table export from source bucket"
            exit 1
        }

        # Step 2: Upload to target bucket
        Write-Info "  Uploading to target bucket..."
        aws s3 sync $tempDir "s3://$TargetImportBucket/$targetPrefix" --profile $TargetProfile --region $Region 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Err "Failed to upload $table data to target bucket"
            exit 1
        }

        # Step 3: Clean up temp
        Remove-Item -Recurse -Force $tempDir

        Write-Success "$table data copied to target bucket"
    }

    # Clean up temp root
    $tempRoot = Join-Path $env:TEMP "h-dcn-migration"
    if (Test-Path $tempRoot) {
        Remove-Item -Recurse -Force $tempRoot
    }

    if (-not $DryRun) {
        Write-Success "All table data copied to nonprofit account S3"
    }
}
else {
    Write-Step "Phase 3: SKIPPED (SkipCopy flag set)"
}

# ============================================================================
# Phase 4: Import Data into Nonprofit DynamoDB Tables
# ============================================================================

if (-not $SkipImport) {
    Write-Step "Phase 4: Import Data into Nonprofit DynamoDB Tables"

    $importArns = @{}

    foreach ($table in $Tables) {
        $importPrefix = "imports/$table/"

        if ($DryRun) {
            Write-Warn "[DRY RUN] Would import s3://$TargetImportBucket/$importPrefix into table: $table"
            continue
        }

        # Check if target table already has data (safety check)
        $targetTableInfo = Invoke-AwsCli -Arguments @("dynamodb", "describe-table", "--table-name", $table) -AwsProfile $TargetProfile -SuppressError
        if ($targetTableInfo -and $targetTableInfo.Table.ItemCount -gt 0) {
            Write-Warn "$table already has $($targetTableInfo.Table.ItemCount) items in target. Skipping import."
            Write-Warn "  To re-import, delete and recreate the table first."
            continue
        }

        # Find the most recent export manifest in the import bucket
        # The PITR export creates a structure: prefix/AWSDynamoDB/<export-id>/manifest-files.json
        Write-Info "Looking for export data for $table in s3://$TargetImportBucket/$importPrefix..."

        $manifestSearch = aws s3 ls "s3://$TargetImportBucket/${importPrefix}" --recursive --profile $TargetProfile --region $Region 2>&1
        if ($LASTEXITCODE -ne 0 -or -not $manifestSearch) {
            Write-Err "No export data found for $table in target bucket. Run copy phase first."
            exit 1
        }

        # Find the S3 prefix that contains the export (look for manifest-summary.json)
        $manifestLines = $manifestSearch | Select-String "manifest-summary.json"
        if (-not $manifestLines) {
            Write-Err "No manifest-summary.json found for $table. Export data may be incomplete."
            exit 1
        }

        # Get the S3 prefix up to the AWSDynamoDB/<export-id>/ level
        $manifestPath = ($manifestLines | Select-Object -Last 1).ToString().Trim()
        # Extract the key from the ls output (format: "date time size key")
        $manifestKey = ($manifestPath -split '\s+', 4)[3]
        # The import needs the prefix up to and including the export-id folder
        $importS3Prefix = $manifestKey -replace '/manifest-summary.json$', ''

        Write-Info "Starting import for $table from s3://$TargetImportBucket/$importS3Prefix"

        # Get table key schema from source to use in import
        $sourceTableDesc = Invoke-AwsCli -Arguments @("dynamodb", "describe-table", "--table-name", $table) -AwsProfile $SourceProfile

        # Build import input JSON
        $importInput = @{
            S3BucketSource          = @{
                S3Bucket      = $TargetImportBucket
                S3KeyPrefix   = $importS3Prefix
                S3BucketOwner = $TargetAccountId
            }
            InputFormat             = "DYNAMODB_JSON"
            InputCompressionType    = "ZSTD"
            TableCreationParameters = @{
                TableName            = $table
                KeySchema            = $sourceTableDesc.Table.KeySchema
                AttributeDefinitions = $sourceTableDesc.Table.AttributeDefinitions
                BillingMode          = "PAY_PER_REQUEST"
            }
        } | ConvertTo-Json -Depth 10 -Compress

        # Write to temp file for the CLI
        $importInputFile = Join-Path $env:TEMP "h-dcn-import-$table.json"
        $importInput | Out-File -FilePath $importInputFile -Encoding utf8 -Force

        $importResult = Invoke-AwsCli -Arguments @(
            "dynamodb", "import-table",
            "--cli-input-json", "file://$importInputFile"
        ) -AwsProfile $TargetProfile

        # Clean up temp file
        Remove-Item -Force $importInputFile -ErrorAction SilentlyContinue

        if (-not $importResult) {
            Write-Err "Failed to start import for $table"
            exit 1
        }

        $importArn = $importResult.ImportTableDescription.ImportArn
        $importArns[$table] = $importArn
        Write-Info "Import started: $importArn"
    }

    # Wait for all imports to complete
    if (-not $DryRun -and $importArns.Count -gt 0) {
        Write-Host ""
        Write-Info "Waiting for imports to complete (polling every ${PollIntervalSeconds}s, max ${MaxWaitMinutes}min)..."

        $waitStart = Get-Date
        $maxWait = New-TimeSpan -Minutes $MaxWaitMinutes
        $pendingImports = @{} + $importArns  # Clone

        while ($pendingImports.Count -gt 0) {
            $elapsed = (Get-Date) - $waitStart
            if ($elapsed -gt $maxWait) {
                Write-Err "Import timeout exceeded `($($MaxWaitMinutes) minutes`). Pending: $($pendingImports.Keys -join ', ')"
                Write-Err "Check import status manually with: aws dynamodb describe-import --import-arn [arn] --profile $TargetProfile"
                exit 1
            }

            Start-Sleep -Seconds $PollIntervalSeconds

            $completedThisRound = @()
            foreach ($entry in $pendingImports.GetEnumerator()) {
                $tableName = $entry.Key
                $arn = $entry.Value

                $status = Invoke-AwsCli -Arguments @(
                    "dynamodb", "describe-import",
                    "--import-arn", $arn
                ) -AwsProfile $TargetProfile

                if ($status) {
                    $importStatus = $status.ImportTableDescription.ImportStatus
                    if ($importStatus -eq "COMPLETED") {
                        $importedCount = $status.ImportTableDescription.ProcessedItemCount
                        Write-Success "$tableName import completed `($($importedCount) items`)"
                        $completedThisRound += $tableName
                    }
                    elseif ($importStatus -eq "FAILED" -or $importStatus -eq "CANCELLED") {
                        $failureReason = $status.ImportTableDescription.FailureMessage
                        Write-Err "$tableName import FAILED: $failureReason"
                        exit 1
                    }
                    else {
                        $processedItems = $status.ImportTableDescription.ProcessedItemCount
                        Write-Info "${tableName}: $importStatus `($($processedItems) items processed, elapsed: $([math]::Round($elapsed.TotalMinutes, 1))min`)"
                    }
                }
            }

            foreach ($completed in $completedThisRound) {
                $pendingImports.Remove($completed)
            }
        }

        Write-Success "All table imports completed successfully"
    }
}
else {
    Write-Step "Phase 4: SKIPPED (SkipImport flag set)"
}

# ============================================================================
# Summary
# ============================================================================

$totalTime = (Get-Date) - $startTime

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Migration Complete!" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Duration: $([math]::Round($totalTime.TotalMinutes, 1)) minutes" -ForegroundColor White
Write-Host " Tables:   $($Tables -join ', ')" -ForegroundColor White
Write-Host ""

if ($DryRun) {
    Write-Host " This was a DRY RUN. No changes were made." -ForegroundColor Yellow
    Write-Host " Remove -DryRun to execute the migration." -ForegroundColor Yellow
}
else {
    Write-Host " Next steps:" -ForegroundColor White
    Write-Host "   1. Run the verification script to compare row counts:" -ForegroundColor Gray
    Write-Host "      .\scripts\migration\verify-dynamodb-migration.ps1" -ForegroundColor Gray
    Write-Host "   2. Enable PITR on the new tables in the nonprofit account" -ForegroundColor Gray
    Write-Host "   3. Update application configuration to point to new tables" -ForegroundColor Gray
}

Write-Host ""
