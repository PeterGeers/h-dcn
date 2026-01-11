import json
import boto3
import sys
import os
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
except ImportError:
    # Fallback to local auth_fallback.py (UPDATED FOR NEW ROLE STRUCTURE)
    from auth_fallback import (
        extract_user_credentials,
        validate_permissions_with_regions,
        cors_headers,
        handle_options_request,
        create_error_response,
        create_success_response,
        log_successful_access
    )
    print("Using fallback auth - ensure auth_fallback.py is updated")

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
        
        # UPDATED: Check for products delete permission with new role structure
        # Users now have Products_CRUD + Regio_* instead of legacy roles
        # The validate_permissions_with_regions function will:
        # 1. Check if user has Products_CRUD role (which grants products_delete permission)
        # 2. Check if user has a region role (Regio_All, Regio_*, etc.)
        # 3. Ensure both permission + region requirements are met
        required_permissions = ['products_delete']
        
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, required_permissions, user_email, None
        )
        if not is_authorized:
            return error_response
        
        # Log successful access
        log_successful_access(user_email, user_roles, 'delete_product')
        
        # Validate product ID parameter
        if not event.get('pathParameters') or 'id' not in event['pathParameters']:
            return create_error_response(400, 'Missing product ID')

        product_id = event['pathParameters']['id']
        print(f"Deleting product with ID: {product_id}")

        # Delete the product
        response = table.delete_item(
            Key={'id': product_id},
            ReturnValues='ALL_OLD'
        )
        
        if 'Attributes' not in response:
            return create_error_response(404, f'Product {product_id} not found')
        
        print(f"Product {product_id} deleted by {user_email} with roles {user_roles}")

        return create_success_response({
            'message': f'Product {product_id} deleted successfully'
        })
        
    except KeyError as e:
        return create_error_response(400, f'Missing required parameter: {str(e)}')
    except Exception as e:
        print(f"Unexpected error in delete_product: {str(e)}")
        return create_error_response(500, 'Internal server error')
