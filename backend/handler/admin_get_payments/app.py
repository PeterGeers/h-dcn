import json
import os
import boto3
import boto3.dynamodb.conditions

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
    from shared.payment_helpers import compute_payment_aggregates
    print("Using shared auth layer")
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("admin_get_payments")
    import sys
    sys.exit(0)

dynamodb = boto3.resource('dynamodb')
orders_table_name = os.environ.get('ORDERS_TABLE_NAME', 'Orders')
orders_table = dynamodb.Table(orders_table_name)


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

        log_successful_access(user_email, user_roles, 'admin_get_payments')

        # Get optional tenant filter from query params
        query_params = event.get('queryStringParameters') or {}
        tenant_filter = query_params.get('tenant')

        # Scan orders with optional tenant filter
        scan_kwargs = {}
        if tenant_filter:
            scan_kwargs['FilterExpression'] = boto3.dynamodb.conditions.Attr('tenant').eq(tenant_filter)

        response = orders_table.scan(**scan_kwargs)
        orders = response.get('Items', [])

        while 'LastEvaluatedKey' in response:
            scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
            response = orders_table.scan(**scan_kwargs)
            orders.extend(response.get('Items', []))

        # Compute payment aggregates
        aggregates = compute_payment_aggregates(orders)

        # Build per-order payment summary
        order_payments = []
        for order in orders:
            total_amount = order.get('total_amount', 0)
            amount_paid = order.get('amount_paid', 0)
            outstanding = total_amount - amount_paid

            # Determine payment status
            if amount_paid >= total_amount and total_amount > 0:
                payment_status = 'paid'
            elif amount_paid > 0:
                payment_status = 'partial'
            else:
                payment_status = 'unpaid'

            order_payments.append({
                'order_id': order.get('order_id'),
                'tenant': order.get('tenant'),
                'customer_name': order.get('customer_name', ''),
                'total_amount': total_amount,
                'amount_paid': amount_paid,
                'outstanding': outstanding,
                'payment_status': payment_status,
                'status': order.get('status')
            })

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({
                'aggregates': aggregates,
                'order_payments': order_payments,
                'total_count': len(order_payments)
            }, default=str)
        }

    except Exception as e:
        print(f"Error retrieving payment data: {str(e)}")
        return create_error_response(500, 'Internal server error')
