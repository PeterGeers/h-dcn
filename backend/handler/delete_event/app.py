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
except ImportError as e:
    # Built-in smart fallback - no local auth_fallback.py needed
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("delete_event")
    # Exit early - the fallback handler will handle all requests
    import sys
    sys.exit(0)

dynamodb = boto3.resource('dynamodb')
lambda_client = boto3.client('lambda')
table_name = os.environ.get('EVENTS_TABLE_NAME', 'Events')
table = dynamodb.Table(table_name)
SYNC_FUNCTION_NAME = os.environ.get('SYNC_GOOGLE_CALENDAR_FUNCTION', '')

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
        
        # Fetch event first to get google_calendar_event_id for sync
        current_event = {}
        if SYNC_FUNCTION_NAME:
            try:
                resp = table.get_item(Key={'event_id': event_id})
                current_event = resp.get('Item', {})
            except Exception as e:
                print(f"Warning: could not fetch event for sync: {e}")

        # Delete the event
        table.delete_item(Key={'event_id': event_id})
        
        print(f"Event {event_id} deleted by {user_email} with roles {user_roles}")

        # Trigger Google Calendar delete (async, best-effort)
        gcal_id = current_event.get('google_calendar_event_id')
        if SYNC_FUNCTION_NAME and gcal_id:
            try:
                sync_payload = {
                    'body': json.dumps({
                        'event_id': event_id,
                        'action': 'delete',
                        'event_data': {
                            'name': current_event.get('name', ''),
                            'start_date': current_event.get('start_date', ''),
                            'end_date': current_event.get('end_date', ''),
                            'event_type': current_event.get('event_type', ''),
                            'google_calendar_event_id': gcal_id,
                        },
                    })
                }
                lambda_client.invoke(
                    FunctionName=SYNC_FUNCTION_NAME,
                    InvocationType='Event',
                    Payload=json.dumps(sync_payload),
                )
                print(f"Triggered Google Calendar delete for event {event_id}")
            except Exception as sync_err:
                print(f"Warning: Google Calendar delete trigger failed: {sync_err}")
        
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