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
    print("Using shared auth layer")
except ImportError as e:
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("delete_membership")
    import sys
    sys.exit(0)

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Memberships')

def lambda_handler(event, context):
    try:
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()

        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error

        required_permissions = ['memberships_delete']
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, required_permissions, user_email, None
        )
        if not is_authorized:
            return error_response

        log_successful_access(user_email, user_roles, 'delete_membership')

        membership_id = event['pathParameters']['id']
        table.delete_item(Key={'membership_type_id': membership_id})

        print(f"Membership {membership_id} deleted by {user_email}")

        return create_success_response({'message': 'Membership deleted successfully'})

    except KeyError as e:
        return create_error_response(400, f'Missing required parameter: {str(e)}')
    except Exception as e:
        print(f"Error in delete_membership: {str(e)}")
        return create_error_response(500, 'Internal server error')
