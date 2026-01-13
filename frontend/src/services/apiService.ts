/**
 * API Service for H-DCN Application
 * 
 * This service handles authenticated API calls using stored JWT tokens
 * from the passwordless authentication system.
 */

import { getAuthHeaders } from '../utils/authHeaders';
import { parseApiError, showMaintenanceScreen, ApiError } from '../utils/errorHandler';

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export class ApiService {
  private static baseUrl = process.env.REACT_APP_API_BASE_URL || 'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod';

  /**
   * Get stored authentication tokens
   */
  private static getAuthTokens(): any {
    try {
      const storedTokens = localStorage.getItem('hdcn_auth_tokens');
      return storedTokens ? JSON.parse(storedTokens) : null;
    } catch (error) {
      console.error('Error parsing stored tokens:', error);
      return null;
    }
  }

  /**
   * Get stored user data
   */
  private static getAuthUser(): any {
    try {
      const storedUser = localStorage.getItem('hdcn_auth_user');
      return storedUser ? JSON.parse(storedUser) : null;
    } catch (error) {
      console.error('Error parsing stored user:', error);
      return null;
    }
  }

  /**
   * Check if user is authenticated
   */
  static isAuthenticated(): boolean {
    const tokens = this.getAuthTokens();
    if (!tokens || !tokens.AccessToken) {
      return false;
    }

    // Check token expiration
    if (tokens.AccessTokenPayload && tokens.AccessTokenPayload.exp) {
      const expirationTime = tokens.AccessTokenPayload.exp * 1000;
      const currentTime = Date.now();
      return currentTime < expirationTime;
    }

    return true;
  }

  /**
   * Get current user's email
   */
  static getCurrentUserEmail(): string | null {
    const user = this.getAuthUser();
    return user?.attributes?.email || null;
  }

  /**
   * Get current user's roles from JWT token
   * Only returns roles that are part of the new role structure (no legacy roles)
   */
  static getCurrentUserRoles(): string[] {
    const tokens = this.getAuthTokens();
    if (tokens && tokens.AccessTokenPayload && tokens.AccessTokenPayload['cognito:groups']) {
      const cognitoGroups = tokens.AccessTokenPayload['cognito:groups'];
      
      // Filter out any legacy roles that might still exist in JWT tokens
      // Only allow roles that are part of the new permission + region structure
      const validRoles = cognitoGroups.filter((role: string) => {
        // Allow new permission-based roles (but NOT old _All versions)
        if (role.includes('_CRUD') || role.includes('_Read') || role.includes('_Export') || role.includes('_Status_Approve')) {
          // Reject old _All roles (except Regio_All which is valid)
          if (role.endsWith('_All') && role !== 'Regio_All') {
            console.warn(`ApiService: Filtering out legacy role: ${role}`);
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
        
        // Reject any other legacy roles (deprecated roles no longer supported)
        console.warn(`ApiService: Filtering out legacy role: ${role}`);
        return false;
      });
      
      return validRoles;
    }
    return [];
  }

  /**
   * Make authenticated API request with global 503 error handling
   */
  static async request<T = any>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    try {
      const url = endpoint.startsWith('http') ? endpoint : `${this.baseUrl}${endpoint}`;
      
      // Get proper auth headers with X-Enhanced-Groups
      let authHeaders: Record<string, string>;
      try {
        authHeaders = await getAuthHeaders();
        console.log('[ApiService] Auth headers obtained:', Object.keys(authHeaders));
        console.log('[ApiService] Auth headers values:', authHeaders);
      } catch (authError) {
        console.error('[ApiService] Failed to get auth headers:', authError);
        // Fallback to old method if new one fails
        authHeaders = {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.getAuthTokens()?.AccessToken || ''}`,
        };
      }
      
      const response = await fetch(url, {
        ...options,
        headers: {
          ...authHeaders,
          ...options.headers,
        },
      });

      // Handle 503 maintenance mode globally
      if (response.status === 503) {
        const error = await parseApiError(response);
        showMaintenanceScreen(error);
        return {
          success: false,
          error: error.message,
          data: undefined,
        };
      }

      const data = await response.json();

      if (!response.ok) {
        return {
          success: false,
          error: data.message || data.error || `HTTP ${response.status}`,
          data: data,
        };
      }

      return {
        success: true,
        data: data,
      };
    } catch (error) {
      console.error('API request failed:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Network error',
      };
    }
  }

  /**
   * GET request
   */
  static async get<T = any>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: 'GET' });
  }

  /**
   * GET request for binary data (like parquet files) with 503 handling
   */
  static async getBinary(endpoint: string): Promise<ApiResponse<string>> {
    try {
      // Get proper auth headers with X-Enhanced-Groups
      let authHeaders: Record<string, string>;
      try {
        authHeaders = await getAuthHeaders();
        console.log('[ApiService] Binary auth headers obtained:', Object.keys(authHeaders));
      } catch (authError) {
        console.error('[ApiService] Failed to get binary auth headers:', authError);
        // Fallback to old method if new one fails
        authHeaders = {
          'Authorization': `Bearer ${this.getAuthTokens()?.AccessToken || ''}`,
        };
      }
      
      const response = await fetch(`${this.baseUrl}${endpoint}`, {
        method: 'GET',
        headers: {
          ...authHeaders,
        },
      });

      // Handle 503 maintenance mode globally
      if (response.status === 503) {
        const error = await parseApiError(response);
        showMaintenanceScreen(error);
        return {
          success: false,
          error: error.message,
        };
      }

      if (!response.ok) {
        const errorData = await response.text();
        return {
          success: false,
          error: `HTTP ${response.status}: ${errorData}`,
        };
      }

      // For binary responses, get the response as text (base64)
      const data = await response.text();

      return {
        success: true,
        data: data,
      };
    } catch (error) {
      console.error('API binary request failed:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Network error',
      };
    }
  }

  /**
   * POST request
   */
  static async post<T = any>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  /**
   * PUT request
   */
  static async put<T = any>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  /**
   * DELETE request
   */
  static async delete<T = any>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }

  /**
   * Clear authentication data (for logout)
   */
  static clearAuth(): void {
    localStorage.removeItem('hdcn_auth_user');
    localStorage.removeItem('hdcn_auth_tokens');
  }
}