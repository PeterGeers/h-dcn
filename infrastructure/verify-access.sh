#!/usr/bin/env bash
#
# Cross-Account Access Verification Script
# Verifies that all AWS CLI profiles are correctly configured and can assume
# the expected roles in the correct accounts.
#
# Profiles verified:
#   personal        → Account 344561557829 (personal account)
#   nonprofit-dev   → Account 506221081911, role NonprofitDevRole (MFA required)
#   nonprofit-deploy → Account 506221081911, role NonprofitDeployRole
#   nonprofit-admin → Account 506221081911, role NonprofitAdminRole (MFA required)
#
# Usage: ./verify-access.sh [--skip-mfa]
#   --skip-mfa  Skip profiles that require MFA (nonprofit-dev, nonprofit-admin)
#
# Exit codes:
#   0 - All checks passed
#   1 - One or more checks failed

set -euo pipefail

# --- Configuration ---
PERSONAL_ACCOUNT_ID="344561557829"
NONPROFIT_ACCOUNT_ID="506221081911"

# Expected profiles and their verification criteria
declare -A EXPECTED_ACCOUNT
EXPECTED_ACCOUNT[personal]="$PERSONAL_ACCOUNT_ID"
EXPECTED_ACCOUNT[nonprofit-dev]="$NONPROFIT_ACCOUNT_ID"
EXPECTED_ACCOUNT[nonprofit-deploy]="$NONPROFIT_ACCOUNT_ID"
EXPECTED_ACCOUNT[nonprofit-admin]="$NONPROFIT_ACCOUNT_ID"

declare -A EXPECTED_ROLE
EXPECTED_ROLE[nonprofit-dev]="NonprofitDevRole"
EXPECTED_ROLE[nonprofit-deploy]="NonprofitDeployRole"
EXPECTED_ROLE[nonprofit-admin]="NonprofitAdminRole"

# Profiles that require MFA
MFA_PROFILES=("nonprofit-dev" "nonprofit-admin")

# --- Parse arguments ---
SKIP_MFA=false
for arg in "$@"; do
  case $arg in
    --skip-mfa)
      SKIP_MFA=true
      ;;
    *)
      echo "Unknown argument: $arg"
      echo "Usage: $0 [--skip-mfa]"
      exit 1
      ;;
  esac
done

# --- Helper functions ---
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

pass() {
  echo -e "  ${GREEN}PASS${NC} $1"
}

fail() {
  echo -e "  ${RED}FAIL${NC} $1"
}

warn() {
  echo -e "  ${YELLOW}SKIP${NC} $1"
}

# --- Main verification ---
echo "============================================"
echo " Cross-Account Access Verification"
echo "============================================"
echo ""

FAILURES=0
SKIPPED=0

PROFILES=("personal" "nonprofit-dev" "nonprofit-deploy" "nonprofit-admin")

for profile in "${PROFILES[@]}"; do
  echo "--- Profile: $profile ---"

  # Check if this is an MFA profile and we're skipping
  if [[ "$SKIP_MFA" == "true" ]]; then
    for mfa_profile in "${MFA_PROFILES[@]}"; do
      if [[ "$profile" == "$mfa_profile" ]]; then
        warn "Skipped (requires MFA, use without --skip-mfa to test)"
        SKIPPED=$((SKIPPED + 1))
        echo ""
        continue 2
      fi
    done
  fi

  # Inform user about MFA prompt
  for mfa_profile in "${MFA_PROFILES[@]}"; do
    if [[ "$profile" == "$mfa_profile" ]]; then
      echo "  Note: This profile requires MFA. You will be prompted for your MFA token."
    fi
  done

  # Run get-caller-identity
  IDENTITY_OUTPUT=""
  if ! IDENTITY_OUTPUT=$(aws sts get-caller-identity --profile "$profile" --output json 2>&1); then
    fail "Could not get caller identity for profile '$profile'"
    echo "       Error: $IDENTITY_OUTPUT"
    FAILURES=$((FAILURES + 1))
    echo ""
    continue
  fi

  # Parse the response
  ACCOUNT=$(echo "$IDENTITY_OUTPUT" | grep -o '"Account": "[^"]*"' | cut -d'"' -f4)
  ARN=$(echo "$IDENTITY_OUTPUT" | grep -o '"Arn": "[^"]*"' | cut -d'"' -f4)

  # Verify account ID
  EXPECTED_ACCT="${EXPECTED_ACCOUNT[$profile]}"
  if [[ "$ACCOUNT" == "$EXPECTED_ACCT" ]]; then
    pass "Account ID: $ACCOUNT (expected: $EXPECTED_ACCT)"
  else
    fail "Account ID: $ACCOUNT (expected: $EXPECTED_ACCT)"
    FAILURES=$((FAILURES + 1))
  fi

  # Verify role ARN (only for nonprofit profiles)
  if [[ -n "${EXPECTED_ROLE[$profile]:-}" ]]; then
    EXPECTED_ROLE_NAME="${EXPECTED_ROLE[$profile]}"
    if echo "$ARN" | grep -q "$EXPECTED_ROLE_NAME"; then
      pass "Role ARN contains '$EXPECTED_ROLE_NAME': $ARN"
    else
      fail "Role ARN does not contain '$EXPECTED_ROLE_NAME': $ARN"
      FAILURES=$((FAILURES + 1))
    fi
  else
    pass "ARN: $ARN"
  fi

  echo ""
done

# --- Summary ---
echo "============================================"
echo " Summary"
echo "============================================"

TOTAL=${#PROFILES[@]}
TESTED=$((TOTAL - SKIPPED))

if [[ $FAILURES -eq 0 ]]; then
  echo -e "${GREEN}All $TESTED tested profile(s) passed.${NC}"
  if [[ $SKIPPED -gt 0 ]]; then
    echo -e "${YELLOW}$SKIPPED profile(s) skipped (MFA required).${NC}"
  fi
  exit 0
else
  echo -e "${RED}$FAILURES check(s) failed out of $TESTED tested profile(s).${NC}"
  if [[ $SKIPPED -gt 0 ]]; then
    echo -e "${YELLOW}$SKIPPED profile(s) skipped (MFA required).${NC}"
  fi
  exit 1
fi
