"""
Admin record payment handler.

POST /admin/payments — records a manual payment for an order and recalculates
payment_status. Triggers stock reservation when payment transitions to "paid".

Key design decisions:
- Recalculates total_paid = sum of all payments for the order
- payment_status: "paid" if total_paid >= total_amount, "partial" if 0 < total_paid < total
- Stock reservation triggered ONLY on transition TO "paid" (not if already paid)
- Uses stock_reserved flag as idempotency guard (same pattern as mollie_webhook)
- Requires Products_CRUD permission

Requirements: 9.10
"""

import json
import logging
import os
import traceback
import uuid
import boto3
from botocore.exceptions import ClientError
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
    from shared.stock_reservation import (
        reserve_stock_for_order,
        StockReservationError,
        InsufficientStockError,
    )
    print("Using shared auth layer")
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("admin_record_payment")
    import sys
    sys.exit(0)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
orders_table_name = os.environ.get('ORDERS_TABLE_NAME', 'Orders')
orders_table = dynamodb.Table(orders_table_name)
producten_table_name = os.environ.get('PRODUCTEN_TABLE_NAME', 'Producten')
producten_table = dynamodb.Table(producten_table_name)


def _now_iso() -> str:
    """Return current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def _convert_decimals(obj):
    """Recursively convert Decimal values to int or float for JSON serialization."""
    if isinstance(obj, dict):
        return {k: _convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_decimals(item) for item in obj]
    elif isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    return obj


def _calculate_total_paid(order: dict, new_payment_amount: Decimal) -> Decimal:
    """
    Calculate total paid by summing all existing payments plus the new one.

    Recalculates from the payments list to avoid floating-point drift from
    incremental addition.
    """
    existing_payments = order.get('payments', [])
    total = Decimal('0')
    for payment in existing_payments:
        total += Decimal(str(payment.get('amount', 0)))
    total += new_payment_amount
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
        logger.warning(
            "Order %s has no valid variant items for stock reservation", order_id
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
            return create_error_response(
                400, 'order_id is required',
                details={'error_code': 'VALIDATION_ERROR', 'field': 'order_id'}
            )
        if amount is None or not isinstance(amount, (int, float)):
            return create_error_response(
                400, 'amount must be a number',
                details={'error_code': 'VALIDATION_ERROR', 'field': 'amount'}
            )
        if amount < 0.01 or amount > 999999.99:
            return create_error_response(
                400, 'amount must be between 0.01 and 999999.99',
                details={'error_code': 'VALIDATION_ERROR', 'field': 'amount'}
            )
        if not date:
            return create_error_response(
                400, 'date is required (ISO 8601 format)',
                details={'error_code': 'VALIDATION_ERROR', 'field': 'date'}
            )
        if description and len(description) > 255:
            return create_error_response(
                400, 'description must be 255 characters or less',
                details={'error_code': 'VALIDATION_ERROR', 'field': 'description'}
            )

        # Validate date format
        try:
            datetime.fromisoformat(date.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return create_error_response(
                400, 'date must be valid ISO 8601 format',
                details={'error_code': 'VALIDATION_ERROR', 'field': 'date'}
            )

        # Get order
        response = orders_table.get_item(Key={'order_id': order_id})
        if 'Item' not in response:
            return create_error_response(404, 'Order not found')

        order = response['Item']
        previous_payment_status = order.get('payment_status', 'unpaid')

        # Create payment record
        payment_id = f"pay_{uuid.uuid4().hex[:12]}"
        now = _now_iso()
        payment_amount = Decimal(str(amount))

        payment_record = {
            'payment_id': payment_id,
            'order_id': order_id,
            'amount': payment_amount,
            'date': date,
            'description': description,
            'recorded_by': user_email,
            'created_at': now
        }

        # Recalculate total_paid from all payments (not incremental)
        total_paid = _calculate_total_paid(order, payment_amount)
        total_amount = Decimal(str(order.get('total_amount', 0)))

        # Determine new payment_status
        new_payment_status = _determine_payment_status(total_paid, total_amount)

        # Check if this is a transition TO "paid"
        transitioning_to_paid = (
            new_payment_status == 'paid' and previous_payment_status != 'paid'
        )

        # Update order with conditional stock_reserved guard if transitioning to paid
        if transitioning_to_paid:
            # Use conditional update to set stock_reserved = true atomically
            # This prevents double stock reservation on concurrent requests
            try:
                orders_table.update_item(
                    Key={'order_id': order_id},
                    UpdateExpression=(
                        'SET amount_paid = :new_paid, '
                        'payment_status = :payment_status, '
                        'stock_reserved = :true_val, '
                        'updated_at = :now, '
                        'payments = list_append(if_not_exists(payments, :empty_list), :payment_entry)'
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
                        ':payment_entry': [payment_record],
                        ':empty_list': []
                    }
                )
                # Trigger stock reservation
                _trigger_stock_reservation(order)

            except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
                # stock_reserved already true — still record the payment but skip reservation
                logger.info(
                    "Order %s already has stock_reserved=true, recording payment without reservation",
                    order_id
                )
                orders_table.update_item(
                    Key={'order_id': order_id},
                    UpdateExpression=(
                        'SET amount_paid = :new_paid, '
                        'payment_status = :payment_status, '
                        'updated_at = :now, '
                        'payments = list_append(if_not_exists(payments, :empty_list), :payment_entry)'
                    ),
                    ExpressionAttributeValues={
                        ':new_paid': total_paid,
                        ':payment_status': new_payment_status,
                        ':now': now,
                        ':payment_entry': [payment_record],
                        ':empty_list': []
                    }
                )
        else:
            # Not transitioning to paid — standard update without stock reservation
            orders_table.update_item(
                Key={'order_id': order_id},
                UpdateExpression=(
                    'SET amount_paid = :new_paid, '
                    'payment_status = :payment_status, '
                    'updated_at = :now, '
                    'payments = list_append(if_not_exists(payments, :empty_list), :payment_entry)'
                ),
                ExpressionAttributeValues={
                    ':new_paid': total_paid,
                    ':payment_status': new_payment_status,
                    ':now': now,
                    ':payment_entry': [payment_record],
                    ':empty_list': []
                }
            )

        return create_success_response(_convert_decimals({
            'payment': payment_record,
            'order_id': order_id,
            'new_amount_paid': total_paid,
            'payment_status': new_payment_status,
            'message': 'Payment recorded successfully'
        }))

    except json.JSONDecodeError:
        return create_error_response(
            400, 'Invalid JSON in request body',
            details={'error_code': 'INVALID_JSON'}
        )
    except ClientError as e:
        logger.error(
            "DynamoDB ClientError in admin_record_payment: %s\n%s",
            str(e), traceback.format_exc()
        )
        return create_error_response(
            500, 'Internal server error',
            details={'error_code': 'DYNAMO_ERROR'}
        )
    except Exception as e:
        logger.error(
            "Unexpected error in admin_record_payment: %s\n%s",
            str(e), traceback.format_exc()
        )
        return create_error_response(
            500, 'Internal server error',
            details={'error_code': 'INTERNAL_ERROR'}
        )
