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
except ImportError as e:
    # Built-in smart fallback - no local auth_fallback.py needed
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("get_member_payments")
    # Exit early - the fallback handler will handle all requests
    import sys
    sys.exit(0)

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Payments')

def log_member_payment_audit(event_type, member_id, user_email, user_roles, additional_data=None):
    """
    Log member payment operations for comprehensive audit trail
    
    Args:
        event_type (str): Type of member payment event (ACCESS)
        member_id (str): ID of the member whose payments are being accessed
        user_email (str): Email of the user performing the action
        user_roles (list): List of user's roles
        additional_data (dict): Additional data to include in audit log
    """
    try:
        from datetime import datetime
        
        audit_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': f'MEMBER_PAYMENT_{event_type}',
            'member_id': member_id,
            'user_email': user_email,
            'user_roles': user_roles,
            'severity': 'INFO',
            'requires_review': False
        }
        
        # Add additional data if provided
        if additional_data:
            audit_entry.update(additional_data)
        
        # Log as structured JSON for monitoring systems
        print(f"MEMBER_PAYMENT_AUDIT: {json.dumps(audit_entry)}")
        
        # Human-readable log
        action_desc = {
            'ACCESS': 'accessed'
        }.get(event_type, 'processed')
        
        print(f"Member {member_id} payments {action_desc} by user {user_email}")
            
    except Exception as e:
        print(f"Error logging member payment audit: {str(e)}")
        # Don't fail the operation if logging fails

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
        
        member_id = event['pathParameters']['member_id']
        
        response = table.query(
            IndexName='MemberPaymentsIndex',
            KeyConditionExpression=boto3.dynamodb.conditions.Key('member_id').eq(member_id)
        )
        
        payments = response['Items']
        
        # Log member payment access for comprehensive audit trail
        log_member_payment_audit('ACCESS', member_id, user_email, user_roles, {
            'payment_count': len(payments),
            'total_payment_value': sum(float(payment.get('amount', 0)) for payment in payments if payment.get('amount')),
            'access_method': 'member_id_query'
        })
        
        return create_success_response(payments)
    except KeyError as e:
        return create_error_response(400, f'Missing required parameter: {str(e)}')
    except Exception as e:
        print(f"Error retrieving member payments: {str(e)}")
        return create_error_response(500, 'Internal server error')