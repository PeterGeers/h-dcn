import json
import os
import boto3
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
    print("Using shared auth layer for get_order_byid")
except ImportError as e:
    # Built-in smart fallback - no local auth_fallback.py needed
    print(f"⚠️ Shared auth unavailable: {str(e)}")
    from shared.maintenance_fallback import create_smart_fallback_handler
    lambda_handler = create_smart_fallback_handler("get_order_byid")
    # Exit early - the fallback handler will handle all requests
    import sys
    sys.exit(0)

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('ORDERS_TABLE_NAME', 'Orders'))


def _convert_decimals(obj):
    """Recursively convert Decimal to int/float for JSON serialization."""
    if isinstance(obj, list):
        return [_convert_decimals(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: _convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    return obj

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
        
        # Access check: any authenticated member or admin
        is_admin, _, _ = validate_permissions_with_regions(
            user_roles, ['Products_CRUD'], user_email, None
        )
        has_member_access = 'hdcnLeden' in user_roles
        has_event_access = any(r in user_roles for r in ('Regio_Pressmeet', 'Regio_All', 'event_participant'))

        if not is_admin and not has_member_access and not has_event_access:
            return create_error_response(403, 'Access denied: Requires membership access')
        
        # Log successful access
        log_successful_access(user_email, user_roles, 'get_order_byid')
        
        order_id = event['pathParameters'].get('id') or event['pathParameters'].get('order_id')
        
        response = table.get_item(Key={'order_id': order_id})
        
        if 'Item' not in response:
            return create_error_response(404, 'Order not found')
        
        order = response['Item']
        
        # Validate order ownership - users can only access their own orders unless admin
        order_user_email = order.get('user_email')
        has_admin_role = is_admin or any(role in user_roles for role in ['Members_CRUD', 'Webshop_Management'])
        
        if not has_admin_role and order_user_email and order_user_email.lower() != user_email.lower():
            return create_error_response(403, 'Access denied: You can only access your own orders')
        
        # Log order access for comprehensive audit trail
        access_type = "admin" if has_admin_role else "owner"
        log_order_audit('ACCESS', order_id, user_email, user_roles, {
            'order_owner': order_user_email,
            'access_type': access_type,
            'access_method': 'direct_id_lookup',
            'order_total': order.get('total_amount', 0),
            'order_status': order.get('status', 'unknown'),
            'admin_roles': [role for role in user_roles if role in ['Members_CRUD', 'Webshop_Management']] if has_admin_role else []
        })
        
        return create_success_response(_convert_decimals(order))
        
    except KeyError as e:
        return create_error_response(400, f'Missing required parameter: {str(e)}')
    except Exception as e:
        print(f"Error retrieving order: {str(e)}")
        return create_error_response(500, 'Internal server error')