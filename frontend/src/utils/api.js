import { Auth } from 'aws-amplify';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod';

const getAuthHeaders = async () => {
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

export const membershipAPI = {
  async createMember(memberData) {
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/members`, {
        method: 'POST',
        headers,
        credentials: 'omit',
        body: JSON.stringify(memberData)
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }
      
      return await response.json();
    } catch (error) {
      if (error.name === 'TypeError') {
        throw new Error('Network error: Unable to connect to server');
      }
      throw error;
    }
  }
};