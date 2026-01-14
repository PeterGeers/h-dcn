"""
Local copy of shared authentication utilities for Lambda handlers
This is a fallback when the shared module is not available via Lambda layers

Updated for new role structure - legacy _All roles have been removed as part of cleanup.
All users should now use Permission + Region role combinations.

STANDARDIZED VERSION - Consistent with backend/shared/auth_utils.py
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
        
        # Define role-to-permission mappings (STANDARDIZED with shared auth_utils.py)
        role_permissions = {
            # Administrative roles
            'System_CRUD': ['*'],  # Full system access (new role structure)
            'System_User_Management': ['users_manage', 'roles_assign'],
            'System_Logs_Read': ['logs_read', 'audit_read'],
            
            # NEW SIMPLIFIED ROLE STRUCTURE
            # Permission roles (what you can do)
            'Members_CRUD': ['members_create', 'members_read', 'members_update', 'members_delete', 'members_export'],
            'Members_Read': ['members_read', 'members_list'],  # Removed members_export - read-only users shouldn't export
            'Members_Export': ['members_export'],  # Separate export permission
            'Events_CRUD': ['events_create', 'events_read', 'events_update', 'events_delete', 'events_export'],
            'Events_Read': ['events_read', 'events_list'],
            'Events_Export': ['events_export'],
            'Products_CRUD': ['products_create', 'products_read', 'products_update', 'products_delete', 'products_export'],
            'Products_Read': ['products_read', 'products_list'],
            'Products_Export': ['products_export'],
            'Communication_CRUD': ['communication_create', 'communication_read', 'communication_update', 'communication_delete'],
            'Communication_Read': ['communication_read'],
            'Communication_Export': ['communication_export'],
            
            # Region roles (where you can access) - these don't grant permissions by themselves
            # They are combined with permission roles to determine regional access
            'Regio_All': [],  # Access to all regions (combined with permission roles)
            'Regio_Noord-Holland': [],
            'Regio_Zuid-Holland': [],
            'Regio_Friesland': [],
            'Regio_Utrecht': [],
            'Regio_Oost': [],
            'Regio_Limburg': [],
            'Regio_Groningen/Drenthe': [],
            'Regio_Brabant/Zeeland': [],
            'Regio_Duitsland': [],
            
            # Other roles
            'Members_Status_Approve': ['members_status_change'],
            
            # Webshop
            'Webshop_Management': ['products_create', 'products_read', 'products_update', 'products_delete', 'orders_manage'],
            
            # Organizational roles
            'National_Chairman': ['members_read', 'events_read', 'communication_read', 'reports_read'],
            'National_Secretary': ['members_read', 'events_read', 'communication_create', 'communication_read'],
            'National_Treasurer': ['members_read', 'payments_read', 'financial_reports'],
            
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


def validate_permissions_with_regions(user_roles, required_permissions, user_email=None, resource_context=None):
    """
    Enhanced permission validation that supports the new permission + region role structure
    
    Args:
        user_roles (list): List of user's roles from credentials
        required_permissions (list or str): Required permission(s) for the operation
        user_email (str): Optional user email for logging
        resource_context (dict): Optional context about the resource being accessed
                                 Should include 'region' field for regional filtering
        
    Returns:
        tuple: (is_authorized, error_response, regional_access_info)
               If authorized: (True, None, regional_info_dict)
               If not authorized: (False, error_response_dict, None)
    """
    try:
        # Convert single permission to list
        if isinstance(required_permissions, str):
            required_permissions = [required_permissions]
        
        # Check for admin roles that have full access
        admin_roles = ['System_CRUD', 'System_User_Management']
        if any(role in user_roles for role in admin_roles):
            regional_info = determine_regional_access(user_roles, resource_context)
            return True, None, regional_info
        
        # Check for legacy _All roles (backward compatibility)
        legacy_all_roles = [role for role in user_roles if role.endswith('_All')]
        if legacy_all_roles:
            # Validate permissions using existing function for legacy roles
            is_authorized, error_response = validate_permissions(
                user_roles, required_permissions, user_email, resource_context
            )
            if is_authorized:
                regional_info = determine_regional_access(user_roles, resource_context)
                return True, None, regional_info
            else:
                return False, error_response, None
        
        # NEW ROLE STRUCTURE VALIDATION
        # For new role structure, we need BOTH permission role AND region role
        
        # Check if user has required permissions
        is_authorized, error_response = validate_permissions(
            user_roles, required_permissions, user_email, resource_context
        )
        
        if not is_authorized:
            return False, error_response, None
        
        # For new role structure, also check that user has region roles
        # Exception: System roles don't need region roles
        system_roles = ['System_CRUD', 'System_User_Management', 'System_Logs_Read']
        has_system_role = any(role in user_roles for role in system_roles)
        
        if not has_system_role:
            # Check if user has any region role
            region_roles = [role for role in user_roles if role.startswith('Regio_')]
            if not region_roles:
                # User has permission but no region - this is incomplete for new role structure
                error_msg = 'Access denied: Permission requires region assignment'
                error_details = {
                    'error': error_msg,
                    'required_structure': 'Permission (e.g., Members_CRUD) + Region (e.g., Regio_All)',
                    'user_roles': user_roles,
                    'missing': 'Region assignment (Regio_All, Regio_Noord-Holland, etc.)'
                }
                
                log_permission_denial(
                    user_email=user_email,
                    user_roles=user_roles,
                    required_permissions=required_permissions + ['region_role'],
                    user_permissions=['permission_role_present', 'region_role_missing'],
                    resource_context=resource_context
                )
                
                return False, {
                    'statusCode': 403,
                    'headers': cors_headers(),
                    'body': json.dumps(error_details)
                }, None
        
        # If we get here, user has both permission and region roles (or is system user)
        regional_info = determine_regional_access(user_roles, resource_context)
        return True, None, regional_info
        
    except Exception as e:
        print(f"Error validating permissions with regions: {str(e)}")
        return False, {
            'statusCode': 500,
            'headers': cors_headers(),
            'body': json.dumps({'error': 'Error validating permissions'})
        }, None


def determine_regional_access(user_roles, resource_context=None):
    """
    Determine what regional access the user has based on their roles
    
    Args:
        user_roles (list): List of user's roles
        resource_context (dict): Optional context about the resource
        
    Returns:
        dict: Regional access information
    """
    regional_info = {
        'has_full_access': False,
        'allowed_regions': [],
        'access_type': 'none'
    }
    
    # Check for full access roles
    full_access_roles = ['System_CRUD', 'System_User_Management']
    if any(role in user_roles for role in full_access_roles):
        regional_info.update({
            'has_full_access': True,
            'allowed_regions': ['all'],
            'access_type': 'admin'
        })
        return regional_info
    
    # Check for Regio_All access
    if 'Regio_All' in user_roles:
        regional_info.update({
            'has_full_access': True,
            'allowed_regions': ['all'],
            'access_type': 'national'
        })
        return regional_info
    
    # Check for specific regional roles
    region_roles = [role for role in user_roles if role.startswith('Regio_') and role != 'Regio_All']
    if region_roles:
        # Extract region names from roles (e.g., 'Regio_Groningen/Drenthe' -> 'Groningen/Drenthe')
        allowed_regions = [role.replace('Regio_', '') for role in region_roles]
        regional_info.update({
            'has_full_access': False,
            'allowed_regions': allowed_regions,
            'access_type': 'regional'
        })
        return regional_info
    
    # Check for legacy _All roles (backward compatibility)
    legacy_all_roles = [role for role in user_roles if role.endswith('_All')]
    if legacy_all_roles:
        regional_info.update({
            'has_full_access': True,
            'allowed_regions': ['all'],
            'access_type': 'legacy_all'
        })
        return regional_info
    
    return regional_info


def check_regional_data_access(user_roles, data_region, user_email=None):
    """
    Check if user can access data from a specific region
    
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
        return True, f"Full access via {regional_info['access_type']}"
    
    # Regional users can only access their assigned regions
    if regional_info['access_type'] == 'regional':
        if data_region in regional_info['allowed_regions']:
            return True, f"Regional access to {data_region}"
        else:
            if user_email:
                print(f"REGIONAL_ACCESS_DENIED: User {user_email} (regions: {regional_info['allowed_regions']}) "
                      f"attempted to access data from region: {data_region}")
            return False, f"Access denied: User can only access regions {regional_info['allowed_regions']}"
    
    # No regional access
    return False, "No regional access permissions"


def get_user_accessible_regions(user_roles):
    """
    Get list of regions the user can access
    
    Args:
        user_roles (list): User's roles
        
    Returns:
        list: List of accessible region names, or ['all'] for full access
    """
    regional_info = determine_regional_access(user_roles)
    return regional_info['allowed_regions']


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


# ============================================================================
# VALIDATION UTILITIES - Helper functions for common role checking patterns
# ============================================================================

def is_admin_user(user_roles):
    """
    Check if user has admin privileges
    
    Args:
        user_roles (list): User's roles
        
    Returns:
        tuple: (is_admin, admin_roles_found)
    """
    # Only include roles that actually exist in Cognito (verified 2026-01-08)
    # Note: Legacy _All roles have been removed as part of role migration cleanup
    admin_roles = ['System_CRUD', 'System_User_Management']
    
    admin_roles_found = [role for role in user_roles if role in admin_roles]
    return len(admin_roles_found) > 0, admin_roles_found


def has_any_role(user_roles, required_roles):
    """
    Check if user has any of the required roles
    
    Args:
        user_roles (list): User's roles
        required_roles (list): List of roles to check for
        
    Returns:
        tuple: (has_role, matching_roles)
    """
    matching_roles = [role for role in user_roles if role in required_roles]
    return len(matching_roles) > 0, matching_roles


def has_all_roles(user_roles, required_roles):
    """
    Check if user has all of the required roles
    
    Args:
        user_roles (list): User's roles
        required_roles (list): List of roles that must all be present
        
    Returns:
        tuple: (has_all_roles, missing_roles)
    """
    missing_roles = [role for role in required_roles if role not in user_roles]
    return len(missing_roles) == 0, missing_roles


def has_permission_and_region_access(user_roles, required_permission_type, required_regions=None):
    """
    Check if user has both permission role and appropriate region access
    
    Args:
        user_roles (list): User's roles
        required_permission_type (str): Permission type (e.g., 'Members_CRUD', 'Events_Read')
        required_regions (list): Optional list of required regions. If None, any region access is sufficient
        
    Returns:
        dict: {
            'has_access': bool,
            'has_permission': bool,
            'has_region_access': bool,
            'permission_roles': list,
            'region_roles': list,
            'access_type': str,  # 'admin', 'legacy', 'new_structure', 'denied'
            'message': str
        }
    """
    # Check for admin access first
    is_admin, admin_roles_found = is_admin_user(user_roles)
    if is_admin:
        return {
            'has_access': True,
            'has_permission': True,
            'has_region_access': True,
            'permission_roles': [],
            'region_roles': [],
            'access_type': 'admin',
            'message': f'Admin access via: {admin_roles_found}'
        }
    
    # Check for legacy _All roles
    legacy_role = f"{required_permission_type}_All"
    if legacy_role in user_roles:
        return {
            'has_access': True,
            'has_permission': True,
            'has_region_access': True,
            'permission_roles': [legacy_role],
            'region_roles': [],
            'access_type': 'legacy',
            'message': f'Legacy access via: {legacy_role} (migration recommended)'
        }
    
    # Check for new role structure
    has_permission_role = required_permission_type in user_roles
    region_roles = [role for role in user_roles if role.startswith('Regio_')]
    has_region_role = len(region_roles) > 0
    
    # Check specific region requirements if provided
    region_access_valid = True
    if required_regions and not ('Regio_All' in user_roles):
        # User needs specific regions and doesn't have Regio_All
        user_regions = [role.replace('Regio_', '') for role in region_roles]
        region_access_valid = any(region in user_regions for region in required_regions)
    
    has_new_structure_access = has_permission_role and has_region_role and region_access_valid
    
    if has_new_structure_access:
        return {
            'has_access': True,
            'has_permission': True,
            'has_region_access': True,
            'permission_roles': [required_permission_type],
            'region_roles': region_roles,
            'access_type': 'new_structure',
            'message': f'New structure access: {required_permission_type} + {region_roles}'
        }
    
    # Determine what's missing
    missing_parts = []
    if not has_permission_role:
        missing_parts.append(f'permission role ({required_permission_type})')
    if not has_region_role:
        missing_parts.append('region role (Regio_*)')
    elif required_regions and not region_access_valid:
        missing_parts.append(f'required region access ({required_regions})')
    
    return {
        'has_access': False,
        'has_permission': has_permission_role,
        'has_region_access': has_region_role and region_access_valid,
        'permission_roles': [required_permission_type] if has_permission_role else [],
        'region_roles': region_roles,
        'access_type': 'denied',
        'message': f'Access denied: missing {", ".join(missing_parts)}'
    }


def can_access_resource_region(user_roles, resource_region):
    """
    Check if user can access a resource from a specific region
    
    Args:
        user_roles (list): User's roles
        resource_region (str): Region of the resource (e.g., 'Noord-Holland', 'Groningen/Drenthe')
        
    Returns:
        dict: {
            'can_access': bool,
            'access_type': str,  # 'admin', 'national', 'regional', 'denied'
            'user_regions': list,
            'message': str
        }
    """
    # Check for admin access
    is_admin, admin_roles_found = is_admin_user(user_roles)
    if is_admin:
        return {
            'can_access': True,
            'access_type': 'admin',
            'user_regions': ['all'],
            'message': f'Admin access via: {admin_roles_found}'
        }
    
    # Check for national access (Regio_All)
    if 'Regio_All' in user_roles:
        return {
            'can_access': True,
            'access_type': 'national',
            'user_regions': ['all'],
            'message': 'National access via Regio_All'
        }
    
    # Check for specific regional access
    region_roles = [role for role in user_roles if role.startswith('Regio_') and role != 'Regio_All']
    user_regions = [role.replace('Regio_', '') for role in region_roles]
    
    if resource_region in user_regions:
        return {
            'can_access': True,
            'access_type': 'regional',
            'user_regions': user_regions,
            'message': f'Regional access to {resource_region}'
        }
    
    # No access
    return {
        'can_access': False,
        'access_type': 'denied',
        'user_regions': user_regions,
        'message': f'Access denied: user regions {user_regions} do not include {resource_region}'
    }


def validate_crud_access(user_roles, resource_type, operation='read', resource_region=None):
    """
    Validate CRUD access for a specific resource type and operation
    
    Args:
        user_roles (list): User's roles
        resource_type (str): Type of resource ('Members', 'Events', 'Products', 'Communication')
        operation (str): Operation type ('create', 'read', 'update', 'delete', 'export')
        resource_region (str): Optional region of the resource being accessed
        
    Returns:
        dict: {
            'has_access': bool,
            'access_type': str,
            'required_permission': str,
            'regional_access': dict,
            'message': str
        }
    """
    # Map operations to permission roles
    operation_to_role = {
        'create': f'{resource_type}_CRUD',
        'read': f'{resource_type}_Read',
        'update': f'{resource_type}_CRUD',
        'delete': f'{resource_type}_CRUD',
        'export': f'{resource_type}_Export'
    }
    
    # CRUD includes all operations
    crud_role = f'{resource_type}_CRUD'
    required_permission = operation_to_role.get(operation, f'{resource_type}_Read')
    
    # Check if user has CRUD (which includes all operations) or specific permission
    possible_permissions = [crud_role, required_permission]
    
    access_result = None
    for permission in possible_permissions:
        result = has_permission_and_region_access(user_roles, permission)
        if result['has_access']:
            access_result = result
            break
    
    if not access_result:
        # Try the last permission for error details
        access_result = has_permission_and_region_access(user_roles, required_permission)
    
    # Check regional access if resource has a region
    regional_access = {'can_access': True, 'message': 'No regional restriction'}
    if resource_region and access_result['has_access']:
        regional_access = can_access_resource_region(user_roles, resource_region)
        if not regional_access['can_access']:
            access_result['has_access'] = False
            access_result['message'] += f" + {regional_access['message']}"
    
    return {
        'has_access': access_result['has_access'] and regional_access['can_access'],
        'access_type': access_result['access_type'],
        'required_permission': required_permission,
        'regional_access': regional_access,
        'message': access_result['message']
    }