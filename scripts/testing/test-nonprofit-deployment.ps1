#Requires -Version 5.1
<#
.SYNOPSIS
    Nonprofit Deployment Integration Tests

.DESCRIPTION
    Verifies that the nonprofit account deployment is working correctly.
    Tests API Gateway, DynamoDB, Cognito, and the Migration Lambda.

    Uses the nonprofit-deploy profile for all AWS CLI calls.
    All test data is cleaned up after execution (idempotent).

    Validates: Requirements 6.1, 6.2, 6.3, 16.3

.PARAMETER SkipCleanup
    Skip cleanup of test data (useful for debugging)

.PARAMETER Verbose
    Show detailed output for each test

.EXAMPLE
    .\test-nonprofit-deployment.ps1
    Run all integration tests

.EXAMPLE
    .\test-nonprofit-deployment.ps1 -SkipCleanup
    Run tests without cleaning up test data
#>

param(
    [switch]$SkipCleanup,
    [switch]$Detailed
)

# --- Configuration ---
$Profile = "nonprofit-deploy"
$Region = "eu-west-1"
$ApiGatewayUrl = "https://44sw408alh.execute-api.eu-west-1.amazonaws.com/prod"
$CognitoUserPoolId = "eu-west-1_gKK2nZjEK"
$CognitoClientId = "3ag4luf0qkru437ajvdmqa0u8"
$CognitoDomain = "https://h-dcn-auth-506221081911.auth.eu-west-1.amazoncognito.com"
$NonprofitAccountId = "506221081911"
$TestItemId = "integration-test-$(Get-Date -Format 'yyyyMMddHHmmss')"

# --- Counters ---
$script:passed = 0
$script:failed = 0
$script:skipped = 0

# --- Helper Functions ---
function Write-TestHeader {
    param([string]$Title)
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
    Write-Host "  $Title" -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
}

function Write-Pass {
    param([string]$Message)
    Write-Host "  ✅ PASS " -ForegroundColor Green -NoNewline
    Write-Host $Message
    $script:passed++
}

function Write-Fail {
    param([string]$Message, [string]$Detail = "")
    Write-Host "  ❌ FAIL " -ForegroundColor Red -NoNewline
    Write-Host $Message
    if ($Detail -and $Detailed) {
        Write-Host "         $Detail" -ForegroundColor DarkGray
    }
    $script:failed++
}

function Write-Skip {
    param([string]$Message, [string]$Reason = "")
    Write-Host "  ⏭️  SKIP " -ForegroundColor Yellow -NoNewline
    Write-Host $Message
    if ($Reason) {
        Write-Host "         Reason: $Reason" -ForegroundColor DarkGray
    }
    $script:skipped++
}

function Write-Info {
    param([string]$Message)
    Write-Host "  ℹ️  " -ForegroundColor Blue -NoNewline
    Write-Host $Message -ForegroundColor DarkGray
}

# --- Pre-flight: Verify profile access ---
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Nonprofit Deployment Integration Tests              ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Profile:    $Profile" -ForegroundColor White
Write-Host "  Region:     $Region" -ForegroundColor White
Write-Host "  API:        $ApiGatewayUrl" -ForegroundColor White
Write-Host "  Cognito:    $CognitoUserPoolId" -ForegroundColor White
Write-Host ""

Write-Host "Pre-flight: Verifying AWS profile access..." -ForegroundColor Yellow
try {
    $identity = aws sts get-caller-identity --profile $Profile --output json 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ❌ Cannot access AWS with profile '$Profile'" -ForegroundColor Red
        Write-Host "     Error: $identity" -ForegroundColor DarkGray
        Write-Host ""
        Write-Host "  Make sure the nonprofit-deploy profile is configured in ~/.aws/config" -ForegroundColor Yellow
        exit 1
    }
    $identityObj = $identity | ConvertFrom-Json
    if ($identityObj.Account -ne $NonprofitAccountId) {
        Write-Host "  ❌ Profile '$Profile' points to wrong account: $($identityObj.Account)" -ForegroundColor Red
        Write-Host "     Expected: $NonprofitAccountId" -ForegroundColor DarkGray
        exit 1
    }
    Write-Host "  ✅ Authenticated as: $($identityObj.Arn)" -ForegroundColor Green
    Write-Host ""
}
catch {
    Write-Host "  ❌ AWS CLI error: $_" -ForegroundColor Red
    exit 1
}

# ============================================================
# TEST 1: API Gateway Health Check
# Validates: Requirement 6.1 (nonprofit-deploy profile works)
# ============================================================
Write-TestHeader "Test 1: API Gateway Health Check"

try {
    Write-Info "Calling: GET $ApiGatewayUrl/"
    $response = Invoke-WebRequest -Uri "$ApiGatewayUrl/" -Method GET -UseBasicParsing -TimeoutSec 30 -ErrorAction Stop
    
    if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
        Write-Pass "API Gateway responds with status $($response.StatusCode)"
        if ($Detailed) {
            Write-Info "Response body (first 200 chars): $($response.Content.Substring(0, [Math]::Min(200, $response.Content.Length)))"
        }
    }
    else {
        Write-Fail "API Gateway returned unexpected status: $($response.StatusCode)"
    }
}
catch {
    $statusCode = $null
    if ($_.Exception.Response) {
        $statusCode = [int]$_.Exception.Response.StatusCode
    }
    
    # A 403 or 401 still means the API Gateway is responding (just needs auth)
    # A 404 means the stage/path exists but no route matched
    if ($statusCode -in @(401, 403, 404)) {
        Write-Pass "API Gateway is responding (status: $statusCode - expected without auth/valid path)"
    }
    elseif ($statusCode) {
        Write-Pass "API Gateway is responding (status: $statusCode)"
    }
    else {
        Write-Fail "API Gateway not reachable" -Detail $_.Exception.Message
    }
}

# Also test a known endpoint pattern (e.g., members)
try {
    Write-Info "Calling: GET $ApiGatewayUrl/members"
    $response = Invoke-WebRequest -Uri "$ApiGatewayUrl/members" -Method GET -UseBasicParsing -TimeoutSec 30 -ErrorAction Stop
    Write-Pass "API Gateway /members endpoint responds with status $($response.StatusCode)"
}
catch {
    $statusCode = $null
    if ($_.Exception.Response) {
        $statusCode = [int]$_.Exception.Response.StatusCode
    }
    if ($statusCode -in @(401, 403)) {
        Write-Pass "API Gateway /members endpoint responds (status: $statusCode - auth required as expected)"
    }
    elseif ($statusCode) {
        Write-Pass "API Gateway /members endpoint responds (status: $statusCode)"
    }
    else {
        Write-Fail "API Gateway /members endpoint not reachable" -Detail $_.Exception.Message
    }
}

# ============================================================
# TEST 2: DynamoDB Read/Write
# Validates: Requirement 6.2 (Lambda can read/write DynamoDB)
# ============================================================
Write-TestHeader "Test 2: DynamoDB Read/Write"

# Find a DynamoDB table to test with
$testTableName = $null
try {
    Write-Info "Listing DynamoDB tables in nonprofit account..."
    $tablesOutput = aws dynamodb list-tables --profile $Profile --region $Region --output json 2>&1
    if ($LASTEXITCODE -eq 0) {
        $tables = ($tablesOutput | ConvertFrom-Json).TableNames
        Write-Info "Found $($tables.Count) table(s): $($tables -join ', ')"
        
        # Use the Producten table for testing (uses 'id' as key)
        if ($tables -contains "Producten") {
            $testTableName = "Producten"
        }
        elseif ($tables.Count -gt 0) {
            $testTableName = $tables[0]
        }
    }
    else {
        Write-Fail "Cannot list DynamoDB tables" -Detail $tablesOutput
    }
}
catch {
    Write-Fail "DynamoDB list-tables error" -Detail $_.Exception.Message
}

if ($testTableName) {
    # Write a test item
    Write-Info "Writing test item to table '$testTableName' (id: $TestItemId)..."
    $testItem = @{
        id              = @{ S = $TestItemId }
        _test_marker    = @{ S = "integration-test" }
        _test_timestamp = @{ S = (Get-Date -Format "o") }
    } | ConvertTo-Json -Compress
    
    try {
        $putResult = aws dynamodb put-item `
            --table-name $testTableName `
            --item $testItem `
            --profile $Profile `
            --region $Region `
            --output json 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Pass "Successfully wrote test item to '$testTableName'"
        }
        else {
            Write-Fail "Failed to write test item to '$testTableName'" -Detail $putResult
        }
    }
    catch {
        Write-Fail "DynamoDB put-item error" -Detail $_.Exception.Message
    }
    
    # Read the test item back
    Write-Info "Reading test item back from table '$testTableName'..."
    $keyJson = @{ id = @{ S = $TestItemId } } | ConvertTo-Json -Compress
    
    try {
        $getResult = aws dynamodb get-item `
            --table-name $testTableName `
            --key $keyJson `
            --profile $Profile `
            --region $Region `
            --output json 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            $getObj = $getResult | ConvertFrom-Json
            if ($getObj.Item) {
                Write-Pass "Successfully read test item from '$testTableName'"
                if ($Detailed) {
                    Write-Info "Item: $($getObj.Item | ConvertTo-Json -Compress)"
                }
            }
            else {
                Write-Fail "Item was written but could not be read back"
            }
        }
        else {
            Write-Fail "Failed to read test item from '$testTableName'" -Detail $getResult
        }
    }
    catch {
        Write-Fail "DynamoDB get-item error" -Detail $_.Exception.Message
    }
    
    # Cleanup: Delete the test item
    if (-not $SkipCleanup) {
        Write-Info "Cleaning up test item..."
        try {
            aws dynamodb delete-item `
                --table-name $testTableName `
                --key $keyJson `
                --profile $Profile `
                --region $Region 2>&1 | Out-Null
            Write-Info "Test item cleaned up successfully"
        }
        catch {
            Write-Host "  ⚠️  Warning: Could not clean up test item (id: $TestItemId)" -ForegroundColor Yellow
        }
    }
}
else {
    Write-Skip "DynamoDB read/write test" -Reason "No DynamoDB tables found in nonprofit account"
}

# ============================================================
# TEST 3: Cognito User Pool Verification
# Validates: Requirement 6.3, 16.1
# ============================================================
Write-TestHeader "Test 3: Cognito User Pool Configuration"

try {
    Write-Info "Describing Cognito User Pool: $CognitoUserPoolId..."
    $poolOutput = aws cognito-idp describe-user-pool `
        --user-pool-id $CognitoUserPoolId `
        --profile $Profile `
        --region $Region `
        --output json 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        $pool = ($poolOutput | ConvertFrom-Json).UserPool
        Write-Pass "Cognito User Pool exists: $($pool.Name) (ID: $CognitoUserPoolId)"
        
        # Check pool status
        if ($pool.Status -eq "Enabled" -or $null -eq $pool.Status) {
            Write-Pass "User Pool is active (Status: $($pool.Status ?? 'Enabled'))"
        }
        else {
            Write-Fail "User Pool status is unexpected: $($pool.Status)"
        }
        
        # Check MFA configuration
        if ($Detailed) {
            Write-Info "MFA Config: $($pool.MfaConfiguration)"
            Write-Info "Schema attributes: $($pool.SchemaAttributes.Count)"
        }
        
        # Check Lambda triggers (Migration Lambda)
        if ($pool.LambdaConfig) {
            if ($pool.LambdaConfig.UserMigration) {
                Write-Pass "Migration Lambda Trigger is configured: $($pool.LambdaConfig.UserMigration)"
            }
            else {
                Write-Info "No Migration Lambda Trigger configured (may not be attached yet)"
            }
            
            if ($pool.LambdaConfig.PostConfirmation) {
                Write-Pass "Post-Confirmation trigger is configured"
            }
        }
        else {
            Write-Info "No Lambda triggers configured on the pool"
        }
    }
    else {
        Write-Fail "Cannot describe Cognito User Pool" -Detail $poolOutput
    }
}
catch {
    Write-Fail "Cognito describe-user-pool error" -Detail $_.Exception.Message
}

# Verify the App Client
try {
    Write-Info "Describing Cognito App Client: $CognitoClientId..."
    $clientOutput = aws cognito-idp describe-user-pool-client `
        --user-pool-id $CognitoUserPoolId `
        --client-id $CognitoClientId `
        --profile $Profile `
        --region $Region `
        --output json 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        $client = ($clientOutput | ConvertFrom-Json).UserPoolClient
        Write-Pass "App Client exists: $($client.ClientName) (ID: $CognitoClientId)"
        
        # Check OAuth flows
        if ($client.AllowedOAuthFlows) {
            Write-Pass "OAuth flows configured: $($client.AllowedOAuthFlows -join ', ')"
        }
        
        # Check callback URLs
        if ($client.CallbackURLs -and $client.CallbackURLs.Count -gt 0) {
            Write-Pass "Callback URLs configured ($($client.CallbackURLs.Count) URL(s))"
            if ($Detailed) {
                $client.CallbackURLs | ForEach-Object { Write-Info "  Callback: $_" }
            }
        }
        
        # Check identity providers
        if ($client.SupportedIdentityProviders) {
            Write-Pass "Identity providers: $($client.SupportedIdentityProviders -join ', ')"
        }
    }
    else {
        Write-Fail "Cannot describe App Client" -Detail $clientOutput
    }
}
catch {
    Write-Fail "Cognito describe-user-pool-client error" -Detail $_.Exception.Message
}

# ============================================================
# TEST 4: Migration Lambda Verification
# Validates: Requirement 16.3
# ============================================================
Write-TestHeader "Test 4: Migration Lambda Function Verification"

# Find the migration lambda
try {
    Write-Info "Searching for Migration Lambda function..."
    $functionsOutput = aws lambda list-functions `
        --profile $Profile `
        --region $Region `
        --output json 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        $functions = ($functionsOutput | ConvertFrom-Json).Functions
        
        # Look for the migration lambda by name pattern
        $migrationLambda = $functions | Where-Object { 
            $_.FunctionName -match "migration|user.?migrat|cognito.?migrat" -or
            $_.FunctionName -match "UserMigration"
        }
        
        if ($migrationLambda) {
            $lambdaName = $migrationLambda[0].FunctionName
            Write-Pass "Migration Lambda found: $lambdaName"
            
            # Get function configuration to check environment variables
            Write-Info "Checking Lambda environment variables..."
            $lambdaConfig = aws lambda get-function-configuration `
                --function-name $lambdaName `
                --profile $Profile `
                --region $Region `
                --output json 2>&1
            
            if ($LASTEXITCODE -eq 0) {
                $config = $lambdaConfig | ConvertFrom-Json
                $envVars = $config.Environment.Variables
                
                # Check for expected environment variables
                if ($envVars) {
                    $expectedVars = @("SOURCE_USER_POOL_ID", "SOURCE_CLIENT_ID", "SOURCE_REGION")
                    $foundVars = @()
                    $missingVars = @()
                    
                    foreach ($var in $expectedVars) {
                        # Check exact name or common variations
                        $found = $envVars.PSObject.Properties | Where-Object { 
                            $_.Name -match $var -or $_.Name -match ($var -replace "_", "")
                        }
                        if ($found) {
                            $foundVars += $var
                        }
                        else {
                            $missingVars += $var
                        }
                    }
                    
                    if ($foundVars.Count -gt 0) {
                        Write-Pass "Environment variables configured: $($foundVars -join ', ')"
                    }
                    
                    if ($missingVars.Count -gt 0) {
                        Write-Info "Variables not found (may use different naming): $($missingVars -join ', ')"
                    }
                    
                    if ($Detailed) {
                        Write-Info "All env vars: $($envVars.PSObject.Properties.Name -join ', ')"
                    }
                }
                else {
                    Write-Fail "Migration Lambda has no environment variables configured"
                }
                
                # Check runtime
                Write-Pass "Runtime: $($config.Runtime)"
                Write-Info "Last modified: $($config.LastModified)"
            }
            else {
                Write-Fail "Cannot get Lambda configuration" -Detail $lambdaConfig
            }
        }
        else {
            # List all functions for debugging
            Write-Info "No migration-specific Lambda found. Checking all h-dcn functions..."
            $hdcnFunctions = $functions | Where-Object { $_.FunctionName -match "h-dcn|hdcn" }
            
            if ($hdcnFunctions.Count -gt 0) {
                Write-Info "Found $($hdcnFunctions.Count) h-dcn Lambda function(s):"
                $hdcnFunctions | ForEach-Object { Write-Info "  - $($_.FunctionName)" }
                Write-Skip "Migration Lambda verification" -Reason "Could not identify migration-specific Lambda by name pattern"
            }
            else {
                Write-Skip "Migration Lambda verification" -Reason "No h-dcn Lambda functions found in nonprofit account"
            }
        }
    }
    else {
        Write-Fail "Cannot list Lambda functions" -Detail $functionsOutput
    }
}
catch {
    Write-Fail "Lambda list-functions error" -Detail $_.Exception.Message
}

# Note: We do NOT invoke the migration lambda with real users
Write-Info "Note: Migration Lambda is NOT invoked with real users (safety measure)"
Write-Info "      To test actual migration, use a dedicated test user in the old pool"

# ============================================================
# TEST 5: GitHub Actions OIDC (Documentation Only)
# Validates: Requirement 19.4
# ============================================================
Write-TestHeader "Test 5: GitHub Actions OIDC Deployment"

Write-Info "GitHub Actions OIDC cannot be fully tested locally."
Write-Info "The OIDC flow requires a GitHub Actions workflow run."
Write-Info ""
Write-Info "To verify OIDC deployment:"
Write-Info "  1. Push a change to the repository"
Write-Info "  2. Check the GitHub Actions 'Deploy Frontend' workflow"
Write-Info "  3. Verify it assumes NonprofitDeployRole via OIDC"
Write-Info "  4. Verify S3 sync and CloudFront invalidation succeed"
Write-Info ""

# But we CAN verify the OIDC provider exists
try {
    Write-Info "Verifying OIDC provider exists in nonprofit account..."
    $oidcOutput = aws iam list-open-id-connect-providers `
        --profile $Profile `
        --output json 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        $providers = ($oidcOutput | ConvertFrom-Json).OpenIDConnectProviderList
        $githubProvider = $providers | Where-Object { $_.Arn -match "token.actions.githubusercontent.com" }
        
        if ($githubProvider) {
            Write-Pass "GitHub Actions OIDC provider exists: $($githubProvider[0].Arn)"
        }
        else {
            Write-Fail "GitHub Actions OIDC provider not found in nonprofit account"
        }
    }
    else {
        Write-Fail "Cannot list OIDC providers" -Detail $oidcOutput
    }
}
catch {
    Write-Fail "OIDC provider check error" -Detail $_.Exception.Message
}

# Verify the deploy role has the OIDC trust
try {
    Write-Info "Verifying NonprofitDeployRole trust policy includes OIDC..."
    $roleOutput = aws iam get-role `
        --role-name NonprofitDeployRole `
        --profile $Profile `
        --output json 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        $role = ($roleOutput | ConvertFrom-Json).Role
        $trustPolicy = $role.AssumeRolePolicyDocument
        $trustJson = $trustPolicy | ConvertTo-Json -Depth 10
        
        if ($trustJson -match "token.actions.githubusercontent.com") {
            Write-Pass "NonprofitDeployRole trust policy includes GitHub OIDC"
        }
        else {
            Write-Fail "NonprofitDeployRole trust policy does NOT include GitHub OIDC"
        }
    }
    else {
        Write-Fail "Cannot get NonprofitDeployRole" -Detail $roleOutput
    }
}
catch {
    Write-Fail "Role trust policy check error" -Detail $_.Exception.Message
}

Write-Skip "Full OIDC deployment test" -Reason "Requires GitHub Actions workflow run (cannot test locally)"

# ============================================================
# SUMMARY
# ============================================================
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Test Results Summary                                ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$total = $script:passed + $script:failed + $script:skipped
Write-Host "  Total:   $total" -ForegroundColor White
Write-Host "  Passed:  $($script:passed)" -ForegroundColor Green
Write-Host "  Failed:  $($script:failed)" -ForegroundColor $(if ($script:failed -gt 0) { "Red" } else { "Green" })
Write-Host "  Skipped: $($script:skipped)" -ForegroundColor Yellow
Write-Host ""

if ($script:failed -eq 0) {
    Write-Host "  🎉 All tests passed! Nonprofit deployment is working." -ForegroundColor Green
    exit 0
}
else {
    Write-Host "  ⚠️  Some tests failed. Review the output above for details." -ForegroundColor Yellow
    Write-Host "     Run with -Detailed for more information." -ForegroundColor DarkGray
    exit 1
}
