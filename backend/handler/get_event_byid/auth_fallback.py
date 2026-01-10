"""
Fallback authentication module for get_event_byid handler
This ensures consistent auth behavior when shared modules aren't available

Updated for new permission + region role structure
Version: 2.0 - Standardized Fallback Authentication
"""

import json
import base64
from datetime import datetime


def extract_user_credentials(event):
    """
    Extract user credentials with enhanced groups support
    Standardized implementation for all handlers
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
    STANDARDIZED permission validation using new permission + region role structure
    Uses new permission + region role structure
    """
    try:
        # Convert single permission to list
        if isinstance(required_permissions, str):
            required_permissions = [required_permissions]
        
        # SYSTEM ADMIN ROLES (Full access, no region required)
        system_admin_roles = ['System_CRUD', 'System_User_Management', 'System_Logs_Read']
        if any(role in system_admin_roles for role in user_roles):
            print(f"✅ System admin access granted for {user_email}: {[r for r in user_roles if r in system_admin_roles]}")
            return True, None# NEW ROLE STRUCTURE: Permission-based roles
        permission_roles = [
            'Members_CRUD', 'Members_Read', 'Members_Export',
            'Events_CRUD', 'Events_Read', 'Events_Export', 
            'Products_CRUD', 'Products_Read', 'Products_Export',
            'Communication_CRUD', 'Communication_Read', 'Communication_Export',
            'Webshop_Management', 'Members_Status_Approve'
        ]
        
        # Check if user has any permission roles
        user_permission_roles = [role for role in user_roles if role in permission_roles]
        if user_permission_roles:
            # For new role structure, also check for region roles
            region_roles = [role for role in user_roles if role.startswith('Regio_')]
            
            if region_roles:
                print(f"✅ Permission + region access granted for {user_email}: permissions={user_permission_roles}, regions={region_roles}")
                return True, None
            else:
                # User has permission role but no region role - incomplete new structure
                print(f"❌ Incomplete role structure for {user_email}: has permissions {user_permission_roles} but no region role")
                return False, {
                    'statusCode': 403,
                    'headers': cors_headers(),
                    'body': json.dumps({
                        'error': 'Access denied: Permission requires region assignment',
                        'required_structure': 'Permission (e.g., Members_CRUD) + Region (e.g., Regio_All)',
                        'user_roles': user_roles,
                        'missing': 'Region assignment (Regio_All, Regio_Noord-Holland, etc.)'
                    })
                }# SPECIAL ROLES: Limited access roles
        special_roles = ['hdcnLeden', 'verzoek_lid']
        if any(role in special_roles for role in user_roles):
            # These roles have limited access - deny by default for admin functions
            print(f"❌ Limited role access denied for {user_email}: {[r for r in user_roles if r in special_roles]}")
            return False, {
                'statusCode': 403,
                'headers': cors_headers(),
                'body': json.dumps({
                    'error': 'Access denied: Insufficient permissions',
                    'user_roles': user_roles,
                    'note': 'Limited access role - contact administrator for elevated permissions'
                })
            }
        
        # No valid roles found
        print(f"❌ No valid roles found for {user_email}: {user_roles}")
        return False, {
            'statusCode': 403,
            'headers': cors_headers(),
            'body': json.dumps({
                'error': 'Access denied: No valid permissions found',
                'required_permissions': required_permissions,
                'user_roles': user_roles,
                'help': 'Contact administrator to assign appropriate permission and region roles'
            })
        }
        
    except Exception as e:
        print(f"Error validating permissions: {str(e)}")
        return False, {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Error validating permissions'})
        }


def validate_permissions_with_regions(user_roles, required_permissions, user_email=None, resource_context=None):
    """
    STANDARDIZED enhanced permission validation that supports the new permission + region role structure
    This is the simplified fallback version that delegates to validate_permissions
    """
    try:
        # Convert single permission to list
        if isinstance(required_permissions, str):
            required_permissions = [required_permissions]
        
        # Use the standardized validate_permissions function
        is_authorized, error_response = validate_permissions(
            user_roles, required_permissions, user_email, resource_context
        )
        
        if is_authorized:
            # Determine regional access (simplified for fallback)
            regional_info = determine_regional_access(user_roles, resource_context)
            return True, None, regional_info
        else:
            return False, error_response, None
            
    except Exception as e:
        print(f"Error in validate_permissions_with_regions: {str(e)}")
        return False, {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Error validating permissions'})
        }, None


def determine_regional_access(user_roles, resource_context=None):
    """
    STANDARDIZED regional access determination based on user roles
    Simplified version for auth_fallback.py files
    """
    # System admin roles have full access
    system_admin_roles = ['System_CRUD', 'System_User_Management', 'System_Logs_Read']
    if any(role in system_admin_roles for role in user_roles):
        return {
            'access_type': 'system_admin',
            'has_full_access': True,
            'allowed_regions': ['all']
        }# Check for region roles
    region_roles = [role for role in user_roles if role.startswith('Regio_')]
    
    if 'Regio_All' in region_roles:
        return {
            'access_type': 'national',
            'has_full_access': True,
            'allowed_regions': ['all']
        }
    elif region_roles:
        # Extract region names from roles
        allowed_regions = []
        for role in region_roles:
            if role.startswith('Regio_'):
                region = role.replace('Regio_', '')
                allowed_regions.append(region)
        
        return {
            'access_type': 'regional',
            'has_full_access': False,
            'allowed_regions': allowed_regions
        }
    else:
        # No region roles - limited access
        return {
            'access_type': 'limited',
            'has_full_access': False,
            'allowed_regions': []
        }


def cors_headers():
    """
    STANDARDIZED CORS headers for all API responses
    """
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Enhanced-Groups"
    }


def handle_options_request():
    """
    STANDARDIZED OPTIONS request handler for CORS preflight
    """
    return {
        'statusCode': 200,
        'headers': cors_headers(),
        'body': ''
    }


def create_error_response(status_code, error_message, details=None):
    """
    STANDARDIZED error response creation
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
    STANDARDIZED success response creation
    """
    return {
        'statusCode': status_code,
        'headers': cors_headers(),
        'body': json.dumps(data)
    }


def log_successful_access(user_email, user_roles, operation, resource_context=None):
    """
    STANDARDIZED access logging for audit trail
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
    print(f"ACCESS: {user_email} (roles: {user_roles}) performed {operation}")
    if resource_context:
        print(f"CONTEXT: {resource_context}")


def require_auth_and_permissions(required_permissions):
    """
    STANDARDIZED decorator function to add authentication and permission checking to any handler
    Usage: @require_auth_and_permissions(['members_update'])
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
            
            # Validate permissions using standardized structure
            has_permission, permission_error = validate_permissions(
                user_roles, required_permissions, user_email
            )
            if not has_permission:
                return permission_error
            
            # Log successful access
            log_successful_access(user_email, user_roles, handler_func.__name__)
            
            # Call original handler with auth info
            return handler_func(event, context, user_email, user_roles)
        
        return wrapper
    return decorator


# ============================================================================
# STANDARDIZED FALLBACK AUTHENTICATION CONSTANTS
# ============================================================================

# These constants ensure consistency across all fallback files
SYSTEM_ADMIN_ROLES = ['System_CRUD', 'System_User_Management', 'System_Logs_Read']
PERMISSION_ROLES = [
    'Members_CRUD', 'Members_Read', 'Members_Export',
    'Events_CRUD', 'Events_Read', 'Events_Export', 
    'Products_CRUD', 'Products_Read', 'Products_Export',
    'Communication_CRUD', 'Communication_Read', 'Communication_Export',
    'Webshop_Management', 'Members_Status_Approve'
]
SPECIAL_ROLES = ['hdcnLeden', 'verzoek_lid']

# Version information for tracking updates
FALLBACK_AUTH_VERSION = "2.0"
FALLBACK_AUTH_UPDATED = "2026-01-08"
