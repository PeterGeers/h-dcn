/**
 * Field-Level Permission Tests for New Role Structure
 * 
 * Tests that memberFields.ts permissions work correctly with the new permission + region role structure.
 * This validates that field visibility, editability, and access controls function properly.
 */

import { 
  MEMBER_FIELDS, 
  MEMBER_TABLE_CONTEXTS, 
  MEMBER_MODAL_CONTEXTS,
  createPermissionConfig,
  HDCNGroup,
  FieldDefinition,
  PermissionConfig
} from '../memberFields';

import { 
  checkUIPermission,
  userHasPermissionType,
  userHasPermissionWithRegion,
  getUserAccessibleRegions
} from '../../utils/functionPermissions';

// Mock user objects for testing different role combinations
const mockUsers = {
  // National administrator with full CRUD access
  nationalAdmin: {
    id: 'admin1',
    username: 'admin1',
    email: 'admin@h-dcn.nl',
    groups: ['Members_CRUD', 'Regio_All'] as HDCNGroup[],
    attributes: {}
  },

  // Regional administrator with CRUD access to Utrecht only
  regionalAdmin: {
    id: 'regional1',
    username: 'regional1', 
    email: 'regional@h-dcn.nl',
    groups: ['Members_CRUD', 'Regio_Utrecht'] as HDCNGroup[],
    attributes: {}
  },

  // National read-only user
  nationalReadOnly: {
    id: 'readonly1',
    username: 'readonly1',
    email: 'readonly@h-dcn.nl', 
    groups: ['Members_Read', 'Regio_All'] as HDCNGroup[],
    attributes: {}
  },

  // Regional read-only user
  regionalReadOnly: {
    id: 'readregional1',
    username: 'readregional1',
    email: 'readregional@h-dcn.nl',
    groups: ['Members_Read', 'Regio_Limburg'] as HDCNGroup[],
    attributes: {}
  },

  // Basic member (can only edit own data)
  basicMember: {
    id: 'member1',
    username: 'member1',
    email: 'member@h-dcn.nl',
    groups: ['hdcnLeden'] as HDCNGroup[],
    attributes: {}
  },

  // User with no regional access (incomplete role)
  noRegionalAccess: {
    id: 'incomplete1',
    username: 'incomplete1',
    email: 'incomplete@h-dcn.nl',
    groups: ['Members_CRUD'] as HDCNGroup[], // Missing regional role
    attributes: {}
  },

  // System administrator
  systemAdmin: {
    id: 'system1',
    username: 'system1',
    email: 'system@h-dcn.nl',
    groups: ['System_User_Management'] as HDCNGroup[],
    attributes: {}
  }
};

describe('Field-Level Permissions with New Role Structure', () => {
  
  describe('createPermissionConfig Helper Function', () => {
    test('should create correct permissions for member level with admin edit', () => {
      const config = createPermissionConfig('member', 'admin', false);
      
      expect(config.view).toContain('Members_Read');
      expect(config.view).toContain('Members_CRUD');
      expect(config.edit).toContain('Members_CRUD');
      expect(config.edit).not.toContain('hdcnLeden');
      expect(config.selfService).toBe(false);
    });

    test('should create correct permissions for member level with self-service', () => {
      const config = createPermissionConfig('member', 'self', true);
      
      expect(config.view).toContain('Members_Read');
      expect(config.view).toContain('Members_CRUD');
      expect(config.edit).toContain('hdcnLeden');
      expect(config.edit).toContain('Members_CRUD');
      expect(config.selfService).toBe(true);
    });

    test('should create correct permissions for admin level', () => {
      const config = createPermissionConfig('admin', 'admin', false);
      
      expect(config.view).toContain('Members_Read');
      expect(config.view).toContain('Members_CRUD');
      expect(config.view).not.toContain('hdcnLeden');
      expect(config.edit).toContain('Members_CRUD');
    });

    test('should create correct permissions for system level', () => {
      const config = createPermissionConfig('system', 'system', false);
      
      expect(config.view).toContain('System_User_Management');
      expect(config.view).not.toContain('Members_Read');
      expect(config.edit).toContain('System_User_Management');
    });
  });

  describe('Personal Information Field Permissions', () => {
    test('voornaam field should be viewable by all member roles', () => {
      const field = MEMBER_FIELDS.voornaam;
      
      expect(field.permissions?.view).toContain('hdcnLeden');
      expect(field.permissions?.view).toContain('Members_Read');
      expect(field.permissions?.view).toContain('Members_CRUD');
      // System_User_Management should NOT have view access to member fields (separation of concerns)
      expect(field.permissions?.view).not.toContain('System_User_Management');
    });

    test('voornaam field should be editable by admin and self-service', () => {
      const field = MEMBER_FIELDS.voornaam;
      
      expect(field.permissions?.edit).toContain('Members_CRUD');
      expect(field.permissions?.edit).toContain('System_User_Management');
      expect(field.permissions?.selfService).toBe(true);
    });

    test('geboortedatum field should have regional restrictions', () => {
      const field = MEMBER_FIELDS.geboortedatum;
      
      expect(field.permissions?.regionalRestricted).toBe(true);
      expect(field.permissions?.view).toContain('Members_Read');
      expect(field.permissions?.view).toContain('Members_CRUD');
    });

    test('computed fields should not be editable', () => {
      const korteNaamField = MEMBER_FIELDS.korte_naam;
      const leeftijdField = MEMBER_FIELDS.leeftijd;
      const verjaardagField = MEMBER_FIELDS.verjaardag;
      
      expect(korteNaamField.computed).toBe(true);
      expect(korteNaamField.permissions?.edit).toEqual([]);
      
      expect(leeftijdField.computed).toBe(true);
      expect(leeftijdField.permissions?.edit).toEqual([]);
      
      expect(verjaardagField.computed).toBe(true);
      expect(verjaardagField.permissions?.edit).toEqual([]);
    });
  });

  describe('Membership Information Field Permissions', () => {
    test('status field should only be editable by admins', () => {
      const field = MEMBER_FIELDS.status;
      
      expect(field.permissions?.view).toContain('Members_Read');
      expect(field.permissions?.view).toContain('Members_CRUD');
      expect(field.permissions?.edit).toContain('Members_CRUD');
      expect(field.permissions?.edit).not.toContain('hdcnLeden');
      expect(field.permissions?.selfService).toBe(false);
    });

    test('lidmaatschap field should have conditional edit permissions for new applicants', () => {
      const field = MEMBER_FIELDS.lidmaatschap;
      
      expect(field.conditionalEdit).toBeDefined();
      expect(field.conditionalEdit?.condition.field).toBe('status');
      expect(field.conditionalEdit?.condition.value).toBe('Aangemeld');
      expect(field.conditionalEdit?.permissions.selfService).toBe(true);
    });

    test('regio field should have conditional edit permissions for new applicants', () => {
      const field = MEMBER_FIELDS.regio;
      
      expect(field.conditionalEdit).toBeDefined();
      expect(field.conditionalEdit?.condition.field).toBe('status');
      expect(field.conditionalEdit?.condition.value).toBe('Aangemeld');
      expect(field.conditionalEdit?.permissions.selfService).toBe(true);
    });

    test('lidnummer field should be computed and not editable', () => {
      const field = MEMBER_FIELDS.lidnummer;
      
      expect(field.computed).toBe(true);
      expect(field.permissions?.edit).toEqual([]);
    });
  });

  describe('Motor Information Field Permissions', () => {
    test('motor fields should be restricted to specific membership types', () => {
      const motormerkField = MEMBER_FIELDS.motormerk;
      const motortypeField = MEMBER_FIELDS.motortype;
      const bouwjaarField = MEMBER_FIELDS.bouwjaar;
      const kentekenField = MEMBER_FIELDS.kenteken;
      
      [motormerkField, motortypeField, bouwjaarField, kentekenField].forEach(field => {
        expect(field.permissions?.membershipTypeRestricted).toContain('Gewoon lid');
        expect(field.permissions?.membershipTypeRestricted).toContain('Gezins lid');
        expect(field.permissions?.regionalRestricted).toBe(true);
        
        expect(field.showWhen).toBeDefined();
        expect(field.showWhen?.some(rule => 
          rule.field === 'lidmaatschap' && rule.value === 'Gewoon lid'
        )).toBe(true);
      });
    });
  });

  describe('Financial Information Field Permissions', () => {
    test('bankrekeningnummer field should have regional restrictions', () => {
      const field = MEMBER_FIELDS.bankrekeningnummer;
      
      expect(field.permissions?.regionalRestricted).toBe(true);
      expect(field.permissions?.view).toContain('Members_Read');
      expect(field.permissions?.view).toContain('Members_CRUD');
      expect(field.permissions?.edit).toContain('Members_CRUD');
      expect(field.permissions?.selfService).toBe(true);
    });

    test('betaalwijze field should have regional restrictions', () => {
      const field = MEMBER_FIELDS.betaalwijze;
      
      expect(field.permissions?.regionalRestricted).toBe(true);
      expect(field.permissions?.selfService).toBe(true);
    });
  });

  describe('Administrative Field Permissions', () => {
    test('system fields should only be viewable by system roles', () => {
      const createdAtField = MEMBER_FIELDS.created_at;
      const updatedAtField = MEMBER_FIELDS.updated_at;
      
      expect(createdAtField.permissions?.view).toContain('System_User_Management');
      expect(createdAtField.permissions?.edit).toEqual([]);
      
      expect(updatedAtField.permissions?.view).toContain('System_User_Management');
      expect(updatedAtField.permissions?.edit).toEqual([]);
    });

    test('notities field should only be accessible by admins', () => {
      const field = MEMBER_FIELDS.notities;
      
      expect(field.permissions?.view).toContain('Members_Read');
      expect(field.permissions?.view).toContain('Members_CRUD');
      expect(field.permissions?.edit).toContain('Members_CRUD');
      expect(field.permissions?.selfService).toBe(false);
    });
  });

  describe('Enum Permission Restrictions', () => {
    test('lidmaatschap field should restrict Erelid to CRUD roles only', () => {
      const field = MEMBER_FIELDS.lidmaatschap;
      
      expect(field.enumPermissions?.['Erelid']).toContain('Members_CRUD');
      expect(field.enumPermissions?.['Erelid']).toContain('System_User_Management');
      expect(field.enumPermissions?.['Erelid']).not.toContain('Members_Read');
    });

    test('regio field should restrict Overig to CRUD roles only', () => {
      const field = MEMBER_FIELDS.regio;
      
      expect(field.enumPermissions?.['Overig']).toContain('Members_CRUD');
      expect(field.enumPermissions?.['Overig']).toContain('System_User_Management');
      expect(field.enumPermissions?.['Overig']).not.toContain('Members_Read');
    });
  });

  describe('Table Context Permissions', () => {
    test('memberOverview table should have correct permissions', () => {
      const context = MEMBER_TABLE_CONTEXTS.memberOverview;
      
      expect(context.permissions.view).toContain('Members_Read');
      expect(context.permissions.view).toContain('Members_CRUD');
      expect(context.permissions.view).toContain('System_User_Management');
      expect(context.permissions.export).toContain('Members_Read');
      expect(context.regionalRestricted).toBe(true);
    });

    test('motorView table should have appropriate permissions', () => {
      const context = MEMBER_TABLE_CONTEXTS.motorView;
      
      expect(context.permissions.view).toContain('hdcnLeden');
      expect(context.permissions.view).toContain('Members_Read');
      expect(context.permissions.view).toContain('Events_Read');
      expect(context.permissions.export).toContain('Members_CRUD');
      expect(context.permissions.export).toContain('Events_CRUD');
    });

    test('communicationView table should have communication permissions', () => {
      const context = MEMBER_TABLE_CONTEXTS.communicationView;
      
      expect(context.permissions.view).toContain('Communication_Read');
      expect(context.permissions.view).toContain('Communication_CRUD');
      // Communication_CRUD should NOT have export access - they need Communication_Export specifically
      expect(context.permissions.export).not.toContain('Communication_CRUD');
      expect(context.permissions.export).toContain('Communication_Export');
    });

    test('financialView table should have restricted permissions', () => {
      const context = MEMBER_TABLE_CONTEXTS.financialView;
      
      expect(context.permissions.view).toContain('Members_Read');
      expect(context.permissions.view).toContain('Members_CRUD');
      expect(context.permissions.export).toContain('Members_Read');
      expect(context.permissions.export).toContain('Members_CRUD');
      // Financial view should not include basic member access
      expect(context.permissions.view).not.toContain('hdcnLeden');
    });
  });

  describe('Modal Context Permissions', () => {
    test('memberView modal should have correct section permissions', () => {
      const context = MEMBER_MODAL_CONTEXTS.memberView;
      
      // Check overall modal permissions
      expect(context.permissions.view).toContain('hdcnLeden');
      expect(context.permissions.view).toContain('Members_Read');
      expect(context.permissions.edit).toContain('Members_CRUD');
      
      // Check individual section permissions
      const personalSection = context.sections.find(s => s.name === 'personal');
      expect(personalSection?.permissions?.view).toContain('hdcnLeden');
      expect(personalSection?.permissions?.edit).toContain('Members_CRUD');
      
      const adminSection = context.sections.find(s => s.name === 'administrative');
      expect(adminSection?.permissions?.view).toContain('Members_Read');
      expect(adminSection?.permissions?.edit).toContain('Members_CRUD');
    });

    test('memberRegistration modal should allow verzoek_lid access', () => {
      const context = MEMBER_MODAL_CONTEXTS.memberRegistration;
      
      expect(context.permissions.view).toContain('verzoek_lid');
      expect(context.permissions.edit).toContain('verzoek_lid');
      
      // Check that all sections allow verzoek_lid access
      context.sections.forEach(section => {
        expect(section.permissions?.view).toContain('verzoek_lid');
        expect(section.permissions?.edit).toContain('verzoek_lid');
      });
    });

    test('memberQuickView modal should have read-only permissions', () => {
      const context = MEMBER_MODAL_CONTEXTS.memberQuickView;
      
      expect(context.permissions.view).toContain('Members_Read');
      expect(context.permissions.view).toContain('Members_CRUD');
      expect(context.permissions.view).not.toContain('hdcnLeden');
      
      // Check that fields are marked as read-only
      const essentialSection = context.sections.find(s => s.name === 'essential');
      essentialSection?.fields?.forEach(field => {
        expect(field.readOnly).toBe(true);
      });
    });
  });

  describe('Integration with Permission System', () => {
    test('national admin should have access to all fields', () => {
      const user = mockUsers.nationalAdmin;
      
      // Test basic permission checks
      expect(userHasPermissionType(user, 'members', 'crud')).toBe(true);
      expect(userHasPermissionType(user, 'members', 'read')).toBe(true);
      expect(getUserAccessibleRegions(user)).toEqual(['all']);
      
      // Test UI permission checks
      expect(checkUIPermission(user, 'members', 'read')).toBe(true);
      expect(checkUIPermission(user, 'members', 'write')).toBe(true);
      expect(checkUIPermission(user, 'members', 'read', 'utrecht')).toBe(true);
      expect(checkUIPermission(user, 'members', 'write', 'limburg')).toBe(true);
    });

    test('regional admin should have limited regional access', () => {
      const user = mockUsers.regionalAdmin;
      
      // Test basic permission checks
      expect(userHasPermissionType(user, 'members', 'crud')).toBe(true);
      expect(getUserAccessibleRegions(user)).toEqual(['utrecht']);
      
      // Test regional access
      expect(checkUIPermission(user, 'members', 'write', 'utrecht')).toBe(true);
      expect(checkUIPermission(user, 'members', 'write', 'limburg')).toBe(false);
    });

    test('read-only user should not have write access', () => {
      const user = mockUsers.nationalReadOnly;
      
      // Test permission checks
      expect(userHasPermissionType(user, 'members', 'read')).toBe(true);
      expect(userHasPermissionType(user, 'members', 'crud')).toBe(false);
      
      // Test UI permissions
      expect(checkUIPermission(user, 'members', 'read')).toBe(true);
      expect(checkUIPermission(user, 'members', 'write')).toBe(false);
    });

    test('basic member should have limited access', () => {
      const user = mockUsers.basicMember;
      
      // Basic members don't have Members_Read or Members_CRUD roles
      expect(userHasPermissionType(user, 'members', 'read')).toBe(false);
      expect(userHasPermissionType(user, 'members', 'crud')).toBe(false);
      
      // Should not have UI access to member management
      expect(checkUIPermission(user, 'members', 'read')).toBe(false);
      expect(checkUIPermission(user, 'members', 'write')).toBe(false);
    });

    test('user with incomplete roles should be denied access', () => {
      const user = mockUsers.noRegionalAccess;
      
      // Has permission but no regional access
      expect(userHasPermissionType(user, 'members', 'crud')).toBe(true);
      expect(getUserAccessibleRegions(user)).toEqual([]);
      
      // Should be denied UI access due to missing regional role
      expect(checkUIPermission(user, 'members', 'read')).toBe(false);
      expect(checkUIPermission(user, 'members', 'write')).toBe(false);
    });

    test('system admin should have system-level access', () => {
      const user = mockUsers.systemAdmin;
      
      // System admin doesn't have member permissions
      expect(userHasPermissionType(user, 'members', 'read')).toBe(false);
      expect(userHasPermissionType(user, 'members', 'crud')).toBe(false);
      
      // But should have system access (if we had system permission checks)
      expect(checkUIPermission(user, 'members', 'read')).toBe(false);
    });
  });

  describe('Field Validation with Permissions', () => {
    test('required fields should respect conditional requirements', () => {
      const minderjarigNaamField = MEMBER_FIELDS.minderjarigNaam;
      
      expect(minderjarigNaamField.validation).toBeDefined();
      const requiredValidation = minderjarigNaamField.validation?.find(v => v.type === 'required');
      expect(requiredValidation?.condition?.field).toBe('geboortedatum');
      expect(requiredValidation?.condition?.operator).toBe('age_less_than');
      expect(requiredValidation?.condition?.value).toBe(18);
    });

    test('IBAN field should have conditional requirements', () => {
      const ibanField = MEMBER_FIELDS.bankrekeningnummer;
      
      expect(ibanField.validation).toBeDefined();
      const requiredValidation = ibanField.validation?.find(v => v.type === 'required');
      expect(requiredValidation?.condition?.field).toBe('lidmaatschap');
      expect(requiredValidation?.condition?.operator).toBe('contains');
    });

    test('wiewatwaar field should be required for new applications only', () => {
      const field = MEMBER_FIELDS.wiewatwaar;
      
      expect(field.validation).toBeDefined();
      const requiredValidation = field.validation?.find(v => v.type === 'required');
      expect(requiredValidation?.condition?.field).toBe('member_id');
      expect(requiredValidation?.condition?.operator).toBe('not_exists');
    });
  });

  describe('Conditional Field Visibility', () => {
    test('motor fields should only show for appropriate membership types', () => {
      const motorFields = ['motormerk', 'motortype', 'bouwjaar', 'kenteken'];
      
      motorFields.forEach(fieldKey => {
        const field = MEMBER_FIELDS[fieldKey];
        expect(field.showWhen).toBeDefined();
        
        const hasGewoonLidCondition = field.showWhen?.some(condition =>
          condition.field === 'lidmaatschap' && 
          condition.operator === 'equals' && 
          condition.value === 'Gewoon lid'
        );
        
        const hasGezinsLidCondition = field.showWhen?.some(condition =>
          condition.field === 'lidmaatschap' && 
          condition.operator === 'equals' && 
          condition.value === 'Gezins lid'
        );
        
        expect(hasGewoonLidCondition || hasGezinsLidCondition).toBe(true);
      });
    });

    test('minderjarigNaam field should only show for minors', () => {
      const field = MEMBER_FIELDS.minderjarigNaam;
      
      expect(field.showWhen).toBeDefined();
      const ageCondition = field.showWhen?.find(condition =>
        condition.field === 'geboortedatum' && 
        condition.operator === 'age_less_than' && 
        condition.value === 18
      );
      
      expect(ageCondition).toBeDefined();
    });
  });
});