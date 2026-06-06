"""
Mollie webhook handler for the unified webshop/PresMeet payment pipeline.

POST /mollie-webhook — processes Mollie payment status callbacks.

Key design decisions:
- NO auth required (Mollie calls this endpoint externally)
- Always returns 200 for valid webhook calls (Mollie requirement)
- Uses shared.mollie_client.get_payment() to fetch current payment status
- Uses shared.stock_reservation.reserve_stock_for_order() when paid
- Idempotent: uses mollie_payment_id as lookup key, guards stock reservation
  with conditional update (stock_reserved field on order)
- Only transitions order state forward (never backward): open → paid, open → failed

Requirements: 9.6, 9.7, 9.11
"""

import json
import os
import logging
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Attr

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


def _find_order_by_mollie_payment_id(mollie_payment_id: str) -> dict | None:
    """
    Find an order by scanning the Orders table for mollie_payment_id.

    Args:
        mollie_payment_id: The Mollie payment ID to look up.

    Returns:
        The order record, or None if not found.
    """
    try:
        response = orders_table.scan(
            FilterExpression=Attr('mollie_payment_id').eq(mollie_payment_id)
        )
        items = response.get('Items', [])

        # Handle pagination
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
        logger.error("Error finding order by mollie_payment_id %s: %s", mollie_payment_id, str(e))
        return None


def _can_transition_to_paid(current_status: str) -> bool:
    """Check if order can transition to paid (only forward transitions)."""
    # Already paid — idempotent, no action needed
    if current_status in TERMINAL_PAID_STATUSES:
        return False
    # Already marked as failed — we still allow transition to paid
    # (Mollie may retry and succeed after initial failure report)
    # Only "paid" is truly terminal for the paid path
    return True


def _can_transition_to_failed(current_status: str) -> bool:
    """Check if order can transition to payment_failed (only forward transitions)."""
    # Already paid — never go backward
    if current_status in TERMINAL_PAID_STATUSES:
        return False
    # Already failed — idempotent
    if current_status in TERMINAL_FAILED_STATUSES:
        return False
    return True


def _update_order_to_paid(order: dict) -> bool:
    """
    Update order payment_status to "paid" with conditional guard on stock_reserved.

    Uses a conditional update to ensure stock reservation is only triggered once:
    - Sets payment_status = "paid"
    - Sets stock_reserved = true (only if not already true)

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
        # stock_reserved is already True — order was already processed
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

    # Build order_items list for stock_reservation module
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
        # Log but don't fail the webhook — payment is confirmed, stock issue
        # needs admin attention
        logger.error(
            "Insufficient stock during reservation for order %s: variant=%s, "
            "available=%d, requested=%d",
            order_id, e.variant_id, e.available, e.requested
        )
    except StockReservationError as e:
        logger.error(
            "Stock reservation error for order %s: %s", order_id, str(e)
        )


def lambda_handler(event, context):
    """
    Mollie webhook handler.

    - No Cognito auth (public endpoint called by Mollie)
    - Receives Mollie payment ID via form-encoded or JSON POST body
    - Fetches payment status from Mollie API via shared.mollie_client
    - Updates order payment_status and triggers stock reservation if paid
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

        # Fetch current payment status from Mollie API using shared client
        try:
            mollie_payment = get_payment(mollie_payment_id)
        except MollieError as e:
            logger.error("Failed to fetch Mollie payment %s: %s", mollie_payment_id, e.reason)
            # Return 200 to prevent Mollie from retrying endlessly
            return {
                'statusCode': 200,
                'headers': cors_headers(),
                'body': json.dumps({'status': 'error', 'reason': 'mollie api unavailable'})
            }

        mollie_status = mollie_payment.get('status', '')
        logger.info("Mollie payment %s status: %s", mollie_payment_id, mollie_status)

        # Find our order by mollie_payment_id
        order = _find_order_by_mollie_payment_id(mollie_payment_id)
        if not order:
            logger.warning("No order found for mollie_payment_id %s", mollie_payment_id)
            return {
                'statusCode': 200,
                'headers': cors_headers(),
                'body': json.dumps({'status': 'ignored', 'reason': 'order not found'})
            }

        order_id = order['order_id']
        current_payment_status = order.get('payment_status', '')
        logger.info(
            "Order %s current payment_status: %s", order_id, current_payment_status
        )

        # Process based on Mollie payment status
        if mollie_status == 'paid':
            if _can_transition_to_paid(current_payment_status):
                # Update order to paid with conditional guard on stock_reserved
                should_reserve = _update_order_to_paid(order)
                if should_reserve:
                    # Trigger stock reservation (only once due to conditional update)
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
            # Other statuses (open, pending, authorized): log but don't change order
            logger.info(
                "Mollie payment %s has intermediate status '%s', no order update",
                mollie_payment_id, mollie_status
            )

        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({'status': 'ok'})
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
