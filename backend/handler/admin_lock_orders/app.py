import json
import os
import boto3
import boto3.dynamodb.conditions
from datetime import datetime, timezone
from decimal import Decimal

# Import from shared auth layer (REQUIRED)
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
    from shared.order_state_machine import is_valid_transition
    print("Using shared auth layer")
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("admin_lock_orders")
    import sys
    sys.exit(0)

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('ORDERS_TABLE_NAME', 'Orders')
table = dynamodb.Table(table_name)


def _json_serialize(obj):
    """Custom JSON serializer for Decimal objects from DynamoDB."""
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _has_order_admin_access(user_roles):
    """Check if user has Webshop_Management + event/region access."""
    has_webshop = 'Webshop_Management' in user_roles
    has_regio = 'Regio_Pressmeet' in user_roles or 'Regio_All' in user_roles
    return has_webshop and has_regio


def _lock_single_order(order_id, user_email):
    """Lock a single order by ID with status_history and concurrency check."""
    # Get current order
    response = table.get_item(Key={'order_id': order_id})
    if 'Item' not in response:
        return create_error_response(404, 'Order not found')

    order = response['Item']
    current_status = order.get('status', 'draft')

    # Only submitted orders can be locked
    if current_status != 'submitted':
        return create_error_response(
            400,
            f'Cannot lock order with status "{current_status}". Only submitted orders can be locked.'
        )

    now = datetime.now(timezone.utc).isoformat()
    history_entry = {
        'from': current_status,
        'to': 'locked',
        'at': now,
        'by': user_email,
        'source': 'manual'
    }

    # Update with concurrency check (ConditionExpression on status)
    try:
        updated = table.update_item(
            Key={'order_id': order_id},
            UpdateExpression='SET #status = :locked, updated_at = :now, status_history = list_append(if_not_exists(status_history, :empty_list), :history_entry)',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':locked': 'locked',
                ':now': now,
                ':submitted': 'submitted',
                ':history_entry': [history_entry],
                ':empty_list': []
            },
            ConditionExpression='#status = :submitted',
            ReturnValues='ALL_NEW'
        )
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        return create_error_response(
            409, 'Order status was modified concurrently. Please retry.'
        )

    return create_success_response({
        'order': json.loads(json.dumps(updated.get('Attributes', {}), default=_json_serialize)),
        'transition': history_entry,
        'message': 'Order locked successfully'
    })


def _lock_bulk_orders(body, user_email):
    """Lock all submitted orders, optionally filtered by event_id."""
    event_id_filter = body.get('event_id')

    # Find all submitted orders (optionally filtered by event_id)
    filter_expr = boto3.dynamodb.conditions.Attr('status').eq('submitted')
    if event_id_filter == 'null':
        filter_expr = filter_expr & (
            boto3.dynamodb.conditions.Attr('event_id').not_exists()
            | boto3.dynamodb.conditions.Attr('event_id').eq(None)
        )
    elif event_id_filter:
        filter_expr = filter_expr & boto3.dynamodb.conditions.Attr('event_id').eq(event_id_filter)

    response = table.scan(FilterExpression=filter_expr)
    submitted_orders = response.get('Items', [])

    while 'LastEvaluatedKey' in response:
        response = table.scan(
            FilterExpression=filter_expr,
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        submitted_orders.extend(response.get('Items', []))

    # Bulk transition submitted → locked
    now = datetime.now(timezone.utc).isoformat()
    locked_count = 0
    failed_ids = []

    for order in submitted_orders:
        order_id = order['order_id']
        history_entry = {
            'from': 'submitted',
            'to': 'locked',
            'at': now,
            'by': user_email,
            'source': 'manual'
        }
        try:
            table.update_item(
                Key={'order_id': order_id},
                UpdateExpression='SET #status = :locked, updated_at = :now, status_history = list_append(if_not_exists(status_history, :empty_list), :history_entry)',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':locked': 'locked',
                    ':now': now,
                    ':submitted': 'submitted',
                    ':history_entry': [history_entry],
                    ':empty_list': []
                },
                ConditionExpression='#status = :submitted'
            )
            locked_count += 1
        except Exception as lock_err:
            print(f"Failed to lock order {order_id}: {str(lock_err)}")
            failed_ids.append(order_id)

    return create_success_response({
        'locked_count': locked_count,
        'failed_count': len(failed_ids),
        'failed_order_ids': failed_ids,
        'message': f'{locked_count} orders locked successfully'
    })


def lambda_handler(event, context):
    try:
        # Handle OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # Validate permissions - requires Webshop_Management + event/region admin
        if not _has_order_admin_access(user_roles):
            return create_error_response(
                403,
                'Access denied: Requires Webshop_Management + Regio_Pressmeet or Regio_All'
            )

        log_successful_access(user_email, user_roles, 'admin_lock_orders')

        # Determine mode: single-order lock (path param) vs bulk lock (body)
        path_params = event.get('pathParameters') or {}
        order_id = path_params.get('id')

        if order_id:
            # Single-order lock mode
            return _lock_single_order(order_id, user_email)
        else:
            # Bulk lock mode (legacy behavior)
            raw_body = event.get('body')
            body = json.loads(raw_body) if raw_body and raw_body != 'null' else {}
            if not isinstance(body, dict):
                body = {}
            # Also check query params for event_id (frontend sends it there)
            query_params = event.get('queryStringParameters') or {}
            if not body.get('event_id') and query_params.get('event_id'):
                body['event_id'] = query_params['event_id']
            return _lock_bulk_orders(body, user_email)

    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        print(f"Error locking orders: {str(e)}")
        return create_error_response(500, 'Internal server error')
