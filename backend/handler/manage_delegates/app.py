"""
Manage delegates handler for club-scoped event orders.
Endpoint: POST /booking/{id}/delegates

Allows the primary delegate or an admin to add/remove a secondary delegate
on a club-scoped order. Only applicable when order has delegates (club scope).

Body: { "action": "add" | "remove", "member_id": "<target_member_id>" }

Logic:
  1. Load order by order_id from path params
  2. Verify order is club-scoped (has delegates field)
  3. Verify requester is primary delegate or admin (events_crud)
  4. For "add": set delegates.secondary_member_id, verify target exists + same club
  5. For "remove": remove secondary_member_id from delegates
  6. Return updated order
"""

import json
import os
import logging
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key, Attr

try:
    from shared.auth_utils import (
        extract_user_credentials,
        validate_permissions_with_regions,
        create_success_response,
        create_error_response,
        handle_options_request,
        log_successful_access,
    )
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


def _is_admin(user_roles, user_email):
    """Check if user has admin-level access (events_crud permission)."""
    is_authorized, _, _ = validate_permissions_with_regions(
        user_roles, ['events_crud'], user_email, None
    )
    return is_authorized


def _resolve_member_by_email(user_email):
    """
    Resolve member_id from the Members table by email scan.
    Returns member record or None.
    """
    try:
        response = members_table.scan(
            FilterExpression=Attr('email').eq(user_email),
            ProjectionExpression='member_id, club_id, member_type, allowed_events'
        )
        items = response.get('Items', [])
        if not items:
            return None
        return items[0]
    except Exception as e:
        logger.error(f"Error resolving member by email: {str(e)}")
        return None


def _get_member_by_id(member_id):
    """
    Get a member record by member_id.
    Returns member record or None.
    """
    try:
        response = members_table.get_item(Key={'member_id': member_id})
        return response.get('Item')
    except Exception as e:
        logger.error(f"Error getting member by id: {str(e)}")
        return None


def lambda_handler(event, context):
    """POST /booking/{id}/delegates"""
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

        # 3. Parse request body
        try:
            body = json.loads(event.get('body') or '{}')
        except (json.JSONDecodeError, TypeError):
            return create_error_response(400, 'Invalid JSON body')

        action = body.get('action')
        if action not in ('add', 'remove'):
            return create_error_response(400, 'action must be "add" or "remove"')

        target_member_id = body.get('member_id')
        if action == 'add' and not target_member_id:
            return create_error_response(400, 'member_id is required for add action')

        # 4. Load order
        response = orders_table.get_item(Key={'order_id': order_id})
        order = response.get('Item')
        if not order:
            return create_error_response(404, 'Order not found')

        # 5. Verify order is club-scoped (has delegates field)
        delegates = order.get('delegates')
        if not delegates:
            return create_error_response(400, 'Delegate management is only available for club-scoped orders')

        # 6. Resolve requester's member_id
        requester_member = _resolve_member_by_email(user_email)
        if not requester_member:
            return create_error_response(404, 'Requester member record not found')

        requester_member_id = requester_member['member_id']

        # 7. Verify requester is primary delegate or admin
        primary_member_id = delegates.get('primary_member_id')
        is_primary = (requester_member_id == primary_member_id)
        is_admin_user = _is_admin(user_roles, user_email)

        if not is_primary and not is_admin_user:
            return create_error_response(403, 'Only the primary delegate or an admin can manage delegates')

        log_successful_access(user_email, user_roles, 'manage_delegates')

        # 8. Execute action
        now = datetime.now(timezone.utc).isoformat()

        if action == 'add':
            return _handle_add(order, target_member_id, primary_member_id, requester_member, now)
        else:
            return _handle_remove(order, now)

    except Exception as e:
        logger.error(f"Error in manage_delegates handler: {str(e)}", exc_info=True)
        return create_error_response(500, 'Internal server error')


def _handle_add(order, target_member_id, primary_member_id, requester_member, now):
    """Handle adding a secondary delegate."""
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

    # Verify target member has same club_id as the order
    order_club_id = order.get('club_id')
    target_club_id = target_member.get('club_id')
    if order_club_id and target_club_id != order_club_id:
        return create_error_response(400, 'Target member does not belong to the same club')

    # Update order: set secondary_member_id
    current_version = order.get('version', 1)
    try:
        result = orders_table.update_item(
            Key={'order_id': order_id},
            UpdateExpression=(
                'SET delegates.secondary_member_id = :target, '
                'updated_at = :now, '
                'version = :new_version'
            ),
            ExpressionAttributeValues={
                ':target': target_member_id,
                ':now': now,
                ':new_version': current_version + 1,
            },
            ReturnValues='ALL_NEW',
        )
    except Exception as e:
        logger.error(f"Failed to update order delegates: {str(e)}")
        return create_error_response(500, 'Failed to update delegates')

    updated_order = _convert_decimals(result.get('Attributes', {}))
    return create_success_response({
        'order': updated_order,
        'message': f'Secondary delegate added successfully',
    })


def _handle_remove(order, now):
    """Handle removing the secondary delegate."""
    order_id = order['order_id']
    delegates = order.get('delegates', {})

    # Check if there is a secondary to remove
    current_secondary = delegates.get('secondary_member_id')
    if not current_secondary:
        return create_error_response(400, 'No secondary delegate to remove')

    # Update order: remove secondary_member_id
    current_version = order.get('version', 1)
    try:
        result = orders_table.update_item(
            Key={'order_id': order_id},
            UpdateExpression=(
                'REMOVE delegates.secondary_member_id '
                'SET updated_at = :now, '
                'version = :new_version'
            ),
            ExpressionAttributeValues={
                ':now': now,
                ':new_version': current_version + 1,
            },
            ReturnValues='ALL_NEW',
        )
    except Exception as e:
        logger.error(f"Failed to remove secondary delegate: {str(e)}")
        return create_error_response(500, 'Failed to remove delegate')

    updated_order = _convert_decimals(result.get('Attributes', {}))
    return create_success_response({
        'order': updated_order,
        'message': 'Secondary delegate removed successfully',
    })
