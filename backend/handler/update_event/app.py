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
        
        # UPDATED: Check for events update permission with new role structure
        # Users now have Events_CRUD + Regio_* instead of Events_CRUD_All
        # The validate_permissions_with_regions function will:
        # 1. Check if user has Events_CRUD role (which grants events_update permission)
        # 2. Check if user has a region role (Regio_All, Regio_*, etc.)
        # 3. Ensure both permission + region requirements are met
        required_permissions = ['events_update']
        
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, required_permissions, user_email, None
        )
        if not is_authorized:
            return error_response
        
        # Log successful access
        log_successful_access(user_email, user_roles, 'update_event')
        
        event_id = event['pathParameters']['event_id']
        body = json.loads(event['body'])
        
        update_expression = "SET updated_at = :updated_at"
        expression_values = {':updated_at': datetime.now().isoformat()}
        expression_names = {}
        
        for key, value in body.items():
            if key != 'event_id':
                attr_name = f"#{key}"
                update_expression += f", {attr_name} = :{key}"
                expression_values[f":{key}"] = value
                expression_names[attr_name] = key
        
        update_params = {
            'Key': {'event_id': event_id},
            'UpdateExpression': update_expression,
            'ExpressionAttributeValues': expression_values
        }
        
        if expression_names:
            update_params['ExpressionAttributeNames'] = expression_names
        
        table.update_item(**update_params)
        
        print(f"Event {event_id} updated by {user_email} with roles {user_roles}")
        
        return create_success_response({
            'message': 'Event updated successfully',
            'updated_fields': list(body.keys())
        })
        
    except KeyError as e:
        return create_error_response(400, f'Missing required parameter: {str(e)}')
    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        print(f"Unexpected error in update_event: {str(e)}")
        return create_error_response(500, 'Internal server error')