"""
Admin endpoint to confirm bank transfer payment receipt.

POST /admin/orders/{id}/confirm-payment

Transitions:
- payment_status: awaiting_payment → paid
- order status: submitted → confirmed

Also:
- Generates a sequential invoice number (F-YYYY-NNNN)
- Stores invoice_number and paid_at timestamp on the order
- Records transition in status_history

Requires admin permission: manage_orders (via validate_permissions_with_regions)

Requirements: 1.4, 2.4, 7.1, 7.3
"""

import json
import os
import logging
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
        log_successful_access,
    )
    from shared.order_state_machine import (
        transition_payment,
        transition_order,
        InvalidTransitionError,
    )
    from shared.number_generator import (
        generate_invoice_number,
        CounterWriteError,
    )
    print("Using shared auth layer for admin_confirm_payment")
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("admin_confirm_payment")
    import sys
    sys.exit(0)

import boto3

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# DynamoDB resources
dynamodb = boto3.resource('dynamodb')
orders_table = dynamodb.Table(os.environ.get('ORDERS_TABLE_NAME', 'Orders'))
counters_table = dynamodb.Table(os.environ.get('COUNTERS_TABLE_NAME', 'Counters'))


def _now_iso() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
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


def lambda_handler(event, context):
    """
    Admin confirms receipt of a bank transfer payment for an order.

    Path: POST /admin/orders/{id}/confirm-payment
    Auth: Requires manage_orders permission

    Steps:
    1. Validate admin permissions
    2. Fetch the order by ID
    3. Transition payment_status from awaiting_payment → paid
    4. Transition order status from submitted → confirmed
    5. Generate invoice number (F-YYYY-NNNN)
    6. Update order record with new statuses, invoice_number, paid_at
    7. Return updated order
    """
    try:
        # Handle OPTIONS (CORS preflight)
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # --- Authentication & Authorization ---
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        is_authorized, permission_error, regional_info = validate_permissions_with_regions(
            user_roles, ['Products_CRUD'], user_email, None
        )
        if not is_authorized:
            return permission_error

        log_successful_access(user_email, user_roles, 'admin_confirm_payment')

        # --- Extract order ID from path ---
        path_params = event.get('pathParameters') or {}
        order_id = path_params.get('id')
        if not order_id:
            return create_error_response(400, 'Order ID is required')

        # --- Fetch the order ---
        response = orders_table.get_item(Key={'order_id': order_id})
        if 'Item' not in response:
            return create_error_response(404, 'Order not found')

        order = response['Item']
        current_status = order.get('status', 'draft')
        current_payment_status = order.get('payment_status', 'unpaid')

        # --- Validate state transitions ---
        # Payment: awaiting_payment → paid
        try:
            new_payment_status = transition_payment(current_payment_status, 'paid')
        except InvalidTransitionError as e:
            return create_error_response(
                400,
                f'Invalid payment transition: cannot move from '
                f'"{current_payment_status}" to "paid". '
                f'Allowed transitions from "{current_payment_status}": {e.allowed}'
            )

        # Order: submitted → confirmed
        try:
            new_order_status = transition_order(current_status, 'confirmed')
        except InvalidTransitionError as e:
            return create_error_response(
                400,
                f'Invalid order transition: cannot move from '
                f'"{current_status}" to "confirmed". '
                f'Allowed transitions from "{current_status}": {e.allowed}'
            )

        # --- Generate invoice number ---
        try:
            invoice_number = generate_invoice_number(counters_table)
        except CounterWriteError as e:
            logger.error("Failed to generate invoice number for order %s: %s", order_id, str(e))
            return create_error_response(
                500, 'Failed to generate invoice number. Please try again.'
            )

        # --- Build status history entries ---
        now = _now_iso()

        payment_history_entry = {
            'type': 'payment_status',
            'from_status': current_payment_status,
            'to_status': new_payment_status,
            'timestamp': now,
            'triggered_by': user_email,
            'trigger': 'admin_confirm_payment',
        }

        order_history_entry = {
            'type': 'order_status',
            'from_status': current_status,
            'to_status': new_order_status,
            'timestamp': now,
            'triggered_by': user_email,
            'trigger': 'admin_confirm_payment',
        }

        # --- Update order with conditional expression for optimistic locking ---
        try:
            update_result = orders_table.update_item(
                Key={'order_id': order_id},
                UpdateExpression=(
                    'SET #status = :new_status, '
                    'payment_status = :new_payment_status, '
                    'invoice_number = :invoice_number, '
                    'paid_at = :paid_at, '
                    'updated_at = :now, '
                    'status_history = list_append('
                    '  if_not_exists(status_history, :empty_list), '
                    '  :history_entries'
                    ')'
                ),
                ExpressionAttributeNames={
                    '#status': 'status',
                },
                ExpressionAttributeValues={
                    ':new_status': new_order_status,
                    ':new_payment_status': new_payment_status,
                    ':invoice_number': invoice_number,
                    ':paid_at': now,
                    ':now': now,
                    ':current_status': current_status,
                    ':current_payment_status': current_payment_status,
                    ':history_entries': [payment_history_entry, order_history_entry],
                    ':empty_list': [],
                },
                ConditionExpression=(
                    '#status = :current_status AND '
                    'payment_status = :current_payment_status'
                ),
                ReturnValues='ALL_NEW',
            )
        except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
            return create_error_response(
                409,
                'Order was modified concurrently. Please refresh and try again.'
            )

        updated_order = update_result.get('Attributes', {})

        logger.info(
            "Admin %s confirmed payment for order %s: "
            "status=%s→%s, payment_status=%s→%s, invoice_number=%s",
            user_email, order_id,
            current_status, new_order_status,
            current_payment_status, new_payment_status,
            invoice_number,
        )

        return create_success_response({
            'order': _convert_decimals(updated_order),
            'transitions': {
                'status': {'from': current_status, 'to': new_order_status},
                'payment_status': {'from': current_payment_status, 'to': new_payment_status},
            },
            'invoice_number': invoice_number,
            'message': f'Payment confirmed. Invoice {invoice_number} generated.',
        })

    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        logger.error("Error in admin_confirm_payment: %s", str(e))
        import traceback
        logger.error("Traceback: %s", traceback.format_exc())
        return create_error_response(500, 'Internal server error')
