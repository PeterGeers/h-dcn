import json
import os
import boto3
from decimal import Decimal

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
except ImportError as e:
    # Built-in smart fallback - no local auth_fallback.py needed
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("get_events")
    # Exit early - the fallback handler will handle all requests
    import sys
    sys.exit(0)

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('EVENTS_TABLE_NAME', 'Events'))

def convert_decimals(obj):
    """Convert Decimal objects to int or float for JSON serialization"""
    if isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        # Convert to int if it's a whole number, otherwise float
        if obj % 1 == 0:
            return int(obj)
        else:
            return float(obj)
    else:
        return obj

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

        # Check if user is admin (events_crud or system_crud)
        is_admin, _, _ = validate_permissions_with_regions(
            user_roles, ['events_crud'], user_email, None
        )
        if not is_admin:
            is_admin, _, _ = validate_permissions_with_regions(
                user_roles, ['system_crud'], user_email, None
            )

        # Get events from database
        response = table.scan()
        events = response['Items']

        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            events.extend(response['Items'])

        # Filter for non-admins: only published events, exclude webshop
        if not is_admin:
            events = [
                e for e in events
                if e.get('status') == 'published' and e.get('event_type') != 'webshop'
            ]
        
        # Convert Decimal objects to JSON-serializable types
        events = convert_decimals(events)
        
        return create_success_response(events)
        
    except Exception as e:
        print(f"Error in get_events handler: {str(e)}")
        return create_error_response(500, f'Internal server error: {str(e)}')