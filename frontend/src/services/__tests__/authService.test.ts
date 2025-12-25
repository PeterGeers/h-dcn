import { 
  decodeJWTPayload, 
  validateCognitoGroupsClaim, 
  getCurrentUserRoles,
  getCurrentUserInfo 
} from '../authService';
import { HDCNGroup } from '../../types/user';

// Mock aws-amplify/auth
jest.mock('aws-amplify/auth', () => ({
  fetchAuthSession: jest.fn()
}));

import { fetchAuthSession } from 'aws-amplify/auth';
const mockFetchAuthSession = fetchAuthSession as jest.MockedFunction<typeof fetchAuthSession>;

describe('AuthService JWT Token Handling', () => {
  // Helper function to create a mock JWT token
  const createMockJWT = (payload: any): string => {
    const header = { alg: 'HS256', typ: 'JWT' };
    const encodedHeader = btoa(JSON.stringify(header));
    const encodedPayload = btoa(JSON.stringify(payload));
    const signature = 'mock-signature';
    
    return `${encodedHeader}.${encodedPayload}.${signature}`;
  };

  describe('decodeJWTPayload', () => {
    it('should decode valid JWT token payload', () => {
      const payload = {
        'cognito:groups': ['hdcnLeden', 'Members_Read_All'],
        username: 'testuser',
        email: 'test@example.com',
        sub: 'user-123'
      };
      
      const token = createMockJWT(payload);
      const decoded = decodeJWTPayload(token);
      
      expect(decoded).toEqual(payload);
    });

    it('should return null for invalid JWT format', () => {
      const invalidToken = 'invalid.token';
      const decoded = decodeJWTPayload(invalidToken);
      
      expect(decoded).toBeNull();
    });

    it('should return null for malformed JWT payload', () => {
      const invalidToken = 'header.invalid-base64.signature';
      const decoded = decodeJWTPayload(invalidToken);
      
      expect(decoded).toBeNull();
    });
  });

  describe('validateCognitoGroupsClaim', () => {
    it('should validate JWT token with cognito:groups claim', () => {
      const payload = {
        'cognito:groups': ['hdcnLeden', 'Members_Read_All'],
        username: 'testuser'
      };
      
      const token = createMockJWT(payload);
      const isValid = validateCognitoGroupsClaim(token);
      
      expect(isValid).toBe(true);
    });

    it('should validate JWT token with empty cognito:groups array', () => {
      const payload = {
        'cognito:groups': [],
        username: 'testuser'
      };
      
      const token = createMockJWT(payload);
      const isValid = validateCognitoGroupsClaim(token);
      
      expect(isValid).toBe(true);
    });

    it('should reject JWT token missing cognito:groups claim', () => {
      const payload = {
        username: 'testuser',
        email: 'test@example.com'
      };
      
      const token = createMockJWT(payload);
      const isValid = validateCognitoGroupsClaim(token);
      
      expect(isValid).toBe(false);
    });

    it('should reject JWT token with non-array cognito:groups', () => {
      const payload = {
        'cognito:groups': 'not-an-array',
        username: 'testuser'
      };
      
      const token = createMockJWT(payload);
      const isValid = validateCognitoGroupsClaim(token);
      
      expect(isValid).toBe(false);
    });

    it('should reject invalid JWT token', () => {
      const invalidToken = 'invalid.token';
      const isValid = validateCognitoGroupsClaim(invalidToken);
      
      expect(isValid).toBe(false);
    });
  });

  describe('getCurrentUserRoles', () => {
    beforeEach(() => {
      jest.clearAllMocks();
    });

    it('should extract roles from access token', async () => {
      const payload = {
        'cognito:groups': ['hdcnLeden', 'Members_Read_All'] as HDCNGroup[],
        username: 'testuser'
      };
      
      const accessToken = createMockJWT(payload);
      
      mockFetchAuthSession.mockResolvedValue({
        tokens: {
          accessToken: {
            toString: () => accessToken
          }
        }
      } as any);

      const roles = await getCurrentUserRoles();
      
      expect(roles).toEqual(['hdcnLeden', 'Members_Read_All']);
    });

    it('should return empty array when no access token', async () => {
      mockFetchAuthSession.mockResolvedValue({
        tokens: null
      } as any);

      const roles = await getCurrentUserRoles();
      
      expect(roles).toEqual([]);
    });

    it('should return empty array when access token has no cognito:groups', async () => {
      const payload = {
        username: 'testuser',
        email: 'test@example.com'
      };
      
      const accessToken = createMockJWT(payload);
      
      mockFetchAuthSession.mockResolvedValue({
        tokens: {
          accessToken: {
            toString: () => accessToken
          }
        }
      } as any);

      const roles = await getCurrentUserRoles();
      
      expect(roles).toEqual([]);
    });

    it('should handle authentication errors gracefully', async () => {
      mockFetchAuthSession.mockRejectedValue(new Error('Auth failed'));

      const roles = await getCurrentUserRoles();
      
      expect(roles).toEqual([]);
    });
  });

  describe('getCurrentUserInfo', () => {
    beforeEach(() => {
      jest.clearAllMocks();
    });

    it('should extract complete user info from access token', async () => {
      const payload = {
        'cognito:groups': ['hdcnLeden', 'Members_Read_All'] as HDCNGroup[],
        username: 'testuser',
        email: 'test@example.com',
        sub: 'user-123'
      };
      
      const accessToken = createMockJWT(payload);
      
      mockFetchAuthSession.mockResolvedValue({
        tokens: {
          accessToken: {
            toString: () => accessToken
          }
        }
      } as any);

      const userInfo = await getCurrentUserInfo();
      
      expect(userInfo).toEqual({
        username: 'testuser',
        email: 'test@example.com',
        roles: ['hdcnLeden', 'Members_Read_All'],
        sub: 'user-123'
      });
    });

    it('should return null when no access token', async () => {
      mockFetchAuthSession.mockResolvedValue({
        tokens: null
      } as any);

      const userInfo = await getCurrentUserInfo();
      
      expect(userInfo).toBeNull();
    });

    it('should handle missing optional fields gracefully', async () => {
      const payload = {
        'cognito:groups': ['hdcnLeden'] as HDCNGroup[],
        sub: 'user-123'
      };
      
      const accessToken = createMockJWT(payload);
      
      mockFetchAuthSession.mockResolvedValue({
        tokens: {
          accessToken: {
            toString: () => accessToken
          }
        }
      } as any);

      const userInfo = await getCurrentUserInfo();
      
      expect(userInfo).toEqual({
        username: undefined,
        email: undefined,
        roles: ['hdcnLeden'],
        sub: 'user-123'
      });
    });
  });

  describe('JWT Token Integration', () => {
    it('should properly handle real-world JWT token structure', () => {
      // Simulate a real Cognito JWT token structure
      const realWorldPayload = {
        'cognito:groups': ['hdcnLeden', 'Members_Read_All'],
        'cognito:username': 'testuser',
        'email': 'test@example.com',
        'email_verified': true,
        'aud': 'client-id',
        'iss': 'https://cognito-idp.eu-west-1.amazonaws.com/eu-west-1_VtKQHhXGN',
        'exp': Math.floor(Date.now() / 1000) + 3600,
        'iat': Math.floor(Date.now() / 1000),
        'sub': 'user-123'
      };
      
      const token = createMockJWT(realWorldPayload);
      
      // Test decoding
      const decoded = decodeJWTPayload(token);
      expect(decoded).toEqual(realWorldPayload);
      
      // Test validation
      const isValid = validateCognitoGroupsClaim(token);
      expect(isValid).toBe(true);
      
      // Test role extraction
      expect(decoded?.['cognito:groups']).toEqual(['hdcnLeden', 'Members_Read_All']);
    });

    it('should handle JWT tokens with multiple H-DCN roles', () => {
      const payload = {
        'cognito:groups': [
          'hdcnLeden',
          'Members_CRUD_All',
          'Events_Read_All',
          'Regional_Chairman_Region1'
        ] as HDCNGroup[],
        username: 'admin-user',
        email: 'admin@h-dcn.nl'
      };
      
      const token = createMockJWT(payload);
      const decoded = decodeJWTPayload(token);
      
      expect(decoded?.['cognito:groups']).toHaveLength(4);
      expect(decoded?.['cognito:groups']).toContain('hdcnLeden');
      expect(decoded?.['cognito:groups']).toContain('Members_CRUD_All');
      expect(decoded?.['cognito:groups']).toContain('Events_Read_All');
      expect(decoded?.['cognito:groups']).toContain('Regional_Chairman_Region1');
    });
  });
});