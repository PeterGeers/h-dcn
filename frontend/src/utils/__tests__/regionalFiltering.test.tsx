/**
 * Regional Filtering System Tests
 * 
 * Tests the complete regional filtering functionality including
 * permission validation, region mapping, and data filtering logic.
 */

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
import { Member } from '../../types/index';

// ============================================================================
// TEST DATA SETUP
// ============================================================================

// Mock users with different regional access levels
const testUsers = {
  // National administrator with full access
  nationalAdmin: {
    id: 'national_admin',
    username: 'national_admin',
    email: 'national@hdcn.nl',
    groups: ['Members_CRUD', 'Regio_All'] as HDCNGroup[],
    attributes: {}
  },

  // Regional coordinator for Utrecht
  utrechtCoordinator: {
    id: 'utrecht_coord',
    username: 'utrecht_coord', 
    email: 'utrecht@hdcn.nl',
    groups: ['Members_CRUD', 'Regio_Utrecht'] as HDCNGroup[],
    attributes: {}
  },

  // Regional viewer for Limburg (read-only)
  limburgViewer: {
    id: 'limburg_viewer',
    username: 'limburg_viewer',
    email: 'limburg@hdcn.nl', 
    groups: ['Members_Read', 'Regio_Limburg'] as HDCNGroup[],
    attributes: {}
  },

  // Multi-regional user (Noord-Holland + Zuid-Holland)
  multiRegionalUser: {
    id: 'multi_regional',
    username: 'multi_regional',
    email: 'multi@hdcn.nl',
    groups: ['Members_CRUD', 'Regio_Noord-Holland', 'Regio_Zuid-Holland'] as HDCNGroup[],
    attributes: {}
  },

  // User with permission but no regional access (incomplete role)
  incompleteUser: {
    id: 'incomplete',
    username: 'incomplete',
    email: 'incomplete@hdcn.nl',
    groups: ['Members_CRUD'] as HDCNGroup[], // Missing regional role
    attributes: {}
  },

  // Regular member with no admin access
  regularMember: {
    id: 'regular',
    username: 'regular',
    email: 'regular@hdcn.nl',
    groups: ['hdcnLeden', 'Regio_Utrecht'] as HDCNGroup[],
    attributes: {}
  }
};

// Region mapping constants for testing
const REGION_ID_TO_NAME_MAP: { [key: string]: string } = {
  'utrecht': 'Regio_Utrecht',
  'limburg': 'Regio_Limburg',
  'groningen_drenthe': 'Regio_Groningen/Drenthe',
  'zuid_holland': 'Regio_Zuid-Holland',
  'noord_holland': 'Regio_Noord-Holland',
  'oost': 'Regio_Oost',
  'brabant_zeeland': 'Regio_Brabant/Zeeland',
  'friesland': 'Regio_Friesland',
  'duitsland': 'Regio_Duitsland'
};

const REGION_NAME_TO_ID_MAP: { [key: string]: string } = {
  'Regio_Utrecht': 'utrecht',
  'Regio_Limburg': 'limburg',
  'Regio_Groningen/Drenthe': 'groningen_drenthe',
  'Regio_Zuid-Holland': 'zuid_holland',
  'Regio_Noord-Holland': 'noord_holland',
  'Regio_Oost': 'oost',
  'Regio_Brabant/Zeeland': 'brabant_zeeland',
  'Regio_Friesland': 'friesland',
  'Regio_Duitsland': 'duitsland'
};

// Helper functions for regional access validation
function validateRegionalAccess(userRoles: string[], targetRegion?: string): boolean {
  // Check for full access
  if (userRoles.includes('Regio_All')) {
    return true;
  }
  
  // Check for specific regional access
  if (targetRegion) {
    const requiredRole = REGION_ID_TO_NAME_MAP[targetRegion];
    return userRoles.includes(requiredRole);
  }
  
  // Check for any regional access
  return userRoles.some(role => role.startsWith('Regio_'));
}

function getAllowedRegions(userRoles: string[]): string[] {
  if (userRoles.includes('Regio_All')) {
    return ['all'];
  }
  
  const regionalRoles = userRoles.filter(role => role.startsWith('Regio_') && role !== 'Regio_All');
  return regionalRoles.map(role => REGION_NAME_TO_ID_MAP[role]).filter(Boolean);
}

// ============================================================================
// TESTS
// ============================================================================

describe('Regional Filtering System', () => {
  describe('Regional Mapping Functions', () => {
    test('should correctly map region IDs to names', () => {
      expect(REGION_ID_TO_NAME_MAP['utrecht']).toBe('Regio_Utrecht');
      expect(REGION_ID_TO_NAME_MAP['limburg']).toBe('Regio_Limburg');
      expect(REGION_ID_TO_NAME_MAP['groningen_drenthe']).toBe('Regio_Groningen/Drenthe');
      expect(REGION_ID_TO_NAME_MAP['zuid_holland']).toBe('Regio_Zuid-Holland');
    });

    test('should correctly map region names to IDs', () => {
      expect(REGION_NAME_TO_ID_MAP['Regio_Utrecht']).toBe('utrecht');
      expect(REGION_NAME_TO_ID_MAP['Regio_Limburg']).toBe('limburg');
      expect(REGION_NAME_TO_ID_MAP['Regio_Groningen/Drenthe']).toBe('groningen_drenthe');
      expect(REGION_NAME_TO_ID_MAP['Regio_Zuid-Holland']).toBe('zuid_holland');
    });

    test('should validate regional access for new roles', () => {
      const newRoles = ['Members_CRUD', 'Regio_Utrecht'];
      expect(validateRegionalAccess(newRoles, 'utrecht')).toBe(true);
      expect(validateRegionalAccess(newRoles, 'limburg')).toBe(false);
    });

    test('should get allowed regions for users with full access', () => {
      const fullAccessRoles = ['Members_CRUD', 'Regio_All'];
      expect(getAllowedRegions(fullAccessRoles)).toEqual(['all']);
    });

    test('should get allowed regions for regional users', () => {
      const regionalRoles = ['Members_CRUD', 'Regio_Utrecht', 'Regio_Limburg'];
      const allowedRegions = getAllowedRegions(regionalRoles);
      expect(allowedRegions).toContain('utrecht');
      expect(allowedRegions).toContain('limburg');
      expect(allowedRegions).toHaveLength(2);
    });
  });

  describe('User Role Functions', () => {
    test('should extract roles from user groups array', () => {
      const roles = getUserRoles(testUsers.nationalAdmin);
      expect(roles).toEqual(['Members_CRUD', 'Regio_All']);
    });

    test('should check if user has specific role', () => {
      expect(userHasRole(testUsers.utrechtCoordinator, 'Members_CRUD')).toBe(true);
      expect(userHasRole(testUsers.utrechtCoordinator, 'Regio_Utrecht')).toBe(true);
      expect(userHasRole(testUsers.utrechtCoordinator, 'Members_Read')).toBe(false);
    });

    test('should check if user has any of specified roles', () => {
      expect(userHasAnyRole(testUsers.limburgViewer, ['Members_Read', 'Members_CRUD'])).toBe(true);
      expect(userHasAnyRole(testUsers.limburgViewer, ['Events_CRUD', 'Products_CRUD'])).toBe(false);
    });

    test('should check if user has all specified roles', () => {
      expect(userHasAllRoles(testUsers.utrechtCoordinator, ['Members_CRUD', 'Regio_Utrecht'])).toBe(true);
      expect(userHasAllRoles(testUsers.utrechtCoordinator, ['Members_CRUD', 'Regio_Limburg'])).toBe(false);
    });
  });

  describe('Permission Type Checking', () => {
    test('should validate read permissions', () => {
      expect(userHasPermissionType(testUsers.limburgViewer, 'members', 'read')).toBe(true);
      expect(userHasPermissionType(testUsers.utrechtCoordinator, 'members', 'read')).toBe(true);
    });

    test('should validate CRUD permissions', () => {
      expect(userHasPermissionType(testUsers.utrechtCoordinator, 'members', 'crud')).toBe(true);
      expect(userHasPermissionType(testUsers.limburgViewer, 'members', 'crud')).toBe(false);
    });

    test('should validate export permissions', () => {
      const exportUser = {
        ...testUsers.nationalAdmin,
        groups: ['Members_Export', 'Regio_All'] as HDCNGroup[]
      };
      expect(userHasPermissionType(exportUser, 'members', 'export')).toBe(true);
      expect(userHasPermissionType(testUsers.limburgViewer, 'members', 'export')).toBe(false);
    });
  });

  describe('Regional Permission Validation', () => {
    test('should validate permission with region for national admin', () => {
      const user = testUsers.nationalAdmin;
      expect(userHasPermissionWithRegion(user, 'members_read', 'utrecht')).toBe(true);
      expect(userHasPermissionWithRegion(user, 'members_crud', 'limburg')).toBe(true);
      expect(userHasPermissionWithRegion(user, 'events_crud', 'noord_holland')).toBe(true);
    });

    test('should validate permission with region for regional coordinator', () => {
      const user = testUsers.utrechtCoordinator;
      expect(userHasPermissionWithRegion(user, 'members_read', 'utrecht')).toBe(true);
      expect(userHasPermissionWithRegion(user, 'members_crud', 'utrecht')).toBe(true);
      expect(userHasPermissionWithRegion(user, 'members_read', 'limburg')).toBe(false);
    });

    test('should validate permission with region for multi-region user', () => {
      const user = testUsers.multiRegionalUser;
      expect(userHasPermissionWithRegion(user, 'members_read', 'noord_holland')).toBe(true);
      expect(userHasPermissionWithRegion(user, 'members_crud', 'zuid_holland')).toBe(true);
      expect(userHasPermissionWithRegion(user, 'members_read', 'utrecht')).toBe(false);
    });

    test('should deny access for users without regional permissions', () => {
      const user = testUsers.incompleteUser;
      expect(userHasPermissionWithRegion(user, 'members_read', 'utrecht')).toBe(false);
      expect(userHasPermissionWithRegion(user, 'members_crud', 'limburg')).toBe(false);
    });

    test('should validate multiple permissions with region', () => {
      expect(validatePermissionWithRegion(
        testUsers.nationalAdmin,
        ['members_read', 'members_crud'],
        'utrecht'
      )).toBe(true);
      
      expect(validatePermissionWithRegion(
        testUsers.utrechtCoordinator, 
        ['members_read', 'members_crud'],
        'utrecht'
      )).toBe(true);
      
      expect(validatePermissionWithRegion(
        testUsers.utrechtCoordinator,
        ['members_read', 'members_crud'],
        'limburg'
      )).toBe(false);
      
      expect(validatePermissionWithRegion(
        testUsers.limburgViewer,
        ['members_read', 'members_crud'],
        'limburg'
      )).toBe(false); // Lacks CRUD permission
    });
  });

  describe('User Accessible Regions', () => {
    test('should return all regions for national admin', () => {
      expect(getUserAccessibleRegions(testUsers.nationalAdmin)).toEqual(['all']);
    });

    test('should return specific regions for regional users', () => {
      expect(getUserAccessibleRegions(testUsers.utrechtCoordinator)).toEqual(['utrecht']);
      expect(getUserAccessibleRegions(testUsers.limburgViewer)).toEqual(['limburg']);
    });

    test('should return multiple regions for multi-region users', () => {
      const regions = getUserAccessibleRegions(testUsers.multiRegionalUser);
      expect(regions).toContain('noord_holland');
      expect(regions).toContain('zuid_holland');
      expect(regions).toHaveLength(2);
    });

    test('should return empty array for users without regional access', () => {
      expect(getUserAccessibleRegions(testUsers.incompleteUser)).toEqual([]);
    });

    test('should return empty array for null user', () => {
      expect(getUserAccessibleRegions(null)).toEqual([]);
    });
  });

  describe('UI Permission Checking', () => {
    test('should grant UI access for users with proper permissions and regions', () => {
      expect(checkUIPermission(testUsers.nationalAdmin, 'members', 'read')).toBe(true);
      expect(checkUIPermission(testUsers.nationalAdmin, 'members', 'write')).toBe(true);
      expect(checkUIPermission(testUsers.utrechtCoordinator, 'members', 'read', 'utrecht')).toBe(true);
      expect(checkUIPermission(testUsers.utrechtCoordinator, 'members', 'write', 'utrecht')).toBe(true);
      expect(checkUIPermission(testUsers.limburgViewer, 'members', 'read', 'limburg')).toBe(true);
    });

    test('should deny UI access for users without proper permissions', () => {
      expect(checkUIPermission(testUsers.limburgViewer, 'members', 'write', 'limburg')).toBe(false);
      expect(checkUIPermission(testUsers.regularMember, 'members', 'read')).toBe(false);
      expect(checkUIPermission(testUsers.regularMember, 'members', 'write')).toBe(false);
    });

    test('should deny UI access for users without regional access', () => {
      expect(checkUIPermission(testUsers.utrechtCoordinator, 'members', 'read', 'limburg')).toBe(false);
      expect(checkUIPermission(testUsers.utrechtCoordinator, 'members', 'write', 'limburg')).toBe(false);
      expect(checkUIPermission(testUsers.incompleteUser, 'members', 'read')).toBe(false);
    });

    test('should handle different function types correctly', () => {
      const eventUser = {
        ...testUsers.utrechtCoordinator,
        groups: ['Events_CRUD', 'Regio_Noord-Holland'] as HDCNGroup[]
      };
      expect(checkUIPermission(eventUser, 'events', 'write', 'noord_holland')).toBe(true);
      
      const productUser = {
        ...testUsers.nationalAdmin,
        groups: ['Products_CRUD', 'Regio_All'] as HDCNGroup[]
      };
      expect(checkUIPermission(productUser, 'products', 'write')).toBe(true);
      
      const commUser = {
        ...testUsers.utrechtCoordinator,
        groups: ['Communication_CRUD', 'Regio_Oost'] as HDCNGroup[]
      };
      expect(checkUIPermission(commUser, 'communication', 'write', 'oost')).toBe(true);
    });
  });

  describe('Edge Cases and Error Handling', () => {
    test('should handle users with no groups', () => {
      const emptyUser = {
        id: 'empty',
        username: 'empty',
        email: 'empty@hdcn.nl',
        groups: [] as HDCNGroup[],
        attributes: {}
      };
      
      expect(userHasPermissionWithRegion(emptyUser, 'members_read', 'utrecht')).toBe(false);
      expect(getUserAccessibleRegions(emptyUser)).toEqual([]);
      expect(checkUIPermission(emptyUser, 'members', 'read')).toBe(false);
    });

    test('should handle invalid region names', () => {
      const user = testUsers.utrechtCoordinator;
      expect(userHasPermissionWithRegion(user, 'members_read', 'invalid_region')).toBe(false);
      expect(checkUIPermission(user, 'members', 'read', 'nonexistent')).toBe(false);
    });

    test('should handle empty permission arrays', () => {
      expect(validatePermissionWithRegion(testUsers.nationalAdmin, [], 'utrecht')).toBe(false);
    });

    test('should handle undefined target regions', () => {
      expect(userHasPermissionWithRegion(testUsers.utrechtCoordinator, 'members_read')).toBe(true);
    });
  });

  describe('Regional Mapping Constants', () => {
    test('should have consistent region mappings', () => {
      // Test that all region IDs have corresponding names
      Object.keys(REGION_ID_TO_NAME_MAP).forEach(regionId => {
        const regionName = REGION_ID_TO_NAME_MAP[regionId];
        expect(REGION_NAME_TO_ID_MAP[regionName]).toBe(regionId);
      });
      
      // Test that all region names have corresponding IDs
      Object.keys(REGION_NAME_TO_ID_MAP).forEach(regionName => {
        const regionId = REGION_NAME_TO_ID_MAP[regionName];
        expect(REGION_ID_TO_NAME_MAP[regionId]).toBe(regionName);
      });
    });

    test('should include all expected regions', () => {
      const expectedRegions = [
        'utrecht', 'limburg', 'groningen_drenthe', 'zuid_holland',
        'noord_holland', 'oost', 'brabant_zeeland', 'friesland', 'duitsland'
      ];
      
      expectedRegions.forEach(region => {
        expect(REGION_ID_TO_NAME_MAP[region]).toBeDefined();
        expect(REGION_ID_TO_NAME_MAP[region]).toMatch(/^Regio_/);
      });
    });
  });
});