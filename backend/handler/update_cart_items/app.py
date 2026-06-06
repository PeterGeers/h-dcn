import json
import os
import boto3
from decimal import Decimal
from datetime import datetime

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
    print("Using shared auth layer")
except ImportError as e:
    # Built-in smart fallback - no local auth_fallback.py needed
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("update_cart_items")
    # Exit early - the fallback handler will handle all requests
    import sys
    sys.exit(0)

dynamodb = boto3.resource('dynamodb')
carts_table = dynamodb.Table('Carts')
producten_table_name = os.environ.get('PRODUCTEN_TABLE_NAME', 'Producten')
producten_table = dynamodb.Table(producten_table_name)


def log_cart_audit(event_type, cart_id, user_email, user_roles, additional_data=None):
    """Log cart operations for comprehensive audit trail."""
    try:
        audit_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': f'CART_{event_type}',
            'cart_id': cart_id,
            'user_email': user_email,
            'user_roles': user_roles,
            'severity': 'INFO',
            'requires_review': False
        }
        if additional_data:
            audit_entry.update(additional_data)
        if event_type in ['UPDATE', 'DELETE', 'UPDATE_DENIED']:
            audit_entry['requires_review'] = True
            audit_entry['severity'] = additional_data.get('severity', 'WARN') if additional_data else 'WARN'
        print(f"CART_AUDIT: {json.dumps(audit_entry, default=str)}")
    except Exception as e:
        print(f"Error logging cart audit: {str(e)}")


def _get_variant(variant_id):
    """Fetch a variant record from the Producten table."""
    response = producten_table.get_item(Key={'product_id': variant_id})
    return response.get('Item')


def _get_product(product_id):
    """Fetch a parent product record from the Producten table."""
    response = producten_table.get_item(Key={'product_id': product_id})
    item = response.get('Item')
    if item and item.get('is_parent', False):
        return item
    return None


def _validate_variant_for_product(variant_id, product_id):
    """
    Validate that a variant exists and belongs to the referenced product.

    Returns:
        (variant_record, error_response) - variant if valid, error dict otherwise.
    """
    variant = _get_variant(variant_id)
    if variant is None or variant.get('is_parent', True):
        return None, {
            'error': 'variant_not_found',
            'details': {'product_id': product_id, 'variant_id': variant_id}
        }

    if variant.get('parent_id') != product_id:
        return None, {
            'error': 'variant_not_found',
            'details': {'product_id': product_id, 'variant_id': variant_id}
        }

    return variant, None


def _check_stock_availability(variant, quantity):
    """
    Check stock availability for a variant.

    Returns:
        error_response dict if insufficient stock, None otherwise.
    """
    allow_oversell = variant.get('allow_oversell', False)
    if allow_oversell:
        return None

    stock = int(variant.get('stock', 0))
    if stock < quantity:
        return {
            'error': 'insufficient_stock',
            'details': {
                'variant_id': variant['product_id'],
                'available': stock,
                'requested': quantity
            }
        }
    return None


def _apply_quantity_decrease(existing_item_fields_data, new_quantity):
    """
    When quantity decreases, remove highest-numbered item_fields_data entries.
    Retains entries for items 1..new_quantity, discards new_quantity+1..old_quantity.

    Args:
        existing_item_fields_data: Current list of item field data entries.
        new_quantity: The new (lower) quantity.

    Returns:
        Trimmed list of item_fields_data.
    """
    if not existing_item_fields_data:
        return []
    # Keep only the first new_quantity entries
    return existing_item_fields_data[:new_quantity]


def _apply_schema_evolution(item_fields_data, product):
    """
    Discard orphaned field values whose field_id no longer exists in the
    product's current order_item_fields definition.

    Args:
        item_fields_data: List of field value dicts for this cart item.
        product: The parent product record.

    Returns:
        Cleaned list of item_fields_data with orphaned keys removed.
    """
    order_item_fields = product.get('order_item_fields')
    if not order_item_fields or not item_fields_data:
        return item_fields_data

    # Build set of currently valid field_ids
    valid_field_ids = {field_def['id'] for field_def in order_item_fields}

    cleaned = []
    for entry in item_fields_data:
        if isinstance(entry, dict):
            # Support both {"field_values": {...}} wrapper and direct dict
            if 'field_values' in entry:
                filtered_values = {
                    k: v for k, v in entry['field_values'].items()
                    if k in valid_field_ids
                }
                cleaned.append({'field_values': filtered_values})
            else:
                filtered = {k: v for k, v in entry.items() if k in valid_field_ids}
                cleaned.append(filtered)
        else:
            cleaned.append(entry)

    return cleaned


def _validate_and_process_items(items):
    """
    Validate all cart items: check variants exist, belong to products,
    have sufficient stock, and process item_fields_data.

    Args:
        items: List of cart item dicts from the request body.

    Returns:
        (processed_items, error_response) - processed items or error dict.
    """
    processed_items = []

    for idx, item in enumerate(items):
        product_id = item.get('product_id')
        variant_id = item.get('variant_id')
        quantity = item.get('quantity', 1)
        item_fields_data = item.get('item_fields_data')

        if not product_id:
            return None, create_error_response(
                400, f'Missing product_id in item at index {idx}')
        if not variant_id:
            return None, create_error_response(
                400, f'Missing variant_id in item at index {idx}')
        if not isinstance(quantity, int) or quantity < 1:
            return None, create_error_response(
                400, f'Invalid quantity in item at index {idx}: must be integer >= 1')

        # Validate variant exists and belongs to product
        variant, variant_error = _validate_variant_for_product(variant_id, product_id)
        if variant_error:
            return None, create_error_response(
                404 if variant_error['error'] == 'variant_not_found' else 400,
                variant_error['error'],
                variant_error['details']
            )

        # Check stock availability
        stock_error = _check_stock_availability(variant, quantity)
        if stock_error:
            return None, create_error_response(400, stock_error['error'], stock_error['details'])

        # Build processed cart item
        processed_item = {
            'product_id': product_id,
            'variant_id': variant_id,
            'variant_attributes': variant.get('variant_attributes', {}),
            'quantity': quantity,
            'unit_price': variant.get('price') or _get_parent_price(product_id),
        }

        # Support item_fields_data (partial data allowed during cart phase)
        if item_fields_data is not None:
            # Apply quantity decrease logic: trim to match quantity
            if len(item_fields_data) > quantity:
                item_fields_data = _apply_quantity_decrease(item_fields_data, quantity)

            # Apply schema evolution: discard orphaned field values
            product = _get_product(product_id)
            if product:
                item_fields_data = _apply_schema_evolution(item_fields_data, product)

            processed_item['item_fields_data'] = item_fields_data

        processed_items.append(processed_item)

    return processed_items, None


def _get_parent_price(product_id):
    """Fetch the price from the parent product record."""
    product = _get_product(product_id)
    if product:
        return product.get('price')
    return None


def _handle_quantity_decrease_for_existing_cart(existing_items, new_items):
    """
    For items that already exist in the cart with item_fields_data,
    apply quantity decrease logic when quantity is reduced.

    Args:
        existing_items: Current cart items from DynamoDB.
        new_items: New items from the request body.

    Returns:
        Updated new_items with item_fields_data trimmed where needed.
    """
    # Build lookup of existing items by (product_id, variant_id)
    existing_by_key = {}
    for item in (existing_items or []):
        key = (item.get('product_id'), item.get('variant_id'))
        existing_by_key[key] = item

    updated_items = []
    for new_item in new_items:
        key = (new_item.get('product_id'), new_item.get('variant_id'))
        existing = existing_by_key.get(key)

        if existing and 'item_fields_data' not in new_item:
            # Carry over existing item_fields_data if not provided in request
            existing_fields = existing.get('item_fields_data', [])
            new_quantity = new_item.get('quantity', 1)
            old_quantity = existing.get('quantity', 1)

            if existing_fields and new_quantity < old_quantity:
                # Quantity decreased: trim highest-numbered entries
                new_item['item_fields_data'] = _apply_quantity_decrease(
                    existing_fields, new_quantity)
            elif existing_fields:
                new_item['item_fields_data'] = existing_fields

        updated_items.append(new_item)

    return updated_items


def _calculate_total(items):
    """Calculate the cart total from processed items."""
    total = Decimal('0')
    for item in items:
        price = item.get('unit_price')
        if price is not None:
            total += Decimal(str(price)) * item.get('quantity', 1)
    return total


def lambda_handler(event, context):
    try:
        # Handle OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # Check for webshop access permission
        required_permissions = ['webshop_access']
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, required_permissions, user_email, None
        )
        if not is_authorized:
            return error_response

        # Log successful access
        log_successful_access(user_email, user_roles, 'update_cart_items')

        cart_id = event['pathParameters']['cart_id']
        body = json.loads(event['body'])

        # Fetch cart and validate ownership
        cart_response = carts_table.get_item(Key={'cart_id': cart_id})
        if 'Item' not in cart_response:
            return create_error_response(404, 'Cart not found')

        cart = cart_response['Item']

        # Validate cart ownership
        cart_user_email = cart.get('user_email')
        if cart_user_email and cart_user_email.lower() != user_email.lower():
            log_cart_audit('UPDATE_DENIED', cart_id, user_email, user_roles, {
                'cart_owner': cart_user_email,
                'security_violation': True,
                'severity': 'CRITICAL'
            })
            return create_error_response(403, 'Access denied: You can only update your own cart')

        # Extract items from body
        items = body.get('items')
        if items is None:
            return create_error_response(400, 'Missing required field: items')
        if not isinstance(items, list):
            return create_error_response(400, 'items must be an array')

        # Validate and process items (variant check, stock check, schema evolution)
        processed_items, error = _validate_and_process_items(items)
        if error:
            return error

        # Apply quantity decrease logic for existing cart items
        existing_items = cart.get('items', [])
        processed_items = _handle_quantity_decrease_for_existing_cart(
            existing_items, processed_items)

        # Apply schema evolution on carried-over item_fields_data
        for item in processed_items:
            if 'item_fields_data' in item:
                product = _get_product(item['product_id'])
                if product:
                    item['item_fields_data'] = _apply_schema_evolution(
                        item['item_fields_data'], product)

        # Calculate total
        total_amount = _calculate_total(processed_items)

        # Update cart in DynamoDB
        now = datetime.now().isoformat()
        carts_table.update_item(
            Key={'cart_id': cart_id},
            UpdateExpression='SET #items = :items, total_amount = :total, updated_at = :updated_at',
            ExpressionAttributeNames={'#items': 'items'},
            ExpressionAttributeValues={
                ':items': processed_items,
                ':total': total_amount,
                ':updated_at': now,
            }
        )

        # Log cart update
        log_cart_audit('UPDATE', cart_id, user_email, user_roles, {
            'item_count': len(processed_items),
            'new_total': str(total_amount),
        })

        return create_success_response({
            'message': 'Cart updated successfully',
            'items': processed_items,
            'total_amount': str(total_amount),
        })

    except KeyError as e:
        return create_error_response(400, f'Missing required parameter: {str(e)}')
    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        print(f"Error updating cart items: {str(e)}")
        return create_error_response(500, 'Internal server error')
