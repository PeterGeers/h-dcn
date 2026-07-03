"""
Admin batch status update handler for H-DCN.

POST /admin/orders/batch-status — Updates multiple orders to a target status.
Validates each order individually using the shared order state machine.
Returns per-order success/failure results.

Requirements: 4.1 (Batch status update endpoint)
"""

import json
import os
import boto3
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Dict, Any

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
    from shared.stock_helpers import reserve_stock
    print("Using shared auth layer")
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("admin_batch_update_status")
    import sys
    sys.exit(0)

dynamodb = boto3.resource('dynamodb')
orders_table_name = os.environ.get('ORDERS_TABLE_NAME', 'Orders')
producten_table_name = os.environ.get('PRODUCTEN_TABLE_NAME', 'Producten')
movements_table_name = os.environ.get('STOCK_MOVEMENTS_TABLE_NAME', 'StockMovements')
orders_table = dynamodb.Table(orders_table_name)
producten_table = dynamodb.Table(producten_table_name)
movements_table = dynamodb.Table(movements_table_name)

MAX_BATCH_SIZE = 25


def _decimal_default(obj: Any) -> Any:
    """JSON serializer for Decimal types."""
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _update_single_order(
    order_id: str,
    target_status: str,
    user_email: str,
    tracking_number: str | None = None,
    shipping_carrier: str | None = None,
) -> Dict[str, Any]:
    """
    Attempt to transition a single order to target_status.
    Returns a result dict with success/failure info.
    """
    try:
        # Get current order
        response = orders_table.get_item(Key={'order_id': order_id})
        if 'Item' not in response:
            return {'order_id': order_id, 'success': False, 'error': 'Order not found'}

        order = response['Item']
        current_status = order.get('status', 'draft')

        # Skip if already at target status
        if current_status == target_status:
            return {'order_id': order_id, 'success': True}

        now = datetime.now(timezone.utc).isoformat()

        # Build status history entry
        history_entry = {
            'from_status': current_status,
            'to_status': target_status,
            'timestamp': now,
            'triggered_by': user_email,
            'source': 'admin_batch',
        }

        # Reserve stock if transitioning to 'paid'
        if target_status == 'paid':
            order_items = order.get('items', [])
            if order_items:
                reserve_stock(order_items, producten_table, movements_table, order_id)

        # Build update expression
        update_parts = [
            '#status = :target_status',
            'updated_at = :now',
            'status_history = list_append(if_not_exists(status_history, :empty_list), :history_entry)',
        ]
        expr_names = {'#status': 'status'}
        expr_values = {
            ':target_status': target_status,
            ':now': now,
            ':current_status': current_status,
            ':history_entry': [history_entry],
            ':empty_list': [],
        }

        # Set timestamps for specific transitions
        if target_status == 'shipped':
            update_parts.append('shipped_at = :shipped_at')
            expr_values[':shipped_at'] = now
        elif target_status == 'picked_up':
            update_parts.append('picked_up_at = :picked_up_at')
            expr_values[':picked_up_at'] = now
            update_parts.append('picked_up_by = :picked_up_by')
            expr_values[':picked_up_by'] = user_email

        # Set tracking info if provided
        if tracking_number:
            update_parts.append('tracking_number = :tracking_number')
            expr_values[':tracking_number'] = tracking_number
        if shipping_carrier:
            update_parts.append('shipping_carrier = :shipping_carrier')
            expr_values[':shipping_carrier'] = shipping_carrier

        update_expression = 'SET ' + ', '.join(update_parts)

        # Update with optimistic locking
        orders_table.update_item(
            Key={'order_id': order_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
            ConditionExpression='#status = :current_status',
        )

        return {'order_id': order_id, 'success': True}

    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        return {
            'order_id': order_id,
            'success': False,
            'error': 'Order status was modified concurrently',
        }
    except Exception as e:
        print(f"Error updating order {order_id}: {str(e)}")
        return {'order_id': order_id, 'success': False, 'error': 'Internal error'}


def lambda_handler(event, context):
    """Main handler for POST /admin/orders/batch-status."""
    try:
        # Handle OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # Validate permissions - requires Products_CRUD
        is_authorized, permission_error, regional_info = validate_permissions_with_regions(
            user_roles, ['Products_CRUD'], user_email, None
        )
        if not is_authorized:
            return permission_error

        log_successful_access(user_email, user_roles, 'admin_batch_update_status')

        # Parse request body
        body = json.loads(event.get('body') or '{}')
        order_ids: List[str] = body.get('order_ids', [])
        target_status: str = body.get('target_status', '')
        tracking_number: str | None = body.get('tracking_number')
        shipping_carrier: str | None = body.get('shipping_carrier')

        # Validate input
        if not order_ids:
            return create_error_response(400, 'order_ids is required and must be non-empty')
        if not target_status:
            return create_error_response(400, 'target_status is required')
        if not isinstance(order_ids, list):
            return create_error_response(400, 'order_ids must be an array')
        if len(order_ids) > MAX_BATCH_SIZE:
            return create_error_response(
                400, f'Maximum batch size is {MAX_BATCH_SIZE} orders'
            )

        # Process each order individually
        results: List[Dict[str, Any]] = []
        for order_id in order_ids:
            result = _update_single_order(
                order_id=order_id,
                target_status=target_status,
                user_email=user_email,
                tracking_number=tracking_number,
                shipping_carrier=shipping_carrier,
            )
            results.append(result)

        success_count = sum(1 for r in results if r['success'])
        failure_count = len(results) - success_count

        return create_success_response(
            json.loads(json.dumps({
                'results': results,
                'summary': {
                    'total': len(results),
                    'success': success_count,
                    'failed': failure_count,
                },
            }, default=_decimal_default))
        )

    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        print(f"Error in batch status update: {str(e)}")
        return create_error_response(500, 'Internal server error')
