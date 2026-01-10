/**
 * Integration Tests for Field-Level Permissions
 * 
 * Tests the integration between memberFields.ts configuration and the permission system
 * to ensure field visibility and editability work correctly in real-world scenarios.
 */

import { 
  MEMBER_FIELDS, 
  MEMBER_TABLE_CONTEXTS, 
  MEMBER_MODAL_CONTEXTS,
  HDCNGroup,
  FieldDefinition,
  PermissionConfig
} from '../memberFields';

import { 
  checkUIPermission,
  userHasPermissionType,
  userHasPermissionWithRegion,
  getUserAccessibleRegions,
  FunctionPermissionManager
} from '../../utils/functionPermissions';

// Mock user objects representing real-world scenarios
const testUsers = {
  // National member administrator - can manage all members nationwide
  nationalMemberAdmin: {
    id: 'nat_admin',
    username: 'nat_admin',
    email: 'national.admin@h-dcn.nl',
    groups: ['Members_CRUD', 'Regio_All'] as HDCNGroup[],
    attributes: {}
  },

  // Regional coordinator for Utrecht - can only manage Utrecht members
  utrechtCoordinator: {
    id: 'utrecht_coord',
    username: 'utrecht_coord',
    email: 'utrecht@h-dcn.nl',
    groups: ['Members_CRUD', 'Regio_Utrecht'] as HDCNGroup[],
    attributes: {}
  },

  // National read-only user - can view all members but not edit
  nationalViewer: {
    id: 'nat_viewer',
    username: 'nat_viewer',
    email: 'viewer@h-dcn.nl',
    groups: ['Members_Read', 'Regio_All'] as HDCNGroup[],
    attributes: {}
  },

  // Regional viewer for Limburg - can only view Limburg members
  limburgViewer: {
    id: 'limburg_viewer',
    username: 'limburg_viewer',
    email: 'limburg.viewer@h-dcn.nl',
    groups: ['Members_Read', 'Regio_Limburg'] as HDCNGroup[],
    attributes: {}
  },

  // Regular member - can only view/edit own data (needs regional role for regional restricted fields)
  regularMember: {
    id: 'regular_member',
    username: 'regular_member',
    email: 'member@h-dcn.nl',
    groups: ['hdcnLeden', 'Regio_Utrecht'] as HDCNGroup[], // Added regional role for testing
    attributes: {}
  },

  // New applicant - limited access during registration (needs regional role for regional restricted fields)
  newApplicant: {
    id: 'new_applicant',
    username: 'new_applicant',
    email: 'applicant@h-dcn.nl',
    groups: ['verzoek_lid', 'Regio_Utrecht'] as HDCNGroup[], // Added regional role for testing
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

  // Regular member without regional access - should be denied regional restricted fields
  memberWithoutRegion: {
    id: 'member_no_region',
    username: 'member_no_region',
    email: 'member.noregion@h-dcn.nl',
    groups: ['hdcnLeden'] as HDCNGroup[], // No regional role
    attributes: {}
  }
};

/**
 * Helper function to simulate field access checking
 * This mimics how the UI would check field permissions
 */
function canUserAccessField(user: any, fieldKey: string, action: 'view' | 'edit' = 'view'): boolean {
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
 * Helper function to check table context access
 */
function canUserAccessTableContext(user: any, contextName: string, action: 'view' | 'export' = 'view'): boolean {
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

describe('Field-Level Permission Integration Tests', () => {

  describe('Personal Information Field Access', () => {
    test('national member admin should have full access to personal fields', () => {
      const user = testUsers.nationalMemberAdmin;
      
      // Should be able to view and edit basic personal information
      expect(canUserAccessField(user, 'voornaam', 'view')).toBe(true);
      expect(canUserAccessField(user, 'voornaam', 'edit')).toBe(true);
      expect(canUserAccessField(user, 'achternaam', 'view')).toBe(true);
      expect(canUserAccessField(user, 'achternaam', 'edit')).toBe(true);
      expect(canUserAccessField(user, 'email', 'view')).toBe(true);
      expect(canUserAccessField(user, 'email', 'edit')).toBe(true);
      
      // Should be able to view sensitive information (regional restricted)
      expect(canUserAccessField(user, 'geboortedatum', 'view')).toBe(true);
      expect(canUserAccessField(user, 'geboortedatum', 'edit')).toBe(true);
      expect(canUserAccessField(user, 'telefoon', 'view')).toBe(true);
      expect(canUserAccessField(user, 'telefoon', 'edit')).toBe(true);
    });

    test('regional coordinator should have limited access to personal fields', () => {
      const user = testUsers.utrechtCoordinator;
      
      // Should be able to view and edit basic personal information
      expect(canUserAccessField(user, 'voornaam', 'view')).toBe(true);
      expect(canUserAccessField(user, 'voornaam', 'edit')).toBe(true);
      expect(canUserAccessField(user, 'achternaam', 'view')).toBe(true);
      expect(canUserAccessField(user, 'achternaam', 'edit')).toBe(true);
      
      // Should be able to view regional restricted fields (has Regio_Utrecht)
      expect(canUserAccessField(user, 'geboortedatum', 'view')).toBe(true);
      expect(canUserAccessField(user, 'geboortedatum', 'edit')).toBe(true);
      expect(canUserAccessField(user, 'telefoon', 'view')).toBe(true);
      expect(canUserAccessField(user, 'telefoon', 'edit')).toBe(true);
    });

    test('national viewer should have read-only access to personal fields', () => {
      const user = testUsers.nationalViewer;
      
      // Should be able to view but not edit personal information
      expect(canUserAccessField(user, 'voornaam', 'view')).toBe(true);
      expect(canUserAccessField(user, 'voornaam', 'edit')).toBe(false);
      expect(canUserAccessField(user, 'achternaam', 'view')).toBe(true);
      expect(canUserAccessField(user, 'achternaam', 'edit')).toBe(false);
      
      // Should be able to view regional restricted fields (has Regio_All)
      expect(canUserAccessField(user, 'geboortedatum', 'view')).toBe(true);
      expect(canUserAccessField(user, 'geboortedatum', 'edit')).toBe(false);
    });

    test('regular member should have very limited access to personal fields', () => {
      const user = testUsers.regularMember;
      
      // Should be able to view basic fields (hdcnLeden in view permissions)
      expect(canUserAccessField(user, 'voornaam', 'view')).toBe(true);
      expect(canUserAccessField(user, 'achternaam', 'view')).toBe(true);
      
      // Should not be able to edit (no Members_CRUD role)
      expect(canUserAccessField(user, 'voornaam', 'edit')).toBe(false);
      expect(canUserAccessField(user, 'achternaam', 'edit')).toBe(false);
      
      // geboortedatum uses admin-level permissions, so hdcnLeden should not have access
      expect(canUserAccessField(user, 'geboortedatum', 'view')).toBe(false);
      
      // telefoon uses member-level permissions + regional restriction, so hdcnLeden with regional role should have access
      expect(canUserAccessField(user, 'telefoon', 'view')).toBe(true);
    });

    test('member without regional access should be denied regional restricted fields', () => {
      const user = testUsers.memberWithoutRegion;
      
      // Should be able to view basic fields (hdcnLeden in view permissions)
      expect(canUserAccessField(user, 'voornaam', 'view')).toBe(true);
      expect(canUserAccessField(user, 'achternaam', 'view')).toBe(true);
      
      // Should not be able to view regional restricted fields (no regional role)
      expect(canUserAccessField(user, 'geboortedatum', 'view')).toBe(false); // Admin-level field
      expect(canUserAccessField(user, 'telefoon', 'view')).toBe(false); // Regional restricted + no regional role
    });
  });

  describe('Membership Information Field Access', () => {
    test('admins should have full access to membership fields', () => {
      const user = testUsers.nationalMemberAdmin;
      
      // Should be able to view and edit membership information
      expect(canUserAccessField(user, 'status', 'view')).toBe(true);
      expect(canUserAccessField(user, 'status', 'edit')).toBe(true);
      expect(canUserAccessField(user, 'lidmaatschap', 'view')).toBe(true);
      expect(canUserAccessField(user, 'lidmaatschap', 'edit')).toBe(true);
      expect(canUserAccessField(user, 'regio', 'view')).toBe(true);
      expect(canUserAccessField(user, 'regio', 'edit')).toBe(true);
      
      // Should be able to view computed fields but not edit them
      expect(canUserAccessField(user, 'lidnummer', 'view')).toBe(true);
      expect(canUserAccessField(user, 'lidnummer', 'edit')).toBe(false);
      expect(canUserAccessField(user, 'jaren_lid', 'view')).toBe(true);
      expect(canUserAccessField(user, 'jaren_lid', 'edit')).toBe(false);
    });

    test('viewers should have read-only access to membership fields', () => {
      const user = testUsers.nationalViewer;
      
      // Should be able to view but not edit membership information
      expect(canUserAccessField(user, 'status', 'view')).toBe(true);
      expect(canUserAccessField(user, 'status', 'edit')).toBe(false);
      expect(canUserAccessField(user, 'lidmaatschap', 'view')).toBe(true);
      expect(canUserAccessField(user, 'lidmaatschap', 'edit')).toBe(false);
      expect(canUserAccessField(user, 'regio', 'view')).toBe(true);
      expect(canUserAccessField(user, 'regio', 'edit')).toBe(false);
    });

    test('new applicants should have limited access during registration', () => {
      const user = testUsers.newApplicant;
      
      // verzoek_lid is now included in the base field view permissions for personal and membership fields
      expect(canUserAccessField(user, 'voornaam', 'view')).toBe(true);
      expect(canUserAccessField(user, 'achternaam', 'view')).toBe(true);
      expect(canUserAccessField(user, 'email', 'view')).toBe(true);
      expect(canUserAccessField(user, 'lidmaatschap', 'view')).toBe(true);
      expect(canUserAccessField(user, 'regio', 'view')).toBe(true);
      
      // They can also edit these fields during registration
      expect(canUserAccessField(user, 'voornaam', 'edit')).toBe(true);
      expect(canUserAccessField(user, 'achternaam', 'edit')).toBe(true);
      expect(canUserAccessField(user, 'email', 'edit')).toBe(true);
      expect(canUserAccessField(user, 'lidmaatschap', 'edit')).toBe(true);
      expect(canUserAccessField(user, 'regio', 'edit')).toBe(true);
      
      // Should not be able to edit status (admin only)
      expect(canUserAccessField(user, 'status', 'view')).toBe(false);
      expect(canUserAccessField(user, 'status', 'edit')).toBe(false);
    });
  });

  describe('Motor Information Field Access', () => {
    test('admins should have full access to motor fields', () => {
      const user = testUsers.nationalMemberAdmin;
      
      // Should be able to view and edit motor information
      expect(canUserAccessField(user, 'motormerk', 'view')).toBe(true);
      expect(canUserAccessField(user, 'motormerk', 'edit')).toBe(true);
      expect(canUserAccessField(user, 'motortype', 'view')).toBe(true);
      expect(canUserAccessField(user, 'motortype', 'edit')).toBe(true);
      expect(canUserAccessField(user, 'bouwjaar', 'view')).toBe(true);
      expect(canUserAccessField(user, 'bouwjaar', 'edit')).toBe(true);
      expect(canUserAccessField(user, 'kenteken', 'view')).toBe(true);
      expect(canUserAccessField(user, 'kenteken', 'edit')).toBe(true);
    });

    test('regular members should have limited access to motor fields', () => {
      const user = testUsers.regularMember;
      
      // Should be able to view motor information (hdcnLeden in view permissions + has regional role)
      expect(canUserAccessField(user, 'motormerk', 'view')).toBe(true);
      expect(canUserAccessField(user, 'motortype', 'view')).toBe(true);
      expect(canUserAccessField(user, 'bouwjaar', 'view')).toBe(true);
      expect(canUserAccessField(user, 'kenteken', 'view')).toBe(true);
      
      // Should not be able to edit (no Members_CRUD role)
      expect(canUserAccessField(user, 'motormerk', 'edit')).toBe(false);
      expect(canUserAccessField(user, 'motortype', 'edit')).toBe(false);
      expect(canUserAccessField(user, 'bouwjaar', 'edit')).toBe(false);
      expect(canUserAccessField(user, 'kenteken', 'edit')).toBe(false);
    });

    test('members without regional access should be denied motor fields', () => {
      const user = testUsers.memberWithoutRegion;
      
      // Should not be able to view motor information (regional restricted + no regional role)
      expect(canUserAccessField(user, 'motormerk', 'view')).toBe(false);
      expect(canUserAccessField(user, 'motortype', 'view')).toBe(false);
      expect(canUserAccessField(user, 'bouwjaar', 'view')).toBe(false);
      expect(canUserAccessField(user, 'kenteken', 'view')).toBe(false);
    });
  });

  describe('Financial Information Field Access', () => {
    test('admins should have full access to financial fields', () => {
      const user = testUsers.nationalMemberAdmin;
      
      // Should be able to view and edit financial information
      expect(canUserAccessField(user, 'bankrekeningnummer', 'view')).toBe(true);
      expect(canUserAccessField(user, 'bankrekeningnummer', 'edit')).toBe(true);
      expect(canUserAccessField(user, 'betaalwijze', 'view')).toBe(true);
      expect(canUserAccessField(user, 'betaalwijze', 'edit')).toBe(true);
    });

    test('viewers should have read-only access to financial fields', () => {
      const user = testUsers.nationalViewer;
      
      // Should be able to view but not edit financial information
      expect(canUserAccessField(user, 'bankrekeningnummer', 'view')).toBe(true);
      expect(canUserAccessField(user, 'bankrekeningnummer', 'edit')).toBe(false);
      expect(canUserAccessField(user, 'betaalwijze', 'view')).toBe(true);
      expect(canUserAccessField(user, 'betaalwijze', 'edit')).toBe(false);
    });

    test('regular members should have limited access to financial fields', () => {
      const user = testUsers.regularMember;
      
      // Should be able to view financial information (hdcnLeden in view permissions + has regional role)
      expect(canUserAccessField(user, 'bankrekeningnummer', 'view')).toBe(true);
      expect(canUserAccessField(user, 'betaalwijze', 'view')).toBe(true);
      
      // Should not be able to edit (no Members_CRUD role)
      expect(canUserAccessField(user, 'bankrekeningnummer', 'edit')).toBe(false);
      expect(canUserAccessField(user, 'betaalwijze', 'edit')).toBe(false);
    });

    test('members without regional access should be denied financial fields', () => {
      const user = testUsers.memberWithoutRegion;
      
      // Should not be able to view financial information (regional restricted + no regional role)
      expect(canUserAccessField(user, 'bankrekeningnummer', 'view')).toBe(false);
      expect(canUserAccessField(user, 'betaalwijze', 'view')).toBe(false);
    });
  });

  describe('Administrative Field Access', () => {
    test('system admin should have access to system fields', () => {
      const user = testUsers.systemAdmin;
      
      // Should be able to view system fields
      expect(canUserAccessField(user, 'created_at', 'view')).toBe(true);
      expect(canUserAccessField(user, 'updated_at', 'view')).toBe(true);
      
      // System fields should not be editable by anyone
      expect(canUserAccessField(user, 'created_at', 'edit')).toBe(false);
      expect(canUserAccessField(user, 'updated_at', 'edit')).toBe(false);
    });

    test('regular users should not have access to system fields', () => {
      const user = testUsers.regularMember;
      
      // Should not be able to view system fields
      expect(canUserAccessField(user, 'created_at', 'view')).toBe(false);
      expect(canUserAccessField(user, 'updated_at', 'view')).toBe(false);
    });

    test('admins should have access to notities field', () => {
      const user = testUsers.nationalMemberAdmin;
      
      // Should be able to view and edit notes
      expect(canUserAccessField(user, 'notities', 'view')).toBe(true);
      expect(canUserAccessField(user, 'notities', 'edit')).toBe(true);
    });

    test('regular members should not have access to notities field', () => {
      const user = testUsers.regularMember;
      
      // Should not be able to view or edit notes
      expect(canUserAccessField(user, 'notities', 'view')).toBe(false);
      expect(canUserAccessField(user, 'notities', 'edit')).toBe(false);
    });
  });

  describe('Table Context Access', () => {
    test('member admins should have access to all table contexts', () => {
      const user = testUsers.nationalMemberAdmin;
      
      // Should have access to all member table contexts
      expect(canUserAccessTableContext(user, 'memberOverview', 'view')).toBe(true);
      expect(canUserAccessTableContext(user, 'memberOverview', 'export')).toBe(true);
      expect(canUserAccessTableContext(user, 'memberCompact', 'view')).toBe(true);
      expect(canUserAccessTableContext(user, 'motorView', 'view')).toBe(true);
      expect(canUserAccessTableContext(user, 'communicationView', 'view')).toBe(true);
      expect(canUserAccessTableContext(user, 'financialView', 'view')).toBe(true);
      expect(canUserAccessTableContext(user, 'financialView', 'export')).toBe(true);
    });

    test('viewers should have read-only access to table contexts', () => {
      const user = testUsers.nationalViewer;
      
      // Should have view access but limited export access
      expect(canUserAccessTableContext(user, 'memberOverview', 'view')).toBe(true);
      expect(canUserAccessTableContext(user, 'memberOverview', 'export')).toBe(true); // Members_Read can export
      expect(canUserAccessTableContext(user, 'memberCompact', 'view')).toBe(true);
      expect(canUserAccessTableContext(user, 'financialView', 'view')).toBe(true);
      expect(canUserAccessTableContext(user, 'financialView', 'export')).toBe(true); // Members_Read can export
    });

    test('regular members should have limited table access', () => {
      const user = testUsers.regularMember;
      
      // Should have access to motor view (hdcnLeden included + has regional role)
      expect(canUserAccessTableContext(user, 'motorView', 'view')).toBe(true);
      
      // Should not have access to admin table contexts
      expect(canUserAccessTableContext(user, 'memberOverview', 'view')).toBe(false);
      expect(canUserAccessTableContext(user, 'financialView', 'view')).toBe(false);
      expect(canUserAccessTableContext(user, 'communicationView', 'view')).toBe(false);
    });

    test('members without regional access should be denied regional restricted tables', () => {
      const user = testUsers.memberWithoutRegion;
      
      // Should not have access to motor view (regional restricted + no regional role)
      expect(canUserAccessTableContext(user, 'motorView', 'view')).toBe(false);
      
      // Should not have access to admin table contexts
      expect(canUserAccessTableContext(user, 'memberOverview', 'view')).toBe(false);
      expect(canUserAccessTableContext(user, 'financialView', 'view')).toBe(false);
      expect(canUserAccessTableContext(user, 'communicationView', 'view')).toBe(false);
    });

    test('users without regional access should be denied regional restricted tables', () => {
      const userWithoutRegion = {
        id: 'no_region',
        username: 'no_region',
        email: 'no.region@h-dcn.nl',
        groups: ['Members_CRUD'] as HDCNGroup[], // Missing regional role
        attributes: {}
      };
      
      // Should be denied access to regional restricted tables
      expect(canUserAccessTableContext(userWithoutRegion, 'memberOverview', 'view')).toBe(false);
      expect(canUserAccessTableContext(userWithoutRegion, 'memberCompact', 'view')).toBe(false);
      expect(canUserAccessTableContext(userWithoutRegion, 'motorView', 'view')).toBe(false);
      expect(canUserAccessTableContext(userWithoutRegion, 'communicationView', 'view')).toBe(false);
    });
  });

  describe('Regional Access Restrictions', () => {
    test('regional users should be restricted to their region', () => {
      const utrechtUser = testUsers.utrechtCoordinator;
      const limburgUser = testUsers.limburgViewer;
      
      // Utrecht user should have Utrecht access
      expect(getUserAccessibleRegions(utrechtUser)).toEqual(['utrecht']);
      
      // Limburg user should have Limburg access
      expect(getUserAccessibleRegions(limburgUser)).toEqual(['limburg']);
      
      // Both should be able to access regional restricted fields within their region
      expect(canUserAccessField(utrechtUser, 'geboortedatum', 'view')).toBe(true);
      expect(canUserAccessField(limburgUser, 'geboortedatum', 'view')).toBe(true);
    });

    test('national users should have access to all regions', () => {
      const nationalUser = testUsers.nationalMemberAdmin;
      
      // Should have access to all regions
      expect(getUserAccessibleRegions(nationalUser)).toEqual(['all']);
      
      // Should be able to access regional restricted fields
      expect(canUserAccessField(nationalUser, 'geboortedatum', 'view')).toBe(true);
      expect(canUserAccessField(nationalUser, 'telefoon', 'view')).toBe(true);
    });
  });

  describe('Permission System Integration', () => {
    test('permission system should correctly validate field access', () => {
      const user = testUsers.nationalMemberAdmin;
      
      // Test integration with permission system
      expect(checkUIPermission(user, 'members', 'read')).toBe(true);
      expect(checkUIPermission(user, 'members', 'write')).toBe(true);
      expect(checkUIPermission(user, 'members', 'read', 'utrecht')).toBe(true);
      expect(checkUIPermission(user, 'members', 'write', 'limburg')).toBe(true);
      
      // Test permission types
      expect(userHasPermissionType(user, 'members', 'read')).toBe(true);
      expect(userHasPermissionType(user, 'members', 'crud')).toBe(true);
      expect(userHasPermissionType(user, 'members', 'export')).toBe(false); // No Members_Export role
    });

    test('permission system should deny access for insufficient permissions', () => {
      const user = testUsers.regularMember;
      
      // Regular member should not have member management permissions
      expect(checkUIPermission(user, 'members', 'read')).toBe(false);
      expect(checkUIPermission(user, 'members', 'write')).toBe(false);
      
      // Should not have permission types
      expect(userHasPermissionType(user, 'members', 'read')).toBe(false);
      expect(userHasPermissionType(user, 'members', 'crud')).toBe(false);
    });
  });

  describe('Self-Service Permissions', () => {
    test('fields with self-service should allow member editing of own data', () => {
      // Test fields that have selfService: true
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
      
      // Verify self-service configuration
      selfServiceFields.forEach(fieldKey => {
        const field = MEMBER_FIELDS[fieldKey];
        expect(field.permissions?.selfService).toBe(true);
        expect(field.permissions?.edit).toContain('Members_CRUD');
      });
    });

    test('administrative fields should not allow self-service', () => {
      const adminOnlyFields = ['status', 'notities', 'created_at', 'updated_at'];
      
      adminOnlyFields.forEach(fieldKey => {
        const field = MEMBER_FIELDS[fieldKey];
        expect(field.permissions?.selfService).not.toBe(true);
      });
    });
  });
});