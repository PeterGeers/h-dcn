/**
 * Regional Filtering Integration Tests
 * 
 * Tests the complete regional filtering functionality across the UI,
 * including permission checks, data filtering, and component behavior.
 */

import {
  userHasPermissionWithRegion,
  getUserAccessibleRegions,
  checkUIPermission,
  validatePermissionWithRegion
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

// Mock member data from different regions
const mockMembers: Member[] = [
  {
    id: '1',
    voornaam: 'Jan',
    achternaam: 'Jansen',
    email: 'jan@example.com',
    regio: 'Utrecht',
    status: 'Actief'
  },
  {
    id: '2', 
    voornaam: 'Piet',
    achternaam: 'Pietersen',
    email: 'piet@example.com',
    regio: 'Limburg',
    status: 'Actief'
  },
  {
    id: '3',
    voornaam: 'Klaas',
    achternaam: 'Klaassen', 
    email: 'klaas@example.com',
    regio: 'Noord-Holland',
    status: 'Actief'
  },
  {
    id: '4',
    voornaam: 'Marie',
    achternaam: 'Mariesen',
    email: 'marie@example.com',
    regio: 'Zuid-Holland',
    status: 'Actief'
  },
  {
    id: '5',
    voornaam: 'Henk',
    achternaam: 'Hendriks',
    email: 'henk@example.com',
    regio: 'Groningen/Drenthe',
    status: 'Actief'
  },
  {
    id: '6',
    voornaam: 'Anna',
    achternaam: 'Annesen',
    email: 'anna@example.com',
    regio: undefined, // Member without region assignment
    status: 'Actief'
  }
] as Member[];

// ============================================================================
// REGIONAL ACCESS PERMISSION TESTS
// ============================================================================

describe('Regional Filtering Integration Tests', () => {
  describe('Regional Access Permissions', () => {
    test('national admin should have access to all regions', () => {
      const user = testUsers.nationalAdmin;
      
      // Should have access to any specific region
      expect(userHasPermissionWithRegion(user, 'members_read', 'utrecht')).toBe(true);
      expect(userHasPermissionWithRegion(user, 'members_read', 'limburg')).toBe(true);
      expect(userHasPermissionWithRegion(user, 'members_crud', 'noord_holland')).toBe(true);
      
      // Should have access without specifying region
      expect(userHasPermissionWithRegion(user, 'members_read')).toBe(true);
      expect(userHasPermissionWithRegion(user, 'members_crud')).toBe(true);
      
      // Should return 'all' for accessible regions
      expect(getUserAccessibleRegions(user)).toEqual(['all']);
    });

    test('regional coordinator should have access only to assigned region', () => {
      const user = testUsers.utrechtCoordinator;
      
      // Should have access to assigned region
      expect(userHasPermissionWithRegion(user, 'members_read', 'utrecht')).toBe(true);
      expect(userHasPermissionWithRegion(user, 'members_crud', 'utrecht')).toBe(true);
      
      // Should NOT have access to other regions
      expect(userHasPermissionWithRegion(user, 'members_read', 'limburg')).toBe(false);
      expect(userHasPermissionWithRegion(user, 'members_crud', 'limburg')).toBe(false);
      expect(userHasPermissionWithRegion(user, 'members_read', 'noord_holland')).toBe(false);
      
      // Should have access without specifying region (general permission check)
      expect(userHasPermissionWithRegion(user, 'members_read')).toBe(true);
      
      // Should return specific region
      expect(getUserAccessibleRegions(user)).toEqual(['utrecht']);
    });

    test('regional viewer should have read-only access to assigned region', () => {
      const user = testUsers.limburgViewer;
      
      // Should have read access to assigned region
      expect(userHasPermissionWithRegion(user, 'members_read', 'limburg')).toBe(true);
      
      // Should NOT have write access
      expect(userHasPermissionWithRegion(user, 'members_crud', 'limburg')).toBe(false);
      
      // Should NOT have access to other regions
      expect(userHasPermissionWithRegion(user, 'members_read', 'utrecht')).toBe(false);
      expect(userHasPermissionWithRegion(user, 'members_read', 'noord_holland')).toBe(false);
      
      // Should return specific region
      expect(getUserAccessibleRegions(user)).toEqual(['limburg']);
    });

    test('multi-regional user should have access to multiple assigned regions', () => {
      const user = testUsers.multiRegionalUser;
      
      // Should have access to both assigned regions
      expect(userHasPermissionWithRegion(user, 'members_read', 'noord_holland')).toBe(true);
      expect(userHasPermissionWithRegion(user, 'members_crud', 'noord_holland')).toBe(true);
      expect(userHasPermissionWithRegion(user, 'members_read', 'zuid_holland')).toBe(true);
      expect(userHasPermissionWithRegion(user, 'members_crud', 'zuid_holland')).toBe(true);
      
      // Should NOT have access to unassigned regions
      expect(userHasPermissionWithRegion(user, 'members_read', 'utrecht')).toBe(false);
      expect(userHasPermissionWithRegion(user, 'members_read', 'limburg')).toBe(false);
      
      // Should return both regions
      const accessibleRegions = getUserAccessibleRegions(user);
      expect(accessibleRegions).toContain('noord_holland');
      expect(accessibleRegions).toContain('zuid_holland');
      expect(accessibleRegions).toHaveLength(2);
    });

    test('incomplete user should be denied access due to missing regional role', () => {
      const user = testUsers.incompleteUser;
      
      // Should be denied access to any region despite having Members_CRUD
      expect(userHasPermissionWithRegion(user, 'members_read', 'utrecht')).toBe(false);
      expect(userHasPermissionWithRegion(user, 'members_crud', 'utrecht')).toBe(false);
      expect(userHasPermissionWithRegion(user, 'members_read', 'limburg')).toBe(false);
      
      // Should be denied general access due to missing regional role
      expect(userHasPermissionWithRegion(user, 'members_read')).toBe(false);
      
      // Should return empty regions array
      expect(getUserAccessibleRegions(user)).toEqual([]);
    });

    test('regular member should not have admin access regardless of region', () => {
      const user = testUsers.regularMember;
      
      // Should not have member management access
      expect(userHasPermissionWithRegion(user, 'members_read', 'utrecht')).toBe(false);
      expect(userHasPermissionWithRegion(user, 'members_crud', 'utrecht')).toBe(false);
      
      // Should return regional access but not for admin functions
      // Regular members have regional roles but no admin permissions
      expect(getUserAccessibleRegions(user)).toEqual(['utrecht']);
    });
  });

  // ============================================================================
  // UI PERMISSION INTEGRATION TESTS
  // ============================================================================

  describe('UI Permission Integration', () => {
    test('checkUIPermission should work correctly with regional access', () => {
      // National admin should have full UI access
      expect(checkUIPermission(testUsers.nationalAdmin, 'members', 'read')).toBe(true);
      expect(checkUIPermission(testUsers.nationalAdmin, 'members', 'write')).toBe(true);
      expect(checkUIPermission(testUsers.nationalAdmin, 'members', 'read', 'utrecht')).toBe(true);
      expect(checkUIPermission(testUsers.nationalAdmin, 'members', 'write', 'limburg')).toBe(true);
      
      // Regional coordinator should have regional UI access
      expect(checkUIPermission(testUsers.utrechtCoordinator, 'members', 'read', 'utrecht')).toBe(true);
      expect(checkUIPermission(testUsers.utrechtCoordinator, 'members', 'write', 'utrecht')).toBe(true);
      expect(checkUIPermission(testUsers.utrechtCoordinator, 'members', 'read', 'limburg')).toBe(false);
      expect(checkUIPermission(testUsers.utrechtCoordinator, 'members', 'write', 'limburg')).toBe(false);
      
      // Regional viewer should have read-only UI access
      expect(checkUIPermission(testUsers.limburgViewer, 'members', 'read', 'limburg')).toBe(true);
      expect(checkUIPermission(testUsers.limburgViewer, 'members', 'write', 'limburg')).toBe(false);
      expect(checkUIPermission(testUsers.limburgViewer, 'members', 'read', 'utrecht')).toBe(false);
      
      // Incomplete user should be denied UI access
      expect(checkUIPermission(testUsers.incompleteUser, 'members', 'read')).toBe(false);
      expect(checkUIPermission(testUsers.incompleteUser, 'members', 'write')).toBe(false);
      
      // Regular member should not have admin UI access
      expect(checkUIPermission(testUsers.regularMember, 'members', 'read')).toBe(false);
      expect(checkUIPermission(testUsers.regularMember, 'members', 'write')).toBe(false);
    });

    test('validatePermissionWithRegion should handle multiple permissions correctly', () => {
      // National admin should pass multiple permission validation
      expect(validatePermissionWithRegion(
        testUsers.nationalAdmin,
        ['members_read', 'members_crud'],
        'utrecht'
      )).toBe(true);
      
      // Regional coordinator should pass for assigned region
      expect(validatePermissionWithRegion(
        testUsers.utrechtCoordinator,
        ['members_read', 'members_crud'],
        'utrecht'
      )).toBe(true);
      
      // Regional coordinator should fail for unassigned region
      expect(validatePermissionWithRegion(
        testUsers.utrechtCoordinator,
        ['members_read', 'members_crud'],
        'limburg'
      )).toBe(false);
      
      // Regional viewer should fail CRUD validation (lacks write permission)
      expect(validatePermissionWithRegion(
        testUsers.limburgViewer,
        ['members_read', 'members_crud'],
        'limburg'
      )).toBe(false);
      
      // Regional viewer should pass read-only validation
      expect(validatePermissionWithRegion(
        testUsers.limburgViewer,
        ['members_read'],
        'limburg'
      )).toBe(true);
    });
  });

  // ============================================================================
  // DATA FILTERING SIMULATION TESTS
  // ============================================================================

  describe('Data Filtering Simulation', () => {
    /**
     * Simulates the regional filtering logic that would be applied to member data
     * This tests the filtering logic without requiring the full ParquetDataService
     */
    function simulateRegionalFiltering(members: Member[], user: typeof testUsers.nationalAdmin): Member[] {
      const userRoles = user.groups || [];
      
      // Check for full access roles
      const hasFullAccess = userRoles.some(role => 
        ['Members_CRUD', 'System_CRUD', 'System_User_Management'].includes(role)
      );
      const hasRegioAll = userRoles.includes('Regio_All');
      
      if (hasFullAccess && hasRegioAll) {
        return members; // No filtering for full access users
      }
      
      // Extract regional roles
      const regionalRoles = userRoles.filter(role => role.startsWith('Regio_') && role !== 'Regio_All');
      
      if (regionalRoles.length === 0) {
        // No regional access
        return [];
      }
      
      // Map roles to region names
      const allowedRegions = regionalRoles.map(role => role.replace('Regio_', ''));
      
      // Filter members by region
      return members.filter(member => {
        const memberRegion = member.regio;
        if (!memberRegion) {
          // Members without region - only include for full access users with Regio_All
          return hasFullAccess && hasRegioAll;
        }
        return allowedRegions.includes(memberRegion);
      });
    }

    test('national admin should see all members', () => {
      const filteredMembers = simulateRegionalFiltering(mockMembers, testUsers.nationalAdmin);
      
      expect(filteredMembers).toHaveLength(mockMembers.length);
      expect(filteredMembers).toEqual(mockMembers);
    });

    test('regional coordinator should see only assigned region members', () => {
      const filteredMembers = simulateRegionalFiltering(mockMembers, testUsers.utrechtCoordinator);
      
      // Should only see Utrecht members
      expect(filteredMembers).toHaveLength(1);
      expect(filteredMembers[0].regio).toBe('Utrecht');
      expect(filteredMembers[0].voornaam).toBe('Jan');
    });

    test('regional viewer should see only assigned region members', () => {
      const filteredMembers = simulateRegionalFiltering(mockMembers, testUsers.limburgViewer);
      
      // Should only see Limburg members
      expect(filteredMembers).toHaveLength(1);
      expect(filteredMembers[0].regio).toBe('Limburg');
      expect(filteredMembers[0].voornaam).toBe('Piet');
    });

    test('multi-regional user should see members from both assigned regions', () => {
      const filteredMembers = simulateRegionalFiltering(mockMembers, testUsers.multiRegionalUser);
      
      // Should see Noord-Holland and Zuid-Holland members
      expect(filteredMembers).toHaveLength(2);
      
      const regions = filteredMembers.map(m => m.regio);
      expect(regions).toContain('Noord-Holland');
      expect(regions).toContain('Zuid-Holland');
      
      const names = filteredMembers.map(m => m.voornaam);
      expect(names).toContain('Klaas'); // Noord-Holland
      expect(names).toContain('Marie'); // Zuid-Holland
    });

    test('incomplete user should see no members', () => {
      const filteredMembers = simulateRegionalFiltering(mockMembers, testUsers.incompleteUser);
      
      expect(filteredMembers).toHaveLength(0);
    });

    test('regular member should see no members (no admin access)', () => {
      const filteredMembers = simulateRegionalFiltering(mockMembers, testUsers.regularMember);
      
      expect(filteredMembers).toHaveLength(0);
    });

    test('members without region assignment should only be visible to full access users', () => {
      const memberWithoutRegion = mockMembers.find(m => !m.regio);
      expect(memberWithoutRegion).toBeDefined();
      
      // National admin should see member without region
      const nationalFiltered = simulateRegionalFiltering(mockMembers, testUsers.nationalAdmin);
      expect(nationalFiltered.some(m => !m.regio)).toBe(true);
      
      // Regional users should NOT see member without region
      const utrechtFiltered = simulateRegionalFiltering(mockMembers, testUsers.utrechtCoordinator);
      expect(utrechtFiltered.some(m => !m.regio)).toBe(false);
      
      const limburgFiltered = simulateRegionalFiltering(mockMembers, testUsers.limburgViewer);
      expect(limburgFiltered.some(m => !m.regio)).toBe(false);
    });
  });

  // ============================================================================
  // EDGE CASES AND ERROR SCENARIOS
  // ============================================================================

  describe('Edge Cases and Error Scenarios', () => {
    test('should handle null/undefined users gracefully', () => {
      expect(userHasPermissionWithRegion(null, 'members_read', 'utrecht')).toBe(false);
      expect(getUserAccessibleRegions(null)).toEqual([]);
      expect(checkUIPermission(null, 'members', 'read')).toBe(false);
      expect(validatePermissionWithRegion(null, ['members_read'], 'utrecht')).toBe(false);
    });

    test('should handle users with empty groups array', () => {
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

    test('should handle invalid region names gracefully', () => {
      const user = testUsers.utrechtCoordinator;
      
      // Should deny access to non-existent regions
      expect(userHasPermissionWithRegion(user, 'members_read', 'invalid_region')).toBe(false);
      expect(checkUIPermission(user, 'members', 'read', 'nonexistent')).toBe(false);
      
      // Empty string should be treated as no specific region (should pass)
      expect(userHasPermissionWithRegion(user, 'members_read', '')).toBe(true);
    });

    test('should handle invalid permission types gracefully', () => {
      const user = testUsers.nationalAdmin;
      
      // Should deny access for invalid permission types
      expect(userHasPermissionWithRegion(user, 'invalid_permission', 'utrecht')).toBe(false);
      expect(userHasPermissionWithRegion(user, '', 'utrecht')).toBe(false);
    });

    test('should handle case sensitivity in region names', () => {
      const user = testUsers.utrechtCoordinator;
      
      // Should be case sensitive (current implementation)
      expect(userHasPermissionWithRegion(user, 'members_read', 'Utrecht')).toBe(false); // Capital U
      expect(userHasPermissionWithRegion(user, 'members_read', 'UTRECHT')).toBe(false); // All caps
      expect(userHasPermissionWithRegion(user, 'members_read', 'utrecht')).toBe(true); // Lowercase
    });
  });

  // ============================================================================
  // SECURITY VALIDATION TESTS
  // ============================================================================

  describe('Security Validation', () => {
    test('should prevent privilege escalation through role manipulation', () => {
      // User should not be able to gain access by having partial roles
      const partialUser = {
        id: 'partial',
        username: 'partial',
        email: 'partial@hdcn.nl',
        groups: ['Regio_Utrecht'] as HDCNGroup[], // Regional role without permission role
        attributes: {}
      };
      
      expect(userHasPermissionWithRegion(partialUser, 'members_read', 'utrecht')).toBe(false);
      expect(checkUIPermission(partialUser, 'members', 'read', 'utrecht')).toBe(false);
    });

    test('should enforce strict regional boundaries', () => {
      const user = testUsers.utrechtCoordinator;
      
      // Should not be able to access any other region
      const otherRegions = ['limburg', 'noord_holland', 'zuid_holland', 'groningen_drenthe', 'brabant_zeeland', 'friesland', 'duitsland', 'oost'];
      
      otherRegions.forEach(region => {
        expect(userHasPermissionWithRegion(user, 'members_read', region)).toBe(false);
        expect(userHasPermissionWithRegion(user, 'members_crud', region)).toBe(false);
        expect(checkUIPermission(user, 'members', 'read', region)).toBe(false);
        expect(checkUIPermission(user, 'members', 'write', region)).toBe(false);
      });
    });

    test('should require both permission and regional roles for access', () => {
      // Test that having only one type of role is insufficient
      const onlyPermission = {
        id: 'only_perm',
        username: 'only_perm',
        email: 'only_perm@hdcn.nl',
        groups: ['Members_CRUD'] as HDCNGroup[], // Permission without region
        attributes: {}
      };
      
      const onlyRegion = {
        id: 'only_region',
        username: 'only_region', 
        email: 'only_region@hdcn.nl',
        groups: ['Regio_Utrecht'] as HDCNGroup[], // Region without permission
        attributes: {}
      };
      
      // Both should be denied access
      expect(userHasPermissionWithRegion(onlyPermission, 'members_read', 'utrecht')).toBe(false);
      expect(userHasPermissionWithRegion(onlyRegion, 'members_read', 'utrecht')).toBe(false);
      expect(checkUIPermission(onlyPermission, 'members', 'read')).toBe(false);
      expect(checkUIPermission(onlyRegion, 'members', 'read')).toBe(false);
    });

    test('should properly validate Regio_All special permissions', () => {
      const regioAllUser = {
        id: 'regio_all',
        username: 'regio_all',
        email: 'regio_all@hdcn.nl',
        groups: ['Members_Read', 'Regio_All'] as HDCNGroup[],
        attributes: {}
      };
      
      // Should have access to all regions
      expect(userHasPermissionWithRegion(regioAllUser, 'members_read', 'utrecht')).toBe(true);
      expect(userHasPermissionWithRegion(regioAllUser, 'members_read', 'limburg')).toBe(true);
      expect(userHasPermissionWithRegion(regioAllUser, 'members_read', 'noord_holland')).toBe(true);
      expect(getUserAccessibleRegions(regioAllUser)).toEqual(['all']);
      
      // But should still respect permission boundaries (no CRUD with only Read role)
      expect(userHasPermissionWithRegion(regioAllUser, 'members_crud', 'utrecht')).toBe(false);
    });
  });
});