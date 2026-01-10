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
    # Fallback to local auth_fallback.py
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
table = dynamodb.Table('Members')

def lambda_handler(event, context):
    """
    Get members handler using new permission + region role structure
    Replaces Members_Read_All references with permission-based validation
    """
    try:
        # Handle OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()
        
        # Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error
        
        # UPDATED: Use new permission-based validation instead of Members_Read_All role checking
        # Required permissions: members_read (basic read access) or members_list (list all members)
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['members_read', 'members_list'], user_email, {'operation': 'get_members'}
        )
        if not is_authorized:
            return error_response
        
        # Log successful access
        log_successful_access(user_email, user_roles, 'get_members', {'regional_access': regional_info})
        
        # Get all members from database
        response = table.scan()
        members = response['Items']
        
        # Apply regional filtering if user has regional restrictions
        if regional_info and not regional_info.get('has_full_access', False):
            allowed_regions = regional_info.get('allowed_regions', [])
            if allowed_regions and 'all' not in allowed_regions:
                # Filter members by user's allowed regions
                filtered_members = []
                for member in members:
                    member_region = member.get('regio', 'Overig')  # Default to 'Overig' if no region
                    if member_region in allowed_regions:
                        filtered_members.append(member)
                
                members = filtered_members
                print(f"REGIONAL_FILTER: User {user_email} (regions: {allowed_regions}) "
                      f"filtered {len(response['Items'])} members to {len(members)} members")
        
        return create_success_response(members)
        
    except Exception as e:
        print(f"Error in get_members: {str(e)}")
        return create_error_response(500, f"Internal server error in get_members: {str(e)}")