"""
Local copy of shared authentication utilities for Lambda handlers
This is a fallback when the shared module is not available via Lambda layers
"""

import json
import base64
from datetime import datetime


def extract_user_credentials(event):
    """
    Extract user credentials from Lambda event with enhanced groups support
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
    Basic permission validation - allows admin roles full access
    """
    # Admin roles that have full access
    admin_roles = [
        'hdcnAdmins', 'System_CRUD_All', 'Webmaster', 
        'Members_CRUD_All', 'Products_CRUD_All', 'Events_CRUD_All'
    ]
    
    # Check if user has any admin role
    has_admin_access = any(role in admin_roles for role in user_roles)
    
    if has_admin_access:
        return True, None
    
    # For non-admin users, deny access for now (can be enhanced later)
    return False, {
        'statusCode': 403,
        'headers': cors_headers(),
        'body': json.dumps({
            'error': 'Access denied: Insufficient permissions',
            'required_permissions': required_permissions,
            'user_roles': user_roles
        })
    }


def cors_headers():
    """Standard CORS headers"""
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Enhanced-Groups"
    }


def handle_options_request():
    """Standard OPTIONS request handler"""
    return {
        'statusCode': 200,
        'headers': cors_headers(),
        'body': ''
    }


def log_successful_access(user_email, user_roles, operation, resource_context=None):
    """Log successful access"""
    print(f"ACCESS: {user_email} (roles: {user_roles}) performed {operation}")
    if resource_context:
        print(f"CONTEXT: {resource_context}")


def create_error_response(status_code, error_message, details=None):
    """Create error response"""
    body = {'error': error_message}
    if details:
        body.update(details)
    
    return {
        'statusCode': status_code,
        'headers': cors_headers(),
        'body': json.dumps(body)
    }


def create_success_response(data, status_code=200):
    """Create success response"""
    return {
        'statusCode': status_code,
        'headers': cors_headers(),
        'body': json.dumps(data)
    }