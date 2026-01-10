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
table_name = os.environ.get('DYNAMODB_TABLE', 'Events')
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
        
        # UPDATED: Check for events delete permission with new role structure
        # Users now have Events_CRUD + Regio_* instead of Events_CRUD_All
        # The validate_permissions_with_regions function will:
        # 1. Check if user has Events_CRUD role (which grants events_delete permission)
        # 2. Check if user has a region role (Regio_All, Regio_*, etc.)
        # 3. Ensure both permission + region requirements are met
        required_permissions = ['events_delete']
        
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, required_permissions, user_email, None
        )
        if not is_authorized:
            return error_response
        
        # Log successful access
        log_successful_access(user_email, user_roles, 'delete_event')
        
        # Get event ID from path parameters
        event_id = event['pathParameters']['event_id']
        
        # Delete the event
        table.delete_item(Key={'event_id': event_id})
        
        print(f"Event {event_id} deleted by {user_email} with roles {user_roles}")
        
        return {
            'statusCode': 204,
            'headers': cors_headers(),
            'body': ''
        }
        
    except KeyError as e:
        return create_error_response(400, f'Missing required parameter: {str(e)}')
    except Exception as e:
        print(f"Unexpected error in delete_event: {str(e)}")
        return create_error_response(500, 'Internal server error')