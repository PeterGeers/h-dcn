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
    from shared.order_state_machine import is_valid_transition
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

        # Get current order
        response = orders_table.get_item(Key={'order_id': order_id})
        if 'Item' not in response:
            return create_error_response(404, 'Order not found')

        order = response['Item']
        current_status = order.get('status', 'draft')

        # Validate state transition
        if not is_valid_transition(current_status, target_status):
            return create_error_response(400, f'Invalid transition from {current_status} to {target_status}')

        now = datetime.now(timezone.utc).isoformat()

        # Build status history entry
        history_entry = {
            'from_status': current_status,
            'to_status': target_status,
            'timestamp': now,
            'triggered_by': user_email
        }

        # Reserve stock if transitioning to 'paid'
        if target_status == 'paid':
            order_items = order.get('items', [])
            tenant = order.get('tenant', 'h-dcn')
            if order_items:
                reserve_stock(order_items, producten_table, movements_table, order_id, tenant)

        # Update order with optimistic locking on current status
        try:
            updated = orders_table.update_item(
                Key={'order_id': order_id},
                UpdateExpression='SET #status = :target_status, updated_at = :now, status_history = list_append(if_not_exists(status_history, :empty_list), :history_entry)',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':target_status': target_status,
                    ':now': now,
                    ':current_status': current_status,
                    ':history_entry': [history_entry],
                    ':empty_list': []
                },
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
