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
    from shared.product_validation import validate_product
    print("Using shared auth layer")
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("admin_update_product")
    import sys
    sys.exit(0)

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('PRODUCTEN_TABLE_NAME', 'Producten')
table = dynamodb.Table(table_name)

# Fields allowed to be updated on a product
UPDATABLE_FIELDS = [
    'name', 'description', 'category', 'price', 'active',
    'min_per_club', 'max_per_club', 'required_attributes',
    'image_url', 'tenant'
]


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

        log_successful_access(user_email, user_roles, 'admin_update_product')

        # Get product ID from path parameters
        path_params = event.get('pathParameters') or {}
        product_id = path_params.get('id')
        if not product_id:
            return create_error_response(400, 'Product ID is required')

        # Parse request body
        body = json.loads(event.get('body') or '{}')

        # Validate product payload
        is_valid, errors = validate_product(body)
        if not is_valid:
            return create_error_response(400, 'Validation failed', {'errors': errors})

        # Check product exists
        response = table.get_item(Key={'product_id': product_id})
        if 'Item' not in response:
            return create_error_response(404, 'Product not found')

        existing = response['Item']
        if not existing.get('is_parent', False):
            return create_error_response(400, 'Cannot update a variant with this endpoint. Use the variant update endpoint.')

        # Build update expression
        update_parts = []
        expression_values = {}
        expression_names = {}

        for field in UPDATABLE_FIELDS:
            if field in body:
                attr_name = f'#{field}'
                attr_val = f':{field}'
                update_parts.append(f'{attr_name} = {attr_val}')
                expression_names[attr_name] = field
                expression_values[attr_val] = body[field]

        if not update_parts:
            return create_error_response(400, 'No updatable fields provided')

        # Always update updated_at
        update_parts.append('#updated_at = :updated_at')
        expression_names['#updated_at'] = 'updated_at'
        expression_values[':updated_at'] = datetime.now(timezone.utc).isoformat()

        update_expression = 'SET ' + ', '.join(update_parts)

        updated = table.update_item(
            Key={'product_id': product_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_names,
            ExpressionAttributeValues=expression_values,
            ReturnValues='ALL_NEW'
        )

        return create_success_response({
            'product': updated.get('Attributes', {}),
            'message': 'Product updated successfully'
        })

    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        print(f"Error updating product: {str(e)}")
        return create_error_response(500, 'Internal server error')
