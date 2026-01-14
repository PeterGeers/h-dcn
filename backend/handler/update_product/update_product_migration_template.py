"""
MIGRATION TEMPLATE FOR: update_product
OLD ROLES: ['Products_CRUD'] (DEPRECATED _All ROLES REMOVED)
NEW PERMISSIONS: ['products_read', 'products_create', 'products_delete', 'products_update', 'products_export']

MIGRATION NOTES:
- 'Products_CRUD' -> check permissions: ['products_create', 'products_read', 'products_update', 'products_delete', 'products_export']
"""

import json
import boto3
from datetime import datetime

# Import from shared auth layer (REQUIRED)
try:
    from auth_utils import (
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
    # Fallback to local auth_fallback.py (UPDATE THIS FILE TOO)
    from auth_fallback import (
        extract_user_credentials,
        validate_permissions_with_regions,  # MUST BE UPDATED IN FALLBACK
        cors_headers,
        handle_options_request,
        create_error_response,
        create_success_response,
        log_successful_access
    )
    print("Using fallback auth - ensure auth_fallback.py is updated")


def lambda_handler(event, context):
    """
    Updated handler using new role structure
    """
    try:
        # Handle OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()
        
        # Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error
        
        # UPDATED: Use new permission-based validation instead of role checking
        # Updated role check - use enhanced validation
is_authorized, error_response, regional_info = validate_permissions_with_regions(
    user_roles, ['products_read', 'products_create', 'products_delete', 'products_update', 'products_export'], user_email, resource_context
)
if not is_authorized:
    return error_response
        
        # Log successful access
        log_successful_access(user_email, user_roles, 'update_product')
        
        # TODO: Add your handler logic here
        # The user is now authorized with the new role structure
        
        return create_success_response({"message": "Handler updated successfully"})
        
    except Exception as e:
        print(f"Error in update_product: {str(e)}")
        return create_error_response(500, f"Internal server error in update_product")
