/**
 * Permission Helper Utilities
 * 
 * Utilities for checking field-level permissions and regional access
 */

import { FieldDefinition, HDCNGroup, ConditionalRule } from '../config/memberFields';

/**
 * Check if user can view a specific field
 */
export function canViewField(
  field: FieldDefinition, 
  userRole: HDCNGroup, 
  memberData?: any,
  userRegion?: string
): boolean {
  if (!field.permissions) return true;
  
  // Check basic view permission
  if (!field.permissions.view.includes(userRole)) {
    return false;
  }
  
  // Check regional restrictions
  if (field.permissions.regionalRestricted && userRole === 'Members_Read_All') {
    if (!memberData || !userRegion) return false;
    
    // User can only view members from their own region
    if (memberData.regio !== userRegion) {
      return false;
    }
  }
  
  // Check membership type restrictions
  if (field.permissions.membershipTypeRestricted && memberData) {
    const membershipType = memberData.lidmaatschap;
    if (!field.permissions.membershipTypeRestricted.includes(membershipType)) {
      return false;
    }
  }
  
  // Check conditional visibility
  if (field.showWhen && memberData) {
    const shouldShow = field.showWhen.some(condition => 
      evaluateCondition(condition, memberData)
    );
    if (!shouldShow) return false;
  }
  
  if (field.hideWhen && memberData) {
    const shouldHide = field.hideWhen.some(condition => 
      evaluateCondition(condition, memberData)
    );
    if (shouldHide) return false;
  }
  
  return true;
}

/**
 * Check if user can edit a specific field
 */
export function canEditField(
  field: FieldDefinition, 
  userRole: HDCNGroup, 
  memberData?: any,
  userRegion?: string,
  isOwnRecord?: boolean
): boolean {
  if (!field.permissions) return false;
  
  // Computed fields cannot be edited
  if (field.computed) return false;
  
  // Check if user can view the field first
  if (!canViewField(field, userRole, memberData, userRegion)) {
    return false;
  }
  
  // Check conditional edit permissions first
  if (field.conditionalEdit && memberData) {
    const conditionMet = evaluateCondition(field.conditionalEdit.condition, memberData);
    if (conditionMet) {
      // Use conditional edit permissions
      if (!field.conditionalEdit.permissions.edit.includes(userRole)) {
        return false;
      }
      
      // Check self-service for conditional edit
      if (isOwnRecord && field.conditionalEdit.permissions.selfService) {
        return true;
      }
      
      return field.conditionalEdit.permissions.edit.includes(userRole);
    }
  }
  
  // Check basic edit permission
  if (!field.permissions.edit.includes(userRole)) {
    return false;
  }
  
  // Check self-service permission for own records
  if (isOwnRecord && field.permissions.selfService) {
    return true;
  }
  
  // Check regional restrictions for editing
  if (field.permissions.regionalRestricted && userRole === 'Members_Read_All') {
    if (!memberData || !userRegion) return false;
    
    // User can only edit members from their own region
    if (memberData.regio !== userRegion) {
      return false;
    }
  }
  
  return true;
}

/**
 * Check if user has regional access to a member
 */
export function hasRegionalAccess(
  userRole: HDCNGroup, 
  memberRegion: string, 
  userRegion?: string
): boolean {
  // System admins and full member admins have access to all regions
  if (['System_CRUD_All', 'Members_CRUD_All', 'System_User_Management'].includes(userRole)) {
    return true;
  }
  
  // Regional users (Members_Read_All) can only access their own region
  if (userRole === 'Members_Read_All') {
    return userRegion === memberRegion;
  }
  
  // Other roles have access based on their specific permissions
  return true;
}

/**
 * Get all editable fields for a user role and member data
 */
export function getEditableFields(
  fields: FieldDefinition[], 
  userRole: HDCNGroup, 
  memberData?: any,
  userRegion?: string,
  isOwnRecord?: boolean
): FieldDefinition[] {
  return fields.filter(field => 
    canEditField(field, userRole, memberData, userRegion, isOwnRecord)
  );
}

/**
 * Get all viewable fields for a user role and member data
 */
export function getViewableFields(
  fields: FieldDefinition[], 
  userRole: HDCNGroup, 
  memberData?: any,
  userRegion?: string
): FieldDefinition[] {
  return fields.filter(field => 
    canViewField(field, userRole, memberData, userRegion)
  );
}

/**
 * Check if user can perform a specific action on a member
 */
export function canPerformAction(
  action: 'view' | 'edit' | 'delete' | 'approve',
  userRole: HDCNGroup,
  memberData?: any,
  userRegion?: string,
  isOwnRecord?: boolean
): boolean {
  switch (action) {
    case 'view':
      // Check if user has regional access
      if (memberData && !hasRegionalAccess(userRole, memberData.regio, userRegion)) {
        return false;
      }
      
      // Basic view permissions
      return ['System_CRUD_All', 'Members_Read_All', 'Members_CRUD_All', 'System_User_Management', 'hdcnLeden'].includes(userRole);
    
    case 'edit':
      // Check regional access first
      if (memberData && !hasRegionalAccess(userRole, memberData.regio, userRegion)) {
        return false;
      }
      
      // Self-service editing
      if (isOwnRecord && userRole === 'hdcnLeden') {
        return true;
      }
      
      // Admin edit permissions
      return ['System_CRUD_All', 'Members_CRUD_All', 'System_User_Management'].includes(userRole);
    
    case 'delete':
      // Only system admins can delete
      return userRole === 'System_CRUD_All';
    
    case 'approve':
      // Status approval permissions
      return ['System_CRUD_All', 'Members_CRUD_All', 'Members_Status_Approve'].includes(userRole);
    
    default:
      return false;
  }
}

/**
 * Get permission summary for a user and member
 */
export function getPermissionSummary(
  userRole: HDCNGroup,
  memberData?: any,
  userRegion?: string,
  isOwnRecord?: boolean
): {
  canView: boolean;
  canEdit: boolean;
  canDelete: boolean;
  canApprove: boolean;
  hasRegionalAccess: boolean;
  editableFieldCount: number;
  viewableFieldCount: number;
} {
  const hasRegionalAccessResult = memberData ? 
    hasRegionalAccess(userRole, memberData.regio, userRegion) : true;
  
  return {
    canView: canPerformAction('view', userRole, memberData, userRegion, isOwnRecord),
    canEdit: canPerformAction('edit', userRole, memberData, userRegion, isOwnRecord),
    canDelete: canPerformAction('delete', userRole, memberData, userRegion, isOwnRecord),
    canApprove: canPerformAction('approve', userRole, memberData, userRegion, isOwnRecord),
    hasRegionalAccess: hasRegionalAccessResult,
    editableFieldCount: 0, // Would need field list to calculate
    viewableFieldCount: 0  // Would need field list to calculate
  };
}

/**
 * Check if user can access a specific table context
 */
export function canAccessTableContext(
  contextName: string,
  userRole: HDCNGroup
): boolean {
  // This would integrate with table context permissions
  // For now, basic role checking
  const adminRoles = ['System_CRUD_All', 'Members_CRUD_All', 'Members_Read_All', 'System_User_Management'];
  const memberRoles = ['hdcnLeden'];
  
  switch (contextName) {
    case 'memberOverview':
    case 'memberCompact':
      return [...adminRoles, ...memberRoles].includes(userRole);
    
    case 'motorView':
      return [...adminRoles, ...memberRoles, 'Event_Organizer'].includes(userRole);
    
    case 'communicationView':
      return [...adminRoles, 'Communication_Read_All', 'Communication_CRUD_All'].includes(userRole);
    
    case 'financialView':
      return ['System_CRUD_All', 'Members_CRUD_All', 'Members_Read_All'].includes(userRole);
    
    default:
      return adminRoles.includes(userRole);
  }
}

/**
 * Check if user can access a specific modal context
 */
export function canAccessModalContext(
  contextName: string,
  userRole: HDCNGroup
): boolean {
  const adminRoles = ['System_CRUD_All', 'Members_CRUD_All', 'Members_Read_All', 'System_User_Management'];
  
  switch (contextName) {
    case 'memberView':
    case 'memberQuickView':
    case 'memberRegistration':
      return adminRoles.includes(userRole);
    
    case 'membershipApplication':
      // New applicants don't have roles yet, so this is handled differently
      return ['System_CRUD_All', 'Members_CRUD_All'].includes(userRole);
    
    default:
      return adminRoles.includes(userRole);
  }
}

/**
 * Get filtered member data based on regional restrictions
 */
export function filterMembersByRegion(
  members: any[],
  userRole: HDCNGroup,
  userRegion?: string
): any[] {
  // No filtering needed for system admins
  if (['System_CRUD_All', 'Members_CRUD_All', 'System_User_Management'].includes(userRole)) {
    return members;
  }
  
  // Filter by region for regional users
  if (userRole === 'Members_Read_All' && userRegion) {
    return members.filter(member => member.regio === userRegion);
  }
  
  return members;
}

/**
 * Evaluate a conditional rule against member data
 */
function evaluateCondition(condition: ConditionalRule, memberData: any): boolean {
  const fieldValue = memberData[condition.field];
  
  switch (condition.operator) {
    case 'equals':
      return fieldValue === condition.value;
    case 'not_equals':
      return fieldValue !== condition.value;
    case 'contains':
      return Array.isArray(condition.value) 
        ? condition.value.includes(fieldValue)
        : String(fieldValue).includes(String(condition.value));
    case 'not_contains':
      return Array.isArray(condition.value)
        ? !condition.value.includes(fieldValue)
        : !String(fieldValue).includes(String(condition.value));
    case 'exists':
      return fieldValue !== undefined && fieldValue !== null && fieldValue !== '';
    case 'not_exists':
      return fieldValue === undefined || fieldValue === null || fieldValue === '';
    case 'age_less_than':
      if (condition.field === 'geboortedatum' && fieldValue) {
        const birthDate = new Date(fieldValue);
        const today = new Date();
        const age = today.getFullYear() - birthDate.getFullYear();
        const monthDiff = today.getMonth() - birthDate.getMonth();
        
        if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
          return (age - 1) < condition.value;
        }
        return age < condition.value;
      }
      return false;
    default:
      console.warn(`Unknown condition operator: ${condition.operator}`);
      return true;
  }
}

/**
 * Get role hierarchy level (higher number = more permissions)
 */
export function getRoleLevel(role: HDCNGroup): number {
  const roleLevels: Record<HDCNGroup, number> = {
    'System_CRUD_All': 100,
    'System_User_Management': 90,
    'Members_CRUD_All': 80,
    'Members_Status_Approve': 70,
    'Members_Read_All': 60,
    'National_Chairman': 85,
    'National_Secretary': 75,
    'Communication_CRUD_All': 65,
    'Communication_Read_All': 55,
    'Club_Magazine_Editorial': 50,
    'Event_Organizer': 45,
    'hdcnLeden': 10,
    'Verzoek_lid': 5
  };
  
  return roleLevels[role] || 0;
}

/**
 * Check if user role has higher or equal permissions than required role
 */
export function hasMinimumRole(userRole: HDCNGroup, requiredRole: HDCNGroup): boolean {
  return getRoleLevel(userRole) >= getRoleLevel(requiredRole);
}

/**
 * Get user-friendly role name
 */
export function getRoleName(role: HDCNGroup): string {
  const roleNames: Record<HDCNGroup, string> = {
    'System_CRUD_All': 'Systeem Beheerder',
    'System_User_Management': 'Gebruikers Beheerder',
    'Members_CRUD_All': 'Leden Beheerder',
    'Members_Status_Approve': 'Leden Goedkeurder',
    'Members_Read_All': 'Regio Beheerder',
    'National_Chairman': 'Landelijk Voorzitter',
    'National_Secretary': 'Landelijk Secretaris',
    'Communication_CRUD_All': 'Communicatie Beheerder',
    'Communication_Read_All': 'Communicatie Lezer',
    'Club_Magazine_Editorial': 'Clubblad Redactie',
    'Event_Organizer': 'Evenement Organisator',
    'hdcnLeden': 'Lid',
    'Verzoek_lid': 'Aanvrager'
  };
  
  return roleNames[role] || role;
}