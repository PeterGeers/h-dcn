import json
import boto3
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
    print("✅ Using shared auth layer")
except ImportError as e:
    # Built-in smart fallback - no local auth_fallback.py needed
    print(f"❌ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("update_membership")
    # Exit early - the fallback handler will handle all requests
    import sys
    sys.exit(0)

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Memberships')

def lambda_handler(event, context):
    try:
        # Handle OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()
        
        # Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error
        
        # Validate permissions - only admins can update membership types
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, ['members_update'], user_email, {'operation': 'update_membership'}
        )
        if not is_authorized:
            return error_response
        
        # Log successful access
        log_successful_access(user_email, user_roles, 'update_membership')
        
        # Get membership_id from path parameters
        if not event.get('pathParameters') or not event['pathParameters'].get('id'):
            return create_error_response(400, 'Membership ID is required in path parameters')
        
        membership_id = event['pathParameters']['id']
        
        # Parse request body
        if not event.get('body'):
            return create_error_response(400, 'Request body is required')
        
        data = json.loads(event['body'])
        
        # Check if membership exists
        response = table.get_item(Key={'membership_type_id': membership_id})
        if 'Item' not in response:
            return create_error_response(404, 'Membership type not found')
        
        # Build update expression
        update_expression = "SET #updated_at = :updated_at"
        expression_values = {':updated_at': datetime.utcnow().isoformat()}
        expression_names = {'#updated_at': 'updated_at'}
        
        for key, value in data.items():
            if key not in ['membership_type_id', 'updated_at']:  # Exclude protected fields
                update_expression += f", #{key} = :{key}"
                expression_values[f":{key}"] = value
                expression_names[f"#{key}"] = key
        
        # Update the membership type
        table.update_item(
            Key={'membership_type_id': membership_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values,
            ExpressionAttributeNames=expression_names
        )
        
        return create_success_response({'message': 'Membership updated successfully', 'membership_id': membership_id})
        
    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        return create_error_response(500, f'Internal server error: {str(e)}')