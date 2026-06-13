"""
Unified order submission handler.
Handles both webshop and event-scoped orders.
Replaces: submit_presmeet_booking + webshop submit_order.

POST /orders/{order_id}/submit

Logic:
  1. Extract credentials, resolve member_id from email
  2. Get order_id from path parameters
  3. Load order by order_id from Orders table
  4. Verify ownership: order's member_id must match authenticated member (or admin)
  5. Determine source: read source_id from the order record

  6. If source_id is an event UUID:
     - Load event record → get product_ids[] and constraints[]
     - Load products by IDs from Producten table
     - Apply event constraints validation (validate_submission)
     - Query all orders for this source via event-member-index

  7. If source_id == "webshop":
     - Load products from catalog (only ones in order items)
     - No event constraints to apply
     - Basic validation only (items have valid product_ids, required fields)

  8. Validate order items against product definitions
  9. If validation passes: update order status to "submitted", increment version
  10. If validation fails: return 400 with validation errors
"""

import json
import os
import logging
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key, Attr

try:
    from shared.auth_utils import (
        extract_user_credentials,
        validate_permissions_with_regions,
        create_success_response,
        create_error_response,
        handle_options_request,
        log_successful_access,
    )
    from shared.event_access import has_event_access
    try:
        from shared.event_validation import (
            validate_item_fields,
            validate_purchase_rules,
            validate_submission,
        )
    except ImportError:
        from shared.presmeet_validation import (
            validate_item_fields,
            validate_purchase_rules,
            validate_submission,
        )
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("submit_order")
    import sys
    sys.exit(0)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# DynamoDB resources
dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
orders_table = dynamodb.Table(os.environ.get('ORDERS_TABLE_NAME', 'Orders'))
events_table = dynamodb.Table(os.environ.get('EVENTS_TABLE_NAME', 'Events'))
members_table = dynamodb.Table(os.environ.get('MEMBERS_TABLE_NAME', 'Members'))
producten_table = dynamodb.Table(os.environ.get('PRODUCTEN_TABLE_NAME', 'Producten'))

GSI_NAME = 'event-member-index'


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
    """Fetch order by order_id. Returns order dict or None."""
    try:
        response = orders_table.get_item(Key={'order_id': order_id})
        return response.get('Item')
    except Exception as e:
        logger.error(f"Error fetching order {order_id}: {e}")
        return None


def _get_event(event_id):
    """Load an event record by event_id. Returns None if not found."""
    try:
        response = events_table.get_item(Key={'event_id': event_id})
        return response.get('Item')
    except Exception:
        return None


def _get_products_by_ids(product_ids):
    """
    Load products by a list of product_ids from Producten table.
    Returns dict mapping product_id -> product record.
    """
    products = {}
    for product_id in product_ids:
        try:
            response = producten_table.get_item(Key={'product_id': product_id})
            item = response.get('Item')
            if item:
                products[product_id] = item
        except Exception as e:
            logger.warning(f"Error fetching product {product_id}: {e}")
    return products


def _get_products_for_items(items):
    """
    Load products referenced by order items.
    Returns dict mapping product_id -> product record.
    """
    product_ids = set()
    for item in items:
        pid = item.get('product_id')
        if pid:
            product_ids.add(pid)
    return _get_products_by_ids(list(product_ids))


def _query_all_orders_for_source(source_id):
    """Query GSI with source_id only (PK-only, returns all orders for this source)."""
    items = []
    response = orders_table.query(
        IndexName=GSI_NAME,
        KeyConditionExpression=Key('source_id').eq(source_id)
    )
    items.extend(response.get('Items', []))
    while response.get('LastEvaluatedKey'):
        response = orders_table.query(
            IndexName=GSI_NAME,
            KeyConditionExpression=Key('source_id').eq(source_id),
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        items.extend(response.get('Items', []))
    return items


def _is_admin(user_roles, user_email):
    """Check if user has admin-level access."""
    is_authorized, _, _ = validate_permissions_with_regions(
        user_roles, ['products_create'], user_email, None
    )
    return is_authorized


def _validate_webshop_items(items, products):
    """
    Basic validation for webshop orders:
    - Items have valid product_ids that exist
    - Required fields are present (via validate_item_fields)
    """
    errors = validate_item_fields(items, products)
    rule_errors = validate_purchase_rules(items, products)
    errors.extend(rule_errors)
    return errors


def lambda_handler(event, context):
    """POST /orders/{order_id}/submit"""
    try:
        # Handle OPTIONS (CORS preflight)
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # 1. Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # Validate basic permissions (any authenticated member)
        is_authorized, error_response, _ = validate_permissions_with_regions(
            user_roles, ['events_read'], user_email, None
        )
        if not is_authorized:
            return error_response

        # 2. Get order_id from path parameters
        path_params = event.get('pathParameters') or {}
        order_id = path_params.get('id') or path_params.get('order_id')
        if not order_id:
            return create_error_response(400, 'Order ID is required')

        # 3. Resolve member record from email
        member_record, member_error = _resolve_member_id(user_email)
        if member_error:
            return member_error

        member_id = member_record['member_id']

        # 4. Load order by order_id
        order = _get_order(order_id)
        if not order:
            return create_error_response(404, 'Order not found')

        # 5. Verify ownership: order's member_id must match authenticated member (or admin)
        order_member_id = order.get('member_id')
        admin = _is_admin(user_roles, user_email)

        if order_member_id != member_id and not admin:
            # For club-scoped orders, also check delegate access
            delegates = order.get('delegates', {})
            is_delegate = member_id in [
                delegates.get('primary_member_id'),
                delegates.get('secondary_member_id'),
            ]
            if not is_delegate:
                return create_error_response(403, 'Access denied: not the order owner')

        # 6. Verify order is in draft status
        current_status = order.get('status', 'draft')
        if current_status != 'draft':
            return create_error_response(
                409, f'Cannot submit order in "{current_status}" status'
            )

        # 7. Check items exist
        items = order.get('items', [])
        if not items:
            return create_error_response(400, 'Cannot submit order with no items')

        # 8. Determine source and validate accordingly
        source_id = order.get('source_id')
        if not source_id:
            return create_error_response(400, 'Order missing source_id')

        validation_errors = []

        if source_id == 'webshop':
            # --- Webshop source ---
            if 'hdcnLeden' not in user_roles and not admin:
                return create_error_response(403, 'Member access required for webshop')

            # Load products referenced by order items
            products = _get_products_for_items(items)

            # Basic validation: item fields + purchase rules
            validation_errors = _validate_webshop_items(items, products)

        else:
            # --- Event source (UUID) ---
            event_record = _get_event(source_id)
            if not event_record:
                return create_error_response(404, 'Event not found')

            # Check event access
            if not has_event_access(member_id, source_id) and not admin:
                return create_error_response(403, 'Event access required')

            # Check event status
            event_status = event_record.get('status')
            if event_status != 'open':
                return create_error_response(403, 'Registration is not open')

            # Load products via event's product_ids[]
            event_product_ids = event_record.get('product_ids', [])
            products = _get_products_by_ids(event_product_ids)

            # Query all orders for this source for constraint validation
            all_source_orders = _query_all_orders_for_source(source_id)

            # Full event validation: fields + purchase rules + event constraints
            validation_errors = validate_submission(
                order, event_record, products, all_source_orders
            )

        # 9. If validation fails: return 400 with errors
        if validation_errors:
            return create_error_response(
                400,
                'Validation failed',
                {'errors': convert_decimals(validation_errors)}
            )

        # 10. Validation passed — submit the order with optimistic locking (version check)
        now = datetime.now(timezone.utc).isoformat()
        current_version = order.get('version', 1)

        try:
            updated = orders_table.update_item(
                Key={'order_id': order_id},
                UpdateExpression=(
                    'SET #status = :submitted, submitted_at = :now, '
                    'updated_at = :now, version = :new_version'
                ),
                ConditionExpression=(
                    Attr('status').eq('draft') & Attr('version').eq(current_version)
                ),
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':submitted': 'submitted',
                    ':now': now,
                    ':new_version': current_version + 1,
                },
                ReturnValues='ALL_NEW',
            )
        except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
            return create_error_response(
                409, 'Order was modified concurrently. Please reload and retry.'
            )

        updated_order = updated.get('Attributes', {})

        log_successful_access(user_email, user_roles, 'submit_order')
        logger.info(
            f"Order {order_id} submitted by {user_email} "
            f"(source={source_id}, version={current_version + 1})"
        )

        return create_success_response(convert_decimals(updated_order))

    except Exception as e:
        logger.error(f"Error in submit_order handler: {str(e)}", exc_info=True)
        return create_error_response(500, 'Internal server error')
