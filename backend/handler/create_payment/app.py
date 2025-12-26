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
payments_table = dynamodb.Table('Payments')
orders_table = dynamodb.Table('Orders')

def validate_payment_amount(payment_amount, order_data):
    """
    Validate payment amount against order total
    
    Args:
        payment_amount (float): Amount being paid
        order_data (dict): Order data containing total amount
        
    Returns:
        tuple: (is_valid, error_response)
               If valid: (True, None)
               If invalid: (False, error_response_dict)
    """
    try:
        if not order_data:
            # No order to validate against - allow payment (e.g., membership fees)
            return True, None
        
        order_total = order_data.get('total_amount')
        if order_total is None:
            # Order has no total amount - log warning but allow payment
            print(f"WARNING: Order {order_data.get('order_id')} has no total_amount field")
            return True, None
        
        # Convert to float for comparison
        try:
            payment_amount_float = float(payment_amount)
            order_total_float = float(order_total)
        except (ValueError, TypeError):
            return False, {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({
                    'error': 'Invalid payment amount or order total format',
                    'payment_amount': payment_amount,
                    'order_total': order_total
                })
            }
        
        # Allow some tolerance for rounding differences (1 cent)
        tolerance = 0.01
        amount_difference = abs(payment_amount_float - order_total_float)
        
        if amount_difference > tolerance:
            # Log potential fraud attempt
            print(f"SECURITY ALERT: Payment amount mismatch - Payment: {payment_amount_float}, Order: {order_total_float}, Difference: {amount_difference}")
            return False, {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({
                    'error': 'Payment amount does not match order total',
                    'payment_amount': payment_amount_float,
                    'order_total': order_total_float,
                    'difference': amount_difference,
                    'order_id': order_data.get('order_id')
                })
            }
        
        return True, None
        
    except Exception as e:
        print(f"Error validating payment amount: {str(e)}")
        return False, {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Error validating payment amount'})
        }

def log_payment_audit(event_type, payment_id, user_email, user_roles, additional_data=None):
    """
    Log payment operations for comprehensive audit trail
    
    Args:
        event_type (str): Type of payment event (CREATE, UPDATE, ACCESS, DELETE)
        payment_id (str): ID of the payment
        user_email (str): Email of the user performing the action
        user_roles (list): List of user's roles
        additional_data (dict): Additional data to include in audit log
    """
    try:
        audit_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': f'PAYMENT_{event_type}',
            'payment_id': payment_id,
            'user_email': user_email,
            'user_roles': user_roles,
            'severity': 'INFO',
            'requires_review': False
        }
        
        # Add additional data if provided
        if additional_data:
            audit_entry.update(additional_data)
        
        # Determine if this requires review
        if event_type in ['UPDATE', 'DELETE'] or (additional_data and additional_data.get('payment_amount', 0) > 1000):
            audit_entry['requires_review'] = True
            audit_entry['severity'] = 'WARN'
        
        # Log as structured JSON for monitoring systems
        print(f"PAYMENT_AUDIT: {json.dumps(audit_entry)}")
        
        # Human-readable log
        action_desc = {
            'CREATE': 'created',
            'UPDATE': 'updated', 
            'ACCESS': 'accessed',
            'DELETE': 'deleted'
        }.get(event_type, 'processed')
        
        print(f"Payment {payment_id} {action_desc} by user {user_email}")
        
        # Special logging for high-value payments
        payment_amount = additional_data.get('payment_amount') if additional_data else None
        if payment_amount and isinstance(payment_amount, (int, float)) and payment_amount > 1000:
            print(f"HIGH VALUE PAYMENT: Payment {payment_id} has amount {payment_amount} - review recommended")
            
    except Exception as e:
        print(f"Error logging payment audit: {str(e)}")
        # Don't fail the payment operation if logging fails

def validate_order_ownership(order_id, user_email):
    """
    Validate that the order belongs to the authenticated user
    
    Args:
        order_id (str): ID of the order to validate
        user_email (str): Email of the authenticated user
        
    Returns:
        tuple: (is_valid, order_data, error_response)
               If valid: (True, order_dict, None)
               If invalid: (False, None, error_response_dict)
    """
    try:
        if not order_id:
            return True, None, None  # Payment without order is allowed (e.g., membership fees)
        
        # Get order from database
        response = orders_table.get_item(Key={'order_id': order_id})
        
        if 'Item' not in response:
            return False, None, {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({
                    'error': 'Order not found',
                    'order_id': order_id
                })
            }
        
        order = response['Item']
        order_user_email = order.get('user_email')
        
        # Validate order ownership
        if not order_user_email:
            # Log security issue - order without owner
            print(f"SECURITY WARNING: Order {order_id} has no user_email - potential data integrity issue")
            return False, None, {
                'statusCode': 400,
                'headers': cors_headers(),
                'body': json.dumps({
                    'error': 'Order ownership cannot be verified',
                    'order_id': order_id
                })
            }
        
        if order_user_email.lower() != user_email.lower():
            # Log unauthorized order access attempt
            print(f"SECURITY ALERT: User {user_email} attempted to create payment for order {order_id} owned by {order_user_email}")
            return False, None, {
                'statusCode': 403,
                'headers': cors_headers(),
                'body': json.dumps({
                    'error': 'Access denied: You can only create payments for your own orders',
                    'order_id': order_id
                })
            }
        
        return True, order, None
        
    except Exception as e:
        print(f"Error validating order ownership for order {order_id}: {str(e)}")
        return False, None, {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Error validating order ownership'})
        }

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
                'attempted_action': 'create_payment',
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
        
        # Extract order_id from request body for validation
        order_id = body.get('order_id')
        payment_amount = body.get('amount')
        
        # Validate order ownership if order_id is provided
        order_valid, order_data, order_error = validate_order_ownership(order_id, user_email)
        if not order_valid:
            return order_error
        
        # Validate payment amount against order total
        amount_valid, amount_error = validate_payment_amount(payment_amount, order_data)
        if not amount_valid:
            return amount_error
        
        payment_id = str(uuid.uuid4())
        payment = {
            'payment_id': payment_id, 
            'payment_date': datetime.now().isoformat(),
            'user_email': user_email,  # Link payment to authenticated user
            'created_by': user_email,  # Track who created the payment
            **body
        }
        
        # Add order information if order was validated
        if order_data:
            payment['verified_order_id'] = order_id
            payment['order_user_email'] = order_data.get('user_email')
            payment['order_member_id'] = order_data.get('member_id')
        
        payments_table.put_item(Item=payment)
        
        # Log payment creation for comprehensive audit trail
        log_payment_audit('CREATE', payment_id, user_email, user_roles, {
            'order_id': order_id,
            'payment_amount': payment_amount,
            'order_total': order_data.get('total_amount') if order_data else None,
            'amount_validated': order_data is not None,
            'verified_order': order_data is not None,
            'payment_method': body.get('payment_method', 'unknown'),
            'order_member_id': order_data.get('member_id') if order_data else None
        })
        
        return {
            'statusCode': 201,
            'headers': cors_headers(),
            'body': json.dumps({'payment_id': payment_id, 'message': 'Payment created successfully'})
        }
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    except Exception as e:
        print(f"Error creating payment: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Internal server error'})
        }