"""
MIGRATION TEMPLATE FOR: hdcn_cognito_admin
OLD ROLES: ['Members_CRUD', 'Members_Read', 'Events_CRUD', 'Events_Read', 'Products_CRUD', 'Products_Read']
NEW PERMISSIONS: ['members_update', 'events_read', 'products_read', 'events_delete', 'products_create', 'events_update', 'events_list', 'members_list', 'members_read', 'members_export', 'products_export', 'events_create', 'products_list', 'events_export', 'members_delete', 'products_delete', 'products_update', 'members_create']

MIGRATION NOTES:
- 'Members_CRUD' -> check permissions: ['members_create', 'members_read', 'members_update', 'members_delete', 'members_export']
- 'Members_Read' -> check permissions: ['members_read', 'members_list', 'members_export']
- 'Events_CRUD' -> check permissions: ['events_create', 'events_read', 'events_update', 'events_delete', 'events_export']
- 'Events_Read' -> check permissions: ['events_read', 'events_list', 'events_export']
- 'Products_CRUD' -> check permissions: ['products_create', 'products_read', 'products_update', 'products_delete', 'products_export']
- 'Products_Read' -> check permissions: ['products_read', 'products_list', 'products_export']
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
    user_roles, ['members_update', 'events_read', 'products_read', 'events_delete', 'products_create', 'events_update', 'events_list', 'members_list', 'members_read', 'members_export', 'products_export', 'events_create', 'products_list', 'events_export', 'members_delete', 'products_delete', 'products_update', 'members_create'], user_email, resource_context
)
if not is_authorized:
    return error_response
        
        # Log successful access
        log_successful_access(user_email, user_roles, 'hdcn_cognito_admin')
        
        # TODO: Add your handler logic here
        # The user is now authorized with the new role structure
        
        return create_success_response({"message": "Handler updated successfully"})
        
    except Exception as e:
        print(f"Error in hdcn_cognito_admin: {str(e)}")
        return create_error_response(500, f"Internal server error in hdcn_cognito_admin")
