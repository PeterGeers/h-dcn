/**
 * Real-World Field-Level Permission Tests
 * 
 * Tests field-level permissions in realistic scenarios to ensure the new role structure
 * works correctly for actual use cases in the H-DCN system.
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

// Real-world user scenarios based on H-DCN organizational structure
const realWorldUsers = {
  // National member administrator - can manage all members nationwide
  nationalMemberAdmin: {
    id: 'admin_national',
    username: 'admin_national',
    email: 'admin@h-dcn.nl',
    groups: ['Members_CRUD', 'Regio_All'] as HDCNGroup[],
    attributes: {}
  },

  // Utrecht regional coordinator - manages only Utrecht members
  utrechtCoordinator: {
    id: 'coord_utrecht',
    username: 'coord_utrecht',
    email: 'utrecht@h-dcn.nl',
    groups: ['Members_CRUD', 'Regio_Utrecht'] as HDCNGroup[],
    attributes: {}
  },

  // Limburg regional viewer - can only view Limburg members
  limburgViewer: {
    id: 'viewer_limburg',
    username: 'viewer_limburg',
    email: 'limburg.viewer@h-dcn.nl',
    groups: ['Members_Read', 'Regio_Limburg'] as HDCNGroup[],
    attributes: {}
  },

  // Regular member from Noord-Holland - limited self-service access
  regularMemberNH: {
    id: 'member_nh',
    username: 'member_nh',
    email: 'member@h-dcn.nl',
    groups: ['hdcnLeden', 'Regio_Noord-Holland'] as HDCNGroup[],
    attributes: {}
  },

  // New applicant - registration process access
  newApplicant: {
    id: 'applicant_new',
    username: 'applicant_new',
    email: 'new.applicant@h-dcn.nl',
    groups: ['verzoek_lid', 'Regio_Brabant/Zeeland'] as HDCNGroup[],
    attributes: {}
  },

  // System administrator - system-level access
  systemAdmin: {
    id: 'sys_admin',
    username: 'sys_admin',
    email: 'system@h-dcn.nl',
    groups: ['System_User_Management'] as HDCNGroup[],
    attributes: {}
  },

  // Communication manager - communication permissions
  communicationManager: {
    id: 'comm_manager',
    username: 'comm_manager',
    email: 'communication@h-dcn.nl',
    groups: ['Communication_CRUD', 'Regio_All'] as HDCNGroup[],
    attributes: {}
  },

  // Events coordinator for Groningen/Drenthe
  eventsCoordGD: {
    id: 'events_gd',
    username: 'events_gd',
    email: 'events.gd@h-dcn.nl',
    groups: ['Events_CRUD', 'Members_Read', 'Regio_Groningen/Drenthe'] as HDCNGroup[],
    attributes: {}
  },

  // Member with incomplete roles (missing regional access)
  incompleteRoleMember: {
    id: 'incomplete',
    username: 'incomplete',
    email: 'incomplete@h-dcn.nl',
    groups: ['Members_CRUD'] as HDCNGroup[], // Missing regional role
    attributes: {}
  }
};

/**
 * Helper function to test field access in realistic scenarios
 */
function testFieldAccess(user: any, fieldKey: string, action: 'view' | 'edit' = 'view'): boolean {
  const field = MEMBER_FIELDS[fieldKey];
  if (!field || !field.permissions) return false;

  const requiredRoles = action === 'view' ? field.permissions.view : field.permissions.edit;
  if (!requiredRoles || requiredRoles.length === 0) return false;

  const userRoles = user.groups || [];
  
  // Check if user has any of the required roles
  const hasRequiredRole = requiredRoles.some(role => userRoles.includes(role));
  if (!hasRequiredRole) return false;

  // If field has regional restrictions, check regional access
  if (field.permissions.regionalRestricted) {
    const hasRegionalAccess = userRoles.some(role => 
      role === 'Regio_All' || role.startsWith('Regio_')
    );
    if (!hasRegionalAccess) return false;
  }

  return true;
}

/**
 * Helper function to test table context access
 */
function testTableContextAccess(user: any, contextName: string, action: 'view' | 'export' = 'view'): boolean {
  const context = MEMBER_TABLE_CONTEXTS[contextName];
  if (!context) return false;

  const requiredRoles = action === 'view' ? context.permissions.view : context.permissions.export;
  if (!requiredRoles) return false;

  const userRoles = user.groups || [];
  const hasRequiredRole = requiredRoles.some(role => userRoles.includes(role));
  
  if (!hasRequiredRole) return false;

  // Check regional restrictions
  if (context.regionalRestricted) {
    const hasRegionalAccess = userRoles.some(role => 
      role === 'Regio_All' || role.startsWith('Regio_')
    );
    if (!hasRegionalAccess) return false;
  }

  return true;
}

describe('Real-World Field-Level Permission Tests', () => {

  describe('National Member Administrator Scenarios', () => {
    const user = realWorldUsers.nationalMemberAdmin;

    test('should have full access to all personal information fields', () => {
      // Basic personal information
      expect(testFieldAccess(user, 'voornaam', 'view')).toBe(true);
      expect(testFieldAccess(user, 'voornaam', 'edit')).toBe(true);
      expect(testFieldAccess(user, 'achternaam', 'view')).toBe(true);
      expect(testFieldAccess(user, 'achternaam', 'edit')).toBe(true);
      expect(testFieldAccess(user, 'email', 'view')).toBe(true);
      expect(testFieldAccess(user, 'email', 'edit')).toBe(true);

      // Sensitive information (regional restricted)
      expect(testFieldAccess(user, 'geboortedatum', 'view')).toBe(true);
      expect(testFieldAccess(user, 'geboortedatum', 'edit')).toBe(true);
      expect(testFieldAccess(user, 'telefoon', 'view')).toBe(true);
      expect(testFieldAccess(user, 'telefoon', 'edit')).toBe(true);

      // Computed fields (view only)
      expect(testFieldAccess(user, 'korte_naam', 'view')).toBe(true);
      expect(testFieldAccess(user, 'korte_naam', 'edit')).toBe(false);
      expect(testFieldAccess(user, 'leeftijd', 'view')).toBe(true);
      expect(testFieldAccess(user, 'leeftijd', 'edit')).toBe(false);
    });

    test('should have full access to membership management fields', () => {
      // Administrative fields
      expect(testFieldAccess(user, 'status', 'view')).toBe(true);
      expect(testFieldAccess(user, 'status', 'edit')).toBe(true);
      expect(testFieldAccess(user, 'lidmaatschap', 'view')).toBe(true);
      expect(testFieldAccess(user, 'lidmaatschap', 'edit')).toBe(true);
      expect(testFieldAccess(user, 'regio', 'view')).toBe(true);
      expect(testFieldAccess(user, 'regio', 'edit')).toBe(true);

      // Computed membership fields
      expect(testFieldAccess(user, 'lidnummer', 'view')).toBe(true);
      expect(testFieldAccess(user, 'lidnummer', 'edit')).toBe(false);
      expect(testFieldAccess(user, 'jaren_lid', 'view')).toBe(true);
      expect(testFieldAccess(user, 'jaren_lid', 'edit')).toBe(false);
    });

    test('should have access to all table contexts', () => {
      expect(testTableContextAccess(user, 'memberOverview', 'view')).toBe(true);
      expect(testTableContextAccess(user, 'memberOverview', 'export')).toBe(true);
      expect(testTableContextAccess(user, 'memberCompact', 'view')).toBe(true);
      expect(testTableContextAccess(user, 'motorView', 'view')).toBe(true);
      expect(testTableContextAccess(user, 'communicationView', 'view')).toBe(true);
      expect(testTableContextAccess(user, 'financialView', 'view')).toBe(true);
      expect(testTableContextAccess(user, 'financialView', 'export')).toBe(true);
    });

    test('should have correct permission system integration', () => {
      expect(checkUIPermission(user, 'members', 'read')).toBe(true);
      expect(checkUIPermission(user, 'members', 'write')).toBe(true);
      expect(checkUIPermission(user, 'members', 'read', 'utrecht')).toBe(true);
      expect(checkUIPermission(user, 'members', 'write', 'limburg')).toBe(true);
      expect(getUserAccessibleRegions(user)).toEqual(['all']);
    });
  });

  describe('Regional Coordinator Scenarios', () => {
    const user = realWorldUsers.utrechtCoordinator;

    test('should have full access within their region', () => {
      // Should have CRUD access to personal information
      expect(testFieldAccess(user, 'voornaam', 'view')).toBe(true);
      expect(testFieldAccess(user, 'voornaam', 'edit')).toBe(true);
      expect(testFieldAccess(user, 'achternaam', 'view')).toBe(true);
      expect(testFieldAccess(user, 'achternaam', 'edit')).toBe(true);

      // Should have access to regional restricted fields
      expect(testFieldAccess(user, 'geboortedatum', 'view')).toBe(true);
      expect(testFieldAccess(user, 'geboortedatum', 'edit')).toBe(true);
      expect(testFieldAccess(user, 'telefoon', 'view')).toBe(true);
      expect(testFieldAccess(user, 'telefoon', 'edit')).toBe(true);

      // Should have access to membership management
      expect(testFieldAccess(user, 'status', 'view')).toBe(true);
      expect(testFieldAccess(user, 'status', 'edit')).toBe(true);
      expect(testFieldAccess(user, 'lidmaatschap', 'view')).toBe(true);
      expect(testFieldAccess(user, 'lidmaatschap', 'edit')).toBe(true);
    });

    test('should have regional access restrictions', () => {
      expect(getUserAccessibleRegions(user)).toEqual(['utrecht']);
      expect(checkUIPermission(user, 'members', 'write', 'utrecht')).toBe(true);
      expect(checkUIPermission(user, 'members', 'write', 'limburg')).toBe(false);
    });

    test('should have access to appropriate table contexts', () => {
      expect(testTableContextAccess(user, 'memberOverview', 'view')).toBe(true);
      expect(testTableContextAccess(user, 'memberOverview', 'export')).toBe(true);
      expect(testTableContextAccess(user, 'motorView', 'view')).toBe(true);
      expect(testTableContextAccess(user, 'financialView', 'view')).toBe(true);
    });
  });

  describe('Regional Viewer Scenarios', () => {
    const user = realWorldUsers.limburgViewer;

    test('should have read-only access to member information', () => {
      // Should be able to view but not edit personal information
      expect(testFieldAccess(user, 'voornaam', 'view')).toBe(true);
      expect(testFieldAccess(user, 'voornaam', 'edit')).toBe(false);
      expect(testFieldAccess(user, 'achternaam', 'view')).toBe(true);
      expect(testFieldAccess(user, 'achternaam', 'edit')).toBe(false);

      // Should be able to view regional restricted fields
      expect(testFieldAccess(user, 'geboortedatum', 'view')).toBe(true);
      expect(testFieldAccess(user, 'geboortedatum', 'edit')).toBe(false);
      expect(testFieldAccess(user, 'telefoon', 'view')).toBe(true);
      expect(testFieldAccess(user, 'telefoon', 'edit')).toBe(false);

      // Should be able to view membership information
      expect(testFieldAccess(user, 'status', 'view')).toBe(true);
      expect(testFieldAccess(user, 'status', 'edit')).toBe(false);
      expect(testFieldAccess(user, 'lidmaatschap', 'view')).toBe(true);
      expect(testFieldAccess(user, 'lidmaatschap', 'edit')).toBe(false);
    });

    test('should have regional access restrictions', () => {
      expect(getUserAccessibleRegions(user)).toEqual(['limburg']);
      expect(checkUIPermission(user, 'members', 'read', 'limburg')).toBe(true);
      expect(checkUIPermission(user, 'members', 'read', 'utrecht')).toBe(false);
      expect(checkUIPermission(user, 'members', 'write')).toBe(false);
    });

    test('should have read-only table access', () => {
      expect(testTableContextAccess(user, 'memberOverview', 'view')).toBe(true);
      expect(testTableContextAccess(user, 'memberOverview', 'export')).toBe(true); // Members_Read can export
      expect(testTableContextAccess(user, 'motorView', 'view')).toBe(true);
      expect(testTableContextAccess(user, 'financialView', 'view')).toBe(true);
    });
  });

  describe('Regular Member Scenarios', () => {
    const user = realWorldUsers.regularMemberNH;

    test('should have limited access to personal information', () => {
      // Should be able to view basic fields (hdcnLeden in view permissions)
      expect(testFieldAccess(user, 'voornaam', 'view')).toBe(true);
      expect(testFieldAccess(user, 'achternaam', 'view')).toBe(true);
      expect(testFieldAccess(user, 'email', 'view')).toBe(true);

      // Should not be able to edit (no Members_CRUD role)
      expect(testFieldAccess(user, 'voornaam', 'edit')).toBe(false);
      expect(testFieldAccess(user, 'achternaam', 'edit')).toBe(false);

      // geboortedatum uses admin-level permissions, so hdcnLeden should not have access
      expect(testFieldAccess(user, 'geboortedatum', 'view')).toBe(false);

      // telefoon uses member-level permissions + regional restriction, so hdcnLeden with regional role should have access
      expect(testFieldAccess(user, 'telefoon', 'view')).toBe(true);
    });

    test('should have limited membership information access', () => {
      // Should be able to view basic membership info
      expect(testFieldAccess(user, 'lidmaatschap', 'view')).toBe(true);
      expect(testFieldAccess(user, 'regio', 'view')).toBe(true);
      expect(testFieldAccess(user, 'lidnummer', 'view')).toBe(true);

      // Should not be able to edit membership info
      expect(testFieldAccess(user, 'lidmaatschap', 'edit')).toBe(false);
      expect(testFieldAccess(user, 'regio', 'edit')).toBe(false);

      // Should not be able to view/edit status (admin only)
      expect(testFieldAccess(user, 'status', 'view')).toBe(false);
      expect(testFieldAccess(user, 'status', 'edit')).toBe(false);
    });

    test('should have limited table access', () => {
      // Should have access to motor view (hdcnLeden included + has regional role)
      expect(testTableContextAccess(user, 'motorView', 'view')).toBe(true);

      // Should not have access to admin table contexts
      expect(testTableContextAccess(user, 'memberOverview', 'view')).toBe(false);
      expect(testTableContextAccess(user, 'financialView', 'view')).toBe(false);
      expect(testTableContextAccess(user, 'communicationView', 'view')).toBe(false);
    });

    test('should not have member management permissions', () => {
      expect(checkUIPermission(user, 'members', 'read')).toBe(false);
      expect(checkUIPermission(user, 'members', 'write')).toBe(false);
      expect(userHasPermissionType(user, 'members', 'read')).toBe(false);
      expect(userHasPermissionType(user, 'members', 'crud')).toBe(false);
    });
  });

  describe('New Applicant Scenarios', () => {
    const user = realWorldUsers.newApplicant;

    test('should have registration access to required fields', () => {
      // verzoek_lid is included in view permissions for personal and membership fields
      expect(testFieldAccess(user, 'voornaam', 'view')).toBe(true);
      expect(testFieldAccess(user, 'voornaam', 'edit')).toBe(true);
      expect(testFieldAccess(user, 'achternaam', 'view')).toBe(true);
      expect(testFieldAccess(user, 'achternaam', 'edit')).toBe(true);
      expect(testFieldAccess(user, 'email', 'view')).toBe(true);
      expect(testFieldAccess(user, 'email', 'edit')).toBe(true);

      // Should be able to select membership type and region during registration
      expect(testFieldAccess(user, 'lidmaatschap', 'view')).toBe(true);
      expect(testFieldAccess(user, 'lidmaatschap', 'edit')).toBe(true);
      expect(testFieldAccess(user, 'regio', 'view')).toBe(true);
      expect(testFieldAccess(user, 'regio', 'edit')).toBe(true);
    });

    test('should not have access to administrative fields', () => {
      // Should not be able to view/edit status (admin only)
      expect(testFieldAccess(user, 'status', 'view')).toBe(false);
      expect(testFieldAccess(user, 'status', 'edit')).toBe(false);

      // Should not have access to system fields
      expect(testFieldAccess(user, 'created_at', 'view')).toBe(false);
      expect(testFieldAccess(user, 'updated_at', 'view')).toBe(false);
      expect(testFieldAccess(user, 'notities', 'view')).toBe(false);
    });

    test('should not have table access during registration', () => {
      expect(testTableContextAccess(user, 'memberOverview', 'view')).toBe(false);
      expect(testTableContextAccess(user, 'motorView', 'view')).toBe(false);
      expect(testTableContextAccess(user, 'financialView', 'view')).toBe(false);
    });
  });

  describe('System Administrator Scenarios', () => {
    const user = realWorldUsers.systemAdmin;

    test('should have access to system fields', () => {
      // Should be able to view system fields
      expect(testFieldAccess(user, 'created_at', 'view')).toBe(true);
      expect(testFieldAccess(user, 'updated_at', 'view')).toBe(true);

      // System fields should not be editable by anyone
      expect(testFieldAccess(user, 'created_at', 'edit')).toBe(false);
      expect(testFieldAccess(user, 'updated_at', 'edit')).toBe(false);
    });

    test('should not have member management permissions', () => {
      // System admin doesn't have member permissions
      expect(testFieldAccess(user, 'voornaam', 'view')).toBe(false);
      expect(testFieldAccess(user, 'status', 'view')).toBe(false);
      expect(checkUIPermission(user, 'members', 'read')).toBe(false);
      expect(checkUIPermission(user, 'members', 'write')).toBe(false);
    });
  });

  describe('Communication Manager Scenarios', () => {
    const user = realWorldUsers.communicationManager;

    test('should have access to communication-related table contexts', () => {
      expect(testTableContextAccess(user, 'communicationView', 'view')).toBe(true);
      expect(testTableContextAccess(user, 'communicationView', 'export')).toBe(false); // Needs Communication_Export role
    });

    test('should not have member CRUD permissions', () => {
      expect(checkUIPermission(user, 'members', 'read')).toBe(false);
      expect(checkUIPermission(user, 'members', 'write')).toBe(false);
    });
  });

  describe('Events Coordinator Scenarios', () => {
    const user = realWorldUsers.eventsCoordGD;

    test('should have member read access for event planning', () => {
      // Has Members_Read role, so should be able to view member information
      expect(testFieldAccess(user, 'voornaam', 'view')).toBe(true);
      expect(testFieldAccess(user, 'email', 'view')).toBe(true);
      expect(testFieldAccess(user, 'telefoon', 'view')).toBe(true);

      // Should not be able to edit member information (no Members_CRUD)
      expect(testFieldAccess(user, 'voornaam', 'edit')).toBe(false);
      expect(testFieldAccess(user, 'status', 'edit')).toBe(false);
    });

    test('should have regional access restrictions', () => {
      expect(getUserAccessibleRegions(user)).toEqual(['groningen_drenthe']);
      expect(checkUIPermission(user, 'members', 'read', 'groningen_drenthe')).toBe(true);
      expect(checkUIPermission(user, 'members', 'read', 'utrecht')).toBe(false);
    });

    test('should have access to motor view for event planning', () => {
      expect(testTableContextAccess(user, 'motorView', 'view')).toBe(true);
      expect(testTableContextAccess(user, 'memberOverview', 'view')).toBe(true);
    });
  });

  describe('Incomplete Role Scenarios', () => {
    const user = realWorldUsers.incompleteRoleMember;

    test('should be denied access due to missing regional role', () => {
      // Has Members_CRUD but no regional role
      expect(userHasPermissionType(user, 'members', 'crud')).toBe(true);
      expect(getUserAccessibleRegions(user)).toEqual([]);

      // Should be denied UI access due to missing regional role
      expect(checkUIPermission(user, 'members', 'read')).toBe(false);
      expect(checkUIPermission(user, 'members', 'write')).toBe(false);

      // Should be denied access to regional restricted fields
      expect(testFieldAccess(user, 'geboortedatum', 'view')).toBe(false);
      expect(testFieldAccess(user, 'telefoon', 'view')).toBe(false);

      // Should be denied access to regional restricted table contexts
      expect(testTableContextAccess(user, 'memberOverview', 'view')).toBe(false);
      expect(testTableContextAccess(user, 'motorView', 'view')).toBe(false);
    });
  });

  describe('Self-Service Permission Scenarios', () => {
    test('should identify fields that allow self-service editing', () => {
      const selfServiceFields = Object.entries(MEMBER_FIELDS)
        .filter(([key, field]) => field.permissions?.selfService === true)
        .map(([key]) => key);

      // These fields should allow self-service editing
      expect(selfServiceFields).toContain('voornaam');
      expect(selfServiceFields).toContain('achternaam');
      expect(selfServiceFields).toContain('email');
      expect(selfServiceFields).toContain('telefoon');
      expect(selfServiceFields).toContain('bankrekeningnummer');
      expect(selfServiceFields).toContain('betaalwijze');

      // Administrative fields should not allow self-service
      expect(selfServiceFields).not.toContain('status');
      expect(selfServiceFields).not.toContain('notities');
      expect(selfServiceFields).not.toContain('created_at');
    });

    test('should verify self-service permissions are correctly configured', () => {
      const selfServiceFields = ['voornaam', 'achternaam', 'email', 'telefoon', 'bankrekeningnummer', 'betaalwijze'];
      
      selfServiceFields.forEach(fieldKey => {
        const field = MEMBER_FIELDS[fieldKey];
        expect(field.permissions?.selfService).toBe(true);
        expect(field.permissions?.edit).toContain('Members_CRUD');
        expect(field.permissions?.edit).toContain('System_User_Management');
      });
    });
  });

  describe('Conditional Permission Scenarios', () => {
    test('should handle conditional edit permissions for new applicants', () => {
      const lidmaatschapField = MEMBER_FIELDS.lidmaatschap;
      const regioField = MEMBER_FIELDS.regio;

      // Both fields should have conditional edit permissions for new applicants
      expect(lidmaatschapField.conditionalEdit).toBeDefined();
      expect(lidmaatschapField.conditionalEdit?.condition.field).toBe('status');
      expect(lidmaatschapField.conditionalEdit?.condition.value).toBe('Aangemeld');
      expect(lidmaatschapField.conditionalEdit?.permissions.selfService).toBe(true);

      expect(regioField.conditionalEdit).toBeDefined();
      expect(regioField.conditionalEdit?.condition.field).toBe('status');
      expect(regioField.conditionalEdit?.condition.value).toBe('Aangemeld');
      expect(regioField.conditionalEdit?.permissions.selfService).toBe(true);
    });

    test('should handle membership type restrictions for motor fields', () => {
      const motorFields = ['motormerk', 'motortype', 'bouwjaar', 'kenteken'];
      
      motorFields.forEach(fieldKey => {
        const field = MEMBER_FIELDS[fieldKey];
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

  describe('Enum Permission Restrictions', () => {
    test('should restrict special enum values to appropriate roles', () => {
      const lidmaatschapField = MEMBER_FIELDS.lidmaatschap;
      const regioField = MEMBER_FIELDS.regio;

      // Erelid should be restricted to CRUD roles only
      expect(lidmaatschapField.enumPermissions?.['Erelid']).toContain('Members_CRUD');
      expect(lidmaatschapField.enumPermissions?.['Erelid']).toContain('System_User_Management');
      expect(lidmaatschapField.enumPermissions?.['Erelid']).not.toContain('Members_Read');

      // Overig region should be restricted to CRUD roles only
      expect(regioField.enumPermissions?.['Overig']).toContain('Members_CRUD');
      expect(regioField.enumPermissions?.['Overig']).toContain('System_User_Management');
      expect(regioField.enumPermissions?.['Overig']).not.toContain('Members_Read');
    });
  });

  describe('Integration with Permission System', () => {
    test('should correctly integrate with checkUIPermission function', () => {
      const nationalAdmin = realWorldUsers.nationalMemberAdmin;
      const regionalCoord = realWorldUsers.utrechtCoordinator;
      const viewer = realWorldUsers.limburgViewer;
      const regularMember = realWorldUsers.regularMemberNH;

      // National admin should have full access
      expect(checkUIPermission(nationalAdmin, 'members', 'read')).toBe(true);
      expect(checkUIPermission(nationalAdmin, 'members', 'write')).toBe(true);

      // Regional coordinator should have regional access
      expect(checkUIPermission(regionalCoord, 'members', 'write', 'utrecht')).toBe(true);
      expect(checkUIPermission(regionalCoord, 'members', 'write', 'limburg')).toBe(false);

      // Viewer should have read-only access
      expect(checkUIPermission(viewer, 'members', 'read', 'limburg')).toBe(true);
      expect(checkUIPermission(viewer, 'members', 'write')).toBe(false);

      // Regular member should not have member management access
      expect(checkUIPermission(regularMember, 'members', 'read')).toBe(false);
      expect(checkUIPermission(regularMember, 'members', 'write')).toBe(false);
    });

    test('should correctly integrate with userHasPermissionType function', () => {
      const nationalAdmin = realWorldUsers.nationalMemberAdmin;
      const viewer = realWorldUsers.limburgViewer;
      const regularMember = realWorldUsers.regularMemberNH;

      // National admin should have CRUD permissions
      expect(userHasPermissionType(nationalAdmin, 'members', 'read')).toBe(true);
      expect(userHasPermissionType(nationalAdmin, 'members', 'crud')).toBe(true);

      // Viewer should have read permissions only
      expect(userHasPermissionType(viewer, 'members', 'read')).toBe(true);
      expect(userHasPermissionType(viewer, 'members', 'crud')).toBe(false);

      // Regular member should not have member management permissions
      expect(userHasPermissionType(regularMember, 'members', 'read')).toBe(false);
      expect(userHasPermissionType(regularMember, 'members', 'crud')).toBe(false);
    });

    test('should correctly integrate with getUserAccessibleRegions function', () => {
      const nationalAdmin = realWorldUsers.nationalMemberAdmin;
      const utrechtCoord = realWorldUsers.utrechtCoordinator;
      const limburgViewer = realWorldUsers.limburgViewer;
      const incompleteUser = realWorldUsers.incompleteRoleMember;

      expect(getUserAccessibleRegions(nationalAdmin)).toEqual(['all']);
      expect(getUserAccessibleRegions(utrechtCoord)).toEqual(['utrecht']);
      expect(getUserAccessibleRegions(limburgViewer)).toEqual(['limburg']);
      expect(getUserAccessibleRegions(incompleteUser)).toEqual([]);
    });
  });
});