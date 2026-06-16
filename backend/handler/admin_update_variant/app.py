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
    print("Using shared auth layer")
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("admin_update_variant")
    import sys
    sys.exit(0)

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('PRODUCTEN_TABLE_NAME', 'Producten')
table = dynamodb.Table(table_name)

# Fields allowed to be updated on a variant
UPDATABLE_VARIANT_FIELDS = ['stock', 'allow_oversell', 'prijs', 'naam', 'active']


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

        log_successful_access(user_email, user_roles, 'admin_update_variant')

        # Get path parameters
        path_params = event.get('pathParameters') or {}
        product_id = path_params.get('id')
        variant_id = path_params.get('vid')
        if not product_id or not variant_id:
            return create_error_response(400, 'Product ID and Variant ID are required')

        # Parse request body
        body = json.loads(event.get('body') or '{}')

        # Verify variant exists and belongs to the product
        response = table.get_item(Key={'product_id': variant_id})
        if 'Item' not in response:
            return create_error_response(404, 'Variant not found')

        variant = response['Item']
        if variant.get('parent_id') != product_id:
            return create_error_response(400, 'Variant does not belong to the specified product')

        # Build update expression
        update_parts = []
        remove_parts = []
        expression_values = {}
        expression_names = {}

        for field in UPDATABLE_VARIANT_FIELDS:
            if field in body:
                if body[field] is None:
                    # Remove the attribute when value is null
                    attr_name = f'#{field}'
                    remove_parts.append(attr_name)
                    expression_names[attr_name] = field
                else:
                    attr_name = f'#{field}'
                    attr_val = f':{field}'
                    update_parts.append(f'{attr_name} = {attr_val}')
                    expression_names[attr_name] = field
                    expression_values[attr_val] = body[field]

        if not update_parts and not remove_parts:
            return create_error_response(400, 'No updatable fields provided')

        # Always update updated_at
        update_parts.append('#updated_at = :updated_at')
        expression_names['#updated_at'] = 'updated_at'
        expression_values[':updated_at'] = datetime.now(timezone.utc).isoformat()

        update_expression = 'SET ' + ', '.join(update_parts)
        if remove_parts:
            update_expression += ' REMOVE ' + ', '.join(remove_parts)

        updated = table.update_item(
            Key={'product_id': variant_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_names,
            ExpressionAttributeValues=expression_values,
            ReturnValues='ALL_NEW'
        )

        return create_success_response({
            'variant': updated.get('Attributes', {}),
            'message': 'Variant updated successfully'
        })

    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        print(f"Error updating variant: {str(e)}")
        return create_error_response(500, 'Internal server error')
