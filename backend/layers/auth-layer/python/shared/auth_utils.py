"""
Shared authentication and authorization utilities for H-DCN Lambda functions
Deployed as Lambda Layer for consistent authentication across all handlers
"""

import json
import base64
from datetime import datetime


def extract_user_credentials(event):
    """
    Extract user credentials from Lambda event with enhanced groups support
    
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
        
        # Decode JWT token to get user info
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
        try:
            payload_decoded = base64.urlsafe_b64decode(payload_encoded)
        except Exception as decode_error:
            return None, None, {
                'statusCode': 401,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Invalid JWT token encoding'})
            }
        
        try:
            payload = json.loads(payload_decoded)
        except Exception as json_error:
            return None, None, {
                'statusCode': 401,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Invalid JWT token payload'})
            }
        
        # Extract user email
        user_email = payload.get('email') or payload.get('username')
        if not user_email:
            return None, None, {
                'statusCode': 401,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'User email not found in token'})
            }
        
        # Check for enhanced groups from frontend credential combination
        # This supports the H-DCN credential mapping where Google SSO users
        # get mapped to their native account permissions
        enhanced_groups_header = event.get('headers', {}).get('X-Enhanced-Groups')
        if enhanced_groups_header:
            try:
                # Try parsing as JSON first (array format)
                enhanced_groups = json.loads(enhanced_groups_header)
                if isinstance(enhanced_groups, list):
                    # Return the mapped user email (webmaster@h-dcn.nl) instead of Google email for audit trail
                    mapped_email = "webmaster@h-dcn.nl" if user_email.startswith("Google_") else user_email
                    return mapped_email, enhanced_groups, None
                else:
                    pass  # Fall back to JWT groups
            except json.JSONDecodeError:
                # If JSON parsing fails, try comma-separated string format
                try:
                    enhanced_groups = [group.strip() for group in enhanced_groups_header.split(',') if group.strip()]
                    if enhanced_groups:
                        # Return the mapped user email (webmaster@h-dcn.nl) instead of Google email for audit trail
                        mapped_email = "webmaster@h-dcn.nl" if user_email.startswith("Google_") else user_email
                        return mapped_email, enhanced_groups, None
                    else:
                        pass  # Fall back to JWT groups
                except Exception as e:
                    pass  # Fall back to JWT groups
        
        # Fallback to JWT token groups
        user_roles = payload.get('cognito:groups', [])
        
        return user_email, user_roles, None
        
    except Exception as e:
        print(f"LAYER AUTH ERROR: Error extracting user credentials: {str(e)}")
        return None, None, {
            'statusCode': 401,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Invalid authorization token'})
        }


def validate_permissions(user_roles, required_permissions, user_email=None, resource_context=None):
    """
    Validate user has required permissions for an operation
    
    Args:
        user_roles (list): List of user's roles from credentials
        required_permissions (list or str): Required permission(s) or roles for the operation
        user_email (str): Optional user email for logging
        resource_context (dict): Optional context about the resource being accessed
        
    Returns:
        tuple: (is_authorized, error_response)
               If authorized: (True, None)
               If not authorized: (False, error_response_dict)
    """
    try:
        # Convert single permission to list
        if isinstance(required_permissions, str):
            required_permissions = [required_permissions]
        
        # SIMPLIFIED APPROACH: Check if user has any of the required roles directly
        # This eliminates the complex mapping layer and makes authorization clearer
        
        # Admin roles get full access
        admin_roles = ['hdcnAdmins', 'System_CRUD_All', 'Webmaster']
        if any(role in user_roles for role in admin_roles):
            return True, None
        
        # Check if user has any of the required roles directly
        has_permission = any(role in user_roles for role in required_permissions)
        
        if not has_permission:
            # Log permission denial
            log_permission_denial(
                user_email=user_email,
                user_roles=user_roles,
                required_permissions=required_permissions,
                user_permissions=user_roles,  # User permissions are just their roles now
                resource_context=resource_context
            )
            
            return False, {
                'statusCode': 403,
                'headers': cors_headers(),
                'body': json.dumps({
                    'error': 'Access denied: Insufficient permissions',
                    'required_roles': required_permissions,
                    'user_roles': user_roles
                })
            }
        
        return True, None
        
    except Exception as e:
        print(f"LAYER AUTH ERROR: Error validating permissions: {str(e)}")
        return False, {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Error validating permissions'})
        }


def log_permission_denial(user_email, user_roles, required_permissions, user_permissions, resource_context=None):
    """Log permission denial for security monitoring"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'event_type': 'PERMISSION_DENIED',
        'user_email': user_email,
        'user_roles': user_roles,
        'required_permissions': required_permissions,
        'user_permissions': user_permissions,
        'resource_context': resource_context,
        'severity': 'WARNING'
    }
    
    print(f"LAYER SECURITY_AUDIT: {json.dumps(log_entry)}")


def log_successful_access(user_email, user_roles, operation, resource_context=None):
    """Log successful access for audit trail"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'event_type': 'ACCESS_GRANTED',
        'user_email': user_email,
        'user_roles': user_roles,
        'operation': operation,
        'resource_context': resource_context,
        'severity': 'INFO'
    }
    
    print(f"LAYER ACCESS_AUDIT: {json.dumps(log_entry)}")


def cors_headers():
    """Standard CORS headers for all API responses"""
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Enhanced-Groups"
    }


def handle_options_request():
    """Standard OPTIONS request handler for CORS preflight"""
    return {
        'statusCode': 200,
        'headers': cors_headers(),
        'body': ''
    }


def create_error_response(status_code, error_message, details=None):
    """Create standardized error response"""
    body = {'error': error_message}
    if details:
        body.update(details)
    
    return {
        'statusCode': status_code,
        'headers': cors_headers(),
        'body': json.dumps(body)
    }


def create_success_response(data, status_code=200):
    """Create standardized success response"""
    return {
        'statusCode': status_code,
        'headers': cors_headers(),
        'body': json.dumps(data)
    }


def require_auth(required_permissions):
    """
    Decorator to add authentication and authorization to any Lambda handler
    
    Usage:
    @require_auth(['members_update'])
    def lambda_handler(event, context):
        # Handler code here
        # User info available in event['auth_user'] and event['auth_roles']
    """
    def decorator(handler_func):
        def wrapper(event, context):
            # Handle OPTIONS request
            if event.get('httpMethod') == 'OPTIONS':
                return handle_options_request()
            
            # Extract credentials
            user_email, user_roles, auth_error = extract_user_credentials(event)
            if auth_error:
                return auth_error
            
            # Validate permissions
            has_permission, permission_error = validate_permissions(
                user_roles, required_permissions, user_email
            )
            if not has_permission:
                return permission_error
            
            # Log access
            log_successful_access(user_email, user_roles, handler_func.__name__)
            
            # Add auth info to event for handler use
            event['auth_user'] = user_email
            event['auth_roles'] = user_roles
            
            # Call original handler
            return handler_func(event, context)
        
        return wrapper
    return decorator