"""
Unified submit_order handler for H-DCN orders.

POST /orders/{id}/submit — Validates and submits a draft order:
1. Verify order exists and is in "draft" status
2. For each item:
   - Verify product_id exists in Producten table
   - If variant_id present: verify variant exists and variant.parent_id == product_id
   - Validate required item_fields_data against product's order_item_fields
3. On success: set status to "submitted", record submitted_at timestamp
4. On failure: return 400 with structured errors [{item_index, field, message}]

Requirements: 7.1, 7.10, 10.8, 10.9
"""

import json
import os
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
    from shared.item_fields_validator import validate_item_fields_data
    print("Using shared auth layer for submit_order")
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("submit_order")
    import sys
    sys.exit(0)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# DynamoDB resources
dynamodb = boto3.resource('dynamodb')
orders_table = dynamodb.Table(os.environ.get('ORDERS_TABLE_NAME', 'Orders'))
producten_table = dynamodb.Table(os.environ.get('PRODUCTEN_TABLE_NAME', 'Producten'))


def _json_serialize(obj):
    """Custom JSON serializer for Decimal objects from DynamoDB."""
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def lambda_handler(event, context):
    """Main handler for POST /orders/{id}/submit."""
    try:
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # Authentication
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # Access check: any authenticated member or admin
        is_admin, _, _ = validate_permissions_with_regions(
            user_roles, ['products_create'], user_email, None
        )
        has_member_access = 'hdcnLeden' in user_roles
        has_presmeet_access = any(
            r in user_roles for r in ('Regio_Pressmeet', 'Regio_All')
        )

        if not is_admin and not has_member_access and not has_presmeet_access:
            return create_error_response(
                403, 'Access denied: Requires webshop or PresMeet access'
            )

        log_successful_access(user_email, user_roles, 'submit_order')

        # Extract order_id from path parameters
        path_params = event.get('pathParameters') or {}
        order_id = path_params.get('id')

        if not order_id:
            return create_error_response(400, 'Order ID is required')

        # Fetch order
        order = _get_order(order_id)
        if not order:
            return create_error_response(404, 'Order not found', {
                'order_id': order_id,
            })

        # Validate order status — only draft orders can be submitted
        current_status = order.get('status', 'draft')
        if current_status != 'draft':
            return create_error_response(
                400,
                f'Cannot submit order with status "{current_status}". '
                f'Only draft orders can be submitted.'
            )

        # Validate all order items
        items = order.get('items', [])
        if not items:
            return create_error_response(
                400, 'Cannot submit order with no items'
            )

        validation_errors = _validate_order_items(items)

        if validation_errors:
            return {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({
                    'error': 'Validation failed',
                    'errors': validation_errors,
                    'error_count': len(validation_errors),
                }, default=_json_serialize),
            }

        # All validations passed — submit the order
        now = datetime.now(timezone.utc).isoformat()
        history_entry = {
            'from': current_status,
            'to': 'submitted',
            'at': now,
            'by': user_email,
            'source': 'user',
        }

        updated = orders_table.update_item(
            Key={'order_id': order_id},
            UpdateExpression=(
                'SET #status = :submitted, submitted_at = :now, '
                'updated_at = :now, '
                'status_history = list_append('
                'if_not_exists(status_history, :empty_list), :history_entry)'
            ),
            ConditionExpression=Attr('status').eq('draft'),
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':submitted': 'submitted',
                ':now': now,
                ':history_entry': [history_entry],
                ':empty_list': [],
            },
            ReturnValues='ALL_NEW',
        )

        updated_order = updated.get('Attributes', {})

        logger.info(f"Order {order_id} submitted successfully by {user_email}")

        return create_success_response({
            'order_id': order_id,
            'status': 'submitted',
            'submitted_at': now,
        })

    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        return create_error_response(
            409, 'Order status was modified concurrently. Please retry.'
        )
    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        logger.error(f"Error submitting order {path_params.get('id', 'unknown')}: {str(e)}", exc_info=True)
        return create_error_response(500, 'Internal server error')


def _get_order(order_id):
    """Fetch order by order_id. Returns order dict or None."""
    try:
        response = orders_table.get_item(Key={'order_id': order_id})
        return response.get('Item')
    except Exception as e:
        logger.error(f"Error fetching order {order_id}: {e}")
        return None


def _validate_order_items(items):
    """
    Validate all items in an order for submission.

    For each item:
    - Verify product_id exists in Producten table
    - If variant_id present: verify variant exists and parent_id matches product_id
    - Validate required item_fields_data against product's order_item_fields

    Returns list of error dicts [{item_index, field, message}], empty if valid.
    """
    errors = []

    for idx, item in enumerate(items):
        product_id = item.get('product_id')
        variant_id = item.get('variant_id')
        quantity = int(item.get('quantity', 1))

        # Validate product_id is present
        if not product_id:
            errors.append({
                'item_index': idx,
                'field': 'product_id',
                'message': 'Product ID is required',
            })
            continue

        # Fetch product from Producten table
        product = _get_product(product_id)
        if not product:
            errors.append({
                'item_index': idx,
                'field': 'product_id',
                'message': f'Product not found: {product_id}',
            })
            continue

        # Validate variant_id if present
        if variant_id:
            variant = _get_product(variant_id)
            if not variant:
                errors.append({
                    'item_index': idx,
                    'field': 'variant_id',
                    'message': f'Variant not found: {variant_id}',
                })
            elif variant.get('parent_id') != product_id:
                errors.append({
                    'item_index': idx,
                    'field': 'variant_id',
                    'message': (
                        f'Variant {variant_id} does not belong to '
                        f'product {product_id}'
                    ),
                })

        # Validate item_fields_data if product has order_item_fields
        order_item_fields = product.get('order_item_fields')
        if order_item_fields:
            item_fields_data = item.get('item_fields_data')
            field_errors = _validate_item_fields(
                item_fields_data, order_item_fields, quantity, idx
            )
            errors.extend(field_errors)

    return errors


def _get_product(product_id):
    """Fetch a product/variant record by product_id. Returns item or None."""
    try:
        response = producten_table.get_item(Key={'product_id': product_id})
        return response.get('Item')
    except Exception as e:
        logger.error(f"Error fetching product {product_id}: {e}")
        return None


def _validate_item_fields(item_fields_data, order_item_fields, quantity, item_index):
    """
    Validate item_fields_data against the product's order_item_fields definition.

    Uses the shared item_fields_validator for detailed field-level validation.
    Converts validation errors into the submit_order error format:
    [{item_index, field, message}]
    """
    errors = []

    # Use shared validator
    validation_result = validate_item_fields_data(
        item_fields_data, order_item_fields, quantity, line_item_index=item_index
    )

    if validation_result:
        error_type = validation_result.get('error', '')
        details = validation_result.get('details', {})

        if error_type == 'item_fields_count_mismatch':
            errors.append({
                'item_index': item_index,
                'field': 'item_fields_data',
                'message': (
                    f"Expected {details.get('expected', quantity)} entries, "
                    f"got {details.get('actual', 0)}"
                ),
            })
        elif error_type == 'item_fields_validation_error':
            field_id = details.get('field_id', 'unknown')
            constraint = details.get('constraint', 'invalid')
            sub_item_index = details.get('item_index', 0)
            errors.append({
                'item_index': item_index,
                'field': field_id,
                'message': (
                    f"Field '{field_id}' validation failed: {constraint} "
                    f"(entry {sub_item_index})"
                ),
            })
        else:
            # Generic validation error
            errors.append({
                'item_index': item_index,
                'field': 'item_fields_data',
                'message': str(validation_result),
            })

    return errors
