"""
Mollie webhook handler for the unified webshop/PresMeet payment pipeline.

POST /mollie-webhook — processes Mollie payment status callbacks.

Key design decisions:
- NO auth required (Mollie calls this endpoint externally)
- Always returns 200 for valid webhook calls (Mollie requirement)
- Uses shared.mollie_client.get_payment() to fetch current payment status
- Uses shared.stock_reservation.reserve_stock_for_order() when paid
- Supports TWO lookup paths:
  1. Payments table (PresMeet flow): mollie_payment_id → payment record → order
  2. Orders table (legacy webshop flow): mollie_payment_id directly on order
- Idempotent: guards stock reservation with conditional update (stock_reserved field)
- Only transitions order state forward (never backward): open → paid, open → failed

Requirements: 7.3, 7.4, 9.6, 9.7, 9.11
"""

import json
import os
import logging
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr, Key

# Import shared utilities
try:
    from shared.auth_utils import cors_headers
    from shared.mollie_client import get_payment, MollieError
    from shared.stock_reservation import (
        reserve_stock_for_order,
        StockReservationError,
        InsufficientStockError,
    )
    print("Using shared auth layer for mollie_webhook")
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("mollie_webhook")
    import sys
    sys.exit(0)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# DynamoDB resources
dynamodb = boto3.resource('dynamodb')
orders_table = dynamodb.Table(os.environ.get('ORDERS_TABLE_NAME', 'Orders'))
payments_table = dynamodb.Table(os.environ.get('PAYMENTS_TABLE_NAME', 'Payments'))
producten_table = dynamodb.Table(os.environ.get('PRODUCTEN_TABLE_NAME', 'Producten'))

# Payment statuses that indicate a terminal failure
FAILED_STATUSES = ("failed", "expired", "cancelled")

# Order payment statuses that are already terminal (no backward transitions)
TERMINAL_PAID_STATUSES = ("paid",)
TERMINAL_FAILED_STATUSES = ("payment_failed",)


def _now_iso() -> str:
    """Return current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def _extract_payment_id(event: dict) -> str | None:
    """
    Extract Mollie payment ID from the webhook request body.

    Mollie sends the payment ID as form-encoded body (id=tr_xxx) or JSON {"id": "tr_xxx"}.
    API Gateway may base64-encode the body.

    Returns:
        The payment ID string, or None if not found.
    """
    body = event.get('body', '')
    if not body:
        return None

    # Decode base64 if needed (API Gateway behavior)
    if event.get('isBase64Encoded', False):
        import base64
        body = base64.b64decode(body).decode('utf-8')

    # Try form-encoded first (Mollie's default format)
    try:
        from urllib.parse import parse_qs
        parsed = parse_qs(body)
        if 'id' in parsed:
            return parsed['id'][0]
    except Exception:
        pass

    # Fallback: try JSON body
    try:
        json_body = json.loads(body)
        return json_body.get('id')
    except (json.JSONDecodeError, TypeError):
        pass

    return None


def _find_payment_record(mollie_payment_id: str) -> dict | None:
    """
    Find a payment record in the Payments table by mollie_payment_id.

    Uses a scan with filter since there's no GSI on mollie_payment_id.

    Returns:
        The payment record, or None if not found.
    """
    try:
        response = payments_table.scan(
            FilterExpression=Attr('mollie_payment_id').eq(mollie_payment_id)
        )
        items = response.get('Items', [])

        while 'LastEvaluatedKey' in response:
            response = payments_table.scan(
                FilterExpression=Attr('mollie_payment_id').eq(mollie_payment_id),
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            items.extend(response.get('Items', []))

        if items:
            return items[0]
        return None
    except Exception as e:
        logger.error(
            "Error finding payment record by mollie_payment_id %s: %s",
            mollie_payment_id, str(e)
        )
        return None


def _find_order_by_mollie_payment_id(mollie_payment_id: str) -> dict | None:
    """
    Find an order by scanning the Orders table for mollie_payment_id.

    This is the legacy webshop lookup path where mollie_payment_id is stored
    directly on the order record.

    Returns:
        The order record, or None if not found.
    """
    try:
        response = orders_table.scan(
            FilterExpression=Attr('mollie_payment_id').eq(mollie_payment_id)
        )
        items = response.get('Items', [])

        while 'LastEvaluatedKey' in response:
            response = orders_table.scan(
                FilterExpression=Attr('mollie_payment_id').eq(mollie_payment_id),
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            items.extend(response.get('Items', []))

        if items:
            return items[0]
        return None
    except Exception as e:
        logger.error(
            "Error finding order by mollie_payment_id %s: %s",
            mollie_payment_id, str(e)
        )
        return None


def _get_order(order_id: str) -> dict | None:
    """Fetch an order by order_id."""
    try:
        response = orders_table.get_item(Key={'order_id': order_id})
        return response.get('Item')
    except Exception as e:
        logger.error("Error fetching order %s: %s", order_id, str(e))
        return None


def _get_all_payments_for_order(order_id: str) -> list:
    """
    Get all payment records for a given order from the Payments table.

    Returns:
        List of payment records for the order.
    """
    try:
        response = payments_table.scan(
            FilterExpression=Attr('order_id').eq(order_id)
        )
        items = response.get('Items', [])

        while 'LastEvaluatedKey' in response:
            response = payments_table.scan(
                FilterExpression=Attr('order_id').eq(order_id),
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            items.extend(response.get('Items', []))

        return items
    except Exception as e:
        logger.error("Error fetching payments for order %s: %s", order_id, str(e))
        return []


def _calculate_total_paid(payments: list) -> Decimal:
    """
    Calculate total paid from all payment records with status "paid".

    Returns:
        Sum of amounts for all paid payment records.
    """
    total = Decimal('0')
    for payment in payments:
        if payment.get('status') == 'paid':
            total += Decimal(str(payment.get('amount', 0)))
    return total


def _determine_payment_status(total_paid: Decimal, total_amount: Decimal) -> str:
    """
    Determine payment_status based on total_paid vs order total.

    Returns:
        "paid" if total_paid >= total_amount (and total_amount > 0)
        "partial" if 0 < total_paid < total_amount
        "unpaid" otherwise
    """
    if total_amount > 0 and total_paid >= total_amount:
        return 'paid'
    elif total_paid > 0:
        return 'partial'
    return 'unpaid'


def _update_payment_record_status(payment_id: str, new_status: str) -> None:
    """Update a payment record's status in the Payments table."""
    try:
        payments_table.update_item(
            Key={'payment_id': payment_id},
            UpdateExpression='SET #s = :status, updated_at = :now',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={
                ':status': new_status,
                ':now': _now_iso(),
            }
        )
        logger.info("Payment record %s updated to status '%s'", payment_id, new_status)
    except Exception as e:
        logger.error("Error updating payment record %s: %s", payment_id, str(e))
        raise


def _update_order_payment_totals(
    order_id: str, total_paid: Decimal, payment_status: str
) -> None:
    """
    Update an order's total_paid and payment_status.

    This is used for the PresMeet flow where payment tracking is via the
    Payments table rather than directly on the order.
    """
    try:
        orders_table.update_item(
            Key={'order_id': order_id},
            UpdateExpression=(
                'SET total_paid = :total_paid, '
                'payment_status = :payment_status, '
                'updated_at = :now'
            ),
            ExpressionAttributeValues={
                ':total_paid': total_paid,
                ':payment_status': payment_status,
                ':now': _now_iso(),
            }
        )
        logger.info(
            "Order %s updated: total_paid=%s, payment_status=%s",
            order_id, total_paid, payment_status
        )
    except Exception as e:
        logger.error("Error updating order %s payment totals: %s", order_id, str(e))
        raise


def _handle_presmeet_payment(
    mollie_payment_id: str, mollie_status: str, payment_record: dict
) -> dict:
    """
    Handle payment callback for PresMeet orders (Payments table flow).

    1. Update payment record status in Payments table
    2. Fetch all payments for the order
    3. Recalculate total_paid (sum of all "paid" payments)
    4. Determine and update order payment_status
    5. Trigger stock reservation if transitioning to "paid"

    Returns:
        Response body dict.
    """
    payment_id = payment_record['payment_id']
    order_id = payment_record['order_id']

    # Map Mollie status to our payment record status
    if mollie_status == 'paid':
        new_payment_status = 'paid'
    elif mollie_status in FAILED_STATUSES:
        new_payment_status = 'failed'
    else:
        # Intermediate status (open, pending) — no update needed
        logger.info(
            "Mollie payment %s has intermediate status '%s', no update for PresMeet payment",
            mollie_payment_id, mollie_status
        )
        return {'status': 'ok', 'detail': 'intermediate status, no update'}

    # Step 1: Update payment record status
    _update_payment_record_status(payment_id, new_payment_status)

    # Step 2: Fetch the order
    order = _get_order(order_id)
    if not order:
        logger.warning("Order %s not found for payment %s", order_id, payment_id)
        return {'status': 'error', 'reason': 'order not found for payment'}

    # Step 3: Fetch all payments for this order and recalculate total_paid
    all_payments = _get_all_payments_for_order(order_id)
    total_paid = _calculate_total_paid(all_payments)

    # Step 4: Determine payment_status
    total_amount = Decimal(str(order.get('total_amount', 0)))
    payment_status = _determine_payment_status(total_paid, total_amount)

    previous_payment_status = order.get('payment_status', 'unpaid')

    # Step 5: Update order with new totals
    _update_order_payment_totals(order_id, total_paid, payment_status)

    # Step 6: Trigger stock reservation if transitioning to "paid"
    if payment_status == 'paid' and previous_payment_status != 'paid':
        _trigger_stock_reservation_with_guard(order)

    logger.info(
        "PresMeet payment processed: order=%s, total_paid=%s, status=%s→%s",
        order_id, total_paid, previous_payment_status, payment_status
    )

    return {'status': 'ok', 'flow': 'presmeet'}


def _trigger_stock_reservation_with_guard(order: dict) -> None:
    """
    Trigger stock reservation with idempotency guard (stock_reserved flag).

    Uses conditional update to ensure stock is only reserved once.
    """
    order_id = order['order_id']

    try:
        orders_table.update_item(
            Key={'order_id': order_id},
            UpdateExpression='SET stock_reserved = :true_val',
            ConditionExpression=(
                'attribute_not_exists(stock_reserved) OR stock_reserved = :false_val'
            ),
            ExpressionAttributeValues={
                ':true_val': True,
                ':false_val': False,
            }
        )
        # Condition passed — safe to reserve stock
        _trigger_stock_reservation(order)
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        logger.info(
            "Order %s already has stock_reserved=true (idempotent)", order_id
        )


def _can_transition_to_paid(current_status: str) -> bool:
    """Check if order can transition to paid (only forward transitions)."""
    if current_status in TERMINAL_PAID_STATUSES:
        return False
    return True


def _can_transition_to_failed(current_status: str) -> bool:
    """Check if order can transition to payment_failed (only forward transitions)."""
    if current_status in TERMINAL_PAID_STATUSES:
        return False
    if current_status in TERMINAL_FAILED_STATUSES:
        return False
    return True


def _update_order_to_paid(order: dict) -> bool:
    """
    Update order payment_status to "paid" with conditional guard on stock_reserved.

    Returns:
        True if update succeeded (stock reservation should proceed),
        False if order was already paid/reserved (idempotent).
    """
    order_id = order['order_id']

    try:
        orders_table.update_item(
            Key={'order_id': order_id},
            UpdateExpression=(
                'SET payment_status = :paid, '
                'stock_reserved = :true_val, '
                'updated_at = :now'
            ),
            ConditionExpression=(
                'attribute_not_exists(stock_reserved) OR stock_reserved = :false_val'
            ),
            ExpressionAttributeValues={
                ':paid': 'paid',
                ':true_val': True,
                ':false_val': False,
                ':now': _now_iso(),
            }
        )
        logger.info("Order %s payment_status updated to 'paid'", order_id)
        return True
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        logger.info("Order %s already has stock_reserved=true (idempotent)", order_id)
        return False
    except Exception as e:
        logger.error("Error updating order %s to paid: %s", order_id, str(e))
        raise


def _update_order_to_failed(order: dict) -> None:
    """Update order payment_status to 'payment_failed'."""
    order_id = order['order_id']

    try:
        orders_table.update_item(
            Key={'order_id': order_id},
            UpdateExpression='SET payment_status = :status, updated_at = :now',
            ExpressionAttributeValues={
                ':status': 'payment_failed',
                ':now': _now_iso(),
            }
        )
        logger.info("Order %s payment_status updated to 'payment_failed'", order_id)
    except Exception as e:
        logger.error("Error updating order %s to payment_failed: %s", order_id, str(e))
        raise


def _trigger_stock_reservation(order: dict) -> None:
    """
    Trigger stock reservation for all items in the order.

    Extracts variant_id and quantity from order items and calls
    shared.stock_reservation.reserve_stock_for_order().
    """
    order_id = order['order_id']
    items = order.get('items', [])

    if not items:
        logger.warning("Order %s has no items, skipping stock reservation", order_id)
        return

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
        logger.warning("Order %s has no valid variant items for stock reservation", order_id)
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
        logger.error(
            "Insufficient stock during reservation for order %s: variant=%s, "
            "available=%d, requested=%d",
            order_id, e.variant_id, e.available, e.requested
        )
    except StockReservationError as e:
        logger.error(
            "Stock reservation error for order %s: %s", order_id, str(e)
        )


def _handle_legacy_webshop_payment(
    mollie_payment_id: str, mollie_status: str, order: dict
) -> dict:
    """
    Handle payment callback for legacy webshop orders (mollie_payment_id on order).

    This is the original flow where mollie_payment_id is stored directly on the
    order record.

    Returns:
        Response body dict.
    """
    order_id = order['order_id']
    current_payment_status = order.get('payment_status', '')

    if mollie_status == 'paid':
        if _can_transition_to_paid(current_payment_status):
            should_reserve = _update_order_to_paid(order)
            if should_reserve:
                _trigger_stock_reservation(order)
        else:
            logger.info(
                "Order %s already in terminal status '%s', skipping paid transition",
                order_id, current_payment_status
            )

    elif mollie_status in FAILED_STATUSES:
        if _can_transition_to_failed(current_payment_status):
            _update_order_to_failed(order)
        else:
            logger.info(
                "Order %s in status '%s', cannot transition to failed",
                order_id, current_payment_status
            )
    else:
        logger.info(
            "Mollie payment %s has intermediate status '%s', no order update",
            mollie_payment_id, mollie_status
        )

    return {'status': 'ok', 'flow': 'webshop'}


def lambda_handler(event, context):
    """
    Mollie webhook handler.

    - No Cognito auth (public endpoint called by Mollie)
    - Receives Mollie payment ID via form-encoded or JSON POST body
    - Fetches payment status from Mollie API via shared.mollie_client
    - Supports two lookup paths:
      1. Payments table (PresMeet): updates payment record + recalculates order totals
      2. Orders table (webshop): updates order payment_status directly
    - Always returns 200 to Mollie (Mollie requirement)
    - Idempotent: re-processing same payment ID produces same final state
    """
    try:
        # Handle OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': cors_headers(),
                'body': ''
            }

        # Extract Mollie payment ID from request body
        mollie_payment_id = _extract_payment_id(event)

        if not mollie_payment_id:
            logger.warning("No Mollie payment ID found in webhook request body")
            return {
                'statusCode': 200,
                'headers': cors_headers(),
                'body': json.dumps({'status': 'ignored', 'reason': 'no payment id'})
            }

        logger.info("Processing Mollie webhook for payment: %s", mollie_payment_id)

        # Fetch current payment status from Mollie API
        try:
            mollie_payment = get_payment(mollie_payment_id)
        except MollieError as e:
            logger.error("Failed to fetch Mollie payment %s: %s", mollie_payment_id, e.reason)
            return {
                'statusCode': 200,
                'headers': cors_headers(),
                'body': json.dumps({'status': 'error', 'reason': 'mollie api unavailable'})
            }

        mollie_status = mollie_payment.get('status', '')
        logger.info("Mollie payment %s status: %s", mollie_payment_id, mollie_status)

        # Path 1: Check Payments table first (PresMeet flow)
        payment_record = _find_payment_record(mollie_payment_id)
        if payment_record:
            logger.info(
                "Found payment record %s in Payments table (PresMeet flow)",
                payment_record['payment_id']
            )
            result = _handle_presmeet_payment(
                mollie_payment_id, mollie_status, payment_record
            )
            return {
                'statusCode': 200,
                'headers': cors_headers(),
                'body': json.dumps(result)
            }

        # Path 2: Check Orders table (legacy webshop flow)
        order = _find_order_by_mollie_payment_id(mollie_payment_id)
        if order:
            logger.info(
                "Found order %s via mollie_payment_id in Orders table (webshop flow)",
                order['order_id']
            )
            result = _handle_legacy_webshop_payment(
                mollie_payment_id, mollie_status, order
            )
            return {
                'statusCode': 200,
                'headers': cors_headers(),
                'body': json.dumps(result)
            }

        # Neither path found a match
        logger.warning("No payment record or order found for mollie_payment_id %s", mollie_payment_id)
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({'status': 'ignored', 'reason': 'order not found'})
        }

    except Exception as e:
        # Always return 200 to Mollie to prevent retry flooding
        logger.error("Error processing Mollie webhook: %s", str(e))
        import traceback
        logger.error("Traceback: %s", traceback.format_exc())
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({'status': 'error', 'reason': 'internal error'})
        }
