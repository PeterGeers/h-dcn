"""
Role Permission Mapping Constants for H-DCN Cognito Authentication

This module defines the mapping between H-DCN organizational roles and their corresponding permissions.
Updated for the new permission + region role structure.
"""

# NEW ROLE STRUCTURE: Permission + Region Role Combinations
# Users need BOTH a permission role (what they can do) AND a region role (where they can do it)
# Exception: System admin roles don't need region roles

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
    
    # NEW PERMISSION ROLES (What you can do) - Must be combined with region roles
    # Member management permissions
    'Members_CRUD': [
        'members_create',
        'members_read', 
        'members_update',
        'members_delete',
        'members_export'
    ],
    'Members_Read': [
        'members_read',
        'members_list'
    ],
    'Members_Export': [
        'members_export'
    ],
    'Members_Status_Approve': [
        'members_read',
        'members_update_status',
        'members_approve_status'
    ],
    
    # Event management permissions
    'Events_CRUD': [
        'events_create',
        'events_read',
        'events_update', 
        'events_delete',
        'events_export'
    ],
    'Events_Read': [
        'events_read',
        'events_list'
    ],
    'Events_Export': [
        'events_export'
    ],
    
    # Product management permissions
    'Products_CRUD': [
        'products_create',
        'products_read',
        'products_update',
        'products_delete', 
        'products_export'
    ],
    'Products_Read': [
        'products_read',
        'products_list'
    ],
    'Products_Export': [
        'products_export'
    ],
    
    # Communication permissions
    'Communication_CRUD': [
        'communication_create',
        'communication_read',
        'communication_update',
        'communication_delete'
    ],
    'Communication_Read': [
        'communication_read'
    ],
    'Communication_Export': [
        'communication_export'
    ],
    
    # REGION ROLES (Where you can access) - Combined with permission roles
    # These don't grant permissions by themselves, they define regional scope
    'Regio_All': [],  # Access to all regions
    'Regio_Noord-Holland': [],
    'Regio_Zuid-Holland': [],
    'Regio_Friesland': [],
    'Regio_Utrecht': [],
    'Regio_Oost': [],
    'Regio_Limburg': [],
    'Regio_Groningen/Drenthe': [],
    'Regio_Brabant/Zeeland': [],
    'Regio_Duitsland': [],
    
    # SYSTEM ADMINISTRATION ROLES (Don't need region roles)
    'System_CRUD': [
        'system_user_management',
        'system_role_assignment', 
        'system_logs_read',
        'system_audit_read',
        'system_configuration',
        'system_maintenance',
        '*'  # Full system access
    ],
    'System_User_Management': [
        'system_user_management',
        'system_role_assignment',
        'cognito_admin_access'
    ],
    'System_Logs_Read': [
        'system_logs_read',
        'system_audit_read'
    ],
    
    # OTHER SPECIALIZED ROLES
    'Webshop_Management': [
        'products_create',
        'products_read', 
        'products_update',
        'products_delete',
        'orders_manage',
        'webshop_admin'
    ],
    
    # BACKWARD COMPATIBILITY - Legacy _All roles (DEPRECATED)
    # NOTE: Legacy _All roles have been removed as part of role migration cleanup
    # These are maintained for backward compatibility during migration
    # New users should use Permission + Region role combinations instead
}

# NEW ROLE STRUCTURE COMBINATIONS
# Valid combinations of permission + region roles that provide equivalent access to legacy roles
NEW_ROLE_STRUCTURE_COMBINATIONS = {
    # National level access (equivalent to old _All roles)
    'national_member_admin': ['Members_CRUD', 'Regio_All'],
    'national_member_reader': ['Members_Read', 'Members_Export', 'Regio_All'],
    'national_event_admin': ['Events_CRUD', 'Regio_All'],
    'national_event_reader': ['Events_Read', 'Events_Export', 'Regio_All'],
    'national_product_admin': ['Products_CRUD', 'Regio_All'],
    'national_product_reader': ['Products_Read', 'Products_Export', 'Regio_All'],
    'national_communication_admin': ['Communication_CRUD', 'Regio_All'],
    'national_communication_reader': ['Communication_Read', 'Communication_Export', 'Regio_All'],
    
    # Regional level access examples
    'regional_member_admin_groningen': ['Members_CRUD', 'Regio_Groningen/Drenthe'],
    'regional_member_reader_utrecht': ['Members_Read', 'Members_Export', 'Regio_Utrecht'],
    'regional_event_admin_limburg': ['Events_CRUD', 'Regio_Limburg'],
    
    # System administration (no region needed)
    'system_administrator': ['System_CRUD'],
    'system_user_manager': ['System_User_Management'],
    'system_auditor': ['System_Logs_Read']
}

# LEGACY TO NEW ROLE MAPPING
# Maps old _All roles to equivalent new role combinations
# NOTE: Legacy _All roles have been removed as part of role migration cleanup
LEGACY_TO_NEW_ROLE_MAPPING = {
    # Reference mappings for documentation purposes only
    # 'Members_CRUD_All': ['Members_CRUD', 'Regio_All'],
    # 'Members_Read_All': ['Members_Read', 'Members_Export', 'Regio_All'],
    # 'Members_Export_All': ['Members_Export', 'Regio_All'],
    # 'Events_CRUD_All': ['Events_CRUD', 'Regio_All'],
    # 'Events_Read_All': ['Events_Read', 'Events_Export', 'Regio_All'],
    # 'Events_Export_All': ['Events_Export', 'Regio_All'],
    # 'Products_CRUD_All': ['Products_CRUD', 'Regio_All'],
    # 'Products_Read_All': ['Products_Read', 'Products_Export', 'Regio_All'],
    # 'Products_Export_All': ['Products_Export', 'Regio_All'],
    # 'Communication_CRUD_All': ['Communication_CRUD', 'Regio_All'],
    # 'Communication_Read_All': ['Communication_Read', 'Regio_All'],
    # 'Communication_Export_All': ['Communication_Export', 'Regio_All'],
    # NOTE: Legacy _All roles have been removed as part of role migration cleanup
    # 'System_CRUD_All': ['System_CRUD']  # System roles don't need region
}

# ORGANIZATIONAL ROLE COMBINATIONS - Updated for new role structure
# These represent common organizational positions and their role combinations
# Aligned with frontend functionPermissions.ts organizational roles
ORGANIZATIONAL_ROLE_COMBINATIONS = {
    # National level positions (General Board)
    'National_Chairman': [
        'Members_Read', 'Members_Export', 'Regio_All',
        'Events_Read', 'Events_Export', 'Regio_All',
        'Products_Read', 'Regio_All',
        'Communication_Read', 'Regio_All',
        'System_Logs_Read'
    ],
    'National_Secretary': [
        'Members_Read', 'Members_Export', 'Regio_All',
        'Events_Read', 'Events_Export', 'Regio_All',
        'Products_Read', 'Products_Export', 'Regio_All',
        'Communication_CRUD', 'Regio_All',  # Changed to CRUD for create permissions
        'System_Logs_Read'
    ],
    'National_Treasurer': [
        'Members_Read', 'Regio_All',  # Financial access to all regions
        'Events_Read', 'Regio_All',   # Event financial data
        'Products_Read', 'Regio_All'  # Product financial data
    ],
    'Vice_Chairman': [
        'Members_Read', 'Members_Export', 'Regio_All',
        'Events_Read', 'Events_Export', 'Regio_All',
        'Products_Read', 'Regio_All',
        'Communication_Read', 'Regio_All'
    ],
    
    # Supporting function roles
    'Webmaster': [
        'System_CRUD',  # Full system access
        'Members_CRUD', 'Regio_All',
        'Events_CRUD', 'Regio_All',
        'Products_CRUD', 'Regio_All',
        'Communication_CRUD', 'Regio_All'
    ],
    'Tour_Commissioner': [
        'Members_Read', 'Members_Export', 'Regio_All',
        'Events_CRUD', 'Regio_All',
        'Products_Read', 'Regio_All',
        'Communication_Read', 'Communication_Export', 'Regio_All'
    ],
    'Club_Magazine_Editorial': [
        'Members_Read', 'Members_Export', 'Regio_All',
        'Events_Read', 'Regio_All',
        'Products_Read', 'Regio_All',
        'Communication_CRUD', 'Regio_All'
    ],
    'Webshop_Management': [
        'Webshop_Management',  # Specialized webshop role
        'Members_Read', 'Regio_All',  # Basic member info for orders
        'Events_Read', 'Regio_All',
        'Products_CRUD', 'Regio_All',
        'Communication_Read', 'Regio_All'
    ],
    
    # Regional level positions - Template for all 9 regions
    # Region 1: Noord-Holland
    'Regional_Chairman_Region1': [
        'Members_Read', 'Members_Export', 'Regio_Noord-Holland',
        'Events_CRUD', 'Regio_Noord-Holland',
        'Products_Read', 'Regio_Noord-Holland',  # Changed from Regio_All to regional
        'Communication_Read', 'Communication_Export', 'Regio_Noord-Holland'
    ],
    'Regional_Secretary_Region1': [
        'Members_Read', 'Members_Export', 'Regio_Noord-Holland',
        'Events_Read', 'Events_Export', 'Regio_Noord-Holland',
        'Products_Read', 'Regio_Noord-Holland',  # Changed from Regio_All to regional
        'Communication_Read', 'Communication_Export', 'Regio_Noord-Holland'
    ],
    'Regional_Treasurer_Region1': [
        'Members_Read', 'Regio_Noord-Holland',  # Regional financial access
        'Events_Read', 'Regio_Noord-Holland',
        'Products_Read', 'Regio_Noord-Holland'  # Changed from Regio_All to regional
    ],
    'Regional_Volunteer_Region1': [
        'Members_Read', 'Regio_Noord-Holland',
        'Events_Read', 'Regio_Noord-Holland',
        'Products_Read', 'Regio_Noord-Holland'  # Changed from Regio_All to regional
    ],
    
    # Region 2: Zuid-Holland
    'Regional_Chairman_Region2': [
        'Members_Read', 'Members_Export', 'Regio_Zuid-Holland',
        'Events_CRUD', 'Regio_Zuid-Holland',
        'Products_Read', 'Regio_All',
        'Communication_Read', 'Communication_Export', 'Regio_Zuid-Holland'
    ],
    'Regional_Secretary_Region2': [
        'Members_Read', 'Members_Export', 'Regio_Zuid-Holland',
        'Events_Read', 'Events_Export', 'Regio_Zuid-Holland',
        'Products_Read', 'Regio_All',
        'Communication_Read', 'Communication_Export', 'Regio_Zuid-Holland'
    ],
    'Regional_Treasurer_Region2': [
        'Members_Read', 'Regio_Zuid-Holland',
        'Events_Read', 'Regio_Zuid-Holland',
        'Products_Read', 'Regio_All'
    ],
    'Regional_Volunteer_Region2': [
        'Members_Read', 'Regio_Zuid-Holland',
        'Events_Read', 'Regio_Zuid-Holland',
        'Products_Read', 'Regio_All'
    ],
    
    # Region 3: Friesland
    'Regional_Chairman_Region3': [
        'Members_Read', 'Members_Export', 'Regio_Friesland',
        'Events_CRUD', 'Regio_Friesland',
        'Products_Read', 'Regio_All',
        'Communication_Read', 'Communication_Export', 'Regio_Friesland'
    ],
    'Regional_Secretary_Region3': [
        'Members_Read', 'Members_Export', 'Regio_Friesland',
        'Events_Read', 'Events_Export', 'Regio_Friesland',
        'Products_Read', 'Regio_All',
        'Communication_Read', 'Communication_Export', 'Regio_Friesland'
    ],
    'Regional_Treasurer_Region3': [
        'Members_Read', 'Regio_Friesland',
        'Events_Read', 'Regio_Friesland',
        'Products_Read', 'Regio_All'
    ],
    'Regional_Volunteer_Region3': [
        'Members_Read', 'Regio_Friesland',
        'Events_Read', 'Regio_Friesland',
        'Products_Read', 'Regio_All'
    ],
    
    # Region 4: Utrecht
    'Regional_Chairman_Region4': [
        'Members_Read', 'Members_Export', 'Regio_Utrecht',
        'Events_CRUD', 'Regio_Utrecht',
        'Products_Read', 'Regio_Utrecht',  # Changed from Regio_All to regional
        'Communication_Read', 'Communication_Export', 'Regio_Utrecht'
    ],
    'Regional_Secretary_Region4': [
        'Members_Read', 'Members_Export', 'Regio_Utrecht',
        'Events_Read', 'Events_Export', 'Regio_Utrecht',
        'Products_Read', 'Regio_Utrecht',  # Changed from Regio_All to regional
        'Communication_Read', 'Communication_Export', 'Regio_Utrecht'
    ],
    'Regional_Treasurer_Region4': [
        'Members_Read', 'Regio_Utrecht',
        'Events_Read', 'Regio_Utrecht',
        'Products_Read', 'Regio_Utrecht'  # Changed from Regio_All to regional
    ],
    'Regional_Volunteer_Region4': [
        'Members_Read', 'Regio_Utrecht',
        'Events_Read', 'Regio_Utrecht',
        'Products_Read', 'Regio_Utrecht'  # Changed from Regio_All to regional
    ],
    
    # Region 5: Oost
    'Regional_Chairman_Region5': [
        'Members_Read', 'Members_Export', 'Regio_Oost',
        'Events_CRUD', 'Regio_Oost',
        'Products_Read', 'Regio_All',
        'Communication_Read', 'Communication_Export', 'Regio_Oost'
    ],
    'Regional_Secretary_Region5': [
        'Members_Read', 'Members_Export', 'Regio_Oost',
        'Events_Read', 'Events_Export', 'Regio_Oost',
        'Products_Read', 'Regio_All',
        'Communication_Read', 'Communication_Export', 'Regio_Oost'
    ],
    'Regional_Treasurer_Region5': [
        'Members_Read', 'Regio_Oost',
        'Events_Read', 'Regio_Oost',
        'Products_Read', 'Regio_All'
    ],
    'Regional_Volunteer_Region5': [
        'Members_Read', 'Regio_Oost',
        'Events_Read', 'Regio_Oost',
        'Products_Read', 'Regio_All'
    ],
    
    # Region 6: Limburg
    'Regional_Chairman_Region6': [
        'Members_Read', 'Members_Export', 'Regio_Limburg',
        'Events_CRUD', 'Regio_Limburg',
        'Products_Read', 'Regio_All',
        'Communication_Read', 'Communication_Export', 'Regio_Limburg'
    ],
    'Regional_Secretary_Region6': [
        'Members_Read', 'Members_Export', 'Regio_Limburg',
        'Events_Read', 'Events_Export', 'Regio_Limburg',
        'Products_Read', 'Regio_All',
        'Communication_Read', 'Communication_Export', 'Regio_Limburg'
    ],
    'Regional_Treasurer_Region6': [
        'Members_Read', 'Regio_Limburg',
        'Events_Read', 'Regio_Limburg',
        'Products_Read', 'Regio_All'
    ],
    'Regional_Volunteer_Region6': [
        'Members_Read', 'Regio_Limburg',
        'Events_Read', 'Regio_Limburg',
        'Products_Read', 'Regio_All'
    ],
    
    # Region 7: Groningen/Drenthe
    'Regional_Chairman_Region7': [
        'Members_Read', 'Members_Export', 'Regio_Groningen/Drenthe',
        'Events_CRUD', 'Regio_Groningen/Drenthe',
        'Products_Read', 'Regio_All',
        'Communication_Read', 'Communication_Export', 'Regio_Groningen/Drenthe'
    ],
    'Regional_Secretary_Region7': [
        'Members_Read', 'Members_Export', 'Regio_Groningen/Drenthe',
        'Events_Read', 'Events_Export', 'Regio_Groningen/Drenthe',
        'Products_Read', 'Regio_All',
        'Communication_Read', 'Communication_Export', 'Regio_Groningen/Drenthe'
    ],
    'Regional_Treasurer_Region7': [
        'Members_Read', 'Regio_Groningen/Drenthe',
        'Events_Read', 'Regio_Groningen/Drenthe',
        'Products_Read', 'Regio_Groningen/Drenthe'  # Changed from Regio_All to regional
    ],
    'Regional_Volunteer_Region7': [
        'Members_Read', 'Regio_Groningen/Drenthe',
        'Events_Read', 'Regio_Groningen/Drenthe',
        'Products_Read', 'Regio_All'
    ],
    
    # Region 8: Brabant/Zeeland
    'Regional_Chairman_Region8': [
        'Members_Read', 'Members_Export', 'Regio_Brabant/Zeeland',
        'Events_CRUD', 'Regio_Brabant/Zeeland',
        'Products_Read', 'Regio_All',
        'Communication_Read', 'Communication_Export', 'Regio_Brabant/Zeeland'
    ],
    'Regional_Secretary_Region8': [
        'Members_Read', 'Members_Export', 'Regio_Brabant/Zeeland',
        'Events_Read', 'Events_Export', 'Regio_Brabant/Zeeland',
        'Products_Read', 'Regio_All',
        'Communication_Read', 'Communication_Export', 'Regio_Brabant/Zeeland'
    ],
    'Regional_Treasurer_Region8': [
        'Members_Read', 'Regio_Brabant/Zeeland',
        'Events_Read', 'Regio_Brabant/Zeeland',
        'Products_Read', 'Regio_All'
    ],
    'Regional_Volunteer_Region8': [
        'Members_Read', 'Regio_Brabant/Zeeland',
        'Events_Read', 'Regio_Brabant/Zeeland',
        'Products_Read', 'Regio_All'
    ],
    
    # Region 9: Duitsland
    'Regional_Chairman_Region9': [
        'Members_Read', 'Members_Export', 'Regio_Duitsland',
        'Events_CRUD', 'Regio_Duitsland',
        'Products_Read', 'Regio_All',
        'Communication_Read', 'Communication_Export', 'Regio_Duitsland'
    ],
    'Regional_Secretary_Region9': [
        'Members_Read', 'Members_Export', 'Regio_Duitsland',
        'Events_Read', 'Events_Export', 'Regio_Duitsland',
        'Products_Read', 'Regio_All',
        'Communication_Read', 'Communication_Export', 'Regio_Duitsland'
    ],
    'Regional_Treasurer_Region9': [
        'Members_Read', 'Regio_Duitsland',
        'Events_Read', 'Regio_Duitsland',
        'Products_Read', 'Regio_All'
    ],
    'Regional_Volunteer_Region9': [
        'Members_Read', 'Regio_Duitsland',
        'Events_Read', 'Regio_Duitsland',
        'Products_Read', 'Regio_Duitsland'  # Changed from Regio_All to regional
    ],
    
    # Legacy organizational combinations (for backward compatibility)
    'member_administration': [
        'Members_CRUD', 'Regio_All',
        'Events_Read', 'Products_Read', 'Communication_Read'
    ],
    'webmaster': [  # Alias for Webmaster
        'System_CRUD',
        'Members_CRUD', 'Regio_All',
        'Events_CRUD', 'Regio_All',
        'Products_CRUD', 'Regio_All',
        'Communication_CRUD', 'Regio_All'
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
    return required_permission in user_permissions or '*' in user_permissions

def has_new_role_structure(user_roles):
    """
    Check if user has the new permission + region role structure
    
    Args:
        user_roles (list): List of user's role names
        
    Returns:
        dict: {
            'has_new_structure': bool,
            'has_permission_role': bool,
            'has_region_role': bool,
            'permission_roles': list,
            'region_roles': list,
            'admin_roles': list,
            'legacy_roles': list
        }
    """
    # System admin roles don't need region roles
    admin_roles = ['System_CRUD', 'System_User_Management', 'System_Logs_Read']
    
    # Permission role prefixes
    permission_prefixes = ['Members_', 'Events_', 'Products_', 'Communication_']
    
    # Categorize user roles
    user_admin_roles = [role for role in user_roles if role in admin_roles]
    user_permission_roles = [role for role in user_roles 
                           if any(role.startswith(prefix) for prefix in permission_prefixes) 
                           and not role.endswith('_All')]
    user_region_roles = [role for role in user_roles if role.startswith('Regio_')]
    user_legacy_roles = [role for role in user_roles if role.endswith('_All') and not role.startswith('Regio_')]
    
    # Admin users have valid structure
    if user_admin_roles:
        has_new_structure = True
    else:
        # Need both permission and region roles for new structure
        has_new_structure = len(user_permission_roles) > 0 and len(user_region_roles) > 0
    
    return {
        'has_new_structure': has_new_structure,
        'has_permission_role': len(user_permission_roles) > 0,
        'has_region_role': len(user_region_roles) > 0,
        'permission_roles': user_permission_roles,
        'region_roles': user_region_roles,
        'admin_roles': user_admin_roles,
        'legacy_roles': user_legacy_roles
    }

def convert_legacy_roles_to_new_structure(user_roles):
    """
    Convert legacy _All roles to equivalent new role combinations
    
    Args:
        user_roles (list): List of user's current roles (may include legacy)
        
    Returns:
        dict: {
            'converted_roles': list,      # New role structure equivalent
            'legacy_roles_found': list,   # Legacy roles that were converted
            'unchanged_roles': list,      # Roles that didn't need conversion
            'conversion_notes': list      # Notes about the conversion
        }
    """
    converted_roles = []
    legacy_roles_found = []
    unchanged_roles = []
    conversion_notes = []
    
    for role in user_roles:
        if role in LEGACY_TO_NEW_ROLE_MAPPING:
            # This is a legacy role - convert it
            legacy_roles_found.append(role)
            new_roles = LEGACY_TO_NEW_ROLE_MAPPING[role]
            converted_roles.extend(new_roles)
            conversion_notes.append(f"'{role}' -> {new_roles}")
        else:
            # This is already new structure or other role
            unchanged_roles.append(role)
            converted_roles.append(role)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_converted_roles = []
    for role in converted_roles:
        if role not in seen:
            seen.add(role)
            unique_converted_roles.append(role)
    
    return {
        'converted_roles': unique_converted_roles,
        'legacy_roles_found': legacy_roles_found,
        'unchanged_roles': unchanged_roles,
        'conversion_notes': conversion_notes
    }

def can_edit_field(roles, field_name, is_own_record=False):
    """
    Check if user can edit a specific field based on their roles
    Updated to support new role structure
    
    Args:
        roles (list): List of user's role names
        field_name (str): Name of the field to check
        is_own_record (bool): Whether this is the user's own record
        
    Returns:
        bool: True if user can edit the field, False otherwise
    """
    # Check for admin access first
    admin_roles = ['System_CRUD', 'System_User_Management']
    if any(role in roles for role in admin_roles):
        return True
    
    # Check for legacy _All roles (backward compatibility)
    legacy_admin_roles = ['Members_CRUD_All', 'System_CRUD_All']
    if any(role in roles for role in legacy_admin_roles):
        return True
    
    # Check for new role structure
    role_structure = has_new_role_structure(roles)
    
    # For new role structure, check if user has Members_CRUD permission
    if role_structure['has_new_structure']:
        if 'Members_CRUD' in roles:
            return True
    
    # Special handling for status field - only Members_CRUD or admin can modify
    if field_name == 'status':
        return ('Members_CRUD' in roles and role_structure['has_region_role']) or \
               'Members_CRUD_All' in roles or \
               any(role in roles for role in admin_roles)
    
    # Administrative fields require special permissions
    if field_name in ADMINISTRATIVE_FIELDS:
        return ('Members_CRUD' in roles and role_structure['has_region_role']) or \
               'Members_CRUD_All' in roles or \
               any(role in roles for role in admin_roles)
    
    # Personal and motorcycle fields can be edited by user for own record
    if field_name in PERSONAL_FIELDS:
        if is_own_record and 'hdcnLeden' in roles:
            return True
        # Or if user has admin permissions
        return ('Members_CRUD' in roles and role_structure['has_region_role']) or \
               'Members_CRUD_All' in roles or \
               any(role in roles for role in admin_roles)
    
    if field_name in MOTORCYCLE_FIELDS:
        if is_own_record and 'hdcnLeden' in roles:
            return True
        # Or if user has admin permissions
        return ('Members_CRUD' in roles and role_structure['has_region_role']) or \
               'Members_CRUD_All' in roles or \
               any(role in roles for role in admin_roles)
    
    # For other fields, require admin permissions
    return ('Members_CRUD' in roles and role_structure['has_region_role']) or \
           'Members_CRUD_All' in roles or \
           any(role in roles for role in admin_roles)

def get_regional_permissions(region_id, role_template):
    """
    Generate regional permissions for a specific region using new role structure
    
    Args:
        region_id (str): Region identifier (e.g., "Groningen/Drenthe", "Utrecht", etc.)
        role_template (str): Template name from NEW_ROLE_STRUCTURE_COMBINATIONS
        
    Returns:
        list: List of region-specific roles
    """
    # Map region_id to actual region role names
    region_role_mapping = {
        '1': 'Regio_Groningen/Drenthe',
        '2': 'Regio_Friesland', 
        '3': 'Regio_Noord-Holland',
        '4': 'Regio_Utrecht',
        '5': 'Regio_Zuid-Holland',
        '6': 'Regio_Oost',
        '7': 'Regio_Limburg',
        '8': 'Regio_Brabant/Zeeland',
        '9': 'Regio_Duitsland',
        'all': 'Regio_All'
    }
    
    # Get the actual region role name
    region_role = region_role_mapping.get(region_id, f'Regio_{region_id}')
    
    # Get base role combination from template
    if role_template in NEW_ROLE_STRUCTURE_COMBINATIONS:
        base_roles = NEW_ROLE_STRUCTURE_COMBINATIONS[role_template].copy()
        
        # Replace Regio_All with specific region if needed
        if 'Regio_All' in base_roles and region_id != 'all':
            base_roles.remove('Regio_All')
            base_roles.append(region_role)
        
        return base_roles
    
    # Fallback: return just the region role
    return [region_role]

def get_organizational_role_combination(organizational_role):
    """
    Get the role combination for a specific organizational position
    
    Args:
        organizational_role (str): Name of the organizational position
        
    Returns:
        list: List of roles for the organizational position, empty list if not found
    """
    return ORGANIZATIONAL_ROLE_COMBINATIONS.get(organizational_role, [])

def assign_organizational_role(user_roles, organizational_role):
    """
    Assign an organizational role combination to a user's existing roles
    
    Args:
        user_roles (list): List of user's current role names
        organizational_role (str): Name of the organizational position to assign
        
    Returns:
        dict: {
            'success': bool,
            'new_roles': list,      # Updated role list with organizational roles added
            'added_roles': list,    # Roles that were added
            'message': str          # Success or error message
        }
    """
    if organizational_role not in ORGANIZATIONAL_ROLE_COMBINATIONS:
        return {
            'success': False,
            'new_roles': user_roles,
            'added_roles': [],
            'message': f"Unknown organizational role: {organizational_role}"
        }
    
    org_roles = ORGANIZATIONAL_ROLE_COMBINATIONS[organizational_role]
    
    # Combine existing roles with organizational roles
    combined_roles = list(user_roles)  # Copy existing roles
    added_roles = []
    
    for role in org_roles:
        if role not in combined_roles:
            combined_roles.append(role)
            added_roles.append(role)
    
    return {
        'success': True,
        'new_roles': combined_roles,
        'added_roles': added_roles,
        'message': f"Successfully assigned organizational role '{organizational_role}'. Added {len(added_roles)} new roles."
    }

def validate_organizational_role_structure(organizational_role):
    """
    Validate that an organizational role has a proper new role structure
    
    Args:
        organizational_role (str): Name of the organizational position
        
    Returns:
        dict: {
            'is_valid': bool,
            'validation_type': str,  # 'valid_new_structure', 'has_legacy_roles', 'invalid'
            'role_analysis': dict,   # Analysis of the role structure
            'suggestions': list      # Suggested improvements
        }
    """
    if organizational_role not in ORGANIZATIONAL_ROLE_COMBINATIONS:
        return {
            'is_valid': False,
            'validation_type': 'invalid',
            'role_analysis': {},
            'suggestions': [f"Organizational role '{organizational_role}' not found"]
        }
    
    org_roles = ORGANIZATIONAL_ROLE_COMBINATIONS[organizational_role]
    role_analysis = has_new_role_structure(org_roles)
    
    # Check if organizational role uses new structure
    if role_analysis['has_new_structure']:
        return {
            'is_valid': True,
            'validation_type': 'valid_new_structure',
            'role_analysis': role_analysis,
            'suggestions': []
        }
    
    # Check if it has legacy roles
    if role_analysis['legacy_roles']:
        conversion = convert_legacy_roles_to_new_structure(org_roles)
        return {
            'is_valid': True,  # Still valid during migration
            'validation_type': 'has_legacy_roles',
            'role_analysis': role_analysis,
            'suggestions': [
                f"Consider updating organizational role to use new structure: {conversion['converted_roles']}"
            ]
        }
    
    # Invalid structure
    return {
        'is_valid': False,
        'validation_type': 'invalid',
        'role_analysis': role_analysis,
        'suggestions': [
            "Organizational role needs both permission and region roles",
            "Add permission roles like Members_CRUD, Events_Read, etc.",
            "Add region roles like Regio_All, Regio_Utrecht, etc."
        ]
    }

def get_all_organizational_roles():
    """
    Get a list of all available organizational roles
    
    Returns:
        dict: {
            'national_roles': list,    # National level organizational roles
            'regional_roles': list,    # Regional level organizational roles
            'function_roles': list,    # Supporting function roles
            'legacy_roles': list       # Legacy organizational roles
        }
    """
    national_roles = []
    regional_roles = []
    function_roles = []
    legacy_roles = []
    
    for role_name in ORGANIZATIONAL_ROLE_COMBINATIONS.keys():
        if role_name.startswith('National_'):
            national_roles.append(role_name)
        elif role_name.startswith('Regional_'):
            regional_roles.append(role_name)
        elif role_name in ['Webmaster', 'Tour_Commissioner', 'Club_Magazine_Editorial', 'Webshop_Management', 'Vice_Chairman']:
            function_roles.append(role_name)
        else:
            legacy_roles.append(role_name)
    
    return {
        'national_roles': sorted(national_roles),
        'regional_roles': sorted(regional_roles),
        'function_roles': sorted(function_roles),
        'legacy_roles': sorted(legacy_roles)
    }

def validate_role_combination(user_roles):
    """
    Validate that user has a valid role combination for the new structure
    
    Args:
        user_roles (list): List of user's role names
        
    Returns:
        dict: {
            'is_valid': bool,
            'validation_type': str,  # 'admin', 'new_structure', 'legacy', 'invalid'
            'missing_roles': list,   # What roles are missing for valid structure
            'suggestions': list      # Suggested role combinations
        }
    """
    role_structure = has_new_role_structure(user_roles)
    
    # Admin users are always valid
    if role_structure['admin_roles']:
        return {
            'is_valid': True,
            'validation_type': 'admin',
            'missing_roles': [],
            'suggestions': []
        }
    
    # Check for valid new structure
    if role_structure['has_new_structure']:
        return {
            'is_valid': True,
            'validation_type': 'new_structure',
            'missing_roles': [],
            'suggestions': []
        }
    
    # Check for legacy roles (still valid during migration)
    if role_structure['legacy_roles']:
        conversion = convert_legacy_roles_to_new_structure(user_roles)
        return {
            'is_valid': True,
            'validation_type': 'legacy',
            'missing_roles': [],
            'suggestions': [f"Consider migrating to: {conversion['converted_roles']}"]
        }
    
    # Invalid structure - determine what's missing
    missing_roles = []
    suggestions = []
    
    if not role_structure['has_permission_role']:
        missing_roles.append('permission_role')
        suggestions.append('Add a permission role like Members_CRUD, Events_Read, etc.')
    
    if not role_structure['has_region_role']:
        missing_roles.append('region_role')
        suggestions.append('Add a region role like Regio_All, Regio_Utrecht, etc.')
    
    return {
        'is_valid': False,
        'validation_type': 'invalid',
        'missing_roles': missing_roles,
        'suggestions': suggestions
    }