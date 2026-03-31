import json
import boto3
from decimal import Decimal

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
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("get_event_byid")
    import sys
    sys.exit(0)

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Events')

def convert_decimals(obj):
    if isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    return obj

def lambda_handler(event, context):
    try:
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        required_permissions = ['events_read']
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, required_permissions, user_email, None
        )
        if not is_authorized:
            return error_response

        log_successful_access(user_email, user_roles, 'get_event_byid')

        event_id = event['pathParameters']['event_id']
        response = table.get_item(Key={'event_id': event_id})

        if 'Item' not in response:
            return create_error_response(404, 'Event not found')

        return create_success_response(convert_decimals(response['Item']))

    except KeyError as e:
        return create_error_response(400, f'Missing required parameter: {str(e)}')
    except Exception as e:
        print(f"Error in get_event_byid: {str(e)}")
        return create_error_response(500, 'Internal server error')
