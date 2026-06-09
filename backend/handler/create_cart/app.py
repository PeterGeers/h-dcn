import json
import boto3
import uuid
from datetime import datetime
from decimal import Decimal

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
    from shared.channel_resolver import resolve_channels
    from shared.club_identity import get_club_id
    print("Using shared auth layer")
except ImportError as e:
    # Built-in smart fallback - no local auth_fallback.py needed
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("create_cart")
    # Exit early - the fallback handler will handle all requests
    import sys
    sys.exit(0)

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

def validate_cart_items(items):
    """
    Validate cart items use variant_id reference (not selectedOption).

    Each item must have: product_id, variant_id, quantity.
    Items must NOT contain selectedOption.

    Args:
        items (list): List of cart item dicts

    Returns:
        tuple: (is_valid, error_message)
    """
    if not isinstance(items, list):
        return False, "items must be an array"

    for i, item in enumerate(items):
        if not isinstance(item, dict):
            return False, f"Item at index {i} must be an object"

        # Required fields
        if 'product_id' not in item:
            return False, f"Item at index {i} missing required field 'product_id'"
        if 'variant_id' not in item:
            return False, f"Item at index {i} missing required field 'variant_id'"
        if 'quantity' not in item:
            return False, f"Item at index {i} missing required field 'quantity'"

        # Validate quantity is a positive integer
        quantity = item['quantity']
        if not isinstance(quantity, int) or quantity < 1:
            return False, f"Item at index {i}: quantity must be a positive integer"

        # Reject legacy selectedOption field
        if 'selectedOption' in item:
            return False, f"Item at index {i}: 'selectedOption' is not allowed, use 'variant_id' instead"

    return True, None


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
        log_successful_access(user_email, user_roles, 'create_cart')
        
        body = json.loads(event['body'])
        
        # Derive channel from Cognito group membership
        user_channels = resolve_channels(user_roles)
        # Use requested channel from body, or default to first available channel
        channel = body.get('channel')
        if channel:
            if channel not in user_channels:
                return create_error_response(403, 'Channel access denied', {
                    'details': {
                        'requested_channel': channel,
                        'allowed_channels': sorted(user_channels)
                    }
                })
        else:
            # Default to h-dcn if available, otherwise first channel
            channel = 'h-dcn' if 'h-dcn' in user_channels else (
                next(iter(sorted(user_channels))) if user_channels else None
            )

        if not channel:
            return create_error_response(403, 'No channel access available')

        # Derive club_id for PresMeet users (from Member record)
        club_id = None
        if channel == 'presmeet':
            club_id = get_club_id(user_email)

        # Validate items if provided
        items = body.get('items', [])
        if items:
            is_valid, error_msg = validate_cart_items(items)
            if not is_valid:
                return create_error_response(400, error_msg)

        # Build cart items with proper structure
        cart_items = []
        total_amount = Decimal('0')
        for item in items:
            unit_price = Decimal(str(item.get('unit_price', '0')))
            quantity = item['quantity']
            cart_item = {
                'product_id': item['product_id'],
                'variant_id': item['variant_id'],
                'quantity': quantity,
                'unit_price': unit_price,
            }
            # Include optional display fields
            if 'variant_attributes' in item:
                cart_item['variant_attributes'] = item['variant_attributes']
            if 'item_fields_data' in item:
                cart_item['item_fields_data'] = item['item_fields_data']
            cart_items.append(cart_item)
            total_amount += unit_price * quantity

        cart_id = str(uuid.uuid4())
        cart = {
            'cart_id': cart_id,
            'customer_id': body['customer_id'],
            'user_email': user_email,
            'channel': channel,
            'items': cart_items,
            'total_amount': total_amount,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }

        # Add club_id for PresMeet users
        if club_id:
            cart['club_id'] = club_id
        
        table.put_item(Item=cart)
        
        # Log cart creation for comprehensive audit trail
        log_cart_audit('CREATE', cart_id, user_email, user_roles, {
            'customer_id': body['customer_id'],
            'channel': channel,
            'club_id': club_id,
            'total_amount': str(total_amount),
            'item_count': len(cart_items),
            'timestamp': cart['created_at']
        })
        
        return create_success_response({
            'cart_id': cart_id, 
            'message': 'Cart created successfully'
        }, 201)
        
    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body')
    except KeyError as e:
        return create_error_response(400, f'Missing required field: {str(e)}')
    except Exception as e:
        print(f"Error creating cart: {str(e)}")
        return create_error_response(500, 'Internal server error')