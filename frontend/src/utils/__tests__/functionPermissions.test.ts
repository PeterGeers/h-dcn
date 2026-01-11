import {
  userHasPermissionWithRegion,
  getUserAccessibleRegions,
  userHasPermissionType,
  validatePermissionWithRegion,
  checkUIPermission,
  getUserRoles,
  userHasRole,
  userHasAnyRole,
  userHasAllRoles
} from '../functionPermissions';
import { HDCNGroup } from '../../types/user';

// Mock user objects for testing
const mockUserWithMembersCRUD = {
  id: 'test1',
  username: 'test1',
  email: 'test1@example.com',
  groups: ['Members_CRUD', 'Regio_Utrecht'] as HDCNGroup[],
  attributes: {}
};

const mockUserWithMembersRead = {
  id: 'test2',
  username: 'test2',
  email: 'test2@example.com',
  groups: ['Members_Read', 'Regio_All'] as HDCNGroup[],
  attributes: {}
};

const mockUserWithNoRegion = {
  id: 'test3',
  username: 'test3',
  email: 'test3@example.com',
  groups: ['Members_CRUD'] as HDCNGroup[],
  attributes: {}
};

describe('Permission System', () => {
  describe('getUserRoles', () => {
    test('should extract roles from groups array', () => {
      const roles = getUserRoles(mockUserWithMembersCRUD);
      expect(roles).toEqual(['Members_CRUD', 'Regio_Utrecht']);
    });

    test('should return empty array for user with no groups', () => {
      const userWithNoGroups = { id: 'test', username: 'test', email: 'test@example.com', attributes: {} };
      const roles = getUserRoles(userWithNoGroups);
      expect(roles).toEqual([]);
    });
  });

  describe('userHasRole', () => {
    test('should return true when user has the specific role', () => {
      expect(userHasRole(mockUserWithMembersCRUD, 'Members_CRUD')).toBe(true);
      expect(userHasRole(mockUserWithMembersCRUD, 'Regio_Utrecht')).toBe(true);
    });

    test('should return false when user lacks the specific role', () => {
      expect(userHasRole(mockUserWithMembersCRUD, 'Members_Read')).toBe(false);
      expect(userHasRole(mockUserWithMembersCRUD, 'Regio_Limburg')).toBe(false);
    });

    test('should return false for null user', () => {
      expect(userHasRole(null, 'Members_CRUD')).toBe(false);
    });
  });

  describe('userHasAnyRole', () => {
    test('should return true when user has any of the specified roles', () => {
      expect(userHasAnyRole(mockUserWithMembersCRUD, ['Members_CRUD', 'Members_Read'])).toBe(true);
      expect(userHasAnyRole(mockUserWithMembersCRUD, ['Regio_Utrecht', 'Regio_Limburg'])).toBe(true);
    });

    test('should return false when user has none of the specified roles', () => {
      expect(userHasAnyRole(mockUserWithMembersCRUD, ['Members_Read', 'Events_CRUD'])).toBe(false);
    });

    test('should return false for null user or empty roles array', () => {
      expect(userHasAnyRole(null, ['Members_CRUD'])).toBe(false);
      expect(userHasAnyRole(mockUserWithMembersCRUD, [])).toBe(false);
    });
  });

  describe('userHasAllRoles', () => {
    test('should return true when user has all specified roles', () => {
      expect(userHasAllRoles(mockUserWithMembersCRUD, ['Members_CRUD', 'Regio_Utrecht'])).toBe(true);
    });

    test('should return false when user lacks any of the specified roles', () => {
      expect(userHasAllRoles(mockUserWithMembersCRUD, ['Members_CRUD', 'Members_Read'])).toBe(false);
      expect(userHasAllRoles(mockUserWithMembersCRUD, ['Members_CRUD', 'Regio_Limburg'])).toBe(false);
    });

    test('should return false for null user or empty roles array', () => {
      expect(userHasAllRoles(null, ['Members_CRUD'])).toBe(false);
      expect(userHasAllRoles(mockUserWithMembersCRUD, [])).toBe(false);
    });
  });

  describe('userHasPermissionType', () => {
    test('should grant CRUD permission for Members_CRUD role', () => {
      expect(userHasPermissionType(mockUserWithMembersCRUD, 'members', 'crud')).toBe(true);
    });

    test('should grant read permission for Members_Read role', () => {
      expect(userHasPermissionType(mockUserWithMembersRead, 'members', 'read')).toBe(true);
    });

    test('should deny write permission for Members_Read role', () => {
      expect(userHasPermissionType(mockUserWithMembersRead, 'members', 'crud')).toBe(false);
    });
  });

  describe('getUserAccessibleRegions', () => {
    test('should return specific region for regional user', () => {
      const regions = getUserAccessibleRegions(mockUserWithMembersCRUD);
      expect(regions).toContain('utrecht');
    });

    test('should return all regions for Regio_All user', () => {
      const regions = getUserAccessibleRegions(mockUserWithMembersRead);
      expect(regions).toEqual(['all']);
    });

    test('should return empty array for user with no regional roles', () => {
      const regions = getUserAccessibleRegions(mockUserWithNoRegion);
      expect(regions).toEqual([]);
    });
  });

  describe('userHasPermissionWithRegion', () => {
    test('should grant access when user has both permission and region', () => {
      expect(userHasPermissionWithRegion(mockUserWithMembersCRUD, 'members_crud', 'utrecht')).toBe(true);
    });

    test('should deny access when user lacks regional access', () => {
      expect(userHasPermissionWithRegion(mockUserWithMembersCRUD, 'members_crud', 'limburg')).toBe(false);
    });

    test('should grant access for Regio_All users to any region', () => {
      expect(userHasPermissionWithRegion(mockUserWithMembersRead, 'members_read', 'utrecht')).toBe(true);
      expect(userHasPermissionWithRegion(mockUserWithMembersRead, 'members_read', 'limburg')).toBe(true);
    });
  });

  describe('validatePermissionWithRegion', () => {
    test('should validate multiple permissions correctly', () => {
      expect(validatePermissionWithRegion(
        mockUserWithMembersCRUD, 
        ['members_read', 'members_crud'], 
        'utrecht'
      )).toBe(true);
    });

    test('should fail when user lacks one of multiple permissions', () => {
      expect(validatePermissionWithRegion(
        mockUserWithMembersRead, 
        ['members_read', 'members_crud'], 
        'utrecht'
      )).toBe(false);
    });
  });

  describe('checkUIPermission', () => {
    test('should grant UI access for valid permission + region combination', () => {
      expect(checkUIPermission(mockUserWithMembersCRUD, 'members', 'write', 'utrecht')).toBe(true);
    });

    test('should deny UI access for invalid region', () => {
      expect(checkUIPermission(mockUserWithMembersCRUD, 'members', 'write', 'limburg')).toBe(false);
    });

    test('should deny access for user with no regional roles', () => {
      expect(checkUIPermission(mockUserWithNoRegion, 'members', 'read')).toBe(false);
    });
  });
});