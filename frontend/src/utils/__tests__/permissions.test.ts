/**
 * Tests for permission calculation utilities
 */

import {
  getRolePermissions,
  getCombinedPermissions,
  hasPermission,
  getPermissionDescription,
  getPermissionCategory,
  groupPermissionsByCategory,
  getAccessLevelSummary,
  isAdministrator
} from '../permissions';

describe('Permission System', () => {
  describe('getRolePermissions', () => {
    it('should return correct permissions for hdcnLeden role', () => {
      const permissions = getRolePermissions('hdcnLeden');
      expect(permissions).toContain('members:read_own');
      expect(permissions).toContain('webshop:access');
      expect(permissions).toContain('events:read_public');
    });

    it('should return correct permissions for Members_CRUD role', () => {
      const permissions = getRolePermissions('Members_CRUD');
      expect(permissions).toContain('members:read_all');
      expect(permissions).toContain('members:update_all');
      expect(permissions).toContain('members:update_administrative');
    });

    it('should return empty array for unknown role', () => {
      const permissions = getRolePermissions('unknown_role');
      expect(permissions).toEqual([]);
    });
  });

  describe('getCombinedPermissions', () => {
    it('should combine permissions from multiple roles', () => {
      const roles = ['hdcnLeden', 'Members_Read'];
      const permissions = getCombinedPermissions(roles);
      
      expect(permissions).toContain('members:read_own');
      expect(permissions).toContain('members:read_all');
      expect(permissions).toContain('webshop:access');
    });

    it('should remove duplicates and sort permissions', () => {
      const roles = ['hdcnLeden', 'Events_Read'];
      const permissions = getCombinedPermissions(roles);
      
      // Should be sorted
      const sortedPermissions = [...permissions].sort();
      expect(permissions).toEqual(sortedPermissions);
      
      // Should not have duplicates
      const uniquePermissions = [...new Set(permissions)];
      expect(permissions).toEqual(uniquePermissions);
    });

    it('should return empty array for empty roles', () => {
      expect(getCombinedPermissions([])).toEqual([]);
      expect(getCombinedPermissions(null as any)).toEqual([]);
    });
  });

  describe('hasPermission', () => {
    it('should return true when user has the permission', () => {
      const roles = ['hdcnLeden'];
      expect(hasPermission(roles, 'members:read_own')).toBe(true);
      expect(hasPermission(roles, 'webshop:access')).toBe(true);
    });

    it('should return false when user does not have the permission', () => {
      const roles = ['hdcnLeden'];
      expect(hasPermission(roles, 'members:read_all')).toBe(false);
      expect(hasPermission(roles, 'system:user_management')).toBe(false);
    });
  });

  describe('getAccessLevelSummary', () => {
    it('should return system level for system admin roles', () => {
      const summary = getAccessLevelSummary(['System_CRUD']);
      expect(summary.level).toBe('system');
      expect(summary.description).toContain('Systeembeheerder');
    });

    it('should return administrative level for admin roles', () => {
      const summary = getAccessLevelSummary(['Members_CRUD']);
      expect(summary.level).toBe('administrative');
      expect(summary.description).toContain('Beheerder');
    });

    it('should return functional level for functional roles', () => {
      const summary = getAccessLevelSummary(['Members_Read']);
      expect(summary.level).toBe('functional');
      expect(summary.description).toContain('Functionaris');
    });

    it('should return basic level for basic member', () => {
      const summary = getAccessLevelSummary(['hdcnLeden']);
      expect(summary.level).toBe('basic');
      expect(summary.description).toContain('Basis lid');
    });

    it('should return basic level for no roles', () => {
      const summary = getAccessLevelSummary([]);
      expect(summary.level).toBe('basic');
      expect(summary.description).toContain('Geen toegang');
    });
  });

  describe('isAdministrator', () => {
    it('should return true for system admin roles', () => {
      expect(isAdministrator(['System_CRUD'])).toBe(true);
    });

    it('should return true for administrative roles', () => {
      expect(isAdministrator(['Members_CRUD'])).toBe(true);
      expect(isAdministrator(['National_Chairman'])).toBe(true);
    });

    it('should return false for basic roles', () => {
      expect(isAdministrator(['hdcnLeden'])).toBe(false);
      expect(isAdministrator(['Members_Read'])).toBe(false);
    });

    it('should return false for no roles', () => {
      expect(isAdministrator([])).toBe(false);
    });
  });

  describe('groupPermissionsByCategory', () => {
    it('should group permissions by category correctly', () => {
      const permissions = [
        'members:read_own',
        'members:update_own_personal',
        'events:read_public',
        'products:browse_catalog',
        'system:user_management'
      ];
      
      const grouped = groupPermissionsByCategory(permissions);
      
      expect(grouped['Ledenadministratie']).toContain('members:read_own');
      expect(grouped['Ledenadministratie']).toContain('members:update_own_personal');
      expect(grouped['Evenementen']).toContain('events:read_public');
      expect(grouped['Producten']).toContain('products:browse_catalog');
      expect(grouped['Systeembeheer']).toContain('system:user_management');
    });
  });

  describe('getPermissionDescription', () => {
    it('should return Dutch description for known permissions', () => {
      expect(getPermissionDescription('members:read_own')).toBe('Eigen gegevens bekijken');
      expect(getPermissionDescription('webshop:access')).toBe('Webshop toegang');
    });

    it('should return the permission itself for unknown permissions', () => {
      expect(getPermissionDescription('unknown:permission')).toBe('unknown:permission');
    });
  });
});