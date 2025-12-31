import { fetchAuthSession } from 'aws-amplify/auth';

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
        
        // Add enhanced groups as custom header if available
        if (enhancedGroups && Array.isArray(enhancedGroups)) {
          headers['X-Enhanced-Groups'] = JSON.stringify(enhancedGroups);
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
        
        // Add enhanced groups as custom header if available
        if (enhancedGroups && Array.isArray(enhancedGroups)) {
          headers['X-Enhanced-Groups'] = JSON.stringify(enhancedGroups);
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