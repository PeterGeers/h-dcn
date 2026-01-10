import { fetchAuthSession } from 'aws-amplify/auth';

/**
 * Filters cognito groups to only include valid new role structure roles
 * Removes any legacy roles that might still exist in JWT tokens
 */
const filterValidRoles = (groups: string[]): string[] => {
  return groups.filter((role: string) => {
    // Allow new permission-based roles (but NOT old _All versions)
    if (role.includes('_CRUD') || role.includes('_Read') || role.includes('_Export') || role.includes('_Status_Approve')) {
      // Reject old _All roles (except Regio_All which is valid)
      if (role.endsWith('_All') && role !== 'Regio_All') {
        console.warn(`AuthHeaders: Filtering out legacy role: ${role}`);
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
    console.warn(`AuthHeaders: Filtering out legacy role: ${role}`);
    return false;
  });
};

export const getAuthHeaders = async (): Promise<Record<string, string>> => {
  try {
    // First try to get enhanced user object with combined credentials
    const storedUser = localStorage.getItem('hdcn_auth_user');
    if (storedUser) {
      const user = JSON.parse(storedUser);
      const token = user.signInUserSession?.accessToken?.jwtToken || user.signInUserSession?.idToken?.jwtToken;
      const enhancedGroups = user.signInUserSession?.accessToken?.payload?.['cognito:groups'];
      
      if (token) {
        const headers: Record<string, string> = {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
          'X-Requested-With': 'XMLHttpRequest'
        };
        
        // Add enhanced groups as custom header if available (filtered for new role structure only)
        if (enhancedGroups && Array.isArray(enhancedGroups)) {
          const validGroups = filterValidRoles(enhancedGroups);
          headers['X-Enhanced-Groups'] = JSON.stringify(validGroups);
        }
        
        return headers;
      }
    }
    
    // Fallback: try Amplify session (for backward compatibility)
    try {
      const session = await fetchAuthSession();
      const token = session.tokens?.idToken?.toString();
      if (token) {
        return {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
          'X-Requested-With': 'XMLHttpRequest'
        };
      }
    } catch (amplifyError) {
      // Amplify session not available, try custom auth
    }
    
    // Last resort: try custom authentication tokens from localStorage
    const storedTokens = localStorage.getItem('hdcn_auth_tokens');
    if (storedTokens) {
      const tokens = JSON.parse(storedTokens);
      const token = tokens.IdToken || tokens.AccessToken;
      if (token) {
        return {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
          'X-Requested-With': 'XMLHttpRequest'
        };
      }
    }
    
    throw new Error('No authentication token available');
  } catch (error) {
    throw new Error('Authentication required');
  }
};

export const getAuthHeadersForGet = async (): Promise<Record<string, string>> => {
  try {
    // First try to get enhanced user object with combined credentials
    const storedUser = localStorage.getItem('hdcn_auth_user');
    if (storedUser) {
      const user = JSON.parse(storedUser);
      const token = user.signInUserSession?.accessToken?.jwtToken || user.signInUserSession?.idToken?.jwtToken;
      const enhancedGroups = user.signInUserSession?.accessToken?.payload?.['cognito:groups'];
      
      if (token) {
        const headers: Record<string, string> = {
          'Authorization': `Bearer ${token}`
        };
        
        // Add enhanced groups as custom header if available (filtered for new role structure only)
        if (enhancedGroups && Array.isArray(enhancedGroups)) {
          const validGroups = filterValidRoles(enhancedGroups);
          headers['X-Enhanced-Groups'] = JSON.stringify(validGroups);
        }
        
        return headers;
      }
    }
    
    // Fallback: try Amplify session (for backward compatibility)
    try {
      const session = await fetchAuthSession();
      const token = session.tokens?.idToken?.toString();
      if (token) {
        return {
          'Authorization': `Bearer ${token}`
        };
      }
    } catch (amplifyError) {
      // Amplify session not available, try custom auth
    }
    
    // Last resort: try custom authentication tokens from localStorage
    const storedTokens = localStorage.getItem('hdcn_auth_tokens');
    if (storedTokens) {
      const tokens = JSON.parse(storedTokens);
      const token = tokens.IdToken || tokens.AccessToken;
      if (token) {
        return {
          'Authorization': `Bearer ${token}`
        };
      }
    }
    
    throw new Error('No authentication token available');
  } catch (error) {
    throw new Error('Authentication required');
  }
};