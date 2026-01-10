import { fetchAuthSession } from 'aws-amplify/auth';
import { HDCNGroup } from '../types/user';

/**
 * JWT Token utilities for Cognito authentication
 */

export interface JWTPayload {
  'cognito:groups'?: HDCNGroup[];
  username?: string;
  email?: string;
  sub?: string;
  aud?: string;
  iss?: string;
  exp?: number;
  iat?: number;
}

export interface AuthTokens {
  idToken?: string;
  accessToken?: string;
  refreshToken?: string;
}

/**
 * Extracts JWT payload from a token string
 * @param token - JWT token string
 * @returns Decoded JWT payload or null if invalid
 */
export function decodeJWTPayload(token: string): JWTPayload | null {
  try {
    // JWT tokens have 3 parts separated by dots: header.payload.signature
    const parts = token.split('.');
    if (parts.length !== 3) {
      console.error('Invalid JWT token format');
      return null;
    }

    // Decode the payload (second part)
    const payload = parts[1];
    
    // Add padding if needed for base64 decoding
    const paddedPayload = payload + '='.repeat((4 - payload.length % 4) % 4);
    
    // Decode base64 and parse JSON
    const decodedPayload = JSON.parse(atob(paddedPayload));
    
    return decodedPayload as JWTPayload;
  } catch (error) {
    console.error('Failed to decode JWT payload:', error);
    return null;
  }
}

/**
 * Gets current authentication tokens from Amplify session
 * @returns Promise with current auth tokens or null if not authenticated
 */
export async function getCurrentAuthTokens(): Promise<AuthTokens | null> {
  try {
    const session = await fetchAuthSession();
    
    if (!session.tokens) {
      console.log('No tokens available in session');
      return null;
    }

    return {
      idToken: session.tokens.idToken?.toString(),
      accessToken: session.tokens.accessToken?.toString(),
      // Note: refreshToken may not be available in all Amplify v6 configurations
      refreshToken: (session.tokens as any).refreshToken?.toString()
    };
  } catch (error) {
    console.error('Failed to get auth tokens:', error);
    return null;
  }
}

/**
 * Extracts cognito:groups from current user's JWT tokens
 * Only returns roles that are part of the new role structure (no legacy roles)
 * @returns Promise with array of user roles/groups or empty array if none found
 */
export async function getCurrentUserRoles(): Promise<HDCNGroup[]> {
  try {
    const tokens = await getCurrentAuthTokens();
    
    if (!tokens?.accessToken) {
      console.log('No access token available');
      return [];
    }

    const payload = decodeJWTPayload(tokens.accessToken);
    
    if (!payload) {
      console.error('Failed to decode access token payload');
      return [];
    }

    const cognitoGroups = payload['cognito:groups'] || [];
    
    // Filter out any legacy roles that might still exist in JWT tokens
    // Only allow roles that are part of the new permission + region structure
    const validRoles = cognitoGroups.filter((role: string) => {
      // Allow new permission-based roles (but NOT old _All versions)
      if (role.includes('_CRUD') || role.includes('_Read') || role.includes('_Export') || role.includes('_Status_Approve')) {
        // Reject old _All roles (except Regio_All which is valid)
        if (role.endsWith('_All') && role !== 'Regio_All') {
          console.warn(`Filtering out legacy role: ${role}`);
          return false;
        }
        return true;
      }
      
      // Allow regional roles
      if (role.startsWith('Regio_')) {
        return true;
      }
      
      // Allow system roles
      if (role.startsWith('System_')) {
        return true;
      }
      
      // Allow specific valid roles
      if (['hdcnLeden', 'Webshop_Management', 'verzoek_lid'].includes(role)) {
        return true;
      }
      
      // Reject any other legacy roles (deprecated roles no longer supported)
      console.warn(`Filtering out legacy role: ${role}`);
      return false;
    }) as HDCNGroup[];
    
    console.log('Extracted and filtered cognito:groups from JWT:', validRoles);
    
    return validRoles;
  } catch (error) {
    console.error('Failed to extract user roles from JWT:', error);
    return [];
  }
}

/**
 * Validates that JWT token contains expected cognito:groups claim
 * @param token - JWT token string to validate
 * @returns boolean indicating if token contains valid cognito:groups claim
 */
export function validateCognitoGroupsClaim(token: string): boolean {
  const payload = decodeJWTPayload(token);
  
  if (!payload) {
    console.error('Invalid JWT token - cannot decode payload');
    return false;
  }

  // Check if cognito:groups claim exists (can be empty array)
  if (!payload.hasOwnProperty('cognito:groups')) {
    console.error('JWT token missing cognito:groups claim');
    return false;
  }

  // Validate that cognito:groups is an array
  if (!Array.isArray(payload['cognito:groups'])) {
    console.error('cognito:groups claim is not an array');
    return false;
  }

  console.log('JWT token contains valid cognito:groups claim:', payload['cognito:groups']);
  return true;
}

/**
 * Gets user information from JWT tokens including roles
 * @returns Promise with user info extracted from JWT tokens
 */
export async function getCurrentUserInfo(): Promise<{
  username?: string;
  email?: string;
  roles: HDCNGroup[];
  sub?: string;
} | null> {
  try {
    const tokens = await getCurrentAuthTokens();
    
    if (!tokens?.accessToken) {
      return null;
    }

    const payload = decodeJWTPayload(tokens.accessToken);
    
    if (!payload) {
      return null;
    }

    // Get filtered roles using the same logic as getCurrentUserRoles
    const roles = await getCurrentUserRoles();

    return {
      username: payload.username,
      email: payload.email,
      roles,
      sub: payload.sub
    };
  } catch (error) {
    console.error('Failed to get current user info:', error);
    return null;
  }
}

/**
 * Validates that user has valid role combinations according to new role structure
 * Users must have both permission roles AND regional roles (except for system roles)
 * @param roles - Array of user roles to validate
 * @returns Object with validation result and details
 */
export function validateRoleCombinations(roles: HDCNGroup[]): {
  isValid: boolean;
  hasPermissions: boolean;
  hasRegions: boolean;
  missingRoles: string[];
  warnings: string[];
} {
  const permissionRoles = roles.filter(role => 
    role.includes('_CRUD') || 
    role.includes('_Read') || 
    role.includes('_Export') || 
    role.includes('_Status_Approve')
  );
  
  const regionalRoles = roles.filter(role => role.startsWith('Regio_'));
  
  const systemRoles = roles.filter(role => 
    role.startsWith('System_') || 
    role === 'Webshop_Management'
  );
  
  const basicRoles = roles.filter(role => 
    ['hdcnLeden', 'verzoek_lid'].includes(role)
  );

  const hasPermissions = permissionRoles.length > 0;
  const hasRegions = regionalRoles.length > 0;
  const hasSystemAccess = systemRoles.length > 0;
  const hasBasicAccess = basicRoles.length > 0;

  const missingRoles: string[] = [];
  const warnings: string[] = [];

  // System roles don't need regional roles
  if (hasSystemAccess) {
    return {
      isValid: true,
      hasPermissions: true,
      hasRegions: true, // System roles bypass regional requirements
      missingRoles: [],
      warnings: []
    };
  }

  // Basic member roles (hdcnLeden, verzoek_lid) don't need additional permissions
  if (hasBasicAccess && !hasPermissions) {
    return {
      isValid: true,
      hasPermissions: false, // Basic roles don't have admin permissions
      hasRegions: true, // Basic roles bypass regional requirements
      missingRoles: [],
      warnings: []
    };
  }

  // For permission-based roles, both permission and region are required
  if (hasPermissions && !hasRegions) {
    missingRoles.push('Regional role (Regio_*)');
  }

  if (!hasPermissions && hasRegions) {
    missingRoles.push('Permission role (*_CRUD, *_Read, *_Export)');
  }

  // Check for potentially problematic combinations
  if (regionalRoles.length > 1 && !regionalRoles.includes('Regio_All')) {
    warnings.push('User has multiple regional roles - this may cause unexpected behavior');
  }

  const isValid = missingRoles.length === 0;

  return {
    isValid,
    hasPermissions,
    hasRegions,
    missingRoles,
    warnings
  };
}

/**
 * Gets current user roles and validates they form valid combinations
 * @returns Promise with validated user roles and validation details
 */
export async function getCurrentUserRolesValidated(): Promise<{
  roles: HDCNGroup[];
  validation: ReturnType<typeof validateRoleCombinations>;
}> {
  const roles = await getCurrentUserRoles();
  const validation = validateRoleCombinations(roles);
  
  if (!validation.isValid) {
    console.warn('User has invalid role combination:', {
      roles,
      missingRoles: validation.missingRoles,
      warnings: validation.warnings
    });
  }
  
  return { roles, validation };
}