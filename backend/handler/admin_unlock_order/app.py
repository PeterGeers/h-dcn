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
    print("Using shared auth layer")
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("admin_unlock_order")
    import sys
    sys.exit(0)

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('ORDERS_TABLE_NAME', 'Orders')
table = dynamodb.Table(table_name)


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

        log_successful_access(user_email, user_roles, 'admin_unlock_order')

        # Get order ID from path parameters
        path_params = event.get('pathParameters') or {}
        order_id = path_params.get('id')
        if not order_id:
            return create_error_response(400, 'Order ID is required')

        # Get current order
        response = table.get_item(Key={'order_id': order_id})
        if 'Item' not in response:
            return create_error_response(404, 'Order not found')

        order = response['Item']
        current_status = order.get('status', 'draft')

        # Only locked orders can be unlocked
        if current_status != 'locked':
            return create_error_response(400, f'Cannot unlock order with status "{current_status}". Only locked orders can be unlocked.')

        # Validate transition (locked → submitted)
        if not is_valid_transition('locked', 'submitted'):
            return create_error_response(400, 'Invalid state transition')

        now = datetime.now(timezone.utc).isoformat()
        history_entry = {
            'from_status': 'locked',
            'to_status': 'submitted',
            'timestamp': now,
            'triggered_by': user_email
        }

        # Update order with optimistic locking
        try:
            updated = table.update_item(
                Key={'order_id': order_id},
                UpdateExpression='SET #status = :submitted, updated_at = :now, status_history = list_append(if_not_exists(status_history, :empty_list), :history_entry)',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':submitted': 'submitted',
                    ':now': now,
                    ':locked': 'locked',
                    ':history_entry': [history_entry],
                    ':empty_list': []
                },
                ConditionExpression='#status = :locked',
                ReturnValues='ALL_NEW'
            )
        except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
            return create_error_response(409, 'Order status was modified concurrently. Please retry.')

        return create_success_response({
            'order': updated.get('Attributes', {}),
            'transition': history_entry,
            'message': 'Order unlocked successfully'
        })

    except Exception as e:
        print(f"Error unlocking order: {str(e)}")
        return create_error_response(500, 'Internal server error')
