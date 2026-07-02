import json
import os
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
table = dynamodb.Table(os.environ.get('EVENTS_TABLE_NAME', 'Events'))

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

        # Access: admin (events_read) OR any authenticated member (hdcnLeden/event_participant)
        is_admin, _, _ = validate_permissions_with_regions(
            user_roles, ['events_read'], user_email, None
        )
        has_member_access = 'hdcnLeden' in user_roles
        has_event_access = any(r in user_roles for r in ('Regio_Pressmeet', 'Regio_All', 'event_participant'))

        if not is_admin and not has_member_access and not has_event_access:
            return create_error_response(403, 'Access denied')

        log_successful_access(user_email, user_roles, 'get_event_byid')

        event_id = event['pathParameters']['event_id']
        response = table.get_item(Key={'event_id': event_id})

        if 'Item' not in response:
            return create_error_response(404, 'Event not found')

        event_record = response['Item']

        # Non-admins can only see published events
        if not is_admin and event_record.get('status') != 'published':
            return create_error_response(404, 'Event not found')

        return create_success_response(convert_decimals(event_record))

    except KeyError as e:
        return create_error_response(400, f'Missing required parameter: {str(e)}')
    except Exception as e:
        print(f"Error in get_event_byid: {str(e)}")
        return create_error_response(500, 'Internal server error')
