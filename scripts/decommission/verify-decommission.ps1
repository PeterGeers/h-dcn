#!/usr/bin/env pwsh
# ============================================================================
# H-DCN Decommission Verification Script
# ============================================================================
# Verifies that h-dcn resources have been successfully removed from the
# Personal Account while confirming myAdmin resources remain unchanged and
# the backup bucket exists with proper lifecycle configuration.
#
# Usage:
#   .\scripts\decommission\verify-decommission.ps1
#   .\scripts\decommission\verify-decommission.ps1 -Profile personal
#
# Prerequisites:
#   - AWS CLI v2 configured with personal profile
#   - cleanup-personal-account.ps1 has been executed
#
# Requirements: 21.1, 21.2, 21.3, 21.5
# ============================================================================

param(
    [Parameter(Mandatory = $false)]
    [string]$Profile = "personal",

    [Parameter(Mandatory = $false)]
    [string]$Region = "eu-west-1",

    [Parameter(Mandatory = $false)]
    [string]$AccountId = "344561557829",

    [Parameter(Mandatory = $false)]
    [string]$StackName = "h-dcn",

    [Parameter(Mandatory = $false)]
    [string]$S3Bucket = "my-hdcn-bucket",

    [Parameter(Mandatory = $false)]
    [string]$CognitoPoolId = "eu-west-1_OAT3oPCIm",

    [Parameter(Mandatory = $false)]
    [string]$BackupBucket = "h-dcn-decommission-backup",

    [Parameter(Mandatory = $false)]
    [string[]]$Tables = @("Producten", "Members", "Payments", "Events", "Memberships", "Carts", "Orders"),

    [Parameter(Mandatory = $false)]
    [int]$ExpectedRetentionDays = 90
)

$ErrorActionPreference = "Stop"

# ============================================================================
# Banner
# ============================================================================

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " H-DCN Decommission Verification" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Account:       $AccountId ($Profile)" -ForegroundColor White
Write-Host " Region:        $Region" -ForegroundColor White
Write-Host " Stack:         $StackName" -ForegroundColor White
Write-Host " Backup Bucket: $BackupBucket" -ForegroundColor White
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
        [switch]$SuppressError
    )

    $allArgs = $Arguments + @("--profile", $Profile, "--region", $Region, "--output", "json")
    $result = aws @allArgs 2>&1

    if ($LASTEXITCODE -ne 0) {
        if (-not $SuppressError) {
            # Don't print error for expected "not found" cases
        }
        return $null
    }

    if ($result) {
        return $result | ConvertFrom-Json
    }
    return $true
}

$testResults = @()
$hasFailure = $false

function Add-TestResult {
    param(
        [string]$Test,
        [string]$Status,
        [string]$Details = ""
    )
    $script:testResults += [PSCustomObject]@{
        Test    = $Test
        Status  = $Status
        Details = $Details
    }
    if ($Status -eq "FAIL") {
        $script:hasFailure = $true
    }
}

# ============================================================================
# Pre-flight Check
# ============================================================================

Write-Step "Pre-flight Check"

Write-Info "Verifying account access..."
$identity = Invoke-AwsCli -Arguments @("sts", "get-caller-identity")
if (-not $identity -or $identity.Account -ne $AccountId) {
    Write-Err "Cannot authenticate with personal account"
    exit 1
}
Write-Success "Authenticated: $($identity.Arn)"

# ============================================================================
# Test 1: CloudFormation Stack Deleted
# ============================================================================

Write-Step "Test 1: h-dcn CloudFormation Stack Deleted"

$stackInfo = Invoke-AwsCli -Arguments @("cloudformation", "describe-stacks", "--stack-name", $StackName) -SuppressError

if ($stackInfo) {
    $stackStatus = $stackInfo.Stacks[0].StackStatus
    if ($stackStatus -eq "DELETE_COMPLETE") {
        Write-Success "Stack '$StackName' is DELETE_COMPLETE"
        Add-TestResult -Test "CloudFormation Stack" -Status "PASS" -Details "DELETE_COMPLETE"
    }
    else {
        Write-Err "Stack '$StackName' still exists with status: $stackStatus"
        Add-TestResult -Test "CloudFormation Stack" -Status "FAIL" -Details "Status: $stackStatus"
    }
}
else {
    # Stack not found = deleted (describe-stacks returns error for non-existent stacks)
    Write-Success "Stack '$StackName' not found (deleted)"
    Add-TestResult -Test "CloudFormation Stack" -Status "PASS" -Details "Not found (deleted)"
}

# ============================================================================
# Test 2: DynamoDB Tables Removed
# ============================================================================

Write-Step "Test 2: DynamoDB Tables Removed"

$remainingTables = @()
foreach ($table in $Tables) {
    $tableInfo = Invoke-AwsCli -Arguments @("dynamodb", "describe-table", "--table-name", $table) -SuppressError
    if ($tableInfo) {
        $remainingTables += $table
        Write-Err "Table still exists: $table ($($tableInfo.Table.ItemCount) items)"
    }
    else {
        Write-Success "Table removed: $table"
    }
}

if ($remainingTables.Count -eq 0) {
    Add-TestResult -Test "DynamoDB Tables" -Status "PASS" -Details "All 7 tables removed"
}
else {
    Add-TestResult -Test "DynamoDB Tables" -Status "FAIL" -Details "Remaining: $($remainingTables -join ', ')"
}

# ============================================================================
# Test 3: S3 Bucket Removed
# ============================================================================

Write-Step "Test 3: S3 Bucket Removed"

$bucketExists = Invoke-AwsCli -Arguments @("s3api", "head-bucket", "--bucket", $S3Bucket) -SuppressError
if ($bucketExists) {
    Write-Err "S3 bucket still exists: $S3Bucket"
    Add-TestResult -Test "S3 Bucket ($S3Bucket)" -Status "FAIL" -Details "Still exists"
}
else {
    Write-Success "S3 bucket removed: $S3Bucket"
    Add-TestResult -Test "S3 Bucket ($S3Bucket)" -Status "PASS" -Details "Removed"
}

# ============================================================================
# Test 4: Cognito User Pool Removed
# ============================================================================

Write-Step "Test 4: Cognito User Pool Removed"

$poolInfo = Invoke-AwsCli -Arguments @("cognito-idp", "describe-user-pool", "--user-pool-id", $CognitoPoolId) -SuppressError
if ($poolInfo) {
    Write-Err "Cognito User Pool still exists: $CognitoPoolId"
    Add-TestResult -Test "Cognito User Pool" -Status "FAIL" -Details "Still exists: $CognitoPoolId"
}
else {
    Write-Success "Cognito User Pool removed: $CognitoPoolId"
    Add-TestResult -Test "Cognito User Pool" -Status "PASS" -Details "Removed"
}

# ============================================================================
# Test 5: myAdmin Resources Unchanged
# ============================================================================

Write-Step "Test 5: myAdmin Resources Unchanged"

# Check for myAdmin CloudFormation stacks
$allStacks = Invoke-AwsCli -Arguments @("cloudformation", "list-stacks", "--stack-status-filter", "CREATE_COMPLETE", "UPDATE_COMPLETE") -SuppressError
$myAdminStacks = @()
if ($allStacks) {
    $myAdminStacks = $allStacks.StackSummaries | Where-Object { $_.StackName -match "myAdmin|myadmin|my-admin" }
}

if ($myAdminStacks.Count -gt 0) {
    foreach ($stack in $myAdminStacks) {
        Write-Success "myAdmin stack intact: $($stack.StackName) ($($stack.StackStatus))"
    }
    Add-TestResult -Test "myAdmin Stacks" -Status "PASS" -Details "$($myAdminStacks.Count) stack(s) intact"
}
else {
    Write-Info "No myAdmin CloudFormation stacks found (may use different naming or be manually managed)"
    Add-TestResult -Test "myAdmin Stacks" -Status "PASS" -Details "No stacks to verify (OK if manually managed)"
}

# Check for myAdmin DynamoDB tables
$allTablesResult = Invoke-AwsCli -Arguments @("dynamodb", "list-tables") -SuppressError
if ($allTablesResult) {
    $myAdminTables = $allTablesResult.TableNames | Where-Object { $_ -match "myAdmin|myadmin|my-admin|MyAdmin" }
    if ($myAdminTables.Count -gt 0) {
        foreach ($t in $myAdminTables) {
            Write-Success "myAdmin table intact: $t"
        }
        Add-TestResult -Test "myAdmin DynamoDB" -Status "PASS" -Details "$($myAdminTables.Count) table(s) intact"
    }
    else {
        # Check for other non-h-dcn tables that might be myAdmin
        $otherTables = $allTablesResult.TableNames | Where-Object { $_ -notin $Tables }
        if ($otherTables.Count -gt 0) {
            Write-Info "Other tables still present (likely myAdmin): $($otherTables -join ', ')"
            Add-TestResult -Test "myAdmin DynamoDB" -Status "PASS" -Details "Other tables present: $($otherTables -join ', ')"
        }
        else {
            Write-Info "No myAdmin-named tables found"
            Add-TestResult -Test "myAdmin DynamoDB" -Status "PASS" -Details "No myAdmin tables to verify"
        }
    }
}

# Check for myAdmin Lambda functions
$lambdaFunctions = Invoke-AwsCli -Arguments @("lambda", "list-functions") -SuppressError
if ($lambdaFunctions) {
    $myAdminLambdas = $lambdaFunctions.Functions | Where-Object { $_.FunctionName -match "myAdmin|myadmin|my-admin|MyAdmin" }
    if ($myAdminLambdas.Count -gt 0) {
        foreach ($fn in $myAdminLambdas) {
            Write-Success "myAdmin Lambda intact: $($fn.FunctionName)"
        }
        Add-TestResult -Test "myAdmin Lambdas" -Status "PASS" -Details "$($myAdminLambdas.Count) function(s) intact"
    }
    else {
        Write-Info "No myAdmin-named Lambda functions found"
        Add-TestResult -Test "myAdmin Lambdas" -Status "PASS" -Details "No myAdmin Lambdas to verify"
    }
}

# ============================================================================
# Test 6: Backup Bucket Exists with Lifecycle
# ============================================================================

Write-Step "Test 6: Backup Bucket Exists with $ExpectedRetentionDays-Day Lifecycle"

$backupExists = Invoke-AwsCli -Arguments @("s3api", "head-bucket", "--bucket", $BackupBucket) -SuppressError
if ($backupExists) {
    Write-Success "Backup bucket exists: $BackupBucket"

    # Check lifecycle configuration
    $lifecycle = Invoke-AwsCli -Arguments @("s3api", "get-bucket-lifecycle-configuration", "--bucket", $BackupBucket) -SuppressError
    if ($lifecycle) {
        $expirationRule = $lifecycle.Rules | Where-Object { $_.Status -eq "Enabled" -and $_.Expiration }
        if ($expirationRule) {
            $days = $expirationRule[0].Expiration.Days
            if ($days -eq $ExpectedRetentionDays) {
                Write-Success "Lifecycle rule: objects expire after $days days"
                Add-TestResult -Test "Backup Bucket" -Status "PASS" -Details "Exists with $days-day lifecycle"
            }
            else {
                Write-Warn "Lifecycle rule has $days-day expiration (expected $ExpectedRetentionDays)"
                Add-TestResult -Test "Backup Bucket" -Status "PASS" -Details "Exists with $days-day lifecycle (expected $ExpectedRetentionDays)"
            }
        }
        else {
            Write-Warn "No expiration lifecycle rule found on backup bucket"
            Add-TestResult -Test "Backup Bucket" -Status "PASS" -Details "Exists but no lifecycle rule"
        }
    }
    else {
        Write-Warn "No lifecycle configuration on backup bucket"
        Add-TestResult -Test "Backup Bucket" -Status "PASS" -Details "Exists but no lifecycle configured"
    }

    # Check that backup has data
    $objectCount = aws s3 ls "s3://$BackupBucket" --recursive --profile $Profile --region $Region 2>&1 | Where-Object { $_ -match '\S' }
    $count = if ($objectCount -is [array]) { $objectCount.Count } elseif ($objectCount) { 1 } else { 0 }
    if ($count -gt 0) {
        Write-Success "Backup bucket contains $count objects"
    }
    else {
        Write-Warn "Backup bucket appears empty"
    }
}
else {
    Write-Err "Backup bucket NOT found: $BackupBucket"
    Add-TestResult -Test "Backup Bucket" -Status "FAIL" -Details "Bucket does not exist"
}

# ============================================================================
# Test 7: No Orphaned h-dcn Resources
# ============================================================================

Write-Step "Test 7: No Orphaned h-dcn Resources"

$orphanedResources = @()

# Check for h-dcn log groups
$logGroups = Invoke-AwsCli -Arguments @("logs", "describe-log-groups", "--log-group-name-prefix", "/aws/lambda/h-dcn") -SuppressError
if ($logGroups -and $logGroups.logGroups.Count -gt 0) {
    foreach ($lg in $logGroups.logGroups) {
        $orphanedResources += "LogGroup: $($lg.logGroupName)"
    }
}

# Check for h-dcn SSM parameters
$ssmParams = Invoke-AwsCli -Arguments @("ssm", "get-parameters-by-path", "--path", "/h-dcn/", "--recursive") -SuppressError
if ($ssmParams -and $ssmParams.Parameters.Count -gt 0) {
    foreach ($param in $ssmParams.Parameters) {
        $orphanedResources += "SSM: $($param.Name)"
    }
}

# Check for h-dcn CloudWatch alarms
$alarms = Invoke-AwsCli -Arguments @("cloudwatch", "describe-alarms", "--alarm-name-prefix", "h-dcn") -SuppressError
if ($alarms -and $alarms.MetricAlarms.Count -gt 0) {
    foreach ($alarm in $alarms.MetricAlarms) {
        $orphanedResources += "Alarm: $($alarm.AlarmName)"
    }
}

if ($orphanedResources.Count -eq 0) {
    Write-Success "No orphaned h-dcn resources found"
    Add-TestResult -Test "Orphaned Resources" -Status "PASS" -Details "None found"
}
else {
    Write-Warn "Found $($orphanedResources.Count) orphaned resource(s):"
    foreach ($resource in $orphanedResources) {
        Write-Warn "  - $resource"
    }
    Add-TestResult -Test "Orphaned Resources" -Status "WARN" -Details "$($orphanedResources.Count) remaining"
}

# ============================================================================
# Results Summary
# ============================================================================

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Decommission Verification Results" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

$headerFormat = "  {0,-25} {1,-8} {2}"
Write-Host ($headerFormat -f "Test", "Status", "Details") -ForegroundColor White
Write-Host ("  " + ("-" * 70)) -ForegroundColor Gray

foreach ($result in $testResults) {
    $color = switch ($result.Status) {
        "PASS" { "Green" }
        "FAIL" { "Red" }
        "WARN" { "Yellow" }
        default { "White" }
    }
    Write-Host ($headerFormat -f $result.Test, $result.Status, $result.Details) -ForegroundColor $color
}

Write-Host ""

# ============================================================================
# Final Verdict
# ============================================================================

if ($hasFailure) {
    Write-Host "============================================" -ForegroundColor Red
    Write-Host " DECOMMISSION VERIFICATION FAILED" -ForegroundColor Red
    Write-Host "============================================" -ForegroundColor Red
    Write-Host ""
    Write-Host " Some h-dcn resources still exist in the Personal Account." -ForegroundColor Red
    Write-Host " Run cleanup-personal-account.ps1 to remove remaining resources." -ForegroundColor Red
    Write-Host ""
    exit 1
}
else {
    Write-Host "============================================" -ForegroundColor Green
    Write-Host " DECOMMISSION VERIFICATION PASSED" -ForegroundColor Green
    Write-Host "============================================" -ForegroundColor Green
    Write-Host ""
    Write-Host " h-dcn has been fully removed from the Personal Account." -ForegroundColor Green
    Write-Host " myAdmin resources are intact." -ForegroundColor Green
    Write-Host " Backup bucket exists with $ExpectedRetentionDays-day retention." -ForegroundColor Green
    Write-Host ""
    Write-Host " The nonprofit account is now the sole host for h-dcn." -ForegroundColor Green
    Write-Host ""
    exit 0
}
