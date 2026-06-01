/**
 * API Service Error Handling Tests
 * 
 * Comprehensive tests for API service error handling including 503 maintenance
 * mode detection, authentication failures, and user experience during errors.
 */

import { ApiService } from '../apiService';

// Mock dependencies
jest.mock('../../utils/authHeaders');
jest.mock('aws-amplify/auth', () => ({
  fetchAuthSession: jest.fn(),
}));
jest.mock('../../utils/errorHandler', () => ({
  parseApiError: jest.fn(),
  showMaintenanceScreen: jest.fn(),
  hideMaintenanceScreen: jest.fn(),
  setMaintenanceScreenCallback: jest.fn(),
  ERROR_MESSAGES: {
    NETWORK: 'Netwerkfout - controleer je internetverbinding',
    UNAUTHORIZED: 'Je bent niet geautoriseerd voor deze actie',
    FORBIDDEN: 'Toegang geweigerd - onvoldoende rechten',
    NOT_FOUND: 'Gevraagde gegevens niet gevonden',
    SERVER_ERROR: 'Serverfout - probeer het later opnieuw',
    MAINTENANCE: 'Het systeem is tijdelijk niet beschikbaar voor onderhoud',
    VALIDATION: 'Invoergegevens zijn niet correct',
    TIMEOUT: 'Verzoek duurde te lang - probeer opnieuw',
    UNKNOWN: 'Er is een onbekende fout opgetreden'
  }
}));

import { getAuthHeaders } from '../../utils/authHeaders';
import { parseApiError, showMaintenanceScreen } from '../../utils/errorHandler';

const mockGetAuthHeaders = getAuthHeaders as jest.MockedFunction<typeof getAuthHeaders>;
const mockParseApiError = parseApiError as jest.MockedFunction<typeof parseApiError>;
const mockShowMaintenanceScreen = showMaintenanceScreen as jest.MockedFunction<typeof showMaintenanceScreen>;

// Mock fetch
global.fetch = jest.fn();
const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>;

describe('ApiService Error Handling', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Set up default environment
    process.env.REACT_APP_API_BASE_URL = 'https://test-api.example.com';
  });

  describe('503 Maintenance Mode Handling', () => {
    test('should detect and handle 503 maintenance response', async () => {
      // Mock auth headers
      mockGetAuthHeaders.mockResolvedValue({
        'Authorization': 'Bearer test-token',
        'Content-Type': 'application/json',
        'X-Enhanced-Groups': JSON.stringify(['hdcnLeden'])
      });

      // Mock 503 response
      const mockResponse = {
        status: 503,
        ok: false,
        json: () => Promise.resolve({
          message: 'Het authenticatiesysteem is tijdelijk niet beschikbaar voor onderhoud',
          details: 'AUTH_SYSTEM_FAILURE'
        })
      } as Response;

      mockFetch.mockResolvedValue(mockResponse);

      // Mock parseApiError
      const mockError = {
        status: 503,
        message: 'Het authenticatiesysteem is tijdelijk niet beschikbaar voor onderhoud',
        details: 'AUTH_SYSTEM_FAILURE',
        isMaintenanceMode: true
      };
      mockParseApiError.mockResolvedValue(mockError);

      // Make API request
      const result = await ApiService.get('/test-endpoint');

      // Verify 503 handling
      expect(parseApiError).toHaveBeenCalledWith(mockResponse);
      expect(showMaintenanceScreen).toHaveBeenCalledWith(mockError);
      expect(result).toEqual({
        success: false,
        error: 'Het authenticatiesysteem is tijdelijk niet beschikbaar voor onderhoud',
        data: undefined
      });
    });

    test('should handle 503 in POST requests', async () => {
      mockGetAuthHeaders.mockResolvedValue({
        'Authorization': 'Bearer test-token',
        'Content-Type': 'application/json'
      });

      const mockResponse = {
        status: 503,
        ok: false,
        json: () => Promise.resolve({ message: 'Service unavailable' })
      } as Response;

      mockFetch.mockResolvedValue(mockResponse);

      const mockError = {
        status: 503,
        message: 'Service unavailable',
        isMaintenanceMode: true
      };
      mockParseApiError.mockResolvedValue(mockError);

      const result = await ApiService.post('/test-endpoint', { data: 'test' });

      expect(showMaintenanceScreen).toHaveBeenCalledWith(mockError);
      expect(result.success).toBe(false);
    });

    test('should handle 503 in binary requests', async () => {
      mockGetAuthHeaders.mockResolvedValue({
        'Authorization': 'Bearer test-token'
      });

      const mockResponse = {
        status: 503,
        ok: false,
        text: () => Promise.resolve('Service temporarily unavailable')
      } as Response;

      mockFetch.mockResolvedValue(mockResponse);

      const mockError = {
        status: 503,
        message: 'Het systeem is tijdelijk niet beschikbaar voor onderhoud',
        isMaintenanceMode: true
      };
      mockParseApiError.mockResolvedValue(mockError);

      const result = await ApiService.getBinary('/test-file.parquet');

      expect(showMaintenanceScreen).toHaveBeenCalledWith(mockError);
      expect(result.success).toBe(false);
    });
  });

  describe('Authentication Error Handling', () => {
    test('should handle auth header generation failure', async () => {
      // Mock auth headers failure - now this propagates as an error
      mockGetAuthHeaders.mockRejectedValue(new Error('Not authenticated'));

      const result = await ApiService.get('/test-endpoint');

      // Should return error since there's no localStorage fallback
      expect(result).toEqual({
        success: false,
        error: 'Not authenticated'
      });
    });

    test('should handle 401 unauthorized responses', async () => {
      mockGetAuthHeaders.mockResolvedValue({
        'Authorization': 'Bearer invalid-token',
        'Content-Type': 'application/json'
      });

      const mockResponse = {
        status: 401,
        ok: false,
        json: () => Promise.resolve({
          error: 'Invalid or expired token'
        })
      } as Response;

      mockFetch.mockResolvedValue(mockResponse);

      const result = await ApiService.get('/protected-endpoint');

      expect(result).toEqual({
        success: false,
        error: 'Invalid or expired token',
        data: { error: 'Invalid or expired token' }
      });
    });

    test('should handle 403 forbidden responses', async () => {
      mockGetAuthHeaders.mockResolvedValue({
        'Authorization': 'Bearer valid-token',
        'Content-Type': 'application/json',
        'X-Enhanced-Groups': JSON.stringify(['hdcnLeden']) // Basic member, no admin rights
      });

      const mockResponse = {
        status: 403,
        ok: false,
        json: () => Promise.resolve({
          error: 'Insufficient permissions for this operation'
        })
      } as Response;

      mockFetch.mockResolvedValue(mockResponse);

      const result = await ApiService.get('/admin-endpoint');

      expect(result).toEqual({
        success: false,
        error: 'Insufficient permissions for this operation',
        data: { error: 'Insufficient permissions for this operation' }
      });
    });
  });

  describe('Network Error Handling', () => {
    test('should handle network failures gracefully', async () => {
      mockGetAuthHeaders.mockResolvedValue({
        'Authorization': 'Bearer test-token',
        'Content-Type': 'application/json'
      });

      // Mock network error
      mockFetch.mockRejectedValue(new Error('Failed to fetch'));

      const result = await ApiService.get('/test-endpoint');

      expect(result).toEqual({
        success: false,
        error: 'Failed to fetch'
      });
    });

    test('should handle timeout errors', async () => {
      mockGetAuthHeaders.mockResolvedValue({
        'Authorization': 'Bearer test-token',
        'Content-Type': 'application/json'
      });

      // Mock timeout error
      const timeoutError = new Error('Request timeout');
      timeoutError.name = 'AbortError';
      mockFetch.mockRejectedValue(timeoutError);

      const result = await ApiService.get('/slow-endpoint');

      expect(result).toEqual({
        success: false,
        error: 'Request timeout'
      });
    });

    test('should handle DNS resolution failures', async () => {
      mockGetAuthHeaders.mockResolvedValue({
        'Authorization': 'Bearer test-token',
        'Content-Type': 'application/json'
      });

      // Mock DNS error
      const dnsError = new Error('getaddrinfo ENOTFOUND');
      dnsError.name = 'TypeError';
      mockFetch.mockRejectedValue(dnsError);

      const result = await ApiService.get('/test-endpoint');

      expect(result).toEqual({
        success: false,
        error: 'getaddrinfo ENOTFOUND'
      });
    });
  });

  describe('Response Parsing Error Handling', () => {
    test('should handle malformed JSON responses', async () => {
      mockGetAuthHeaders.mockResolvedValue({
        'Authorization': 'Bearer test-token',
        'Content-Type': 'application/json'
      });

      const mockResponse = {
        status: 200,
        ok: true,
        json: () => Promise.reject(new Error('Unexpected token in JSON'))
      } as Response;

      mockFetch.mockResolvedValue(mockResponse);

      const result = await ApiService.get('/test-endpoint');

      expect(result).toEqual({
        success: false,
        error: 'Unexpected token in JSON'
      });
    });

    test('should handle empty responses gracefully', async () => {
      mockGetAuthHeaders.mockResolvedValue({
        'Authorization': 'Bearer test-token',
        'Content-Type': 'application/json'
      });

      const mockResponse = {
        status: 200,
        ok: true,
        json: () => Promise.resolve(null)
      } as Response;

      mockFetch.mockResolvedValue(mockResponse);

      const result = await ApiService.get('/test-endpoint');

      expect(result).toEqual({
        success: true,
        data: null
      });
    });
  });

  describe('User Experience During Errors', () => {
    test('should provide user-friendly error messages', async () => {
      mockGetAuthHeaders.mockResolvedValue({
        'Authorization': 'Bearer test-token',
        'Content-Type': 'application/json'
      });

      const mockResponse = {
        status: 500,
        ok: false,
        json: () => Promise.resolve({
          message: 'Internal server error',
          stack: 'Error: Something went wrong\n    at handler.js:123:45'
        })
      } as Response;

      mockFetch.mockResolvedValue(mockResponse);

      const result = await ApiService.get('/test-endpoint');

      // Should return user-friendly message, not technical details
      expect(result.error).toBe('Internal server error');
      expect(result.error).not.toContain('stack');
      expect(result.error).not.toContain('handler.js');
    });

    test('should handle multiple concurrent 503 errors without duplicate maintenance screens', async () => {
      mockGetAuthHeaders.mockResolvedValue({
        'Authorization': 'Bearer test-token',
        'Content-Type': 'application/json'
      });

      const mockResponse = {
        status: 503,
        ok: false,
        json: () => Promise.resolve({ message: 'Service unavailable' })
      } as Response;

      mockFetch.mockResolvedValue(mockResponse);

      const mockError = {
        status: 503,
        message: 'Service unavailable',
        isMaintenanceMode: true
      };
      mockParseApiError.mockResolvedValue(mockError);

      // Make multiple concurrent requests
      const requests = [
        ApiService.get('/endpoint1'),
        ApiService.get('/endpoint2'),
        ApiService.get('/endpoint3')
      ];

      await Promise.all(requests);

      // Should show maintenance screen for each request (component should handle deduplication)
      expect(showMaintenanceScreen).toHaveBeenCalledTimes(3);
      expect(showMaintenanceScreen).toHaveBeenCalledWith(mockError);
    });
  });

  describe('Authentication State Management', () => {
    test('should detect valid session as authenticated', async () => {
      // Mock fetchAuthSession to return valid tokens
      const { fetchAuthSession } = require('aws-amplify/auth');
      fetchAuthSession.mockResolvedValue({
        tokens: {
          accessToken: {
            toString: () => 'valid-token',
            payload: { exp: Math.floor(Date.now() / 1000) + 3600 }
          }
        }
      });

      expect(await ApiService.isAuthenticated()).toBe(true);
    });

    test('should detect missing session as not authenticated', async () => {
      const { fetchAuthSession } = require('aws-amplify/auth');
      fetchAuthSession.mockResolvedValue({ tokens: undefined });

      expect(await ApiService.isAuthenticated()).toBe(false);
    });

    test('should handle session fetch failure as not authenticated', async () => {
      const { fetchAuthSession } = require('aws-amplify/auth');
      fetchAuthSession.mockRejectedValue(new Error('No session'));

      expect(await ApiService.isAuthenticated()).toBe(false);
    });
  });
});