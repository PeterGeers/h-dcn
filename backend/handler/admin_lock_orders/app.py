import json
import os
import boto3
import boto3.dynamodb.conditions
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
    lambda_handler = create_smart_fallback_handler("admin_lock_orders")
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

        log_successful_access(user_email, user_roles, 'admin_lock_orders')

        # Parse request body for tenant filter
        body = json.loads(event.get('body') or '{}')
        tenant_filter = body.get('tenant')

        # Find all submitted orders (optionally filtered by tenant)
        filter_expr = boto3.dynamodb.conditions.Attr('status').eq('submitted')
        if tenant_filter:
            filter_expr = filter_expr & boto3.dynamodb.conditions.Attr('tenant').eq(tenant_filter)

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
                'from_status': 'submitted',
                'to_status': 'locked',
                'timestamp': now,
                'triggered_by': user_email
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

    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        print(f"Error locking orders: {str(e)}")
        return create_error_response(500, 'Internal server error')
