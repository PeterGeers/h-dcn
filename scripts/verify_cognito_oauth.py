#!/usr/bin/env python3
"""
Verify Cognito app client OAuth configuration matches expected settings.

This script calls describe-user-pool-client for the H-DCN Cognito pool and asserts
that the OAuth settings (flows, scopes, callback URLs, logout URLs, identity providers)
match the expected configuration for the unified auth flow.

Run:
    python scripts/verify_cognito_oauth.py
    python scripts/verify_cognito_oauth.py --profile nonprofit-deploy

Exit code 0 = configuration matches expected settings.
Exit code 1 = drift detected (one or more settings differ).
"""

import argparse
import sys

import boto3

USER_POOL_ID = "eu-west-1_fcUkvwjH5"
CLIENT_ID = "6jhvk853b0lfg9q1m861qs0cug"
REGION = "eu-west-1"

EXPECTED = {
    "allowed_oauth_flows_user_pool_client": True,
    "allowed_oauth_flows": {"code"},
    "allowed_oauth_scopes": {"openid", "email", "profile"},
    "callback_urls": {"https://portal.h-dcn.nl/", "http://localhost:3000/"},
    "logout_urls": {"https://portal.h-dcn.nl/", "http://localhost:3000/"},
    "supported_identity_providers": {"Google", "COGNITO"},
}


def verify(profile: str) -> int:
    """Verify Cognito OAuth config. Returns 0 if OK, 1 if drift detected."""
    session = boto3.Session(profile_name=profile, region_name=REGION)
    client = session.client("cognito-idp")

    resp = client.describe_user_pool_client(
        UserPoolId=USER_POOL_ID,
        ClientId=CLIENT_ID,
    )
    cfg = resp["UserPoolClient"]

    errors: list[str] = []

    # Check OAuth is enabled
    if not cfg.get("AllowedOAuthFlowsUserPoolClient"):
        errors.append("OAuth is DISABLED on app client")

    # Check OAuth flows
    actual_flows = set(cfg.get("AllowedOAuthFlows", []))
    if actual_flows != EXPECTED["allowed_oauth_flows"]:
        errors.append(
            f"OAuth flows: got {sorted(actual_flows)}, "
            f"expected {sorted(EXPECTED['allowed_oauth_flows'])}"
        )

    # Check OAuth scopes
    actual_scopes = set(cfg.get("AllowedOAuthScopes", []))
    if actual_scopes != EXPECTED["allowed_oauth_scopes"]:
        errors.append(
            f"OAuth scopes: got {sorted(actual_scopes)}, "
            f"expected {sorted(EXPECTED['allowed_oauth_scopes'])}"
        )

    # Check callback URLs
    actual_callbacks = set(cfg.get("CallbackURLs", []))
    if actual_callbacks != EXPECTED["callback_urls"]:
        errors.append(
            f"Callback URLs: got {sorted(actual_callbacks)}, "
            f"expected {sorted(EXPECTED['callback_urls'])}"
        )

    # Check logout URLs
    actual_logouts = set(cfg.get("LogoutURLs", []))
    if actual_logouts != EXPECTED["logout_urls"]:
        errors.append(
            f"Logout URLs: got {sorted(actual_logouts)}, "
            f"expected {sorted(EXPECTED['logout_urls'])}"
        )

    # Check identity providers
    actual_idps = set(cfg.get("SupportedIdentityProviders", []))
    if actual_idps != EXPECTED["supported_identity_providers"]:
        errors.append(
            f"Identity providers: got {sorted(actual_idps)}, "
            f"expected {sorted(EXPECTED['supported_identity_providers'])}"
        )

    # Report results
    if errors:
        print("❌ Cognito OAuth config DRIFT DETECTED:")
        for error in errors:
            print(f"   - {error}")
        return 1

    print("✅ Cognito OAuth config matches expected settings")
    print(f"   Pool: {USER_POOL_ID}")
    print(f"   Client: {CLIENT_ID}")
    print(f"   Flows: {sorted(EXPECTED['allowed_oauth_flows'])}")
    print(f"   Scopes: {sorted(EXPECTED['allowed_oauth_scopes'])}")
    print(f"   Callback URLs: {sorted(EXPECTED['callback_urls'])}")
    print(f"   Logout URLs: {sorted(EXPECTED['logout_urls'])}")
    print(f"   Identity Providers: {sorted(EXPECTED['supported_identity_providers'])}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Verify Cognito app client OAuth configuration"
    )
    parser.add_argument(
        "--profile",
        default="nonprofit-deploy",
        help="AWS CLI profile to use (default: nonprofit-deploy)",
    )
    args = parser.parse_args()
    sys.exit(verify(args.profile))
