import { fetchAuthSession } from 'aws-amplify/auth';

export const getAuthHeaders = async (): Promise<Record<string, string>> => {
  try {
    // First try Amplify session (for backward compatibility)
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
    
    // Try custom authentication tokens from localStorage
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
    // First try Amplify session (for backward compatibility)
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
    
    // Try custom authentication tokens from localStorage
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