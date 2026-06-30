"""
Manage delegates handler for row-scoped event orders.
Endpoint: POST /booking/{id}/delegates
          DELETE /booking/{id}/delegates

Supports multiple actions:
  - "invite": invite a secondary delegate by email (validate email, enforce
    max_delegates_per_row, reject self-invitation, store pending_secondary_email)
  - "revoke": revoke pending invitation or remove linked secondary delegate
    (only allowed when order status is draft)
  - "add": (legacy) add secondary delegate by member_id
  - "remove": (legacy) remove secondary delegate by member_id

Requirements: 5.1, 5.2, 5.3, 5.7
"""

import json
import os
import re
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import TypedDict, NotRequired

import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

try:
    from shared.auth_utils import (
        extract_user_credentials,
        validate_permissions_with_regions,
        create_success_response,
        create_error_response,
        handle_options_request,
        log_successful_access,
    )
    from shared.event_access import verify_order_event_access
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("manage_delegates")
    import sys
    sys.exit(0)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# DynamoDB resources
dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
orders_table = dynamodb.Table(os.environ.get('ORDERS_TABLE_NAME', 'Orders'))
members_table = dynamodb.Table(os.environ.get('MEMBERS_TABLE_NAME', 'Members'))
events_table = dynamodb.Table(os.environ.get('EVENTS_TABLE_NAME', 'Events'))

# Simple email regex for basic format validation
EMAIL_REGEX = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


# --- Types ---

class InviteRequest(TypedDict):
    action: str
    email: str


class RevokeRequest(TypedDict):
    action: str


# --- Helpers ---

def _convert_decimals(obj):
    """Convert Decimal objects to int or float for JSON serialization."""
    if isinstance(obj, list):
        return [_convert_decimals(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: _convert_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        else:
            return float(obj)
    else:
        return obj


def _is_admin(user_roles: list[str], user_email: str) -> bool:
    """Check if user has admin-level access (events_crud permission)."""
    is_authorized, _, _ = validate_permissions_with_regions(
        user_roles, ['events_crud'], user_email, None
    )
    return is_authorized


def _resolve_member_by_email(user_email: str) -> dict | None:
    """Resolve member record from the Members table by email scan."""
    try:
        response = members_table.scan(
            FilterExpression=Attr('email').eq(user_email.lower()),
            ProjectionExpression='member_id, email, registry_row_id, member_type, allowed_events',
        )
        items = response.get('Items', [])
        return items[0] if items else None
    except Exception as e:
        logger.error(f"Error resolving member by email: {str(e)}")
        return None


def _get_member_by_id(member_id: str) -> dict | None:
    """Get a member record by member_id."""
    try:
        response = members_table.get_item(Key={'member_id': member_id})
        return response.get('Item')
    except Exception as e:
        logger.error(f"Error getting member by id: {str(e)}")
        return None


def _is_valid_email(email: str) -> bool:
    """Check if the email has a valid format."""
    if not email or not isinstance(email, str):
        return False
    return bool(EMAIL_REGEX.match(email.strip()))


def _get_max_delegates_per_row(event_id: str) -> int:
    """
    Fetch max_delegates_per_row from the event's registry_config.
    Returns the configured limit (default 2 if not set — primary + secondary).
    """
    try:
        response = events_table.get_item(
            Key={'event_id': event_id},
            ProjectionExpression='registry_config',
        )
        item = response.get('Item', {})
        registry_config = item.get('registry_config', {})
        max_delegates = registry_config.get('max_delegates_per_row', 2)
        return int(max_delegates)
    except Exception as e:
        logger.error(f"Error fetching registry_config for event {event_id}: {e}")
        return 2  # Default: primary + 1 secondary


def _count_current_delegates(delegates: dict) -> int:
    """
    Count the current number of delegates on an order.
    Counts: primary (always 1) + secondary (if linked or pending).
    """
    count = 1  # Primary always exists
    if delegates.get('secondary_member_id'):
        count += 1
    elif delegates.get('pending_secondary_email'):
        count += 1
    return count


# --- Main Handler ---

def lambda_handler(event, context):
    """POST/DELETE /booking/{id}/delegates"""
    try:
        # Handle OPTIONS (CORS preflight)
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # 1. Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # 2. Get order_id from path params
        path_params = event.get('pathParameters') or {}
        order_id = path_params.get('id')
        if not order_id:
            return create_error_response(400, 'Order ID is required in path')

        # 3. Route by HTTP method
        http_method = event.get('httpMethod', '').upper()

        if http_method == 'DELETE':
            return _handle_delete(event, order_id, user_email, user_roles)

        if http_method != 'POST':
            return create_error_response(405, 'Method not allowed')

        # 4. Parse request body
        try:
            body = json.loads(event.get('body') or '{}')
        except (json.JSONDecodeError, TypeError):
            return create_error_response(400, 'Invalid JSON body')

        action = body.get('action')
        if action not in ('invite', 'revoke', 'add', 'remove'):
            return create_error_response(
                400, 'action must be "invite", "revoke", "add", or "remove"'
            )

        # 5. Load order
        response = orders_table.get_item(Key={'order_id': order_id})
        order = response.get('Item')
        if not order:
            return create_error_response(404, 'Order not found')

        # 5a. Resolve requester's member record (needed for both access check and auth)
        is_admin_user = _is_admin(user_roles, user_email)
        requester_member = _resolve_member_by_email(user_email)

        # 5b. Event access verification (Req 16.5, 16.7):
        # For event-scoped orders, verify allowed_events + delegate ownership.
        # On failure, return 403 without revealing order existence.
        if not is_admin_user:
            event_id = order.get('event_id') or order.get('source_id')
            if event_id and event_id != 'webshop':
                if not requester_member:
                    return create_error_response(403, 'Insufficient event access')
                requester_member_id = requester_member['member_id']
                if not verify_order_event_access(order, requester_member_id):
                    return create_error_response(403, 'Insufficient event access')

        # 6. Verify order is row-scoped (has delegates field)
        delegates = order.get('delegates')
        if not delegates:
            return create_error_response(
                400, 'Delegate management is only available for row-scoped orders'
            )

        # 7. Verify authorization (primary delegate or admin)
        if not requester_member:
            return create_error_response(404, 'Requester member record not found')

        requester_member_id = requester_member['member_id']
        primary_member_id = delegates.get('primary_member_id')
        is_primary = (requester_member_id == primary_member_id)

        if not is_primary and not is_admin_user:
            return create_error_response(
                403, 'Only the primary delegate or an admin can manage delegates'
            )

        log_successful_access(user_email, user_roles, 'manage_delegates')

        # 8. Dispatch to action handler
        if action == 'invite':
            return _handle_invite(order, body, delegates, user_email)
        elif action == 'revoke':
            return _handle_revoke(order, delegates)
        elif action == 'add':
            # Legacy add by member_id
            target_member_id = body.get('member_id')
            if not target_member_id:
                return create_error_response(400, 'member_id is required for add action')
            return _handle_add(order, target_member_id, primary_member_id, requester_member)
        else:
            # Legacy remove by member_id
            return _handle_remove(order)

    except Exception as e:
        logger.error(f"Error in manage_delegates handler: {str(e)}", exc_info=True)
        return create_error_response(500, 'Internal server error')


# --- Invite Action (Req 5.1, 5.2, 5.3) ---

def _handle_invite(order: dict, body: dict, delegates: dict, requester_email: str):
    """
    Handle inviting a secondary delegate by email.

    Validates:
    - Email format
    - Not self-invitation (Req 5.2)
    - max_delegates_per_row limit not exceeded (Req 5.1)

    Stores pending_secondary_email lowercased on the order (Req 5.3).
    """
    order_id = order['order_id']
    email = body.get('email', '').strip()

    # Validate email format
    if not _is_valid_email(email):
        return create_error_response(400, 'Invalid email address')

    email_lower = email.lower()

    # Reject self-invitation (Req 5.2)
    primary_email = (delegates.get('primary') or '').lower()
    if email_lower == primary_email or email_lower == requester_email.lower():
        return create_error_response(
            400, 'Self-invitation is not allowed'
        )

    # Check if there's already a secondary delegate linked or pending
    if delegates.get('secondary_member_id'):
        return create_error_response(
            400, 'A secondary delegate is already linked. Remove them first.'
        )
    if delegates.get('pending_secondary_email'):
        return create_error_response(
            400, 'An invitation is already pending. Revoke it first.'
        )

    # Enforce max_delegates_per_row limit (Req 5.1)
    event_id = order.get('event_id')
    if event_id:
        max_delegates = _get_max_delegates_per_row(event_id)
        current_count = _count_current_delegates(delegates)
        if current_count >= max_delegates:
            return create_error_response(
                400,
                f'Maximum delegates per row ({max_delegates}) reached'
            )

    # Store pending_secondary_email lowercased on the order (Req 5.3)
    now = datetime.now(timezone.utc).isoformat()
    current_version = order.get('version', 1)

    try:
        result = orders_table.update_item(
            Key={'order_id': order_id},
            UpdateExpression=(
                'SET delegates.pending_secondary_email = :email, '
                'updated_at = :now, '
                'version = :new_version'
            ),
            ExpressionAttributeValues={
                ':email': email_lower,
                ':now': now,
                ':new_version': current_version + 1,
            },
            ReturnValues='ALL_NEW',
        )
    except ClientError as e:
        logger.error(f"Failed to store pending delegate email: {str(e)}")
        return create_error_response(500, 'Failed to send invitation')

    updated_order = _convert_decimals(result.get('Attributes', {}))
    return create_success_response({
        'order': updated_order,
        'message': f'Invitation sent to {email_lower}',
    })


# --- Revoke Action (Req 5.7) ---

def _handle_revoke(order: dict, delegates: dict):
    """
    Handle revoking a pending invitation or removing a linked secondary delegate.
    Only allowed when order status is draft (Req 5.7).
    """
    order_id = order['order_id']
    order_status = order.get('status', '')

    # Only allowed in draft status (Req 5.7)
    if order_status != 'draft':
        return create_error_response(
            400, 'Delegates can only be revoked while the order is in draft status'
        )

    # Determine what to clear
    has_pending = delegates.get('pending_secondary_email')
    has_linked = delegates.get('secondary_member_id')

    if not has_pending and not has_linked:
        return create_error_response(
            400, 'No secondary delegate or pending invitation to revoke'
        )

    now = datetime.now(timezone.utc).isoformat()
    current_version = order.get('version', 1)

    # Build the update expression to clear secondary delegate fields
    remove_parts = []
    if has_pending:
        remove_parts.append('delegates.pending_secondary_email')
    if has_linked:
        remove_parts.append('delegates.secondary_member_id')
        remove_parts.append('delegates.secondary')

    remove_expr = 'REMOVE ' + ', '.join(remove_parts)
    set_expr = 'SET updated_at = :now, version = :new_version'
    update_expr = f'{remove_expr} {set_expr}'

    try:
        result = orders_table.update_item(
            Key={'order_id': order_id},
            UpdateExpression=update_expr,
            ExpressionAttributeValues={
                ':now': now,
                ':new_version': current_version + 1,
            },
            ReturnValues='ALL_NEW',
        )
    except ClientError as e:
        logger.error(f"Failed to revoke delegate: {str(e)}")
        return create_error_response(500, 'Failed to revoke delegate')

    updated_order = _convert_decimals(result.get('Attributes', {}))
    message = 'Pending invitation revoked' if has_pending else 'Secondary delegate removed'
    return create_success_response({
        'order': updated_order,
        'message': message,
    })


# --- DELETE method handler (alternative to revoke action) ---

def _handle_delete(event, order_id: str, user_email: str, user_roles: list):
    """
    DELETE /booking/{id}/delegates — revoke/remove secondary delegate.
    Only allowed when order status is draft (Req 5.7).
    """
    # Load order
    response = orders_table.get_item(Key={'order_id': order_id})
    order = response.get('Item')
    if not order:
        return create_error_response(404, 'Order not found')

    # Event access verification (Req 16.5, 16.7)
    is_admin_user = _is_admin(user_roles, user_email)
    requester_member = _resolve_member_by_email(user_email)

    if not is_admin_user:
        event_id = order.get('event_id') or order.get('source_id')
        if event_id and event_id != 'webshop':
            if not requester_member:
                return create_error_response(403, 'Insufficient event access')
            if not verify_order_event_access(order, requester_member['member_id']):
                return create_error_response(403, 'Insufficient event access')

    delegates = order.get('delegates')
    if not delegates:
        return create_error_response(
            400, 'Delegate management is only available for row-scoped orders'
        )

    # Verify requester is primary delegate or admin
    if not requester_member:
        return create_error_response(404, 'Requester member record not found')

    requester_member_id = requester_member['member_id']
    primary_member_id = delegates.get('primary_member_id')
    is_primary = (requester_member_id == primary_member_id)

    if not is_primary and not is_admin_user:
        return create_error_response(
            403, 'Only the primary delegate or an admin can manage delegates'
        )

    log_successful_access(user_email, user_roles, 'manage_delegates')

    return _handle_revoke(order, delegates)


# --- Legacy Actions (backward compatible) ---

def _handle_add(order: dict, target_member_id: str, primary_member_id: str, requester_member: dict):
    """Handle adding a secondary delegate by member_id (legacy action)."""
    order_id = order['order_id']
    delegates = order.get('delegates', {})

    # Cannot add primary as secondary
    if target_member_id == primary_member_id:
        return create_error_response(400, 'Cannot set primary delegate as secondary delegate')

    # Check if target is already the secondary
    current_secondary = delegates.get('secondary_member_id')
    if current_secondary == target_member_id:
        return create_error_response(400, 'This member is already the secondary delegate')

    # Verify target member exists
    target_member = _get_member_by_id(target_member_id)
    if not target_member:
        return create_error_response(400, 'Target member not found')

    # Verify target member's registry_row_id matches the order's registry_row_id
    order_registry_row_id = order.get('registry_row_id')
    target_registry_row_id = target_member.get('registry_row_id')
    if order_registry_row_id and target_registry_row_id != order_registry_row_id:
        return create_error_response(
            403, 'Target member does not belong to the same registry row',
            details={'error_code': 'DELEGATE_ROW_MISMATCH'}
        )

    # Update order: set secondary_member_id and secondary email
    now = datetime.now(timezone.utc).isoformat()
    current_version = order.get('version', 1)
    target_email = target_member.get('email', '')

    try:
        result = orders_table.update_item(
            Key={'order_id': order_id},
            UpdateExpression=(
                'SET delegates.secondary_member_id = :target, '
                'delegates.secondary = :email, '
                'updated_at = :now, '
                'version = :new_version '
                'REMOVE delegates.pending_secondary_email'
            ),
            ExpressionAttributeValues={
                ':target': target_member_id,
                ':email': target_email.lower(),
                ':now': now,
                ':new_version': current_version + 1,
            },
            ReturnValues='ALL_NEW',
        )
    except ClientError as e:
        logger.error(f"Failed to update order delegates: {str(e)}")
        return create_error_response(500, 'Failed to update delegates')

    updated_order = _convert_decimals(result.get('Attributes', {}))
    return create_success_response({
        'order': updated_order,
        'message': 'Secondary delegate added successfully',
    })


def _handle_remove(order: dict):
    """Handle removing the secondary delegate (legacy action)."""
    order_id = order['order_id']
    delegates = order.get('delegates', {})

    # Check if there is a secondary to remove
    current_secondary = delegates.get('secondary_member_id')
    if not current_secondary:
        return create_error_response(400, 'No secondary delegate to remove')

    # Update order: remove secondary_member_id
    now = datetime.now(timezone.utc).isoformat()
    current_version = order.get('version', 1)

    try:
        result = orders_table.update_item(
            Key={'order_id': order_id},
            UpdateExpression=(
                'REMOVE delegates.secondary_member_id, delegates.secondary '
                'SET updated_at = :now, '
                'version = :new_version'
            ),
            ExpressionAttributeValues={
                ':now': now,
                ':new_version': current_version + 1,
            },
            ReturnValues='ALL_NEW',
        )
    except ClientError as e:
        logger.error(f"Failed to remove secondary delegate: {str(e)}")
        return create_error_response(500, 'Failed to remove delegate')

    updated_order = _convert_decimals(result.get('Attributes', {}))
    return create_success_response({
        'order': updated_order,
        'message': 'Secondary delegate removed successfully',
    })
