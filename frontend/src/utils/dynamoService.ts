import { Auth } from 'aws-amplify';

interface ParameterData {
  [key: string]: any;
}

// DynamoDB service for parameter management
export class DynamoService {
  static API_BASE = process.env.REACT_APP_API_BASE_URL;
  static _authCache: Record<string, string> | null = null;
  static _authExpiry = 0;

  
  static async getAuthHeaders(): Promise<Record<string, string>> {
    const now = Date.now();
    if (this._authCache && now < this._authExpiry) {
      return this._authCache;
    }
    
    try {
      const session = await Auth.currentSession();
      const token = session.getIdToken().getJwtToken();
      this._authCache = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        'X-Requested-With': 'XMLHttpRequest'
      };
      this._authExpiry = now + 300000; // 5 minutes
      return this._authCache;
    } catch (error) {
      this._authCache = null;
      throw new Error('Authentication required');
    }
  }
  
  // Get all parameters
  static async getParameters(): Promise<ParameterData> {
    try {
      const headers = await this.getAuthHeaders();
      const response = await fetch(`${this.API_BASE}/parameters`, {
        headers,
        credentials: 'omit'
      });
      if (response.ok) {
        const data = await response.json();
        this._setCachedData(data);
        return data;
      }
      throw new Error('API not available');
    } catch (error) {
      console.log('Using cached parameters:', error.message);
      return this._getCachedData() || {};
    }
  }
  
  // Save parameters
  static async saveParameters(data: ParameterData): Promise<boolean> {
    try {
      const headers = await this.getAuthHeaders();
      const response = await fetch(`${this.API_BASE}/parameters`, {
        method: 'PUT',
        headers,
        credentials: 'omit',
        body: JSON.stringify(data)
      });
      if (response.ok) {
        this._setCachedData(data);
        return true;
      }
      throw new Error('API save failed');
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