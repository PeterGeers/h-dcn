import { ApiService, ApiResponse } from '../services/apiService';

import { API_CONFIG } from '../config/api';

const API_BASE_URL = API_CONFIG.BASE_URL;

interface MemberData {
  [key: string]: any;
}

/**
 * @deprecated Use main ApiService directly instead
 */
const getAuthHeaders = async (): Promise<Record<string, string>> => {
  if (!ApiService.isAuthenticated()) {
    throw new Error('Authentication required');
  }
  
  // Return empty object as main ApiService handles auth headers internally
  return {
    'Content-Type': 'application/json',
    'X-Requested-With': 'XMLHttpRequest'
  };
};

export const membershipAPI = {
  async createMember(memberData: MemberData): Promise<ApiResponse<any>> {
    try {
      const response = await ApiService.post('/members', memberData);
      
      if (!response.success) {
        throw new Error(response.error || 'Failed to create member');
      }
      
      return response;
    } catch (error) {
      if (error.name === 'TypeError') {
        throw new Error('Network error: Unable to connect to server');
      }
      throw error;
    }
  }
};