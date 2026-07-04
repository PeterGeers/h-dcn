"""
Get Event Registry handler.

GET /events/{event_id}/registry

Public endpoint that requires either:
- A valid session token (JWT from verify-password step), OR
- An authenticated user with event access (allowed_events contains event_id)

Returns merged registry rows from S3 invitee_registry.json + DynamoDB registry_claims,
with masked claimant emails, sorted alphabetically case-insensitive by label.
"""

import json
import os
import time
import boto3
import jwt
from decimal import Decimal
from typing import TypedDict, NotRequired

# Import shared authentication utilities with fallback support
try:
    from shared.auth_utils import (
        extract_user_credentials,
        validate_permissions_with_regions,
        cors_headers,
        handle_options_request,
        create_error_response,
        create_success_response,
        log_successful_access
    )
    from shared.event_access import has_event_access, get_member_allowed_events
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("get_event_registry")
    import sys
    sys.exit(0)

dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
events_table = dynamodb.Table(os.environ.get('EVENTS_TABLE_NAME', 'Events'))
members_table = dynamodb.Table(os.environ.get('MEMBERS_TABLE_NAME', 'Members'))
s3 = boto3.client('s3', region_name='eu-west-1')

REGISTRY_BUCKET = os.environ.get('REGISTRY_BUCKET_NAME', 'h-dcn-data-506221081911')
JWT_SECRET_BASE = os.environ.get('JWT_SECRET_BASE', 'h-dcn-event-session-secret')
SESSION_TOKEN_MAX_AGE = 900  # 15 minutes


# --- Types ---

class RegistryRow(TypedDict):
    row_id: str
    label: str
    available: bool
    logo_url: str | None
    claimed_contact: str | None
    allowed_emails: NotRequired[list[str]]


class RegistryResponse(TypedDict):
    rows: list[RegistryRow]
    row_label: str
    claim_mode: str


# --- Helper functions ---

def mask_email(email: str) -> str:
    """
    Mask an email address: show first 2 chars of local part + *** + @domain.
    Example: "hans.de.vries@example.com" → "ha***@example.com"
    """
    if not email or '@' not in email:
        return '***@unknown'
    local, domain = email.split('@', 1)
    return f"{local[:2]}***@{domain}"


def _get_event_signing_secret(event_id: str) -> str:
    """Derive a per-event signing secret from the base secret and event_id."""
    return f"{JWT_SECRET_BASE}:{event_id}"


def validate_session_token(token: str, event_id: str) -> tuple[bool, str | None]:
    """
    Validate a session token (JWT from verify-password step).

    Uses PyJWT to decode and verify the token signature and expiration,
    matching the jwt.encode() call in verify_event_password handler.

    Args:
        token: The JWT session token string
        event_id: The event_id that should match the token's event_id claim

    Returns:
        (True, None) if valid, (False, error_message) if invalid
    """
    try:
        secret = _get_event_signing_secret(event_id)
        payload = jwt.decode(token, secret, algorithms=['HS256'])

        # Check event_id match
        token_event_id = payload.get('event_id')
        if token_event_id != event_id:
            return False, 'Token event_id mismatch'

        return True, None

    except jwt.ExpiredSignatureError:
        return False, 'Token expired'
    except jwt.InvalidTokenError as e:
        print(f"Session token validation error: {e}")
        return False, 'Invalid token signature'
    except Exception as e:
        print(f"Session token validation error: {e}")
        return False, 'Token validation failed'


def authenticate_request(event: dict, event_id: str) -> tuple[bool, str | None]:
    """
    Authenticate the request using either:
    1. Session token (from verify-password step) via X-Session-Token header
    2. Standard Cognito auth (Bearer token) with event access check

    Returns:
        (True, None) if authenticated
        (False, error_message) if not authenticated
    """
    headers = event.get('headers', {}) or {}

    # Try session token first (case-insensitive header lookup)
    session_token = headers.get('X-Session-Token') or headers.get('x-session-token')
    if session_token:
        is_valid, error = validate_session_token(session_token, event_id)
        if is_valid:
            return True, None
        # If session token was provided but invalid, reject
        return False, error

    # Fall back to standard Cognito auth
    user_email, user_roles, auth_error = extract_user_credentials(event)
    if auth_error:
        return False, 'Authentication required'

    # Check if user has event access via allowed_events
    # Look up member by email to get member_id
    from boto3.dynamodb.conditions import Attr
    try:
        response = members_table.scan(
            FilterExpression=Attr('email').eq(user_email.lower()),
            ProjectionExpression='member_id, allowed_events'
        )
        items = response.get('Items', [])
        if not items:
            return False, 'Member not found'

        member = items[0]
        allowed_events = member.get('allowed_events', [])
        if event_id in allowed_events:
            return True, None

        # Also allow admins (Products_CRUD, Regio_All)
        admin_roles = {'Products_CRUD', 'Regio_All', 'System_CRUD', 'Webshop_Management'}
        if set(user_roles) & admin_roles:
            return True, None

        return False, 'No access to this event'

    except Exception as e:
        print(f"Error checking event access: {e}")
        return False, 'Access check failed'


def convert_decimals(obj):
    """Convert DynamoDB Decimal types to int/float for JSON serialization."""
    if isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    return obj


def lambda_handler(event, context):
    """Main handler for GET /events/{event_id}/registry."""
    try:
        # Handle OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # Extract event_id from path parameters
        path_params = event.get('pathParameters') or {}
        event_id = path_params.get('event_id')
        if not event_id:
            return create_error_response(400, 'Missing event_id parameter')

        # Authenticate request (session token OR Cognito auth)
        is_authenticated, auth_error = authenticate_request(event, event_id)
        if not is_authenticated:
            return create_error_response(401, auth_error or 'Authentication required')

        # Fetch Event record from DynamoDB
        event_response = events_table.get_item(Key={'event_id': event_id})
        if 'Item' not in event_response:
            return create_error_response(404, 'Event not found')

        event_record = event_response['Item']
        registry_config = event_record.get('registry_config', {})
        registry_claims = event_record.get('registry_claims', {})

        # Get S3 path for invitee_registry.json
        s3_path = registry_config.get('s3_path')
        if not s3_path:
            return create_error_response(404, 'Registry not configured for this event')

        # Fetch S3 invitee_registry.json
        try:
            s3_response = s3.get_object(Bucket=REGISTRY_BUCKET, Key=s3_path)
            registry_data = json.loads(s3_response['Body'].read().decode('utf-8'))
        except s3.exceptions.NoSuchKey:
            return create_error_response(404, 'Registry file not found')
        except Exception as e:
            print(f"Error fetching registry from S3: {e}")
            return create_error_response(503, 'Registry temporarily unavailable')

        # Extract config values for response
        row_label = registry_config.get('row_label', 'row')
        claim_mode = registry_config.get('claim_mode', 'first_come_first_served')

        # Merge S3 rows with DynamoDB claims
        s3_rows = registry_data.get('rows', [])
        merged_rows: list[RegistryRow] = []

        for row in s3_rows:
            row_id = row.get('row_id', '')
            label = row.get('label', '')
            logo_url = row.get('logo_url')
            allowed_emails = row.get('allowed_emails', [])

            # Check if this row is claimed
            claim = registry_claims.get(row_id)
            is_claimed = claim is not None

            # Build the merged row
            merged_row: RegistryRow = {
                'row_id': row_id,
                'label': label,
                'available': not is_claimed,
                'logo_url': logo_url,
                'claimed_contact': mask_email(claim['email']) if is_claimed and claim.get('email') else None,
            }

            # Include allowed_emails only in email_restricted mode
            if claim_mode == 'email_restricted':
                merged_row['allowed_emails'] = allowed_emails

            merged_rows.append(merged_row)

        # Sort rows alphabetically case-insensitive by label
        merged_rows.sort(key=lambda r: r['label'].lower())

        # Build response
        response_data: RegistryResponse = {
            'rows': merged_rows,
            'row_label': row_label,
            'claim_mode': claim_mode,
        }

        return create_success_response(convert_decimals(response_data))

    except Exception as e:
        print(f"Error in get_event_registry: {str(e)}")
        return create_error_response(500, 'Internal server error')
