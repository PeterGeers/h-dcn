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
table = dynamodb.Table('Payments')

# REMOVED: Custom JWT parsing function - now using shared auth system
# This function has been replaced by extract_user_credentials from shared.auth_utils


def lambda_handler(event, context):
    # Handle OPTIONS request for CORS
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': ''
        }
    
    try:
        # Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error
        
        # Validate user has webshop access permission (hdcnLeden role)
        if 'hdcnLeden' not in user_roles:
            return {
                'statusCode': 403,
                'headers': cors_headers(),
                'body': json.dumps({
                    'error': 'Access denied: webshop access requires hdcnLeden role',
                    'required_role': 'hdcnLeden',
                    'user_roles': user_roles
                })
            }
        
        payment_id = event['pathParameters']['payment_id']
        
        # Get existing payment to validate ownership
        existing_payment_response = table.get_item(Key={'payment_id': payment_id})
        
        if 'Item' not in existing_payment_response:
            return create_error_response(404, \'Payment not found\')
        
        existing_payment = existing_payment_response['Item']
        
        # Validate payment ownership (only payment owner or admin can delete)
        payment_owner_email = existing_payment.get('user_email')
        # UPDATED: Use new role structure - Members_CRUD or System_CRUD can delete any payment
        is_admin = any(role in user_roles for role in ['Members_CRUD', 'System_CRUD', 'System_User_Management'])
        
        if not is_admin and (not payment_owner_email or payment_owner_email.lower() != user_email.lower()):
            print(f"SECURITY ALERT: User {user_email} attempted to delete payment {payment_id} owned by {payment_owner_email}")
            return {
                'statusCode': 403,
                'headers': cors_headers(),
                'body': json.dumps({
                    'error': 'Access denied: You can only delete your own payments',
                    'payment_id': payment_id
                })
            }
        
        table.delete_item(Key={'payment_id': payment_id})
        
        # Log payment deletion for audit purposes
        print(f"Payment {payment_id} deleted by user {user_email} with roles {user_roles}")
        
        return create_success_response({'message': 'Payment deleted successfully'})
    except KeyError as e:
        return create_error_response(400, f\'Missing required parameter: {str(e)}\')
    except Exception as e:
        print(f"Error deleting payment: {str(e)}")
        return create_error_response(500, \'Internal server error\')