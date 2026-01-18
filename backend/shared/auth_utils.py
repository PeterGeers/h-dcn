"""
Shared authentication and authorization utilities for Lambda handlers
Provides consistent credential validation across all backend functions
Version: 2.1.1 - Fixed regional access for users with both hdcnLeden and regional roles (2026-01-18)
"""

import json
import base64
from datetime import datetime


def extract_user_credentials(event):
    """
    Extract user credentials from Lambda event with built-in smart fallback
    
    Args:
        event: Lambda event containing headers
        
    Returns:
        tuple: (user_email, user_roles, error_response)
               If successful: (email_string, roles_list, None)
               If error: (None, None, error_response_dict)
    """
    try:
        from datetime import datetime
        FIX_VERSION = f"FIX_{datetime.now().strftime('%Y%m%d_%H%M%S')}"  # Auto-generated timestamp
        print(f"[AUTH_DEBUG] extract_user_credentials called from SHARED auth utils - FIX: {FIX_VERSION}")
        
        # Extract Authorization header
        headers = event.get('headers', {})
        print(f"[AUTH_DEBUG] Available headers: {list(headers.keys())}")
        
        auth_header = headers.get('Authorization')
        if not auth_header:
            print(f"❌ [AUTH_DEBUG] No Authorization header found")
            return None, None, {
                'statusCode': 401,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Authorization header required'})
            }
        
        print(f"🔍 [AUTH_DEBUG] Authorization header found")
        
        # Validate Bearer token format
        if not auth_header.startswith('Bearer '):
            print(f"❌ [AUTH_DEBUG] Invalid authorization header format")
            return None, None, {
                'statusCode': 401,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Invalid authorization header format'})
            }
        
        # Extract JWT token
        jwt_token = auth_header.replace('Bearer ', '')
        print(f"[AUTH_DEBUG] JWT token extracted (length: {len(jwt_token)})")
        print(f"[AUTH_DEBUG] JWT token full: {jwt_token}")
        
        # Additional validation for common issues
        if not jwt_token or jwt_token == 'undefined' or jwt_token == 'null':
            print(f"[AUTH_DEBUG] JWT token is empty or invalid: '{jwt_token}'")
            return None, None, {
                'statusCode': 401,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Empty or invalid JWT token'})
            }
        
        # Decode JWT token to get user info
        parts = jwt_token.split('.')
        if len(parts) != 3:
            print(f"❌ [AUTH_DEBUG] Invalid JWT token format - parts: {len(parts)}")
            print(f"❌ [AUTH_DEBUG] Token preview: {jwt_token[:100]}...")
            print(f"❌ [AUTH_DEBUG] Token ending: ...{jwt_token[-50:]}")
            print(f"❌ [AUTH_DEBUG] Parts breakdown:")
            for i, part in enumerate(parts):
                print(f"   Part {i}: {part[:50]}... (length: {len(part)})")
            return None, None, {
                'statusCode': 401,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'Invalid JWT token format'})
            }
        
        print(f"🔍 [AUTH_DEBUG] JWT token has correct format (3 parts)")
        
        # Decode payload (second part of JWT)
        payload_encoded = parts[1]
        # Add padding if needed for base64 decoding
        payload_encoded += '=' * (4 - len(payload_encoded) % 4)
        payload_decoded = base64.urlsafe_b64decode(payload_encoded)
        payload = json.loads(payload_decoded)
        
        print(f"🔍 [AUTH_DEBUG] JWT payload decoded successfully")
        print(f"🔍 [AUTH_DEBUG] JWT payload keys: {list(payload.keys())}")
        
        # Extract user email - try multiple possible fields
        user_email = (payload.get('email') or 
                     payload.get('username') or 
                     payload.get('cognito:username'))
        if not user_email:
            print(f"[AUTH_DEBUG] No email/username found in JWT payload")
            print(f"[AUTH_DEBUG] Available payload fields: {list(payload.keys())}")
            return None, None, {
                'statusCode': 401,
                'headers': cors_headers(),
                'body': json.dumps({'error': 'User email not found in token'})
            }
        
        print(f"🔍 [AUTH_DEBUG] User email extracted: {user_email}")
        
        # Check for enhanced groups from frontend credential combination
        enhanced_groups_header = headers.get('X-Enhanced-Groups')
        if enhanced_groups_header:
            try:
                enhanced_groups = json.loads(enhanced_groups_header)
                if isinstance(enhanced_groups, list):
                    print(f"✅ [AUTH_DEBUG] Using enhanced groups from frontend: {enhanced_groups} for user {user_email}")
                    return user_email, enhanced_groups, None
                else:
                    print(f"⚠️ [AUTH_DEBUG] Invalid enhanced groups format, falling back to JWT groups")
            except json.JSONDecodeError:
                print(f"⚠️ [AUTH_DEBUG] Failed to parse enhanced groups header, falling back to JWT groups")
        
        # Fallback to JWT token groups
        user_roles = payload.get('cognito:groups', [])
        print(f"🔍 [AUTH_DEBUG] Using JWT token groups: {user_roles} for user {user_email}")
        
        return user_email, user_roles, None
        
    except Exception as e:
        print(f"❌ [AUTH_DEBUG] Error extracting user credentials: {str(e)}")
        import traceback
        print(f"❌ [AUTH_DEBUG] Traceback: {traceback.format_exc()}")
        
        # Built-in smart fallback
        try:
            from shared.maintenance_fallback import log_auth_system_failure, create_maintenance_response
            log_auth_system_failure(None, e)  # Log for developers
            return None, None, create_maintenance_response()  # Return for users
        except ImportError:
            # Fallback if maintenance_fallback is not available
            return None, None, {
                'statusCode': 503,
                'headers': cors_headers(),
                'body': json.dumps({
                    'error': 'Service Temporarily Unavailable',
                    'message': 'Our authentication system is currently undergoing maintenance. Please try again in a few minutes.',
                    'contact': 'webmaster@h-dcn.nl',
                    'status': 'maintenance'
                })
            }


def validate_permissions_with_regions(user_roles, required_permissions, user_email=None, resource_context=None):
    """
    Streamlined permission validation with built-in smart fallback
    
    Args:
        user_roles (list): List of user's roles from credentials
        required_permissions (list or str): Required permission(s) for the operation
        user_email (str): Optional user email for logging
        resource_context (dict): Optional context about the resource being accessed
        
    Returns:
        tuple: (is_authorized, error_response, regional_access_info)
               If authorized: (True, None, regional_info_dict)
               If not authorized: (False, error_response_dict, None)
    """
    try:
        # Convert single permission to list
        if isinstance(required_permissions, str):
            required_permissions = [required_permissions]
        
        # STREAMLINED ROLE VALIDATION
        # 1. Check for system admin roles (full access, no region required)
        if any(role in ['System_CRUD', 'System_User_Management'] for role in user_roles):
            return True, None, {'has_full_access': True, 'allowed_regions': ['all'], 'access_type': 'admin'}
        
        # 2. Check permissions using streamlined validation
        is_authorized, error_response = validate_permissions(user_roles, required_permissions, user_email, resource_context)
        if not is_authorized:
            return False, error_response, None
        
        # 3. Validate region requirements (simplified logic)
        # Check for regional roles FIRST
        region_roles = [role for role in user_roles if role.startswith('Regio_')]
        
        # If user has regional roles, use regional access (even if they also have hdcnLeden)
        if region_roles:
            regional_info = determine_regional_access(user_roles, resource_context)
            print(f"[AUTH_DEBUG] User has regional roles: {region_roles}, regional_info: {regional_info}")
            return True, None, regional_info
        
        # Basic member roles (hdcnLeden, verzoek_lid) without regional roles
        if any(role in ['hdcnLeden', 'verzoek_lid'] for role in user_roles):
            print(f"[AUTH_DEBUG] User has basic member role without regional roles")
            return True, None, {'has_full_access': False, 'allowed_regions': [], 'access_type': 'basic_member'}
        
        # All other permission roles require region assignment
        return False, {
            'statusCode': 403,
            'headers': cors_headers(),
            'body': json.dumps({
                'error': 'Access denied: Permission requires region assignment',
                'required_structure': 'Permission (e.g., Members_CRUD) + Region (e.g., Regio_All)',
                'user_roles': user_roles,
                'missing': 'Region assignment'
            })
        }, None
        
    except Exception as e:
        print(f"Error validating permissions with regions: {str(e)}")
        
        # Built-in smart fallback
        try:
            from shared.maintenance_fallback import log_auth_system_failure, create_maintenance_response
            log_auth_system_failure(None, e)  # Log for developers
            return False, create_maintenance_response(), None  # Return for users
        except ImportError:
            # Fallback if maintenance_fallback is not available
            return False, {
                'statusCode': 503,
                'headers': cors_headers(),
                'body': json.dumps({
                    'error': 'Service Temporarily Unavailable',
                    'message': 'Our authentication system is currently undergoing maintenance. Please try again in a few minutes.',
                    'contact': 'webmaster@h-dcn.nl',
                    'status': 'maintenance'
                })
            }, None


def determine_regional_access(user_roles, resource_context=None):
    """
    Streamlined regional access determination for the new role structure
    
    Args:
        user_roles (list): List of user's roles
        resource_context (dict): Optional context about the resource
        
    Returns:
        dict: Regional access information
    """
    # System admin roles have full access
    if any(role in ['System_CRUD', 'System_User_Management'] for role in user_roles):
        return {'has_full_access': True, 'allowed_regions': ['all'], 'access_type': 'admin'}
    
    # Regio_All grants national access
    if 'Regio_All' in user_roles:
        return {'has_full_access': True, 'allowed_regions': ['all'], 'access_type': 'national'}
    
    # Specific regional roles
    region_roles = [role for role in user_roles if role.startswith('Regio_') and role != 'Regio_All']
    if region_roles:
        allowed_regions = [role.replace('Regio_', '') for role in region_roles]
        return {'has_full_access': False, 'allowed_regions': allowed_regions, 'access_type': 'regional'}
    
    # No regional access
    return {'has_full_access': False, 'allowed_regions': [], 'access_type': 'none'}


def check_regional_data_access(user_roles, data_region, user_email=None):
    """
    Streamlined regional data access check with enhanced logging
    
    Args:
        user_roles (list): User's roles
        data_region (str): Region of the data being accessed
        user_email (str): Optional user email for logging
        
    Returns:
        tuple: (is_allowed, reason)
    """
    regional_info = determine_regional_access(user_roles)
    
    # Full access users can access all regions
    if regional_info['has_full_access']:
        reason = f"Full access via {regional_info['access_type']}"
        if user_email:
            log_regional_access_event(user_email, user_roles, data_region, True, reason)
        return True, reason
    
    # Regional users can only access their assigned regions
    if data_region in regional_info['allowed_regions']:
        reason = f"Regional access to {data_region}"
        if user_email:
            log_regional_access_event(user_email, user_roles, data_region, True, reason)
        return True, reason
    
    # Access denied
    reason = f"Access denied: User can only access regions {regional_info['allowed_regions']}"
    if user_email:
        log_regional_access_event(user_email, user_roles, data_region, False, reason)
        print(f"REGIONAL_ACCESS_DENIED: User {user_email} (regions: {regional_info['allowed_regions']}) "
              f"attempted to access data from region: {data_region}")
    return False, reason


def get_user_accessible_regions(user_roles):
    """
    Get list of regions the user can access (streamlined)
    
    Args:
        user_roles (list): User's roles
        
    Returns:
        list: List of accessible region names, or ['all'] for full access
    """
    return determine_regional_access(user_roles)['allowed_regions']


def validate_permissions(user_roles, required_permissions, user_email=None, resource_context=None):
    """
    Streamlined permission validation for the new role structure
    
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
        
        # STREAMLINED ROLE-TO-PERMISSION MAPPING
        role_permissions = {
            # System roles (full access)
            'System_CRUD': ['*'],
            'System_User_Management': ['users_manage', 'roles_assign'],
            'System_Logs_Read': ['logs_read', 'audit_read'],
            
            # Permission roles (what you can do)
            'Members_CRUD': ['members_create', 'members_read', 'members_update', 'members_delete', 'members_export'],
            'Members_Read': ['members_read', 'members_list'],
            'Members_Export': ['members_export', 'members_read'],
            'Events_CRUD': ['events_create', 'events_read', 'events_update', 'events_delete', 'events_export'],
            'Events_Read': ['events_read', 'events_list'],
            'Events_Export': ['events_export', 'events_read'],
            'Products_CRUD': ['products_create', 'products_read', 'products_update', 'products_delete', 'products_export'],
            'Products_Read': ['products_read', 'products_list'],
            'Products_Export': ['products_export', 'products_read'],
            'Communication_CRUD': ['communication_create', 'communication_read', 'communication_update', 'communication_delete'],
            'Communication_Read': ['communication_read'],
            'Communication_Export': ['communication_export', 'communication_read'],
            'Members_Status_Approve': ['members_status_change'],
            'Webshop_Management': ['products_create', 'products_read', 'products_update', 'products_delete', 'orders_manage', 'webshop_access'],
            'hdcnLeden': [
                # Self-service member data
                'profile_read', 'profile_update_own', 'members_self_read', 'members_self_update',
                # Events access
                'events_read', 'events_list',
                # Webshop full access
                'products_read', 'products_list', 'webshop_access',
                'carts_create', 'carts_read', 'carts_update', 'carts_delete',
                'orders_create', 'orders_read_own', 'payments_create', 'payments_read_own'
            ],
            'verzoek_lid': ['members_self_read', 'members_self_create', 'members_self_update']  # Applicants can only manage their application
            # Note: Region roles (Regio_*) don't grant permissions by themselves
        }
        
        # Get all permissions for user's roles
        user_permissions = set()
        for role in user_roles:
            if role in role_permissions:
                permissions = role_permissions[role]
                if '*' in permissions:
                    return True, None  # Full access
                user_permissions.update(permissions)
        
        # Check if user has required permissions
        if not required_permissions or any(perm in user_permissions for perm in required_permissions):
            return True, None
        
        # Permission denied - log and return error
        log_permission_denial(user_email, user_roles, required_permissions, list(user_permissions), resource_context)
        
        return False, {
            'statusCode': 403,
            'headers': cors_headers(),
            'body': json.dumps({
                'error': 'Access denied: Insufficient permissions',
                'required_permissions': required_permissions,
                'user_roles': user_roles
            })
        }
        
    except Exception as e:
        print(f"Error validating permissions: {str(e)}")
        return False, {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Error validating permissions'})
        }


def log_permission_denial(user_email, user_roles, required_permissions, user_permissions, resource_context=None):
    """
    Log permission denial for security monitoring (NEW ROLE STRUCTURE ONLY)
    
    Args:
        user_email (str): Email of user attempting access
        user_roles (list): User's roles (permission + region structure)
        required_permissions (list): Permissions that were required
        user_permissions (list): Permissions the user actually has
        resource_context (dict): Optional context about the resource
    """
    # Extract role structure information for monitoring
    permission_roles = [role for role in user_roles if not role.startswith('Regio_') and role not in ['hdcnLeden', 'verzoek_lid']]
    region_roles = [role for role in user_roles if role.startswith('Regio_')]
    
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'event_type': 'PERMISSION_DENIED',
        'user_email': user_email,
        'user_roles': user_roles,
        'permission_roles': permission_roles,  # NEW: Track permission roles separately
        'region_roles': region_roles,          # NEW: Track region roles separately
        'required_permissions': required_permissions,
        'user_permissions': user_permissions,
        'resource_context': resource_context,
        'severity': 'WARNING',
        'role_structure_version': '2.0'        # NEW: Track role structure version
    }
    
    print(f"SECURITY_AUDIT: {json.dumps(log_entry)}")
    print(f"Permission denied: User {user_email} (permission roles: {permission_roles}, region roles: {region_roles}) "
          f"attempted to access resource requiring {required_permissions} but only has {user_permissions}")


def log_successful_access(user_email, user_roles, operation, resource_context=None):
    """
    Log successful access for audit trail (NEW ROLE STRUCTURE ONLY)
    
    Args:
        user_email (str): Email of user performing operation
        user_roles (list): User's roles (permission + region structure)
        operation (str): Operation being performed
        resource_context (dict): Optional context about the resource
    """
    # Extract role structure information for monitoring
    permission_roles = [role for role in user_roles if not role.startswith('Regio_') and role not in ['hdcnLeden', 'verzoek_lid']]
    region_roles = [role for role in user_roles if role.startswith('Regio_')]
    
    # Determine access level for monitoring
    access_level = 'basic_member'
    if any(role in ['System_CRUD', 'System_User_Management'] for role in user_roles):
        access_level = 'system_admin'
    elif 'Regio_All' in user_roles:
        access_level = 'national_admin'
    elif region_roles:
        access_level = 'regional_admin'
    
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'event_type': 'ACCESS_GRANTED',
        'user_email': user_email,
        'user_roles': user_roles,
        'permission_roles': permission_roles,  # NEW: Track permission roles separately
        'region_roles': region_roles,          # NEW: Track region roles separately
        'access_level': access_level,          # NEW: Track access level for monitoring
        'operation': operation,
        'resource_context': resource_context,
        'severity': 'INFO',
        'role_structure_version': '2.0'        # NEW: Track role structure version
    }
    
    print(f"ACCESS_AUDIT: {json.dumps(log_entry)}")
    print(f"Access granted: User {user_email} (permission roles: {permission_roles}, region roles: {region_roles}, "
          f"access level: {access_level}) performed operation: {operation}")


def log_regional_access_event(user_email, user_roles, data_region, access_granted, reason, resource_context=None):
    """
    Log regional data access events for compliance and monitoring (NEW ROLE STRUCTURE ONLY)
    
    Args:
        user_email (str): Email of user attempting access
        user_roles (list): User's roles (permission + region structure)
        data_region (str): Region of the data being accessed
        access_granted (bool): Whether access was granted
        reason (str): Reason for access decision
        resource_context (dict): Optional context about the resource
    """
    # Extract role structure information for monitoring
    permission_roles = [role for role in user_roles if not role.startswith('Regio_') and role not in ['hdcnLeden', 'verzoek_lid']]
    region_roles = [role for role in user_roles if role.startswith('Regio_')]
    
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'event_type': 'REGIONAL_ACCESS_CHECK',
        'user_email': user_email,
        'user_roles': user_roles,
        'permission_roles': permission_roles,
        'region_roles': region_roles,
        'data_region': data_region,
        'access_granted': access_granted,
        'reason': reason,
        'resource_context': resource_context,
        'severity': 'INFO' if access_granted else 'WARNING',
        'role_structure_version': '2.0'
    }
    
    print(f"REGIONAL_ACCESS_AUDIT: {json.dumps(log_entry)}")
    if access_granted:
        print(f"Regional access granted: User {user_email} (region roles: {region_roles}) "
              f"accessed data from region: {data_region} - {reason}")
    else:
        print(f"Regional access denied: User {user_email} (region roles: {region_roles}) "
              f"attempted to access data from region: {data_region} - {reason}")


def log_role_structure_validation(user_email, user_roles, validation_result, validation_context=None):
    """
    Log role structure validation events for monitoring (NEW ROLE STRUCTURE ONLY)
    
    Args:
        user_email (str): Email of user being validated
        user_roles (list): User's roles (permission + region structure)
        validation_result (dict): Result of role structure validation
        validation_context (dict): Optional context about the validation
    """
    # Extract role structure information for monitoring
    permission_roles = [role for role in user_roles if not role.startswith('Regio_') and role not in ['hdcnLeden', 'verzoek_lid']]
    region_roles = [role for role in user_roles if role.startswith('Regio_')]
    
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'event_type': 'ROLE_STRUCTURE_VALIDATION',
        'user_email': user_email,
        'user_roles': user_roles,
        'permission_roles': permission_roles,
        'region_roles': region_roles,
        'validation_result': validation_result,
        'validation_context': validation_context,
        'severity': 'INFO' if validation_result.get('valid', False) else 'WARNING',
        'role_structure_version': '2.0'
    }
    
    print(f"ROLE_VALIDATION_AUDIT: {json.dumps(log_entry)}")
    if validation_result.get('valid', False):
        print(f"Role structure valid: User {user_email} has valid permission + region structure")
    else:
        print(f"Role structure invalid: User {user_email} has invalid role structure - {validation_result.get('reason', 'Unknown')}")


def cors_headers():
    """
    Standard CORS headers for all API responses - matches template.yaml Global CORS configuration
    """
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "OPTIONS,GET,POST,PUT,DELETE,PATCH",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,X-Enhanced-Groups,x-requested-with",
        "Access-Control-Allow-Credentials": "false"
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