"""
Unified submit_order handler for H-DCN orders.

POST /orders/{id}/submit — Validates and submits a draft order:
1. Validate state transition draft→submitted via order_state_machine
2. Generate human-readable order_number via number_generator
3. For each item:
   - Verify product_id exists in Producten table
   - If variant_id present: verify variant exists and variant.parent_id == product_id
   - Validate required item_fields_data against product's order_item_fields (strict)
   - Validate purchase_rules server-side
4. On success: set status to "submitted", store order_number, record submitted_at
5. On failure: return 400 with structured errors [{item_index, field, message}]

Requirements: 1.2, 3.1, 3.2, 3.3, 5.5, 6.3, 6.4, 6.5
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
    from shared.order_state_machine import transition_order, InvalidTransitionError
    from shared.number_generator import generate_order_number, CounterWriteError
    from shared.item_fields_validator import validate_item_fields
    from shared.purchase_rules_engine import validate_purchase_rules as check_purchase_rules
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
counters_table = dynamodb.Table(os.environ.get('COUNTERS_TABLE_NAME', 'Counters'))
memberships_table_name = os.environ.get('MEMBERSHIPS_TABLE_NAME', 'Memberships')
memberships_table = dynamodb.Table(memberships_table_name)


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

        # Validate state transition draft→submitted via state machine
        current_status = order.get('status', 'draft')
        try:
            transition_order(current_status, 'submitted')
        except InvalidTransitionError as e:
            return create_error_response(400, str(e), {
                'current': e.current,
                'target': e.target,
                'allowed': e.allowed,
            })

        # Validate all order items
        items = order.get('items', [])
        if not items:
            return create_error_response(
                400, 'Cannot submit order with no items'
            )

        validation_errors = _validate_order_items(items, order)

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

        # Generate order number
        try:
            order_number = generate_order_number(counters_table)
        except CounterWriteError as e:
            logger.error(f"Failed to generate order number: {e}")
            return create_error_response(
                500, 'Failed to generate order number. Please retry.'
            )

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
                'updated_at = :now, order_number = :order_number, '
                'status_history = list_append('
                'if_not_exists(status_history, :empty_list), :history_entry)'
            ),
            ConditionExpression=Attr('status').eq('draft'),
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':submitted': 'submitted',
                ':now': now,
                ':order_number': order_number,
                ':history_entry': [history_entry],
                ':empty_list': [],
            },
            ReturnValues='ALL_NEW',
        )

        updated_order = updated.get('Attributes', {})

        logger.info(
            f"Order {order_id} submitted successfully by {user_email} "
            f"(order_number={order_number})"
        )

        return create_success_response({
            'order_id': order_id,
            'order_number': order_number,
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
        logger.error(
            f"Error submitting order "
            f"{(event.get('pathParameters') or {}).get('id', 'unknown')}: "
            f"{str(e)}",
            exc_info=True,
        )
        return create_error_response(500, 'Internal server error')


def _get_order(order_id):
    """Fetch order by order_id. Returns order dict or None."""
    try:
        response = orders_table.get_item(Key={'order_id': order_id})
        return response.get('Item')
    except Exception as e:
        logger.error(f"Error fetching order {order_id}: {e}")
        return None


def _validate_order_items(items, order):
    """
    Validate all items in an order for submission.

    For each item:
    - Verify product_id exists in Producten table
    - If variant_id present: verify variant exists and parent_id matches product_id
    - Validate required item_fields_data against product's order_item_fields (strict)
    - Validate purchase_rules server-side

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

        # Validate item_fields_data if product has order_item_fields (strict)
        order_item_fields = product.get('order_item_fields')
        if order_item_fields:
            item_fields_data = item.get('item_fields_data')
            field_errors = _validate_item_fields_strict(
                item_fields_data, order_item_fields, quantity, idx
            )
            errors.extend(field_errors)

        # Validate purchase_rules server-side
        purchase_rules = product.get('purchase_rules')
        if purchase_rules:
            rule_error = _validate_purchase_rules_for_item(
                purchase_rules, product_id, quantity, order
            )
            if rule_error:
                errors.append({
                    'item_index': idx,
                    'field': 'purchase_rules',
                    'message': rule_error,
                })

    return errors


def _get_product(product_id):
    """Fetch a product/variant record by product_id. Returns item or None."""
    try:
        response = producten_table.get_item(Key={'product_id': product_id})
        return response.get('Item')
    except Exception as e:
        logger.error(f"Error fetching product {product_id}: {e}")
        return None


def _validate_item_fields_strict(item_fields_data, order_item_fields, quantity, item_index):
    """
    Validate item_fields_data against the product's order_item_fields definition.

    Uses the shared validate_item_fields for strict validation (all errors returned).
    Converts validation errors into the submit_order error format:
    [{item_index, field, message}]
    """
    errors = []

    # Use strict shared validator (returns list of all errors)
    field_errors = validate_item_fields(order_item_fields, item_fields_data, quantity)

    for err in field_errors:
        errors.append({
            'item_index': item_index,
            'field': err.get('field_id', 'item_fields_data'),
            'message': err.get('message', 'Validation failed'),
        })

    return errors


def _validate_purchase_rules_for_item(purchase_rules, product_id, quantity, order):
    """
    Server-side check of purchase_rules for a single item.

    Uses the purchase_rules_engine orchestrator which queries DynamoDB for
    existing member/club counts.

    Returns error message string if violated, None if passes.
    """
    member_id = order.get('member_id')
    club_id = order.get('club_id')

    context = {
        'quantity': quantity,
        'product_id': product_id,
        'member_id': member_id or '',
        'club_id': club_id,
        'orders_table': orders_table,
        'memberships_table': memberships_table,
    }

    violation = check_purchase_rules(purchase_rules, context)
    if violation:
        details = violation.get('details', {})
        rule = details.get('rule', 'unknown')
        limit = details.get('limit', '?')
        current = details.get('current_total', details.get('remaining_allowed', '?'))
        return (
            f"Purchase rule violated: {rule} "
            f"(limit={limit}, current={current}, requested={quantity})"
        )

    return None
