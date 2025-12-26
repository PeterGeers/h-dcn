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
table = dynamodb.Table('Carts')

def log_cart_audit(event_type, cart_id, user_email, user_roles, additional_data=None):
    """
    Log cart operations for comprehensive audit trail
    
    Args:
        event_type (str): Type of cart event (CREATE, UPDATE, ACCESS, DELETE)
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
        if event_type in ['UPDATE', 'DELETE']:
            audit_entry['requires_review'] = True
            audit_entry['severity'] = 'WARN'
        
        # Log as structured JSON for monitoring systems
        print(f"CART_AUDIT: {json.dumps(audit_entry)}")
        
        # Human-readable log
        action_desc = {
            'CREATE': 'created',
            'UPDATE': 'updated', 
            'ACCESS': 'accessed',
            'DELETE': 'deleted'
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
                'attempted_action': 'create_cart',
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
        
        body = json.loads(event['body'])
        
        cart_id = str(uuid.uuid4())
        cart = {
            'cart_id': cart_id,
            'customer_id': body['customer_id'],
            'user_email': user_email,  # Link cart to authenticated user
            'items': [],
            'total_amount': 0,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        table.put_item(Item=cart)
        
        # Log cart creation for comprehensive audit trail
        log_cart_audit('CREATE', cart_id, user_email, user_roles, {
            'customer_id': body['customer_id'],
            'total_amount': cart.get('total_amount', 0),
            'item_count': len(cart.get('items', [])),
            'timestamp': cart['created_at']
        })
        
        return {
            'statusCode': 201,
            'headers': cors_headers(),
            'body': json.dumps({'cart_id': cart_id, 'message': 'Cart created successfully'})
        }
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    except Exception as e:
        print(f"Error creating cart: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Internal server error'})
        }