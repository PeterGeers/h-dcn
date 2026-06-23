"""
Event Onboard handler — POST /events/{event_id}/onboard

Atomic onboarding flow for closed community booking:
1. Validate session token (JWT, event_id match, not expired)
2. If email_restricted: verify user email against row's allowed_emails
3. Check user doesn't already hold a claim for this event
4. Atomic claim via DynamoDB conditional write on registry_claims map
5. Create Cognito user (or link existing)
6. Create/update Member record
7. Add user to event_participant Cognito group
8. Check and auto-link pending delegate invitations

Rollback on failure:
- Cognito fails → release claim
- Member creation fails → delete Cognito user + release claim

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 4.1, 4.2, 4.3, 4.4, 4.5, 4.7, 16.3, 16.4, 16.6
"""

import json
import os
import time
import uuid
import logging
from datetime import datetime, timezone
from typing import TypedDict, NotRequired
from decimal import Decimal

import boto3
import jwt
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr

# Import shared utilities
try:
    from shared.auth_utils import (
        cors_headers,
        handle_options_request,
        create_error_response,
        create_success_response,
    )
except ImportError:
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("event_onboard")
    import sys
    sys.exit(0)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# AWS resources
dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
events_table = dynamodb.Table(os.environ.get('EVENTS_TABLE_NAME', 'Events'))
members_table = dynamodb.Table(os.environ.get('MEMBERS_TABLE_NAME', 'Members'))
orders_table = dynamodb.Table(os.environ.get('ORDERS_TABLE_NAME', 'Orders'))
s3 = boto3.client('s3', region_name='eu-west-1')
cognito = boto3.client('cognito-idp', region_name='eu-west-1')

REGISTRY_BUCKET = os.environ.get('REGISTRY_BUCKET_NAME', 'h-dcn-data-506221081911')
JWT_SECRET_BASE = os.environ.get('JWT_SECRET_BASE', 'h-dcn-event-session-secret')
COGNITO_USER_POOL_ID = os.environ.get('COGNITO_USER_POOL_ID', 'eu-west-1_fcUkvwjH5')


# --- Types ---

class OnboardRequest(TypedDict):
    row_id: str
    email: str
    name: str
    password: NotRequired[str]  # Only for new users
    session_token: str


class OnboardResponse(TypedDict):
    member_id: str
    message: str
    is_new_user: bool


# --- Validation ---

def validate_onboard_request(body: dict) -> tuple[OnboardRequest | None, str | None]:
    """Validate and return typed request, or error message."""
    if not body:
        return None, "Missing request body"

    row_id = body.get('row_id')
    if not row_id or not isinstance(row_id, str):
        return None, "row_id is required"

    email = body.get('email')
    if not email or not isinstance(email, str) or '@' not in email:
        return None, "Valid email is required"

    name = body.get('name')
    if not name or not isinstance(name, str) or not name.strip():
        return None, "Name is required"

    session_token = body.get('session_token')
    if not session_token or not isinstance(session_token, str):
        return None, "session_token is required"

    return body, None


# --- Session Token Validation ---

def _get_event_signing_secret(event_id: str) -> str:
    """Derive a per-event signing secret from the base secret and event_id."""
    return f"{JWT_SECRET_BASE}:{event_id}"


def validate_session_token(token: str, event_id: str) -> tuple[bool, str | None]:
    """
    Validate a session token (JWT from verify-password step).
    Uses the same signing secret as verify_event_password handler.

    Returns:
        (True, None) if valid, (False, error_message) if invalid
    """
    try:
        secret = _get_event_signing_secret(event_id)
        payload = jwt.decode(token, secret, algorithms=['HS256'])

        # Verify event_id match
        token_event_id = payload.get('event_id')
        if token_event_id != event_id:
            return False, 'Token event_id mismatch'

        return True, None

    except jwt.ExpiredSignatureError:
        return False, 'Session token expired'
    except jwt.InvalidTokenError as e:
        logger.warning(f"Session token validation error: {e}")
        return False, 'Invalid session token'


# --- Email Helpers ---

def mask_email(email: str) -> str:
    """Mask an email: show first 2 chars of local part + *** + @domain."""
    if not email or '@' not in email:
        return '***@unknown'
    local, domain = email.split('@', 1)
    return f"{local[:2]}***@{domain}"


def email_matches_list(email: str, allowed_emails: list[str]) -> bool:
    """Case-insensitive email matching against allowed_emails list."""
    email_lower = email.lower().strip()
    return any(allowed.lower().strip() == email_lower for allowed in allowed_emails)


# --- Cognito Operations ---

def get_cognito_user(email: str) -> dict | None:
    """Check if a Cognito user with this email already exists."""
    try:
        response = cognito.list_users(
            UserPoolId=COGNITO_USER_POOL_ID,
            Filter=f'email = "{email.lower()}"',
            Limit=1
        )
        users = response.get('Users', [])
        if users:
            return users[0]
        return None
    except ClientError as e:
        logger.error(f"Error checking Cognito user: {e}")
        return None


def create_cognito_user(email: str, name: str, password: str) -> tuple[str | None, str | None]:
    """
    Create a Cognito user in CONFIRMED state.
    Returns (username, None) on success, (None, error) on failure.
    """
    try:
        # Create user with suppressed welcome message
        username = email.lower()
        response = cognito.admin_create_user(
            UserPoolId=COGNITO_USER_POOL_ID,
            Username=username,
            UserAttributes=[
                {'Name': 'email', 'Value': email.lower()},
                {'Name': 'email_verified', 'Value': 'true'},
                {'Name': 'name', 'Value': name},
            ],
            MessageAction='SUPPRESS',
        )

        # Set permanent password to move user to CONFIRMED state
        cognito.admin_set_user_password(
            UserPoolId=COGNITO_USER_POOL_ID,
            Username=username,
            Password=password,
            Permanent=True,
        )

        return username, None

    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_msg = e.response['Error']['Message']
        logger.error(f"Cognito create user failed: {error_code} - {error_msg}")
        return None, f"Account creation failed: {error_msg}"


def delete_cognito_user(username: str) -> None:
    """Delete a Cognito user (rollback operation)."""
    try:
        cognito.admin_delete_user(
            UserPoolId=COGNITO_USER_POOL_ID,
            Username=username,
        )
        logger.info(f"Rolled back Cognito user: {username}")
    except ClientError as e:
        logger.error(f"Failed to rollback Cognito user {username}: {e}")


def add_user_to_group(username: str, group_name: str) -> None:
    """Add a user to a Cognito group."""
    try:
        cognito.admin_add_user_to_group(
            UserPoolId=COGNITO_USER_POOL_ID,
            Username=username,
            GroupName=group_name,
        )
    except ClientError as e:
        logger.warning(f"Failed to add {username} to group {group_name}: {e}")


# --- DynamoDB Operations ---

def atomic_claim_row(event_id: str, row_id: str, member_id: str, email: str, name: str) -> tuple[bool, str | None]:
    """
    Atomically claim a row via DynamoDB conditional write.
    Returns (True, None) on success, (False, masked_contact) on conflict.
    """
    now = datetime.now(timezone.utc).isoformat()
    claim_data = {
        'member_id': member_id,
        'email': email.lower(),
        'name': name,
        'claimed_at': now,
    }

    try:
        events_table.update_item(
            Key={'event_id': event_id},
            UpdateExpression='SET registry_claims = if_not_exists(registry_claims, :empty_map), registry_claims.#row = :claim',
            ConditionExpression='attribute_not_exists(registry_claims.#row)',
            ExpressionAttributeNames={'#row': row_id},
            ExpressionAttributeValues={':claim': claim_data, ':empty_map': {}},
        )
        return True, None

    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            # Row already claimed — get existing claimant for masked contact
            existing_contact = _get_existing_claim_contact(event_id, row_id)
            return False, existing_contact
        logger.error(f"Atomic claim failed: {e}")
        raise


def release_claim(event_id: str, row_id: str) -> None:
    """Release a claim (rollback operation)."""
    try:
        events_table.update_item(
            Key={'event_id': event_id},
            UpdateExpression='REMOVE registry_claims.#row',
            ExpressionAttributeNames={'#row': row_id},
        )
        logger.info(f"Released claim on row {row_id} for event {event_id}")
    except ClientError as e:
        logger.error(f"Failed to release claim {row_id}: {e}")


def _get_existing_claim_contact(event_id: str, row_id: str) -> str:
    """Get the masked email of the existing claimant for a row."""
    try:
        response = events_table.get_item(
            Key={'event_id': event_id},
            ProjectionExpression='registry_claims.#row',
            ExpressionAttributeNames={'#row': row_id},
        )
        item = response.get('Item', {})
        claims = item.get('registry_claims', {})
        claim = claims.get(row_id, {})
        email = claim.get('email', '')
        return mask_email(email)
    except Exception:
        return '***@unknown'


def check_existing_claim_for_user(event_id: str, email: str) -> str | None:
    """
    Check if the user already holds a claim for this event.
    Returns the row_id if found, None otherwise.
    """
    try:
        response = events_table.get_item(
            Key={'event_id': event_id},
            ProjectionExpression='registry_claims',
        )
        item = response.get('Item', {})
        claims = item.get('registry_claims', {})

        email_lower = email.lower()
        for row_id, claim in claims.items():
            if claim.get('email', '').lower() == email_lower:
                return row_id

        return None
    except Exception as e:
        logger.error(f"Error checking existing claims: {e}")
        return None


def create_member_record(member_id: str, email: str, name: str, event_id: str, row_id: str) -> tuple[bool, str | None]:
    """
    Create a new Member record for an event-only user.
    Returns (True, None) on success, (False, error) on failure.
    """
    now = datetime.now(timezone.utc).isoformat()
    try:
        members_table.put_item(
            Item={
                'member_id': member_id,
                'email': email.lower(),
                'name': name,
                'member_type': event_id,
                'club_id': row_id,
                'allowed_events': [event_id],
                'created_at': now,
                'updated_at': now,
            },
            ConditionExpression='attribute_not_exists(member_id)',
        )
        return True, None
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            # member_id collision (extremely unlikely with UUID) — treat as error
            return False, "Member ID conflict"
        logger.error(f"Failed to create member: {e}")
        return False, f"Member creation failed: {str(e)}"


def update_member_event_access(member_id: str, event_id: str) -> tuple[bool, str | None]:
    """
    Append event_id to an existing member's allowed_events list.
    Only adds if not already present. Does not modify other fields.
    Returns (True, None) on success, (False, error) on failure.
    """
    try:
        # Use ADD to append to a set-like list (DynamoDB list append with dedup check)
        # First check current allowed_events
        response = members_table.get_item(
            Key={'member_id': member_id},
            ProjectionExpression='allowed_events',
        )
        item = response.get('Item', {})
        allowed_events = item.get('allowed_events', [])

        if event_id in allowed_events:
            # Already has access, nothing to do
            return True, None

        # Append event_id
        members_table.update_item(
            Key={'member_id': member_id},
            UpdateExpression='SET allowed_events = list_append(if_not_exists(allowed_events, :empty), :event_list), updated_at = :now',
            ExpressionAttributeValues={
                ':event_list': [event_id],
                ':empty': [],
                ':now': datetime.now(timezone.utc).isoformat(),
            },
        )
        return True, None

    except ClientError as e:
        logger.error(f"Failed to update member event access: {e}")
        return False, f"Member update failed: {str(e)}"


def find_member_by_email(email: str) -> dict | None:
    """Find an existing member record by email."""
    try:
        response = members_table.scan(
            FilterExpression=Attr('email').eq(email.lower()),
            Limit=10,
        )
        items = response.get('Items', [])
        return items[0] if items else None
    except Exception as e:
        logger.error(f"Error finding member by email: {e}")
        return None


def check_and_link_pending_delegates(email: str, member_id: str) -> None:
    """
    Check for orders with pending_secondary_email matching this user's email.
    If found, link as secondary delegate.
    """
    try:
        response = orders_table.scan(
            FilterExpression=Attr('delegates.pending_secondary_email').eq(email.lower()),
        )
        items = response.get('Items', [])

        for order in items:
            order_id = order.get('order_id')
            if not order_id:
                continue

            delegates = order.get('delegates', {})
            orders_table.update_item(
                Key={'order_id': order_id},
                UpdateExpression='SET delegates.secondary = :email, delegates.secondary_member_id = :mid, delegates.pending_secondary_email = :null',
                ExpressionAttributeValues={
                    ':email': email.lower(),
                    ':mid': member_id,
                    ':null': None,
                },
            )
            logger.info(f"Linked {email} as secondary delegate on order {order_id}")

    except Exception as e:
        logger.warning(f"Error checking pending delegates: {e}")


# --- S3 Registry ---

def get_row_allowed_emails(s3_path: str, row_id: str) -> list[str] | None:
    """Fetch allowed_emails for a specific row from S3 registry."""
    try:
        response = s3.get_object(Bucket=REGISTRY_BUCKET, Key=s3_path)
        registry_data = json.loads(response['Body'].read().decode('utf-8'))
        rows = registry_data.get('rows', [])

        for row in rows:
            if row.get('row_id') == row_id:
                return row.get('allowed_emails', [])

        return None  # Row not found
    except Exception as e:
        logger.error(f"Error fetching S3 registry: {e}")
        return None


# --- Main Handler ---

def lambda_handler(event, context):
    """POST /events/{event_id}/onboard — Atomic onboarding flow."""
    try:
        # Handle OPTIONS request
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
            return create_error_response(400, 'Invalid JSON body')

        request, error = validate_onboard_request(body)
        if error:
            return create_error_response(400, error)

        row_id = request['row_id']
        email = request['email'].strip()
        name = request['name'].strip()
        session_token = request['session_token']
        password = request.get('password')

        # 1. Validate session token
        is_valid, token_error = validate_session_token(session_token, event_id)
        if not is_valid:
            return create_error_response(401, token_error or 'Invalid session token')

        # 2. Fetch Event record + registry_config
        event_response = events_table.get_item(Key={'event_id': event_id})
        if 'Item' not in event_response:
            return create_error_response(404, 'Event not found')

        event_record = event_response['Item']
        registry_config = event_record.get('registry_config', {})
        claim_mode = registry_config.get('claim_mode', 'first_come_first_served')

        # 3. If email_restricted: verify email against row's allowed_emails
        if claim_mode == 'email_restricted':
            s3_path = registry_config.get('s3_path')
            if not s3_path:
                return create_error_response(500, 'Registry not configured')

            allowed_emails = get_row_allowed_emails(s3_path, row_id)
            if allowed_emails is None:
                return create_error_response(404, 'Row not found in registry')

            if not email_matches_list(email, allowed_emails):
                return create_error_response(403, 'Email not authorized for this row')

        # 4. Check user doesn't already hold a claim for this event
        existing_row = check_existing_claim_for_user(event_id, email)
        if existing_row is not None:
            return create_error_response(409, 'You already have a claim for this event')

        # 5. Check if user already exists (Cognito + Member)
        existing_member = find_member_by_email(email)
        existing_cognito_user = get_cognito_user(email)

        is_new_user = existing_cognito_user is None
        cognito_username = None
        member_id = existing_member['member_id'] if existing_member else str(uuid.uuid4())

        # 6. Atomic claim via conditional write
        claim_success, conflict_contact = atomic_claim_row(event_id, row_id, member_id, email, name)
        if not claim_success:
            return create_error_response(
                409,
                f'Row already claimed. Contact: {conflict_contact}'
            )

        # 7. Create or link Cognito user
        if is_new_user:
            if not password:
                # Rollback claim — password required for new users
                release_claim(event_id, row_id)
                return create_error_response(400, 'Password is required for new users')

            cognito_username, cognito_error = create_cognito_user(email, name, password)
            if cognito_error:
                # ROLLBACK: release claim
                release_claim(event_id, row_id)
                return create_error_response(500, cognito_error)
        else:
            # Existing user — get their username
            cognito_username = existing_cognito_user.get('Username', email.lower())

        # 8. Create or update Member record
        if existing_member:
            # Append event access
            success, member_error = update_member_event_access(member_id, event_id)
        else:
            # Create new member
            success, member_error = create_member_record(member_id, email, name, event_id, row_id)

        if not success:
            # ROLLBACK: delete Cognito user (if new) + release claim
            if is_new_user and cognito_username:
                delete_cognito_user(cognito_username)
            release_claim(event_id, row_id)
            return create_error_response(500, member_error or 'Member operation failed')

        # 9. Add to event_participant Cognito group
        add_user_to_group(cognito_username, 'event_participant')

        # 10. Check and auto-link pending delegate invitations
        check_and_link_pending_delegates(email, member_id)

        # Success response
        response_data: OnboardResponse = {
            'member_id': member_id,
            'message': 'Successfully onboarded',
            'is_new_user': is_new_user,
        }

        return create_success_response(response_data)

    except Exception as e:
        logger.error(f"Error in event_onboard handler: {str(e)}")
        return create_error_response(500, 'Internal server error')
