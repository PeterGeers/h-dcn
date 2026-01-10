import json
import boto3

# Import authentication utilities from shared layer or fallback
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
    print("✅ Using shared auth layer")
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
    print("⚠️ Using fallback auth - ensure auth_fallback.py is updated")

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Members')

def lambda_handler(event, context):
    try:
        # Handle OPTIONS request for CORS
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()
        
        # Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error
        
        # UPDATED: Use new permission-based validation instead of Members_Read_All
        # Required permissions for reading member data
        required_permissions = ['members_read', 'members_list']
        
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, required_permissions, user_email
        )
        if not is_authorized:
            return error_response
        
        # Log successful access
        log_successful_access(user_email, user_roles, 'get_member_byid')
        
        # Get member ID from path parameters
        member_id = event['pathParameters']['id']
        
        # Retrieve member record
        response = table.get_item(Key={'member_id': member_id})
        
        if 'Item' not in response:
            return create_error_response(404, 'Member not found')
        
        member_data = response['Item']
        
        # Apply regional filtering if user has regional restrictions
        if regional_info and not regional_info.get('has_full_access', False):
            member_region = member_data.get('regio', '')
            allowed_regions = regional_info.get('allowed_regions', [])
            
            # Check if user can access this member's region
            if member_region and allowed_regions and member_region not in allowed_regions:
                print(f"REGIONAL_ACCESS_DENIED: User {user_email} (regions: {allowed_regions}) "
                      f"attempted to access member from region: {member_region}")
                return create_error_response(403, 
                    f'Access denied: You can only access members from regions: {", ".join(allowed_regions)}')
        
        print(f"✅ Member {member_id} retrieved by user {user_email} with roles {user_roles}")
        
        return create_success_response(member_data)
        
    except KeyError as e:
        return create_error_response(400, f'Missing required parameter: {str(e)}')
    except Exception as e:
        print(f"Error in get_member_byid: {str(e)}")
        return create_error_response(500, 'Internal server error')