"""
Permission utility functions for hdcn_cognito_admin.

Provides field-level permission validation, user permission lookups,
role permission checks, and role summary information.
"""

from shared.role_permissions import (
    DEFAULT_ROLE_PERMISSIONS,
    has_permission,
    can_edit_field,
    ADMINISTRATIVE_FIELDS,
    PERSONAL_FIELDS,
    MOTORCYCLE_FIELDS
)


def validate_field_permissions(user_roles, field_name, target_user_id, requesting_user_id):
    """
    Validate if a user can edit a specific field based on their roles and field type
    
    Args:
        user_roles (list): List of user's role names
        field_name (str): Name of the field to validate
        target_user_id (str): ID of the user whose record is being edited
        requesting_user_id (str): ID of the user making the request
        
    Returns:
        dict: Validation result with 'allowed' boolean and 'reason' string
    """
    try:
        is_own_record = target_user_id == requesting_user_id
        
        # Use the centralized field permission function
        can_edit = can_edit_field(user_roles, field_name, is_own_record)
        
        if can_edit:
            if field_name in ADMINISTRATIVE_FIELDS:
                return {
                    'allowed': True,
                    'reason': 'User has administrative permissions to edit this field'
                }
            elif is_own_record and (field_name in PERSONAL_FIELDS or field_name in MOTORCYCLE_FIELDS):
                return {
                    'allowed': True,
                    'reason': 'User can edit their own personal/motorcycle information'
                }
            else:
                return {
                    'allowed': True,
                    'reason': 'User has sufficient permissions to edit this field'
                }
        else:
            if field_name in ADMINISTRATIVE_FIELDS:
                return {
                    'allowed': False,
                    'reason': 'Administrative fields require System_User_Management role'
                }
            elif not is_own_record and (field_name in PERSONAL_FIELDS or field_name in MOTORCYCLE_FIELDS):
                return {
                    'allowed': False,
                    'reason': 'Can only edit personal/motorcycle fields for your own record'
                }
            else:
                return {
                    'allowed': False,
                    'reason': 'Insufficient permissions to edit this field'
                }
                
    except Exception as e:
        print(f"Error validating field permissions: {str(e)}")
        return {
            'allowed': False,
            'reason': 'Error validating field permissions'
        }


def get_user_field_permissions(user_roles, target_user_id, requesting_user_id):
    """
    Get field-level permissions for a user
    
    Args:
        user_roles (list): List of user's role names
        target_user_id (str): ID of the user whose record is being accessed
        requesting_user_id (str): ID of the user making the request
        
    Returns:
        dict: Field permissions organized by category
    """
    try:
        is_own_record = target_user_id == requesting_user_id
        
        field_permissions = {
            'personal_fields': {},
            'motorcycle_fields': {},
            'administrative_fields': {}
        }
        
        # Check personal fields
        for field in PERSONAL_FIELDS:
            validation = validate_field_permissions(user_roles, field, target_user_id, requesting_user_id)
            field_permissions['personal_fields'][field] = validation
        
        # Check motorcycle fields
        for field in MOTORCYCLE_FIELDS:
            validation = validate_field_permissions(user_roles, field, target_user_id, requesting_user_id)
            field_permissions['motorcycle_fields'][field] = validation
        
        # Check administrative fields
        for field in ADMINISTRATIVE_FIELDS:
            validation = validate_field_permissions(user_roles, field, target_user_id, requesting_user_id)
            field_permissions['administrative_fields'][field] = validation
        
        return field_permissions
        
    except Exception as e:
        print(f"Error getting user field permissions: {str(e)}")
        return {
            'personal_fields': {},
            'motorcycle_fields': {},
            'administrative_fields': {}
        }


def check_role_permission(user_roles, required_permission):
    """
    Check if user has a specific permission based on their roles
    
    Args:
        user_roles (list): List of user's role names
        required_permission (str): Permission to check for
        
    Returns:
        dict: Permission check result with 'allowed' boolean and details
    """
    try:
        # Use the centralized permission checking function
        has_perm = has_permission(user_roles, required_permission)
        
        if has_perm:
            # Find which roles provide this permission
            providing_roles = []
            for role in user_roles:
                role_permissions = DEFAULT_ROLE_PERMISSIONS.get(role, [])
                if required_permission in role_permissions:
                    providing_roles.append(role)
            
            return {
                'allowed': True,
                'permission': required_permission,
                'providing_roles': providing_roles,
                'user_roles': user_roles
            }
        else:
            return {
                'allowed': False,
                'permission': required_permission,
                'user_roles': user_roles,
                'reason': f'User does not have required permission: {required_permission}'
            }
            
    except Exception as e:
        print(f"Error checking role permission: {str(e)}")
        return {
            'allowed': False,
            'permission': required_permission,
            'error': str(e)
        }


def get_role_summary(role_name):
    """
    Get summary information about a specific role
    
    Args:
        role_name (str): Name of the role
        
    Returns:
        dict: Role summary with permissions and metadata
    """
    try:
        role_permissions = DEFAULT_ROLE_PERMISSIONS.get(role_name, [])
        
        if not role_permissions:
            return {
                'role_name': role_name,
                'exists': False,
                'permissions': [],
                'permission_count': 0
            }
        
        # Categorize permissions
        permission_categories = {
            'members': [],
            'events': [],
            'products': [],
            'communication': [],
            'system': [],
            'webshop': [],
            'cognito': []
        }
        
        for permission in role_permissions:
            category = permission.split(':')[0]
            if category in permission_categories:
                permission_categories[category].append(permission)
            else:
                if 'other' not in permission_categories:
                    permission_categories['other'] = []
                permission_categories['other'].append(permission)
        
        return {
            'role_name': role_name,
            'exists': True,
            'permissions': role_permissions,
            'permission_count': len(role_permissions),
            'permission_categories': permission_categories,
            'is_administrative': any(perm.startswith('system:') or perm.startswith('cognito:') for perm in role_permissions),
            'is_basic_member': role_name == 'hdcnLeden'
        }
        
    except Exception as e:
        print(f"Error getting role summary for {role_name}: {str(e)}")
        return {
            'role_name': role_name,
            'exists': False,
            'error': str(e)
        }
