import json
import boto3

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
    print("✅ Using shared auth layer")
except ImportError as e:
    # Built-in smart fallback - no local auth_fallback.py needed
    print(f"❌ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("delete_member")
    # Exit early - the fallback handler will handle all requests
    import sys
    sys.exit(0)

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Members')

def lambda_handler(event, context):
    try:
        # Handle OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()
        
        # Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error
        
        # Validate permissions - only admins can delete members
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['members_delete'], user_email, {'operation': 'delete_member'}
        )
        if not is_authorized:
            return error_response
        
        # Log successful access
        log_successful_access(user_email, user_roles, 'delete_member')
        
        # Get member_id from path parameters
        if not event.get('pathParameters') or not event['pathParameters'].get('id'):
            return create_error_response(400, 'Member ID is required in path parameters')
        
        member_id = event['pathParameters']['id']
        
        # Check if member exists before deleting
        response = table.get_item(Key={'member_id': member_id})
        if 'Item' not in response:
            return create_error_response(404, 'Member not found')
        
        # Delete the member
        table.delete_item(Key={'member_id': member_id})
        
        return create_success_response({'message': 'Member deleted successfully', 'member_id': member_id})
        
    except Exception as e:
        return create_error_response(500, f'Internal server error: {str(e)}')