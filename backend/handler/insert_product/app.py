import json
import boto3
import sys
import os
import uuid
from datetime import datetime

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
    # Built-in smart fallback - no local auth_fallback.py needed
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("insert_product")
    # Exit early - the fallback handler will handle all requests
    import sys
    sys.exit(0)

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('DYNAMODB_TABLE', 'Producten')
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
        
        # UPDATED: Check for products create permission with new role structure
        # Users now have Products_CRUD + Regio_* instead of Products_CRUD_All
        # The validate_permissions_with_regions function will:
        # 1. Check if user has Products_CRUD role (which grants products_create permission)
        # 2. Check if user has a region role (Regio_All, Regio_*, etc.)
        # 3. Ensure both permission + region requirements are met
        required_permissions = ['products_create']
        
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, required_permissions, user_email, None
        )
        if not is_authorized:
            return error_response
        
        # Log successful access
        log_successful_access(user_email, user_roles, 'insert_product')
        
        # Parse product data from request body
        product = json.loads(event['body']) if event['body'] else {}
        
        # Generate product ID
        product_id = str(uuid.uuid4())
        
        # Convert image to array if it's a string
        if 'image' in product and isinstance(product['image'], str):
            product['image'] = [product['image']]
        
        # Create item with generated ID and timestamp
        item = {
            'id': product_id,
            'createdAt': datetime.now().isoformat(), 
            **product
        }

        table.put_item(Item=item)

        print(f"Product {product_id} created by {user_email} with roles {user_roles}")

        return create_success_response({
            "id": product_id,
            "message": "Product created successfully"
        }, 201)
        
    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        print(f"Unexpected error in insert_product: {str(e)}")
        return create_error_response(500, 'Internal server error')
