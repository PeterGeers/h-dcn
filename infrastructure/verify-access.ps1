#Requires -Version 5.1
<#
.SYNOPSIS
    Cross-Account Access Verification Script

.DESCRIPTION
    Verifies that all AWS CLI profiles are correctly configured and can assume
    the expected roles in the correct accounts.

    Profiles verified:
      personal         -> Account 344561557829 (personal account)
      nonprofit-dev    -> Account 506221081911, role NonprofitDevRole (MFA required)
      nonprofit-deploy -> Account 506221081911, role NonprofitDeployRole
      nonprofit-admin  -> Account 506221081911, role NonprofitAdminRole (MFA required)

.PARAMETER SkipMfa
    Skip profiles that require MFA (nonprofit-dev, nonprofit-admin)

.EXAMPLE
    .\verify-access.ps1
    Verifies all profiles (will prompt for MFA where required)

.EXAMPLE
    .\verify-access.ps1 -SkipMfa
    Verifies only profiles that do not require MFA
#>

param(
    [switch]$SkipMfa
)

# --- Configuration ---
$PersonalAccountId = "344561557829"
$NonprofitAccountId = "506221081911"

$ProfileChecks = @(
    @{
        Profile       = "personal"
        ExpectedAccount = $PersonalAccountId
        ExpectedRole  = $null
        RequiresMfa   = $false
    },
    @{
        Profile       = "nonprofit-dev"
        ExpectedAccount = $NonprofitAccountId
        ExpectedRole  = "NonprofitDevRole"
        RequiresMfa   = $true
    },
    @{
        Profile       = "nonprofit-deploy"
        ExpectedAccount = $NonprofitAccountId
        ExpectedRole  = "NonprofitDeployRole"
        RequiresMfa   = $false
    },
    @{
        Profile       = "nonprofit-admin"
        ExpectedAccount = $NonprofitAccountId
        ExpectedRole  = "NonprofitAdminRole"
        RequiresMfa   = $true
    }
)

# --- Helper functions ---
function Write-Pass {
    param([string]$Message)
    Write-Host "  PASS " -ForegroundColor Green -NoNewline
    Write-Host $Message
}

function Write-Fail {
    param([string]$Message)
    Write-Host "  FAIL " -ForegroundColor Red -NoNewline
    Write-Host $Message
}

function Write-Skip {
    param([string]$Message)
    Write-Host "  SKIP " -ForegroundColor Yellow -NoNewline
    Write-Host $Message
}

# --- Main verification ---
Write-Host "============================================"
Write-Host " Cross-Account Access Verification"
Write-Host "============================================"
Write-Host ""

$failures = 0
$skipped = 0

foreach ($check in $ProfileChecks) {
    $profile = $check.Profile
    Write-Host "--- Profile: $profile ---"

    # Check if this is an MFA profile and we're skipping
    if ($SkipMfa -and $check.RequiresMfa) {
        Write-Skip "Skipped (requires MFA, run without -SkipMfa to test)"
        $skipped++
        Write-Host ""
        continue
    }

    # Inform user about MFA prompt
    if ($check.RequiresMfa) {
        Write-Host "  Note: This profile requires MFA. You will be prompted for your MFA token."
    }

    # Run get-caller-identity
    try {
        $output = aws sts get-caller-identity --profile $profile --output json 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Fail "Could not get caller identity for profile '$profile'"
            Write-Host "       Error: $output"
            $failures++
            Write-Host ""
            continue
        }
        $identity = $output | ConvertFrom-Json
    }
    catch {
        Write-Fail "Could not get caller identity for profile '$profile'"
        Write-Host "       Error: $_"
        $failures++
        Write-Host ""
        continue
    }

    # Verify account ID
    $actualAccount = $identity.Account
    $expectedAccount = $check.ExpectedAccount

    if ($actualAccount -eq $expectedAccount) {
        Write-Pass "Account ID: $actualAccount (expected: $expectedAccount)"
    }
    else {
        Write-Fail "Account ID: $actualAccount (expected: $expectedAccount)"
        $failures++
    }

    # Verify role ARN (only for nonprofit profiles)
    $expectedRole = $check.ExpectedRole
    $actualArn = $identity.Arn

    if ($null -ne $expectedRole) {
        if ($actualArn -match $expectedRole) {
            Write-Pass "Role ARN contains '$expectedRole': $actualArn"
        }
        else {
            Write-Fail "Role ARN does not contain '$expectedRole': $actualArn"
            $failures++
        }
    }
    else {
        Write-Pass "ARN: $actualArn"
    }

    Write-Host ""
}

# --- Summary ---
Write-Host "============================================"
Write-Host " Summary"
Write-Host "============================================"

$total = $ProfileChecks.Count
$tested = $total - $skipped

if ($failures -eq 0) {
    Write-Host "All $tested tested profile(s) passed." -ForegroundColor Green
    if ($skipped -gt 0) {
        Write-Host "$skipped profile(s) skipped (MFA required)." -ForegroundColor Yellow
    }
    exit 0
}
else {
    Write-Host "$failures check(s) failed out of $tested tested profile(s)." -ForegroundColor Red
    if ($skipped -gt 0) {
        Write-Host "$skipped profile(s) skipped (MFA required)." -ForegroundColor Yellow
    }
    exit 1
}
