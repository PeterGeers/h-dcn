"""
Unified update_order_items handler for H-DCN draft orders.

PUT /orders/{id}/items — Update items on a draft order:
1. Optimistic locking: reject if provided version ≠ stored version (409 Conflict)
2. Accept incomplete item data without validation (validation at submit only)
3. Fetch prices from Producten table for each item
4. Validate variant parent_id matches product_id
5. Increment version on success, recalculate total_amount

Requirements: 7.6, 7.7, 7.8, 7.9, 7.10, 10.9, 12.21
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


def lambda_handler(event, context):
    """Main handler for PUT /orders/{id}/items."""
    try:
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # Authentication
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # Access check: admin OR webshop member (hdcnLeden / Regio_Pressmeet / Regio_All)
        is_admin_authorized, _, _ = validate_permissions_with_regions(
            user_roles, ['products_create'], user_email, None
        )
        has_webshop_access = 'hdcnLeden' in user_roles
        has_presmeet_access = any(r in user_roles for r in ('Regio_Pressmeet', 'Regio_All'))

        if not is_admin_authorized and not has_webshop_access and not has_presmeet_access:
            return create_error_response(403, 'Access denied: Requires webshop or event access')

        log_successful_access(user_email, user_roles, 'update_order_items')

        # Extract order_id from path
        path_params = event.get('pathParameters') or {}
        order_id = path_params.get('id')
        if not order_id:
            return create_error_response(400, 'Missing order_id in path')

        # Parse request body
        body = json.loads(event.get('body', '{}'))
        version = body.get('version')
        items = body.get('items')

        # Validate required fields
        if version is None:
            return create_error_response(400, 'version is required for optimistic locking')
        if items is None:
            return create_error_response(400, 'items is required')
        if not isinstance(items, list):
            return create_error_response(400, 'items must be an array')

        # Fetch existing order
        order_response = orders_table.get_item(Key={'order_id': order_id})
        if 'Item' not in order_response:
            return create_error_response(404, 'Order not found', {'order_id': order_id})

        order = order_response['Item']

        # Verify order belongs to this user (unless admin)
        if not is_admin_authorized:
            order_email = order.get('user_email', '')
            if order_email.lower() != user_email.lower():
                return create_error_response(403, 'Access denied: order belongs to another user')

        # Verify order is in draft status
        if order.get('status') != 'draft':
            return create_error_response(
                400, 'Only draft orders can be updated',
                {'current_status': order.get('status')}
            )

        # Optimistic locking: check version matches
        stored_version = int(order.get('version', 1))
        provided_version = int(version)
        if provided_version != stored_version:
            return create_error_response(
                409, 'Version conflict',
                {'current_version': stored_version}
            )

        # Process items: fetch prices and validate variants
        processed_items, process_error = _process_items(items)
        if process_error:
            return process_error

        # Calculate total amount
        total_amount = _calculate_total(processed_items)

        # Update order with optimistic locking via ConditionExpression
        new_version = stored_version + 1
        now = datetime.now(timezone.utc).isoformat()

        try:
            orders_table.update_item(
                Key={'order_id': order_id},
                UpdateExpression=(
                    'SET #items = :items, total_amount = :total, '
                    'updated_at = :now, #ver = :new_ver'
                ),
                ConditionExpression=Attr('version').eq(stored_version),
                ExpressionAttributeNames={
                    '#items': 'items',
                    '#ver': 'version',
                },
                ExpressionAttributeValues={
                    ':items': _convert_to_dynamodb(processed_items),
                    ':total': Decimal(str(total_amount)),
                    ':now': now,
                    ':new_ver': new_version,
                },
            )
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                return create_error_response(
                    409, 'Version conflict',
                    {'current_version': stored_version}
                )
            raise

        logger.info(f"Order {order_id} items updated, version {stored_version} -> {new_version}")

        return create_success_response({
            'order_id': order_id,
            'version': new_version,
            'total_amount': float(total_amount),
            'item_count': len(processed_items),
        })

    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        logger.error(f"Error updating order items: {str(e)}", exc_info=True)
        return create_error_response(500, 'Internal server error')


# ---------------------------------------------------------------------------
# Item processing helpers
# ---------------------------------------------------------------------------


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
                404, 'Product not found', {'product_id': product_id}
            )

        # Get price: reject if null/empty/zero
        price = product.get('price') or product.get('prijs')
        if price is None or price == '' or price == 0:
            return None, create_error_response(
                400, 'Product has no configured price', {'product_id': product_id}
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
                404, 'Variant not found', {'variant_id': variant_id}
            )

        # Verify variant's parent_id matches the provided product_id
        if variant.get('parent_id') != product_id:
            return None, create_error_response(
                400, 'Variant does not belong to product',
                {'variant_id': variant_id, 'product_id': product_id}
            )

        return variant, None
    except Exception as e:
        logger.error(f"Error fetching variant {variant_id}: {e}")
        return None, create_error_response(500, 'Error validating variant')


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
