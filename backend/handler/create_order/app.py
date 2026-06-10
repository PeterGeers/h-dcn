"""
Unified create_order handler for H-DCN.

POST /orders — Create a draft order for either webshop or event purchases.

Flow:
- If event_id is provided (non-null): event order
  - Check for existing non-cancelled order for same club_id + event_id
  - If found, return the existing order (no duplicate creation)
  - Otherwise create a new draft order
- If event_id is null/absent: webshop order
  - Always create a new draft order

Draft orders have: status="draft", payment_status="unpaid", version=1.

Product prices are fetched from the Producten table at creation time.
Items with null/empty/zero price are rejected.

Requirements: 7.1, 7.4, 7.5, 7.6, 7.7, 7.8, 7.13, 7.16, 10.8
"""

import json
import os
import uuid
import logging
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr

# Import from shared auth layer
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
    from shared.club_identity import get_club_id
    print("Using shared auth layer for create_order")
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("create_order")
    import sys
    sys.exit(0)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# DynamoDB resources
dynamodb = boto3.resource('dynamodb')
orders_table = dynamodb.Table(os.environ.get('ORDERS_TABLE_NAME', 'Orders'))
producten_table = dynamodb.Table(os.environ.get('PRODUCTEN_TABLE_NAME', 'Producten'))
members_table = dynamodb.Table(os.environ.get('MEMBERS_TABLE_NAME', 'Members'))


def lambda_handler(event, context):
    """Main handler for POST /orders."""
    try:
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # Authentication
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # Access check: any authenticated member (hdcnLeden) or admin
        is_admin, _, _ = validate_permissions_with_regions(
            user_roles, ['products_create'], user_email, None
        )
        has_member_access = 'hdcnLeden' in user_roles
        has_presmeet_access = any(r in user_roles for r in ('Regio_Pressmeet', 'Regio_All'))

        if not is_admin and not has_member_access and not has_presmeet_access:
            return create_error_response(403, 'Access denied: Requires membership access')

        log_successful_access(user_email, user_roles, 'create_order')

        # Parse request body
        body = json.loads(event.get('body', '{}'))
        event_id = body.get('event_id')  # null for webshop, set for event
        items = body.get('items', [])
        club_id = body.get('club_id')

        # Resolve member_id
        member_id, member_error = _get_member_id(user_email)
        if member_error:
            return member_error

        # Resolve club_id from user context if not provided in body
        if not club_id:
            club_id = get_club_id(user_email)

        # --- Event order flow: one per club per event ---
        if event_id:
            existing_order = _find_existing_event_order(club_id, event_id)
            if existing_order:
                logger.info(
                    f"Returning existing order {existing_order['order_id']} "
                    f"for club_id={club_id}, event_id={event_id}"
                )
                return create_success_response(
                    _serialize_order(existing_order), status_code=200
                )

        # --- Validate items and fetch prices ---
        if items:
            validated_items, price_error = _validate_and_price_items(items)
            if price_error:
                return price_error
        else:
            validated_items = []

        # --- Create new draft order ---
        order = _create_draft_order(
            event_id=event_id,
            member_id=member_id,
            user_email=user_email,
            club_id=club_id,
            items=validated_items,
        )

        _store_order(order)

        logger.info(
            f"Created draft order {order['order_id']} "
            f"event_id={event_id}, club_id={club_id}"
        )

        return create_success_response(_serialize_order(order), status_code=201)

    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        logger.error(f"Error creating order: {str(e)}", exc_info=True)
        return create_error_response(500, 'Internal server error')


# ---------------------------------------------------------------------------
# Event order deduplication
# ---------------------------------------------------------------------------


def _find_existing_event_order(club_id, event_id):
    """
    Find an existing non-cancelled order for the given club_id + event_id.
    Returns the order dict if found, None otherwise.
    """
    if not club_id or not event_id:
        return None

    try:
        filter_expr = (
            Attr('club_id').eq(club_id)
            & Attr('event_id').eq(event_id)
            & Attr('status').ne('cancelled')
        )
        response = orders_table.scan(FilterExpression=filter_expr)
        orders = response.get('Items', [])

        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = orders_table.scan(
                FilterExpression=filter_expr,
                ExclusiveStartKey=response['LastEvaluatedKey'],
            )
            orders.extend(response.get('Items', []))

        if orders:
            # Return the most recently created order if multiple exist
            orders.sort(key=lambda o: o.get('created_at', ''), reverse=True)
            return orders[0]

        return None
    except Exception as e:
        logger.error(
            f"Error finding existing order for club={club_id}, event={event_id}: {e}"
        )
        return None


# ---------------------------------------------------------------------------
# Item validation and pricing
# ---------------------------------------------------------------------------


def _validate_and_price_items(items):
    """
    Fetch product prices from Producten table for each item.
    Reject if any product has a null/empty/zero price.

    Returns (validated_items, error_response).
    """
    validated_items = []
    product_cache = {}

    for idx, item in enumerate(items):
        product_id = item.get('product_id')
        variant_id = item.get('variant_id')
        quantity = int(item.get('quantity', 1))

        if not product_id:
            return None, create_error_response(
                400, f'Item at index {idx} is missing product_id'
            )

        # Fetch product if not cached
        if product_id not in product_cache:
            product = _fetch_product(product_id)
            if product is None:
                return None, create_error_response(
                    404, f'Product not found: {product_id}',
                    {'product_id': product_id}
                )
            product_cache[product_id] = product

        product = product_cache[product_id]

        # Determine price: variant price override or parent product price
        unit_price = None
        if variant_id:
            variant = _fetch_product(variant_id)
            if variant and variant.get('price'):
                unit_price = variant.get('price')

        # Fallback to parent product price
        if unit_price is None:
            unit_price = product.get('price')

        # Reject if price is null, empty, or zero
        if not unit_price or Decimal(str(unit_price)) == 0:
            return None, create_error_response(
                400, 'Product has no configured price',
                {'product_id': product_id, 'item_index': idx}
            )

        unit_price_decimal = Decimal(str(unit_price))
        line_total = unit_price_decimal * quantity

        validated_item = {
            'product_id': product_id,
            'quantity': quantity,
            'unit_price': unit_price_decimal,
            'line_total': line_total,
        }

        if variant_id:
            validated_item['variant_id'] = variant_id

        # Pass through optional fields
        if item.get('variant_attributes'):
            validated_item['variant_attributes'] = item['variant_attributes']
        if item.get('product_type'):
            validated_item['product_type'] = item['product_type']
        if item.get('name'):
            validated_item['name'] = item['name']
        if item.get('item_fields_data'):
            validated_item['item_fields_data'] = item['item_fields_data']

        validated_items.append(validated_item)

    return validated_items, None


def _fetch_product(product_id):
    """Fetch a single product/variant record from the Producten table."""
    try:
        response = producten_table.get_item(Key={'product_id': product_id})
        return response.get('Item')
    except Exception as e:
        logger.error(f"Error fetching product {product_id}: {e}")
        return None


# ---------------------------------------------------------------------------
# Order creation
# ---------------------------------------------------------------------------


def _create_draft_order(event_id, member_id, user_email, club_id, items):
    """Build a new draft order record."""
    now = datetime.now(timezone.utc).isoformat()
    total_amount = sum(item.get('line_total', Decimal('0')) for item in items)

    order = {
        'order_id': str(uuid.uuid4()),
        'status': 'draft',
        'payment_status': 'unpaid',
        'member_id': member_id,
        'user_email': user_email,
        'club_id': club_id,
        'items': items,
        'total_amount': total_amount,
        'total_paid': Decimal('0'),
        'version': 1,
        'created_at': now,
        'updated_at': now,
    }

    # Only include event_id if it has a value (DynamoDB GSI key cannot be NULL)
    if event_id:
        order['event_id'] = event_id

    return order


# ---------------------------------------------------------------------------
# Member lookup
# ---------------------------------------------------------------------------


def _get_member_id(user_email):
    """Get member_id from email. Returns (member_id, error)."""
    try:
        response = members_table.scan(
            FilterExpression=Attr('email').eq(user_email.lower()),
            ProjectionExpression='member_id',
        )
        items = response.get('Items', [])
        if not items:
            return None, create_error_response(404, 'Member record not found')
        member_id = items[0].get('member_id')
        if not member_id:
            return None, create_error_response(500, 'Member record missing member_id')
        return member_id, None
    except Exception as e:
        logger.error(f"Error looking up member for {user_email}: {e}")
        return None, create_error_response(500, 'Error looking up member information')


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def _store_order(order):
    """Persist order to DynamoDB, converting floats to Decimal."""
    item = _convert_to_dynamodb(order)
    orders_table.put_item(Item=item)


def _convert_to_dynamodb(obj):
    """Recursively convert floats to Decimal for DynamoDB."""
    if isinstance(obj, dict):
        return {k: _convert_to_dynamodb(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_to_dynamodb(v) for v in obj]
    elif isinstance(obj, float):
        return Decimal(str(obj))
    return obj


def _serialize_order(order):
    """Convert an order dict for JSON response (Decimal → int/float)."""
    return json.loads(json.dumps(order, default=_json_serialize))


def _json_serialize(obj):
    """Custom JSON serializer for Decimal and other non-standard types."""
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
