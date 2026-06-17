"""
Admin endpoint to delete a product (soft or hard).

DELETE /admin/products/{id}
  - Default: soft-delete → sets active=false on product and all child variants
  - With ?hard=true: hard-delete → permanently removes from DynamoDB
    (only allowed if zero non-cancelled orders reference the product)

Requires admin permission: products_delete

Requirements: 8.1, 8.2, 8.6
"""

import os
import logging
from datetime import datetime, timezone

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
    print("Using shared auth layer for admin_delete_product")
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("admin_delete_product")
    import sys
    sys.exit(0)

import boto3
from boto3.dynamodb.conditions import Key, Attr

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# DynamoDB resources
dynamodb = boto3.resource('dynamodb')
producten_table = dynamodb.Table(os.environ.get('PRODUCTEN_TABLE_NAME', 'Producten'))
orders_table = dynamodb.Table(os.environ.get('ORDERS_TABLE_NAME', 'Orders'))

# Maximum batch size for DynamoDB batch operations
_DYNAMO_BATCH_SIZE = 25


def lambda_handler(event, context):
    """Main handler for DELETE /admin/products/{id}."""
    try:
        # Handle OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # Validate permissions — requires products_delete
        is_authorized, permission_error, regional_info = validate_permissions_with_regions(
            user_roles, ['products_delete'], user_email, None
        )
        if not is_authorized:
            return permission_error

        log_successful_access(user_email, user_roles, 'admin_delete_product')

        # Validate product ID parameter
        if not event.get('pathParameters') or 'id' not in event['pathParameters']:
            return create_error_response(400, 'Missing product ID')

        product_id = event['pathParameters']['id']

        # Fetch the product to confirm it exists
        product = _get_product(product_id)
        if not product:
            return create_error_response(404, f'Product {product_id} not found')

        # Determine delete mode: soft (default) or hard (?hard=true)
        query_params = event.get('queryStringParameters') or {}
        is_hard_delete = query_params.get('hard', '').lower() == 'true'

        if is_hard_delete:
            return _handle_hard_delete(product_id, product, user_email)
        else:
            return _handle_soft_delete(product_id, product, user_email)

    except Exception as e:
        logger.error(f"Error in admin_delete_product: {str(e)}", exc_info=True)
        return create_error_response(500, 'Internal server error')


# ---------------------------------------------------------------------------
# Soft-delete: set active=false on product + all child variants
# ---------------------------------------------------------------------------


def _handle_soft_delete(product_id, product, user_email):
    """
    Soft-delete: set active=false on the product and all its child variants.
    """
    now = datetime.now(timezone.utc).isoformat()

    # Update the product itself
    producten_table.update_item(
        Key={'product_id': product_id},
        UpdateExpression='SET active = :false, updated_at = :now',
        ExpressionAttributeValues={
            ':false': False,
            ':now': now,
        },
    )

    # Find and deactivate all child variants
    variants = _get_child_variants(product_id)
    deactivated_count = 0

    for variant in variants:
        variant_id = variant['product_id']
        producten_table.update_item(
            Key={'product_id': variant_id},
            UpdateExpression='SET active = :false, updated_at = :now',
            ExpressionAttributeValues={
                ':false': False,
                ':now': now,
            },
        )
        deactivated_count += 1

    logger.info(
        f"Soft-deleted product {product_id} + {deactivated_count} variants "
        f"by {user_email}"
    )

    return create_success_response({
        'message': f'Product {product_id} deactivated',
        'product_id': product_id,
        'variants_deactivated': deactivated_count,
    })


# ---------------------------------------------------------------------------
# Hard-delete: permanently remove from DynamoDB (with order guard)
# ---------------------------------------------------------------------------


def _handle_hard_delete(product_id, product, user_email):
    """
    Hard-delete: permanently remove product and variants from DynamoDB.
    Blocked if any non-cancelled order references the product.
    """
    # Collect all variant IDs to check in orders
    variants = _get_child_variants(product_id)
    variant_ids = [v['product_id'] for v in variants]
    all_product_ids = [product_id] + variant_ids

    # Check if any non-cancelled orders reference this product
    order_count = _count_non_cancelled_orders_for_products(all_product_ids)

    if order_count > 0:
        logger.info(
            f"Hard-delete blocked for {product_id}: "
            f"{order_count} non-cancelled orders reference it"
        )
        return create_error_response(400, 'Cannot delete product with order history', {
            'order_count': order_count,
        })

    # No references — proceed with hard delete
    # Delete all child variants first
    deleted_variants = 0
    if variants:
        _batch_delete_items(variants)
        deleted_variants = len(variants)

    # Delete the parent product
    producten_table.delete_item(Key={'product_id': product_id})

    logger.info(
        f"Hard-deleted product {product_id} + {deleted_variants} variants "
        f"by {user_email}"
    )

    return create_success_response({
        'message': f'Product {product_id} permanently deleted',
        'product_id': product_id,
        'variants_deleted': deleted_variants,
    })


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _get_product(product_id):
    """Fetch a product record by product_id."""
    try:
        response = producten_table.get_item(Key={'product_id': product_id})
        return response.get('Item')
    except Exception as e:
        logger.error(f"Error fetching product {product_id}: {e}")
        return None


def _get_child_variants(parent_id):
    """
    Query all child variant records for a given parent product.
    Uses the parent_id-index GSI on the Producten table.
    """
    variants = []
    query_kwargs = {
        'IndexName': 'parent-id-index',
        'KeyConditionExpression': Key('parent_id').eq(parent_id),
    }

    try:
        response = producten_table.query(**query_kwargs)
        variants.extend(response.get('Items', []))

        # Handle pagination
        while 'LastEvaluatedKey' in response:
            query_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
            response = producten_table.query(**query_kwargs)
            variants.extend(response.get('Items', []))
    except Exception as e:
        logger.error(f"Error querying variants for parent {parent_id}: {e}")

    return variants


def _count_non_cancelled_orders_for_products(product_ids):
    """
    Scan the Orders table for non-cancelled orders that reference any of the
    given product IDs in their items array.

    Returns the count of matching orders.
    """
    matching_orders = set()

    # Scan orders — filter for status != cancelled
    scan_kwargs = {
        'FilterExpression': Attr('status').ne('cancelled'),
        'ProjectionExpression': 'order_id, items',
    }

    try:
        response = orders_table.scan(**scan_kwargs)
        _check_orders_for_products(response.get('Items', []), product_ids, matching_orders)

        # Handle pagination
        while 'LastEvaluatedKey' in response:
            scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
            response = orders_table.scan(**scan_kwargs)
            _check_orders_for_products(response.get('Items', []), product_ids, matching_orders)
    except Exception as e:
        logger.error(f"Error scanning orders for product references: {e}")

    return len(matching_orders)


def _check_orders_for_products(orders, product_ids, matching_orders):
    """
    Check a batch of orders to see if any items reference the given product IDs.
    Adds matching order_ids to the matching_orders set.
    """
    product_id_set = set(product_ids)

    for order in orders:
        order_id = order.get('order_id')
        items = order.get('items', [])

        for item in items:
            # Check both product_id and variant_id fields
            item_product_id = item.get('product_id')
            item_variant_id = item.get('variant_id')

            if item_product_id in product_id_set or item_variant_id in product_id_set:
                matching_orders.add(order_id)
                break  # No need to check more items in this order


def _batch_delete_items(items):
    """Delete product/variant records in batches of 25."""
    for i in range(0, len(items), _DYNAMO_BATCH_SIZE):
        batch = items[i:i + _DYNAMO_BATCH_SIZE]
        with producten_table.batch_writer() as writer:
            for item in batch:
                writer.delete_item(Key={'product_id': item['product_id']})
