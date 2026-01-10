import json
import boto3
import os
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
        # Users now have Products_CRUD + Regio_* or Products_Read + Regio_* (deprecated _All roles removed)
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
        log_successful_access(user_email, user_roles, 'scan_product')
        
        # Get products from DynamoDB
        table_name = os.environ.get('DYNAMODB_TABLE', 'Producten')
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(table_name)

        response = table.scan(Limit=100)
        items = response['Items']
        
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                ExclusiveStartKey=response['LastEvaluatedKey'],
                Limit=100
            )
            items.extend(response['Items'])

        print(f"Products scanned by {user_email} with roles {user_roles} - returned {len(items)} items")

        return create_success_response(items)
    
    except ClientError as e:
        print(f"DynamoDB error in scan_product: {str(e)}")
        return create_error_response(500, f'Database error: {str(e)}')
    except Exception as e:
        print(f"Unexpected error in scan_product: {str(e)}")
        return create_error_response(500, 'Internal server error')