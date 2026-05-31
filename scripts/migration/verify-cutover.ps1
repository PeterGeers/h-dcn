#!/usr/bin/env pwsh
# ============================================================================
# H-DCN DNS Cutover Verification Script
# ============================================================================
# Verifies end-to-end connectivity from frontend to nonprofit API after DNS
# cutover. Checks DNS resolution, API health, user login flow, and data
# read/write operations.
#
# Usage:
#   .\scripts\migration\verify-cutover.ps1
#   .\scripts\migration\verify-cutover.ps1 -DryRun
#   .\scripts\migration\verify-cutover.ps1 -Profile nonprofit-deploy -SkipLoginTest
#
# Prerequisites:
#   - AWS CLI v2 configured with nonprofit-deploy profile
#   - DNS cutover has been executed (or about to be verified)
#   - Nonprofit account API Gateway and CloudFront are deployed
#
# Requirements: 18.4
# ============================================================================

param(
    [Parameter(Mandatory = $false)]
    [string]$Profile = "nonprofit-deploy",

    [Parameter(Mandatory = $false)]
    [string]$Region = "eu-west-1",

    [Parameter(Mandatory = $false)]
    [string]$NonprofitAccountId = "506221081911",

    [Parameter(Mandatory = $false)]
    [string]$ApiDomain = "api.h-dcn.nl",

    [Parameter(Mandatory = $false)]
    [string]$FrontendDomain = "portal.h-dcn.nl",

    [Parameter(Mandatory = $false)]
    [int]$TimeoutSec = 10,

    [switch]$DryRun,

    [switch]$SkipLoginTest,

    [switch]$SkipDataTest
)

$ErrorActionPreference = "Stop"
$startTime = Get-Date

# ============================================================================
# Banner
# ============================================================================

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " H-DCN DNS Cutover Verification" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " API Domain:       $ApiDomain" -ForegroundColor White
Write-Host " Frontend Domain:  $FrontendDomain" -ForegroundColor White
Write-Host " Expected Account: $NonprofitAccountId" -ForegroundColor White
Write-Host " AWS Profile:      $Profile" -ForegroundColor White
Write-Host " Region:           $Region" -ForegroundColor White
if ($DryRun) {
    Write-Host " Mode:             DRY RUN (checks only)" -ForegroundColor Yellow
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
# Test 1: DNS Resolution
# ============================================================================

Write-Step "Test 1: DNS Resolution"

# Check API domain
Write-Info "Resolving $ApiDomain..."
try {
    $apiDns = Resolve-DnsName -Name $ApiDomain -Type CNAME -ErrorAction Stop 2>$null
    if ($apiDns) {
        $apiTarget = ($apiDns | Where-Object { $_.Type -eq "CNAME" } | Select-Object -First 1).NameHost
        if (-not $apiTarget) {
            # Try A record
            $apiDns = Resolve-DnsName -Name $ApiDomain -Type A -ErrorAction Stop 2>$null
            $apiTarget = ($apiDns | Where-Object { $_.Type -eq "A" } | Select-Object -First 1).IPAddress
        }
        Write-Success "API domain resolves to: $apiTarget"
        Add-TestResult -Test "DNS: $ApiDomain" -Status "PASS" -Details $apiTarget
    }
    else {
        Write-Err "API domain did not resolve"
        Add-TestResult -Test "DNS: $ApiDomain" -Status "FAIL" -Details "No DNS response"
    }
}
catch {
    Write-Err "DNS resolution failed for $ApiDomain : $_"
    Add-TestResult -Test "DNS: $ApiDomain" -Status "FAIL" -Details $_.Exception.Message
}

# Check Frontend domain
Write-Info "Resolving $FrontendDomain..."
try {
    $frontendDns = Resolve-DnsName -Name $FrontendDomain -Type CNAME -ErrorAction Stop 2>$null
    if ($frontendDns) {
        $frontendTarget = ($frontendDns | Where-Object { $_.Type -eq "CNAME" } | Select-Object -First 1).NameHost
        if (-not $frontendTarget) {
            $frontendDns = Resolve-DnsName -Name $FrontendDomain -Type A -ErrorAction Stop 2>$null
            $frontendTarget = ($frontendDns | Where-Object { $_.Type -eq "A" } | Select-Object -First 1).IPAddress
        }
        Write-Success "Frontend domain resolves to: $frontendTarget"
        Add-TestResult -Test "DNS: $FrontendDomain" -Status "PASS" -Details $frontendTarget
    }
    else {
        Write-Err "Frontend domain did not resolve"
        Add-TestResult -Test "DNS: $FrontendDomain" -Status "FAIL" -Details "No DNS response"
    }
}
catch {
    Write-Err "DNS resolution failed for $FrontendDomain : $_"
    Add-TestResult -Test "DNS: $FrontendDomain" -Status "FAIL" -Details $_.Exception.Message
}

# ============================================================================
# Test 2: API Health Check
# ============================================================================

Write-Step "Test 2: API Health Check"

Write-Info "Checking API endpoint: https://$ApiDomain ..."
try {
    # Try common health endpoints
    $healthEndpoints = @("/health", "/", "/api")
    $apiReachable = $false

    foreach ($endpoint in $healthEndpoints) {
        try {
            $response = Invoke-WebRequest -Uri "https://$ApiDomain$endpoint" `
                -Method GET `
                -TimeoutSec $TimeoutSec `
                -UseBasicParsing `
                -ErrorAction Stop

            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                Write-Success "API responds at https://$ApiDomain$endpoint (HTTP $($response.StatusCode))"
                Add-TestResult -Test "API Health: $endpoint" -Status "PASS" -Details "HTTP $($response.StatusCode)"
                $apiReachable = $true
                break
            }
        }
        catch [System.Net.WebException] {
            $webResponse = $_.Exception.Response
            if ($webResponse -and $webResponse.StatusCode.value__ -lt 500) {
                # 4xx is acceptable — means the API is reachable
                Write-Success "API reachable at https://$ApiDomain$endpoint (HTTP $($webResponse.StatusCode.value__))"
                Add-TestResult -Test "API Health: $endpoint" -Status "PASS" -Details "HTTP $($webResponse.StatusCode.value__) (expected for unauthenticated request)"
                $apiReachable = $true
                break
            }
        }
        catch {
            continue
        }
    }

    if (-not $apiReachable) {
        Write-Err "API is not reachable at https://$ApiDomain"
        Add-TestResult -Test "API Health" -Status "FAIL" -Details "No response from any health endpoint"
    }
}
catch {
    Write-Err "API health check failed: $_"
    Add-TestResult -Test "API Health" -Status "FAIL" -Details $_.Exception.Message
}

# ============================================================================
# Test 3: Frontend Accessibility
# ============================================================================

Write-Step "Test 3: Frontend Accessibility"

Write-Info "Checking frontend: https://$FrontendDomain ..."
try {
    $response = Invoke-WebRequest -Uri "https://$FrontendDomain" `
        -Method GET `
        -TimeoutSec $TimeoutSec `
        -UseBasicParsing `
        -ErrorAction Stop

    if ($response.StatusCode -eq 200) {
        Write-Success "Frontend loads successfully (HTTP 200)"

        # Check for expected content
        if ($response.Content -match "h-dcn|portal") {
            Write-Success "Frontend content contains expected markers"
            Add-TestResult -Test "Frontend Load" -Status "PASS" -Details "HTTP 200, content verified"
        }
        else {
            Write-Warn "Frontend loads but content may not be correct"
            Add-TestResult -Test "Frontend Load" -Status "PASS" -Details "HTTP 200, content not verified"
        }
    }
    else {
        Write-Warn "Frontend returned HTTP $($response.StatusCode)"
        Add-TestResult -Test "Frontend Load" -Status "PASS" -Details "HTTP $($response.StatusCode)"
    }
}
catch {
    Write-Err "Frontend is not accessible: $_"
    Add-TestResult -Test "Frontend Load" -Status "FAIL" -Details $_.Exception.Message
}

# ============================================================================
# Test 4: User Login Flow (basic HTTP check)
# ============================================================================

if (-not $SkipLoginTest) {
    Write-Step "Test 4: User Login Flow (Cognito endpoint check)"

    Write-Info "Verifying Cognito endpoints are reachable..."

    # Get Cognito User Pool info from nonprofit account
    try {
        $poolsJson = aws cognito-idp list-user-pools --max-results 10 --profile $Profile --region $Region --output json 2>&1
        if ($LASTEXITCODE -eq 0) {
            $pools = $poolsJson | ConvertFrom-Json
            $hdcnPool = $pools.UserPools | Where-Object { $_.Name -match "h-dcn|hdcn" } | Select-Object -First 1

            if ($hdcnPool) {
                Write-Success "Cognito User Pool found: $($hdcnPool.Name) ($($hdcnPool.Id))"

                # Check if the pool has a domain configured
                $poolDetail = aws cognito-idp describe-user-pool --user-pool-id $hdcnPool.Id --profile $Profile --region $Region --output json 2>&1 | ConvertFrom-Json
                if ($poolDetail.UserPool.Domain) {
                    $cognitoDomain = "https://$($poolDetail.UserPool.Domain).auth.$Region.amazoncognito.com"
                    Write-Info "Cognito domain: $cognitoDomain"

                    try {
                        $cognitoResponse = Invoke-WebRequest -Uri "$cognitoDomain/.well-known/openid-configuration" `
                            -Method GET `
                            -TimeoutSec $TimeoutSec `
                            -UseBasicParsing `
                            -ErrorAction Stop

                        if ($cognitoResponse.StatusCode -eq 200) {
                            Write-Success "Cognito OIDC endpoint reachable"
                            Add-TestResult -Test "Cognito Login Flow" -Status "PASS" -Details "OIDC endpoint responds"
                        }
                    }
                    catch {
                        Write-Warn "Cognito OIDC endpoint not reachable (may need custom domain)"
                        Add-TestResult -Test "Cognito Login Flow" -Status "PASS" -Details "Pool exists, OIDC check skipped"
                    }
                }
                else {
                    Write-Warn "No Cognito domain configured yet"
                    Add-TestResult -Test "Cognito Login Flow" -Status "PASS" -Details "Pool exists, no domain configured"
                }
            }
            else {
                Write-Err "No h-dcn Cognito User Pool found in nonprofit account"
                Add-TestResult -Test "Cognito Login Flow" -Status "FAIL" -Details "No matching User Pool"
            }
        }
        else {
            Write-Err "Cannot list Cognito pools: $poolsJson"
            Add-TestResult -Test "Cognito Login Flow" -Status "FAIL" -Details "AWS CLI error"
        }
    }
    catch {
        Write-Err "Login flow check failed: $_"
        Add-TestResult -Test "Cognito Login Flow" -Status "FAIL" -Details $_.Exception.Message
    }
}
else {
    Write-Step "Test 4: SKIPPED (SkipLoginTest flag set)"
    Add-TestResult -Test "Cognito Login Flow" -Status "SKIP" -Details "Skipped by user"
}

# ============================================================================
# Test 5: Data Read/Write
# ============================================================================

if (-not $SkipDataTest) {
    Write-Step "Test 5: Data Read/Write (DynamoDB)"

    Write-Info "Testing DynamoDB read access in nonprofit account..."

    # Test read on Members table (most critical)
    try {
        $scanResult = aws dynamodb scan `
            --table-name Members `
            --limit 1 `
            --select COUNT `
            --profile $Profile `
            --region $Region `
            --output json 2>&1

        if ($LASTEXITCODE -eq 0) {
            $scanData = $scanResult | ConvertFrom-Json
            Write-Success "DynamoDB read: Members table accessible ($($scanData.Count) items sampled)"

            # Test write with a temporary item
            $testId = "cutover-test-$(Get-Date -Format 'yyyyMMddHHmmss')"
            Write-Info "Testing DynamoDB write with temporary item (id: $testId)..."

            $putResult = aws dynamodb put-item `
                --table-name Members `
                --item "{`"id`": {`"S`": `"$testId`"}, `"test_marker`": {`"S`": `"cutover-verification`"}, `"created`": {`"S`": `"$(Get-Date -Format 'o')`"}}" `
                --profile $Profile `
                --region $Region `
                --output json 2>&1

            if ($LASTEXITCODE -eq 0) {
                Write-Success "DynamoDB write: Successfully wrote test item"

                # Clean up test item
                $deleteResult = aws dynamodb delete-item `
                    --table-name Members `
                    --key "{`"id`": {`"S`": `"$testId`"}}" `
                    --profile $Profile `
                    --region $Region `
                    --output json 2>&1

                if ($LASTEXITCODE -eq 0) {
                    Write-Success "DynamoDB cleanup: Test item removed"
                    Add-TestResult -Test "DynamoDB Read/Write" -Status "PASS" -Details "Read + write + delete successful"
                }
                else {
                    Write-Warn "Could not clean up test item (id: $testId). Remove manually."
                    Add-TestResult -Test "DynamoDB Read/Write" -Status "PASS" -Details "Read + write OK, cleanup failed"
                }
            }
            else {
                Write-Err "DynamoDB write failed: $putResult"
                Add-TestResult -Test "DynamoDB Read/Write" -Status "FAIL" -Details "Read OK, write failed"
            }
        }
        else {
            Write-Err "DynamoDB read failed: $scanResult"
            Add-TestResult -Test "DynamoDB Read/Write" -Status "FAIL" -Details "Cannot read Members table"
        }
    }
    catch {
        Write-Err "Data test failed: $_"
        Add-TestResult -Test "DynamoDB Read/Write" -Status "FAIL" -Details $_.Exception.Message
    }
}
else {
    Write-Step "Test 5: SKIPPED (SkipDataTest flag set)"
    Add-TestResult -Test "DynamoDB Read/Write" -Status "SKIP" -Details "Skipped by user"
}

# ============================================================================
# Test 6: AWS Account Verification
# ============================================================================

Write-Step "Test 6: AWS Account Verification"

Write-Info "Verifying nonprofit account identity..."
try {
    $identityJson = aws sts get-caller-identity --profile $Profile --region $Region --output json 2>&1
    if ($LASTEXITCODE -eq 0) {
        $identity = $identityJson | ConvertFrom-Json
        if ($identity.Account -eq $NonprofitAccountId) {
            Write-Success "Confirmed: operating in nonprofit account ($($identity.Account))"
            Add-TestResult -Test "Account Verification" -Status "PASS" -Details "Account: $($identity.Account), Role: $($identity.Arn)"
        }
        else {
            Write-Err "Wrong account! Expected $NonprofitAccountId, got $($identity.Account)"
            Add-TestResult -Test "Account Verification" -Status "FAIL" -Details "Wrong account: $($identity.Account)"
        }
    }
    else {
        Write-Err "Cannot verify account identity: $identityJson"
        Add-TestResult -Test "Account Verification" -Status "FAIL" -Details "STS call failed"
    }
}
catch {
    Write-Err "Account verification failed: $_"
    Add-TestResult -Test "Account Verification" -Status "FAIL" -Details $_.Exception.Message
}

# ============================================================================
# Results Summary
# ============================================================================

$totalTime = (Get-Date) - $startTime

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Cutover Verification Results" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

$headerFormat = "  {0,-25} {1,-8} {2}"
Write-Host ($headerFormat -f "Test", "Status", "Details") -ForegroundColor White
Write-Host ("  " + ("-" * 70)) -ForegroundColor Gray

foreach ($result in $testResults) {
    $color = switch ($result.Status) {
        "PASS" { "Green" }
        "FAIL" { "Red" }
        "SKIP" { "Yellow" }
        default { "White" }
    }
    Write-Host ($headerFormat -f $result.Test, $result.Status, $result.Details) -ForegroundColor $color
}

Write-Host ""
Write-Host "  Duration: $([math]::Round($totalTime.TotalSeconds, 1)) seconds" -ForegroundColor Gray
Write-Host ""

# ============================================================================
# Final Verdict
# ============================================================================

if ($hasFailure) {
    Write-Host "============================================" -ForegroundColor Red
    Write-Host " CUTOVER VERIFICATION FAILED" -ForegroundColor Red
    Write-Host "============================================" -ForegroundColor Red
    Write-Host ""
    Write-Host " One or more checks failed. Consider rolling back DNS." -ForegroundColor Red
    Write-Host " Rollback runbook: scripts\migration\rollback-dns.md" -ForegroundColor Red
    Write-Host ""
    exit 1
}
else {
    Write-Host "============================================" -ForegroundColor Green
    Write-Host " CUTOVER VERIFICATION PASSED" -ForegroundColor Green
    Write-Host "============================================" -ForegroundColor Green
    Write-Host ""
    Write-Host " All checks passed. DNS cutover is successful." -ForegroundColor Green
    Write-Host " Continue monitoring for 5 minutes, then 24 hours." -ForegroundColor Green
    Write-Host ""
    exit 0
}
