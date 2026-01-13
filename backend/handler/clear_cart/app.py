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
    lambda_handler = create_smart_fallback_handler("clear_cart")
    # Exit early - the fallback handler will handle all requests
    import sys
    sys.exit(0)

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Carts')

def log_cart_audit(event_type, cart_id, user_email, user_roles, additional_data=None):
    """
    Log cart operations for comprehensive audit trail
    
    Args:
        event_type (str): Type of cart event (CREATE, UPDATE, ACCESS, DELETE, DELETE_DENIED)
        cart_id (str): ID of the cart
        user_email (str): Email of the user performing the action
        user_roles (list): List of user's roles
        additional_data (dict): Additional data to include in audit log
    """
    try:
        audit_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': f'CART_{event_type}',
            'cart_id': cart_id,
            'user_email': user_email,
            'user_roles': user_roles,
            'severity': 'INFO',
            'requires_review': False
        }
        
        # Add additional data if provided
        if additional_data:
            audit_entry.update(additional_data)
        
        # Determine if this requires review
        if event_type in ['UPDATE', 'DELETE', 'DELETE_DENIED'] or additional_data.get('security_violation'):
            audit_entry['requires_review'] = True
            audit_entry['severity'] = additional_data.get('severity', 'WARN')
        
        # Log as structured JSON for monitoring systems
        print(f"CART_AUDIT: {json.dumps(audit_entry)}")
        
        # Human-readable log
        action_desc = {
            'CREATE': 'created',
            'UPDATE': 'updated', 
            'ACCESS': 'accessed',
            'DELETE': 'deleted',
            'DELETE_DENIED': 'delete denied'
        }.get(event_type, 'processed')
        
        print(f"Cart {cart_id} {action_desc} by user {user_email}")
            
    except Exception as e:
        print(f"Error logging cart audit: {str(e)}")
        # Don't fail the cart operation if logging fails

def log_security_event(event_type, user_info, additional_data=None):
    """
    Log security-related events for comprehensive monitoring
    
    Args:
        event_type (str): Type of security event (AUTH_FAILURE, ACCESS_DENIED, ROLE_VIOLATION, etc.)
        user_info (dict): User information (email, roles, IP, etc.)
        additional_data (dict): Additional security-relevant data
    """
    try:
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

def lambda_handler(event, context):
    try:
        # Handle OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()
        
        # Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error
        
        # UPDATED: Check for webshop access permission with new role structure
        # Users need hdcnLeden role for webshop access
        required_permissions = ['webshop_access']
        
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, required_permissions, user_email, None
        )
        if not is_authorized:
            return error_response
        
        # Log successful access
        log_successful_access(user_email, user_roles, 'clear_cart')
        
        cart_id = event['pathParameters']['cart_id']
        
        # First, get the cart to validate ownership
        cart_response = table.get_item(Key={'cart_id': cart_id})
        if 'Item' not in cart_response:
            return create_error_response(404, 'Cart not found')
        
        cart = cart_response['Item']
        
        # Validate cart ownership - users can only clear their own carts
        cart_user_email = cart.get('user_email')
        if cart_user_email and cart_user_email.lower() != user_email.lower():
            # Log unauthorized cart clear attempt for comprehensive audit trail
            log_cart_audit('DELETE_DENIED', cart_id, user_email, user_roles, {
                'cart_owner': cart_user_email,
                'security_violation': True,
                'severity': 'CRITICAL'
            })
            return create_error_response(403, 'Access denied: You can only clear your own cart')
        
        # Store cart data for audit before deletion
        cart_data_for_audit = {
            'customer_id': cart.get('customer_id'),
            'item_count': len(cart.get('items', [])),
            'total_amount': cart.get('total_amount', 0),
            'cart_age_days': (datetime.now() - datetime.fromisoformat(cart.get('created_at', datetime.now().isoformat()))).days if cart.get('created_at') else 0
        }
        
        table.delete_item(Key={'cart_id': cart_id})
        
        # Log cart clear for comprehensive audit trail
        log_cart_audit('DELETE', cart_id, user_email, user_roles, cart_data_for_audit)
        
        return create_success_response({'message': 'Cart cleared successfully'})
        
    except KeyError as e:
        return create_error_response(400, f'Missing required parameter: {str(e)}')
    except Exception as e:
        print(f"Error clearing cart: {str(e)}")
        return create_error_response(500, 'Internal server error')