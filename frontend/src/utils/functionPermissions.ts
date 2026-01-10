import { ApiService } from '../services/apiService';
import { getCurrentUserRoles } from '../services/authService';
import { HDCNGroup } from '../types/user';

interface User {
  signInUserSession?: {
    accessToken?: {
      payload: {
        'cognito:groups'?: string[];
      };
      jwtToken?: string;
    };
  };
  attributes?: {
    email?: string;
    given_name?: string;
  };
  groups?: HDCNGroup[];
}

/**
 * Extracts Cognito groups (roles) from a user's JWT token
 * Enhanced version that supports both legacy user objects and new JWT token structure
 * @param user - The user object containing the sign-in session or groups array
 * @returns Array of role strings from cognito:groups claim, or empty array if none found
 */
export function getUserRoles(user: User): string[] {
  // New approach: Use groups array directly if available (from useAuth hook)
  if (user?.groups && Array.isArray(user.groups)) {
    return user.groups;
  }

  // Try to get groups from JWT token payload first
  if (user?.signInUserSession?.accessToken?.payload) {
    const cognitoGroups = user.signInUserSession.accessToken.payload['cognito:groups'];
    if (cognitoGroups && Array.isArray(cognitoGroups)) {
      return cognitoGroups;
    }
  }

  // If payload is empty, try to decode the JWT token directly
  const jwtToken = user?.signInUserSession?.accessToken?.jwtToken;
  if (jwtToken) {
    try {
      // Decode JWT payload (base64 decode the middle part)
      const parts = jwtToken.split('.');
      if (parts.length === 3) {
        const payload = JSON.parse(atob(parts[1]));
        const cognitoGroups = payload['cognito:groups'];
        if (cognitoGroups && Array.isArray(cognitoGroups)) {
          return cognitoGroups;
        }
      }
    } catch (error) {
      console.error('Error decoding JWT token in getUserRoles:', error);
    }
  }

  console.log('🔍 getUserRoles - No groups found, returning empty array');
  return [];
}

/**
 * Enhanced role extraction that works with current authentication session
 * This function directly queries the current authentication session for roles
 * @returns Promise with array of user roles from current session
 */
export async function getCurrentUserRolesFromSession(): Promise<HDCNGroup[]> {
  try {
    return await getCurrentUserRoles();
  } catch (error) {
    console.error('Failed to get current user roles from session:', error);
    return [];
  }
}

/**
 * Utility to check if a user has a specific role
 * @param user - User object or null
 * @param role - Role to check for
 * @returns boolean indicating if user has the role
 */
export function userHasRole(user: User | null, role: HDCNGroup): boolean {
  if (!user) return false;
  
  const userRoles = getUserRoles(user);
  return userRoles.includes(role);
}

/**
 * Utility to check if a user has any of the specified roles
 * @param user - User object or null
 * @param roles - Array of roles to check for
 * @returns boolean indicating if user has any of the roles
 */
export function userHasAnyRole(user: User | null, roles: HDCNGroup[]): boolean {
  if (!user || !roles.length) return false;
  
  const userRoles = getUserRoles(user);
  return roles.some(role => userRoles.includes(role));
}

/**
 * Utility to check if a user has all of the specified roles
 * @param user - User object or null
 * @param roles - Array of roles to check for
 * @returns boolean indicating if user has all of the roles
 */
export function userHasAllRoles(user: User | null, roles: HDCNGroup[]): boolean {
  if (!user || !roles.length) return false;
  
  const userRoles = getUserRoles(user);
  return roles.every(role => userRoles.includes(role));
}

/**
 * Enhanced permission checking for new permission + region role combinations
 * Checks if user has the required permission AND appropriate regional access
 * @param user - User object or null
 * @param requiredPermission - The permission type needed (e.g., 'members_read', 'events_crud')
 * @param targetRegion - Optional specific region to check access for
 * @returns boolean indicating if user has the required permission + region combination
 */
export function userHasPermissionWithRegion(
  user: User | null, 
  requiredPermission: string, 
  targetRegion?: string
): boolean {
  if (!user) return false;
  
  const userRoles = getUserRoles(user);
  
  // Parse permission type (e.g., 'members_read' -> permission: 'members', action: 'read')
  const [permissionType, action] = requiredPermission.split('_');
  
  // Check if user has the required permission role
  const hasPermission = userHasPermissionType(user, permissionType, action as 'read' | 'crud' | 'export');
  if (!hasPermission) {
    console.log(`❌ User lacks ${permissionType} ${action} permission`);
    return false;
  }
  
  // If no specific region is required, check if user has any regional access
  if (!targetRegion || targetRegion === '') {
    const hasAnyRegionalAccess = userRoles.some(role => 
      role === 'Regio_All' || role.startsWith('Regio_')
    );
    if (!hasAnyRegionalAccess) {
      console.log(`❌ User has no regional access`);
      return false;
    }
    return true;
  }
  
  // Check if user has access to the specific target region
  const hasRegionalAccess = userRoles.some(role => {
    if (role === 'Regio_All') return true; // Full regional access
    
    // Map target region to role name
    const regionRoleMap: { [key: string]: string } = {
      'utrecht': 'Regio_Utrecht',
      'limburg': 'Regio_Limburg',
      'groningen_drenthe': 'Regio_Groningen/Drenthe',
      'zuid_holland': 'Regio_Zuid-Holland',
      'noord_holland': 'Regio_Noord-Holland',
      'oost': 'Regio_Oost',
      'brabant_zeeland': 'Regio_Brabant/Zeeland',
      'friesland': 'Regio_Friesland',
      'duitsland': 'Regio_Duitsland'
    };
    
    return role === regionRoleMap[targetRegion];
  });
  
  if (!hasRegionalAccess) {
    console.log(`❌ User lacks regional access for ${targetRegion}`);
    return false;
  }
  
  console.log(`✅ Permission granted: ${requiredPermission} in ${targetRegion || 'any region'}`);
  return true;
}

/**
 * Get user's accessible regions based on their regional roles
 * @param user - User object or null
 * @returns Array of region identifiers the user has access to
 */
export function getUserAccessibleRegions(user: User | null): string[] {
  if (!user) return [];
  
  const userRoles = getUserRoles(user);
  const accessibleRegions: string[] = [];
  
  userRoles.forEach(role => {
    if (role === 'Regio_All') {
      // User has access to all regions
      return ['all'];
    }
    
    // Map role to region identifier
    const roleRegionMap: { [key: string]: string } = {
      'Regio_Utrecht': 'utrecht',
      'Regio_Limburg': 'limburg',
      'Regio_Groningen/Drenthe': 'groningen_drenthe',
      'Regio_Zuid-Holland': 'zuid_holland',
      'Regio_Noord-Holland': 'noord_holland',
      'Regio_Oost': 'oost',
      'Regio_Brabant/Zeeland': 'brabant_zeeland',
      'Regio_Friesland': 'friesland',
      'Regio_Duitsland': 'duitsland'
    };
    
    if (roleRegionMap[role]) {
      accessibleRegions.push(roleRegionMap[role]);
    }
  });
  
  // If user has Regio_All, return all regions
  if (userRoles.includes('Regio_All')) {
    return ['all'];
  }
  
  return Array.from(new Set(accessibleRegions)); // Remove duplicates
}

/**
 * Check if user has specific permission type (without region requirement)
 * @param user - User object or null
 * @param permissionType - The permission type (e.g., 'members', 'events', 'products')
 * @param action - The action type ('read', 'crud', 'export')
 * @returns boolean indicating if user has the permission
 */
export function userHasPermissionType(
  user: User | null, 
  permissionType: string, 
  action: 'read' | 'crud' | 'export'
): boolean {
  if (!user) return false;
  
  const userRoles = getUserRoles(user);
  
  return userRoles.some(role => {
    // Check for specific permission roles
    const capitalizedType = permissionType.charAt(0).toUpperCase() + permissionType.slice(1);
    
    if (action === 'read') {
      // Read permission can be granted by Read or CRUD roles
      if (role === `${capitalizedType}_Read` || role === `${capitalizedType}_CRUD`) return true;
    } else if (action === 'crud') {
      // CRUD permission requires CRUD role
      if (role === `${capitalizedType}_CRUD`) return true;
    } else if (action === 'export') {
      // Export permission requires Export role
      if (role === `${capitalizedType}_Export`) return true;
    }
    
    return false;
  });
}

/**
 * Enhanced role checking that validates permission + region combinations
 * This is the main function for checking new role structure access
 * @param user - User object or null
 * @param requiredPermissions - Array of required permissions (e.g., ['members_read', 'events_crud'])
 * @param targetRegion - Optional specific region to check access for
 * @returns boolean indicating if user has all required permissions with appropriate regional access
 */
export function validatePermissionWithRegion(
  user: User | null,
  requiredPermissions: string[],
  targetRegion?: string
): boolean {
  if (!user || !requiredPermissions.length) return false;
  
  // User must have ALL required permissions
  return requiredPermissions.every(permission => 
    userHasPermissionWithRegion(user, permission, targetRegion)
  );
}

// Role-to-permission mapping based on H-DCN organizational structure
// Updated for new permission + region role combinations
export const ROLE_PERMISSIONS: PermissionConfig = {
  // Basic member role
  hdcnLeden: {
    members: { read: ['own'], write: ['own_personal'] },
    webshop: { read: ['all'], write: ['own'] },
    events: { read: ['public'] },
    products: { read: ['catalog'] }
  },

  // Member management roles - Updated to new permission + region structure
  Members_CRUD: {
    members: { read: ['all'], write: ['all'] },
    events: { read: ['all'] },
    products: { read: ['all'] },
    communication: { read: ['all'] },
    system: { read: ['user_management'], write: ['user_management'] }
  },

  Members_Read: {
    members: { read: ['all'] },
    events: { read: ['all'] },
    products: { read: ['all'] },
    communication: { read: ['all'] }
  },

  Members_Status_Approve: {
    members: { write: ['status'] }
  },

  Members_Export: {
    members: { read: ['all'] },
    communication: { write: ['export'] }
  },

  // Event management roles - Updated to new permission + region structure
  Events_Read: {
    events: { read: ['all'] }
  },

  Events_CRUD: {
    events: { read: ['all'], write: ['all'] }
  },

  Events_Export: {
    events: { read: ['all'] },
    communication: { write: ['export'] }
  },

  // Product management roles - Updated to new permission + region structure
  Products_Read: {
    products: { read: ['all'] }
  },

  Products_CRUD: {
    products: { read: ['all'], write: ['all'] }
  },

  Products_Export: {
    products: { read: ['all'], write: ['export'] }
  },

  // Communication roles - Updated to new permission + region structure
  Communication_Read: {
    communication: { read: ['all'] }
  },

  Communication_CRUD: {
    communication: { read: ['all'], write: ['all'] }
  },

  Communication_Export: {
    communication: { read: ['all'], write: ['export'] }
  },

  // System administration roles
  System_User_Management: {
    system: { read: ['user_management'], write: ['user_management'] }
  },

  System_Logs_Read: {
    system: { read: ['logs'] }
  },

  // Regional roles (Regio_All is kept as it's the only _All role that still exists)
  Regio_All: {
    members: { read: ['all'] },
    events: { read: ['all'] },
    products: { read: ['all'] },
    communication: { read: ['all'] }
  },

  // Individual regional roles - New permission + region structure
  Regio_Utrecht: {
    members: { read: ['region_utrecht'] },
    events: { read: ['region_utrecht'] },
    products: { read: ['all'] },
    communication: { read: ['region_utrecht'] }
  },

  Regio_Limburg: {
    members: { read: ['region_limburg'] },
    events: { read: ['region_limburg'] },
    products: { read: ['all'] },
    communication: { read: ['region_limburg'] }
  },

  'Regio_Groningen/Drenthe': {
    members: { read: ['region_groningen_drenthe'] },
    events: { read: ['region_groningen_drenthe'] },
    products: { read: ['all'] },
    communication: { read: ['region_groningen_drenthe'] }
  },

  'Regio_Zuid-Holland': {
    members: { read: ['region_zuid_holland'] },
    events: { read: ['region_zuid_holland'] },
    products: { read: ['all'] },
    communication: { read: ['region_zuid_holland'] }
  },

  'Regio_Noord-Holland': {
    members: { read: ['region_noord_holland'] },
    events: { read: ['region_noord_holland'] },
    products: { read: ['all'] },
    communication: { read: ['region_noord_holland'] }
  },

  Regio_Oost: {
    members: { read: ['region_oost'] },
    events: { read: ['region_oost'] },
    products: { read: ['all'] },
    communication: { read: ['region_oost'] }
  },

  'Regio_Brabant/Zeeland': {
    members: { read: ['region_brabant_zeeland'] },
    events: { read: ['region_brabant_zeeland'] },
    products: { read: ['all'] },
    communication: { read: ['region_brabant_zeeland'] }
  },

  Regio_Friesland: {
    members: { read: ['region_friesland'] },
    events: { read: ['region_friesland'] },
    products: { read: ['all'] },
    communication: { read: ['region_friesland'] }
  },

  Regio_Duitsland: {
    members: { read: ['region_duitsland'] },
    events: { read: ['region_duitsland'] },
    products: { read: ['all'] },
    communication: { read: ['region_duitsland'] }
  },

  // Webshop Management
  Webshop_Management: {
    members: { read: ['basic'] },
    events: { read: ['all'] },
    products: { read: ['all'], write: ['all'] },
    communication: { read: ['all'] },
    webshop: { read: ['all'], write: ['all'] }
  },

  // Special Application Role
  'Verzoek Lid': {
    // No permissions except signup process
  }
};

/**
 * Calculates combined permissions from multiple roles
 * @param roles - Array of role names assigned to the user
 * @returns Combined permission configuration with all permissions from assigned roles
 */
export function calculatePermissions(roles: string[]): RolePermissions {
  const combinedPermissions: RolePermissions = {};

  roles.forEach((role) => {
    const rolePermissions = ROLE_PERMISSIONS[role];
    if (rolePermissions) {
      // Merge permissions from this role into combined permissions
      Object.keys(rolePermissions).forEach((functionName) => {
        if (!combinedPermissions[functionName]) {
          combinedPermissions[functionName] = { read: [], write: [] };
        }

        const roleFunctionPerms = rolePermissions[functionName];
        const combinedFunctionPerms = combinedPermissions[functionName];

        // Combine read permissions (union of all role permissions)
        if (roleFunctionPerms.read) {
          const existingRead = combinedFunctionPerms.read || [];
          combinedFunctionPerms.read = Array.from(new Set([...existingRead, ...roleFunctionPerms.read]));
        }

        // Combine write permissions (union of all role permissions)
        if (roleFunctionPerms.write) {
          const existingWrite = combinedFunctionPerms.write || [];
          combinedFunctionPerms.write = Array.from(new Set([...existingWrite, ...roleFunctionPerms.write]));
        }
      });
    }
  });

  return combinedPermissions;
}

interface FunctionPermissions {
  read?: string[];
  write?: string[];
}

interface RolePermissions {
  [functionName: string]: FunctionPermissions;
}

interface PermissionConfig {
  [roleName: string]: RolePermissions;
}

interface AccessibleFunctions {
  [functionName: string]: {
    read: boolean;
    write: boolean;
  };
}

// Function Permission Manager using existing parameter table
export class FunctionPermissionManager {
  private userGroups: string[];
  private permissions: RolePermissions;

  constructor(user: User, permissionConfig: RolePermissions = {}) {
    this.userGroups = getUserRoles(user);
    this.permissions = permissionConfig;
  }

  hasAccess(functionName: string, action: 'read' | 'write' = 'read'): boolean {
    const functionPerms = this.permissions[functionName];
    if (!functionPerms) {
      return false;
    }

    const allowedGroups = functionPerms[action] || [];
    
    const hasAccess = this.userGroups.some(userGroup => {
      return allowedGroups.some(allowedGroup => {
        // Direct group matching
        if (userGroup === allowedGroup) {
          return true;
        }
        
        // Handle membership type-based access patterns
        if (allowedGroup.startsWith('membership_')) {
          // This would be checked against user's membership type in a real implementation
          if (this.userGroups.includes('hdcnLeden')) {
            return true;
          }
        }
        
        // Handle region-based access patterns
        if (allowedGroup.startsWith('region_')) {
          // This would be checked against user's region in a real implementation
          const hasRegionalRole = this.userGroups.some(group => group.startsWith('Regio_'));
          if (hasRegionalRole) {
            return true;
          }
        }
        
        return false;
      });
    });
    
    return hasAccess;
  }

  /**
   * Enhanced access check that supports field-level permissions
   * @param functionName - The function/module name
   * @param action - The action type (read/write)
   * @param context - Additional context for permission checking (e.g., record ownership, region)
   * @returns boolean indicating if access is allowed
   */
  hasFieldAccess(functionName: string, action: 'read' | 'write' = 'read', context?: { isOwnRecord?: boolean; fieldType?: string; userRegion?: string }): boolean {
    const functionPerms = this.permissions[functionName];
    if (!functionPerms) return false;

    const allowedPermissions = functionPerms[action] || [];
    
    return this.userGroups.some(userGroup => {
      return allowedPermissions.some(permission => {
        // Handle legacy group-based permissions (backward compatibility)
        if (userGroup === permission) return true;
        
        // Handle wildcard patterns like hdcnRegio_*
        if (permission.endsWith('*')) {
          const prefix = permission.slice(0, -1);
          if (userGroup.startsWith(prefix)) return true;
        }
        
        // Handle field-level permissions
        switch (permission) {
          case 'all':
            return true;
          case 'own':
            return context?.isOwnRecord === true;
          case 'own_personal':
            return context?.isOwnRecord === true && (context?.fieldType === 'personal' || context?.fieldType === 'motorcycle');
          case 'status':
            return context?.fieldType === 'status';
          case 'public':
            return true; // Public access
          case 'catalog':
            return true; // Catalog browsing
          case 'basic':
            return true; // Basic access level
          case 'financial':
            return context?.fieldType === 'financial';
          case 'export':
            return true; // Export permissions
          case 'user_management':
            return this.userGroups.includes('System_User_Management');
          case 'logs':
            return this.userGroups.includes('System_Logs_Read');
          
          // Regional permissions - Updated for new role structure
          case 'region_utrecht':
            return context?.userRegion === 'utrecht' || this.userGroups.includes('Regio_Utrecht') || this.userGroups.includes('Regio_All');
          case 'region_limburg':
            return context?.userRegion === 'limburg' || this.userGroups.includes('Regio_Limburg') || this.userGroups.includes('Regio_All');
          case 'region_groningen_drenthe':
            return context?.userRegion === 'groningen_drenthe' || this.userGroups.includes('Regio_Groningen/Drenthe') || this.userGroups.includes('Regio_All');
          case 'region_zuid_holland':
            return context?.userRegion === 'zuid_holland' || this.userGroups.includes('Regio_Zuid-Holland') || this.userGroups.includes('Regio_All');
          case 'region_noord_holland':
            return context?.userRegion === 'noord_holland' || this.userGroups.includes('Regio_Noord-Holland') || this.userGroups.includes('Regio_All');
          case 'region_oost':
            return context?.userRegion === 'oost' || this.userGroups.includes('Regio_Oost') || this.userGroups.includes('Regio_All');
          case 'region_brabant_zeeland':
            return context?.userRegion === 'brabant_zeeland' || this.userGroups.includes('Regio_Brabant/Zeeland') || this.userGroups.includes('Regio_All');
          case 'region_friesland':
            return context?.userRegion === 'friesland' || this.userGroups.includes('Regio_Friesland') || this.userGroups.includes('Regio_All');
          case 'region_duitsland':
            return context?.userRegion === 'duitsland' || this.userGroups.includes('Regio_Duitsland') || this.userGroups.includes('Regio_All');
          case 'region_noord_holland':
            return context?.userRegion === 'noord_holland' || this.userGroups.includes('Regio_Noord-Holland') || this.userGroups.includes('Regio_All');
          
          default:
            return false;
        }
      });
    });
  }

  static async create(user: User): Promise<FunctionPermissionManager> {
    const userGroups = getUserRoles(user);
    
    // Use the updated ROLE_PERMISSIONS configuration that supports new role structure
    const permissionManager = new FunctionPermissionManager(user, ROLE_PERMISSIONS);
    
    console.log('🔧 Created permission manager for new role structure');
    console.log('👤 User roles:', userGroups);
    
    return permissionManager;
  }

  // Get all accessible functions for current user
  getAccessibleFunctions(): AccessibleFunctions {
    const accessible = {};
    
    Object.keys(this.permissions).forEach(functionName => {
      accessible[functionName] = {
        read: this.hasAccess(functionName, 'read'),
        write: this.hasAccess(functionName, 'write')
      };
    });
    
    return accessible;
  }
}

/**
 * Enhanced Function Permission Manager factory for new permission + region role structure
 * Creates a permission manager that properly handles the new role combinations
 * @param user - User object with roles
 * @returns FunctionPermissionManager configured for new role structure
 */
export async function createEnhancedPermissionManager(user: User): Promise<FunctionPermissionManager> {
  const userRoles = getUserRoles(user);
  
  // Use the updated ROLE_PERMISSIONS configuration that supports new role structure
  const permissionManager = new FunctionPermissionManager(user, ROLE_PERMISSIONS);
  
  console.log('🔧 Created enhanced permission manager for new role structure');
  console.log('👤 User roles:', userRoles);
  
  return permissionManager;
}

/**
 * Utility function to check if user has permission + region combination for UI components
 * This is the main function that UI components should use for permission checks
 * @param user - User object or null
 * @param functionName - The function/feature name (e.g., 'members', 'events', 'products')
 * @param action - The action type ('read' or 'write')
 * @param targetRegion - Optional specific region to check access for
 * @returns boolean indicating if user has access
 */
export function checkUIPermission(
  user: User | null,
  functionName: string,
  action: 'read' | 'write' = 'read',
  targetRegion?: string
): boolean {
  if (!user) return false;
  
  // Map UI action to permission action
  const permissionAction = action === 'write' ? 'crud' : 'read';
  
  // Check if user has the required permission type
  const hasPermission = userHasPermissionType(user, functionName, permissionAction);
  if (!hasPermission) {
    console.log(`❌ User lacks ${functionName} ${action} permission`);
    return false;
  }
  
  // Check regional access using the correct permission format
  const permissionString = `${functionName}_${permissionAction}`;
  const hasRegionalAccess = userHasPermissionWithRegion(user, permissionString, targetRegion);
  if (!hasRegionalAccess) {
    return false; // Error already logged in userHasPermissionWithRegion
  }
  
  console.log(`✅ UI Permission granted: ${functionName}.${action}${targetRegion ? ` in ${targetRegion}` : ''}`);
  return true;
}

// Default function permissions template for parameter table - Updated for new role structure
export const DEFAULT_FUNCTION_PERMISSIONS = {
  id: 'default',
  value: {
    members: {
      read: ['Members_Read', 'Members_CRUD'],
      write: ['Members_CRUD']
    },
    events: {
      read: ['Events_Read', 'Events_CRUD'],
      write: ['Events_CRUD']
    },
    products: {
      read: ['Products_Read', 'Products_CRUD'],
      write: ['Products_CRUD']
    },
    communication: {
      read: ['Communication_Read', 'Communication_CRUD'],
      write: ['Communication_CRUD']
    },
    webshop: {
      read: ['hdcnLeden', 'Webshop_Management'],
      write: ['Webshop_Management']
    },
    system: {
      read: ['System_User_Management', 'System_Logs_Read'],
      write: ['System_User_Management']
    }
  }
};