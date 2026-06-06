"""
Tenant resolver for multi-tenant product visibility.

Derives accessible tenants from Cognito group claims and validates
that requested tenants are within the user's access scope.

Mapping:
    hdcnLeden       → "h-dcn"
    Regio_Pressmeet → "presmeet"
    Regio_All       → "presmeet"

A user with multiple qualifying groups sees the union of granted tenants.
"""

import json
from shared.auth_utils import cors_headers


# Cognito group → tenant mapping
GROUP_TENANT_MAP = {
    "hdcnLeden": "h-dcn",
    "Regio_Pressmeet": "presmeet",
    "Regio_All": "presmeet",
}


def resolve_tenants(cognito_groups):
    """
    Derive the set of accessible tenants from Cognito group claims.

    Args:
        cognito_groups (list): List of Cognito group names from the JWT
            access token's ``cognito:groups`` claim.

    Returns:
        set: Set of tenant strings the user may access.
            Empty set if no relevant groups are present.

    Examples:
        >>> resolve_tenants(["hdcnLeden"])
        {"h-dcn"}
        >>> resolve_tenants(["Regio_Pressmeet"])
        {"presmeet"}
        >>> resolve_tenants(["hdcnLeden", "Regio_All"])
        {"h-dcn", "presmeet"}
        >>> resolve_tenants(["verzoek_lid"])
        set()
    """
    if not cognito_groups:
        return set()

    tenants = set()
    for group in cognito_groups:
        tenant = GROUP_TENANT_MAP.get(group)
        if tenant:
            tenants.add(tenant)

    return tenants


def validate_tenant_access(requested_tenants, user_tenants):
    """
    Validate that all requested tenants are within the user's allowed set.

    Args:
        requested_tenants (str): Comma-separated tenant values from the API
            query parameter (e.g. "h-dcn" or "h-dcn,presmeet").
        user_tenants (set): Set of tenant strings the user is allowed to
            access (as returned by ``resolve_tenants``).

    Returns:
        None: If access is granted (all requested tenants are allowed).
        dict: A 403 Lambda error response if any requested tenant is not
            in the user's allowed set.

    Examples:
        >>> validate_tenant_access("h-dcn", {"h-dcn", "presmeet"})
        None
        >>> validate_tenant_access("presmeet", {"h-dcn"})
        {"statusCode": 403, ...}
    """
    if not requested_tenants:
        return {
            "statusCode": 403,
            "headers": cors_headers(),
            "body": json.dumps({
                "error": "tenant_access_denied",
                "details": {
                    "requested_tenant": "",
                    "allowed_tenants": sorted(user_tenants),
                },
            }),
        }

    # Parse comma-separated tenant parameter
    requested = {t.strip() for t in requested_tenants.split(",") if t.strip()}

    if not requested:
        return {
            "statusCode": 403,
            "headers": cors_headers(),
            "body": json.dumps({
                "error": "tenant_access_denied",
                "details": {
                    "requested_tenant": requested_tenants,
                    "allowed_tenants": sorted(user_tenants),
                },
            }),
        }

    # Check each requested tenant against allowed set
    denied = requested - user_tenants
    if denied:
        return {
            "statusCode": 403,
            "headers": cors_headers(),
            "body": json.dumps({
                "error": "tenant_access_denied",
                "details": {
                    "requested_tenant": ",".join(sorted(denied)),
                    "allowed_tenants": sorted(user_tenants),
                },
            }),
        }

    return None
