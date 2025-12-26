import json
import boto3
import base64

def cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization"
    }

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Orders')

def log_order_audit(event_type, order_id, user_email, user_roles, additional_data=None):
    """
    Log order operations for comprehensive audit trail
    
    Args:
        event_type (str): Type of order event (CREATE, UPDATE, ACCESS, DELETE, ACCESS_DENIED)
        order_id (str): ID of the order
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
            'ACCESS_DENIED': 'access denied',
            'DELETE': 'deleted'
        }.get(event_type, 'processed')
        
        print(f"Order {order_id} {action_desc} by user {user_email}")
            
    except Exception as e:
        print(f"Error logging order audit: {str(e)}")
        # Don't fail the order operation if logging fails

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
    try:
        # Extract Authorization header
        auth_header = event.get('headers', {}).get('Authorization')
        if not auth_header:
            return None, None, {
                'statusCode': 401,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Authorization header required'})
            }
        
        # Validate Bearer token format
        if not auth_header.startswith('Bearer '):
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
            return None, None, {
                'statusCode': 401,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'User email not found in token'})
            }
        
        return user_email, user_roles, None
        
    except Exception as e:
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
            return {
                'statusCode': 403,
                'headers': cors_headers(),
                'body': json.dumps({
                    'error': 'Access denied: webshop access requires hdcnLeden role',
                    'required_role': 'hdcnLeden',
                    'user_roles': user_roles
                })
            }
        
        order_id = event['pathParameters']['order_id']
        
        response = table.get_item(Key={'order_id': order_id})
        
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Order not found'})
            }
        
        order = response['Item']
        
        # Validate order ownership - users can only access their own orders unless they have admin role
        order_user_email = order.get('user_email')
        has_admin_role = any(role in user_roles for role in ['Members_CRUD_All', 'Webshop_Management'])
        
        if not has_admin_role and order_user_email and order_user_email.lower() != user_email.lower():
            # Log unauthorized order access attempt for comprehensive audit trail
            log_order_audit('ACCESS_DENIED', order_id, user_email, user_roles, {
                'order_owner': order_user_email,
                'access_method': 'direct_id_lookup',
                'security_violation': True,
                'severity': 'CRITICAL'
            })
            return {
                'statusCode': 403,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Access denied: You can only access your own orders'})
            }
        
        # Log order access for comprehensive audit trail
        access_type = "admin" if has_admin_role else "owner"
        log_order_audit('ACCESS', order_id, user_email, user_roles, {
            'order_owner': order_user_email,
            'access_type': access_type,
            'access_method': 'direct_id_lookup',
            'order_total': order.get('total_amount', 0),
            'order_status': order.get('status', 'unknown'),
            'admin_roles': [role for role in user_roles if role in ['Members_CRUD_All', 'Webshop_Management']] if has_admin_role else []
        })
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps(order, default=str)
        }
    except KeyError as e:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': f'Missing required parameter: {str(e)}'})
        }
    except Exception as e:
        print(f"Error retrieving order: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Internal server error'})
        }