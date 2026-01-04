/**
 * Field Resolution Engine
 * 
 * Core utilities for resolving fields based on context, user role, and member data
 */

import { 
  MEMBER_FIELDS, 
  MEMBER_TABLE_CONTEXTS, 
  MEMBER_MODAL_CONTEXTS,
  FieldDefinition,
  HDCNGroup,
  ConditionalRule
} from '../config/memberFields';

/**
 * Resolve fields for a specific context
 */
export function resolveFieldsForContext(
  contextName: string, 
  userRole: HDCNGroup, 
  memberData?: any
): FieldDefinition[] {
  // Get context configuration
  const tableContext = MEMBER_TABLE_CONTEXTS[contextName];
  const modalContext = MEMBER_MODAL_CONTEXTS[contextName];
  
  if (!tableContext && !modalContext) {
    throw new Error(`Unknown context: ${contextName}`);
  }
  
  let relevantFields: FieldDefinition[] = [];
  
  if (tableContext) {
    // For table contexts, get fields from column configuration
    relevantFields = tableContext.columns
      .filter(col => col.visible)
      .map(col => MEMBER_FIELDS[col.fieldKey])
      .filter(field => field !== undefined);
  } else if (modalContext) {
    // For modal contexts, get fields from all sections
    const allFieldKeys = modalContext.sections
      .flatMap(section => section.fields)
      .filter(field => field.visible)
      .map(field => field.fieldKey);
    
    relevantFields = allFieldKeys
      .map(key => MEMBER_FIELDS[key])
      .filter(field => field !== undefined);
  }
  
  // Apply permissions
  const permittedFields = applyPermissions(relevantFields, userRole, memberData);
  
  // Apply conditional visibility
  const visibleFields = resolveConditionalVisibility(permittedFields, memberData);
  
  return visibleFields;
}

/**
 * Apply permission filtering to fields
 */
export function applyPermissions(
  fields: FieldDefinition[], 
  userRole: HDCNGroup, 
  memberData?: any
): FieldDefinition[] {
  return fields.filter(field => {
    if (!field.permissions) return true;
    
    // Check basic view permission
    if (!field.permissions.view.includes(userRole)) {
      return false;
    }
    
    // Check regional restrictions
    if (field.permissions.regionalRestricted && userRole === 'Members_Read_All') {
      // TODO: Implement regional boundary checking
      // For now, allow all - this needs user's region vs member's region comparison
      return true;
    }
    
    // Check membership type restrictions
    if (field.permissions.membershipTypeRestricted && memberData) {
      const membershipType = memberData.lidmaatschap;
      if (!field.permissions.membershipTypeRestricted.includes(membershipType)) {
        return false;
      }
    }
    
    return true;
  });
}

/**
 * Resolve conditional visibility based on member data
 */
export function resolveConditionalVisibility(
  fields: FieldDefinition[], 
  memberData?: any
): FieldDefinition[] {
  if (!memberData) return fields;
  
  return fields.filter(field => {
    // Check showWhen conditions
    if (field.showWhen) {
      return field.showWhen.some(condition => evaluateCondition(condition, memberData));
    }
    
    // Check hideWhen conditions
    if (field.hideWhen) {
      return !field.hideWhen.some(condition => evaluateCondition(condition, memberData));
    }
    
    return true;
  });
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
 * Get visible fields for a context (convenience function)
 */
export function getVisibleFields(
  contextName: string, 
  userRole: HDCNGroup, 
  memberData?: any
): FieldDefinition[] {
  return resolveFieldsForContext(contextName, userRole, memberData);
}

/**
 * Check if user can view a specific field
 */
export function canViewField(
  field: FieldDefinition, 
  userRole: HDCNGroup, 
  memberData?: any
): boolean {
  if (!field.permissions) return true;
  
  // Check basic view permission
  if (field.permissions.view.includes(userRole)) {
    return true;
  }
  
  // Check self-service permission for hdcnLeden users and applicants
  if ((userRole === 'hdcnLeden' || userRole === 'Verzoek_lid') && field.permissions.selfService) {
    return true;
  }
  
  return false;
}

/**
 * Check if user can edit a specific field
 */
export function canEditField(
  field: FieldDefinition, 
  userRole: HDCNGroup, 
  memberData?: any
): boolean {
  if (!field.permissions) return false;
  
  // Special case: Verzoek_lid users cannot edit email field (tied to Cognito account)
  if (userRole === 'Verzoek_lid' && field.key === 'email') {
    return false;
  }
  
  // Special case: Verzoek_lid users can edit lidmaatschap field (needed for application)
  if (userRole === 'Verzoek_lid' && field.key === 'lidmaatschap') {
    return true;
  }
  
  // Check basic edit permission
  if (!field.permissions.edit.includes(userRole)) {
    // Check self-service permission for hdcnLeden users and applicants
    if ((userRole === 'hdcnLeden' || userRole === 'Verzoek_lid') && field.permissions.selfService) {
      return true;
    }
    
    // Check conditional edit permissions
    if (field.conditionalEdit && memberData) {
      const conditionMet = evaluateCondition(field.conditionalEdit.condition, memberData);
      if (conditionMet && field.conditionalEdit.permissions.edit.includes(userRole)) {
        return true;
      }
    }
    return false;
  }
  
  return true;
}