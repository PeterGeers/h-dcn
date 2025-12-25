import { fetchAuthSession } from 'aws-amplify/auth';
import { ApiResponse } from '../types';

import { API_CONFIG } from '../config/api';

const API_BASE_URL = API_CONFIG.BASE_URL;

interface MemberData {
  [key: string]: any;
}

const getAuthHeaders = async (): Promise<Record<string, string>> => {
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

export const membershipAPI = {
  async createMember(memberData: MemberData): Promise<ApiResponse<any>> {
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