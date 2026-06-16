import json
import os
import boto3
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
        log_successful_access
    )
    from shared.variant_sync import sync_variant_to_schema
    print("Using shared auth layer")
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("admin_delete_variant")
    import sys
    sys.exit(0)

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('PRODUCTEN_TABLE_NAME', 'Producten')
table = dynamodb.Table(table_name)

orders_table_name = os.environ.get('ORDERS_TABLE_NAME', 'Orders')
orders_table = dynamodb.Table(orders_table_name)


def lambda_handler(event, context):
    try:
        # Handle OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # Validate permissions - requires Products_CRUD
        is_authorized, permission_error, regional_info = validate_permissions_with_regions(
            user_roles, ['Products_CRUD'], user_email, None
        )
        if not is_authorized:
            return permission_error

        log_successful_access(user_email, user_roles, 'admin_delete_variant')

        # Get path parameters
        path_params = event.get('pathParameters') or {}
        product_id = path_params.get('id')
        variant_id = path_params.get('vid')
        if not product_id or not variant_id:
            return create_error_response(400, 'Product ID and Variant ID are required')

        # Verify variant exists and belongs to the product
        response = table.get_item(Key={'product_id': variant_id})
        if 'Item' not in response:
            return create_error_response(404, 'Variant not found')

        variant = response['Item']
        if variant.get('parent_id') != product_id:
            return create_error_response(400, 'Variant does not belong to the specified product')

        # Scan Orders table for any line_items referencing this variant
        order_count = _count_orders_referencing_variant(variant_id)
        if order_count > 0:
            return create_error_response(
                409,
                f'Variant cannot be deleted: referenced by {order_count} order(s). Deactivate instead.'
            )

        # No orders reference this variant — delete it
        table.delete_item(Key={'product_id': variant_id})

        # Rebuild parent schema from remaining active variants
        sync_variant_to_schema(table, product_id, {})

        return create_success_response({
            'message': 'Variant deleted successfully',
            'variant_id': variant_id
        })

    except Exception as e:
        print(f"Error deleting variant: {str(e)}")
        return create_error_response(500, 'Internal server error')


def _count_orders_referencing_variant(variant_id):
    """
    Scan the Orders table and count how many orders have a line_item
    referencing the given variant_id.
    """
    count = 0
    scan_kwargs = {}

    while True:
        response = orders_table.scan(**scan_kwargs)
        items = response.get('Items', [])

        for order in items:
            line_items = order.get('line_items', [])
            for item in line_items:
                if item.get('variant_id') == variant_id:
                    count += 1
                    break  # Only count this order once

        # Handle pagination
        if 'LastEvaluatedKey' in response:
            scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
        else:
            break

    return count
