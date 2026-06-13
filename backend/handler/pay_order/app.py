"""
Unified pay_order handler for H-DCN.

POST /orders/{id}/pay — Initiates a Mollie payment for the outstanding balance
on any order (webshop or event-linked).

This handler replaces the presmeet_create_payment handler with a unified flow
that works for both webshop orders (event_id=null) and event orders (event_id set).

Stock reservation is triggered using variant_id from stored order items when
payment transitions the order to "paid" status. Uses the shared stock_reservation
module with idempotency guard (stock_reserved flag on order).

Key design decisions:
- Unified: works identically for webshop and event orders
- Calculates outstanding = total_amount - total_paid
- Creates a Mollie payment via shared.mollie_client
- Stores a payment record in the Payments table (links to order)
- Returns the Mollie checkout URL to the frontend
- Order items contain variant_id which is used for stock reservation
- Stock reservation triggered on transition to "paid" (same pattern as admin_record_payment)
- If variant_id is present on an item, decrement stock; if not (legacy orders), skip
- Access: order owner (member), event delegate, or admin

Requirements: 10.10
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
    from shared.event_access import get_club_id
    from shared.mollie_client import create_payment, MollieError
    from shared.stock_reservation import (
        reserve_stock_for_order,
        StockReservationError,
        InsufficientStockError,
    )
    from shared.order_state_machine import transition_payment, InvalidTransitionError
    print("Using shared auth layer for pay_order")
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("pay_order")
    import sys
    sys.exit(0)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# DynamoDB resources
dynamodb = boto3.resource('dynamodb')
orders_table = dynamodb.Table(os.environ.get('ORDERS_TABLE_NAME', 'Orders'))
payments_table = dynamodb.Table(os.environ.get('PAYMENTS_TABLE_NAME', 'Payments'))
producten_table = dynamodb.Table(os.environ.get('PRODUCTEN_TABLE_NAME', 'Producten'))

# Payment configuration
REDIRECT_BASE_URL = os.environ.get('PAYMENT_REDIRECT_URL', 'https://portal.h-dcn.nl')
WEBHOOK_URL = os.environ.get('MOLLIE_WEBHOOK_URL', '')

# Supported payment methods
SUPPORTED_METHODS = ('ideal', 'creditcard', 'banktransfer')
DEFAULT_METHOD = 'ideal'


def lambda_handler(event, context):
    """Main handler for POST /orders/{id}/pay."""
    try:
        # Handle OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # Authentication
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # Access check: any authenticated member (hdcnLeden) or event participant or admin
        is_admin, _, _ = validate_permissions_with_regions(
            user_roles, ['Products_CRUD'], user_email, None
        )
        has_member_access = 'hdcnLeden' in user_roles
        has_event_booking_access = any(
            r in user_roles for r in ('Regio_Pressmeet', 'Regio_All', 'event_participant')
        )

        if not is_admin and not has_member_access and not has_event_booking_access:
            return create_error_response(403, 'Access denied: Requires membership access')

        log_successful_access(user_email, user_roles, 'pay_order')

        # Extract order_id from path
        path_params = event.get('pathParameters') or {}
        order_id = path_params.get('id')

        if not order_id:
            return create_error_response(400, 'Order ID is required in path')

        # Parse request body for optional payment method
        body = _parse_body(event)
        method = body.get('method', DEFAULT_METHOD) if body else DEFAULT_METHOD

        if method not in SUPPORTED_METHODS:
            return create_error_response(400, f'Unsupported payment method: {method}', {
                'supported_methods': list(SUPPORTED_METHODS),
            })

        # Fetch the order
        order = _get_order(order_id)
        if not order:
            return create_error_response(404, 'Order not found', {
                'order_id': order_id,
            })

        # Authorization: verify the user can pay this order
        auth_error = _check_payment_authorization(
            order, user_email, user_roles, is_admin
        )
        if auth_error:
            return auth_error

        # Validate order status — must be submitted or locked to pay
        order_status = order.get('status', '')
        if order_status not in ('submitted', 'locked'):
            return create_error_response(400, 'Order must be submitted before payment', {
                'order_id': order_id,
                'current_status': order_status,
            })

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

        # Validate order has items with variant_id for stock reservation
        items = order.get('items', [])
        if not items:
            return create_error_response(400, 'Order has no items', {
                'order_id': order_id,
            })

        # Collect variant_ids for stock reservation (used on payment confirmation)
        # For unified model: all items should have variant_id
        # For legacy orders: items without variant_id are skipped during reservation
        variant_items = [
            {'variant_id': item['variant_id'], 'quantity': item.get('quantity', 1)}
            for item in items
            if item.get('variant_id')
        ]
        logger.info(
            "Order %s payment initiation: %d items, %d with variant_id for stock reservation",
            order_id, len(items), len(variant_items)
        )

        # Format amount for Mollie (2 decimal string)
        amount_str = f"{outstanding:.2f}"

        # Build payment description
        event_id = order.get('event_id')
        if event_id:
            club_id = order.get('club_id', 'unknown')
            description = f"H-DCN Order {order_id[:8]} - {club_id}"
        else:
            description = f"H-DCN Webshop - Order {order_id[:8]}"

        # Build redirect URL based on order type
        if event_id:
            redirect_url = f"{REDIRECT_BASE_URL}/booking?order_id={order_id}&payment=complete"
        else:
            redirect_url = f"{REDIRECT_BASE_URL}/webshop?order_id={order_id}&payment=complete"

        # Transition payment_status using state machine
        current_payment_status = order.get('payment_status', 'unpaid')
        is_bank_transfer = (method == 'banktransfer')

        if is_bank_transfer:
            target_payment_status = 'awaiting_payment'
        else:
            target_payment_status = 'pending'

        try:
            transition_payment(current_payment_status, target_payment_status)
        except InvalidTransitionError as e:
            return create_error_response(400, 'Invalid payment status transition', {
                'current': e.current,
                'target': e.target,
                'allowed': e.allowed,
            })

        # Create Mollie payment (or mock if no valid API key)
        mollie_api_key = os.environ.get('MOLLIE_API_KEY', '')
        use_mock = not mollie_api_key or not mollie_api_key.startswith(('test_', 'live_'))

        if use_mock:
            # Mock mode: simulate payment initiation without Mollie
            logger.info(f"MOCK PAYMENT: No valid Mollie API key, simulating payment for order {order_id}")
            mock_payment_id = f"tr_mock_{uuid.uuid4().hex[:8]}"

            # Store payment record
            payment_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc).isoformat()

            # Bank transfers in mock mode: do NOT mark as paid (Req 2.6)
            # They stay in awaiting_payment until admin confirms receipt
            if is_bank_transfer:
                payment_record_status = 'open'
            else:
                payment_record_status = 'paid'

            payment_record = {
                'payment_id': payment_id,
                'order_id': order_id,
                'amount': outstanding,
                'status': payment_record_status,
                'provider': 'mock',
                'method': method,
                'mollie_payment_id': mock_payment_id,
                'created_at': now,
                'created_by': user_email,
            }
            if order.get('club_id'):
                payment_record['club_id'] = order['club_id']
            if variant_items:
                payment_record['variant_items'] = variant_items

            payments_table.put_item(Item=payment_record)

            if is_bank_transfer:
                # Bank transfer: update payment_status to awaiting_payment, do NOT mark as paid
                orders_table.update_item(
                    Key={'order_id': order_id},
                    UpdateExpression='SET payment_status = :ps, updated_at = :now',
                    ExpressionAttributeValues={
                        ':ps': target_payment_status,
                        ':now': now,
                    },
                )
                logger.info(
                    f"MOCK PAYMENT: Order {order_id} payment_status set to "
                    f"'awaiting_payment' (bank transfer - awaiting admin confirmation)"
                )

                # Build transfer instructions with order_number as reference (Req 3.7)
                order_number = order.get('order_number', order_id[:8])
                transfer_instructions = {
                    'reference': order_number,
                    'amount': float(outstanding),
                    'bank_name': 'H-DCN',
                }

                return create_success_response({
                    'payment_id': payment_id,
                    'checkout_url': None,
                    'amount': float(outstanding),
                    'method': method,
                    'mock': True,
                    'payment_status': 'awaiting_payment',
                    'transfer_instructions': transfer_instructions,
                    'message': 'Bank transfer initiated (awaiting payment confirmation)',
                }, status_code=201)
            else:
                # Online payment (iDEAL, credit card): mark as paid in mock mode
                orders_table.update_item(
                    Key={'order_id': order_id},
                    UpdateExpression='SET #s = :confirmed, payment_status = :paid, total_paid = :amount, updated_at = :now',
                    ExpressionAttributeNames={'#s': 'status'},
                    ExpressionAttributeValues={
                        ':confirmed': 'confirmed',
                        ':paid': 'paid',
                        ':amount': outstanding,
                        ':now': now,
                    },
                )

                logger.info(f"MOCK PAYMENT: Order {order_id} marked as paid (mock mode, online payment)")

                return create_success_response({
                    'payment_id': payment_id,
                    'checkout_url': None,
                    'amount': float(outstanding),
                    'method': method,
                    'mock': True,
                    'message': 'Payment simulated (no Mollie key configured)',
                }, status_code=201)

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
            'amount': outstanding,
            'status': 'pending',
            'provider': 'mollie',
            'method': method,
            'mollie_payment_id': mollie_result['mollie_payment_id'],
            'created_at': now,
            'created_by': user_email,
        }

        # Include club_id for event orders
        if order.get('club_id'):
            payment_record['club_id'] = order['club_id']

        # Store variant_items for stock reservation on payment confirmation
        # Works for both webshop and event orders — same flow regardless of product type
        if variant_items:
            payment_record['variant_items'] = variant_items

        payments_table.put_item(Item=payment_record)

        # Store mollie_payment_id on the order and update payment_status
        _update_order_payment_initiated(order_id, mollie_result['mollie_payment_id'], target_payment_status)

        # Check if this payment covers full outstanding (will transition to "paid")
        # Stock reservation will be triggered by the webhook on payment confirmation
        # using variant_id from order items (same flow for webshop and event orders)
        will_complete_payment = (outstanding >= total_amount - total_paid)
        if will_complete_payment and variant_items:
            logger.info(
                "Order %s: payment of %s covers full outstanding, "
                "stock reservation will trigger on confirmation for %d variants",
                order_id, amount_str, len(variant_items)
            )

        logger.info(
            "Created payment %s for order %s, amount=%s EUR, mollie_id=%s, payment_status=%s",
            payment_id, order_id, amount_str, mollie_result['mollie_payment_id'],
            target_payment_status
        )

        # Build response
        response_data = {
            'payment_id': payment_id,
            'checkout_url': mollie_result['checkout_url'],
            'amount': float(outstanding),
            'method': method,
            'mollie_payment_id': mollie_result['mollie_payment_id'],
            'payment_status': target_payment_status,
        }

        # For bank transfers, include transfer instructions with order_number as reference (Req 3.7)
        if is_bank_transfer:
            order_number = order.get('order_number', order_id[:8])
            response_data['transfer_instructions'] = {
                'reference': order_number,
                'amount': float(outstanding),
                'bank_name': 'H-DCN',
            }

        # Return checkout URL to frontend
        return create_success_response(response_data, status_code=201)

    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        logger.error(f"Error in pay_order: {str(e)}", exc_info=True)
        return create_error_response(500, 'Internal server error')


def _get_order(order_id):
    """Fetch order from Orders table by order_id."""
    try:
        response = orders_table.get_item(Key={'order_id': order_id})
        return response.get('Item')
    except ClientError as e:
        logger.error(f"Error fetching order {order_id}: {e}")
        raise


def _check_payment_authorization(order, user_email, user_roles, is_admin):
    """
    Verify the user is authorized to pay this order.

    Authorization rules:
    - Admin: can pay any order
    - Order owner (user_email match): can pay own orders
    - Event order delegate (primary/secondary): can pay their club's order

    Returns error response if unauthorized, None if authorized.
    """
    if is_admin:
        return None

    # Check if user is order owner
    order_email = order.get('user_email', '')
    if order_email and order_email.lower() == user_email.lower():
        return None

    # Check if user is a delegate for this event order
    delegates = order.get('delegates', {})
    primary = delegates.get('primary', '')
    secondary = delegates.get('secondary', '')

    if primary and user_email.lower() == primary.lower():
        return None
    if secondary and user_email.lower() == secondary.lower():
        return None

    # Check club membership for event orders
    if order.get('event_id') and order.get('club_id'):
        user_club_id = get_club_id(user_email)
        if user_club_id and user_club_id == order.get('club_id'):
            return None

    return create_error_response(403, 'Access denied: You cannot pay this order')


def _update_order_payment_initiated(order_id, mollie_payment_id, payment_status):
    """Store the Mollie payment ID and updated payment_status on the order."""
    try:
        orders_table.update_item(
            Key={'order_id': order_id},
            UpdateExpression='SET mollie_payment_id = :mid, payment_status = :ps, updated_at = :now',
            ExpressionAttributeValues={
                ':mid': mollie_payment_id,
                ':ps': payment_status,
                ':now': datetime.now(timezone.utc).isoformat(),
            }
        )
    except Exception as e:
        logger.error(f"Error updating order {order_id} with mollie_payment_id: {e}")
        # Non-critical — webhook can still find payment via Payments table


def _parse_body(event):
    """Parse JSON request body, return dict or None."""
    body = event.get('body')
    if not body:
        return None
    try:
        return json.loads(body)
    except (json.JSONDecodeError, TypeError):
        return None


def _trigger_stock_reservation(order):
    """
    Trigger stock reservation for all items in the order using variant_id.

    Extracts variant_id and quantity from order items and calls
    shared.stock_reservation.reserve_stock_for_order().

    Works for both webshop and event orders — same flow regardless of product type.
    Items without variant_id (legacy orders) are skipped.
    """
    order_id = order['order_id']
    items = order.get('items', [])

    if not items:
        logger.warning("Order %s has no items, skipping stock reservation", order_id)
        return

    # Build order_items list using variant_id from each item
    order_items = []
    for item in items:
        variant_id = item.get('variant_id')
        quantity = item.get('quantity', 0)
        if variant_id and quantity > 0:
            order_items.append({
                'variant_id': variant_id,
                'quantity': quantity,
            })

    if not order_items:
        logger.warning(
            "Order %s has no items with variant_id for stock reservation (legacy order?)",
            order_id
        )
        return

    try:
        results = reserve_stock_for_order(
            order_items=order_items,
            producten_table=producten_table,
            order_id=order_id,
        )
        for result in results:
            logger.info(
                "Stock reservation for order %s: variant=%s, qty=%d, status=%s",
                order_id, result['variant_id'], result['quantity'], result['status']
            )
    except InsufficientStockError as e:
        # Log but don't fail — payment is confirmed, stock issue needs admin attention
        logger.error(
            "Insufficient stock during reservation for order %s: variant=%s, "
            "available=%d, requested=%d",
            order_id, e.variant_id, e.available, e.requested
        )
    except StockReservationError as e:
        logger.error(
            "Stock reservation error for order %s: %s", order_id, str(e)
        )


def confirm_payment_and_reserve_stock(order_id, payment_amount):
    """
    Confirm payment and trigger stock reservation if order transitions to "paid".

    Called by the Mollie webhook or similar confirmation flow. Uses the same
    variant_id-based stock reservation for both webshop and event orders.

    Uses stock_reserved flag as idempotency guard to prevent double reservation.

    Args:
        order_id: The order ID receiving the confirmed payment.
        payment_amount: The confirmed payment amount (Decimal).

    Returns:
        dict with updated order status info, or None on error.
    """
    try:
        response = orders_table.get_item(Key={'order_id': order_id})
        order = response.get('Item')
        if not order:
            logger.error("Order %s not found during payment confirmation", order_id)
            return None

        total_amount = Decimal(str(order.get('total_amount', 0)))
        total_paid = Decimal(str(order.get('total_paid', 0))) + payment_amount
        previous_payment_status = order.get('payment_status', 'unpaid')

        # Determine new payment status
        if total_amount > 0 and total_paid >= total_amount:
            new_payment_status = 'paid'
        elif total_paid > 0:
            new_payment_status = 'partial'
        else:
            new_payment_status = 'unpaid'

        # Check if transitioning TO "paid"
        transitioning_to_paid = (
            new_payment_status == 'paid' and previous_payment_status != 'paid'
        )

        now = datetime.now(timezone.utc).isoformat()

        if transitioning_to_paid:
            # Atomic update with stock_reserved guard to prevent double reservation
            try:
                orders_table.update_item(
                    Key={'order_id': order_id},
                    UpdateExpression=(
                        'SET total_paid = :new_paid, '
                        'payment_status = :payment_status, '
                        'stock_reserved = :true_val, '
                        'updated_at = :now'
                    ),
                    ConditionExpression=(
                        'attribute_not_exists(stock_reserved) OR stock_reserved = :false_val'
                    ),
                    ExpressionAttributeValues={
                        ':new_paid': total_paid,
                        ':payment_status': new_payment_status,
                        ':true_val': True,
                        ':false_val': False,
                        ':now': now,
                    }
                )
                # Trigger stock reservation using variant_id from order items
                _trigger_stock_reservation(order)

            except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
                # stock_reserved already true — update payment status without reservation
                logger.info(
                    "Order %s already has stock_reserved=true, skipping reservation",
                    order_id
                )
                orders_table.update_item(
                    Key={'order_id': order_id},
                    UpdateExpression=(
                        'SET total_paid = :new_paid, '
                        'payment_status = :payment_status, '
                        'updated_at = :now'
                    ),
                    ExpressionAttributeValues={
                        ':new_paid': total_paid,
                        ':payment_status': new_payment_status,
                        ':now': now,
                    }
                )
        else:
            # Not transitioning to paid — standard update without stock reservation
            orders_table.update_item(
                Key={'order_id': order_id},
                UpdateExpression=(
                    'SET total_paid = :new_paid, '
                    'payment_status = :payment_status, '
                    'updated_at = :now'
                ),
                ExpressionAttributeValues={
                    ':new_paid': total_paid,
                    ':payment_status': new_payment_status,
                    ':now': now,
                }
            )

        return {
            'order_id': order_id,
            'total_paid': float(total_paid),
            'payment_status': new_payment_status,
            'stock_reserved': transitioning_to_paid,
        }

    except Exception as e:
        logger.error(
            "Error confirming payment for order %s: %s", order_id, str(e),
            exc_info=True
        )
        return None
