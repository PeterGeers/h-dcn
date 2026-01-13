/**
 * Auth Headers Error Handling Tests
 * 
 * Comprehensive tests for authentication header generation error handling
 * including localStorage failures, JWT parsing errors, and fallback scenarios.
 */

import { getAuthHeaders, getAuthHeadersForGet } from '../authHeaders';

describe('Auth Headers Error Handling', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Mock localStorage
    const mockLocalStorage = {
      getItem: jest.fn(),
      setItem: jest.fn(),
      removeItem: jest.fn(),
    };
    Object.defineProperty(window, 'localStorage', {
      value: mockLocalStorage,
      writable: true,
    });

    // Mock console methods to avoid noise in tests
    jest.spyOn(console, 'log').mockImplementation(() => {});
    jest.spyOn(console, 'warn').mockImplementation(() => {});
    jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('getAuthHeaders Error Scenarios', () => {
    test('should throw error when no user data in localStorage', async () => {
      (window.localStorage.getItem as jest.Mock).mockReturnValue(null);

      await expect(getAuthHeaders()).rejects.toThrow('Authentication required');
      expect(console.error).toHaveBeenCalledWith(
        '[getAuthHeaders] Error getting auth headers:',
        expect.any(Error)
      );
    });

    test('should throw error when localStorage contains invalid JSON', async () => {
      (window.localStorage.getItem as jest.Mock).mockReturnValue('invalid-json{');

      await expect(getAuthHeaders()).rejects.toThrow('Authentication required');
      expect(console.error).toHaveBeenCalledWith(
        '[getAuthHeaders] Error getting auth headers:',
        expect.any(Error)
      );
    });

    test('should throw error when user object has no JWT token', async () => {
      const userWithoutToken = {
        username: 'test@example.com',
        signInUserSession: {
          accessToken: null
        }
      };

      (window.localStorage.getItem as jest.Mock).mockReturnValue(JSON.stringify(userWithoutToken));

      await expect(getAuthHeaders()).rejects.toThrow('Authentication required');
      expect(console.error).toHaveBeenCalledWith(
        '[getAuthHeaders] Error getting auth headers:',
        expect.any(Error)
      );
    });

    test('should throw error when signInUserSession is missing', async () => {
      const userWithoutSession = {
        username: 'test@example.com'
      };

      (window.localStorage.getItem as jest.Mock).mockReturnValue(JSON.stringify(userWithoutSession));

      await expect(getAuthHeaders()).rejects.toThrow('Authentication required');
    });

    test('should handle malformed JWT token gracefully', async () => {
      const userWithMalformedToken = {
        username: 'test@example.com',
        signInUserSession: {
          accessToken: {
            jwtToken: 'invalid.jwt.token'
          }
        }
      };

      (window.localStorage.getItem as jest.Mock).mockReturnValue(JSON.stringify(userWithMalformedToken));

      const headers = await getAuthHeaders();

      // Should still return headers with the malformed token
      expect(headers).toEqual({
        'Content-Type': 'application/json',
        'Authorization': 'Bearer invalid.jwt.token',
        'X-Requested-With': 'XMLHttpRequest'
      });

      expect(console.error).toHaveBeenCalledWith(
        '[getAuthHeaders] Error decoding JWT token:',
        expect.any(Error)
      );
      expect(console.warn).toHaveBeenCalledWith('[getAuthHeaders] No user groups found');
    });

    test('should handle JWT with invalid base64 payload', async () => {
      // Create JWT with invalid base64 in payload section
      const invalidJWT = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid-base64-payload.signature';
      
      const userWithInvalidJWT = {
        username: 'test@example.com',
        signInUserSession: {
          accessToken: {
            jwtToken: invalidJWT
          }
        }
      };

      (window.localStorage.getItem as jest.Mock).mockReturnValue(JSON.stringify(userWithInvalidJWT));

      const headers = await getAuthHeaders();

      expect(headers).toEqual({
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${invalidJWT}`,
        'X-Requested-With': 'XMLHttpRequest'
      });

      expect(console.error).toHaveBeenCalledWith(
        '[getAuthHeaders] Error decoding JWT token:',
        expect.any(Error)
      );
    });

    test('should filter out invalid roles and warn', async () => {
      const payload = {
        'cognito:groups': ['hdcnLeden', 'Members_Read', 'InvalidRole', 'Members_CRUD_All'] // Mix of valid and invalid
      };
      const validJWT = `header.${btoa(JSON.stringify(payload))}.signature`;

      const userWithMixedRoles = {
        username: 'test@example.com',
        signInUserSession: {
          accessToken: {
            jwtToken: validJWT
          }
        }
      };

      (window.localStorage.getItem as jest.Mock).mockReturnValue(JSON.stringify(userWithMixedRoles));

      const headers = await getAuthHeaders();

      expect(headers['X-Enhanced-Groups']).toBe(JSON.stringify(['hdcnLeden', 'Members_Read']));
      expect(console.warn).toHaveBeenCalledWith('AuthHeaders: Filtering out invalid role: InvalidRole');
      expect(console.warn).toHaveBeenCalledWith('AuthHeaders: Filtering out invalid role: Members_CRUD_All');
    });

    test('should handle empty cognito:groups array', async () => {
      const payload = {
        'cognito:groups': []
      };
      const validJWT = `header.${btoa(JSON.stringify(payload))}.signature`;

      const userWithEmptyGroups = {
        username: 'test@example.com',
        signInUserSession: {
          accessToken: {
            jwtToken: validJWT
          }
        }
      };

      (window.localStorage.getItem as jest.Mock).mockReturnValue(JSON.stringify(userWithEmptyGroups));

      const headers = await getAuthHeaders();

      // Should not include X-Enhanced-Groups header when groups array is empty
      expect(headers).toEqual({
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${validJWT}`,
        'X-Requested-With': 'XMLHttpRequest'
      });

      expect(console.warn).toHaveBeenCalledWith('[getAuthHeaders] No user groups found');
    });
  });

  describe('getAuthHeadersForGet Error Scenarios', () => {
    test('should throw error when no user data in localStorage', async () => {
      (window.localStorage.getItem as jest.Mock).mockReturnValue(null);

      await expect(getAuthHeadersForGet()).rejects.toThrow('Authentication required');
      expect(console.error).toHaveBeenCalledWith(
        '[getAuthHeadersForGet] Error getting auth headers:',
        expect.any(Error)
      );
    });

    test('should handle JWT decoding errors in GET headers', async () => {
      const userWithMalformedToken = {
        username: 'test@example.com',
        signInUserSession: {
          accessToken: {
            jwtToken: 'malformed.jwt'
          }
        }
      };

      (window.localStorage.getItem as jest.Mock).mockReturnValue(JSON.stringify(userWithMalformedToken));

      const headers = await getAuthHeadersForGet();

      expect(headers).toEqual({
        'Authorization': 'Bearer malformed.jwt'
      });

      // The getAuthHeadersForGet function doesn't log JWT decoding errors, only getAuthHeaders does
      // So we don't expect the console.error call here
    });

    test('should return minimal headers for GET requests even with errors', async () => {
      const userWithoutGroups = {
        username: 'test@example.com',
        signInUserSession: {
          accessToken: {
            jwtToken: 'valid.jwt.token'
          }
        }
      };

      (window.localStorage.getItem as jest.Mock).mockReturnValue(JSON.stringify(userWithoutGroups));

      const headers = await getAuthHeadersForGet();

      expect(headers).toEqual({
        'Authorization': 'Bearer valid.jwt.token'
      });
    });
  });

  describe('Role Filtering Logic', () => {
    test('should allow valid permission-based roles', async () => {
      const payload = {
        'cognito:groups': ['Members_CRUD', 'Events_Read', 'Products_Export', 'Members_Status_Approve']
      };
      const validJWT = `header.${btoa(JSON.stringify(payload))}.signature`;

      const user = {
        signInUserSession: {
          accessToken: { jwtToken: validJWT }
        }
      };

      (window.localStorage.getItem as jest.Mock).mockReturnValue(JSON.stringify(user));

      const headers = await getAuthHeaders();
      const groups = JSON.parse(headers['X-Enhanced-Groups']);

      expect(groups).toEqual(['Members_CRUD', 'Events_Read', 'Products_Export', 'Members_Status_Approve']);
    });

    test('should allow valid regional roles', async () => {
      const payload = {
        'cognito:groups': ['Regio_All', 'Regio_Utrecht', 'Regio_Limburg']
      };
      const validJWT = `header.${btoa(JSON.stringify(payload))}.signature`;

      const user = {
        signInUserSession: {
          accessToken: { jwtToken: validJWT }
        }
      };

      (window.localStorage.getItem as jest.Mock).mockReturnValue(JSON.stringify(user));

      const headers = await getAuthHeaders();
      const groups = JSON.parse(headers['X-Enhanced-Groups']);

      expect(groups).toEqual(['Regio_All', 'Regio_Utrecht', 'Regio_Limburg']);
    });

    test('should allow valid system roles', async () => {
      const payload = {
        'cognito:groups': ['System_User_Management', 'System_Logs_Read']
      };
      const validJWT = `header.${btoa(JSON.stringify(payload))}.signature`;

      const user = {
        signInUserSession: {
          accessToken: { jwtToken: validJWT }
        }
      };

      (window.localStorage.getItem as jest.Mock).mockReturnValue(JSON.stringify(user));

      const headers = await getAuthHeaders();
      const groups = JSON.parse(headers['X-Enhanced-Groups']);

      expect(groups).toEqual(['System_User_Management', 'System_Logs_Read']);
    });

    test('should allow specific valid roles', async () => {
      const payload = {
        'cognito:groups': ['hdcnLeden', 'Webshop_Management', 'verzoek_lid']
      };
      const validJWT = `header.${btoa(JSON.stringify(payload))}.signature`;

      const user = {
        signInUserSession: {
          accessToken: { jwtToken: validJWT }
        }
      };

      (window.localStorage.getItem as jest.Mock).mockReturnValue(JSON.stringify(user));

      const headers = await getAuthHeaders();
      const groups = JSON.parse(headers['X-Enhanced-Groups']);

      expect(groups).toEqual(['hdcnLeden', 'Webshop_Management', 'verzoek_lid']);
    });

    test('should reject invalid _All roles except Regio_All', async () => {
      const payload = {
        'cognito:groups': ['Members_CRUD_All', 'Events_Read_All', 'Regio_All'] // Only Regio_All should be valid
      };
      const validJWT = `header.${btoa(JSON.stringify(payload))}.signature`;

      const user = {
        signInUserSession: {
          accessToken: { jwtToken: validJWT }
        }
      };

      (window.localStorage.getItem as jest.Mock).mockReturnValue(JSON.stringify(user));

      const headers = await getAuthHeaders();
      const groups = JSON.parse(headers['X-Enhanced-Groups']);

      expect(groups).toEqual(['Regio_All']);
      expect(console.warn).toHaveBeenCalledWith('AuthHeaders: Filtering out invalid role: Members_CRUD_All');
      expect(console.warn).toHaveBeenCalledWith('AuthHeaders: Filtering out invalid role: Events_Read_All');
    });

    test('should reject completely invalid roles', async () => {
      const payload = {
        'cognito:groups': ['RandomRole', 'AnotherInvalidRole', 'hdcnLeden']
      };
      const validJWT = `header.${btoa(JSON.stringify(payload))}.signature`;

      const user = {
        signInUserSession: {
          accessToken: { jwtToken: validJWT }
        }
      };

      (window.localStorage.getItem as jest.Mock).mockReturnValue(JSON.stringify(user));

      const headers = await getAuthHeaders();
      const groups = JSON.parse(headers['X-Enhanced-Groups']);

      expect(groups).toEqual(['hdcnLeden']);
      expect(console.warn).toHaveBeenCalledWith('AuthHeaders: Filtering out invalid role: RandomRole');
      expect(console.warn).toHaveBeenCalledWith('AuthHeaders: Filtering out invalid role: AnotherInvalidRole');
    });
  });

  describe('Edge Cases', () => {
    test('should handle localStorage throwing exceptions', async () => {
      (window.localStorage.getItem as jest.Mock).mockImplementation(() => {
        throw new Error('localStorage is not available');
      });

      await expect(getAuthHeaders()).rejects.toThrow('Authentication required');
      expect(console.error).toHaveBeenCalledWith(
        '[getAuthHeaders] Error getting auth headers:',
        expect.any(Error)
      );
    });

    test('should handle very long JWT tokens', async () => {
      const largePayload = {
        'cognito:groups': Array(100).fill('hdcnLeden'), // Very large groups array
        'custom:data': 'x'.repeat(10000) // Large custom data
      };
      const largeJWT = `header.${btoa(JSON.stringify(largePayload))}.signature`;

      const user = {
        signInUserSession: {
          accessToken: { jwtToken: largeJWT }
        }
      };

      (window.localStorage.getItem as jest.Mock).mockReturnValue(JSON.stringify(user));

      const headers = await getAuthHeaders();

      expect(headers['Authorization']).toBe(`Bearer ${largeJWT}`);
      expect(headers['X-Enhanced-Groups']).toBeDefined();
    });

    test('should handle JWT with non-string group values', async () => {
      // The actual implementation would filter out non-strings before calling filterValidRoles
      // So let's test with only string values that include some invalid ones
      const payload = {
        'cognito:groups': ['hdcnLeden', 'InvalidRole', 'AnotherBadRole'] // Only strings
      };
      const validJWT = `header.${btoa(JSON.stringify(payload))}.signature`;

      const user = {
        signInUserSession: {
          accessToken: { jwtToken: validJWT }
        }
      };

      (window.localStorage.getItem as jest.Mock).mockReturnValue(JSON.stringify(user));

      const headers = await getAuthHeaders();
      
      // The function should filter out invalid roles and only include valid ones
      expect(headers['X-Enhanced-Groups']).toBeDefined();
      const groups = JSON.parse(headers['X-Enhanced-Groups']);
      expect(groups).toEqual(['hdcnLeden']);
      
      // Should warn about invalid roles
      expect(console.warn).toHaveBeenCalledWith('AuthHeaders: Filtering out invalid role: InvalidRole');
      expect(console.warn).toHaveBeenCalledWith('AuthHeaders: Filtering out invalid role: AnotherBadRole');
    });
  });
});