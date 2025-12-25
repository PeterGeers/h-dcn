import { fetchAuthSession } from 'aws-amplify/auth';

export const getAuthHeaders = async (): Promise<Record<string, string>> => {
  try {
    const session = await fetchAuthSession();
    const token = session.tokens?.idToken?.toString();
    if (!token) {
      throw new Error('No authentication token available');
    }
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      'X-Requested-With': 'XMLHttpRequest'
    };
  } catch (error) {
    throw new Error('Authentication required');
  }
};

export const getAuthHeadersForGet = async (): Promise<Record<string, string>> => {
  try {
    const session = await fetchAuthSession();
    const token = session.tokens?.idToken?.toString();
    if (!token) {
      throw new Error('No authentication token available');
    }
    return {
      'Authorization': `Bearer ${token}`
    };
  } catch (error) {
    throw new Error('Authentication required');
  }
};