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
    from shared.product_validation import validate_variant_attributes
    from shared.variant_helpers import should_remove_default_variant
    print("Using shared auth layer")
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("admin_create_variant")
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

        log_successful_access(user_email, user_roles, 'admin_create_variant')

        # Get product ID from path parameters
        path_params = event.get('pathParameters') or {}
        product_id = path_params.get('id')
        if not product_id:
            return create_error_response(400, 'Product ID is required')

        # Parse request body
        body = json.loads(event.get('body') or '{}')

        # Get parent product to validate attributes
        parent_response = table.get_item(Key={'product_id': product_id})
        if 'Item' not in parent_response:
            return create_error_response(404, 'Parent product not found')

        parent = parent_response['Item']
        if not parent.get('is_parent', False):
            return create_error_response(400, 'Cannot add variants to a non-parent product')

        # Validate variant attributes against parent's required_attributes
        variant_attributes = body.get('variant_attributes', {})
        parent_required_attrs = parent.get('required_attributes')

        is_valid, errors = validate_variant_attributes(variant_attributes, parent_required_attrs)
        if not is_valid:
            return create_error_response(400, 'Variant attribute validation failed', {'errors': errors})

        # Generate variant ID
        variant_id = f"var_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()

        # Build variant record
        variant = {
            'product_id': variant_id,
            'parent_id': product_id,
            'tenant': parent.get('tenant', 'h-dcn'),
            'name': body.get('name', ''),
            'is_parent': False,
            'variant_attributes': variant_attributes,
            'price': body.get('price', parent.get('price')),
            'stock': body.get('stock', 0),
            'sold_count': 0,
            'allow_oversell': body.get('allow_oversell', False),
            'active': body.get('active', True),
            'created_at': now,
            'updated_at': now,
        }

        # Get existing variants to check if Default_Variant should be removed
        existing_variants_response = table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('parent_id').eq(product_id) & boto3.dynamodb.conditions.Attr('is_parent').eq(False)
        )
        existing_variants = existing_variants_response.get('Items', [])

        # Check if we should remove the Default_Variant
        remove_default = should_remove_default_variant(existing_variants, [variant])

        # Write new variant
        table.put_item(Item=variant)

        # Remove Default_Variant if applicable
        removed_default = False
        if remove_default:
            default_variant_id = f"var_{product_id}_default"
            try:
                table.delete_item(Key={'product_id': default_variant_id})
                removed_default = True
            except Exception as del_err:
                print(f"Warning: Could not remove Default_Variant: {str(del_err)}")

        return create_success_response({
            'variant': variant,
            'default_variant_removed': removed_default,
            'message': 'Variant created successfully'
        })

    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        print(f"Error creating variant: {str(e)}")
        return create_error_response(500, 'Internal server error')
