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
        payload_decoded = base64.urlsafe_b64decode(payload_encoded)
        payload = json.loads(payload_decoded)
        
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
                    print(f"🔍 LAYER AUTH: Using enhanced groups from frontend (JSON): {enhanced_groups} for authenticated user {user_email}")
                    # Return the mapped user email (webmaster@h-dcn.nl) instead of Google email for audit trail
                    mapped_email = "webmaster@h-dcn.nl" if user_email.startswith("Google_") else user_email
                    return mapped_email, enhanced_groups, None
                else:
                    print(f"⚠️ LAYER AUTH: Invalid enhanced groups JSON format, falling back to JWT groups")
            except json.JSONDecodeError:
                # If JSON parsing fails, try comma-separated string format
                try:
                    enhanced_groups = [group.strip() for group in enhanced_groups_header.split(',') if group.strip()]
                    if enhanced_groups:
                        print(f"🔍 LAYER AUTH: Using enhanced groups from frontend (CSV): {enhanced_groups} for authenticated user {user_email}")
                        # Return the mapped user email (webmaster@h-dcn.nl) instead of Google email for audit trail
                        mapped_email = "webmaster@h-dcn.nl" if user_email.startswith("Google_") else user_email
                        return mapped_email, enhanced_groups, None
                    else:
                        print(f"⚠️ LAYER AUTH: Empty enhanced groups, falling back to JWT groups")
                except Exception as e:
                    print(f"⚠️ LAYER AUTH: Failed to parse enhanced groups header as CSV: {e}, falling back to JWT groups")
        
        # Fallback to JWT token groups
        user_roles = payload.get('cognito:groups', [])
        print(f"🔍 LAYER AUTH: Using JWT token groups: {user_roles} for user {user_email}")
        
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
        required_permissions (list or str): Required permission(s) for the operation
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
        
        # Define role-to-permission mappings
        role_permissions = {
            # Administrative roles - full access
            'hdcnAdmins': ['*'],
            'System_CRUD_All': ['*'],
            'Webmaster': ['*'],
            
            # Member management
            'Members_CRUD_All': ['members_create', 'members_read', 'members_update', 'members_delete', 'members_export'],
            'Members_Read_All': ['members_read', 'members_list'],
            'Members_Status_Approve': ['members_status_change'],
            'Members_Export_All': ['members_export'],
            
            # Event management
            'Events_CRUD_All': ['events_create', 'events_read', 'events_update', 'events_delete', 'events_export'],
            'Events_Read_All': ['events_read', 'events_list'],
            'Events_Export_All': ['events_export'],
            
            # Product management
            'Products_CRUD_All': ['products_create', 'products_read', 'products_update', 'products_delete', 'products_export'],
            'Products_Read_All': ['products_read', 'products_list'],
            'Products_Export_All': ['products_export'],
            
            # Communication
            'Communication_CRUD_All': ['communication_create', 'communication_read', 'communication_update', 'communication_delete'],
            'Communication_Read_All': ['communication_read'],
            'Communication_Export_All': ['communication_export'],
            
            # System administration
            'System_User_Management': ['users_manage', 'roles_assign'],
            'System_Logs_Read': ['logs_read', 'audit_read'],
            
            # Webshop
            'Webshop_Management': ['products_create', 'products_read', 'products_update', 'products_delete', 'orders_manage'],
            
            # Organizational roles
            'National_Chairman': ['members_read', 'events_read', 'communication_read', 'reports_read'],
            'National_Secretary': ['members_read', 'events_read', 'communication_create', 'communication_read'],
            'National_Treasurer': ['members_read', 'payments_read', 'financial_reports'],
            'Tour_Commissioner': ['events_create', 'events_read', 'events_update', 'events_delete'],
            'Club_Magazine_Editorial': ['communication_create', 'communication_read', 'communication_update'],
            
            # Basic member
            'hdcnLeden': ['profile_read', 'profile_update_own', 'events_read', 'products_read']
        }
        
        # Get all permissions for user's roles
        user_permissions = set()
        for role in user_roles:
            if role in role_permissions:
                permissions = role_permissions[role]
                if '*' in permissions:
                    # Full access - authorize everything
                    print(f"🔍 LAYER AUTH: User {user_email} has full access via role {role}")
                    return True, None
                user_permissions.update(permissions)
        
        # Check if user has any of the required permissions
        has_permission = any(perm in user_permissions for perm in required_permissions)
        
        if not has_permission:
            # Log permission denial
            log_permission_denial(
                user_email=user_email,
                user_roles=user_roles,
                required_permissions=required_permissions,
                user_permissions=list(user_permissions),
                resource_context=resource_context
            )
            
            return False, {
                'statusCode': 403,
                'headers': cors_headers(),
                'body': json.dumps({
                    'error': 'Access denied: Insufficient permissions',
                    'required_permissions': required_permissions,
                    'user_roles': user_roles
                })
            }
        
        print(f"🔍 LAYER AUTH: User {user_email} authorized for {required_permissions}")
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