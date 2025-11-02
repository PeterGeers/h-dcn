import { Auth } from 'aws-amplify';

export const getAuthHeaders = async (): Promise<Record<string, string>> => {
  try {
    const session = await Auth.currentSession();
    const token = session.getIdToken().getJwtToken();
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
    const session = await Auth.currentSession();
    const token = session.getIdToken().getJwtToken();
    return {
      'Authorization': `Bearer ${token}`
    };
  } catch (error) {
    throw new Error('Authentication required');
  }
};