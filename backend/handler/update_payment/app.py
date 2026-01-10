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
table_name = os.environ.get('DYNAMODB_TABLE', 'Payments')
table = dynamodb.Table(table_name)

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

def lambda_handler(event, context):
    try:
        # Handle OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return handle_options_request()
        
        # Extract user credentials
        user_email, user_roles, auth_error = extract_user_credentials(event)
        if auth_error:
            return auth_error
        
        # DUAL ACCESS PATTERN: Admin access OR user access to own payments
        
        # First check if user has admin permissions for payment management
        required_permissions = ['products_update']
        is_admin_authorized, admin_error_response, regional_info = validate_permissions_with_regions(
            user_roles, required_permissions, user_email, None
        )
        
        # If not admin, check if user has basic webshop access (hdcnLeden) for own payments
        has_webshop_access = 'hdcnLeden' in user_roles
        
        if not is_admin_authorized and not has_webshop_access:
            return create_error_response(403, 'Access denied: Requires admin permissions or hdcnLeden membership for own payments', {
                'required_admin_permissions': required_permissions,
                'required_user_role': 'hdcnLeden',
                'user_roles': user_roles
            })
        
        # Log successful access
        log_successful_access(user_email, user_roles, 'update_payment')
        
        payment_id = event['pathParameters']['payment_id']
        data = json.loads(event['body']) if event['body'] else {}
        
        # Get existing payment to validate ownership
        existing_payment_response = table.get_item(Key={'payment_id': payment_id})
        
        if 'Item' not in existing_payment_response:
            return create_error_response(404, 'Payment not found')
        
        existing_payment = existing_payment_response['Item']
        
        # Validate payment ownership (only payment owner or admin can update)
        payment_owner_email = existing_payment.get('user_email')
        is_admin = is_admin_authorized  # Use the admin authorization result
        
        if not is_admin and (not payment_owner_email or payment_owner_email.lower() != user_email.lower()):
            print(f"SECURITY ALERT: User {user_email} attempted to update payment {payment_id} owned by {payment_owner_email}")
            return create_error_response(403, 'Access denied: You can only update your own payments', {
                'payment_id': payment_id
            })
        
        # Dynamically build update expression and attribute values
        update_expression_parts = []
        expression_attribute_names = {}
        expression_attribute_values = {}
        
        for key, value in data.items():
            # Prevent updating sensitive fields
            if key in ['payment_id', 'user_email', 'created_at']:
                continue
            
            placeholder_name = f"#{key}"
            placeholder_value = f":{key}"
            update_expression_parts.append(f"{placeholder_name} = {placeholder_value}")
            expression_attribute_names[placeholder_name] = key
            expression_attribute_values[placeholder_value] = value
        
        # Add updated timestamp and user
        update_expression_parts.append("#updated_at = :updated_at")
        update_expression_parts.append("#updated_by = :updated_by")
        expression_attribute_names["#updated_at"] = "updated_at"
        expression_attribute_names["#updated_by"] = "updated_by"
        expression_attribute_values[":updated_at"] = datetime.utcnow().isoformat()
        expression_attribute_values[":updated_by"] = user_email
        
        update_expression = "SET " + ", ".join(update_expression_parts)
        
        table.update_item(
            Key={'payment_id': payment_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values
        )
        
        # Log payment update for comprehensive audit trail
        log_payment_audit('UPDATE', payment_id, user_email, user_roles, {
            'updated_fields': list(data.keys()),
            'is_admin_update': is_admin,
            'original_owner': payment_owner_email,
            'payment_amount': existing_payment.get('amount', 0)
        })
        
        print(f"Payment {payment_id} updated by {user_email} with roles {user_roles}")
        
        return create_success_response({
            'message': f'Payment {payment_id} updated successfully',
            'updated_fields': list(data.keys())
        })
        
    except KeyError as e:
        return create_error_response(400, f'Missing required parameter: {str(e)}')
    except json.JSONDecodeError:
        return create_error_response(400, 'Invalid JSON in request body')
    except Exception as e:
        print(f"Unexpected error in update_payment: {str(e)}")
        return create_error_response(500, 'Internal server error')