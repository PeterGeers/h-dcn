#!/usr/bin/env bash
# =============================================================================
# H-DCN Centraal Configuratiebestand
# =============================================================================
# Dit bestand bevat alle resource IDs en URLs die door scripts en tests
# worden gebruikt. Source dit bestand in plaats van hardcoded waarden te gebruiken.
#
# Gebruik in bash scripts:
#   source "$(dirname "$0")/../config.sh"   # vanuit een subdirectory
#   source scripts/config.sh                 # vanuit project root
#
# =============================================================================

# --- AWS Account ---
# Dynamically resolve the AWS account ID from the current caller identity
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query 'Account' --output text 2>/dev/null)
if [ -z "$AWS_ACCOUNT_ID" ]; then
  echo "WARNING: Could not determine AWS Account ID. Ensure AWS credentials are configured." >&2
fi

# --- Frontend (GitHub Pages) ---
export FRONTEND_URL="https://petergeers.github.io/h-dcn"

# --- AWS Regio ---
export AWS_REGION="eu-west-1"

# --- API Gateway ---
export API_BASE_URL="https://qsdq51d2r3.execute-api.eu-west-1.amazonaws.com/dev"

# --- Cognito ---
export COGNITO_USER_POOL_ID="eu-west-1_OAT3oPCIm"
export COGNITO_CLIENT_ID="6unl8mg5tbv5r727vc39d847vn"
export COGNITO_DOMAIN="h-dcn-auth-${AWS_ACCOUNT_ID}.auth.eu-west-1.amazoncognito.com"

# --- DynamoDB ---
export DYNAMODB_MEMBERS_TABLE="Members"
