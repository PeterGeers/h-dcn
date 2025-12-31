"""
Shared authentication and authorization utilities for Lambda handlers
Provides consistent credential validation across all backend functions
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
        enhanced_groups_header = event.get('headers', {}).get('X-Enhanced-Groups')
        if enhanced_groups_header:
            try:
                enhanced_groups = json.loads(enhanced_groups_header)
                if isinstance(enhanced_groups, list):
                    print(f"🔍 Using enhanced groups from frontend: {enhanced_groups} for user {user_email}")
                    return user_email, enhanced_groups, None
                else:
                    print(f"⚠️ Invalid enhanced groups format, falling back to JWT groups")
            except json.JSONDecodeError:
                print(f"⚠️ Failed to parse enhanced groups header, falling back to JWT groups")
        
        # Fallback to JWT token groups
        user_roles = payload.get('cognito:groups', [])
        print(f"🔍 Using JWT token groups: {user_roles} for user {user_email}")
        
        return user_email, user_roles, None
        
    except Exception as e:
        print(f"Error extracting user credentials: {str(e)}")
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
            # Administrative roles
            'hdcnAdmins': ['*'],  # Full access
            'System_CRUD_All': ['*'],  # Full system access
            'System_User_Management': ['users_manage', 'roles_assign'],
            'System_Logs_Read': ['logs_read', 'audit_read'],
            
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
            
            # Webshop
            'Webshop_Management': ['products_create', 'products_read', 'products_update', 'products_delete', 'orders_manage'],
            
            # Organizational roles
            'National_Chairman': ['members_read', 'events_read', 'communication_read', 'reports_read'],
            'National_Secretary': ['members_read', 'events_read', 'communication_create', 'communication_read'],
            'National_Treasurer': ['members_read', 'payments_read', 'financial_reports'],
            'Webmaster': ['*'],  # Full access
            
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
        
        return True, None
        
    except Exception as e:
        print(f"Error validating permissions: {str(e)}")
        return False, {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Error validating permissions'})
        }


def log_permission_denial(user_email, user_roles, required_permissions, user_permissions, resource_context=None):
    """
    Log permission denial for security monitoring
    
    Args:
        user_email (str): Email of user attempting access
        user_roles (list): User's roles
        required_permissions (list): Permissions that were required
        user_permissions (list): Permissions the user actually has
        resource_context (dict): Optional context about the resource
    """
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
    
    print(f"SECURITY_AUDIT: {json.dumps(log_entry)}")
    print(f"Permission denied: User {user_email} (roles: {user_roles}) attempted to access "
          f"resource requiring {required_permissions} but only has {user_permissions}")


def log_successful_access(user_email, user_roles, operation, resource_context=None):
    """
    Log successful access for audit trail
    
    Args:
        user_email (str): Email of user performing operation
        user_roles (list): User's roles
        operation (str): Operation being performed
        resource_context (dict): Optional context about the resource
    """
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'event_type': 'ACCESS_GRANTED',
        'user_email': user_email,
        'user_roles': user_roles,
        'operation': operation,
        'resource_context': resource_context,
        'severity': 'INFO'
    }
    
    print(f"ACCESS_AUDIT: {json.dumps(log_entry)}")


def cors_headers():
    """
    Standard CORS headers for all API responses
    """
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Enhanced-Groups"
    }


def handle_options_request():
    """
    Standard OPTIONS request handler for CORS preflight
    """
    return {
        'statusCode': 200,
        'headers': cors_headers(),
        'body': ''
    }


def create_error_response(status_code, error_message, details=None):
    """
    Create standardized error response
    
    Args:
        status_code (int): HTTP status code
        error_message (str): Error message
        details (dict): Optional additional error details
        
    Returns:
        dict: Lambda response object
    """
    body = {'error': error_message}
    if details:
        body.update(details)
    
    return {
        'statusCode': status_code,
        'headers': cors_headers(),
        'body': json.dumps(body)
    }


def create_success_response(data, status_code=200):
    """
    Create standardized success response
    
    Args:
        data (dict): Response data
        status_code (int): HTTP status code (default 200)
        
    Returns:
        dict: Lambda response object
    """
    return {
        'statusCode': status_code,
        'headers': cors_headers(),
        'body': json.dumps(data)
    }