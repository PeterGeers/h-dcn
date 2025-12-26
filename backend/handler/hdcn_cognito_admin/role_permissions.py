"""
Role Permission Mapping Constants for H-DCN Cognito Authentication

This module defines the mapping between H-DCN organizational roles and their corresponding permissions.
Based on the design document permission matrix and organizational structure.
"""

# Default role permissions mapping based on H-DCN organizational structure
DEFAULT_ROLE_PERMISSIONS = {
    # Basic member role - all authenticated members get this role
    'hdcnLeden': [
        'members:read_own',
        'members:update_own_personal',
        'members:update_own_motorcycle', 
        'events:read_public',
        'products:browse_catalog',
        'webshop:access'
    ],
    
    # Member management roles
    'Members_CRUD_All': [
        'members:read_all',
        'members:create',
        'members:update_all',
        'members:delete',
        'members:update_status',
        'members:export_all',
        'members:update_administrative'
    ],
    'Members_Read_All': [
        'members:read_all',
        'members:export_all'
    ],
    'Members_Status_Approve': [
        'members:read_all',
        'members:update_status',
        'members:approve_status'
    ],
    
    # Event management roles
    'Events_Read_All': [
        'events:read_all',
        'events:export_all'
    ],
    'Events_CRUD_All': [
        'events:read_all',
        'events:create',
        'events:update_all',
        'events:delete',
        'events:export_all'
    ],
    
    # Product management roles
    'Products_Read_All': [
        'products:read_all',
        'products:export_all'
    ],
    'Products_CRUD_All': [
        'products:read_all',
        'products:create',
        'products:update_all',
        'products:delete',
        'products:export_all'
    ],
    
    # Communication roles
    'Communication_Read_All': [
        'communication:read_all'
    ],
    'Communication_Export_All': [
        'communication:read_all',
        'communication:export_all'
    ],
    'Communication_CRUD_All': [
        'communication:read_all',
        'communication:create',
        'communication:update_all',
        'communication:delete',
        'communication:export_all'
    ],
    
    # System administration roles
    'System_User_Management': [
        'system:user_management',
        'system:role_assignment',
        'cognito:admin_access'
    ],
    'System_Logs_Read': [
        'system:logs_read',
        'system:audit_read'
    ],
    'System_CRUD_All': [
        'system:user_management',
        'system:role_assignment',
        'system:logs_read',
        'system:audit_read',
        'system:configuration',
        'system:maintenance'
    ]
}

# Regional permission templates - can be used to generate region-specific roles
REGIONAL_PERMISSION_TEMPLATES = {
    'regional_chairman': [
        'members:read_own_region',
        'members:export_own_region',
        'events:read_own_region',
        'events:create_own_region',
        'events:update_own_region',
        'events:delete_own_region',
        'products:read_all',
        'communication:export_own_region'
    ],
    'regional_secretary': [
        'members:read_own_region',
        'members:export_own_region',
        'events:read_own_region',
        'products:read_all',
        'communication:export_own_region'
    ],
    'regional_treasurer': [
        'members:read_own_region_financial',
        'events:read_own_region_financial',
        'products:read_financial_only'
    ],
    'regional_volunteer': [
        'members:read_own_region_basic',
        'events:read_own_region',
        'products:read_all'
    ]
}

# Organizational role combinations based on H-DCN structure
ORGANIZATIONAL_ROLE_COMBINATIONS = {
    'member_administration': [
        'Members_CRUD_All',
        'Events_Read_All', 
        'Products_Read_All',
        'Communication_Read_All',
        'System_User_Management'
    ],
    'national_chairman': [
        'Members_Read_All',
        'Members_Status_Approve',
        'Events_Read_All',
        'Products_Read_All', 
        'Communication_Read_All',
        'System_Logs_Read'
    ],
    'national_secretary': [
        'Members_Read_All',
        'Members_Export_All',
        'Events_Read_All',
        'Events_Export_All',
        'Products_Read_All',
        'Communication_Export_All',
        'System_Logs_Read'
    ],
    'national_treasurer': [
        'Members_Read_Financial',
        'Events_Read_Financial',
        'Products_Read_Financial'
    ],
    'webmaster': [
        'Members_Read_All',
        'Events_CRUD_All',
        'Products_CRUD_All',
        'Communication_CRUD_All',
        'System_CRUD_All'
    ],
    'tour_commissioner': [
        'Members_Read_All',
        'Members_Export_All',
        'Events_CRUD_All',
        'Products_Read_All',
        'Communication_Export_All'
    ],
    'club_magazine_editorial': [
        'Members_Read_All',
        'Members_Export_All',
        'Events_Read_All',
        'Products_Read_All',
        'Communication_CRUD_All'
    ],
    'webshop_management': [
        'Members_Read_Basic',
        'Events_Read_All',
        'Products_CRUD_All',
        'Communication_Read_All'
    ]
}

# Administrative field permissions - fields that require special permissions to modify
ADMINISTRATIVE_FIELDS = [
    'member_id',
    'lidnummer', 
    'lidmaatschap',
    'status',
    'tijdstempel',
    'aanmeldingsjaar',
    'regio',
    'clubblad',
    'bankrekeningnummer',
    'datum_ondertekening',
    'created_at',
    'updated_at'
]

# Personal fields - editable by members for their own record
PERSONAL_FIELDS = [
    'voornaam',
    'achternaam', 
    'tussenvoegsel',
    'initialen',
    'telefoon',
    'straat',
    'postcode',
    'woonplaats',
    'land',
    'email',
    'nieuwsbrief',
    'geboortedatum',
    'geslacht',
    'wiewatwaar'
]

# Motorcycle fields - editable by members for their own record  
MOTORCYCLE_FIELDS = [
    'bouwjaar',
    'motormerk',
    'motortype', 
    'kenteken'
]

def get_role_permissions(role_name):
    """
    Get permissions for a specific role
    
    Args:
        role_name (str): Name of the role
        
    Returns:
        list: List of permissions for the role, empty list if role not found
    """
    return DEFAULT_ROLE_PERMISSIONS.get(role_name, [])

def get_combined_permissions(roles):
    """
    Get combined permissions from multiple roles
    
    Args:
        roles (list): List of role names
        
    Returns:
        list: Sorted list of unique permissions from all roles
    """
    if not roles:
        return []
        
    all_permissions = set()
    for role in roles:
        role_permissions = get_role_permissions(role)
        all_permissions.update(role_permissions)
        
    return sorted(list(all_permissions))

def has_permission(roles, required_permission):
    """
    Check if user with given roles has a specific permission
    
    Args:
        roles (list): List of user's role names
        required_permission (str): Permission to check for
        
    Returns:
        bool: True if user has the permission, False otherwise
    """
    user_permissions = get_combined_permissions(roles)
    return required_permission in user_permissions

def can_edit_field(roles, field_name, is_own_record=False):
    """
    Check if user can edit a specific field based on their roles
    
    Args:
        roles (list): List of user's role names
        field_name (str): Name of the field to check
        is_own_record (bool): Whether this is the user's own record
        
    Returns:
        bool: True if user can edit the field, False otherwise
    """
    user_permissions = get_combined_permissions(roles)
    
    # Special handling for status field - only Members_CRUD_All role can modify
    if field_name == 'status':
        return 'Members_CRUD_All' in roles
    
    # Administrative fields require special permissions
    if field_name in ADMINISTRATIVE_FIELDS:
        return 'members:update_administrative' in user_permissions
    
    # Personal and motorcycle fields can be edited by user for own record
    if field_name in PERSONAL_FIELDS:
        if is_own_record and 'members:update_own_personal' in user_permissions:
            return True
        # Or if user has admin permissions
        return 'members:update_all' in user_permissions
    
    if field_name in MOTORCYCLE_FIELDS:
        if is_own_record and 'members:update_own_motorcycle' in user_permissions:
            return True
        # Or if user has admin permissions
        return 'members:update_all' in user_permissions
    
    # For other fields, require admin permissions
    return 'members:update_all' in user_permissions

def get_regional_permissions(region_id, role_template):
    """
    Generate regional permissions for a specific region
    
    Args:
        region_id (str): Region identifier (e.g., "1", "2", etc.)
        role_template (str): Template name from REGIONAL_PERMISSION_TEMPLATES
        
    Returns:
        list: List of region-specific permissions
    """
    template_permissions = REGIONAL_PERMISSION_TEMPLATES.get(role_template, [])
    
    # Replace 'own_region' with specific region ID
    regional_permissions = []
    for permission in template_permissions:
        if 'own_region' in permission:
            regional_permission = permission.replace('own_region', f'region_{region_id}')
            regional_permissions.append(regional_permission)
        else:
            regional_permissions.append(permission)
            
    return regional_permissions