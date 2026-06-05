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
    from shared.variant_helpers import create_default_variant
    from shared.product_validation import validate_product
    print("Using shared auth layer")
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("admin_create_product")
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

        log_successful_access(user_email, user_roles, 'admin_create_product')

        # Parse request body
        body = json.loads(event.get('body') or '{}')

        # Validate product payload
        is_valid, errors = validate_product(body)
        if not is_valid:
            return create_error_response(400, 'Validation failed', {'errors': errors})

        # Generate product ID
        product_id = f"prod_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()

        # Build product record (parent)
        product = {
            'product_id': product_id,
            'tenant': body.get('tenant', 'h-dcn'),
            'name': body.get('name'),
            'description': body.get('description', ''),
            'category': body.get('category', ''),
            'is_parent': True,
            'parent_id': None,
            'price': body.get('price'),
            'active': body.get('active', True),
            'min_per_club': body.get('min_per_club'),
            'max_per_club': body.get('max_per_club'),
            'required_attributes': body.get('required_attributes'),
            'image_url': body.get('image_url'),
            'created_by': user_email,
            'created_at': now,
            'updated_at': now,
        }

        # Remove None values
        product = {k: v for k, v in product.items() if v is not None}

        # Write product to DynamoDB
        table.put_item(Item=product)

        # Auto-create Default_Variant
        default_variant = create_default_variant(product_id, product.get('tenant', 'h-dcn'))
        # Inherit price from parent if set
        if body.get('price') is not None:
            default_variant['price'] = body['price']
        table.put_item(Item=default_variant)

        return create_success_response({
            'product': product,
            'default_variant': default_variant,
            'message': 'Product created successfully'
        })

    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        print(f"Error creating product: {str(e)}")
        return create_error_response(500, 'Internal server error')
