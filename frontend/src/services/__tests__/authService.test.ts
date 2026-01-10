import { 
  decodeJWTPayload, 
  validateCognitoGroupsClaim, 
  getCurrentUserRoles,
  getCurrentUserInfo,
  validateRoleCombinations,
  getCurrentUserRolesValidated
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
        'cognito:groups': ['hdcnLeden', 'Members_Read'],
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
        'cognito:groups': ['hdcnLeden', 'Members_Read'],
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

    it('should extract and filter roles from access token', async () => {
      const payload = {
        'cognito:groups': ['hdcnLeden', 'Members_Read', 'hdcnAdmins', 'Webmaster'] as any[], // Mix of valid and legacy roles
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
      
      // Should only return valid roles, filtering out legacy ones
      expect(roles).toEqual(['hdcnLeden', 'Members_Read']);
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

    it('should filter out legacy roles completely', async () => {
      const payload = {
        'cognito:groups': ['hdcnAdmins', 'Webmaster', 'Members_CRUD_All'] as any[], // All legacy roles
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
      
      // Should return empty array since all roles are legacy
      expect(roles).toEqual([]);
    });

    it('should allow all valid new role structure roles', async () => {
      const payload = {
        'cognito:groups': [
          'Members_CRUD', 
          'Events_Read', 
          'Products_Export',
          'Regio_All',
          'Regio_Utrecht',
          'System_User_Management',
          'Webshop_Management',
          'verzoek_lid'
        ] as any[],
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
      
      // Should return all roles since they're all valid
      expect(roles).toEqual([
        'Members_CRUD', 
        'Events_Read', 
        'Products_Export',
        'Regio_All',
        'Regio_Utrecht',
        'System_User_Management',
        'Webshop_Management',
        'verzoek_lid'
      ]);
    });
  });

  describe('getCurrentUserInfo', () => {
    beforeEach(() => {
      jest.clearAllMocks();
    });

    it('should extract complete user info from access token', async () => {
      const payload = {
        'cognito:groups': ['hdcnLeden', 'Members_Read'] as HDCNGroup[],
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
        roles: ['hdcnLeden', 'Members_Read'],
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
        'cognito:groups': ['hdcnLeden', 'Members_Read'],
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
      expect(decoded?.['cognito:groups']).toEqual(['hdcnLeden', 'Members_Read']);
    });

    it('should handle JWT tokens with multiple H-DCN roles', () => {
      const payload = {
        'cognito:groups': [
          'hdcnLeden',
          'Members_CRUD',
          'Events_Read',
          'Regio_Utrecht'
        ] as HDCNGroup[],
        username: 'admin-user',
        email: 'admin@h-dcn.nl'
      };
      
      const token = createMockJWT(payload);
      const decoded = decodeJWTPayload(token);
      
      expect(decoded?.['cognito:groups']).toHaveLength(4);
      expect(decoded?.['cognito:groups']).toContain('hdcnLeden');
      expect(decoded?.['cognito:groups']).toContain('Members_CRUD');
      expect(decoded?.['cognito:groups']).toContain('Events_Read');
      expect(decoded?.['cognito:groups']).toContain('Regio_Utrecht');
    });
  });

  describe('validateRoleCombinations', () => {
    it('should validate valid permission + region combination', () => {
      const roles: HDCNGroup[] = ['Members_CRUD', 'Regio_All'];
      const validation = validateRoleCombinations(roles);
      
      expect(validation.isValid).toBe(true);
      expect(validation.hasPermissions).toBe(true);
      expect(validation.hasRegions).toBe(true);
      expect(validation.missingRoles).toEqual([]);
    });

    it('should reject permission role without region', () => {
      const roles: HDCNGroup[] = ['Members_CRUD'];
      const validation = validateRoleCombinations(roles);
      
      expect(validation.isValid).toBe(false);
      expect(validation.hasPermissions).toBe(true);
      expect(validation.hasRegions).toBe(false);
      expect(validation.missingRoles).toContain('Regional role (Regio_*)');
    });

    it('should reject region role without permission', () => {
      const roles: HDCNGroup[] = ['Regio_Utrecht'];
      const validation = validateRoleCombinations(roles);
      
      expect(validation.isValid).toBe(false);
      expect(validation.hasPermissions).toBe(false);
      expect(validation.hasRegions).toBe(true);
      expect(validation.missingRoles).toContain('Permission role (*_CRUD, *_Read, *_Export)');
    });

    it('should allow system roles without regional requirements', () => {
      const roles: HDCNGroup[] = ['System_User_Management'];
      const validation = validateRoleCombinations(roles);
      
      expect(validation.isValid).toBe(true);
      expect(validation.hasPermissions).toBe(true);
      expect(validation.hasRegions).toBe(true); // System roles bypass regional requirements
      expect(validation.missingRoles).toEqual([]);
    });

    it('should allow basic member roles without additional requirements', () => {
      const roles: HDCNGroup[] = ['hdcnLeden'];
      const validation = validateRoleCombinations(roles);
      
      expect(validation.isValid).toBe(true);
      expect(validation.hasPermissions).toBe(false); // Basic roles don't have admin permissions
      expect(validation.hasRegions).toBe(true); // Basic roles bypass regional requirements
      expect(validation.missingRoles).toEqual([]);
    });

    it('should warn about multiple regional roles', () => {
      const roles: HDCNGroup[] = ['Members_Read', 'Regio_Utrecht', 'Regio_Limburg'];
      const validation = validateRoleCombinations(roles);
      
      expect(validation.isValid).toBe(true);
      expect(validation.warnings).toContain('User has multiple regional roles - this may cause unexpected behavior');
    });

    it('should not warn about Regio_All with other regions', () => {
      const roles: HDCNGroup[] = ['Members_Read', 'Regio_All', 'Regio_Utrecht'];
      const validation = validateRoleCombinations(roles);
      
      expect(validation.isValid).toBe(true);
      expect(validation.warnings).toEqual([]); // No warning when Regio_All is present
    });
  });

  describe('getCurrentUserRolesValidated', () => {
    beforeEach(() => {
      jest.clearAllMocks();
    });

    it('should return roles with validation for valid combination', async () => {
      const payload = {
        'cognito:groups': ['Members_CRUD', 'Regio_All'] as HDCNGroup[],
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

      const result = await getCurrentUserRolesValidated();
      
      expect(result.roles).toEqual(['Members_CRUD', 'Regio_All']);
      expect(result.validation.isValid).toBe(true);
    });

    it('should return roles with validation for invalid combination', async () => {
      const payload = {
        'cognito:groups': ['Members_CRUD'] as HDCNGroup[], // Missing region
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

      const result = await getCurrentUserRolesValidated();
      
      expect(result.roles).toEqual(['Members_CRUD']);
      expect(result.validation.isValid).toBe(false);
      expect(result.validation.missingRoles).toContain('Regional role (Regio_*)');
    });
  });

  describe('Role Filtering Integration', () => {
    it('should filter legacy roles in getCurrentUserInfo', async () => {
      const payload = {
        'cognito:groups': ['hdcnLeden', 'Members_Read', 'hdcnAdmins', 'Webmaster'] as any[], // Mix of valid and legacy
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
      
      expect(userInfo?.roles).toEqual(['hdcnLeden', 'Members_Read']); // Legacy roles filtered out
    });
  });
});