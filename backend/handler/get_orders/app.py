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

def log_order_audit(event_type, order_id, user_email, user_roles, additional_data=None):
    """
    Log order operations for comprehensive audit trail
    
    Args:
        event_type (str): Type of order event (CREATE, UPDATE, ACCESS, DELETE, ACCESS_ALL, ACCESS_OWN, ACCESS_DENIED)
        order_id (str): ID of the order (or special identifier like 'ALL_ORDERS')
        user_email (str): Email of the user performing the action
        user_roles (list): List of user's roles
        additional_data (dict): Additional data to include in audit log
    """
    try:
        from datetime import datetime
        
        audit_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': f'ORDER_{event_type}',
            'order_id': order_id,
            'user_email': user_email,
            'user_roles': user_roles,
            'severity': 'INFO',
            'requires_review': False
        }
        
        # Add additional data if provided
        if additional_data:
            audit_entry.update(additional_data)
        
        # Determine if this requires review
        if event_type in ['UPDATE', 'DELETE', 'ACCESS_DENIED'] or additional_data.get('security_violation'):
            audit_entry['requires_review'] = True
            audit_entry['severity'] = additional_data.get('severity', 'WARN')
        
        # Log as structured JSON for monitoring systems
        print(f"ORDER_AUDIT: {json.dumps(audit_entry)}")
        
        # Human-readable log
        action_desc = {
            'CREATE': 'created',
            'UPDATE': 'updated', 
            'ACCESS': 'accessed',
            'ACCESS_ALL': 'all orders accessed',
            'ACCESS_OWN': 'own orders accessed',
            'ACCESS_DENIED': 'access denied',
            'DELETE': 'deleted'
        }.get(event_type, 'processed')
        
        print(f"Order {order_id} {action_desc} by user {user_email}")
            
    except Exception as e:
        print(f"Error logging order audit: {str(e)}")
        # Don't fail the order operation if logging fails

def log_security_event(event_type, user_info, additional_data=None):
    """
    Log security-related events for comprehensive monitoring
    
    Args:
        event_type (str): Type of security event (AUTH_FAILURE, ACCESS_DENIED, ROLE_VIOLATION, etc.)
        user_info (dict): User information (email, roles, IP, etc.)
        additional_data (dict): Additional security-relevant data
    """
    try:
        from datetime import datetime
        
        security_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': f'SECURITY_{event_type}',
            'severity': 'CRITICAL',
            'requires_review': True,
            'user_email': user_info.get('email', 'unknown'),
            'user_roles': user_info.get('roles', []),
            'source_ip': user_info.get('source_ip', 'unknown'),
            'user_agent': user_info.get('user_agent', 'unknown'),
            'endpoint': user_info.get('endpoint', 'unknown'),
            'method': user_info.get('method', 'unknown')
        }
        
        # Add additional data if provided
        if additional_data:
            security_entry.update(additional_data)
        
        # Log as structured JSON for security monitoring systems
        print(f"SECURITY_ALERT: {json.dumps(security_entry)}")
        
        # Human-readable security log
        print(f"SECURITY EVENT: {event_type} - User: {user_info.get('email', 'unknown')} - IP: {user_info.get('source_ip', 'unknown')}")
        
    except Exception as e:
        print(f"Error logging security event: {str(e)}")
        # Don't fail the operation if security logging fails

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
            # Log role-based access denial for security monitoring
            log_security_event('ROLE_VIOLATION', {
                'email': user_email,
                'roles': user_roles,
                'source_ip': event.get('requestContext', {}).get('identity', {}).get('sourceIp', 'unknown'),
                'user_agent': event.get('headers', {}).get('User-Agent', 'unknown'),
                'endpoint': event.get('path', 'unknown'),
                'method': event.get('httpMethod', 'unknown')
            }, {
                'required_role': 'hdcnLeden',
                'attempted_action': 'get_orders',
                'access_denied_reason': 'insufficient_role_permissions',
                'attack_type': 'privilege_escalation_attempt'
            })
            return {
                'statusCode': 403,
                'headers': cors_headers(),
                'body': json.dumps({
                    'error': 'Access denied: webshop access requires hdcnLeden role',
                    'required_role': 'hdcnLeden',
                    'user_roles': user_roles
                })
            }
        
        # Check if user has administrative role to view all orders
        has_admin_role = any(role in user_roles for role in ['Members_CRUD_All', 'Webshop_Management'])
        
        if has_admin_role:
            # Admin users can see all orders
            response = table.scan()
            orders = response['Items']
            log_order_audit('ACCESS_ALL', 'ALL_ORDERS', user_email, user_roles, {
                'access_type': 'admin',
                'order_count': len(orders),
                'admin_roles': [role for role in user_roles if role in ['Members_CRUD_All', 'Webshop_Management']]
            })
        else:
            # Regular users can only see their own orders
            response = table.scan(
                FilterExpression=boto3.dynamodb.conditions.Attr('user_email').eq(user_email)
            )
            orders = response['Items']
            log_order_audit('ACCESS_OWN', 'USER_ORDERS', user_email, user_roles, {
                'access_type': 'owner',
                'order_count': len(orders),
                'user_order_total': sum(float(order.get('total_amount', 0)) for order in orders if order.get('total_amount'))
            })
        
        return create_success_response(orders)
    except Exception as e:
        print(f"Error retrieving orders: {str(e)}")
        return create_error_response(500, \'Internal server error\')