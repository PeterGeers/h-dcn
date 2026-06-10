/**
 * API Service for H-DCN Application
 * 
 * This service handles authenticated API calls using Amplify v6 session management.
 * All auth state comes from fetchAuthSession() — no localStorage.
 *
 * Requirements: R4.1, R4.3, R6.3, R6.4, R6.5
 */

import { fetchAuthSession } from 'aws-amplify/auth';
import { getAuthHeaders } from '../utils/authHeaders';
import { parseApiError, showMaintenanceScreen } from '../utils/errorHandler';

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export class ApiService {
  private static baseUrl = process.env.REACT_APP_API_BASE_URL || 'https://44sw408alh.execute-api.eu-west-1.amazonaws.com/prod';

  /**
   * Check if user has a valid Amplify session.
   * Uses fetchAuthSession() — no localStorage.
   */
  static async isAuthenticated(): Promise<boolean> {
    try {
      const session = await fetchAuthSession();
      return !!session.tokens?.accessToken;
    } catch {
      return false;
    }
  }

  /**
   * Get current user's email from the Amplify session ID token.
   */
  static async getCurrentUserEmail(): Promise<string | null> {
    try {
      const session = await fetchAuthSession();
      return (session.tokens?.idToken?.payload?.email as string) || null;
    } catch {
      return null;
    }
  }

  /**
   * Get current user's roles (cognito:groups) from the Amplify session access token.
   */
  static async getCurrentUserRoles(): Promise<string[]> {
    try {
      const session = await fetchAuthSession();
      const groups = (session.tokens?.accessToken?.payload?.['cognito:groups'] as string[] | undefined) ?? [];
      return groups;
    } catch {
      return [];
    }
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
      
      const authHeaders = await getAuthHeaders();
      
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
      const authHeaders = await getAuthHeaders();
      
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
}