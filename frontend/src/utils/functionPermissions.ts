import { getParameters } from './parameterService';
import { getAuthHeadersForGet } from './authHeaders';
import { getCurrentUserRoles } from '../services/authService';
import { HDCNGroup } from '../types/user';

interface User {
  signInUserSession?: {
    accessToken?: {
      payload: {
        'cognito:groups'?: string[];
      };
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

  // Legacy approach: Extract from JWT token payload
  if (!user?.signInUserSession?.accessToken?.payload) {
    return [];
  }
  
  const cognitoGroups = user.signInUserSession.accessToken.payload['cognito:groups'];
  return cognitoGroups || [];
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

// Role-to-permission mapping based on H-DCN organizational structure
export const ROLE_PERMISSIONS: PermissionConfig = {
  // Basic member role
  hdcnLeden: {
    members: { read: ['own'], write: ['own_personal'] },
    webshop: { read: ['all'], write: ['own'] },
    events: { read: ['public'] },
    products: { read: ['catalog'] }
  },

  // Member management roles
  Members_CRUD_All: {
    members: { read: ['all'], write: ['all'] },
    events: { read: ['all'] },
    products: { read: ['all'] },
    communication: { read: ['all'] },
    system: { read: ['user_management'], write: ['user_management'] }
  },

  Members_Read_All: {
    members: { read: ['all'] },
    events: { read: ['all'] },
    products: { read: ['all'] },
    communication: { read: ['all'] }
  },

  Members_Status_Approve: {
    members: { write: ['status'] }
  },

  Members_Export_All: {
    members: { read: ['all'] },
    communication: { write: ['export'] }
  },

  // Event management roles
  Events_Read_All: {
    events: { read: ['all'] }
  },

  Events_CRUD_All: {
    events: { read: ['all'], write: ['all'] }
  },

  Events_Export_All: {
    events: { read: ['all'] },
    communication: { write: ['export'] }
  },

  // Product management roles
  Products_Read_All: {
    products: { read: ['all'] }
  },

  Products_CRUD_All: {
    products: { read: ['all'], write: ['all'] }
  },

  Products_Read_Financial: {
    products: { read: ['financial'] }
  },

  // Communication roles
  Communication_Read_All: {
    communication: { read: ['all'] }
  },

  Communication_CRUD_All: {
    communication: { read: ['all'], write: ['all'] }
  },

  Communication_Export_All: {
    communication: { read: ['all'], write: ['export'] }
  },

  // System administration roles
  System_User_Management: {
    system: { read: ['user_management'], write: ['user_management'] }
  },

  System_CRUD_All: {
    system: { read: ['all'], write: ['all'] }
  },

  System_Logs_Read: {
    system: { read: ['logs'] }
  },

  // National organizational roles (General Board)
  National_Chairman: {
    members: { read: ['all'], write: ['status'] },
    events: { read: ['all'] },
    products: { read: ['all'] },
    communication: { read: ['all'] },
    system: { read: ['logs'] }
  },

  National_Secretary: {
    members: { read: ['all'] },
    events: { read: ['all'] },
    products: { read: ['all'] },
    communication: { read: ['all'], write: ['export'] },
    system: { read: ['logs'] }
  },

  National_Treasurer: {
    members: { read: ['financial'] },
    events: { read: ['financial'] },
    products: { read: ['financial'] }
  },

  Vice_Chairman: {
    members: { read: ['all'] },
    events: { read: ['all'] },
    products: { read: ['all'] },
    communication: { read: ['all'] }
  },

  // Supporting function roles
  Webmaster: {
    members: { read: ['all'] },
    events: { read: ['all'], write: ['all'] },
    products: { read: ['all'], write: ['all'] },
    communication: { read: ['all'], write: ['all'] },
    system: { read: ['all'], write: ['all'] }
  },

  Tour_Commissioner: {
    members: { read: ['all'] },
    events: { read: ['all'], write: ['all'] },
    products: { read: ['all'] },
    communication: { read: ['all'], write: ['export'] }
  },

  Club_Magazine_Editorial: {
    members: { read: ['all'] },
    events: { read: ['all'] },
    products: { read: ['all'] },
    communication: { read: ['all'], write: ['all'] }
  },

  Webshop_Management: {
    members: { read: ['basic'] },
    events: { read: ['all'] },
    products: { read: ['all'], write: ['all'] },
    communication: { read: ['all'] }
  },

  // Regional roles (template for all 9 regions)
  // Region 1: Noord-Holland
  Regional_Chairman_Region1: {
    members: { read: ['region1'] },
    events: { read: ['region1'], write: ['region1'] },
    products: { read: ['all'] },
    communication: { read: ['region1'], write: ['export_region1'] }
  },

  Regional_Secretary_Region1: {
    members: { read: ['region1'] },
    events: { read: ['region1'] },
    products: { read: ['all'] },
    communication: { read: ['region1'], write: ['export_region1'] }
  },

  Regional_Treasurer_Region1: {
    members: { read: ['region1_financial'] },
    events: { read: ['region1_financial'] },
    products: { read: ['financial'] }
  },

  Regional_Volunteer_Region1: {
    members: { read: ['region1_basic'] },
    events: { read: ['region1'] },
    products: { read: ['all'] }
  },

  // Region 2: Zuid-Holland
  Regional_Chairman_Region2: {
    members: { read: ['region2'] },
    events: { read: ['region2'], write: ['region2'] },
    products: { read: ['all'] },
    communication: { read: ['region2'], write: ['export_region2'] }
  },

  Regional_Secretary_Region2: {
    members: { read: ['region2'] },
    events: { read: ['region2'] },
    products: { read: ['all'] },
    communication: { read: ['region2'], write: ['export_region2'] }
  },

  Regional_Treasurer_Region2: {
    members: { read: ['region2_financial'] },
    events: { read: ['region2_financial'] },
    products: { read: ['financial'] }
  },

  Regional_Volunteer_Region2: {
    members: { read: ['region2_basic'] },
    events: { read: ['region2'] },
    products: { read: ['all'] }
  },

  // Region 3: Friesland
  Regional_Chairman_Region3: {
    members: { read: ['region3'] },
    events: { read: ['region3'], write: ['region3'] },
    products: { read: ['all'] },
    communication: { read: ['region3'], write: ['export_region3'] }
  },

  Regional_Secretary_Region3: {
    members: { read: ['region3'] },
    events: { read: ['region3'] },
    products: { read: ['all'] },
    communication: { read: ['region3'], write: ['export_region3'] }
  },

  Regional_Treasurer_Region3: {
    members: { read: ['region3_financial'] },
    events: { read: ['region3_financial'] },
    products: { read: ['financial'] }
  },

  Regional_Volunteer_Region3: {
    members: { read: ['region3_basic'] },
    events: { read: ['region3'] },
    products: { read: ['all'] }
  },

  // Region 4: Utrecht
  Regional_Chairman_Region4: {
    members: { read: ['region4'] },
    events: { read: ['region4'], write: ['region4'] },
    products: { read: ['all'] },
    communication: { read: ['region4'], write: ['export_region4'] }
  },

  Regional_Secretary_Region4: {
    members: { read: ['region4'] },
    events: { read: ['region4'] },
    products: { read: ['all'] },
    communication: { read: ['region4'], write: ['export_region4'] }
  },

  Regional_Treasurer_Region4: {
    members: { read: ['region4_financial'] },
    events: { read: ['region4_financial'] },
    products: { read: ['financial'] }
  },

  Regional_Volunteer_Region4: {
    members: { read: ['region4_basic'] },
    events: { read: ['region4'] },
    products: { read: ['all'] }
  },

  // Region 5: Oost
  Regional_Chairman_Region5: {
    members: { read: ['region5'] },
    events: { read: ['region5'], write: ['region5'] },
    products: { read: ['all'] },
    communication: { read: ['region5'], write: ['export_region5'] }
  },

  Regional_Secretary_Region5: {
    members: { read: ['region5'] },
    events: { read: ['region5'] },
    products: { read: ['all'] },
    communication: { read: ['region5'], write: ['export_region5'] }
  },

  Regional_Treasurer_Region5: {
    members: { read: ['region5_financial'] },
    events: { read: ['region5_financial'] },
    products: { read: ['financial'] }
  },

  Regional_Volunteer_Region5: {
    members: { read: ['region5_basic'] },
    events: { read: ['region5'] },
    products: { read: ['all'] }
  },

  // Region 6: Limburg
  Regional_Chairman_Region6: {
    members: { read: ['region6'] },
    events: { read: ['region6'], write: ['region6'] },
    products: { read: ['all'] },
    communication: { read: ['region6'], write: ['export_region6'] }
  },

  Regional_Secretary_Region6: {
    members: { read: ['region6'] },
    events: { read: ['region6'] },
    products: { read: ['all'] },
    communication: { read: ['region6'], write: ['export_region6'] }
  },

  Regional_Treasurer_Region6: {
    members: { read: ['region6_financial'] },
    events: { read: ['region6_financial'] },
    products: { read: ['financial'] }
  },

  Regional_Volunteer_Region6: {
    members: { read: ['region6_basic'] },
    events: { read: ['region6'] },
    products: { read: ['all'] }
  },

  // Region 7: Groningen/Drente
  Regional_Chairman_Region7: {
    members: { read: ['region7'] },
    events: { read: ['region7'], write: ['region7'] },
    products: { read: ['all'] },
    communication: { read: ['region7'], write: ['export_region7'] }
  },

  Regional_Secretary_Region7: {
    members: { read: ['region7'] },
    events: { read: ['region7'] },
    products: { read: ['all'] },
    communication: { read: ['region7'], write: ['export_region7'] }
  },

  Regional_Treasurer_Region7: {
    members: { read: ['region7_financial'] },
    events: { read: ['region7_financial'] },
    products: { read: ['financial'] }
  },

  Regional_Volunteer_Region7: {
    members: { read: ['region7_basic'] },
    events: { read: ['region7'] },
    products: { read: ['all'] }
  },

  // Region 8: Noord-Brabant/Zeeland
  Regional_Chairman_Region8: {
    members: { read: ['region8'] },
    events: { read: ['region8'], write: ['region8'] },
    products: { read: ['all'] },
    communication: { read: ['region8'], write: ['export_region8'] }
  },

  Regional_Secretary_Region8: {
    members: { read: ['region8'] },
    events: { read: ['region8'] },
    products: { read: ['all'] },
    communication: { read: ['region8'], write: ['export_region8'] }
  },

  Regional_Treasurer_Region8: {
    members: { read: ['region8_financial'] },
    events: { read: ['region8_financial'] },
    products: { read: ['financial'] }
  },

  Regional_Volunteer_Region8: {
    members: { read: ['region8_basic'] },
    events: { read: ['region8'] },
    products: { read: ['all'] }
  },

  // Region 9: Duitsland
  Regional_Chairman_Region9: {
    members: { read: ['region9'] },
    events: { read: ['region9'], write: ['region9'] },
    products: { read: ['all'] },
    communication: { read: ['region9'], write: ['export_region9'] }
  },

  Regional_Secretary_Region9: {
    members: { read: ['region9'] },
    events: { read: ['region9'] },
    products: { read: ['all'] },
    communication: { read: ['region9'], write: ['export_region9'] }
  },

  Regional_Treasurer_Region9: {
    members: { read: ['region9_financial'] },
    events: { read: ['region9_financial'] },
    products: { read: ['financial'] }
  },

  Regional_Volunteer_Region9: {
    members: { read: ['region9_basic'] },
    events: { read: ['region9'] },
    products: { read: ['all'] }
  },

  // Legacy admin role support
  hdcnAdmins: {
    members: { read: ['all'], write: ['all'] },
    events: { read: ['all'], write: ['all'] },
    products: { read: ['all'], write: ['all'] },
    orders: { read: ['all'], write: ['all'] },
    webshop: { read: ['all'], write: ['all'] },
    parameters: { read: ['all'], write: ['all'] },
    memberships: { read: ['all'], write: ['all'] },
    system: { read: ['all'], write: ['all'] }
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
          combinedFunctionPerms.read = [...new Set([...existingRead, ...roleFunctionPerms.read])];
        }

        // Combine write permissions (union of all role permissions)
        if (roleFunctionPerms.write) {
          const existingWrite = combinedFunctionPerms.write || [];
          combinedFunctionPerms.write = [...new Set([...existingWrite, ...roleFunctionPerms.write])];
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
      // BACKWARD COMPATIBILITY: If no specific function permissions exist,
      // check if user has legacy admin access
      if (this.userGroups.includes('hdcnAdmins')) {
        console.log(`🔄 Backward compatibility: Granting ${action} access to ${functionName} for hdcnAdmins`);
        return true;
      }
      
      // BACKWARD COMPATIBILITY: For webshop, allow basic member access even without explicit config
      if (functionName === 'webshop' && this.userGroups.includes('hdcnLeden')) {
        console.log(`🔄 Backward compatibility: Granting ${action} access to webshop for hdcnLeden`);
        return true;
      }
      
      return false;
    }

    const allowedGroups = functionPerms[action] || [];
    
    const hasAccess = this.userGroups.some(userGroup => {
      return allowedGroups.some(allowedGroup => {
        // BACKWARD COMPATIBILITY: Handle wildcard patterns like hdcnRegio_*
        if (allowedGroup.endsWith('*')) {
          const prefix = allowedGroup.slice(0, -1);
          return userGroup.startsWith(prefix);
        }
        
        // BACKWARD COMPATIBILITY: Direct group matching (legacy behavior)
        if (userGroup === allowedGroup) {
          return true;
        }
        
        // ENHANCED: Handle membership type-based access patterns
        if (allowedGroup.startsWith('membership_')) {
          // This would be checked against user's membership type in a real implementation
          // For now, we'll assume basic members have access to basic membership features
          if (this.userGroups.includes('hdcnLeden')) {
            return true;
          }
        }
        
        // ENHANCED: Handle region-based access patterns
        if (allowedGroup.startsWith('region_')) {
          // This would be checked against user's region in a real implementation
          // For now, we'll check if user has any regional role
          const hasRegionalRole = this.userGroups.some(group => group.includes('Regional_'));
          if (hasRegionalRole) {
            return true;
          }
        }
        
        // BACKWARD COMPATIBILITY: Handle legacy regional patterns
        // Support both old hdcnRegio_X_Role and new Regional_Role_RegionX formats
        if (allowedGroup.startsWith('hdcnRegio_') && userGroup.includes('Regional_')) {
          const regionMatch = allowedGroup.match(/hdcnRegio_(\d+)_/);
          if (regionMatch) {
            const regionNumber = regionMatch[1];
            return userGroup.includes(`Region${regionNumber}`);
          }
        }
        
        // BACKWARD COMPATIBILITY: Handle reverse mapping - new roles accessing legacy patterns
        if (allowedGroup.startsWith('hdcnRegio_') && allowedGroup.endsWith('_Voorzitter') && userGroup.includes('Regional_Chairman_')) {
          const regionMatch = allowedGroup.match(/hdcnRegio_(\d+)_/);
          if (regionMatch) {
            const regionNumber = regionMatch[1];
            return userGroup.includes(`Region${regionNumber}`);
          }
        }
        
        if (allowedGroup.startsWith('hdcnRegio_') && allowedGroup.endsWith('_Secretaris') && userGroup.includes('Regional_Secretary_')) {
          const regionMatch = allowedGroup.match(/hdcnRegio_(\d+)_/);
          if (regionMatch) {
            const regionNumber = regionMatch[1];
            return userGroup.includes(`Region${regionNumber}`);
          }
        }
        
        if (allowedGroup.startsWith('hdcnRegio_') && allowedGroup.endsWith('_Penningmeester') && userGroup.includes('Regional_Treasurer_')) {
          const regionMatch = allowedGroup.match(/hdcnRegio_(\d+)_/);
          if (regionMatch) {
            const regionNumber = regionMatch[1];
            return userGroup.includes(`Region${regionNumber}`);
          }
        }
        
        if (allowedGroup.startsWith('hdcnRegio_') && allowedGroup.endsWith('_Vrijwilliger') && userGroup.includes('Regional_Volunteer_')) {
          const regionMatch = allowedGroup.match(/hdcnRegio_(\d+)_/);
          if (regionMatch) {
            const regionNumber = regionMatch[1];
            return userGroup.includes(`Region${regionNumber}`);
          }
        }
        
        return false;
      });
    });
    
    // BACKWARD COMPATIBILITY: Additional fallback for admin users
    if (!hasAccess && this.userGroups.includes('hdcnAdmins')) {
      console.log(`🔄 Backward compatibility: Admin fallback for ${functionName}.${action}`);
      return true;
    }
    
    return hasAccess;
  }

  /**
   * BACKWARD COMPATIBILITY: Legacy permission check method
   * Supports old permission check patterns while transitioning to new role-based system
   * @param legacyFunctionName - Legacy function name that might not match new naming
   * @param action - The action type (read/write)
   * @returns boolean indicating if access is allowed
   */
  hasLegacyAccess(legacyFunctionName: string, action: 'read' | 'write' = 'read'): boolean {
    // BACKWARD COMPATIBILITY: Map legacy function names to new function names
    const legacyFunctionMapping: { [key: string]: string } = {
      'member': 'members',
      'event': 'events',
      'product': 'products',
      'order': 'orders',
      'parameter': 'parameters',
      'membership': 'memberships',
      'shop': 'webshop',
      'webshop': 'webshop'
    };
    
    const mappedFunctionName = legacyFunctionMapping[legacyFunctionName] || legacyFunctionName;
    
    // Use the standard hasAccess method with mapped function name
    return this.hasAccess(mappedFunctionName, action);
  }

  /**
   * BACKWARD COMPATIBILITY: Check if user belongs to any legacy group patterns
   * @param legacyGroupPattern - Legacy group pattern (e.g., 'hdcnRegio_*', 'hdcnAdmins')
   * @returns boolean indicating if user belongs to the legacy group pattern
   */
  hasLegacyGroup(legacyGroupPattern: string): boolean {
    if (legacyGroupPattern.endsWith('*')) {
      const prefix = legacyGroupPattern.slice(0, -1);
      return this.userGroups.some(group => group.startsWith(prefix));
    }
    
    return this.userGroups.includes(legacyGroupPattern);
  }

  /**
   * BACKWARD COMPATIBILITY: Get user's legacy group memberships
   * Maps new role-based groups back to legacy group names for compatibility
   * @returns Array of legacy group names
   */
  getLegacyGroups(): string[] {
    const legacyGroups: string[] = [];
    
    this.userGroups.forEach(group => {
      // Keep existing legacy groups as-is
      if (group.startsWith('hdcn')) {
        legacyGroups.push(group);
      }
      
      // Map new role-based groups to legacy equivalents
      if (group.includes('Regional_') && group.includes('Region')) {
        const regionMatch = group.match(/Region(\d+)/);
        if (regionMatch) {
          const regionNumber = regionMatch[1];
          if (group.includes('Chairman')) {
            legacyGroups.push(`hdcnRegio_${regionNumber}_Voorzitter`);
          } else if (group.includes('Secretary')) {
            legacyGroups.push(`hdcnRegio_${regionNumber}_Secretaris`);
          } else if (group.includes('Treasurer')) {
            legacyGroups.push(`hdcnRegio_${regionNumber}_Penningmeester`);
          } else if (group.includes('Volunteer')) {
            legacyGroups.push(`hdcnRegio_${regionNumber}_Vrijwilliger`);
          }
        }
      }
      
      // Map national roles to legacy admin groups
      if (group.includes('Members_CRUD_All') || group.includes('System_User_Management')) {
        if (!legacyGroups.includes('hdcnAdmins')) {
          legacyGroups.push('hdcnAdmins');
        }
      }
    });
    
    return [...new Set(legacyGroups)]; // Remove duplicates
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
            return this.userGroups.includes('System_User_Management') || this.userGroups.includes('hdcnAdmins');
          case 'logs':
            return this.userGroups.includes('System_Logs_Read') || this.userGroups.includes('hdcnAdmins');
          
          // Regional permissions
          case 'region1':
          case 'region1_basic':
          case 'region1_financial':
            return context?.userRegion === '1' || this.userGroups.some(group => group.includes('Region1'));
          case 'region2':
          case 'region2_basic':
          case 'region2_financial':
            return context?.userRegion === '2' || this.userGroups.some(group => group.includes('Region2'));
          case 'region3':
          case 'region3_basic':
          case 'region3_financial':
            return context?.userRegion === '3' || this.userGroups.some(group => group.includes('Region3'));
          case 'region4':
          case 'region4_basic':
          case 'region4_financial':
            return context?.userRegion === '4' || this.userGroups.some(group => group.includes('Region4'));
          case 'region5':
          case 'region5_basic':
          case 'region5_financial':
            return context?.userRegion === '5' || this.userGroups.some(group => group.includes('Region5'));
          case 'region6':
          case 'region6_basic':
          case 'region6_financial':
            return context?.userRegion === '6' || this.userGroups.some(group => group.includes('Region6'));
          case 'region7':
          case 'region7_basic':
          case 'region7_financial':
            return context?.userRegion === '7' || this.userGroups.some(group => group.includes('Region7'));
          case 'region8':
          case 'region8_basic':
          case 'region8_financial':
            return context?.userRegion === '8' || this.userGroups.some(group => group.includes('Region8'));
          case 'region9':
          case 'region9_basic':
          case 'region9_financial':
            return context?.userRegion === '9' || this.userGroups.some(group => group.includes('Region9'));
          
          // Export permissions for regions
          case 'export_region1':
            return this.userGroups.some(group => group.includes('Region1') && (group.includes('Secretary') || group.includes('Chairman')));
          case 'export_region2':
            return this.userGroups.some(group => group.includes('Region2') && (group.includes('Secretary') || group.includes('Chairman')));
          case 'export_region3':
            return this.userGroups.some(group => group.includes('Region3') && (group.includes('Secretary') || group.includes('Chairman')));
          case 'export_region4':
            return this.userGroups.some(group => group.includes('Region4') && (group.includes('Secretary') || group.includes('Chairman')));
          case 'export_region5':
            return this.userGroups.some(group => group.includes('Region5') && (group.includes('Secretary') || group.includes('Chairman')));
          case 'export_region6':
            return this.userGroups.some(group => group.includes('Region6') && (group.includes('Secretary') || group.includes('Chairman')));
          case 'export_region7':
            return this.userGroups.some(group => group.includes('Region7') && (group.includes('Secretary') || group.includes('Chairman')));
          case 'export_region8':
            return this.userGroups.some(group => group.includes('Region8') && (group.includes('Secretary') || group.includes('Chairman')));
          case 'export_region9':
            return this.userGroups.some(group => group.includes('Region9') && (group.includes('Secretary') || group.includes('Chairman')));
          
          default:
            return false;
        }
      });
    });
  }

  static async create(user: User): Promise<FunctionPermissionManager> {
    const userGroups = getUserRoles(user);
    const isAdmin = userGroups.includes('hdcnAdmins');
    
    console.log('🔍 FunctionPermissionManager.create - User groups:', userGroups);
    console.log('🔍 FunctionPermissionManager.create - Is admin:', isAdmin);
    
    try {
      // Wait a bit for initialization to complete
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // Test direct API call
      try {
        const headers = await getAuthHeadersForGet();
        const apiResponse = await fetch(`${process.env.REACT_APP_API_BASE_URL || 'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod'}/parameters`, {
          headers
        });
        const apiData = await apiResponse.json();
        console.log('🔍 Direct API call - all parameters:', apiData.map(p => p.name));
        const functionPermsFromAPI = apiData.find(p => p.name === 'function_permissions');
        console.log('🔍 Direct API - function_permissions:', functionPermsFromAPI);
      } catch (apiError) {
        console.log('🔍 API call failed:', apiError);
      }
      
      const parameters = await getParameters();
      console.log('🔍 Parameters loaded:', Object.keys(parameters));
      
      const functionPermissions = parameters['Function_permissions'] || [];
      console.log('🔍 Function permissions raw:', functionPermissions);
      
      // Find the function_permissions parameter
      const permissionParam = functionPermissions.find(p => p.value && typeof p.value === 'object');
      let parameterConfig = permissionParam?.value || {};
      
      // BACKWARD COMPATIBILITY: Ensure existing parameter-based permissions are preserved
      // If no parameter config exists, initialize with legacy default structure
      if (Object.keys(parameterConfig).length === 0) {
        console.log('🔄 No parameter config found, initializing with legacy defaults');
        parameterConfig = {
          members: { read: [], write: [] },
          events: { read: [], write: [] },
          products: { read: [], write: [] },
          orders: { read: [], write: [] },
          webshop: { read: [], write: [] },
          parameters: { read: [], write: [] },
          memberships: { read: [], write: [] }
        };
      }
      
      // BACKWARD COMPATIBILITY: Preserve existing legacy group patterns
      // Ensure legacy groups like hdcnRegio_* patterns are maintained
      const preservedLegacyConfig = JSON.parse(JSON.stringify(parameterConfig));
      
      // Calculate role-based permissions from user's assigned roles
      const roleBasedPermissions = calculatePermissions(userGroups);
      console.log('🔍 Role-based permissions calculated:', roleBasedPermissions);
      
      // BACKWARD COMPATIBILITY: Merge parameter-based permissions with role-based permissions
      // Parameter-based permissions take precedence to maintain existing behavior
      let mergedConfig = { ...preservedLegacyConfig };
      
      Object.keys(roleBasedPermissions).forEach(functionName => {
        if (!mergedConfig[functionName]) {
          mergedConfig[functionName] = { read: [], write: [] };
        }
        
        const rolePerms = roleBasedPermissions[functionName];
        const existingPerms = mergedConfig[functionName];
        
        // BACKWARD COMPATIBILITY: Add role permissions to existing parameter permissions
        // This ensures existing permissions continue to work while adding new role-based ones
        if (rolePerms.read) {
          const existingRead = existingPerms.read || [];
          mergedConfig[functionName].read = [...new Set([...existingRead, ...rolePerms.read])];
        }
        
        if (rolePerms.write) {
          const existingWrite = existingPerms.write || [];
          mergedConfig[functionName].write = [...new Set([...existingWrite, ...rolePerms.write])];
        }
      });
      
      // BACKWARD COMPATIBILITY: Ensure legacy admin permissions are preserved
      if (isAdmin) {
        console.log('🔄 Ensuring admin permissions are preserved');
        const adminFunctions = ['members', 'events', 'products', 'orders', 'webshop', 'parameters', 'memberships'];
        adminFunctions.forEach(functionName => {
          if (!mergedConfig[functionName]) {
            mergedConfig[functionName] = { read: [], write: [] };
          }
          
          // Ensure hdcnAdmins group is always included for admin users
          if (!mergedConfig[functionName].read.includes('hdcnAdmins')) {
            mergedConfig[functionName].read.push('hdcnAdmins');
          }
          if (!mergedConfig[functionName].write.includes('hdcnAdmins')) {
            mergedConfig[functionName].write.push('hdcnAdmins');
          }
        });
      }
      
      // BACKWARD COMPATIBILITY: Ensure basic member permissions are preserved
      const hasBasicMemberRole = userGroups.includes('hdcnLeden');
      if (hasBasicMemberRole) {
        console.log('🔄 Ensuring basic member permissions are preserved');
        if (!mergedConfig.webshop) {
          mergedConfig.webshop = { read: [], write: [] };
        }
        if (!mergedConfig.webshop.read.includes('hdcnLeden')) {
          mergedConfig.webshop.read.push('hdcnLeden');
        }
        if (!mergedConfig.webshop.write.includes('hdcnLeden')) {
          mergedConfig.webshop.write.push('hdcnLeden');
        }
      }
      
      // ENHANCED: Preserve parameter-based module visibility
      // Ensure that parameter-based module access rules are maintained
      console.log('🔄 Preserving parameter-based module visibility');
      
      // Check if there are any parameter-based module visibility rules
      const moduleVisibilityParams = parameters['Module_visibility'] || [];
      if (moduleVisibilityParams.length > 0) {
        console.log('🔍 Found module visibility parameters:', moduleVisibilityParams);
        
        // Apply module visibility rules to merged config
        moduleVisibilityParams.forEach(visibilityRule => {
          if (visibilityRule.value && typeof visibilityRule.value === 'object') {
            const { module, conditions } = visibilityRule.value;
            
            if (module && conditions) {
              // Ensure module exists in config
              if (!mergedConfig[module]) {
                mergedConfig[module] = { read: [], write: [] };
              }
              
              // Apply parameter-based visibility conditions
              if (conditions.membershipTypes) {
                // Add membership type-based access
                conditions.membershipTypes.forEach(membershipType => {
                  const membershipAccessKey = `membership_${membershipType.replace(/\s+/g, '_').toLowerCase()}`;
                  if (!mergedConfig[module].read.includes(membershipAccessKey)) {
                    mergedConfig[module].read.push(membershipAccessKey);
                  }
                });
              }
              
              if (conditions.regions) {
                // Add region-based access
                conditions.regions.forEach(region => {
                  const regionAccessKey = `region_${region}`;
                  if (!mergedConfig[module].read.includes(regionAccessKey)) {
                    mergedConfig[module].read.push(regionAccessKey);
                  }
                });
              }
            }
          }
        });
      }
      
      // BACKWARD COMPATIBILITY: If merged config is still empty, use comprehensive fallback
      if (Object.keys(mergedConfig).length === 0) {
        console.log('🔄 Using comprehensive fallback config');
        mergedConfig = isAdmin ? {
          members: { read: ['hdcnAdmins'], write: ['hdcnAdmins'] },
          events: { read: ['hdcnAdmins'], write: ['hdcnAdmins'] },
          products: { read: ['hdcnAdmins'], write: ['hdcnAdmins'] },
          orders: { read: ['hdcnAdmins'], write: ['hdcnAdmins'] },
          webshop: { read: ['hdcnLeden', 'hdcnAdmins'], write: ['hdcnLeden', 'hdcnAdmins'] },
          parameters: { read: ['hdcnAdmins'], write: ['hdcnAdmins'] },
          memberships: { read: ['hdcnAdmins'], write: ['hdcnAdmins'] }
        } : {
          webshop: { read: ['hdcnLeden'], write: ['hdcnLeden'] }
        };
      }
      
      console.log('🔍 Final merged permission config with parameter-based visibility preserved:', mergedConfig);
      
      return new FunctionPermissionManager(user, mergedConfig);
    } catch (error) {
      console.error('❌ Failed to load function permissions:', error);
      
      // BACKWARD COMPATIBILITY: Enhanced fallback handling
      console.log('🔄 Applying enhanced backward compatibility fallback');
      
      // First try: Calculate role-based permissions even if parameter loading fails
      const roleBasedPermissions = calculatePermissions(userGroups);
      
      // If we have role-based permissions, use them with legacy compatibility
      if (Object.keys(roleBasedPermissions).length > 0) {
        console.log('🔄 Using role-based permissions as fallback with legacy support');
        
        // Ensure legacy admin and member permissions are included
        const enhancedRolePermissions = { ...roleBasedPermissions };
        
        if (isAdmin) {
          const adminFunctions = ['members', 'events', 'products', 'orders', 'webshop', 'parameters', 'memberships'];
          adminFunctions.forEach(functionName => {
            if (!enhancedRolePermissions[functionName]) {
              enhancedRolePermissions[functionName] = { read: [], write: [] };
            }
            if (!enhancedRolePermissions[functionName].read.includes('hdcnAdmins')) {
              enhancedRolePermissions[functionName].read.push('hdcnAdmins');
            }
            if (!enhancedRolePermissions[functionName].write.includes('hdcnAdmins')) {
              enhancedRolePermissions[functionName].write.push('hdcnAdmins');
            }
          });
        }
        
        const hasBasicMemberRole = userGroups.includes('hdcnLeden');
        if (hasBasicMemberRole) {
          if (!enhancedRolePermissions.webshop) {
            enhancedRolePermissions.webshop = { read: [], write: [] };
          }
          if (!enhancedRolePermissions.webshop.read.includes('hdcnLeden')) {
            enhancedRolePermissions.webshop.read.push('hdcnLeden');
          }
          if (!enhancedRolePermissions.webshop.write.includes('hdcnLeden')) {
            enhancedRolePermissions.webshop.write.push('hdcnLeden');
          }
        }
        
        return new FunctionPermissionManager(user, enhancedRolePermissions);
      }
      
      // Final fallback: Comprehensive legacy-compatible permissions
      const fallbackConfig = isAdmin ? {
        members: { read: ['hdcnAdmins'], write: ['hdcnAdmins'] },
        events: { read: ['hdcnAdmins'], write: ['hdcnAdmins'] },
        products: { read: ['hdcnAdmins'], write: ['hdcnAdmins'] },
        orders: { read: ['hdcnAdmins'], write: ['hdcnAdmins'] },
        webshop: { read: ['hdcnLeden', 'hdcnAdmins'], write: ['hdcnLeden', 'hdcnAdmins'] },
        parameters: { read: ['hdcnAdmins'], write: ['hdcnAdmins'] },
        memberships: { read: ['hdcnAdmins'], write: ['hdcnAdmins'] }
      } : {
        webshop: { read: ['hdcnLeden'], write: ['hdcnLeden'] }
      };
      
      console.log('🔄 Using final backward-compatible fallback config');
      return new FunctionPermissionManager(user, fallbackConfig);
    }
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

// Default function permissions template for parameter table
export const DEFAULT_FUNCTION_PERMISSIONS = {
  id: 'default',
  value: {
    members: {
      read: ['hdcnAdmins', 'hdcnRegio_*'],
      write: ['hdcnAdmins']
    },
    events: {
      read: ['hdcnAdmins', 'hdcnEvents_Read'],
      write: ['hdcnAdmins', 'hdcnEvents_Write']
    },
    products: {
      read: ['hdcnAdmins', 'hdcnProducts_Read'],
      write: ['hdcnAdmins', 'hdcnProducts_Write']
    },
    orders: {
      read: ['hdcnAdmins', 'hdcnOrders_Read'],
      write: ['hdcnAdmins', 'hdcnOrders_Write']
    },
    webshop: {
      read: ['hdcnLeden', 'hdcnAdmins'],
      write: ['hdcnLeden', 'hdcnAdmins']
    },
    parameters: {
      read: ['hdcnAdmins'],
      write: ['hdcnAdmins']
    },
    memberships: {
      read: ['hdcnAdmins'],
      write: ['hdcnAdmins']
    }
  }
};