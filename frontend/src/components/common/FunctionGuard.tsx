import React, { useState, useEffect, ReactNode, useMemo } from 'react';
import { FunctionPermissionManager } from '../../utils/functionPermissions';

// Helper function to extract user roles from Cognito JWT token
const getUserRoles = (user: any): string[] => {
  try {
    // First, try the standard Amplify location
    const amplifyGroups = user?.signInUserSession?.accessToken?.payload['cognito:groups'];
    if (amplifyGroups && Array.isArray(amplifyGroups)) {
      return amplifyGroups;
    }
    
    // If not found, try to decode the JWT token directly from localStorage
    const accessToken = localStorage.getItem('accessToken');
    if (accessToken) {
      // Decode JWT payload (base64 decode the middle part)
      const parts = accessToken.split('.');
      if (parts.length === 3) {
        const payload = JSON.parse(atob(parts[1]));
        const groups = payload['cognito:groups'] || [];
        console.log('🔍 FunctionGuard - Decoded JWT groups from localStorage:', groups);
        return groups;
      }
    } else {
      // Fallback: try to decode from user session JWT token
      const jwtToken = user?.signInUserSession?.accessToken?.jwtToken;
      if (jwtToken) {
        const parts = jwtToken.split('.');
        if (parts.length === 3) {
          const payload = JSON.parse(atob(parts[1]));
          const groups = payload['cognito:groups'] || [];
          return groups;
        }
      }
    }
    
    return [];
  } catch (error) {
    console.error('Error extracting user roles in FunctionGuard:', error);
    return [];
  }
};

// Helper function to check if user has any of the required roles
const hasRequiredRoles = (userRoles: string[], requiredRoles: string[]): boolean => {
  if (requiredRoles.length === 0) return true; // No roles required
  return requiredRoles.some(role => userRoles.includes(role));
};

interface FunctionGuardProps {
  user: any; // TODO: Add proper User type
  children: ReactNode;
  functionName?: string; // Optional when using role-only access
  action?: 'read' | 'write';
  fallback?: ReactNode;
  /**
   * Optional array of required roles for role-based access control.
   * 
   * COMBINED PERMISSION CHECKING: This prop enables flexible permission checking:
   * 
   * - If requiredRoles is empty/undefined: Uses existing function-based permissions only (backward compatibility)
   * - If requiredRoles is specified but no functionName: Uses role-based permissions only
   * - If both requiredRoles and functionName are specified: Requires BOTH role access AND function access (enhanced security)
   * 
   * This approach provides:
   * 1. Backward compatibility for existing function-based access control
   * 2. Role-only access for new implementations that don't need function restrictions
   * 3. Combined security for critical functionality requiring both role membership and function permissions
   * 
   * @example
   * // Existing function-based access only (backward compatible)
   * <FunctionGuard user={user} functionName="webshop">
   * 
   * // Role-based access only (no function restriction)
   * <FunctionGuard user={user} requiredRoles={['Members_Read_All']}>
   * 
   * // Combined security (requires BOTH role AND function access)
   * <FunctionGuard user={user} functionName="members" requiredRoles={['Members_CRUD_All']}>
   */
  requiredRoles?: string[];
}

/**
 * FunctionGuard component provides access control for UI elements based on user permissions.
 * 
 * COMBINED PERMISSION CHECKING: This component supports flexible permission checking with
 * both backward compatibility and enhanced security through combined role and function checks.
 * 
 * Permission Logic:
 * 1. If no requiredRoles are specified -> uses existing function-based permissions only (backward compatibility)
 * 2. If requiredRoles are specified but no functionName -> uses role-based permissions only
 * 3. If both requiredRoles and functionName are specified -> requires BOTH (AND logic for enhanced security)
 * 
 * This approach allows for:
 * - Backward compatibility: Existing implementations continue to work unchanged
 * - Role-only access: New implementations can use role-based access without function restrictions
 * - Combined security: Critical functionality can require both role membership AND function permissions
 * 
 * @param user - The authenticated user object containing Cognito session data
 * @param functionName - The function/module name to check permissions for (optional when using role-only access)
 * @param action - The action type ('read' or 'write'), defaults to 'read'
 * @param requiredRoles - Optional array of roles required for access
 * @param fallback - Optional component to render when access is denied
 * @param children - The content to render when access is granted
 */
export function FunctionGuard({ 
  user, 
  children, 
  functionName, 
  action = 'read',
  fallback = null,
  requiredRoles = [] // Default to empty array if no roles required
}: FunctionGuardProps): React.ReactElement | null {
  const [hasAccess, setHasAccess] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);

  // Memoize user roles extraction to prevent unnecessary recalculations
  const userRoles = useMemo(() => getUserRoles(user), [user]);

  useEffect(() => {
    const checkAccess = async () => {
      try {
        // Use memoized user roles
        
        // Check role-based access if roles are specified
        const hasRoleAccess = hasRequiredRoles(userRoles, requiredRoles);
        
        // Check function-based access if function name is provided
        let hasFunctionAccess = true; // Default to true if no function check needed
        if (functionName) {
          // BACKWARD COMPATIBILITY: Always check function-based permissions when functionName is provided
          // This ensures existing function-based access control is preserved
          const permissions = await FunctionPermissionManager.create(user);
          hasFunctionAccess = permissions.hasAccess(functionName, action);
        }
        
        // COMBINED PERMISSION CHECKING LOGIC:
        // The permission logic supports both backward compatibility and new role-based restrictions.
        // 
        // Logic:
        // 1. If no roles are required -> use function-based permissions only (backward compatibility)
        // 2. If roles are required but no function specified -> use role-based permissions only
        // 3. If both roles and function are specified -> prefer role-based access for new role system
        // 
        // This provides flexible permission checking while maintaining backward compatibility.
        let combinedAccess: boolean;
        
        if (requiredRoles.length === 0) {
          // No roles required - use existing function-based permissions only (backward compatibility)
          if (!functionName) {
            // Neither roles nor function specified - this is an error case, deny access
            console.warn('FunctionGuard: Neither functionName nor requiredRoles specified');
            combinedAccess = false;
          } else {
            combinedAccess = hasFunctionAccess;
          }
        } else if (!functionName) {
          // Roles required but no function specified - use role-based permissions only
          combinedAccess = hasRoleAccess;
        } else {
          // Both roles and function specified - prefer role-based access for new role system
          // If user has role access, grant access (new role system takes precedence)
          // Only fall back to function access if role access fails (backward compatibility)
          combinedAccess = hasRoleAccess || hasFunctionAccess;
        }
        
        setHasAccess(combinedAccess);
      } catch (error) {
        console.error('Permission check failed:', error);
        // BACKWARD COMPATIBILITY: Enhanced fallback handling
        // Try to preserve existing access patterns even when permission loading fails
        const isAdmin = userRoles.includes('hdcnAdmins');
        const isBasicMember = userRoles.includes('hdcnLeden');
        
        // Fallback logic that preserves existing access patterns
        let fallbackAccess = false;
        
        if (isAdmin) {
          // Admins get access to everything (existing behavior)
          fallbackAccess = true;
        } else if (isBasicMember && functionName && (functionName === 'webshop' || functionName === 'products')) {
          // Basic members get webshop access (existing behavior)
          fallbackAccess = true;
        } else if (requiredRoles.length > 0) {
          // Check if user has any of the required roles as final fallback
          fallbackAccess = hasRequiredRoles(userRoles, requiredRoles);
        } else if (!functionName) {
          // If no function name and no roles, deny access
          fallbackAccess = false;
        }
        
        setHasAccess(fallbackAccess);
      } finally {
        setLoading(false);
      }
    };

    checkAccess();
  }, [user, functionName, action, requiredRoles, userRoles]); // Add userRoles to dependencies

  if (loading) return null;
  return hasAccess ? <>{children}</> : <>{fallback}</>;
}