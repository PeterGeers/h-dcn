import { 
  getUserRoles, 
  getCurrentUserRolesFromSession,
  userHasRole,
  userHasAnyRole,
  userHasAllRoles
} from '../functionPermissions';
import { HDCNGroup } from '../../types/user';

// Mock the authService
jest.mock('../../services/authService', () => ({
  getCurrentUserRoles: jest.fn()
}));

import { getCurrentUserRoles } from '../../services/authService';
const mockGetCurrentUserRoles = getCurrentUserRoles as jest.MockedFunction<typeof getCurrentUserRoles>;

describe('Role Extraction from User Tokens', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('getUserRoles', () => {
    it('should extract roles from new user object with groups array', () => {
      const user = {
        groups: ['hdcnLeden', 'Members_Read_All'] as HDCNGroup[]
      };

      const roles = getUserRoles(user);
      
      expect(roles).toEqual(['hdcnLeden', 'Members_Read_All']);
    });

    it('should extract roles from legacy JWT token structure', () => {
      const user = {
        signInUserSession: {
          accessToken: {
            payload: {
              'cognito:groups': ['hdcnLeden', 'Members_CRUD_All']
            }
          }
        }
      };

      const roles = getUserRoles(user);
      
      expect(roles).toEqual(['hdcnLeden', 'Members_CRUD_All']);
    });

    it('should prefer groups array over JWT token payload', () => {
      const user = {
        groups: ['hdcnLeden', 'Members_Read_All'] as HDCNGroup[],
        signInUserSession: {
          accessToken: {
            payload: {
              'cognito:groups': ['hdcnLeden', 'Members_CRUD_All']
            }
          }
        }
      };

      const roles = getUserRoles(user);
      
      // Should use groups array, not JWT payload
      expect(roles).toEqual(['hdcnLeden', 'Members_Read_All']);
    });

    it('should return empty array when no roles available', () => {
      const user = {};

      const roles = getUserRoles(user);
      
      expect(roles).toEqual([]);
    });

    it('should return empty array when JWT payload has no cognito:groups', () => {
      const user = {
        signInUserSession: {
          accessToken: {
            payload: {}
          }
        }
      };

      const roles = getUserRoles(user);
      
      expect(roles).toEqual([]);
    });

    it('should handle null/undefined cognito:groups gracefully', () => {
      const userWithNull = {
        signInUserSession: {
          accessToken: {
            payload: {
              'cognito:groups': null
            }
          }
        }
      };

      const userWithUndefined = {
        signInUserSession: {
          accessToken: {
            payload: {
              'cognito:groups': undefined
            }
          }
        }
      };

      expect(getUserRoles(userWithNull)).toEqual([]);
      expect(getUserRoles(userWithUndefined)).toEqual([]);
    });
  });

  describe('getCurrentUserRolesFromSession', () => {
    it('should get roles from current authentication session', async () => {
      const expectedRoles: HDCNGroup[] = ['hdcnLeden', 'Members_Read_All'];
      mockGetCurrentUserRoles.mockResolvedValue(expectedRoles);

      const roles = await getCurrentUserRolesFromSession();
      
      expect(roles).toEqual(expectedRoles);
      expect(mockGetCurrentUserRoles).toHaveBeenCalledTimes(1);
    });

    it('should return empty array when session query fails', async () => {
      mockGetCurrentUserRoles.mockRejectedValue(new Error('Session failed'));

      const roles = await getCurrentUserRolesFromSession();
      
      expect(roles).toEqual([]);
    });

    it('should handle various H-DCN role types', async () => {
      const complexRoles: HDCNGroup[] = [
        'hdcnLeden',
        'Members_CRUD_All',
        'Events_Read_All',
        'Regional_Chairman_Region1',
        'System_User_Management'
      ];
      mockGetCurrentUserRoles.mockResolvedValue(complexRoles);

      const roles = await getCurrentUserRolesFromSession();
      
      expect(roles).toEqual(complexRoles);
      expect(roles).toHaveLength(5);
    });
  });

  describe('userHasRole', () => {
    it('should return true when user has the specified role', () => {
      const user = {
        groups: ['hdcnLeden', 'Members_Read_All'] as HDCNGroup[]
      };

      expect(userHasRole(user, 'hdcnLeden')).toBe(true);
      expect(userHasRole(user, 'Members_Read_All')).toBe(true);
    });

    it('should return false when user does not have the specified role', () => {
      const user = {
        groups: ['hdcnLeden'] as HDCNGroup[]
      };

      expect(userHasRole(user, 'Members_CRUD_All')).toBe(false);
    });

    it('should return false when user is null', () => {
      expect(userHasRole(null, 'hdcnLeden')).toBe(false);
    });

    it('should work with legacy JWT token structure', () => {
      const user = {
        signInUserSession: {
          accessToken: {
            payload: {
              'cognito:groups': ['hdcnLeden', 'Members_CRUD_All']
            }
          }
        }
      };

      expect(userHasRole(user, 'hdcnLeden')).toBe(true);
      expect(userHasRole(user, 'Members_CRUD_All')).toBe(true);
      expect(userHasRole(user, 'Events_Read_All')).toBe(false);
    });
  });

  describe('userHasAnyRole', () => {
    it('should return true when user has any of the specified roles', () => {
      const user = {
        groups: ['hdcnLeden', 'Members_Read_All'] as HDCNGroup[]
      };

      expect(userHasAnyRole(user, ['Members_Read_All', 'Members_CRUD_All'])).toBe(true);
      expect(userHasAnyRole(user, ['hdcnLeden'])).toBe(true);
    });

    it('should return false when user has none of the specified roles', () => {
      const user = {
        groups: ['hdcnLeden'] as HDCNGroup[]
      };

      expect(userHasAnyRole(user, ['Members_CRUD_All', 'Events_Read_All'])).toBe(false);
    });

    it('should return false when user is null', () => {
      expect(userHasAnyRole(null, ['hdcnLeden'])).toBe(false);
    });

    it('should return false when roles array is empty', () => {
      const user = {
        groups: ['hdcnLeden'] as HDCNGroup[]
      };

      expect(userHasAnyRole(user, [])).toBe(false);
    });
  });

  describe('userHasAllRoles', () => {
    it('should return true when user has all of the specified roles', () => {
      const user = {
        groups: ['hdcnLeden', 'Members_Read_All', 'Events_Read_All'] as HDCNGroup[]
      };

      expect(userHasAllRoles(user, ['hdcnLeden', 'Members_Read_All'])).toBe(true);
      expect(userHasAllRoles(user, ['hdcnLeden'])).toBe(true);
    });

    it('should return false when user is missing some of the specified roles', () => {
      const user = {
        groups: ['hdcnLeden', 'Members_Read_All'] as HDCNGroup[]
      };

      expect(userHasAllRoles(user, ['hdcnLeden', 'Members_Read_All', 'Events_Read_All'])).toBe(false);
    });

    it('should return false when user is null', () => {
      expect(userHasAllRoles(null, ['hdcnLeden'])).toBe(false);
    });

    it('should return false when roles array is empty', () => {
      const user = {
        groups: ['hdcnLeden'] as HDCNGroup[]
      };

      expect(userHasAllRoles(user, [])).toBe(false);
    });
  });

  describe('Complex Role Scenarios', () => {
    it('should handle multiple administrative roles', () => {
      const adminUser = {
        groups: [
          'hdcnLeden',
          'Members_CRUD_All',
          'Events_CRUD_All',
          'System_User_Management',
          'Regional_Chairman_Region1'
        ] as HDCNGroup[]
      };

      expect(userHasRole(adminUser, 'Members_CRUD_All')).toBe(true);
      expect(userHasAnyRole(adminUser, ['Members_CRUD_All', 'Members_Read_All'])).toBe(true);
      expect(userHasAllRoles(adminUser, ['hdcnLeden', 'Members_CRUD_All'])).toBe(true);
      expect(userHasAllRoles(adminUser, ['hdcnLeden', 'Members_CRUD_All', 'NonExistentRole'])).toBe(false);
    });

    it('should handle regional roles correctly', () => {
      const regionalUser = {
        groups: [
          'hdcnLeden',
          'Regional_Chairman_Region1',
          'Regional_Secretary_Region2'
        ] as HDCNGroup[]
      };

      expect(userHasRole(regionalUser, 'Regional_Chairman_Region1')).toBe(true);
      expect(userHasRole(regionalUser, 'Regional_Secretary_Region2')).toBe(true);
      expect(userHasRole(regionalUser, 'Regional_Chairman_Region2')).toBe(false);
      
      expect(userHasAnyRole(regionalUser, [
        'Regional_Chairman_Region1',
        'Regional_Chairman_Region3'
      ])).toBe(true);
    });

    it('should handle basic member with no additional roles', () => {
      const basicUser = {
        groups: ['hdcnLeden'] as HDCNGroup[]
      };

      expect(userHasRole(basicUser, 'hdcnLeden')).toBe(true);
      expect(userHasRole(basicUser, 'Members_CRUD_All')).toBe(false);
      expect(userHasAnyRole(basicUser, ['hdcnLeden', 'Members_CRUD_All'])).toBe(true);
      expect(userHasAllRoles(basicUser, ['hdcnLeden'])).toBe(true);
      expect(userHasAllRoles(basicUser, ['hdcnLeden', 'Members_CRUD_All'])).toBe(false);
    });
  });

  describe('Integration with Authentication Flow', () => {
    it('should work with user objects from useAuth hook', () => {
      // Simulate user object structure from useAuth hook
      const userFromAuth = {
        id: 'user-123',
        username: 'testuser',
        email: 'test@example.com',
        groups: ['hdcnLeden', 'Members_Read_All'] as HDCNGroup[],
        attributes: {
          email: 'test@example.com',
          username: 'testuser'
        }
      };

      const roles = getUserRoles(userFromAuth);
      
      expect(roles).toEqual(['hdcnLeden', 'Members_Read_All']);
      expect(userHasRole(userFromAuth, 'hdcnLeden')).toBe(true);
      expect(userHasRole(userFromAuth, 'Members_Read_All')).toBe(true);
    });

    it('should handle role updates during session', async () => {
      // Simulate role update scenario
      const initialRoles: HDCNGroup[] = ['hdcnLeden'];
      const updatedRoles: HDCNGroup[] = ['hdcnLeden', 'Members_Read_All'];

      mockGetCurrentUserRoles
        .mockResolvedValueOnce(initialRoles)
        .mockResolvedValueOnce(updatedRoles);

      const initialResult = await getCurrentUserRolesFromSession();
      expect(initialResult).toEqual(initialRoles);

      const updatedResult = await getCurrentUserRolesFromSession();
      expect(updatedResult).toEqual(updatedRoles);
    });
  });
});