/**
 * API Service for H-DCN Application
 * 
 * This service handles authenticated API calls using stored JWT tokens
 * from the passwordless authentication system.
 */

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
   * Get authorization headers for API calls
   */
  private static getAuthHeaders(): Record<string, string> {
    const tokens = this.getAuthTokens();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (tokens && tokens.AccessToken) {
      headers['Authorization'] = `Bearer ${tokens.AccessToken}`;
    }

    return headers;
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
   */
  static getCurrentUserRoles(): string[] {
    const tokens = this.getAuthTokens();
    if (tokens && tokens.AccessTokenPayload && tokens.AccessTokenPayload['cognito:groups']) {
      return tokens.AccessTokenPayload['cognito:groups'];
    }
    return [];
  }

  /**
   * Make authenticated API request
   */
  static async request<T = any>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    try {
      const url = endpoint.startsWith('http') ? endpoint : `${this.baseUrl}${endpoint}`;
      
      const response = await fetch(url, {
        ...options,
        headers: {
          ...this.getAuthHeaders(),
          ...options.headers,
        },
      });

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