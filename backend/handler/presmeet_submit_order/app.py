"""
PresMeet Submit Order Handler.

POST /presmeet/orders/{id}/submit

Validates and submits a PresMeet order. Runs full validation including:
- Item field validation (required fields, type constraints)
- Purchase rules (min/max per club)
- Event-level capacity constraints

On success: sets status=submitted, records submitted_at.
On failure: returns all validation errors, preserves status as draft.

Requirements: 3, 6
"""

import json
import os
import logging
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

# Import shared auth layer
try:
    from shared.auth_utils import (
        extract_user_credentials,
        cors_headers,
        handle_options_request,
        create_error_response,
        create_success_response,
        log_successful_access,
    )
    from shared.club_identity import get_club_id, has_presmeet_access, is_presmeet_admin
    from shared.presmeet_validation import validate_submission
    print("Using shared auth layer for presmeet_submit_order")
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("presmeet_submit_order")
    import sys
    sys.exit(0)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# DynamoDB resources
dynamodb = boto3.resource('dynamodb')
orders_table = dynamodb.Table(os.environ.get('ORDERS_TABLE_NAME', 'Orders'))
events_table = dynamodb.Table(os.environ.get('EVENTS_TABLE_NAME', 'Events'))
producten_table = dynamodb.Table(os.environ.get('PRODUCTEN_TABLE_NAME', 'Producten'))

# GSI name for event+club queries
EVENT_CLUB_INDEX = 'event-club-index'


def lambda_handler(event, context):
    """Main handler for POST /presmeet/orders/{id}/submit."""
    try:
        # Handle OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # --- Authentication ---
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # Gate: require Regio_Pressmeet or Regio_All
        if not has_presmeet_access(user_roles):
            return create_error_response(403, 'PresMeet access required', {
                'required_roles': ['Regio_Pressmeet', 'Regio_All'],
            })

        log_successful_access(user_email, user_roles, 'presmeet_submit_order')

        # --- Extract order_id from path ---
        path_params = event.get('pathParameters') or {}
        order_id = path_params.get('id')
        if not order_id:
            return create_error_response(400, 'Order ID is required in path')

        # Determine admin status
        is_admin = is_presmeet_admin(user_roles)

        # --- Fetch the order ---
        order = _get_order(order_id)
        if not order:
            return create_error_response(404, 'Order not found')

        # --- Authorization: check user is delegate or admin ---
        if not is_admin:
            club_id = get_club_id(user_email)
            if not club_id:
                return create_error_response(
                    403, 'Missing club assignment. Please complete onboarding first.'
                )
            if order.get('club_id') != club_id:
                return create_error_response(403, 'Access denied: order belongs to a different club')
            if not _is_delegate(order, user_email):
                return create_error_response(
                    403, 'Access denied: you are not a delegate on this order'
                )

        # --- Status check: reject if locked ---
        current_status = order.get('status', 'draft')
        if current_status == 'locked':
            return create_error_response(403, 'Order is locked and cannot be submitted', {
                'order_id': order_id,
                'status': 'locked',
            })

        # --- Fetch the event and check status ---
        event_id = order.get('event_id')
        event_record = _get_event(event_id)
        if not event_record:
            return create_error_response(404, 'Event not found', {
                'event_id': event_id,
            })

        event_status = event_record.get('status', '')
        if event_status != 'open':
            return create_error_response(403, 'Registration is not active', {
                'event_id': event_id,
                'event_status': event_status,
                'details': 'Orders can only be submitted when the event is in open status.',
            })

        # --- Fetch all products for the event ---
        products = _get_event_products(event_record)

        # --- Fetch all submitted/locked orders for the event via GSI ---
        all_event_orders = _get_all_event_orders(event_id)

        # --- Run validation ---
        errors = validate_submission(order, event_record, products, all_event_orders)

        if errors:
            # Validation failed: return all errors, keep status as draft
            return create_error_response(400, 'Validation failed', {
                'errors': errors,
                'order_id': order_id,
                'error_count': len(errors),
            })

        # --- Validation passed: set status=submitted, record submitted_at ---
        now = datetime.now(timezone.utc).isoformat()

        status_history_entry = {
            'from': current_status,
            'to': 'submitted',
            'at': now,
            'by': user_email,
            'source': 'delegate',
        }

        try:
            update_response = orders_table.update_item(
                Key={'order_id': order_id},
                UpdateExpression=(
                    'SET #status = :submitted, '
                    'submitted_at = :now, '
                    'updated_at = :now, '
                    'status_history = list_append('
                    '  if_not_exists(status_history, :empty_list), :history_entry'
                    ')'
                ),
                ExpressionAttributeNames={
                    '#status': 'status',
                },
                ExpressionAttributeValues={
                    ':submitted': 'submitted',
                    ':now': now,
                    ':history_entry': [status_history_entry],
                    ':empty_list': [],
                },
                ReturnValues='ALL_NEW',
            )
        except ClientError as e:
            logger.error(f"Error updating order {order_id}: {e}")
            return create_error_response(500, 'Failed to update order status')

        updated_order = update_response.get('Attributes', {})
        response_data = _serialize_order(updated_order)

        return create_success_response(response_data)

    except Exception as e:
        logger.error(f"Error in presmeet_submit_order: {str(e)}", exc_info=True)
        return create_error_response(500, 'Internal server error')


def _get_order(order_id):
    """Fetch order by order_id from Orders table."""
    try:
        response = orders_table.get_item(Key={'order_id': order_id})
        return response.get('Item')
    except ClientError as e:
        logger.error(f"Error fetching order {order_id}: {e}")
        raise


def _get_event(event_id):
    """Fetch event record from Events table."""
    try:
        response = events_table.get_item(Key={'event_id': event_id})
        return response.get('Item')
    except ClientError as e:
        logger.error(f"Error fetching event {event_id}: {e}")
        raise


def _get_event_products(event_record):
    """
    Fetch all products for the event from Producten table.

    Returns a dict mapping product_id -> product record (as expected by
    validate_submission).
    """
    product_ids = event_record.get('product_ids', [])
    products = {}

    for product_id in product_ids:
        try:
            response = producten_table.get_item(Key={'product_id': product_id})
            item = response.get('Item')
            if item:
                products[product_id] = item
        except ClientError as e:
            logger.warning(f"Error fetching product {product_id}: {e}")

    return products


def _get_all_event_orders(event_id):
    """
    Fetch all orders for an event using the event-club-index GSI.

    Returns all orders (any status). The validation module filters to
    submitted/locked internally.
    """
    all_orders = []
    try:
        response = orders_table.query(
            IndexName=EVENT_CLUB_INDEX,
            KeyConditionExpression=Key('event_id').eq(event_id),
        )
        all_orders.extend(response.get('Items', []))

        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = orders_table.query(
                IndexName=EVENT_CLUB_INDEX,
                KeyConditionExpression=Key('event_id').eq(event_id),
                ExclusiveStartKey=response['LastEvaluatedKey'],
            )
            all_orders.extend(response.get('Items', []))

    except ClientError as e:
        logger.error(f"Error querying event orders for {event_id}: {e}")
        raise

    return all_orders


def _is_delegate(order, user_email):
    """Check if user is a delegate (primary or secondary) on this order."""
    delegates = order.get('delegates', {})
    primary = delegates.get('primary', '')
    secondary = delegates.get('secondary')
    return (
        user_email.lower() == (primary or '').lower()
        or (secondary and user_email.lower() == secondary.lower())
    )


def _serialize_order(order):
    """Convert DynamoDB Decimal types to JSON-safe types."""
    if isinstance(order, dict):
        return {k: _serialize_order(v) for k, v in order.items()}
    elif isinstance(order, list):
        return [_serialize_order(i) for i in order]
    elif isinstance(order, Decimal):
        if order % 1 == 0:
            return int(order)
        return float(order)
    return order
