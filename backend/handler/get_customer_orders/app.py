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
        
        customer_id = event['pathParameters']['customer_id']
        
        # Check if user has administrative role to view any customer's orders
        has_admin_role = any(role in user_roles for role in ['Members_CRUD_All', 'Webshop_Management'])
        
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
            'admin_roles': [role for role in user_roles if role in ['Members_CRUD_All', 'Webshop_Management']] if has_admin_role else []
        })
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps(orders, default=str)
        }
    except KeyError as e:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': f'Missing required parameter: {str(e)}'})
        }
    except Exception as e:
        print(f"Error retrieving customer orders: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Internal server error'})
        }