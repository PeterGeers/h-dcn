import boto3
import os
import json
import logging
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

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
    lambda_handler = create_smart_fallback_handler("get_product_byid")
    # Exit early - the fallback handler will handle all requests
    import sys
    sys.exit(0)

table_name = str(os.environ.get('DYNAMODB_TABLE', 'Producten'))
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(table_name)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    try:
        # Handle OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()
        
        # Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error
        
        # UPDATED: Check for products read permission with new role structure
        # Users now have Products_CRUD + Regio_* or Products_Read + Regio_* instead of Products_Read_All
        # The validate_permissions_with_regions function will:
        # 1. Check if user has Products_CRUD or Products_Read role (which grants products_read permission)
        # 2. Check if user has a region role (Regio_All, Regio_*, etc.)
        # 3. Ensure both permission + region requirements are met
        required_permissions = ['products_read']
        
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, required_permissions, user_email, None
        )
        if not is_authorized:
            return error_response
        
        # Log successful access
        log_successful_access(user_email, user_roles, 'get_product_byid')

        if not event.get('pathParameters') or 'id' not in event['pathParameters']:
            return create_error_response(400, 'Missing product ID')

        id = event['pathParameters']['id']
        logger.info(f"Fetching product with ID: {id}")

        # Use id as the key (existing table schema)
        response = table.get_item(
            Key={'id': id}
        )

        if 'Item' not in response:
            return create_error_response(404, f'Product {id} not found')

        print(f"Product {id} retrieved by {user_email} with roles {user_roles}")

        return create_success_response(response['Item'])

    except ClientError as e:
        logger.error(f"DynamoDB error: {e}")
        return create_error_response(500, f'Database error: {str(e)}')
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return create_error_response(500, 'Internal server error')