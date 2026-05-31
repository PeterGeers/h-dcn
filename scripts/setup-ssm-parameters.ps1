# ============================================================================
# H-DCN SSM Parameter Store Setup Script
# ============================================================================
# This script creates the required SSM parameters in AWS Parameter Store
# for the h-dcn application. Run this BEFORE deploying the SAM stack.
#
# Convention: /h-dcn/{environment}/{service}/{key-name}
#
# Usage:
#   .\scripts\setup-ssm-parameters.ps1 -Environment dev -Profile nonprofit-deploy
#   .\scripts\setup-ssm-parameters.ps1 -Environment prod -Profile nonprofit-deploy
#
# Prerequisites:
#   - AWS CLI configured with appropriate profile
#   - Sufficient IAM permissions (ssm:PutParameter)
#   - Actual secret values ready (Google OAuth credentials, Mollie API key, etc.)
#
# Requirements: 9.1, 9.2, 9.3, 9.4, 9.5
# ============================================================================

param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("dev", "test", "prod")]
    [string]$Environment,

    [Parameter(Mandatory = $false)]
    [string]$Profile = "nonprofit-deploy",

    [Parameter(Mandatory = $false)]
    [string]$Region = "eu-west-1",

    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host " H-DCN SSM Parameter Store Setup" -ForegroundColor Cyan
Write-Host " Environment: $Environment" -ForegroundColor Cyan
Write-Host " Profile:     $Profile" -ForegroundColor Cyan
Write-Host " Region:      $Region" -ForegroundColor Cyan
if ($DryRun) {
    Write-Host " Mode:        DRY RUN (no changes)" -ForegroundColor Yellow
}
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# Parameter Definitions
# ============================================================================
# Each parameter follows the convention: /h-dcn/{environment}/{service}/{key-name}
#
# Types:
#   - String:       Non-sensitive configuration values
#   - SecureString: Sensitive values (API keys, secrets) encrypted with AWS KMS
# ============================================================================

$parameters = @(
    # --- Mollie Payment API ---
    @{
        Name        = "/h-dcn/$Environment/mollie/api-key"
        Type        = "SecureString"
        Description = "Mollie payment API key for $Environment environment"
        PromptText  = "Enter Mollie API key (e.g., test_xxx or live_xxx)"
    },

    # --- Cognito Configuration ---
    # NOTE: Uses String type (not SecureString) because CloudFormation does not
    # support {{resolve:ssm-secure:...}} in Lambda environment variables.
    @{
        Name        = "/h-dcn/$Environment/cognito/default-temp-password"
        Type        = "String"
        Description = "Default temporary password for new Cognito users in $Environment"
        PromptText  = "Enter default temporary password for new Cognito users"
    },

    # --- Google OAuth Configuration (SSM Parameters) ---
    # NOTE: client-id and client-secret use String type (not SecureString) because
    # CloudFormation does not support {{resolve:ssm-secure:...}} in Cognito
    # UserPoolIdentityProvider ProviderDetails or Lambda environment variables.
    @{
        Name        = "/h-dcn/$Environment/google/client-id"
        Type        = "String"
        Description = "Google OAuth 2.0 Client ID for $Environment environment"
        PromptText  = "Enter Google OAuth Client ID (e.g., xxx.apps.googleusercontent.com)"
    },
    @{
        Name        = "/h-dcn/$Environment/google/client-secret"
        Type        = "String"
        Description = "Google OAuth 2.0 Client Secret for $Environment environment"
        PromptText  = "Enter Google OAuth Client Secret"
    }
)

# ============================================================================
# Secrets Manager Entries (for structured JSON secrets)
# ============================================================================
# Google credentials are also stored in Secrets Manager as a JSON bundle
# for use cases that need the full credential set (e.g., service accounts).
# ============================================================================

$secretsManagerEntries = @(
    @{
        Name        = "h-dcn/$Environment/google-credentials"
        Description = "Google Workspace OAuth credentials (JSON) for $Environment"
        PromptText  = "Enter Google credentials JSON (or press Enter to skip)"
        Template    = @{
            client_id     = ""
            client_secret = ""
            project_id    = ""
        }
    }
)

# ============================================================================
# Helper Functions
# ============================================================================

function Test-ParameterExists {
    param([string]$ParameterName, [string]$AwsProfile, [string]$AwsRegion)
    
    try {
        aws ssm get-parameter --name $ParameterName --profile $AwsProfile --region $AwsRegion 2>$null | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

function Set-SSMParameter {
    param(
        [string]$Name,
        [string]$Value,
        [string]$Type,
        [string]$Description,
        [string]$AwsProfile,
        [string]$AwsRegion,
        [bool]$IsDryRun
    )

    if ($IsDryRun) {
        Write-Host "  [DRY RUN] Would create: $Name ($Type)" -ForegroundColor Yellow
        return
    }

    $exists = Test-ParameterExists -ParameterName $Name -AwsProfile $AwsProfile -AwsRegion $AwsRegion

    $args = @(
        "ssm", "put-parameter",
        "--name", $Name,
        "--value", $Value,
        "--type", $Type,
        "--description", $Description,
        "--profile", $AwsProfile,
        "--region", $AwsRegion,
        "--tags", "Key=Project,Value=h-dcn", "Key=Environment,Value=$Environment", "Key=ManagedBy,Value=manual"
    )

    if ($exists) {
        $args += "--overwrite"
        Write-Host "  [UPDATE] $Name" -ForegroundColor Yellow
    }
    else {
        Write-Host "  [CREATE] $Name" -ForegroundColor Green
    }

    aws @args
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  [ERROR] Failed to set parameter: $Name" -ForegroundColor Red
        return
    }
}

function Set-SecretsManagerSecret {
    param(
        [string]$Name,
        [string]$Value,
        [string]$Description,
        [string]$AwsProfile,
        [string]$AwsRegion,
        [bool]$IsDryRun
    )

    if ($IsDryRun) {
        Write-Host "  [DRY RUN] Would create secret: $Name" -ForegroundColor Yellow
        return
    }

    # Check if secret exists
    $secretExists = $false
    try {
        aws secretsmanager describe-secret --secret-id $Name --profile $AwsProfile --region $AwsRegion 2>$null | Out-Null
        $secretExists = $true
    }
    catch { }

    if ($secretExists) {
        Write-Host "  [UPDATE] Secret: $Name" -ForegroundColor Yellow
        aws secretsmanager put-secret-value `
            --secret-id $Name `
            --secret-string $Value `
            --profile $AwsProfile `
            --region $AwsRegion
    }
    else {
        Write-Host "  [CREATE] Secret: $Name" -ForegroundColor Green
        aws secretsmanager create-secret `
            --name $Name `
            --description $Description `
            --secret-string $Value `
            --tags "Key=Project,Value=h-dcn" "Key=Environment,Value=$Environment" "Key=ManagedBy,Value=manual" `
            --profile $AwsProfile `
            --region $AwsRegion
    }

    if ($LASTEXITCODE -ne 0) {
        Write-Host "  [ERROR] Failed to set secret: $Name" -ForegroundColor Red
    }
}

# ============================================================================
# Main Execution
# ============================================================================

Write-Host "--- SSM Parameter Store Parameters ---" -ForegroundColor White
Write-Host ""

foreach ($param in $parameters) {
    Write-Host "Parameter: $($param.Name)" -ForegroundColor White
    Write-Host "  Type:        $($param.Type)" -ForegroundColor Gray
    Write-Host "  Description: $($param.Description)" -ForegroundColor Gray

    if ($DryRun) {
        Write-Host "  [DRY RUN] Skipping value prompt" -ForegroundColor Yellow
        Write-Host ""
        continue
    }

    # Prompt for value
    $value = Read-Host "  $($param.PromptText)"
    if ([string]::IsNullOrWhiteSpace($value)) {
        Write-Host "  [SKIP] No value provided, skipping." -ForegroundColor DarkYellow
        Write-Host ""
        continue
    }

    Set-SSMParameter `
        -Name $param.Name `
        -Value $value `
        -Type $param.Type `
        -Description $param.Description `
        -AwsProfile $Profile `
        -AwsRegion $Region `
        -IsDryRun $false

    Write-Host ""
}

Write-Host ""
Write-Host "--- Secrets Manager Entries ---" -ForegroundColor White
Write-Host ""

foreach ($secret in $secretsManagerEntries) {
    Write-Host "Secret: $($secret.Name)" -ForegroundColor White
    Write-Host "  Description: $($secret.Description)" -ForegroundColor Gray

    if ($DryRun) {
        Write-Host "  [DRY RUN] Skipping value prompt" -ForegroundColor Yellow
        Write-Host ""
        continue
    }

    $value = Read-Host "  $($secret.PromptText)"
    if ([string]::IsNullOrWhiteSpace($value)) {
        # If no raw JSON provided, prompt for individual fields
        Write-Host "  Building JSON from individual values..." -ForegroundColor Gray
        $jsonObj = @{}
        foreach ($key in $secret.Template.Keys) {
            $fieldValue = Read-Host "    Enter value for '$key'"
            if (-not [string]::IsNullOrWhiteSpace($fieldValue)) {
                $jsonObj[$key] = $fieldValue
            }
        }

        if ($jsonObj.Count -eq 0) {
            Write-Host "  [SKIP] No values provided, skipping." -ForegroundColor DarkYellow
            Write-Host ""
            continue
        }

        $value = $jsonObj | ConvertTo-Json -Compress
    }

    Set-SecretsManagerSecret `
        -Name $secret.Name `
        -Value $value `
        -Description $secret.Description `
        -AwsProfile $Profile `
        -AwsRegion $Region `
        -IsDryRun $false

    Write-Host ""
}

# ============================================================================
# Summary
# ============================================================================

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Setup Complete!" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "SSM Parameters created under: /h-dcn/$Environment/" -ForegroundColor White
Write-Host ""
Write-Host "These parameters are referenced in the SAM template via:" -ForegroundColor Gray
Write-Host '  {{resolve:ssm:/h-dcn/${Environment}/...}}       (String)' -ForegroundColor Gray
Write-Host '  {{resolve:ssm-secure:/h-dcn/${Environment}/...}} (SecureString)' -ForegroundColor Gray
Write-Host ""
Write-Host "To verify parameters were created:" -ForegroundColor White
Write-Host "  aws ssm get-parameters-by-path --path /h-dcn/$Environment/ --recursive --profile $Profile --region $Region" -ForegroundColor Gray
Write-Host ""
Write-Host "To verify secrets:" -ForegroundColor White
Write-Host "  aws secretsmanager list-secrets --filter Key=name,Values=h-dcn/$Environment --profile $Profile --region $Region" -ForegroundColor Gray
Write-Host ""
if (-not $DryRun) {
    Write-Host "You can now deploy the SAM stack:" -ForegroundColor Green
    Write-Host "  cd backend && sam build && sam deploy --config-env nonprofit" -ForegroundColor Green
}
