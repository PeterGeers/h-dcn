#!/usr/bin/env pwsh
# ============================================================================
# H-DCN Personal Account Cleanup Script
# ============================================================================
# Removes all h-dcn resources from the Personal Account after successful
# migration to the Nonprofit Account. EXPLICITLY EXCLUDES all myAdmin resources.
#
# This script requires confirmation before each destructive action and verifies
# that data exists in the nonprofit account before deleting from personal.
#
# Usage:
#   .\scripts\decommission\cleanup-personal-account.ps1 -DryRun
#   .\scripts\decommission\cleanup-personal-account.ps1
#   .\scripts\decommission\cleanup-personal-account.ps1 -SkipConfirmation
#
# Prerequisites:
#   - AWS CLI v2 configured with personal and nonprofit-deploy profiles
#   - Final backup completed (run backup-personal-account.ps1 first)
#   - Nonprofit account has been running successfully for 7+ days
#   - All users have been migrated to nonprofit Cognito pool
#
# Requirements: 21.2, 21.3, 21.5
# ============================================================================

param(
    [Parameter(Mandatory = $false)]
    [string]$Profile = "personal",

    [Parameter(Mandatory = $false)]
    [string]$NonprofitProfile = "nonprofit-deploy",

    [Parameter(Mandatory = $false)]
    [string]$Region = "eu-west-1",

    [Parameter(Mandatory = $false)]
    [string]$AccountId = "344561557829",

    [Parameter(Mandatory = $false)]
    [string]$NonprofitAccountId = "506221081911",

    [Parameter(Mandatory = $false)]
    [string]$StackName = "h-dcn",

    [Parameter(Mandatory = $false)]
    [string]$S3Bucket = "my-hdcn-bucket",

    [Parameter(Mandatory = $false)]
    [string]$CognitoPoolId = "eu-west-1_OAT3oPCIm",

    [Parameter(Mandatory = $false)]
    [string[]]$Tables = @("Producten", "Members", "Payments", "Events", "Memberships", "Carts", "Orders"),

    [switch]$DryRun,

    [switch]$SkipConfirmation
)

$ErrorActionPreference = "Stop"
$startTime = Get-Date

# ============================================================================
# SAFETY: myAdmin Resource Exclusion List
# ============================================================================
# These resources belong to myAdmin and MUST NEVER be touched.
# If any resource name matches these patterns, it is SKIPPED.

$myAdminPatterns = @(
    "myAdmin*",
    "myadmin*",
    "my-admin*",
    "MyAdmin*",
    "*myAdmin*",
    "*myadmin*"
)

function Test-IsMyAdminResource {
    param([string]$ResourceName)
    foreach ($pattern in $myAdminPatterns) {
        if ($ResourceName -like $pattern) {
            return $true
        }
    }
    return $false
}

# ============================================================================
# Banner
# ============================================================================

Write-Host ""
Write-Host "============================================" -ForegroundColor Red
Write-Host " H-DCN Personal Account CLEANUP" -ForegroundColor Red
Write-Host "============================================" -ForegroundColor Red
Write-Host " Account:          $AccountId ($Profile)" -ForegroundColor White
Write-Host " Stack:            $StackName" -ForegroundColor White
Write-Host " S3 Bucket:        $S3Bucket" -ForegroundColor White
Write-Host " Cognito Pool:     $CognitoPoolId" -ForegroundColor White
Write-Host " Tables:           $($Tables -join ', ')" -ForegroundColor White
Write-Host " Nonprofit Check:  $NonprofitAccountId ($NonprofitProfile)" -ForegroundColor White
Write-Host ""
Write-Host " ⚠️  EXCLUDED: All myAdmin resources" -ForegroundColor Yellow
Write-Host ""
if ($DryRun) {
    Write-Host " Mode:             DRY RUN (no changes)" -ForegroundColor Yellow
}
else {
    Write-Host " Mode:             DESTRUCTIVE - Resources will be DELETED" -ForegroundColor Red
}
Write-Host "============================================" -ForegroundColor Red
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
        [string]$AwsProfile = $Profile,
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

function Confirm-Action {
    param([string]$Message)

    if ($SkipConfirmation -or $DryRun) {
        return $true
    }

    Write-Host ""
    Write-Host "  ⚠️  $Message" -ForegroundColor Yellow
    $response = Read-Host "  Proceed? (yes/no)"
    return ($response -eq "yes")
}

# ============================================================================
# Pre-flight Checks
# ============================================================================

Write-Step "Pre-flight Checks"

# Verify personal account access
Write-Info "Verifying personal account access..."
$personalIdentity = Invoke-AwsCli -Arguments @("sts", "get-caller-identity")
if (-not $personalIdentity -or $personalIdentity.Account -ne $AccountId) {
    Write-Err "Cannot authenticate with personal account"
    exit 1
}
Write-Success "Personal account authenticated: $($personalIdentity.Arn)"

# Verify nonprofit account access
Write-Info "Verifying nonprofit account access..."
$nonprofitIdentity = Invoke-AwsCli -Arguments @("sts", "get-caller-identity") -AwsProfile $NonprofitProfile
if (-not $nonprofitIdentity -or $nonprofitIdentity.Account -ne $NonprofitAccountId) {
    Write-Err "Cannot authenticate with nonprofit account. Required for data verification."
    exit 1
}
Write-Success "Nonprofit account authenticated: $($nonprofitIdentity.Arn)"

# Verify backup exists
Write-Info "Verifying backup bucket exists..."
$backupBucketCheck = Invoke-AwsCli -Arguments @("s3api", "head-bucket", "--bucket", "h-dcn-decommission-backup") -SuppressError
if (-not $backupBucketCheck) {
    Write-Err "Backup bucket 'h-dcn-decommission-backup' not found."
    Write-Err "Run backup-personal-account.ps1 first!"
    exit 1
}
Write-Success "Backup bucket exists"

if ($DryRun) {
    Write-Host ""
    Write-Host "  DRY RUN - Pre-flight checks complete. Showing planned actions." -ForegroundColor Yellow
}

# ============================================================================
# Phase 1: Delete CloudFormation Stack
# ============================================================================

Write-Step "Phase 1: Delete h-dcn CloudFormation Stack"

$stackInfo = Invoke-AwsCli -Arguments @("cloudformation", "describe-stacks", "--stack-name", $StackName) -SuppressError

if ($stackInfo) {
    Write-Info "Stack '$StackName' found. Status: $($stackInfo.Stacks[0].StackStatus)"

    if ($DryRun) {
        Write-Warn "[DRY RUN] Would delete CloudFormation stack: $StackName"
    }
    else {
        if (Confirm-Action "Delete CloudFormation stack '$StackName'? This removes all stack-managed resources.") {
            Write-Info "Deleting stack '$StackName'..."
            Invoke-AwsCli -Arguments @("cloudformation", "delete-stack", "--stack-name", $StackName)

            Write-Info "Waiting for stack deletion to complete..."
            aws cloudformation wait stack-delete-complete --stack-name $StackName --profile $Profile --region $Region 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Success "CloudFormation stack deleted"
            }
            else {
                Write-Err "Stack deletion failed or timed out. Check AWS Console."
                Write-Err "Some resources may need manual deletion (e.g., non-empty S3 buckets)."
            }
        }
        else {
            Write-Warn "Skipped stack deletion"
        }
    }
}
else {
    Write-Info "Stack '$StackName' not found (may already be deleted)"
}

# ============================================================================
# Phase 2: Delete DynamoDB Tables
# ============================================================================

Write-Step "Phase 2: Delete DynamoDB Tables (after verifying data in nonprofit)"

foreach ($table in $Tables) {
    # Safety check: is this a myAdmin resource?
    if (Test-IsMyAdminResource -ResourceName $table) {
        Write-Warn "SKIPPED (myAdmin resource): $table"
        continue
    }

    # Check if table exists in personal account
    $personalTable = Invoke-AwsCli -Arguments @("dynamodb", "describe-table", "--table-name", $table) -SuppressError
    if (-not $personalTable) {
        Write-Info "$table - not found in personal account (already deleted or removed by stack)"
        continue
    }

    $personalCount = $personalTable.Table.ItemCount

    # Verify data exists in nonprofit account
    $nonprofitTable = Invoke-AwsCli -Arguments @("dynamodb", "describe-table", "--table-name", $table) -AwsProfile $NonprofitProfile -SuppressError
    if (-not $nonprofitTable) {
        Write-Err "$table - NOT FOUND in nonprofit account! Skipping deletion."
        continue
    }

    $nonprofitCount = $nonprofitTable.Table.ItemCount
    Write-Info "$table - Personal: $personalCount items, Nonprofit: $nonprofitCount items"

    if ($nonprofitCount -eq 0 -and $personalCount -gt 0) {
        Write-Err "$table - Nonprofit table is EMPTY but personal has $personalCount items. Skipping!"
        continue
    }

    if ($DryRun) {
        Write-Warn "[DRY RUN] Would delete table: $table ($personalCount items)"
    }
    else {
        if (Confirm-Action "Delete DynamoDB table '$table' ($personalCount items)? Data verified in nonprofit ($nonprofitCount items).") {
            Write-Info "Deleting table: $table..."
            $deleteResult = Invoke-AwsCli -Arguments @("dynamodb", "delete-table", "--table-name", $table)
            if ($deleteResult) {
                Write-Success "$table deleted"
            }
            else {
                Write-Err "Failed to delete $table"
            }
        }
        else {
            Write-Warn "Skipped: $table"
        }
    }
}

# ============================================================================
# Phase 3: Empty and Delete S3 Bucket
# ============================================================================

Write-Step "Phase 3: Empty and Delete S3 Bucket"

# Safety check
if (Test-IsMyAdminResource -ResourceName $S3Bucket) {
    Write-Warn "SKIPPED (myAdmin resource): $S3Bucket"
}
else {
    $bucketExists = Invoke-AwsCli -Arguments @("s3api", "head-bucket", "--bucket", $S3Bucket) -SuppressError

    if ($bucketExists) {
        if ($DryRun) {
            Write-Warn "[DRY RUN] Would empty and delete bucket: $S3Bucket"
        }
        else {
            if (Confirm-Action "Empty and delete S3 bucket '$S3Bucket'? All objects will be permanently removed.") {
                Write-Info "Emptying bucket (including versioned objects)..."

                # Delete all object versions
                aws s3api list-object-versions --bucket $S3Bucket --profile $Profile --region $Region --output json | 
                ConvertFrom-Json | ForEach-Object {
                    if ($_.Versions) {
                        foreach ($version in $_.Versions) {
                            aws s3api delete-object --bucket $S3Bucket --key $version.Key --version-id $version.VersionId --profile $Profile --region $Region 2>&1 | Out-Null
                        }
                    }
                    if ($_.DeleteMarkers) {
                        foreach ($marker in $_.DeleteMarkers) {
                            aws s3api delete-object --bucket $S3Bucket --key $marker.Key --version-id $marker.VersionId --profile $Profile --region $Region 2>&1 | Out-Null
                        }
                    }
                }

                # Delete the bucket
                Write-Info "Deleting bucket..."
                aws s3 rb "s3://$S3Bucket" --profile $Profile --region $Region 2>&1
                if ($LASTEXITCODE -eq 0) {
                    Write-Success "S3 bucket deleted: $S3Bucket"
                }
                else {
                    Write-Err "Failed to delete bucket. It may not be empty."
                    Write-Info "Try: aws s3 rb s3://$S3Bucket --force --profile $Profile"
                }
            }
            else {
                Write-Warn "Skipped S3 bucket deletion"
            }
        }
    }
    else {
        Write-Info "Bucket '$S3Bucket' not found (already deleted or removed by stack)"
    }
}

# ============================================================================
# Phase 4: Delete Cognito User Pool
# ============================================================================

Write-Step "Phase 4: Delete Cognito User Pool"

# Safety check
if (Test-IsMyAdminResource -ResourceName $CognitoPoolId) {
    Write-Warn "SKIPPED (myAdmin resource): $CognitoPoolId"
}
else {
    $poolInfo = Invoke-AwsCli -Arguments @("cognito-idp", "describe-user-pool", "--user-pool-id", $CognitoPoolId) -SuppressError

    if ($poolInfo) {
        $userCount = $poolInfo.UserPool.EstimatedNumberOfUsers
        Write-Info "Cognito Pool: $($poolInfo.UserPool.Name) ($userCount estimated users)"

        # Verify users exist in nonprofit pool
        $nonprofitPools = Invoke-AwsCli -Arguments @("cognito-idp", "list-user-pools", "--max-results", "10") -AwsProfile $NonprofitProfile
        $nonprofitHdcnPool = $nonprofitPools.UserPools | Where-Object { $_.Name -match "h-dcn|hdcn" } | Select-Object -First 1

        if ($nonprofitHdcnPool) {
            Write-Info "Nonprofit Cognito Pool found: $($nonprofitHdcnPool.Name)"
        }
        else {
            Write-Warn "No h-dcn Cognito pool found in nonprofit account. Proceed with caution."
        }

        if ($DryRun) {
            Write-Warn "[DRY RUN] Would delete Cognito User Pool: $CognitoPoolId ($userCount users)"
        }
        else {
            if (Confirm-Action "Delete Cognito User Pool '$CognitoPoolId' ($userCount users)? Ensure all users have migrated!") {
                Write-Info "Deleting Cognito User Pool..."

                # Must delete domain first if it exists
                if ($poolInfo.UserPool.Domain) {
                    Write-Info "Removing Cognito domain: $($poolInfo.UserPool.Domain)..."
                    Invoke-AwsCli -Arguments @(
                        "cognito-idp", "delete-user-pool-domain",
                        "--user-pool-id", $CognitoPoolId,
                        "--domain", $poolInfo.UserPool.Domain
                    ) -SuppressError | Out-Null
                }

                $deleteResult = Invoke-AwsCli -Arguments @("cognito-idp", "delete-user-pool", "--user-pool-id", $CognitoPoolId)
                if ($deleteResult) {
                    Write-Success "Cognito User Pool deleted"
                }
                else {
                    Write-Err "Failed to delete Cognito User Pool"
                }
            }
            else {
                Write-Warn "Skipped Cognito deletion"
            }
        }
    }
    else {
        Write-Info "Cognito Pool '$CognitoPoolId' not found (already deleted)"
    }
}

# ============================================================================
# Phase 5: Clean Up Orphaned Resources
# ============================================================================

Write-Step "Phase 5: Clean Up Orphaned Resources"

# --- CloudWatch Log Groups ---
Write-Info "Checking for h-dcn CloudWatch Log Groups..."
$logGroups = Invoke-AwsCli -Arguments @("logs", "describe-log-groups", "--log-group-name-prefix", "/aws/lambda/h-dcn") -SuppressError
if ($logGroups -and $logGroups.logGroups.Count -gt 0) {
    foreach ($lg in $logGroups.logGroups) {
        if (Test-IsMyAdminResource -ResourceName $lg.logGroupName) {
            Write-Warn "SKIPPED (myAdmin): $($lg.logGroupName)"
            continue
        }

        if ($DryRun) {
            Write-Warn "[DRY RUN] Would delete log group: $($lg.logGroupName)"
        }
        else {
            if (Confirm-Action "Delete CloudWatch Log Group: $($lg.logGroupName)?") {
                Invoke-AwsCli -Arguments @("logs", "delete-log-group", "--log-group-name", $lg.logGroupName) | Out-Null
                Write-Success "Deleted: $($lg.logGroupName)"
            }
        }
    }
}
else {
    Write-Info "No h-dcn log groups found"
}

# --- SSM Parameters ---
Write-Info "Checking for h-dcn SSM Parameters..."
$ssmParams = Invoke-AwsCli -Arguments @("ssm", "get-parameters-by-path", "--path", "/h-dcn/", "--recursive") -SuppressError
if ($ssmParams -and $ssmParams.Parameters.Count -gt 0) {
    foreach ($param in $ssmParams.Parameters) {
        if (Test-IsMyAdminResource -ResourceName $param.Name) {
            Write-Warn "SKIPPED (myAdmin): $($param.Name)"
            continue
        }

        if ($DryRun) {
            Write-Warn "[DRY RUN] Would delete SSM parameter: $($param.Name)"
        }
        else {
            if (Confirm-Action "Delete SSM Parameter: $($param.Name)?") {
                Invoke-AwsCli -Arguments @("ssm", "delete-parameter", "--name", $param.Name) | Out-Null
                Write-Success "Deleted: $($param.Name)"
            }
        }
    }
}
else {
    Write-Info "No h-dcn SSM parameters found"
}

# --- IAM Roles (h-dcn prefixed) ---
Write-Info "Checking for h-dcn IAM roles..."
$roles = Invoke-AwsCli -Arguments @("iam", "list-roles") -SuppressError
if ($roles) {
    $hdcnRoles = $roles.Roles | Where-Object { $_.RoleName -match "^h-dcn" -or $_.RoleName -match "^hdcn" }
    foreach ($role in $hdcnRoles) {
        if (Test-IsMyAdminResource -ResourceName $role.RoleName) {
            Write-Warn "SKIPPED (myAdmin): $($role.RoleName)"
            continue
        }

        if ($DryRun) {
            Write-Warn "[DRY RUN] Would delete IAM role: $($role.RoleName)"
        }
        else {
            if (Confirm-Action "Delete IAM Role: $($role.RoleName)?") {
                # Detach all policies first
                $attachedPolicies = Invoke-AwsCli -Arguments @("iam", "list-attached-role-policies", "--role-name", $role.RoleName)
                if ($attachedPolicies) {
                    foreach ($policy in $attachedPolicies.AttachedPolicies) {
                        Invoke-AwsCli -Arguments @("iam", "detach-role-policy", "--role-name", $role.RoleName, "--policy-arn", $policy.PolicyArn) | Out-Null
                    }
                }
                # Delete inline policies
                $inlinePolicies = Invoke-AwsCli -Arguments @("iam", "list-role-policies", "--role-name", $role.RoleName)
                if ($inlinePolicies) {
                    foreach ($policyName in $inlinePolicies.PolicyNames) {
                        Invoke-AwsCli -Arguments @("iam", "delete-role-policy", "--role-name", $role.RoleName, "--policy-name", $policyName) | Out-Null
                    }
                }
                # Delete the role
                Invoke-AwsCli -Arguments @("iam", "delete-role", "--role-name", $role.RoleName) | Out-Null
                Write-Success "Deleted: $($role.RoleName)"
            }
        }
    }
    if (-not $hdcnRoles -or $hdcnRoles.Count -eq 0) {
        Write-Info "No h-dcn IAM roles found"
    }
}

# --- CloudWatch Alarms ---
Write-Info "Checking for h-dcn CloudWatch Alarms..."
$alarms = Invoke-AwsCli -Arguments @("cloudwatch", "describe-alarms", "--alarm-name-prefix", "h-dcn") -SuppressError
if ($alarms -and $alarms.MetricAlarms.Count -gt 0) {
    foreach ($alarm in $alarms.MetricAlarms) {
        if (Test-IsMyAdminResource -ResourceName $alarm.AlarmName) {
            Write-Warn "SKIPPED (myAdmin): $($alarm.AlarmName)"
            continue
        }

        if ($DryRun) {
            Write-Warn "[DRY RUN] Would delete alarm: $($alarm.AlarmName)"
        }
        else {
            if (Confirm-Action "Delete CloudWatch Alarm: $($alarm.AlarmName)?") {
                Invoke-AwsCli -Arguments @("cloudwatch", "delete-alarms", "--alarm-names", $alarm.AlarmName) | Out-Null
                Write-Success "Deleted: $($alarm.AlarmName)"
            }
        }
    }
}
else {
    Write-Info "No h-dcn CloudWatch alarms found"
}

# ============================================================================
# Summary
# ============================================================================

$totalTime = (Get-Date) - $startTime

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Cleanup Complete" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Duration: $([math]::Round($totalTime.TotalMinutes, 1)) minutes" -ForegroundColor White
Write-Host ""

if ($DryRun) {
    Write-Host " This was a DRY RUN. No resources were deleted." -ForegroundColor Yellow
    Write-Host " Remove -DryRun to execute the cleanup." -ForegroundColor Yellow
}
else {
    Write-Host " Resources cleaned up from Personal Account." -ForegroundColor Green
    Write-Host " myAdmin resources were NOT touched." -ForegroundColor Green
    Write-Host ""
    Write-Host " Next step: Run verify-decommission.ps1 to confirm cleanup." -ForegroundColor Gray
}

Write-Host ""
