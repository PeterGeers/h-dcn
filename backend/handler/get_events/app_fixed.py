import json
import boto3

# Import shared authentication utilities with fallback support
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
except ImportError:
    # Fallback to local auth_fallback.py if shared module not available
    from auth_fallback import (
        extract_user_credentials,
        validate_permissions_with_regions,
        cors_headers,
        handle_options_request,
        create_error_response,
        create_success_response,
        log_successful_access
    )

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Events')

def lambda_handler(event, context):
    try:
        # Handle OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        # Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        # Validate permissions - require events_read permission
        required_permissions = ['events_read']
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, required_permissions, user_email, None
        )
        if not is_authorized:
            return error_response

        # Log successful access
        log_successful_access(user_email, user_roles, 'get_events')

        # Get events from database
        response = table.scan()
        events = response['Items']
        
        return create_success_response(events)
        
    except Exception as e:
        print(f"Error in get_events handler: {str(e)}")
        return create_error_response(500, f'Internal server error: {str(e)}')