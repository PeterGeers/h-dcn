import json
import boto3
import sys
import os
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
table_name = os.environ.get('DYNAMODB_TABLE', 'Orders')
table = dynamodb.Table(table_name)

def lambda_handler(event, context):
    try:
        # Handle OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()
        
        # Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error
        
        # DUAL ACCESS PATTERN: Admin access OR user access to own orders
        
        # First check if user has admin permissions for order management
        required_permissions = ['products_update']  # Orders are webshop/product domain
        is_admin_authorized, admin_error_response, regional_info = validate_permissions_with_regions(
            user_roles, required_permissions, user_email, None
        )
        
        # If not admin, check if user has basic webshop access (hdcnLeden) for own orders
        has_webshop_access = 'hdcnLeden' in user_roles
        
        if not is_admin_authorized and not has_webshop_access:
            return create_error_response(403, 'Access denied: Requires admin permissions or hdcnLeden membership for own orders', {
                'required_admin_permissions': required_permissions,
                'required_user_role': 'hdcnLeden',
                'user_roles': user_roles
            })
        
        # Log successful access
        log_successful_access(user_email, user_roles, 'update_order_status')
        
        order_id = event['pathParameters']['order_id']
        data = json.loads(event['body']) if event['body'] else {}
        
        # Get existing order to validate ownership
        existing_order_response = table.get_item(Key={'order_id': order_id})
        
        if 'Item' not in existing_order_response:
            return create_error_response(404, 'Order not found')
        
        existing_order = existing_order_response['Item']
        
        # Validate order ownership (only order owner or admin can update)
        order_owner_email = existing_order.get('user_email')
        is_admin = is_admin_authorized  # Use the admin authorization result
        
        if not is_admin and (not order_owner_email or order_owner_email.lower() != user_email.lower()):
            print(f"SECURITY ALERT: User {user_email} attempted to update order {order_id} owned by {order_owner_email}")
            return create_error_response(403, 'Access denied: You can only update your own orders', {
                'order_id': order_id
            })
        
        # Dynamically build update expression and attribute values
        update_expression_parts = []
        expression_attribute_names = {}
        expression_attribute_values = {}
        
        for key, value in data.items():
            # Prevent updating sensitive fields
            if key in ['order_id', 'user_email', 'created_at']:
                continue
            
            placeholder_name = f"#{key}"
            placeholder_value = f":{key}"
            update_expression_parts.append(f"{placeholder_name} = {placeholder_value}")
            expression_attribute_names[placeholder_name] = key
            expression_attribute_values[placeholder_value] = value
        
        # Add updated timestamp
        update_expression_parts.append("#updated_at = :updated_at")
        expression_attribute_names["#updated_at"] = "updated_at"
        expression_attribute_values[":updated_at"] = datetime.now().isoformat()
        
        update_expression = "SET " + ", ".join(update_expression_parts)
        
        table.update_item(
            Key={'order_id': order_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values
        )
        
        # Log order update for audit purposes
        access_type = 'admin' if is_admin else 'owner'
        print(f"Order {order_id} updated by user {user_email} ({access_type}) with roles {user_roles}. Fields updated: {list(data.keys())}")
        
        return create_success_response({
            'message': f'Order {order_id} updated successfully',
            'updated_fields': list(data.keys())
        })
        
    except KeyError as e:
        return create_error_response(400, f'Missing required parameter: {str(e)}')
    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        print(f"Unexpected error in update_order_status: {str(e)}")
        return create_error_response(500, 'Internal server error')
