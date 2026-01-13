/**
 * Filters cognito groups to only include valid role structure roles
 * Ensures only current permission + region role combinations are used
 */
const filterValidRoles = (groups: string[]): string[] => {
  return groups.filter((role: string) => {
    // Allow permission-based roles (current system)
    if (role.includes('_CRUD') || role.includes('_Read') || role.includes('_Export') || role.includes('_Status_Approve')) {
      // Note: Regio_All is the only _All role that still exists
      if (role.endsWith('_All') && role !== 'Regio_All') {
        console.warn(`AuthHeaders: Filtering out invalid role: ${role}`);
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
    
    // Reject any other invalid roles
    console.warn(`AuthHeaders: Filtering out invalid role: ${role}`);
    return false;
  });
};

export const getAuthHeaders = async (): Promise<Record<string, string>> => {
  try {
    // Use the same method as GroupAccessGuard and other working components
    console.log('[getAuthHeaders] Using user object from localStorage (same as GroupAccessGuard)');
    
    // Get the user object that contains the authentication data
    const storedUser = localStorage.getItem('hdcn_auth_user');
    if (!storedUser) {
      throw new Error('No user data found in localStorage');
    }
    
    const user = JSON.parse(storedUser);
    console.log('[getAuthHeaders] User object keys:', Object.keys(user));
    
    // Get JWT token (same method as GroupAccessGuard)
    const jwtToken = user.signInUserSession?.accessToken?.jwtToken;
    if (!jwtToken) {
      throw new Error('No JWT token found in user session');
    }
    
    console.log('[getAuthHeaders] JWT token found');
    console.log('[getAuthHeaders] JWT token length:', jwtToken.length);
    console.log('[getAuthHeaders] JWT token preview:', jwtToken.substring(0, 50) + '...');
    
    // Get groups (same method as GroupAccessGuard)
    let userGroups: string[] = [];
    
    // First, try the standard Amplify location
    const amplifyGroups = user.signInUserSession?.accessToken?.payload?.['cognito:groups'];
    if (amplifyGroups && Array.isArray(amplifyGroups)) {
      userGroups = amplifyGroups;
    } else {
      // If not found, try to decode the JWT token directly (same as GroupAccessGuard)
      try {
        const parts = jwtToken.split('.');
        if (parts.length === 3) {
          const payload = JSON.parse(atob(parts[1]));
          userGroups = payload['cognito:groups'] || [];
        }
      } catch (error) {
        console.error('[getAuthHeaders] Error decoding JWT token:', error);
      }
    }
    
    console.log('[getAuthHeaders] User groups found:', userGroups);
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${jwtToken}`,
      'X-Requested-With': 'XMLHttpRequest'
    };
    
    // Add enhanced groups header
    if (userGroups && userGroups.length > 0) {
      const validGroups = filterValidRoles(userGroups);
      console.log('[getAuthHeaders] Valid groups to send:', validGroups);
      headers['X-Enhanced-Groups'] = JSON.stringify(validGroups);
    } else {
      console.warn('[getAuthHeaders] No user groups found');
    }
    
    return headers;
    
  } catch (error) {
    console.error('[getAuthHeaders] Error getting auth headers:', error);
    throw new Error('Authentication required');
  }
};

export const getAuthHeadersForGet = async (): Promise<Record<string, string>> => {
  try {
    // Use the same method as the main getAuthHeaders function
    const storedUser = localStorage.getItem('hdcn_auth_user');
    if (!storedUser) {
      throw new Error('No user data found in localStorage');
    }
    
    const user = JSON.parse(storedUser);
    const jwtToken = user.signInUserSession?.accessToken?.jwtToken;
    if (!jwtToken) {
      throw new Error('No JWT token found in user session');
    }
    
    // Get groups (same method as GroupAccessGuard)
    let userGroups: string[] = [];
    const amplifyGroups = user.signInUserSession?.accessToken?.payload?.['cognito:groups'];
    if (amplifyGroups && Array.isArray(amplifyGroups)) {
      userGroups = amplifyGroups;
    } else {
      try {
        const parts = jwtToken.split('.');
        if (parts.length === 3) {
          const payload = JSON.parse(atob(parts[1]));
          userGroups = payload['cognito:groups'] || [];
        }
      } catch (error) {
        console.error('[getAuthHeadersForGet] Error decoding JWT token:', error);
      }
    }
    
    const headers: Record<string, string> = {
      'Authorization': `Bearer ${jwtToken}`
    };
    
    // Add enhanced groups header
    if (userGroups && userGroups.length > 0) {
      const validGroups = filterValidRoles(userGroups);
      headers['X-Enhanced-Groups'] = JSON.stringify(validGroups);
    }
    
    return headers;
    
  } catch (error) {
    console.error('[getAuthHeadersForGet] Error getting auth headers:', error);
    throw new Error('Authentication required');
  }
};