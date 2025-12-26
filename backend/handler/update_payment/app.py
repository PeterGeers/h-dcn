import json
import boto3
import base64
from datetime import datetime

def cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "PUT, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization"
    }

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Payments')

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
    # Handle OPTIONS request for CORS
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': ''
        }
    
    try:
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
        
        payment_id = event['pathParameters']['payment_id']
        data = json.loads(event['body'])
        
        # Get existing payment to validate ownership
        existing_payment_response = table.get_item(Key={'payment_id': payment_id})
        
        if 'Item' not in existing_payment_response:
            return {
                'statusCode': 404,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Payment not found'})
            }
        
        existing_payment = existing_payment_response['Item']
        
        # Validate payment ownership (only payment owner or admin can update)
        payment_owner_email = existing_payment.get('user_email')
        is_admin = any(role in user_roles for role in ['Members_CRUD_All', 'Webmaster'])
        
        if not is_admin and (not payment_owner_email or payment_owner_email.lower() != user_email.lower()):
            print(f"SECURITY ALERT: User {user_email} attempted to update payment {payment_id} owned by {payment_owner_email}")
            return {
                'statusCode': 403,
                'headers': cors_headers(),
                'body': json.dumps({
                    'error': 'Access denied: You can only update your own payments',
                    'payment_id': payment_id
                })
            }
        
        update_expression = "SET #updated_at = :updated_at, #updated_by = :updated_by"
        expression_values = {
            ':updated_at': datetime.utcnow().isoformat(),
            ':updated_by': user_email
        }
        expression_names = {
            '#updated_at': 'updated_at',
            '#updated_by': 'updated_by'
        }
        
        for key, value in data.items():
            # Prevent updating sensitive fields
            if key in ['payment_id', 'user_email', 'created_at']:
                continue
            update_expression += f", #{key} = :{key}"
            expression_values[f":{key}"] = value
            expression_names[f"#{key}"] = key
        
        table.update_item(
            Key={'payment_id': payment_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values,
            ExpressionAttributeNames=expression_names
        )
        
        # Log payment update for comprehensive audit trail
        log_payment_audit('UPDATE', payment_id, user_email, user_roles, {
            'updated_fields': list(data.keys()),
            'is_admin_update': is_admin,
            'original_owner': payment_owner_email,
            'payment_amount': existing_payment.get('amount', 0)
        })
        
        return {
            'statusCode': 200,
            'headers': cors_headers(),
            'body': json.dumps({'message': 'Payment updated successfully'})
        }
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Invalid JSON in request body'})
        }
    except KeyError as e:
        return {
            'statusCode': 400,
            'headers': cors_headers(),
            'body': json.dumps({'error': f'Missing required parameter: {str(e)}'})
        }
    except Exception as e:
        print(f"Error updating payment: {str(e)}")
        return {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Internal server error'})
        }