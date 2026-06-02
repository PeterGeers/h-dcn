import json
import os
import uuid
import boto3
import requests
from decimal import Decimal
from datetime import datetime, timezone
from boto3.dynamodb.conditions import Attr

# Import shared authentication utilities with fallback support
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
    from shared.presmeet_validation import extract_club_id, calculate_outstanding_balance
except ImportError as e:
    # Built-in smart fallback - no local auth_fallback.py needed
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("create_presmeet_payment")
    # Exit early - the fallback handler will handle all requests
    import sys
    sys.exit(0)

dynamodb = boto3.resource('dynamodb')
orders_table = dynamodb.Table(os.environ.get('ORDERS_TABLE_NAME', 'Orders'))
payments_table = dynamodb.Table(os.environ.get('PAYMENTS_TABLE_NAME', 'Payments'))

MOLLIE_API_KEY = os.environ.get('MOLLIE_API_KEY', '')
MOLLIE_API_URL = 'https://api.mollie.com/v2/payments'

# Frontend redirect URL after payment
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://portal.h-dcn.nl')
# Webhook URL for Mollie callbacks
WEBHOOK_BASE_URL = os.environ.get('WEBHOOK_BASE_URL', '')


def convert_decimals(obj):
    """Convert Decimal objects to int or float for JSON serialization."""
    if isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        else:
            return float(obj)
    else:
        return obj


def lambda_handler(event, context):
    try:
        # Handle OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # Validate permissions - Club_User level access
        required_permissions = ['events_read']
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, required_permissions, user_email, None
        )
        if not is_authorized:
            return error_response

        # Log successful access
        log_successful_access(user_email, user_roles, 'create_presmeet_payment')

        # Extract club_id from Cognito groups
        club_id = extract_club_id(user_roles)
        if not club_id:
            return create_error_response(403, 'Missing club assignment')

        # Parse request body to get order_id (optional - can scan by club_id)
        body = {}
        if event.get('body'):
            try:
                body = json.loads(event['body'])
            except (json.JSONDecodeError, TypeError):
                return create_error_response(400, 'Invalid JSON in request body')

        order_id = body.get('order_id')

        # Load order - either by order_id or by club_id scan
        order = None
        if order_id:
            # Get specific order by ID
            response = orders_table.get_item(Key={'order_id': order_id})
            order = response.get('Item')
        else:
            # Scan for the club's PresMeet order
            scan_response = orders_table.scan(
                FilterExpression=Attr('source').eq('presmeet') & Attr('club_id').eq(club_id)
            )
            items = scan_response['Items']
            while 'LastEvaluatedKey' in scan_response:
                scan_response = orders_table.scan(
                    FilterExpression=Attr('source').eq('presmeet') & Attr('club_id').eq(club_id),
                    ExclusiveStartKey=scan_response['LastEvaluatedKey']
                )
                items.extend(scan_response['Items'])
            if items:
                order = items[0]

        if not order:
            return create_error_response(404, 'Booking not found')

        # Verify club_id match
        if order.get('club_id') != club_id:
            return create_error_response(403, 'Access denied: club mismatch')

        # Get the order_id from the loaded order
        order_id = order['order_id']

        # Reject if order status is "draft"
        order_status = order.get('status', 'draft')
        if order_status == 'draft':
            return create_error_response(400, 'Order must be submitted before payment')

        # Calculate outstanding balance
        order_total = Decimal(str(order.get('total_amount', 0)))

        # Get existing payments for this order
        payments_response = payments_table.scan(
            FilterExpression=Attr('order_id').eq(order_id) & Attr('source').eq('presmeet') & Attr('status').eq('paid')
        )
        existing_payments = payments_response['Items']
        while 'LastEvaluatedKey' in payments_response:
            payments_response = payments_table.scan(
                FilterExpression=Attr('order_id').eq(order_id) & Attr('source').eq('presmeet') & Attr('status').eq('paid'),
                ExclusiveStartKey=payments_response['LastEvaluatedKey']
            )
            existing_payments.extend(payments_response['Items'])

        outstanding = calculate_outstanding_balance(order_total, existing_payments)

        # Reject if no outstanding balance
        if outstanding <= Decimal('0.00'):
            return create_error_response(400, 'No outstanding balance')

        # Format amount for Mollie (string with 2 decimal places)
        mollie_amount = f"{outstanding:.2f}"

        # Build redirect and webhook URLs
        redirect_url = f"{FRONTEND_URL}/presmeet/payment/return"
        webhook_url = WEBHOOK_BASE_URL if WEBHOOK_BASE_URL else None

        # Create Mollie payment session
        mollie_payload = {
            'amount': {
                'currency': 'EUR',
                'value': mollie_amount
            },
            'description': f"PresMeet payment for club {club_id}",
            'redirectUrl': redirect_url,
        }

        # Only include webhookUrl if configured
        if webhook_url:
            mollie_payload['webhookUrl'] = webhook_url

        mollie_headers = {
            'Authorization': f'Bearer {MOLLIE_API_KEY}',
            'Content-Type': 'application/json'
        }

        try:
            mollie_response = requests.post(
                MOLLIE_API_URL,
                json=mollie_payload,
                headers=mollie_headers,
                timeout=10
            )
        except requests.exceptions.RequestException as e:
            print(f"Mollie API request failed: {str(e)}")
            return create_error_response(502, 'Payment provider error')

        if mollie_response.status_code not in (200, 201):
            print(f"Mollie API error: {mollie_response.status_code} - {mollie_response.text}")
            return create_error_response(502, 'Payment provider error')

        mollie_data = mollie_response.json()
        mollie_payment_id = mollie_data.get('id')
        checkout_url = mollie_data.get('_links', {}).get('checkout', {}).get('href')

        if not checkout_url:
            print(f"Mollie response missing checkout URL: {mollie_data}")
            return create_error_response(502, 'Payment provider error')

        # Store payment record in Payments table
        payment_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        payment_record = {
            'payment_id': payment_id,
            'source': 'presmeet',
            'order_id': order_id,
            'club_id': club_id,
            'amount': outstanding,
            'status': 'pending',
            'provider': 'mollie',
            'mollie_payment_id': mollie_payment_id,
            'description': f"PresMeet payment for club {club_id}",
            'created_at': now,
            'created_by': user_email
        }

        payments_table.put_item(Item=payment_record)

        # Return payment info to frontend
        response_body = {
            'payment_id': payment_id,
            'checkout_url': checkout_url,
            'amount': float(outstanding),
            'status': 'pending'
        }

        return create_success_response(response_body)

    except Exception as e:
        print(f"Error in create_presmeet_payment handler: {str(e)}")
        return create_error_response(500, 'Internal server error')
