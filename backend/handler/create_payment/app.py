import json
import boto3
import uuid
import base64
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
except ImportError as e:
    # Built-in smart fallback - no local auth_fallback.py needed
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("create_payment")
    # Exit early - the fallback handler will handle all requests
    import sys
    sys.exit(0)

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


def lambda_handler(event, context):
    try:
        # Handle OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()
        
        # Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error
        
        # DUAL ACCESS PATTERN: Admin access OR user access to create own payments
        
        # First check if user has admin permissions for payment creation
        required_permissions = ['products_create']
        is_admin_authorized, admin_error_response, regional_info = validate_permissions_with_regions(
            user_roles, required_permissions, user_email, None
        )
        
        # If not admin, check if user has basic webshop access (hdcnLeden) for own payments
        has_webshop_access = 'hdcnLeden' in user_roles
        
        if not is_admin_authorized and not has_webshop_access:
            return create_error_response(403, 'Access denied: Requires admin permissions or hdcnLeden role for own payments', {
                'required_admin_permissions': required_permissions,
                'required_user_role': 'hdcnLeden',
                'user_roles': user_roles
            })
        
        # Log successful access
        log_successful_access(user_email, user_roles, 'create_payment')
        
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
            'order_member_id': order_data.get('member_id') if order_data else None,
            'is_admin_create': is_admin_authorized
        })
        
        return create_success_response({
            'payment_id': payment_id, 
            'message': 'Payment created successfully'
        })
        
    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        print(f"Error creating payment: {str(e)}")
        return create_error_response(500, 'Internal server error')