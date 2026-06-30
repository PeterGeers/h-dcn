"""
H-DCN Verify Event Password Endpoint

Public endpoint (NO authentication required).
Verifies a shared event password against the bcrypt hash stored on the Event record.
On success, returns event metadata and a short-lived session token (JWT, 15min TTL).

Rate-limited at API Gateway level: 10 requests/IP/minute.
"""

import json
import os
import time
from decimal import Decimal
from typing import TypedDict, NotRequired

import boto3
import bcrypt
import jwt

# Import shared utilities (CORS helpers only — no auth for public endpoint)
try:
    from shared.auth_utils import (
        cors_headers,
        handle_options_request,
        create_error_response,
        create_success_response,
    )
except ImportError:
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("verify_event_password")
    import sys
    sys.exit(0)

dynamodb = boto3.resource('dynamodb')
events_table = dynamodb.Table(os.environ.get('EVENTS_TABLE_NAME', 'Events'))

# JWT signing secret — per-event secret derived from this base + event_id
JWT_SECRET_BASE = os.environ.get('JWT_SECRET_BASE', 'h-dcn-event-session-secret')
SESSION_TOKEN_TTL_SECONDS = 15 * 60  # 15 minutes


def _convert_decimals(obj):
    """Convert Decimal objects to int or float for JSON serialization."""
    if isinstance(obj, list):
        return [_convert_decimals(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: _convert_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    return obj


class VerifyPasswordRequest(TypedDict):
    password: str


class VerifyPasswordResponse(TypedDict):
    valid: bool
    event_name: NotRequired[str]
    registry_config: NotRequired[dict]
    session_token: NotRequired[str]


def _get_event_signing_secret(event_id: str) -> str:
    """Derive a per-event signing secret from the base secret and event_id."""
    return f"{JWT_SECRET_BASE}:{event_id}"


def _generate_session_token(event_id: str) -> str:
    """Generate a short-lived JWT session token for the verified event."""
    now = int(time.time())
    payload = {
        'event_id': event_id,
        'verified_at': now,
        'exp': now + SESSION_TOKEN_TTL_SECONDS,
        'iat': now,
    }
    secret = _get_event_signing_secret(event_id)
    return jwt.encode(payload, secret, algorithm='HS256')


def _truncate_password_to_72_bytes(password: str) -> bytes:
    """
    Truncate password to 72 bytes (bcrypt limit).
    bcrypt silently ignores bytes beyond 72, but we make this explicit
    so that passwords differing only after byte 72 produce identical results.
    """
    password_bytes = password.encode('utf-8')
    return password_bytes[:72]


def _verify_password(password: str, stored_hash: str) -> bool:
    """Verify password against stored bcrypt hash."""
    truncated = _truncate_password_to_72_bytes(password)
    stored_hash_bytes = stored_hash.encode('utf-8') if isinstance(stored_hash, str) else stored_hash
    try:
        return bcrypt.checkpw(truncated, stored_hash_bytes)
    except (ValueError, TypeError):
        return False


def _validate_request_body(body: dict | None) -> tuple[str | None, str | None]:
    """Validate request body and extract password. Returns (password, error)."""
    if body is None:
        return None, "Missing request body"
    password = body.get('password')
    if not password or not isinstance(password, str):
        return None, "Password is required"
    return password, None


def lambda_handler(event, context):
    """
    POST /events/{event_id}/verify-password
    Public endpoint — no auth required.
    """
    try:
        # Handle OPTIONS request (CORS preflight)
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # Only accept POST
        if event.get('httpMethod') != 'POST':
            return create_error_response(405, 'Method not allowed')

        # Extract event_id from path parameters
        path_params = event.get('pathParameters') or {}
        event_id = path_params.get('event_id')

        if not event_id:
            return create_error_response(400, 'Missing event_id parameter')

        # Parse and validate request body
        try:
            body = json.loads(event.get('body') or '{}')
        except (json.JSONDecodeError, TypeError):
            body = {}

        password, error = _validate_request_body(body)
        if error:
            return create_error_response(400, error)

        # Fetch event record from DynamoDB
        try:
            response = events_table.get_item(Key={'event_id': event_id})
        except Exception as e:
            print(f"Error fetching event {event_id}: {str(e)}")
            # Generic error — don't reveal if event exists or not
            return create_success_response({'valid': False})

        event_item = response.get('Item')

        # If event not found or no event_password → generic invalid response (no info leak)
        if not event_item:
            return create_success_response({'valid': False})

        stored_hash = event_item.get('event_password')
        if not stored_hash:
            # No password configured — generic invalid response
            return create_success_response({'valid': False})

        # Verify password
        if not _verify_password(password, stored_hash):
            return create_success_response({'valid': False})

        # Password is correct — generate session token and return event metadata
        session_token = _generate_session_token(event_id)

        registry_config = event_item.get('registry_config', {})

        response_data: VerifyPasswordResponse = {
            'valid': True,
            'event_name': event_item.get('name', ''),
            'registry_config': _convert_decimals({
                'row_label': registry_config.get('row_label', 'club'),
                'claim_mode': registry_config.get('claim_mode', 'first_come_first_served'),
                'max_delegates_per_row': registry_config.get('max_delegates_per_row', 1),
            }),
            'session_token': session_token,
        }

        return create_success_response(response_data)

    except Exception as e:
        print(f"Error in verify_event_password handler: {str(e)}")
        return create_error_response(500, 'Internal server error')
