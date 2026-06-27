"""
Unified update_order_items handler for H-DCN draft orders.

PUT /orders/{id}/items — Update items on a draft order:
1. Optimistic locking: reject if provided version ≠ stored version (409 Conflict)
2. Accept incomplete item data without validation (validation at submit only)
3. Fetch prices from Producten table for each item
4. Validate variant parent_id matches product_id
5. Increment version on success, recalculate total_amount
6. Accept persons array structure with per-person product lines (event booking)
7. Sync item_fields_data.name when person name is updated
8. Remove all product lines when a person is removed (not present in new array)

Requirements: 5.5, 6.4, 6.5, 7.6, 7.7, 7.8, 7.9, 7.10, 8.3, 10.9, 12.21
"""

import json
import os
import logging
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

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
    from shared.event_access import verify_order_event_access
    from shared.i18n.locale_resolver import resolve_request_locale
    print("Using shared auth layer for update_order_items")
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("update_order_items")
    import sys
    sys.exit(0)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# DynamoDB resources
dynamodb = boto3.resource('dynamodb')
orders_table = dynamodb.Table(os.environ.get('ORDERS_TABLE_NAME', 'Orders'))
producten_table = dynamodb.Table(os.environ.get('PRODUCTEN_TABLE_NAME', 'Producten'))
members_table = dynamodb.Table(os.environ.get('MEMBERS_TABLE_NAME', 'Members'))


def _resolve_member_for_access(user_email: str) -> dict | None:
    """Resolve member record from Members table by email for access checks."""
    from boto3.dynamodb.conditions import Attr as AttrFilter
    try:
        response = members_table.scan(
            FilterExpression=AttrFilter('email').eq(user_email),
            ProjectionExpression='member_id, allowed_events'
        )
        items = response.get('Items', [])
        return items[0] if items else None
    except Exception:
        return None


def lambda_handler(event, context):
    """Main handler for PUT /orders/{id}/items."""
    locale = 'nl'  # Default locale for error responses before resolution
    try:
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # Resolve locale from Accept-Language header
        locale = resolve_request_locale(event)

        # Authentication
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # Access check: admin OR member (hdcnLeden / event_participant / Regio_All)
        is_admin_authorized, _, _ = validate_permissions_with_regions(
            user_roles, ['products_create'], user_email, None
        )
        has_webshop_access = 'hdcnLeden' in user_roles
        has_event_booking_access = any(r in user_roles for r in ('Regio_Pressmeet', 'Regio_All', 'event_participant'))

        if not is_admin_authorized and not has_webshop_access and not has_event_booking_access:
            return create_error_response(403, 'Access denied: Requires webshop or event access',
                                         error_key='forbidden', locale=locale)

        log_successful_access(user_email, user_roles, 'update_order_items')

        # Extract order_id from path
        path_params = event.get('pathParameters') or {}
        order_id = path_params.get('id')
        if not order_id:
            return create_error_response(400, 'Missing order_id in path',
                                         error_key='validation_error', locale=locale)

        # Parse request body
        body = json.loads(event.get('body', '{}'))
        version = body.get('version')
        items = body.get('items')
        persons = body.get('persons')

        # Validate required fields
        if version is None:
            return create_error_response(400, 'version is required for optimistic locking',
                                         error_key='validation_error', locale=locale)

        # Must provide either items or persons (persons takes precedence for event orders)
        if items is None and persons is None:
            return create_error_response(400, 'items or persons is required',
                                         error_key='validation_error', locale=locale)

        # Validate types
        if items is not None and not isinstance(items, list):
            return create_error_response(400, 'items must be an array',
                                         error_key='validation_error', locale=locale)
        if persons is not None and not isinstance(persons, list):
            return create_error_response(400, 'persons must be an array',
                                         error_key='validation_error', locale=locale)

        # Fetch existing order
        order_response = orders_table.get_item(Key={'order_id': order_id})
        if 'Item' not in order_response:
            return create_error_response(404, 'Order not found', {'order_id': order_id},
                                         error_key='order_not_found', locale=locale)

        order = order_response['Item']

        # Event access verification (Req 16.5, 16.7):
        # For event-scoped orders, verify allowed_events + delegate ownership.
        # On failure, return 403 without revealing order existence.
        if not is_admin_authorized:
            event_id = order.get('event_id') or order.get('source_id')
            if event_id and event_id != 'webshop':
                # Resolve member_id from email for event access check
                member_record = _resolve_member_for_access(user_email)
                if not member_record:
                    return create_error_response(403, 'Insufficient event access',
                                                 error_key='forbidden', locale=locale)
                member_id = member_record['member_id']
                if not verify_order_event_access(order, member_id):
                    return create_error_response(403, 'Insufficient event access',
                                                 error_key='forbidden', locale=locale)

        # Verify order belongs to this user (unless admin)
        if not is_admin_authorized:
            order_email = order.get('user_email', '')
            delegates = order.get('delegates', {})
            is_delegate = False
            if delegates:
                # For event orders: check delegate membership
                member_id = body.get('member_id')
                is_delegate = user_email.lower() in [
                    (delegates.get('primary') or '').lower(),
                    (delegates.get('secondary') or '').lower(),
                ]
                # Also check by member_id if available
                if not is_delegate and member_id:
                    is_delegate = member_id in [
                        delegates.get('primary_member_id'),
                        delegates.get('secondary_member_id'),
                    ]
            if order_email.lower() != user_email.lower() and not is_delegate:
                return create_error_response(403, 'Access denied: order belongs to another user',
                                             error_key='forbidden', locale=locale)

        # Verify order is in draft status
        if order.get('status') != 'draft':
            return create_error_response(
                400, 'Only draft orders can be updated',
                {'current_status': order.get('status')},
                error_key='validation_error', locale=locale
            )

        # Optimistic locking: check version matches
        stored_version = int(order.get('version', 1))
        provided_version = int(version)
        if provided_version != stored_version:
            return create_error_response(
                409, 'Version conflict',
                {'current_version': stored_version},
                error_key='validation_error', locale=locale
            )

        # Process items: either from persons array or flat items array
        if persons is not None:
            # Event booking: persons array with per-person product lines
            processed_items, persons_data, process_error = _process_persons(persons)
            if process_error:
                return process_error
        else:
            # Webshop: flat items array
            processed_items, process_error = _process_items(items)
            if process_error:
                return process_error
            persons_data = None

        # Calculate total amount
        total_amount = _calculate_total(processed_items)

        # Update order with optimistic locking via ConditionExpression
        new_version = stored_version + 1
        now = datetime.now(timezone.utc).isoformat()

        # Build update expression based on whether persons data is present
        update_expr = (
            'SET #items = :items, total_amount = :total, '
            'updated_at = :now, #ver = :new_ver'
        )
        expr_names = {
            '#items': 'items',
            '#ver': 'version',
        }
        expr_values = {
            ':items': _convert_to_dynamodb(processed_items),
            ':total': Decimal(str(total_amount)),
            ':now': now,
            ':new_ver': new_version,
        }

        if persons_data is not None:
            update_expr += ', persons = :persons'
            expr_values[':persons'] = _convert_to_dynamodb(persons_data)

        try:
            orders_table.update_item(
                Key={'order_id': order_id},
                UpdateExpression=update_expr,
                ConditionExpression=Attr('version').eq(stored_version),
                ExpressionAttributeNames=expr_names,
                ExpressionAttributeValues=expr_values,
            )
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                return create_error_response(
                    409, 'Version conflict',
                    {'current_version': stored_version},
                    error_key='validation_error', locale=locale
                )
            raise

        logger.info(f"Order {order_id} items updated, version {stored_version} -> {new_version}")

        response_data = {
            'order_id': order_id,
            'version': new_version,
            'total_amount': float(total_amount),
            'item_count': len(processed_items),
        }

        if persons_data is not None:
            response_data['person_count'] = len(persons_data)

        return create_success_response(response_data)

    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body',
                                     error_key='invalid_input', locale=locale)
    except Exception as e:
        logger.error(f"Error updating order items: {str(e)}", exc_info=True)
        return create_error_response(500, 'Internal server error',
                                     error_key='internal_error', locale=locale)


# ---------------------------------------------------------------------------
# Item processing helpers
# ---------------------------------------------------------------------------


def _process_persons(persons: list) -> tuple[list, list, dict | None]:
    """
    Process persons array structure for event booking orders.

    Each person has a name and a list of product lines. This function:
    1. Validates persons structure
    2. Syncs item_fields_data.name on each product line to match person name (Req 6.4)
    3. Flattens to items list for storage (with person_index for association)
    4. Fetches prices and validates variants for product lines

    A person not present in the new array = removed, and all their product lines
    are implicitly removed (they simply aren't in the output). (Req 6.5)

    Returns:
        (processed_items, persons_data, error_response)
        - processed_items: flat list of all items across all persons
        - persons_data: list of person metadata (name, person_index)
        - error_response: error response dict if validation fails, None otherwise
    """
    processed_items = []
    persons_data = []

    for person_index, person in enumerate(persons):
        if not isinstance(person, dict):
            return None, None, create_error_response(
                400, f'Person at index {person_index} must be an object',
                error_key='validation_error', locale='nl'
            )

        person_name = person.get('name', '')
        person_lines = person.get('items', [])

        if not isinstance(person_lines, list):
            return None, None, create_error_response(
                400, f'Person at index {person_index}: items must be an array',
                error_key='validation_error', locale='nl'
            )

        # Store person metadata
        persons_data.append({
            'name': person_name,
            'person_index': person_index,
        })

        # Process each product line for this person
        for line_idx, item in enumerate(person_lines):
            product_id = item.get('product_id')
            variant_id = item.get('variant_id')
            quantity = item.get('quantity', 1)
            item_fields_data = item.get('item_fields_data') or {}

            # Sync item_fields_data.name with person name (Req 6.4)
            if isinstance(item_fields_data, dict):
                item_fields_data['name'] = person_name
            elif isinstance(item_fields_data, list):
                # Legacy list format: ensure name is synced
                item_fields_data = {'name': person_name}

            # Draft orders accept incomplete data: product_id might be absent
            if not product_id:
                processed_item = {
                    'person_index': person_index,
                    'quantity': int(quantity) if quantity else 1,
                    'item_fields_data': item_fields_data,
                }
                if variant_id:
                    processed_item['variant_id'] = variant_id
                processed_items.append(processed_item)
                continue

            # Fetch price from Producten table
            product = _get_product(product_id)
            if product is None:
                return None, None, create_error_response(
                    404, 'Product not found', {'product_id': product_id},
                    error_key='product_not_found', locale='nl'
                )

            price = product.get('price') or product.get('prijs')
            if price is None or price == '' or price == 0:
                return None, None, create_error_response(
                    400, 'Product has no configured price', {'product_id': product_id},
                    error_key='validation_error', locale='nl'
                )

            unit_price = Decimal(str(price))

            # Validate variant if provided
            variant_attributes = item.get('variant_attributes')
            if variant_id:
                variant, variant_error = _validate_variant(variant_id, product_id)
                if variant_error:
                    return None, None, variant_error
                variant_price = variant.get('price')
                if variant_price and variant_price != 0:
                    unit_price = Decimal(str(variant_price))
                if not variant_attributes:
                    variant_attributes = variant.get('variant_attributes', {})

            # Build processed item
            qty = int(quantity) if quantity else 1
            line_total = unit_price * qty

            processed_item = {
                'product_id': product_id,
                'person_index': person_index,
                'quantity': qty,
                'unit_price': unit_price,
                'line_total': line_total,
                'item_fields_data': item_fields_data,
            }

            if variant_id:
                processed_item['variant_id'] = variant_id
            if variant_attributes:
                processed_item['variant_attributes'] = variant_attributes

            processed_items.append(processed_item)

    return processed_items, persons_data, None


def _process_items(items):
    """
    Process order items: fetch prices from Producten table, validate variants.

    Draft orders accept incomplete data — missing fields are allowed.
    However, if a product_id is provided, the price must be valid.
    If a variant_id is provided, its parent_id must match the product_id.

    Returns:
        (processed_items, error_response) — list of processed items or error.
    """
    processed_items = []

    for idx, item in enumerate(items):
        product_id = item.get('product_id')
        variant_id = item.get('variant_id')
        quantity = item.get('quantity', 1)
        item_fields_data = item.get('item_fields_data')

        # Draft orders accept incomplete data: product_id might be absent
        if not product_id:
            # Accept item as-is without price lookup (incomplete draft data)
            processed_item = {
                'quantity': int(quantity) if quantity else 1,
            }
            if variant_id:
                processed_item['variant_id'] = variant_id
            if item_fields_data is not None:
                processed_item['item_fields_data'] = item_fields_data
            processed_items.append(processed_item)
            continue

        # Fetch price from Producten table for the parent product
        product = _get_product(product_id)
        if product is None:
            return None, create_error_response(
                404, 'Product not found', {'product_id': product_id},
                error_key='product_not_found', locale='nl'
            )

        # Get price: reject if null/empty/zero
        price = product.get('price') or product.get('prijs')
        if price is None or price == '' or price == 0:
            return None, create_error_response(
                400, 'Product has no configured price', {'product_id': product_id},
                error_key='validation_error', locale='nl'
            )

        unit_price = Decimal(str(price))

        # Validate variant if provided
        variant_attributes = item.get('variant_attributes')
        if variant_id:
            variant, variant_error = _validate_variant(variant_id, product_id)
            if variant_error:
                return None, variant_error
            # Use variant price override if available
            variant_price = variant.get('price')
            if variant_price and variant_price != 0:
                unit_price = Decimal(str(variant_price))
            # Capture variant_attributes from the variant record
            if not variant_attributes:
                variant_attributes = variant.get('variant_attributes', {})

        # Build processed item
        qty = int(quantity) if quantity else 1
        line_total = unit_price * qty

        processed_item = {
            'product_id': product_id,
            'quantity': qty,
            'unit_price': unit_price,
            'line_total': line_total,
        }

        if variant_id:
            processed_item['variant_id'] = variant_id
        if variant_attributes:
            processed_item['variant_attributes'] = variant_attributes
        if item_fields_data is not None:
            processed_item['item_fields_data'] = item_fields_data

        processed_items.append(processed_item)

    return processed_items, None


def _get_product(product_id):
    """Fetch a parent product record from the Producten table."""
    try:
        response = producten_table.get_item(Key={'product_id': product_id})
        return response.get('Item')
    except Exception as e:
        logger.error(f"Error fetching product {product_id}: {e}")
        return None


def _validate_variant(variant_id, product_id):
    """
    Validate that a variant exists and its parent_id matches the product_id.

    Returns:
        (variant_record, error_response) — variant if valid, error if not.
    """
    try:
        response = producten_table.get_item(Key={'product_id': variant_id})
        variant = response.get('Item')

        if variant is None:
            return None, create_error_response(
                404, 'Variant not found', {'variant_id': variant_id},
                error_key='product_not_found', locale='nl'
            )

        # Verify variant's parent_id matches the provided product_id
        if variant.get('parent_id') != product_id:
            return None, create_error_response(
                400, 'Variant does not belong to product',
                {'variant_id': variant_id, 'product_id': product_id},
                error_key='validation_error', locale='nl'
            )

        return variant, None
    except Exception as e:
        logger.error(f"Error fetching variant {variant_id}: {e}")
        return None, create_error_response(500, 'Error validating variant',
                                           error_key='internal_error', locale='nl')


def _calculate_total(items):
    """Calculate total amount from processed items."""
    total = Decimal('0')
    for item in items:
        line_total = item.get('line_total')
        if line_total is not None:
            total += Decimal(str(line_total))
        else:
            # For incomplete items without a price, skip
            unit_price = item.get('unit_price')
            if unit_price is not None:
                qty = item.get('quantity', 1)
                total += Decimal(str(unit_price)) * qty
    return total


def _convert_to_dynamodb(obj):
    """Recursively convert floats to Decimal for DynamoDB storage."""
    if isinstance(obj, dict):
        return {k: _convert_to_dynamodb(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_to_dynamodb(v) for v in obj]
    elif isinstance(obj, float):
        return Decimal(str(obj))
    return obj
