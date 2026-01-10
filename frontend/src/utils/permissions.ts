/**
 * Permission calculation utilities for H-DCN frontend
 * Based on the backend role_permissions.py system
 */

// Permission definitions matching backend system - NEW ROLE STRUCTURE
const DEFAULT_ROLE_PERMISSIONS: { [key: string]: string[] } = {
  // Basic member role - all authenticated members get this role
  'hdcnLeden': [
    'members:read_own',
    'members:update_own_personal',
    'members:update_own_motorcycle', 
    'events:read_public',
    'products:browse_catalog',
    'webshop:access'
  ],
  
  // Member management roles - NEW STRUCTURE (no _All suffix)
  'Members_CRUD': [
    'members:read_all',
    'members:create',
    'members:update_all',
    'members:delete',
    'members:update_status',
    'members:export_all',
    'members:update_administrative'
  ],
  'Members_Read': [
    'members:read_all',
    'members:export_all'
  ],
  'Members_Export': [
    'members:read_all',
    'members:export_all'
  ],
  'Members_Status_Approve': [
    'members:read_all',
    'members:update_status',
    'members:approve_status'
  ],
  
  // Event management roles - NEW STRUCTURE (no _All suffix)
  'Events_Read': [
    'events:read_all',
    'events:export_all'
  ],
  'Events_CRUD': [
    'events:read_all',
    'events:create',
    'events:update_all',
    'events:delete',
    'events:export_all'
  ],
  'Events_Export': [
    'events:read_all',
    'events:export_all'
  ],
  
  // Product management roles - NEW STRUCTURE (no _All suffix)
  'Products_Read': [
    'products:read_all',
    'products:export_all'
  ],
  'Products_CRUD': [
    'products:read_all',
    'products:create',
    'products:update_all',
    'products:delete',
    'products:export_all'
  ],
  'Products_Export': [
    'products:read_all',
    'products:export_all'
  ],
  
  // Communication roles - NEW STRUCTURE (no _All suffix)
  'Communication_Read': [
    'communication:read_all'
  ],
  'Communication_Export': [
    'communication:read_all',
    'communication:export_all'
  ],
  'Communication_CRUD': [
    'communication:read_all',
    'communication:create',
    'communication:update_all',
    'communication:delete',
    'communication:export_all'
  ],
  
  // System administration roles
  'System_User_Management': [
    'system:user_management',
    'system:role_assignment',
    'cognito:admin_access'
  ],
  'System_Logs_Read': [
    'system:logs_read',
    'system:audit_read'
  ],
  'System_CRUD': [
    'system:user_management',
    'system:role_assignment',
    'system:logs_read',
    'system:audit_read',
    'system:configuration',
    'system:maintenance'
  ],
  
  // Webshop management
  'Webshop_Management': [
    'products:read_all',
    'products:create',
    'products:update_all',
    'products:delete',
    'webshop:management'
  ]
};

// Human-readable permission descriptions
const PERMISSION_DESCRIPTIONS: { [key: string]: string } = {
  // Member permissions
  'members:read_own': 'Eigen gegevens bekijken',
  'members:update_own_personal': 'Eigen persoonlijke gegevens bewerken',
  'members:update_own_motorcycle': 'Eigen motorgegevens bewerken',
  'members:read_all': 'Alle ledengegevens bekijken',
  'members:create': 'Nieuwe leden aanmaken',
  'members:update_all': 'Alle ledengegevens bewerken',
  'members:delete': 'Leden verwijderen',
  'members:update_status': 'Lidmaatschapsstatus wijzigen',
  'members:export_all': 'Ledengegevens exporteren',
  'members:update_administrative': 'Administratieve velden bewerken',
  'members:approve_status': 'Lidmaatschap goedkeuren',
  
  // Event permissions
  'events:read_public': 'Publieke evenementen bekijken',
  'events:read_all': 'Alle evenementen bekijken',
  'events:create': 'Evenementen aanmaken',
  'events:update_all': 'Evenementen bewerken',
  'events:delete': 'Evenementen verwijderen',
  'events:export_all': 'Evenementengegevens exporteren',
  
  // Product permissions
  'products:browse_catalog': 'Productcatalogus bekijken',
  'products:read_all': 'Alle producten bekijken',
  'products:create': 'Producten aanmaken',
  'products:update_all': 'Producten bewerken',
  'products:delete': 'Producten verwijderen',
  'products:export_all': 'Productgegevens exporteren',
  
  // Communication permissions
  'communication:read_all': 'Communicatie bekijken',
  'communication:create': 'Communicatie aanmaken',
  'communication:update_all': 'Communicatie bewerken',
  'communication:delete': 'Communicatie verwijderen',
  'communication:export_all': 'Communicatiegegevens exporteren',
  
  // System permissions
  'system:user_management': 'Gebruikersbeheer',
  'system:role_assignment': 'Rolbeheer',
  'system:logs_read': 'Logbestanden bekijken',
  'system:audit_read': 'Auditgegevens bekijken',
  'system:configuration': 'Systeemconfiguratie',
  'system:maintenance': 'Systeemonderhoud',
  'cognito:admin_access': 'Cognito beheer',
  
  // Webshop permissions
  'webshop:access': 'Webshop toegang'
};

// Permission categories for better organization
const PERMISSION_CATEGORIES: { [key: string]: string } = {
  'members:': 'Ledenadministratie',
  'events:': 'Evenementen',
  'products:': 'Producten',
  'communication:': 'Communicatie',
  'system:': 'Systeembeheer',
  'cognito:': 'Authenticatie',
  'webshop:': 'Webshop'
};

/**
 * Get permissions for a specific role
 */
export function getRolePermissions(roleName: string): string[] {
  return DEFAULT_ROLE_PERMISSIONS[roleName] || [];
}

/**
 * Get combined permissions from multiple roles
 */
export function getCombinedPermissions(roles: string[]): string[] {
  if (!roles || roles.length === 0) {
    return [];
  }
  
  const allPermissions = new Set<string>();
  for (const role of roles) {
    const rolePermissions = getRolePermissions(role);
    rolePermissions.forEach(permission => allPermissions.add(permission));
  }
  
  return Array.from(allPermissions).sort();
}

/**
 * Check if user has a specific permission
 */
export function hasPermission(roles: string[], requiredPermission: string): boolean {
  const userPermissions = getCombinedPermissions(roles);
  return userPermissions.includes(requiredPermission);
}

/**
 * Get human-readable description for a permission
 */
export function getPermissionDescription(permission: string): string {
  return PERMISSION_DESCRIPTIONS[permission] || permission;
}

/**
 * Get category for a permission
 */
export function getPermissionCategory(permission: string): string {
  for (const [prefix, category] of Object.entries(PERMISSION_CATEGORIES)) {
    if (permission.startsWith(prefix)) {
      return category;
    }
  }
  return 'Overig';
}

/**
 * Group permissions by category
 */
export function groupPermissionsByCategory(permissions: string[]): { [category: string]: string[] } {
  const grouped: { [category: string]: string[] } = {};
  
  for (const permission of permissions) {
    const category = getPermissionCategory(permission);
    if (!grouped[category]) {
      grouped[category] = [];
    }
    grouped[category].push(permission);
  }
  
  return grouped;
}

/**
 * Get access level summary based on roles
 */
export function getAccessLevelSummary(roles: string[]): {
  level: 'basic' | 'functional' | 'administrative' | 'system';
  description: string;
  icon: string;
} {
  if (!roles || roles.length === 0) {
    return {
      level: 'basic',
      description: 'Geen toegang',
      icon: '❌'
    };
  }
  
  // Check for system admin roles - using new role structure
  if (roles.some(role => 
    role.includes('System_') || 
    role.includes('Webmaster')
  )) {
    return {
      level: 'system',
      description: 'Systeembeheerder - Volledige toegang',
      icon: '⚡'
    };
  }
  
  // Check for administrative roles - NEW ROLE STRUCTURE
  if (roles.some(role => 
    role.includes('Members_CRUD') ||
    role.includes('National_') ||
    role.includes('Communication_CRUD') ||
    role.includes('Events_CRUD') ||
    role.includes('Products_CRUD')
  )) {
    return {
      level: 'administrative',
      description: 'Beheerder - Uitgebreide beheertoegang',
      icon: '🔧'
    };
  }
  
  // Check for functional roles
  if (roles.some(role => 
    role.includes('Members_') || 
    role.includes('Events_') || 
    role.includes('Products_') ||
    role.includes('Communication_') ||
    role.includes('Regional_')
  )) {
    return {
      level: 'functional',
      description: 'Functionaris - Toegang tot specifieke functies',
      icon: '📋'
    };
  }
  
  // Basic member
  if (roles.includes('hdcnLeden')) {
    return {
      level: 'basic',
      description: 'Basis lid - Toegang tot persoonlijke gegevens en webshop',
      icon: '✓'
    };
  }
  
  return {
    level: 'basic',
    description: 'Beperkte toegang',
    icon: 'ℹ️'
  };
}

/**
 * Check if user is an administrator
 */
export function isAdministrator(roles: string[]): boolean {
  if (!roles || roles.length === 0) {
    return false;
  }
  
  return roles.some(role => 
    role.includes('System_') || 
    role.includes('Members_CRUD') ||
    role.includes('National_') ||
    role.includes('Communication_CRUD')
  );
}