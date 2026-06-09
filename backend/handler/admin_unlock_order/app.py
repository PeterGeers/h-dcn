import json
import os
import boto3
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
    lambda_handler = create_smart_fallback_handler("admin_unlock_order")
    import sys
    sys.exit(0)

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('ORDERS_TABLE_NAME', 'Orders')
table = dynamodb.Table(table_name)
events_table_name = os.environ.get('EVENTS_TABLE_NAME', 'Events')
events_table = dynamodb.Table(events_table_name)


def _json_serialize(obj):
    """Custom JSON serializer for Decimal objects from DynamoDB."""
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _has_presmeet_admin_access(user_roles):
    """Check if user has Webshop_Management + (Regio_Pressmeet or Regio_All)."""
    has_webshop = 'Webshop_Management' in user_roles
    has_regio = 'Regio_Pressmeet' in user_roles or 'Regio_All' in user_roles
    return has_webshop and has_regio


def lambda_handler(event, context):
    try:
        # Handle OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # Validate permissions - requires Webshop_Management + (Regio_Pressmeet or Regio_All)
        if not _has_presmeet_admin_access(user_roles):
            return create_error_response(
                403,
                'Access denied: Requires Webshop_Management + Regio_Pressmeet or Regio_All'
            )

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
            return create_error_response(
                400,
                f'Cannot unlock order with status "{current_status}". Only locked orders can be unlocked.'
            )

        # Check if the linked event is closed — reject unlock if so
        event_id = order.get('event_id')
        if event_id:
            event_response = events_table.get_item(Key={'event_id': event_id})
            if 'Item' in event_response:
                event_record = event_response['Item']
                event_status = event_record.get('status', '')
                if event_status == 'closed':
                    return create_error_response(
                        400,
                        'Event is closed. Edit the order directly instead.'
                    )

        # Validate transition (locked → submitted)
        if not is_valid_transition('locked', 'submitted'):
            return create_error_response(400, 'Invalid state transition')

        now = datetime.now(timezone.utc).isoformat()
        history_entry = {
            'from': 'locked',
            'to': 'submitted',
            'at': now,
            'by': user_email,
            'source': 'manual'
        }

        # Update order with concurrency check (ConditionExpression on status)
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
            return create_error_response(
                409, 'Order status was modified concurrently. Please retry.'
            )

        return create_success_response({
            'order': json.loads(json.dumps(updated.get('Attributes', {}), default=_json_serialize)),
            'transition': history_entry,
            'message': 'Order unlocked successfully'
        })

    except Exception as e:
        print(f"Error unlocking order: {str(e)}")
        return create_error_response(500, 'Internal server error')
