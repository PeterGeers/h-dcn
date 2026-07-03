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
payments_table = dynamodb.Table(os.environ.get('PAYMENTS_TABLE_NAME', 'Payments'))


def _decimal_default(obj):
    """JSON serializer for Decimal types."""
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _enrich_order(order):
    """Add computed fields (amount_paid, outstanding) for frontend compatibility."""
    total_amount = float(order.get('total_amount', 0) or 0)
    total_paid = float(order.get('total_paid', 0) or 0)
    order['amount_paid'] = total_paid
    order['outstanding'] = max(0, total_amount - total_paid)
    return order


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
        payment_status_filter = query_params.get('payment_status')
        include_cancelled = query_params.get('include_cancelled') == 'true'

        # Build filter expression
        filter_conditions = []
        if event_id_filter == 'null' or event_id_filter == 'webshop':
            filter_conditions.append(
                boto3.dynamodb.conditions.Attr('event_id').not_exists()
                | boto3.dynamodb.conditions.Attr('event_id').eq(None)
            )
        elif event_id_filter:
            filter_conditions.append(boto3.dynamodb.conditions.Attr('event_id').eq(event_id_filter))
        if status_filter:
            filter_conditions.append(boto3.dynamodb.conditions.Attr('status').eq(status_filter))
        if payment_status_filter:
            filter_conditions.append(boto3.dynamodb.conditions.Attr('payment_status').eq(payment_status_filter))

        # Exclude draft orders always (they are just carts)
        filter_conditions.append(
            boto3.dynamodb.conditions.Attr('status').ne('draft')
        )
        # Exclude cancelled unless explicitly requested
        if not include_cancelled:
            filter_conditions.append(
                boto3.dynamodb.conditions.Attr('status').ne('cancelled')
            )

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

        # Enrich orders with computed fields
        enriched_orders = [_enrich_order(order) for order in orders]

        # Sort by created_at descending (newest first)
        enriched_orders.sort(key=lambda o: o.get('created_at', ''), reverse=True)

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({'orders': enriched_orders, 'total_count': len(enriched_orders)}, default=_decimal_default)
        }

    except Exception as e:
        print(f"Error retrieving admin orders: {str(e)}")
        return create_error_response(500, 'Internal server error')
