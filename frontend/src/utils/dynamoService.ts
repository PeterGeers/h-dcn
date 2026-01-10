import { ApiService } from '../services/apiService';

interface ParameterData {
  [key: string]: any;
}

// DynamoDB service for parameter management - now uses main ApiService for authentication
export class DynamoService {
  static API_BASE = process.env.REACT_APP_API_BASE_URL;
  static _authCache: Record<string, string> | null = null;
  static _authExpiry = 0;

  /**
   * Get authentication headers - now uses main ApiService
   * @deprecated Use main ApiService directly instead
   */
  static async getAuthHeaders(): Promise<Record<string, string>> {
    if (!ApiService.isAuthenticated()) {
      throw new Error('Authentication required');
    }
    
    // Return empty object as main ApiService handles auth headers internally
    return {
      'Content-Type': 'application/json',
      'X-Requested-With': 'XMLHttpRequest'
    };
  }
  
  // Get all parameters - now uses main ApiService
  static async getParameters(): Promise<ParameterData> {
    try {
      const response = await ApiService.get('/parameters');
      if (response.success && response.data) {
        this._setCachedData(response.data);
        return response.data;
      }
      throw new Error(response.error || 'API not available');
    } catch (error) {
      console.log('Using cached parameters:', error.message);
      return this._getCachedData() || {};
    }
  }
  
  // Save parameters - now uses main ApiService
  static async saveParameters(data: ParameterData): Promise<boolean> {
    try {
      const response = await ApiService.put('/parameters', data);
      if (response.success) {
        this._setCachedData(data);
        return true;
      }
      throw new Error(response.error || 'API save failed');
    } catch (error) {
      console.log('Saving to cache only:', error.message);
      this._setCachedData(data);
      return true;
    }
  }
  
  // Cache helpers
  static _getCachedData(): ParameterData | null {
    try {
      const cached = localStorage.getItem('dynamo-parameters');
      return cached ? JSON.parse(cached) : null;
    } catch {
      return null;
    }
  }
  
  static _setCachedData(data: ParameterData): void {
    try {
      localStorage.setItem('dynamo-parameters', JSON.stringify(data));
    } catch (error) {
      console.warn('Cache write failed:', error.message);
    }
  }
  
  // Clear cache
  static clearCache(): void {
    localStorage.removeItem('dynamo-parameters');
  }
}