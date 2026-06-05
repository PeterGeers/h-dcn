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
    from shared.stock_helpers import create_inbound_movement
    print("Using shared auth layer")
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("admin_add_stock")
    import sys
    sys.exit(0)

dynamodb = boto3.resource('dynamodb')
producten_table_name = os.environ.get('PRODUCTEN_TABLE_NAME', 'Producten')
movements_table_name = os.environ.get('STOCK_MOVEMENTS_TABLE_NAME', 'StockMovements')
producten_table = dynamodb.Table(producten_table_name)
movements_table = dynamodb.Table(movements_table_name)


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

        log_successful_access(user_email, user_roles, 'admin_add_stock')

        # Get path parameters
        path_params = event.get('pathParameters') or {}
        product_id = path_params.get('id')
        variant_id = path_params.get('vid')
        if not product_id or not variant_id:
            return create_error_response(400, 'Product ID and Variant ID are required')

        # Parse request body
        body = json.loads(event.get('body') or '{}')

        # Validate required fields
        quantity = body.get('quantity')
        purchase_price_per_unit = body.get('purchase_price_per_unit')
        supplier_name = body.get('supplier_name')

        if not quantity or not isinstance(quantity, int) or quantity <= 0:
            return create_error_response(400, 'quantity must be a positive integer')
        if purchase_price_per_unit is None or not isinstance(purchase_price_per_unit, (int, float)) or purchase_price_per_unit < 0:
            return create_error_response(400, 'purchase_price_per_unit must be a non-negative number')
        if not supplier_name or not isinstance(supplier_name, str):
            return create_error_response(400, 'supplier_name is required')

        # Verify variant exists and belongs to the product
        response = producten_table.get_item(Key={'product_id': variant_id})
        if 'Item' not in response:
            return create_error_response(404, 'Variant not found')

        variant = response['Item']
        if variant.get('parent_id') != product_id:
            return create_error_response(400, 'Variant does not belong to the specified product')

        tenant = variant.get('tenant', 'h-dcn')
        reference = body.get('reference')

        # Create inbound stock movement record
        movement = create_inbound_movement(
            variant_id=variant_id,
            tenant=tenant,
            quantity=quantity,
            purchase_price_per_unit=purchase_price_per_unit,
            supplier_name=supplier_name,
            recorded_by=user_email,
            reference=reference,
            movements_table=movements_table
        )

        # Increment stock on the variant
        producten_table.update_item(
            Key={'product_id': variant_id},
            UpdateExpression='SET stock = stock + :qty, updated_at = :now',
            ExpressionAttributeValues={
                ':qty': quantity,
                ':now': datetime.now(timezone.utc).isoformat()
            }
        )

        return create_success_response({
            'movement': movement,
            'message': f'Stock increased by {quantity} units'
        })

    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        print(f"Error adding stock: {str(e)}")
        return create_error_response(500, 'Internal server error')
