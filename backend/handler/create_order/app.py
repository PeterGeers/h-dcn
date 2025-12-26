import json
import boto3
import uuid
import base64
from datetime import datetime

def cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization"
    }

dynamodb = boto3.resource('dynamodb')
orders_table = dynamodb.Table('Orders')
members_table = dynamodb.Table('Members')
carts_table = dynamodb.Table('Carts')

def get_member_id_from_email(user_email):
    """
    Get member_id from user email by querying the Members table
    
    Args:
        user_email (str): User's email address
        
    Returns:
        tuple: (member_id, error_response)
               If successful: (member_id_string, None)
               If error: (None, error_response_dict)
    """
    try:
        # Scan Members table to find record with matching email
        # Note: In production, consider adding a GSI on email for better performance
        response = members_table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr('email').eq(user_email.lower())
        )
        
        if not response['Items']:
            return None, {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({
                    'error': 'Member record not found for authenticated user',
                    'user_email': user_email,
                    'message': 'Please contact administration to link your account to a member record'
                })
            }
        
        # Get the first matching member record
        member_record = response['Items'][0]
        member_id = member_record.get('member_id')
        
        if not member_id:
            return None, {
                'statusCode': 500,
                'headers': cors_headers(),
                'body': json.dumps({
                    'error': 'Member record found but missing member_id',
                    'user_email': user_email
                })
            }
        
        return member_id, None
        
    except Exception as e:
        print(f"Error looking up member_id for email {user_email}: {str(e)}")
        return None, {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Error looking up member information'})
        }

def validate_cart_ownership(cart_id, user_email):
    """
    Validate that the cart belongs to the authenticated user
    
    Args:
        cart_id (str): ID of the cart to validate
        user_email (str): Email of the authenticated user
        
    Returns:
        tuple: (is_valid, cart_data, error_response)
               If valid: (True, cart_dict, None)
               If invalid: (False, None, error_response_dict)
    """
    try:
        if not cart_id:
            return False, None, {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'cart_id is required for order creation'})
            }
        
        # Get cart from database
        response = carts_table.get_item(Key={'cart_id': cart_id})
        
        if 'Item' not in response:
            return False, None, {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({
                    'error': 'Cart not found',
                    'cart_id': cart_id
                })
            }
        
        cart = response['Item']
        cart_user_email = cart.get('user_email')
        
        # Validate cart ownership
        if not cart_user_email:
            # Log security issue - cart without owner
            print(f"SECURITY WARNING: Cart {cart_id} has no user_email - potential data integrity issue")
            return False, None, {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({
                    'error': 'Cart ownership cannot be verified',
                    'cart_id': cart_id
                })
            }
        
        if cart_user_email.lower() != user_email.lower():
            # Log unauthorized cart access attempt
            print(f"SECURITY ALERT: User {user_email} attempted to create order from cart {cart_id} owned by {cart_user_email}")
            return False, None, {
                'statusCode': 403,
                'headers': cors_headers(),
                'body': json.dumps({
                    'error': 'Access denied: You can only create orders from your own cart',
                    'cart_id': cart_id
                })
            }
        
        return True, cart, None
        
    except Exception as e:
        print(f"Error validating cart ownership for cart {cart_id}: {str(e)}")
        return False, None, {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Error validating cart ownership'})
        }

def log_order_creation_audit(order_id, user_email, user_roles, member_id, cart_id, order_data):
    """
    Log order creation for comprehensive audit trail
    
    Args:
        order_id (str): ID of the created order
        user_email (str): Email of the user creating the order
        user_roles (list): List of user's roles
        member_id (str): Member ID linked to the order
        cart_id (str): Cart ID used for the order
        order_data (dict): Order data that was stored
    """
    try:
        audit_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': 'ORDER_CREATION',
            'order_id': order_id,
            'user_email': user_email,
            'user_roles': user_roles,
            'member_id': member_id,
            'cart_id': cart_id,
            'order_total': order_data.get('total_amount', 'unknown'),
            'item_count': len(order_data.get('items', [])),
            'severity': 'INFO',
            'requires_review': False
        }
        
        # Log as structured JSON for monitoring systems
        print(f"ORDER_AUDIT: {json.dumps(audit_entry)}")
        
        # Human-readable log
        print(f"Order {order_id} created by user {user_email} (member_id: {member_id}) from cart {cart_id}")
        
        # Special logging for high-value orders (if total_amount is available)
        total_amount = order_data.get('total_amount')
        if total_amount and isinstance(total_amount, (int, float)) and total_amount > 500:
            print(f"HIGH VALUE ORDER: Order {order_id} has total amount {total_amount} - review recommended")
            
    except Exception as e:
        print(f"Error logging order creation audit: {str(e)}")
        # Don't fail the order creation if logging fails

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

def extract_user_roles_from_jwt(event):
    """
    Extract user roles from JWT token in Authorization header
    
    Args:
        event: Lambda event containing headers
        
    Returns:
        tuple: (user_email, user_roles, error_response)
               If successful: (email_string, roles_list, None)
               If error: (None, None, error_response_dict)
    """
    # Extract request metadata for security logging
    source_ip = event.get('requestContext', {}).get('identity', {}).get('sourceIp', 'unknown')
    user_agent = event.get('headers', {}).get('User-Agent', 'unknown')
    endpoint = event.get('path', 'unknown')
    method = event.get('httpMethod', 'unknown')
    
    user_info = {
        'source_ip': source_ip,
        'user_agent': user_agent,
        'endpoint': endpoint,
        'method': method
    }
    
    try:
        # Extract Authorization header
        auth_header = event.get('headers', {}).get('Authorization')
        if not auth_header:
            log_security_event('AUTH_FAILURE', {**user_info, 'email': 'unknown', 'roles': []}, {
                'failure_reason': 'missing_authorization_header',
                'attack_type': 'unauthenticated_access_attempt'
            })
            return None, None, {
                'statusCode': 401,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Authorization header required'})
            }
        
        # Validate Bearer token format
        if not auth_header.startswith('Bearer '):
            log_security_event('AUTH_FAILURE', {**user_info, 'email': 'unknown', 'roles': []}, {
                'failure_reason': 'invalid_bearer_format',
                'auth_header_prefix': auth_header[:20] if len(auth_header) > 20 else auth_header,
                'attack_type': 'malformed_token_attempt'
            })
            return None, None, {
                'statusCode': 401,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Invalid authorization header format'})
            }
        
        # Extract JWT token
        jwt_token = auth_header.replace('Bearer ', '')
        
        # Decode JWT token to get user info and roles
        parts = jwt_token.split('.')
        if len(parts) != 3:
            log_security_event('AUTH_FAILURE', {**user_info, 'email': 'unknown', 'roles': []}, {
                'failure_reason': 'invalid_jwt_structure',
                'token_parts_count': len(parts),
                'attack_type': 'malformed_jwt_attempt'
            })
            return None, None, {
                'statusCode': 401,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Invalid JWT token format'})
            }
        
        # Decode payload (second part of JWT)
        payload_encoded = parts[1]
        # Add padding if needed for base64 decoding
        payload_encoded += '=' * (4 - len(payload_encoded) % 4)
        payload_decoded = base64.urlsafe_b64decode(payload_encoded)
        payload = json.loads(payload_decoded)
        
        # Extract user email and roles
        user_email = payload.get('email') or payload.get('username')
        user_roles = payload.get('cognito:groups', [])
        
        if not user_email:
            log_security_event('AUTH_FAILURE', {**user_info, 'email': 'unknown', 'roles': user_roles}, {
                'failure_reason': 'missing_user_email_in_token',
                'token_payload_keys': list(payload.keys()),
                'attack_type': 'invalid_token_content'
            })
            return None, None, {
                'statusCode': 401,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'User email not found in token'})
            }
        
        return user_email, user_roles, None
        
    except json.JSONDecodeError as e:
        log_security_event('AUTH_FAILURE', {**user_info, 'email': 'unknown', 'roles': []}, {
            'failure_reason': 'jwt_decode_error',
            'decode_error': str(e),
            'attack_type': 'malformed_jwt_payload'
        })
        return None, None, {
            'statusCode': 401,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Invalid authorization token'})
        }
    except Exception as e:
        log_security_event('AUTH_FAILURE', {**user_info, 'email': 'unknown', 'roles': []}, {
            'failure_reason': 'jwt_processing_error',
            'error_message': str(e),
            'attack_type': 'token_processing_attack'
        })
        print(f"Error extracting user roles from JWT: {str(e)}")
        return None, None, {
            'statusCode': 401,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Invalid authorization token'})
        }

def lambda_handler(event, context):
    try:
        # Handle OPTIONS request for CORS
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': cors_headers(),
                'body': ''
            }
        
        # Extract user roles from JWT token
        user_email, user_roles, auth_error = extract_user_roles_from_jwt(event)
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
                'attempted_action': 'create_order',
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
        
        # Get member_id from user email
        member_id, member_error = get_member_id_from_email(user_email)
        if member_error:
            return member_error
        
        body = json.loads(event['body'])
        
        # Extract cart_id from request body
        cart_id = body.get('cart_id')
        
        # Validate cart ownership before order creation
        cart_valid, cart_data, cart_error = validate_cart_ownership(cart_id, user_email)
        if not cart_valid:
            return cart_error
        
        order_id = str(uuid.uuid4())
        order = {
            'order_id': order_id,
            'user_email': user_email,  # Link order to authenticated user
            'member_id': member_id,    # Link order to member record
            'cart_id': cart_id,        # Reference to the cart used
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            **body
        }
        
        orders_table.put_item(Item=order)
        
        # Log order creation for comprehensive audit trail
        log_order_creation_audit(order_id, user_email, user_roles, member_id, cart_id, order)
        
        return {
            'statusCode': 201,
            'headers': cors_headers(),
            'body': json.dumps({
                'order_id': order_id, 
                'member_id': member_id,
                'message': 'Order created successfully'
            })
        }
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    except Exception as e:
        print(f"Error creating order: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Internal server error'})
        }