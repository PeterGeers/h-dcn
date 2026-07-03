import json
import os
import boto3
from datetime import datetime, timezone

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
    lambda_handler = create_smart_fallback_handler("admin_update_order_status")
    import sys
    sys.exit(0)

dynamodb = boto3.resource('dynamodb')
orders_table_name = os.environ.get('ORDERS_TABLE_NAME', 'Orders')
producten_table_name = os.environ.get('PRODUCTEN_TABLE_NAME', 'Producten')
movements_table_name = os.environ.get('STOCK_MOVEMENTS_TABLE_NAME', 'StockMovements')
orders_table = dynamodb.Table(orders_table_name)
producten_table = dynamodb.Table(producten_table_name)
movements_table = dynamodb.Table(movements_table_name)


def lambda_handler(event, context):
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

        log_successful_access(user_email, user_roles, 'admin_update_order_status')

        # Get order ID from path parameters
        path_params = event.get('pathParameters') or {}
        order_id = path_params.get('id')
        if not order_id:
            return create_error_response(400, 'Order ID is required')

        # Parse request body
        body = json.loads(event.get('body') or '{}')
        target_status = body.get('target_status')
        if not target_status:
            return create_error_response(400, 'target_status is required')

        # Optional fields that can be set alongside transition
        tracking_number = body.get('tracking_number')
        shipping_carrier = body.get('shipping_carrier')

        # Get current order
        response = orders_table.get_item(Key={'order_id': order_id})
        if 'Item' not in response:
            return create_error_response(404, 'Order not found')

        order = response['Item']
        current_status = order.get('status', 'draft')

        now = datetime.now(timezone.utc).isoformat()

        # Build status history entry
        history_entry = {
            'from_status': current_status,
            'to_status': target_status,
            'timestamp': now,
            'triggered_by': user_email,
            'source': 'admin',
        }

        # Reserve stock if transitioning to 'paid'
        if target_status == 'paid':
            order_items = order.get('items', [])
            if order_items:
                reserve_stock(order_items, producten_table, movements_table, order_id)

        # Build update expression dynamically
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

        # Update order with optimistic locking on current status
        try:
            updated = orders_table.update_item(
                Key={'order_id': order_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expr_names,
                ExpressionAttributeValues=expr_values,
                ConditionExpression='#status = :current_status',
                ReturnValues='ALL_NEW'
            )
        except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
            return create_error_response(409, 'Order status was modified concurrently. Please retry.')

        return create_success_response({
            'order': updated.get('Attributes', {}),
            'transition': history_entry,
            'message': f'Order status updated to {target_status}'
        })

    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        print(f"Error updating order status: {str(e)}")
        return create_error_response(500, 'Internal server error')
