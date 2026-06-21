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
    from shared.event_access import has_event_access, verify_order_event_access
    from shared.event_validation import (
        validate_item_fields,
        validate_purchase_rules,
        validate_submission,
    )
    from shared.number_generator import generate_order_number
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
counters_table = dynamodb.Table(os.environ.get('COUNTERS_TABLE_NAME', 'Counters'))

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


def _validate_event_persons(order, products, all_source_orders):
    """
    Validate an event order with persons structure.

    Validates (Requirements 9.1-9.9):
    - Every person has a non-empty name (≥1 non-whitespace char)
    - Every item has item_fields_data.name populated (non-empty)
    - All required order_item_fields are filled per product line
    - Per-order quantity limits (max_per_club) not exceeded
    - Per-event capacity (max_per_event) via current Sold_Count
    - All variant_id references exist in product's variant list
    - Errors are grouped per person

    Returns list of error dicts with person_index, product_id, field, message.
    """
    persons = order.get('persons', [])
    items = order.get('items', [])
    club_id = order.get('club_id')
    errors = []

    # 1. Validate person names (Req 9.1)
    for idx, person in enumerate(persons):
        name = person.get('name', '')
        if not isinstance(name, str) or not name.strip():
            errors.append({
                'person_index': idx,
                'product_id': None,
                'field': 'name',
                'message': f'Persoon {idx + 1}: naam is verplicht (minimaal 1 niet-witruimte teken)',
            })

    # 2. Validate item_fields_data.name on every line (Req 9.2)
    for item_idx, item in enumerate(items):
        person_index = item.get('person_index')
        product_id = item.get('product_id')
        fields_data = item.get('item_fields_data') or {}

        item_name = fields_data.get('name', '') if isinstance(fields_data, dict) else ''
        if not isinstance(item_name, str) or not item_name.strip():
            errors.append({
                'person_index': person_index,
                'product_id': product_id,
                'field': 'item_fields_data.name',
                'message': (
                    f'Productlijn voor persoon {(person_index or 0) + 1}: '
                    f'item_fields_data.name is verplicht'
                ),
            })

    # 3. Validate required order_item_fields (Req 9.3)
    for item_idx, item in enumerate(items):
        person_index = item.get('person_index')
        product_id = item.get('product_id')
        if not product_id:
            continue

        product = products.get(product_id)
        if not product:
            continue

        field_definitions = product.get('order_item_fields', [])
        if not field_definitions:
            continue

        fields_data = item.get('item_fields_data') or {}
        if not isinstance(fields_data, dict):
            fields_data = {}

        for field_def in field_definitions:
            field_id = field_def.get('id')
            if not field_id:
                continue
            required = field_def.get('required', False)
            if not required:
                continue

            value = fields_data.get(field_id)
            label = field_def.get('label', field_id)

            if value is None or (isinstance(value, str) and not value.strip()):
                errors.append({
                    'person_index': person_index,
                    'product_id': product_id,
                    'field': field_id,
                    'message': (
                        f"Persoon {(person_index or 0) + 1}, product '{product.get('name', product_id)}': "
                        f"veld '{label}' is verplicht"
                    ),
                })

    # 4. Validate per-order quantity limits: max_per_club (Req 9.4)
    product_counts: dict[str, int] = {}
    for item in items:
        product_id = item.get('product_id')
        if product_id:
            quantity = item.get('quantity', 1)
            if isinstance(quantity, Decimal):
                quantity = int(quantity)
            product_counts[product_id] = product_counts.get(product_id, 0) + quantity

    for product_id, count in product_counts.items():
        product = products.get(product_id)
        if not product:
            continue
        purchase_rules = product.get('purchase_rules') or {}
        max_per_club = purchase_rules.get('max_per_club')
        if max_per_club is not None:
            max_val = int(max_per_club) if isinstance(max_per_club, Decimal) else int(max_per_club)
            if count > max_val:
                errors.append({
                    'person_index': None,
                    'product_id': product_id,
                    'field': 'max_per_club',
                    'message': (
                        f"Product '{product.get('name', product_id)}': "
                        f"maximaal {max_val} per bestelling, maar {count} geselecteerd"
                    ),
                })

    # 5. Validate per-event capacity: max_per_event via Sold_Count (Req 9.5, 9.9)
    # Calculate sold counts from other submitted/locked orders (exclude current order)
    sold_counts = _calculate_sold_counts(all_source_orders, club_id)

    for product_id, count in product_counts.items():
        product = products.get(product_id)
        if not product:
            continue
        purchase_rules = product.get('purchase_rules') or {}
        max_per_event = purchase_rules.get('max_per_event')
        if max_per_event is not None:
            max_val = int(max_per_event) if isinstance(max_per_event, Decimal) else int(max_per_event)
            sold = sold_counts.get(product_id, 0)
            remaining = max_val - sold
            if count > remaining:
                errors.append({
                    'person_index': None,
                    'product_id': product_id,
                    'field': 'max_per_event',
                    'message': (
                        f"Product '{product.get('name', product_id)}': "
                        f"evenementcapaciteit overschreden. "
                        f"Resterende capaciteit: {remaining}, gevraagd: {count}"
                    ),
                    'remaining': remaining,
                })

    # 6. Validate variant_id references exist in product's variant list (Req 9.6)
    for item_idx, item in enumerate(items):
        variant_id = item.get('variant_id')
        if not variant_id:
            continue

        person_index = item.get('person_index')
        product_id = item.get('product_id')
        if not product_id:
            continue

        # Fetch variant record from Producten table
        variant = _get_variant(variant_id)
        if variant is None:
            errors.append({
                'person_index': person_index,
                'product_id': product_id,
                'field': 'variant_id',
                'message': (
                    f"Persoon {(person_index or 0) + 1}, product '{products.get(product_id, {}).get('name', product_id)}': "
                    f"variant '{variant_id}' bestaat niet"
                ),
            })
        elif variant.get('parent_id') != product_id:
            errors.append({
                'person_index': person_index,
                'product_id': product_id,
                'field': 'variant_id',
                'message': (
                    f"Persoon {(person_index or 0) + 1}, product '{products.get(product_id, {}).get('name', product_id)}': "
                    f"variant '{variant_id}' behoort niet tot dit product"
                ),
            })

    return errors


def _calculate_sold_counts(all_source_orders, current_club_id):
    """
    Calculate sold counts from submitted/locked orders, excluding the current club's order.
    This mirrors the logic in get_product_sold_counts but excludes the current order.

    Returns dict mapping product_id -> sold count.
    """
    sold_counts: dict[str, int] = {}

    for order in all_source_orders:
        # Only count submitted/locked orders
        if order.get('status') not in ('submitted', 'locked'):
            continue
        # Exclude current club's order (will be replaced by this submission)
        if current_club_id and order.get('club_id') == current_club_id:
            continue

        for item in order.get('items', []):
            product_id = item.get('product_id')
            if not product_id:
                continue
            quantity = item.get('quantity', 1)
            if isinstance(quantity, Decimal):
                quantity = int(quantity)
            sold_counts[product_id] = sold_counts.get(product_id, 0) + quantity

    return sold_counts


def _get_variant(variant_id):
    """Fetch a variant record from the Producten table."""
    try:
        response = producten_table.get_item(Key={'product_id': variant_id})
        return response.get('Item')
    except Exception as e:
        logger.warning(f"Error fetching variant {variant_id}: {e}")
        return None


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

        # No broad permission check — access controlled by order ownership
        # and event access (has_event_access) checked below.

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

        # 4a. Event access verification (Req 16.5, 16.7):
        # For event-scoped orders, verify allowed_events + delegate ownership.
        # On failure, return 403 without revealing order existence.
        admin = _is_admin(user_roles, user_email)
        if not admin:
            event_id = order.get('event_id') or order.get('source_id')
            if event_id and event_id != 'webshop':
                if not verify_order_event_access(order, member_id):
                    return create_error_response(403, 'Insufficient event access')

        # 5. Verify ownership: order's member_id must match authenticated member (or admin)
        order_member_id = order.get('member_id')

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

            # Check if order uses persons structure (closed community booking)
            if order.get('persons'):
                # Person-based event validation (Req 9.1-9.9)
                validation_errors = _validate_event_persons(
                    order, products, all_source_orders
                )
            else:
                # Legacy event validation: fields + purchase rules + event constraints
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

        # Generate order number
        order_number = generate_order_number(counters_table)

        try:
            updated = orders_table.update_item(
                Key={'order_id': order_id},
                UpdateExpression=(
                    'SET #status = :submitted, submitted_at = :now, '
                    'updated_at = :now, version = :new_version, '
                    'order_number = :order_number'
                ),
                ConditionExpression=(
                    Attr('status').eq('draft') & Attr('version').eq(current_version)
                ),
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':submitted': 'submitted',
                    ':now': now,
                    ':new_version': current_version + 1,
                    ':order_number': order_number,
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
