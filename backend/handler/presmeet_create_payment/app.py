"""
PresMeet Create Payment handler.

POST /presmeet/orders/{id}/pay

Initiates a Mollie payment for the outstanding balance on a PresMeet order.
Calculates outstanding = total_amount - total_paid, creates a Mollie payment,
stores a payment record in the Payments table, and returns the checkout URL.

Requirements: 7
"""

import json
import os
import uuid
import logging
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

# Import shared auth layer
try:
    from shared.auth_utils import (
        extract_user_credentials,
        validate_permissions_with_regions,
        cors_headers,
        handle_options_request,
        create_error_response,
        create_success_response,
        log_successful_access,
    )
    from shared.club_identity import get_club_id, has_presmeet_access, is_presmeet_admin
    from shared.mollie_client import create_payment, MollieError
    print("Using shared auth layer for presmeet_create_payment")
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("presmeet_create_payment")
    import sys
    sys.exit(0)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# DynamoDB resources
dynamodb = boto3.resource('dynamodb')
orders_table = dynamodb.Table(os.environ.get('ORDERS_TABLE_NAME', 'Orders'))
payments_table = dynamodb.Table(os.environ.get('PAYMENTS_TABLE_NAME', 'Payments'))

# Payment configuration
REDIRECT_BASE_URL = os.environ.get('PAYMENT_REDIRECT_URL', 'https://portal.h-dcn.nl/presmeet')
WEBHOOK_URL = os.environ.get('MOLLIE_WEBHOOK_URL', '')

# Supported payment methods: iDEAL (primary), banktransfer (secondary)
SUPPORTED_METHODS = ('ideal', 'banktransfer')
DEFAULT_METHOD = 'ideal'


def lambda_handler(event, context):
    """Main handler for POST /presmeet/orders/{id}/pay."""
    try:
        # Handle OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # Authentication
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # Gate: require Regio_Pressmeet or Regio_All
        if not has_presmeet_access(user_roles):
            return create_error_response(403, 'PresMeet access required', {
                'required_roles': ['Regio_Pressmeet', 'Regio_All'],
            })

        log_successful_access(user_email, user_roles, 'presmeet_create_payment')

        # Extract order_id from path
        path_params = event.get('pathParameters') or {}
        order_id = path_params.get('id')

        if not order_id:
            return create_error_response(400, 'Order ID is required in path')

        # Parse request body for optional method
        body = _parse_body(event)
        method = body.get('method', DEFAULT_METHOD) if body else DEFAULT_METHOD

        if method not in SUPPORTED_METHODS:
            return create_error_response(400, f'Unsupported payment method: {method}', {
                'supported_methods': list(SUPPORTED_METHODS),
            })

        # Determine admin status
        is_admin = is_presmeet_admin(user_roles)

        # Fetch the order
        order = _get_order(order_id)
        if not order:
            return create_error_response(404, 'Order not found', {
                'order_id': order_id,
            })

        # Authorization: check user is delegate or admin
        if not is_admin:
            club_id = get_club_id(user_email)
            if not club_id:
                return create_error_response(403, 'Missing club assignment')

            if order.get('club_id') != club_id:
                return create_error_response(403, 'Access denied: order belongs to a different club')

            auth_check = _check_delegate_access(order, user_email)
            if auth_check:
                return auth_check

        # Calculate outstanding balance
        total_amount = Decimal(str(order.get('total_amount', 0)))
        total_paid = Decimal(str(order.get('total_paid', 0)))
        outstanding = total_amount - total_paid

        if outstanding <= 0:
            return create_error_response(400, 'No outstanding balance', {
                'total_amount': float(total_amount),
                'total_paid': float(total_paid),
                'outstanding': float(outstanding),
            })

        # Format amount for Mollie (2 decimal string)
        amount_str = f"{outstanding:.2f}"

        # Build payment description
        club_id = order.get('club_id', 'unknown')
        description = f"PresMeet booking - {club_id} - Order {order_id[:8]}"

        # Build redirect URL
        redirect_url = f"{REDIRECT_BASE_URL}?order_id={order_id}&payment=complete"

        # Create Mollie payment
        try:
            mollie_result = create_payment(
                amount=amount_str,
                description=description,
                redirect_url=redirect_url,
                webhook_url=WEBHOOK_URL if WEBHOOK_URL else None,
                method=method if method != 'banktransfer' else None,
            )
        except MollieError as e:
            logger.error(f"Mollie API error for order {order_id}: {e.reason}")
            return create_error_response(502, 'Payment provider error', {
                'details': {
                    'provider': 'mollie',
                    'reason': e.reason,
                },
            })

        # Store payment record in Payments table
        payment_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        payment_record = {
            'payment_id': payment_id,
            'order_id': order_id,
            'club_id': order.get('club_id'),
            'amount': outstanding,
            'status': 'pending',
            'provider': 'mollie',
            'method': method,
            'mollie_payment_id': mollie_result['mollie_payment_id'],
            'created_at': now,
        }

        payments_table.put_item(Item=payment_record)
        logger.info(
            f"Created payment {payment_id} for order {order_id}, "
            f"amount={amount_str} EUR, mollie_id={mollie_result['mollie_payment_id']}"
        )

        # Return checkout URL to frontend
        return create_success_response({
            'payment_id': payment_id,
            'checkout_url': mollie_result['checkout_url'],
            'amount': float(outstanding),
            'method': method,
            'mollie_payment_id': mollie_result['mollie_payment_id'],
        }, status_code=201)

    except Exception as e:
        logger.error(f"Error in presmeet_create_payment: {str(e)}", exc_info=True)
        return create_error_response(500, 'Internal server error')


def _get_order(order_id):
    """Fetch order from Orders table by order_id."""
    try:
        response = orders_table.get_item(Key={'order_id': order_id})
        return response.get('Item')
    except ClientError as e:
        logger.error(f"Error fetching order {order_id}: {e}")
        raise


def _check_delegate_access(order, user_email):
    """
    Validate user is a delegate for this order.
    Returns an error response if unauthorized, or None if authorized.
    """
    delegates = order.get('delegates', {})
    primary = delegates.get('primary', '')
    secondary = delegates.get('secondary')

    if user_email.lower() == (primary or '').lower():
        return None
    if secondary and user_email.lower() == secondary.lower():
        return None

    return create_error_response(403, 'Access denied: You are not a delegate for this order', {
        'details': 'Only the primary or secondary delegate can initiate payment.',
    })


def _parse_body(event):
    """Parse JSON request body, return dict or None."""
    body = event.get('body')
    if not body:
        return None
    try:
        return json.loads(body)
    except (json.JSONDecodeError, TypeError):
        return None
