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
table = dynamodb.Table('Carts')

def log_cart_audit(event_type, cart_id, user_email, user_roles, additional_data=None):
    """
    Log cart operations for comprehensive audit trail
    
    Args:
        event_type (str): Type of cart event (CREATE, UPDATE, ACCESS, DELETE, UPDATE_DENIED)
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
        if event_type in ['UPDATE', 'DELETE', 'UPDATE_DENIED'] or additional_data.get('security_violation'):
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
            'UPDATE_DENIED': 'update denied'
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
        
        # UPDATED: Check for webshop access permission with new role structure
        # Users need hdcnLeden role for webshop access
        required_permissions = ['webshop_access']
        
        is_authorized, error_response, regional_info = validate_permissions_with_regions(
            user_roles, required_permissions, user_email, None
        )
        if not is_authorized:
            return error_response
        
        # Log successful access
        log_successful_access(user_email, user_roles, 'update_cart_items')
        
        cart_id = event['pathParameters']['cart_id']
        body = json.loads(event['body'])
        
        # First, get the cart to validate ownership
        cart_response = table.get_item(Key={'cart_id': cart_id})
        if 'Item' not in cart_response:
            return create_error_response(404, 'Cart not found')
        
        cart = cart_response['Item']
        
        # Validate cart ownership - users can only update their own carts
        cart_user_email = cart.get('user_email')
        if cart_user_email and cart_user_email.lower() != user_email.lower():
            # Log unauthorized cart update attempt for comprehensive audit trail
            log_cart_audit('UPDATE_DENIED', cart_id, user_email, user_roles, {
                'cart_owner': cart_user_email,
                'attempted_changes': list(body.keys()),
                'security_violation': True,
                'severity': 'CRITICAL'
            })
            return create_error_response(403, 'Access denied: You can only update your own cart')
        
        update_expression = "SET updated_at = :updated_at"
        expression_values = {':updated_at': datetime.now().isoformat()}
        expression_names = {}
        
        for key, value in body.items():
            if key != 'cart_id':
                attr_name = f"#{key}"
                update_expression += f", {attr_name} = :{key}"
                expression_values[f":{key}"] = value
                expression_names[attr_name] = key
        
        update_params = {
            'Key': {'cart_id': cart_id},
            'UpdateExpression': update_expression,
            'ExpressionAttributeValues': expression_values
        }
        
        if expression_names:
            update_params['ExpressionAttributeNames'] = expression_names
        
        table.update_item(**update_params)
        
        # Log cart update for comprehensive audit trail
        log_cart_audit('UPDATE', cart_id, user_email, user_roles, {
            'updated_fields': list(body.keys()),
            'previous_total': cart.get('total_amount', 0),
            'new_total': body.get('total_amount', cart.get('total_amount', 0)),
            'item_count': len(body.get('items', cart.get('items', []))),
            'customer_id': cart.get('customer_id')
        })
        
        return create_success_response({'message': 'Cart updated successfully'})
        
    except KeyError as e:
        return create_error_response(400, f'Missing required parameter: {str(e)}')
    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        print(f"Error updating cart: {str(e)}")
        return create_error_response(500, 'Internal server error')