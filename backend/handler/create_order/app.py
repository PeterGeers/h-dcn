import json
import boto3
import boto3.dynamodb.conditions
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
            return None, create_error_response(404, 'Member record not found for authenticated user', {
                'user_email': user_email,
                'message': 'Please contact administration to link your account to a member record'
            })
        
        # Get the first matching member record
        member_record = response['Items'][0]
        member_id = member_record.get('member_id')
        
        if not member_id:
            return None, create_error_response(500, 'Member record found but missing member_id', {
                'user_email': user_email
            })
        
        return member_id, None
        
    except Exception as e:
        print(f"Error looking up member_id for email {user_email}: {str(e)}")
        return None, create_error_response(500, 'Error looking up member information')

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
            return False, None, create_error_response(400, 'cart_id is required for order creation')
        
        # Get cart from database
        response = carts_table.get_item(Key={'cart_id': cart_id})
        
        if 'Item' not in response:
            return False, None, create_error_response(404, 'Cart not found', {
                'cart_id': cart_id
            })
        
        cart = response['Item']
        cart_user_email = cart.get('user_email')
        
        # Validate cart ownership
        if not cart_user_email:
            # Log security issue - cart without owner
            print(f"SECURITY WARNING: Cart {cart_id} has no user_email - potential data integrity issue")
            return False, None, create_error_response(400, 'Cart ownership cannot be verified', {
                'cart_id': cart_id
            })
        
        if cart_user_email.lower() != user_email.lower():
            # Log unauthorized cart access attempt
            print(f"SECURITY ALERT: User {user_email} attempted to create order from cart {cart_id} owned by {cart_user_email}")
            return False, None, create_error_response(403, 'Access denied: You can only create orders from your own cart', {
                'cart_id': cart_id
            })
        
        return True, cart, None
        
    except Exception as e:
        print(f"Error validating cart ownership for cart {cart_id}: {str(e)}")
        return False, None, create_error_response(500, 'Error validating cart ownership')

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

def lambda_handler(event, context):
    try:
        # Handle OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()
        
        # Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error
        
        # DUAL ACCESS PATTERN: Admin access OR user access for own orders
        
        # First check if user has admin permissions for order management
        required_permissions = ['products_create']
        is_admin_authorized, admin_error_response, regional_info = validate_permissions_with_regions(
            user_roles, required_permissions, user_email, None
        )
        
        # If not admin, check if user has basic webshop access (hdcnLeden) for own orders
        has_webshop_access = 'hdcnLeden' in user_roles
        
        if not is_admin_authorized and not has_webshop_access:
            return create_error_response(403, 'Access denied: Requires admin permissions or hdcnLeden role for own orders', {
                'required_admin_permissions': required_permissions,
                'required_user_role': 'hdcnLeden',
                'user_roles': user_roles
            })
        
        # Log successful access
        log_successful_access(user_email, user_roles, 'create_order')
        
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
        
        return create_success_response({
            'order_id': order_id, 
            'member_id': member_id,
            'message': 'Order created successfully'
        })
    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        print(f"Error creating order: {str(e)}")
        return create_error_response(500, 'Internal server error')