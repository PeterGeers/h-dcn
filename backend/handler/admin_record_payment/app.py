import json
import os
import uuid
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
    print("Using shared auth layer")
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("admin_record_payment")
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

        # Validate permissions - requires Products_CRUD
        is_authorized, permission_error, regional_info = validate_permissions_with_regions(
            user_roles, ['Products_CRUD'], user_email, None
        )
        if not is_authorized:
            return permission_error

        log_successful_access(user_email, user_roles, 'admin_record_payment')

        # Parse request body
        body = json.loads(event.get('body') or '{}')

        # Validate required fields
        order_id = body.get('order_id')
        amount = body.get('amount')
        date = body.get('date')
        description = body.get('description', '')

        if not order_id:
            return create_error_response(400, 'order_id is required')
        if amount is None or not isinstance(amount, (int, float)):
            return create_error_response(400, 'amount must be a number')
        if amount < 0.01 or amount > 999999.99:
            return create_error_response(400, 'amount must be between 0.01 and 999999.99')
        if not date:
            return create_error_response(400, 'date is required (ISO 8601 format)')
        if description and len(description) > 255:
            return create_error_response(400, 'description must be 255 characters or less')

        # Validate date format
        try:
            datetime.fromisoformat(date.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return create_error_response(400, 'date must be valid ISO 8601 format')

        # Get order
        response = orders_table.get_item(Key={'order_id': order_id})
        if 'Item' not in response:
            return create_error_response(404, 'Order not found')

        order = response['Item']

        # Create payment record
        payment_id = f"pay_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()

        payment_record = {
            'payment_id': payment_id,
            'order_id': order_id,
            'amount': Decimal(str(amount)),
            'date': date,
            'description': description,
            'recorded_by': user_email,
            'created_at': now
        }

        # Calculate new amount_paid
        current_paid = float(order.get('amount_paid', 0))
        new_paid = current_paid + amount
        total_amount = float(order.get('total_amount', 0))

        # Determine payment_status
        if new_paid >= total_amount and total_amount > 0:
            payment_status = 'paid'
        elif new_paid > 0:
            payment_status = 'partial'
        else:
            payment_status = 'unpaid'

        # Update order: increment amount_paid, update payment_status, add to payments list
        orders_table.update_item(
            Key={'order_id': order_id},
            UpdateExpression='SET amount_paid = :new_paid, payment_status = :payment_status, updated_at = :now, payments = list_append(if_not_exists(payments, :empty_list), :payment_entry)',
            ExpressionAttributeValues={
                ':new_paid': Decimal(str(new_paid)),
                ':payment_status': payment_status,
                ':now': now,
                ':payment_entry': [payment_record],
                ':empty_list': []
            }
        )

        return create_success_response({
            'payment': payment_record,
            'order_id': order_id,
            'new_amount_paid': new_paid,
            'payment_status': payment_status,
            'message': 'Payment recorded successfully'
        })

    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        print(f"Error recording payment: {str(e)}")
        return create_error_response(500, 'Internal server error')
