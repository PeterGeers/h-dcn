#!/usr/bin/env bash
# =============================================================================
# H-DCN Centraal Configuratiebestand
# =============================================================================
# Dit bestand bevat alle AWS resource IDs en URLs die door scripts en tests
# worden gebruikt. Source dit bestand in plaats van hardcoded waarden te gebruiken.
#
# Gebruik in bash scripts:
#   source "$(dirname "$0")/../config.sh"   # vanuit een subdirectory
#   source scripts/config.sh                 # vanuit project root
#
# Gebruik in PowerShell scripts:
#   $config = Get-Content "scripts/config.sh" | Where-Object { $_ -match '^export' }
#   # Of gebruik de variabelen hieronder direct
#
# Gebruik in Python scripts:
#   import subprocess
#   # Of kopieer de waarden naar een Python config
#
# =============================================================================

# --- AWS Regio ---
export AWS_REGION="eu-west-1"

# --- S3 Buckets ---
export S3_FRONTEND_BUCKET="testportal-h-dcn-frontend"

# --- CloudFront ---
export CLOUDFRONT_DISTRIBUTION_ID="E2QTMDOE6H0R87"
export CLOUDFRONT_DOMAIN="de1irtdutlxqu.cloudfront.net"
export FRONTEND_URL="https://${CLOUDFRONT_DOMAIN}"

# --- API Gateway ---
export API_BASE_URL="https://qsdq51d2r3.execute-api.eu-west-1.amazonaws.com/dev"

# --- Cognito ---
export COGNITO_USER_POOL_ID="eu-west-1_OAT3oPCIm"
export COGNITO_CLIENT_ID="6unl8mg5tbv5r727vc39d847vn"
export COGNITO_DOMAIN="h-dcn-auth-344561557829.auth.eu-west-1.amazoncognito.com"

# --- DynamoDB ---
export DYNAMODB_MEMBERS_TABLE="Members"

# --- ACM (SSL) ---
export ACM_CERTIFICATE_ARN="arn:aws:acm:us-east-1:344561557829:certificate/803dbdc3-f3bd-4cda-98c3-860a45106533"

# --- AWS Account ---
export AWS_ACCOUNT_ID="344561557829"

# --- GitHub Actions OIDC ---
export GITHUB_OIDC_PROVIDER_ARN="arn:aws:iam::344561557829:oidc-provider/token.actions.githubusercontent.com"
export GITHUB_ACTIONS_ROLE_ARN="arn:aws:iam::344561557829:role/github-actions-frontend-deploy"
