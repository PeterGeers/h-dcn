import json
import os
import uuid
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
    from shared.variant_helpers import generate_variant_combinations, should_remove_default_variant
    print("Using shared auth layer")
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("admin_bulk_create_variants")
    import sys
    sys.exit(0)

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('PRODUCTEN_TABLE_NAME', 'Producten')
table = dynamodb.Table(table_name)


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

        log_successful_access(user_email, user_roles, 'admin_bulk_create_variants')

        # Get product ID from path parameters
        path_params = event.get('pathParameters') or {}
        product_id = path_params.get('id')
        if not product_id:
            return create_error_response(400, 'Product ID is required')

        # Get parent product
        parent_response = table.get_item(Key={'product_id': product_id})
        if 'Item' not in parent_response:
            return create_error_response(404, 'Parent product not found')

        parent = parent_response['Item']
        if not parent.get('is_parent', False):
            return create_error_response(400, 'Cannot add variants to a non-parent product')

        required_attributes = parent.get('required_attributes')
        if not required_attributes:
            return create_error_response(400, 'Product has no required_attributes defined. Cannot generate variants.')

        # Generate all attribute combinations
        combinations = generate_variant_combinations(required_attributes)
        if not combinations:
            return create_error_response(400, 'No valid attribute combinations could be generated from required_attributes')

        # Parse optional body for default values
        body = json.loads(event.get('body') or '{}')
        default_price = body.get('price', parent.get('price'))
        default_stock = body.get('stock', 0)
        default_allow_oversell = body.get('allow_oversell', False)

        now = datetime.now(timezone.utc).isoformat()
        tenant = parent.get('tenant', 'h-dcn')

        # Create variant records
        created_variants = []
        for combo in combinations:
            variant_id = f"var_{uuid.uuid4().hex[:12]}"
            # Generate a readable name from attributes
            name_parts = [f"{v}" for v in combo.values()]
            variant_name = ' / '.join(name_parts)

            variant = {
                'product_id': variant_id,
                'parent_id': product_id,
                'tenant': tenant,
                'name': variant_name,
                'is_parent': False,
                'variant_attributes': combo,
                'price': default_price,
                'stock': default_stock,
                'sold_count': 0,
                'allow_oversell': default_allow_oversell,
                'active': True,
                'created_at': now,
                'updated_at': now,
            }
            table.put_item(Item=variant)
            created_variants.append(variant)

        # Check if Default_Variant should be removed
        existing_variants_response = table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('parent_id').eq(product_id) & boto3.dynamodb.conditions.Attr('is_parent').eq(False)
        )
        existing_before = [v for v in existing_variants_response.get('Items', []) if v['product_id'] not in [cv['product_id'] for cv in created_variants]]

        remove_default = should_remove_default_variant(existing_before, created_variants)
        removed_default = False
        if remove_default:
            default_variant_id = f"var_{product_id}_default"
            try:
                table.delete_item(Key={'product_id': default_variant_id})
                removed_default = True
            except Exception as del_err:
                print(f"Warning: Could not remove Default_Variant: {str(del_err)}")

        return create_success_response({
            'variants': created_variants,
            'total_created': len(created_variants),
            'default_variant_removed': removed_default,
            'message': f'{len(created_variants)} variants created successfully'
        })

    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        print(f"Error bulk creating variants: {str(e)}")
        return create_error_response(500, 'Internal server error')
