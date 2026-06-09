import json
import os
import boto3
import boto3.dynamodb.conditions
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
    print("Using shared auth layer")
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("admin_get_orders")
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

        # Validate permissions - requires Products_Read
        is_authorized, permission_error, regional_info = validate_permissions_with_regions(
            user_roles, ['Products_Read'], user_email, None
        )
        if not is_authorized:
            return permission_error

        log_successful_access(user_email, user_roles, 'admin_get_orders')

        # Get optional query param filters
        query_params = event.get('queryStringParameters') or {}
        event_id_filter = query_params.get('event_id')
        status_filter = query_params.get('status')

        # Build filter expression
        filter_conditions = []
        if event_id_filter == 'null':
            filter_conditions.append(
                boto3.dynamodb.conditions.Attr('event_id').not_exists()
                | boto3.dynamodb.conditions.Attr('event_id').eq(None)
            )
        elif event_id_filter:
            filter_conditions.append(boto3.dynamodb.conditions.Attr('event_id').eq(event_id_filter))
        if status_filter:
            filter_conditions.append(boto3.dynamodb.conditions.Attr('status').eq(status_filter))

        # Combine filter conditions
        scan_kwargs = {}
        if filter_conditions:
            combined_filter = filter_conditions[0]
            for condition in filter_conditions[1:]:
                combined_filter = combined_filter & condition
            scan_kwargs['FilterExpression'] = combined_filter

        # Scan orders with filters
        response = table.scan(**scan_kwargs)
        orders = response.get('Items', [])

        # Handle pagination
        while 'LastEvaluatedKey' in response:
            scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
            response = table.scan(**scan_kwargs)
            orders.extend(response.get('Items', []))

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({'orders': orders, 'total_count': len(orders)}, default=str)
        }

    except Exception as e:
        print(f"Error retrieving admin orders: {str(e)}")
        return create_error_response(500, 'Internal server error')
