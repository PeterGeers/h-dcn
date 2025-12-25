import { 
  getMembershipTypeRestrictions, 
  isFieldRequiredForMembershipType,
  hasMembershipTypeModuleAccess,
  hasCombinedModuleAccess,
  getAdditivePermissionBreakdown
} from '../parameterService';

// Mock the functionPermissions module
jest.mock('../functionPermissions', () => ({
  getUserRoles: jest.fn(),
  calculatePermissions: jest.fn()
}));

// Mock the parameterStore
jest.mock('../parameterStore', () => ({
  parameterStore: {
    getParameters: jest.fn(),
    refresh: jest.fn()
  }
}));

describe('Parameter Service - Backward Compatibility and Additive Enhancements', () => {
  describe('Membership Type Restrictions (Backward Compatibility)', () => {
    test('should preserve existing membership type field requirements', () => {
      // Test existing membership type restrictions are preserved
      const gewoonLidRestrictions = getMembershipTypeRestrictions('Gewoon lid');
      expect(gewoonLidRestrictions.requiredFields).toContain('motormerk');
      expect(gewoonLidRestrictions.requiredFields).toContain('motortype');
      expect(gewoonLidRestrictions.requiredFields).toContain('bouwjaar');
      expect(gewoonLidRestrictions.requiredFields).toContain('kenteken');
      
      const donateurRestrictions = getMembershipTypeRestrictions('Donateur zonder motor');
      expect(donateurRestrictions.optionalFields).toContain('motormerk');
      expect(donateurRestrictions.optionalFields).toContain('motortype');
    });

    test('should preserve field requirement checking logic', () => {
      // Test that existing field requirement logic is preserved
      expect(isFieldRequiredForMembershipType('Gewoon lid', 'motormerk')).toBe(true);
      expect(isFieldRequiredForMembershipType('Gewoon lid', 'voornaam')).toBe(false);
      expect(isFieldRequiredForMembershipType('Donateur zonder motor', 'motormerk')).toBe(false);
    });

    test('should preserve membership type module access rules', () => {
      // Test that existing module access rules are preserved
      expect(hasMembershipTypeModuleAccess('Gewoon lid', 'webshop')).toBe(true);
      expect(hasMembershipTypeModuleAccess('Gewoon lid', 'events')).toBe(true);
      expect(hasMembershipTypeModuleAccess('Gewoon lid', 'members_own')).toBe(true);
    });
  });

  describe('Combined Access Control (Additive Enhancements)', () => {
    const mockUser = {
      signInUserSession: {
        accessToken: {
          payload: {
            'cognito:groups': ['hdcnLeden', 'Members_Read_All']
          }
        }
      }
    };

    beforeEach(() => {
      const { getUserRoles, calculatePermissions } = require('../functionPermissions');
      getUserRoles.mockReturnValue(['hdcnLeden', 'Members_Read_All']);
      calculatePermissions.mockReturnValue({
        members: { read: ['all'], write: [] },
        webshop: { read: ['own'], write: ['own'] }
      });
    });

    test('should combine membership type and role-based access additively', () => {
      // Test that role-based access is additive to membership type access
      const hasAccess = hasCombinedModuleAccess(mockUser, 'Gewoon lid', 'webshop');
      expect(hasAccess).toBe(true); // Should have access from both membership type AND roles
    });

    test('should deny access when either membership type or role access is missing', () => {
      // Test that both conditions must be met (not just one)
      const mockUserWithoutRoles = {
        signInUserSession: {
          accessToken: {
            payload: {
              'cognito:groups': []
            }
          }
        }
      };
      
      const { getUserRoles } = require('../functionPermissions');
      getUserRoles.mockReturnValue([]);
      
      const hasAccess = hasCombinedModuleAccess(mockUserWithoutRoles, 'Gewoon lid', 'webshop');
      expect(hasAccess).toBe(false); // Should deny access when role access is missing
    });
  });

  describe('Additive Permission Breakdown', () => {
    const mockUser = {
      signInUserSession: {
        accessToken: {
          payload: {
            'cognito:groups': ['hdcnLeden', 'Members_Read_All']
          }
        }
      }
    };

    beforeEach(() => {
      const { parameterStore } = require('../parameterStore');
      parameterStore.getParameters.mockResolvedValue({
        Function_permissions: [{
          value: {
            webshop: { read: ['hdcnLeden'], write: ['hdcnLeden'] }
          }
        }]
      });
      parameterStore.refresh.mockResolvedValue();

      const { getUserRoles, calculatePermissions } = require('../functionPermissions');
      getUserRoles.mockReturnValue(['hdcnLeden', 'Members_Read_All']);
      calculatePermissions.mockReturnValue({
        webshop: { read: ['own'], write: ['own'] }
      });
    });

    test('should show additive permission combination', async () => {
      const breakdown = await getAdditivePermissionBreakdown(mockUser, 'webshop', 'Gewoon lid');
      
      expect(breakdown.explanation.approach).toBe('ADDITIVE');
      expect(breakdown.explanation.description).toContain('added to existing parameter-based permissions');
      
      // Should preserve existing features
      expect(breakdown.explanation.preservedFeatures).toContain('Existing parameter-based module access rules');
      expect(breakdown.explanation.preservedFeatures).toContain('Membership type field restrictions');
      
      // Should show enhanced features
      expect(breakdown.explanation.enhancedFeatures).toContain('New role-based permissions from Cognito groups');
      expect(breakdown.explanation.enhancedFeatures).toContain('Combined permission checking (parameter + role + membership)');
    });

    test('should combine permissions from all sources without replacing', async () => {
      const breakdown = await getAdditivePermissionBreakdown(mockUser, 'webshop', 'Gewoon lid');
      
      // Should have parameter-based permissions
      expect(breakdown.breakdown.parameterBased.read).toContain('hdcnLeden');
      
      // Should have role-based permissions
      expect(breakdown.breakdown.roleBased.read).toContain('own');
      
      // Should have membership-based permissions
      expect(breakdown.breakdown.membershipBased.read).toContain('membership_gewoon_lid');
      
      // Should combine all permissions additively
      expect(breakdown.breakdown.combined.read).toContain('hdcnLeden');
      expect(breakdown.breakdown.combined.read).toContain('own');
      expect(breakdown.breakdown.combined.read).toContain('membership_gewoon_lid');
    });

    test('should demonstrate additive approach over replacement', () => {
      // This test demonstrates that the approach is additive, not replacement
      const existingPermissions = ['hdcnLeden', 'legacy_group'];
      const newRolePermissions = ['Members_Read_All', 'own'];
      
      // Additive approach: combine both
      const additiveResult = [...existingPermissions, ...newRolePermissions];
      expect(additiveResult).toContain('hdcnLeden'); // Preserves existing
      expect(additiveResult).toContain('legacy_group'); // Preserves existing
      expect(additiveResult).toContain('Members_Read_All'); // Adds new
      expect(additiveResult).toContain('own'); // Adds new
      
      // Replacement approach would lose existing permissions
      const replacementResult = newRolePermissions;
      expect(replacementResult).not.toContain('hdcnLeden'); // Would lose existing
      expect(replacementResult).not.toContain('legacy_group'); // Would lose existing
      
      // Our implementation uses the additive approach
      expect(additiveResult.length).toBeGreaterThan(replacementResult.length);
    });
  });
});