"""
Unified Create Payment handler.
Handles Mollie payment creation for both webshop and event orders.
Replaces: create_presmeet_payment.

POST /booking/{id}/pay

Logic:
  1. Extract credentials, resolve member_id from email
  2. Get order_id from path parameters
  3. Load order by order_id from Orders table
  4. Verify ownership: order's member_id must match authenticated member,
     or user is admin, or user is a delegate (for club-scoped orders)
  5. Verify order status is "submitted"
  6. Calculate outstanding balance from order items
  7. Create Mollie payment for outstanding balance
  8. Store payment record in Payments table with source_id from order
  9. Return Mollie checkout URL for frontend redirect
"""

import json
import os
import uuid
import logging
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr

try:
    from shared.auth_utils import (
        extract_user_credentials,
        validate_permissions_with_regions,
        create_success_response,
        create_error_response,
        handle_options_request,
        log_successful_access,
    )
    from shared.mollie_client import create_payment, MollieError
except ImportError as e:
    print(f"Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("create_payment")
    import sys
    sys.exit(0)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# DynamoDB resources
dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
orders_table = dynamodb.Table(os.environ.get('ORDERS_TABLE_NAME', 'Orders'))
payments_table = dynamodb.Table(os.environ.get('PAYMENTS_TABLE_NAME', 'Payments'))
members_table = dynamodb.Table(os.environ.get('MEMBERS_TABLE_NAME', 'Members'))
producten_table = dynamodb.Table(os.environ.get('PRODUCTEN_TABLE_NAME', 'Producten'))

# Payment configuration
REDIRECT_BASE_URL = os.environ.get(
    'PAYMENT_REDIRECT_URL', 'https://portal.h-dcn.nl/booking'
)
WEBHOOK_URL = os.environ.get('MOLLIE_WEBHOOK_URL', '')

# Supported payment methods
SUPPORTED_METHODS = ('ideal', 'creditcard', 'banktransfer')
DEFAULT_METHOD = 'ideal'


def _resolve_member_id(user_email):
    """
    Resolve member_id from the Members table by email scan.
    Returns (member_record, error_response) tuple.
    """
    try:
        response = members_table.scan(
            FilterExpression=Attr('email').eq(user_email),
            ProjectionExpression='member_id, club_id, member_type, allowed_events'
        )
        items = response.get('Items', [])
        if not items:
            return None, create_error_response(404, 'Member record not found')
        return items[0], None
    except Exception as e:
        logger.error(f"Error resolving member: {str(e)}")
        return None, create_error_response(500, 'Failed to resolve member record')


def _get_order(order_id):
    """Fetch order from Orders table by order_id."""
    try:
        response = orders_table.get_item(Key={'order_id': order_id})
        return response.get('Item')
    except Exception as e:
        logger.error(f"Error fetching order {order_id}: {e}")
        return None


def _is_admin(user_roles, user_email):
    """Check if user has admin-level access."""
    is_authorized, _, _ = validate_permissions_with_regions(
        user_roles, ['products_create'], user_email, None
    )
    return is_authorized


def _calculate_order_total(order):
    """
    Calculate the total amount for an order from its items.
    Each item should have a unit_price and quantity (or line_total).
    Returns total as Decimal.
    """
    items = order.get('items', [])
    total = Decimal('0')

    for item in items:
        line_total = item.get('line_total')
        if line_total is not None:
            total += Decimal(str(line_total))
        else:
            unit_price = Decimal(str(item.get('unit_price', 0)))
            quantity = int(item.get('quantity', 1))
            total += unit_price * quantity

    return total


def _parse_body(event):
    """Parse JSON request body, return dict or None."""
    body = event.get('body')
    if not body:
        return None
    try:
        return json.loads(body)
    except (json.JSONDecodeError, TypeError):
        return None


def lambda_handler(event, context):
    """Main handler for POST /booking/{id}/pay."""
    try:
        # Handle OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # 1. Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # No broad permission check — access controlled by order ownership
        # (verified below via member_id match or delegate check).

        # 2. Get order_id from path parameters
        path_params = event.get('pathParameters') or {}
        order_id = path_params.get('id') or path_params.get('order_id')
        if not order_id:
            return create_error_response(400, 'Order ID is required')

        # Parse request body for optional method
        body = _parse_body(event)
        method = body.get('method', DEFAULT_METHOD) if body else DEFAULT_METHOD

        if method not in SUPPORTED_METHODS:
            return create_error_response(400, f'Unsupported payment method: {method}', {
                'supported_methods': list(SUPPORTED_METHODS),
            })

        # 3. Resolve member record from email
        member_record, member_error = _resolve_member_id(user_email)
        if member_error:
            return member_error

        member_id = member_record['member_id']

        # Determine admin status
        admin = _is_admin(user_roles, user_email)

        # 4. Load order by order_id
        order = _get_order(order_id)
        if not order:
            return create_error_response(404, 'Order not found')

        # 5. Verify ownership
        order_member_id = order.get('member_id')

        if order_member_id != member_id and not admin:
            # For club-scoped orders, also check delegate access
            delegates = order.get('delegates', {})
            is_delegate = member_id in [
                delegates.get('primary_member_id'),
                delegates.get('secondary_member_id'),
            ]
            if not is_delegate:
                return create_error_response(
                    403, 'Access denied: not the order owner'
                )

        # 6. Verify order status is "submitted"
        current_status = order.get('status', 'draft')
        if current_status != 'submitted':
            return create_error_response(
                409,
                f'Cannot pay order in "{current_status}" status. '
                f'Order must be submitted first.'
            )

        # 7. Calculate outstanding balance
        total_amount = _calculate_order_total(order)
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
        source_id = order.get('source_id', 'unknown')
        if source_id == 'webshop':
            description = f"H-DCN Webshop - Order {order_id[:8]}"
        else:
            description = f"H-DCN Event Booking - Order {order_id[:8]}"

        # Build redirect URL
        redirect_url = f"{REDIRECT_BASE_URL}?order_id={order_id}&payment=complete"

        # 8. Create Mollie payment
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

        # 9. Store payment record in Payments table
        payment_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        payment_record = {
            'payment_id': payment_id,
            'order_id': order_id,
            'source_id': source_id,
            'member_id': member_id,
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
            f"amount={amount_str} EUR, "
            f"mollie_id={mollie_result['mollie_payment_id']}, "
            f"source_id={source_id}"
        )

        log_successful_access(user_email, user_roles, 'create_payment')

        # 10. Return checkout URL to frontend
        return create_success_response({
            'payment_id': payment_id,
            'checkout_url': mollie_result['checkout_url'],
            'amount': float(outstanding),
            'method': method,
            'mollie_payment_id': mollie_result['mollie_payment_id'],
        }, status_code=201)

    except Exception as e:
        logger.error(f"Error in create_payment handler: {str(e)}", exc_info=True)
        return create_error_response(500, 'Internal server error')
