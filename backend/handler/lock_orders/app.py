"""
Unified lock/unlock orders handler for the generic event booking system.
Replaces: admin_lock_orders (bulk lock by source_id via event-member-index GSI)
         + admin_unlock_order (single order unlock by order_id)

Two endpoints served from the same CodeUri:
  - POST /admin/booking/lock?source_id={id}  → lock all submitted orders for a source
  - POST /admin/booking/{id}/unlock          → unlock a specific locked order

Access: requires events_crud permission (admin only).
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
    lambda_handler = create_smart_fallback_handler("lock_orders")
    import sys
    sys.exit(0)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# DynamoDB resources
dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
orders_table = dynamodb.Table(os.environ.get('ORDERS_TABLE_NAME', 'Orders'))
members_table = dynamodb.Table(os.environ.get('MEMBERS_TABLE_NAME', 'Members'))

GSI_NAME = 'event-member-index'


def _json_serialize(obj):
    """Custom JSON serializer for Decimal objects from DynamoDB."""
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


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


def _query_orders_by_source(source_id):
    """Query GSI with source_id only (PK-only, returns all orders for this source)."""
    items = []
    response = orders_table.query(
        IndexName=GSI_NAME,
        KeyConditionExpression=Key('source_id').eq(source_id)
    )
    items.extend(response.get('Items', []))
    while response.get('LastEvaluatedKey'):
        response = orders_table.query(
            IndexName=GSI_NAME,
            KeyConditionExpression=Key('source_id').eq(source_id),
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        items.extend(response.get('Items', []))
    return items


def _lock_orders_by_source(source_id, user_email):
    """
    Lock all submitted orders for a given source_id.
    Queries the event-member-index GSI, filters for status == "submitted",
    then updates each to "locked" with version increment and status_history.

    Returns summary: locked_count, locked_order_ids, skipped_count.
    """
    # Query all orders for this source via GSI
    all_orders = _query_orders_by_source(source_id)

    # Filter for submitted orders
    submitted_orders = [o for o in all_orders if o.get('status') == 'submitted']

    if not submitted_orders:
        return create_success_response({
            'locked_count': 0,
            'locked_order_ids': [],
            'skipped_count': len(all_orders),
            'message': 'No submitted orders to lock'
        })

    now = datetime.now(timezone.utc).isoformat()
    locked_ids = []
    failed_ids = []

    for order in submitted_orders:
        order_id = order['order_id']
        current_version = order.get('version', 1)

        history_entry = {
            'from': 'submitted',
            'to': 'locked',
            'at': now,
            'by': user_email,
            'source': 'manual'
        }

        try:
            orders_table.update_item(
                Key={'order_id': order_id},
                UpdateExpression=(
                    'SET #status = :locked, updated_at = :now, '
                    'version = :new_version, '
                    'status_history = list_append(if_not_exists(status_history, :empty_list), :history_entry)'
                ),
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':locked': 'locked',
                    ':now': now,
                    ':new_version': current_version + 1,
                    ':submitted': 'submitted',
                    ':history_entry': [history_entry],
                    ':empty_list': [],
                },
                ConditionExpression='#status = :submitted',
            )
            locked_ids.append(order_id)
        except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
            logger.warning(f"Concurrency conflict locking order {order_id}")
            failed_ids.append(order_id)
        except Exception as e:
            logger.error(f"Failed to lock order {order_id}: {str(e)}")
            failed_ids.append(order_id)

    skipped_count = len(all_orders) - len(submitted_orders)

    result = {
        'locked_count': len(locked_ids),
        'locked_order_ids': locked_ids,
        'skipped_count': skipped_count,
        'message': f'{len(locked_ids)} orders locked successfully'
    }
    if failed_ids:
        result['failed_order_ids'] = failed_ids
        result['failed_count'] = len(failed_ids)

    return create_success_response(result)


def _unlock_order(order_id, user_email):
    """
    Unlock a specific order (set status back to "submitted").
    Only works on orders with status == "locked".
    """
    # Get current order
    response = orders_table.get_item(Key={'order_id': order_id})
    if 'Item' not in response:
        return create_error_response(404, 'Order not found')

    order = response['Item']
    current_status = order.get('status', 'draft')

    # Only locked orders can be unlocked
    if current_status != 'locked':
        return create_error_response(
            400,
            f'Cannot unlock order with status "{current_status}". Only locked orders can be unlocked.'
        )

    now = datetime.now(timezone.utc).isoformat()
    current_version = order.get('version', 1)

    history_entry = {
        'from': 'locked',
        'to': 'submitted',
        'at': now,
        'by': user_email,
        'source': 'manual'
    }

    # Update with concurrency check
    try:
        updated = orders_table.update_item(
            Key={'order_id': order_id},
            UpdateExpression=(
                'SET #status = :submitted, updated_at = :now, '
                'version = :new_version, '
                'status_history = list_append(if_not_exists(status_history, :empty_list), :history_entry)'
            ),
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':submitted': 'submitted',
                ':now': now,
                ':new_version': current_version + 1,
                ':locked': 'locked',
                ':history_entry': [history_entry],
                ':empty_list': [],
            },
            ConditionExpression='#status = :locked',
            ReturnValues='ALL_NEW',
        )
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        return create_error_response(
            409, 'Order status was modified concurrently. Please retry.'
        )

    updated_order = _convert_decimals(updated.get('Attributes', {}))

    return create_success_response({
        'order': updated_order,
        'transition': history_entry,
        'message': 'Order unlocked successfully'
    })


def lambda_handler(event, context):
    """
    Routes to lock or unlock based on path:
      - POST /admin/booking/lock?source_id={id}  → bulk lock
      - POST /admin/booking/{id}/unlock          → single unlock
    """
    try:
        # Handle OPTIONS (CORS preflight)
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # 1. Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # 2. Admin access check: require events_crud permission
        if not _is_admin(user_roles, user_email):
            return create_error_response(403, 'Access denied: admin permissions required')

        log_successful_access(user_email, user_roles, 'lock_orders')

        # 3. Determine action from path parameters
        path_params = event.get('pathParameters') or {}
        order_id = path_params.get('id')

        if order_id:
            # --- Unlock mode: POST /admin/booking/{id}/unlock ---
            return _unlock_order(order_id, user_email)
        else:
            # --- Lock mode: POST /admin/booking/lock?source_id={id} ---
            # Accept source_id from query params or body
            query_params = event.get('queryStringParameters') or {}
            source_id = query_params.get('source_id')

            if not source_id:
                # Try reading from body
                try:
                    body = json.loads(event.get('body') or '{}')
                    source_id = body.get('source_id')
                except (json.JSONDecodeError, TypeError):
                    pass

            if not source_id:
                return create_error_response(400, 'source_id is required (query param or body)')

            return _lock_orders_by_source(source_id, user_email)

    except Exception as e:
        logger.error(f"Error in lock_orders handler: {str(e)}", exc_info=True)
        return create_error_response(500, 'Internal server error')
