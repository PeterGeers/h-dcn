"""
Channel resolver for multi-channel product visibility.

Derives accessible channels from Cognito group claims and validates
that requested channels are within the user's access scope.

Mapping:
    hdcnLeden       → "h-dcn"
    Regio_Pressmeet → "presmeet"
    Regio_All       → "presmeet"

A user with multiple qualifying groups sees the union of granted channels.
"""

import json
from shared.auth_utils import cors_headers


# Cognito group → channel mapping
GROUP_CHANNEL_MAP = {
    "hdcnLeden": "h-dcn",
    "Regio_Pressmeet": "presmeet",
    "Regio_All": "presmeet",
}


def resolve_channels(cognito_groups):
    """
    Derive the set of accessible channels from Cognito group claims.

    Args:
        cognito_groups (list): List of Cognito group names from the JWT
            access token's ``cognito:groups`` claim.

    Returns:
        set: Set of channel strings the user may access.
            Empty set if no relevant groups are present.

    Examples:
        >>> resolve_channels(["hdcnLeden"])
        {"h-dcn"}
        >>> resolve_channels(["Regio_Pressmeet"])
        {"presmeet"}
        >>> resolve_channels(["hdcnLeden", "Regio_All"])
        {"h-dcn", "presmeet"}
        >>> resolve_channels(["verzoek_lid"])
        set()
    """
    if not cognito_groups:
        return set()

    channels = set()
    for group in cognito_groups:
        channel = GROUP_CHANNEL_MAP.get(group)
        if channel:
            channels.add(channel)

    return channels


def validate_channel_access(requested_channels, user_channels):
    """
    Validate that all requested channels are within the user's allowed set.

    Args:
        requested_channels (str): Comma-separated channel values from the API
            query parameter (e.g. "h-dcn" or "h-dcn,presmeet").
        user_channels (set): Set of channel strings the user is allowed to
            access (as returned by ``resolve_channels``).

    Returns:
        None: If access is granted (all requested channels are allowed).
        dict: A 403 Lambda error response if any requested channel is not
            in the user's allowed set.

    Examples:
        >>> validate_channel_access("h-dcn", {"h-dcn", "presmeet"})
        None
        >>> validate_channel_access("presmeet", {"h-dcn"})
        {"statusCode": 403, ...}
    """
    if not requested_channels:
        return {
            "statusCode": 403,
            "headers": cors_headers(),
            "body": json.dumps({
                "error": "channel_access_denied",
                "details": {
                    "requested_channel": "",
                    "allowed_channels": sorted(user_channels),
                },
            }),
        }

    # Parse comma-separated channel parameter
    requested = {t.strip() for t in requested_channels.split(",") if t.strip()}

    if not requested:
        return {
            "statusCode": 403,
            "headers": cors_headers(),
            "body": json.dumps({
                "error": "channel_access_denied",
                "details": {
                    "requested_channel": requested_channels,
                    "allowed_channels": sorted(user_channels),
                },
            }),
        }

    # Check each requested channel against allowed set
    denied = requested - user_channels
    if denied:
        return {
            "statusCode": 403,
            "headers": cors_headers(),
            "body": json.dumps({
                "error": "channel_access_denied",
                "details": {
                    "requested_channel": ",".join(sorted(denied)),
                    "allowed_channels": sorted(user_channels),
                },
            }),
        }

    return None
