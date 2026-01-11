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
table = dynamodb.Table('Orders')

def log_customer_order_audit(event_type, customer_id, user_email, user_roles, additional_data=None):
    """
    Log customer order operations for comprehensive audit trail
    
    Args:
        event_type (str): Type of customer order event (ACCESS, ACCESS_DENIED)
        customer_id (str): ID of the customer whose orders are being accessed
        user_email (str): Email of the user performing the action
        user_roles (list): List of user's roles
        additional_data (dict): Additional data to include in audit log
    """
    try:
        from datetime import datetime
        
        audit_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': f'CUSTOMER_ORDER_{event_type}',
            'customer_id': customer_id,
            'user_email': user_email,
            'user_roles': user_roles,
            'severity': 'INFO',
            'requires_review': False
        }
        
        # Add additional data if provided
        if additional_data:
            audit_entry.update(additional_data)
        
        # Determine if this requires review
        if event_type in ['ACCESS_DENIED'] or additional_data.get('security_violation'):
            audit_entry['requires_review'] = True
            audit_entry['severity'] = additional_data.get('severity', 'WARN')
        
        # Log as structured JSON for monitoring systems
        print(f"CUSTOMER_ORDER_AUDIT: {json.dumps(audit_entry)}")
        
        # Human-readable log
        action_desc = {
            'ACCESS': 'accessed',
            'ACCESS_DENIED': 'access denied'
        }.get(event_type, 'processed')
        
        print(f"Customer {customer_id} orders {action_desc} by user {user_email}")
            
    except Exception as e:
        print(f"Error logging customer order audit: {str(e)}")
        # Don't fail the operation if logging fails

# REMOVED: Custom JWT parsing function - now using shared auth system
# This function has been replaced by extract_user_credentials from shared.auth_utils


def lambda_handler(event, context):
    try:
        # Handle OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()
        
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
        
        customer_id = event['pathParameters']['customer_id']
        
        # Check if user has administrative role to view any customer's orders
        has_admin_role = any(role in user_roles for role in ['Members_CRUD', 'System_CRUD', 'Webshop_Management'])
        
        if not has_admin_role:
            # Regular users can only access orders if they match the customer_id
            # We need to validate that the customer_id corresponds to the authenticated user
            # This requires looking up the user's member_id from their email
            members_table = dynamodb.Table('Members')
            try:
                member_response = members_table.scan(
                    FilterExpression=boto3.dynamodb.conditions.Attr('email').eq(user_email.lower())
                )
                
                if not member_response['Items']:
                    return {
                        'statusCode': 403,
                        'headers': cors_headers(),
                        'body': json.dumps({
                            'error': 'Access denied: Member record not found for authenticated user',
                            'user_email': user_email
                        })
                    }
                
                user_member_id = member_response['Items'][0].get('member_id')
                
                # Check if the requested customer_id matches the user's member_id
                if customer_id != user_member_id:
                    log_customer_order_audit('ACCESS_DENIED', customer_id, user_email, user_roles, {
                        'requested_customer_id': customer_id,
                        'user_member_id': user_member_id,
                        'security_violation': True,
                        'severity': 'CRITICAL'
                    })
                    return {
                        'statusCode': 403,
                        'headers': cors_headers(),
                        'body': json.dumps({'error': 'Access denied: You can only access your own orders'})
                    }
                    
            except Exception as e:
                print(f"Error validating customer access for user {user_email}: {str(e)}")
                return {
                    'statusCode': 500,
                    'headers': cors_headers(),
                    'body': json.dumps({'error': 'Error validating customer access'})
                }
        
        response = table.query(
            IndexName='CustomerOrdersIndex',
            KeyConditionExpression=boto3.dynamodb.conditions.Key('customer_id').eq(customer_id)
        )
        
        orders = response['Items']
        
        # Log customer orders access for comprehensive audit trail
        access_type = "admin" if has_admin_role else "owner"
        log_customer_order_audit('ACCESS', customer_id, user_email, user_roles, {
            'access_type': access_type,
            'order_count': len(orders),
            'total_order_value': sum(float(order.get('total_amount', 0)) for order in orders if order.get('total_amount')),
            'admin_roles': [role for role in user_roles if role in ['Members_CRUD', 'System_CRUD', 'Webshop_Management']] if has_admin_role else []
        })
        
        return create_success_response(orders)
    except KeyError as e:
        return create_error_response(400, f\'Missing required parameter: {str(e)}\')
    except Exception as e:
        print(f"Error retrieving customer orders: {str(e)}")
        return create_error_response(500, \'Internal server error\')