import { 
  validateParameterBackwardCompatibility,
  assessParameterMigrationNeeds,
  getMembershipTypeRestrictions,
  isFieldRequiredForMembershipType,
  hasMembershipTypeModuleAccess
} from '../parameterService';
import { parameterStore } from '../parameterStore';

// Mock the parameterStore
jest.mock('../parameterStore', () => ({
  parameterStore: {
    getParameters: jest.fn(),
    refresh: jest.fn()
  }
}));

describe('Parameter Backward Compatibility Tests', () => {
  const mockParameterStore = parameterStore as jest.Mocked<typeof parameterStore>;

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Existing Parameter Data Continues to Work', () => {
    test('should validate that existing parameter structure is compatible', async () => {
      // Mock existing parameter data structure
      const existingParameterData = {
        Regio: [
          { id: '1', value: 'Noord-Holland' },
          { id: '2', value: 'Zuid-Holland' }
        ],
        Lidmaatschap: [
          { id: '1', value: 'Gewoon lid' },
          { id: '2', value: 'Gezins lid' },
          { id: '3', value: 'Gezins donateur zonder motor' },
          { id: '4', value: 'Donateur zonder motor' }
        ],
        Motormerk: [
          { id: '1', value: 'Harley-Davidson' },
          { id: '2', value: 'Indian' }
        ],
        Clubblad: [
          { id: '1', value: 'Papier' },
          { id: '2', value: 'Digitaal' }
        ],
        WieWatWaar: [
          { id: '1', value: 'Facebook' },
          { id: '2', value: 'Website H-DCN' }
        ],
        Function_permissions: [{
          id: 'default',
          value: {
            members: { read: ['hdcnAdmins', 'hdcnRegio_*'], write: ['hdcnAdmins'] },
            webshop: { read: ['hdcnLeden', 'hdcnAdmins'], write: ['hdcnLeden'] },
            events: { read: ['hdcnAdmins'], write: ['hdcnAdmins'] }
          }
        }]
      };

      mockParameterStore.getParameters.mockResolvedValue(existingParameterData);

      const validation = await validateParameterBackwardCompatibility();

      expect(validation.isCompatible).toBe(true);
      expect(validation.summary.compatibleCategories).toBeGreaterThan(0);
      expect(validation.summary.errorCategories).toBe(0);
      
      // Should detect legacy group patterns
      const functionPermissionsValidation = validation.validationResults.find(
        result => result.category === 'Function_permissions'
      );
      expect(functionPermissionsValidation?.recommendations).toEqual(
        expect.arrayContaining([
          expect.stringContaining('Legacy group patterns detected')
        ])
      );
    });

    test('should preserve membership type restrictions without migration', () => {
      // Test that existing membership type restrictions work without changes
      const gewoonLidRestrictions = getMembershipTypeRestrictions('Gewoon lid');
      expect(gewoonLidRestrictions.requiredFields).toContain('motormerk');
      expect(gewoonLidRestrictions.requiredFields).toContain('motortype');
      expect(gewoonLidRestrictions.requiredFields).toContain('bouwjaar');
      expect(gewoonLidRestrictions.requiredFields).toContain('kenteken');
      expect(gewoonLidRestrictions.moduleAccess).toContain('webshop');
      expect(gewoonLidRestrictions.moduleAccess).toContain('events');

      const donateurRestrictions = getMembershipTypeRestrictions('Donateur zonder motor');
      expect(donateurRestrictions.optionalFields).toContain('motormerk');
      expect(donateurRestrictions.optionalFields).toContain('motortype');
    });

    test('should preserve field requirement logic without changes', () => {
      // Test that existing field requirement checking continues to work
      expect(isFieldRequiredForMembershipType('Gewoon lid', 'motormerk')).toBe(true);
      expect(isFieldRequiredForMembershipType('Gewoon lid', 'voornaam')).toBe(false);
      expect(isFieldRequiredForMembershipType('Donateur zonder motor', 'motormerk')).toBe(false);
      expect(isFieldRequiredForMembershipType('Gezins lid', 'kenteken')).toBe(true);
    });

    test('should preserve module access rules without changes', () => {
      // Test that existing module access rules continue to work
      expect(hasMembershipTypeModuleAccess('Gewoon lid', 'webshop')).toBe(true);
      expect(hasMembershipTypeModuleAccess('Gewoon lid', 'events')).toBe(true);
      expect(hasMembershipTypeModuleAccess('Gewoon lid', 'members_own')).toBe(true);
      expect(hasMembershipTypeModuleAccess('Donateur zonder motor', 'webshop')).toBe(true);
    });

    test('should handle legacy parameter formats gracefully', async () => {
      // Test with legacy parameter format (missing Function_permissions)
      const legacyParameterData = {
        Regio: [{ id: '1', value: 'Noord-Holland' }],
        Lidmaatschap: [{ id: '1', value: 'Gewoon lid' }],
        Motormerk: [{ id: '1', value: 'Harley-Davidson' }],
        Clubblad: [{ id: '1', value: 'Papier' }]
        // Missing Function_permissions - should be handled gracefully
      };

      mockParameterStore.getParameters.mockResolvedValue(legacyParameterData);

      const validation = await validateParameterBackwardCompatibility();

      // Should identify missing Function_permissions
      expect(validation.validationResults.some(result => 
        result.category === 'MISSING_FUNCTION_PERMISSIONS' &&
        result.issues.some(issue => issue.includes('Function_permissions category is missing'))
      )).toBe(true);
      
      // Should provide recommendations for fixing
      expect(validation.validationResults.some(result => 
        result.recommendations.some(rec => rec.includes('Function_permissions will be auto-created'))
      )).toBe(true);
    });
  });

  describe('No Migration Required', () => {
    test('should assess that no migration is required for standard parameter structure', async () => {
      const standardParameterData = {
        Regio: [
          { id: '1', value: 'Noord-Holland' },
          { id: '2', value: 'Zuid-Holland' }
        ],
        Lidmaatschap: [
          { id: '1', value: 'Gewoon lid' },
          { id: '2', value: 'Gezins lid' },
          { id: '3', value: 'Gezins donateur zonder motor' },
          { id: '4', value: 'Donateur zonder motor' }
        ],
        Motormerk: [
          { id: '1', value: 'Harley-Davidson' }
        ],
        Clubblad: [
          { id: '1', value: 'Papier' }
        ],
        WieWatWaar: [
          { id: '1', value: 'Facebook' }
        ],
        Function_permissions: [{
          id: 'default',
          value: {
            members: { read: ['hdcnAdmins'], write: ['hdcnAdmins'] },
            webshop: { read: ['hdcnLeden'], write: ['hdcnLeden'] }
          }
        }]
      };

      mockParameterStore.getParameters.mockResolvedValue(standardParameterData);

      const assessment = await assessParameterMigrationNeeds();

      expect(assessment.migrationRequired).toBe(false);
      expect(assessment.migrationReasons).toHaveLength(0);
      expect(assessment.preservedFeatures).toContain('All expected parameter categories are present');
      expect(assessment.preservedFeatures).toContain('Membership type data structure is compatible');
      expect(assessment.preservedFeatures).toContain('Function permissions structure is compatible');
      
      expect(assessment.recommendations).toContain(
        'No data migration required - existing configurations are fully compatible'
      );
    });

    test('should identify preserved features in existing configurations', async () => {
      const existingConfigWithLegacyGroups = {
        Regio: [{ id: '1', value: 'Noord-Holland' }],
        Lidmaatschap: [{ id: '1', value: 'Gewoon lid' }],
        Motormerk: [{ id: '1', value: 'Harley-Davidson' }],
        Clubblad: [{ id: '1', value: 'Papier' }],
        WieWatWaar: [{ id: '1', value: 'Facebook' }],
        Function_permissions: [{
          id: 'default',
          value: {
            members: { read: ['hdcnAdmins', 'hdcnRegio_*'], write: ['hdcnAdmins'] },
            webshop: { read: ['hdcnLeden', 'hdcnAdmins'], write: ['hdcnLeden'] },
            events: { read: ['hdcnAdmins', 'hdcnEvents_*'], write: ['hdcnAdmins'] }
          }
        }]
      };

      mockParameterStore.getParameters.mockResolvedValue(existingConfigWithLegacyGroups);

      const assessment = await assessParameterMigrationNeeds();

      expect(assessment.preservedFeatures).toContain('Legacy group patterns (hdcn*, wildcards) are preserved');
      expect(assessment.enhancedFeatures).toContain('Role-based permissions work additively with existing parameter permissions');
      expect(assessment.enhancedFeatures).toContain('Backward compatible API for legacy permission checks');
    });

    test('should handle missing categories gracefully without requiring migration', async () => {
      const incompleteParameterData = {
        Regio: [{ id: '1', value: 'Noord-Holland' }],
        Lidmaatschap: [{ id: '1', value: 'Gewoon lid' }]
        // Missing Motormerk, Clubblad, etc.
      };

      mockParameterStore.getParameters.mockResolvedValue(incompleteParameterData);

      const assessment = await assessParameterMigrationNeeds();

      // Should identify missing categories but provide recommendations
      expect(assessment.migrationReasons.some(reason => 
        reason.includes('Missing expected categories')
      )).toBe(true);
      
      expect(assessment.recommendations).toContain('Address missing categories to ensure full compatibility');
      expect(assessment.recommendations).toContain('Consider restoring missing parameter data from backup');
    });

    test('should demonstrate additive enhancement approach', async () => {
      const baseParameterData = {
        Regio: [{ id: '1', value: 'Noord-Holland' }],
        Lidmaatschap: [{ id: '1', value: 'Gewoon lid' }],
        Motormerk: [{ id: '1', value: 'Harley-Davidson' }],
        Clubblad: [{ id: '1', value: 'Papier' }],
        WieWatWaar: [{ id: '1', value: 'Facebook' }],
        Function_permissions: [{
          id: 'default',
          value: {
            webshop: { read: ['hdcnLeden'], write: ['hdcnLeden'] }
          }
        }]
      };

      mockParameterStore.getParameters.mockResolvedValue(baseParameterData);

      const assessment = await assessParameterMigrationNeeds();

      // Should show that enhancements are additive, not replacement
      expect(assessment.enhancedFeatures).toContain(
        'Role-based permissions work additively with existing parameter permissions'
      );
      expect(assessment.enhancedFeatures).toContain(
        'Membership type restrictions enhanced with role-based field access'
      );
      expect(assessment.enhancedFeatures).toContain(
        'Combined permission checking (parameter + role + membership)'
      );
      
      // Should not require migration for additive enhancements
      expect(assessment.migrationRequired).toBe(false);
    });
  });

  describe('Error Handling and Fallbacks', () => {
    test('should handle parameter loading errors gracefully', async () => {
      mockParameterStore.getParameters.mockRejectedValue(new Error('API connection failed'));

      const validation = await validateParameterBackwardCompatibility();

      expect(validation.isCompatible).toBe(false);
      expect(validation.validationResults).toHaveLength(1);
      expect(validation.validationResults[0].category).toBe('SYSTEM');
      expect(validation.validationResults[0].status).toBe('error');
      expect(validation.validationResults[0].recommendations).toContain(
        'Check parameter store connectivity and data integrity'
      );
    });

    test('should provide fallback assessment when parameter loading fails', async () => {
      mockParameterStore.getParameters.mockRejectedValue(new Error('Network error'));

      const assessment = await assessParameterMigrationNeeds();

      expect(assessment.migrationRequired).toBe(false); // Assume no migration needed if can't assess
      expect(assessment.preservedFeatures).toContain('Fallback compatibility mode will be used');
      expect(assessment.enhancedFeatures).toContain('Basic role-based enhancements available');
      expect(assessment.recommendations).toContain('Check parameter store connectivity');
    });
  });
});