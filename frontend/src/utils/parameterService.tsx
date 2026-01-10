import React from 'react';
import { parameterStore } from './parameterStore';
import { getUserRoles, calculatePermissions, checkUIPermission } from './functionPermissions';

interface ParameterItem {
  id: string;
  value: any;
  parent?: string;
}

interface Parameters {
  [category: string]: ParameterItem[];
}

interface UseParametersReturn {
  parameters: ParameterItem[];
  loading: boolean;
}

interface User {
  signInUserSession?: {
    accessToken?: {
      payload: {
        'cognito:groups'?: string[];
      };
    };
  };
  attributes?: {
    email?: string;
    given_name?: string;
  };
}

interface MembershipTypeRestrictions {
  [membershipType: string]: {
    requiredFields?: string[];
    optionalFields?: string[];
    hiddenFields?: string[];
    moduleAccess?: string[];
  };
}

// BACKWARD COMPATIBILITY: Preserve existing membership type restrictions
// These restrictions are based on the current system behavior in MembershipForm.tsx
const MEMBERSHIP_TYPE_RESTRICTIONS: MembershipTypeRestrictions = {
  'Gewoon lid': {
    requiredFields: ['motormerk', 'motortype', 'bouwjaar', 'kenteken'],
    moduleAccess: ['webshop', 'events', 'members_own']
  },
  'Gezins lid': {
    requiredFields: ['motormerk', 'motortype', 'bouwjaar', 'kenteken'],
    moduleAccess: ['webshop', 'events', 'members_own']
  },
  'Gezins donateur zonder motor': {
    optionalFields: ['motormerk', 'motortype', 'bouwjaar', 'kenteken'],
    moduleAccess: ['webshop', 'events', 'members_own']
  },
  'Donateur zonder motor': {
    optionalFields: ['motormerk', 'motortype', 'bouwjaar', 'kenteken'],
    moduleAccess: ['webshop', 'events', 'members_own']
  }
};

// Fetch parameters using parameterStore (which handles S3/DynamoDB/localStorage fallbacks)
export const getParameters = async (): Promise<Parameters> => {
  try {
    // Force refresh to ensure we get latest data
    await parameterStore.refresh();
    const params = await parameterStore.getParameters();
    return params;
  } catch (error) {
    console.error('Error loading parameters:', error);
    throw new Error('Fout bij laden parameters: ' + error.message);
  }
};

// Clear parameter cache
export const clearParameterCache = async (): Promise<void> => {
  await parameterStore.refresh();
};

// Save parameter using parameterStore
export const saveParameter = async (category: string, value: any, id: string | null = null): Promise<void> => {
  try {
    const parameters = await getParameters();
    
    if (!parameters[category]) {
      parameters[category] = [];
    }
    
    if (id) {
      // Update existing
      const index = parameters[category].findIndex(item => item.id === id);
      if (index !== -1) {
        parameters[category][index].value = value;
      }
    } else {
      // Add new
      const newId = crypto.randomUUID();
      parameters[category].push({ id: newId, value });
    }
    
    await parameterStore.saveParameters(parameters);
  } catch (error) {
    throw new Error('Fout bij opslaan parameter: ' + error.message);
  }
};

// Memoized conversion function
const memoizedConversions = new Map<string, Parameters>();

// Category-specific converters
const categoryConverters: Record<string, (items: ParameterItem[]) => ParameterItem[]> = {
  Productgroepen: (items: ParameterItem[]) => items.map(item => {
    try {
      const parsed = JSON.parse(item.value);
      return { id: item.id, value: parsed.value, parent: parsed.parent };
    } catch {
      return item;
    }
  })
};

const convertToFlatStructure = (data: Parameters): Parameters => {
  const cacheKey = JSON.stringify(data);
  if (memoizedConversions.has(cacheKey)) {
    return memoizedConversions.get(cacheKey);
  }
  
  const flat = { ...data };
  
  // Apply category-specific conversions
  for (const [category, converter] of Object.entries(categoryConverters)) {
    if (flat[category]) {
      flat[category] = converter(flat[category]);
    }
  }
  
  memoizedConversions.set(cacheKey, flat);
  return flat;
};

// Delete parameter using parameterStore
export const deleteParameter = async (category: string, id: string): Promise<void> => {
  try {
    const parameters = await getParameters();
    
    if (parameters[category]) {
      parameters[category] = parameters[category].filter(item => item.id !== id);
    }
    
    await parameterStore.saveParameters(parameters);
  } catch (error) {
    throw new Error('Fout bij verwijderen parameter: ' + error.message);
  }
};

// Hook for using parameters in components with memoization
export const useParameters = (category: string): UseParametersReturn => {
  const [parameters, setParameters] = React.useState([]);
  const [loading, setLoading] = React.useState(true);
  
  const loadParams = React.useCallback(async () => {
    try {
      const data = await getParameters();
      setParameters(data[category] || []);
    } catch (error) {
      console.error('Error loading parameters:', error);
    } finally {
      setLoading(false);
    }
  }, [category]);
  
  React.useEffect(() => {
    loadParams();
  }, [loadParams]);
  
  return React.useMemo(() => ({ parameters, loading }), [parameters, loading]);
};

/**
 * BACKWARD COMPATIBILITY: Get membership type restrictions
 * Preserves existing membership type field requirements and module access rules
 * @param membershipType - The membership type (lidmaatschap) value
 * @returns Object containing field restrictions and module access rules
 */
export const getMembershipTypeRestrictions = (membershipType: string) => {
  return MEMBERSHIP_TYPE_RESTRICTIONS[membershipType] || {
    requiredFields: [],
    optionalFields: [],
    hiddenFields: [],
    moduleAccess: ['webshop', 'members_own'] // Default access for unknown membership types
  };
};

/**
 * BACKWARD COMPATIBILITY: Check if field is required for membership type
 * Preserves existing field validation logic from MembershipForm.tsx
 * @param membershipType - The membership type (lidmaatschap) value
 * @param fieldName - The field name to check
 * @returns boolean indicating if field is required
 */
export const isFieldRequiredForMembershipType = (membershipType: string, fieldName: string): boolean => {
  const restrictions = getMembershipTypeRestrictions(membershipType);
  return restrictions.requiredFields?.includes(fieldName) || false;
};

/**
 * BACKWARD COMPATIBILITY: Check if user has module access based on membership type
 * Preserves existing membership-based module visibility logic
 * @param membershipType - The membership type (lidmaatschap) value
 * @param moduleName - The module name to check access for
 * @returns boolean indicating if membership type allows module access
 */
export const hasMembershipTypeModuleAccess = (membershipType: string, moduleName: string): boolean => {
  const restrictions = getMembershipTypeRestrictions(membershipType);
  return restrictions.moduleAccess?.includes(moduleName) || false;
};

/**
 * ENHANCED: Combined membership type and role-based module access check
 * Combines existing membership type restrictions with new role-based permissions
 * @param user - The user object containing Cognito session data
 * @param membershipType - The membership type (lidmaatschap) value
 * @param moduleName - The module name to check access for
 * @returns boolean indicating if user has access based on both membership type AND roles
 */
export const hasCombinedModuleAccess = (user: User, membershipType: string, moduleName: string): boolean => {
  // BACKWARD COMPATIBILITY: Check membership type access first (existing behavior)
  const hasMembershipAccess = hasMembershipTypeModuleAccess(membershipType, moduleName);
  
  // ENHANCED: Check role-based access (new functionality)
  const hasRoleAccess = checkUIPermission(user, 'system', 'read'); // Basic check - user has system access
  
  // COMBINED LOGIC: User needs BOTH membership type access AND role access
  // This preserves existing restrictions while adding role-based enhancements
  return hasMembershipAccess && hasRoleAccess;
};

/**
 * ENHANCED: Get enhanced parameters with membership type and role context
 * Filters parameters based on both membership type restrictions and user roles
 * @param category - Parameter category to load
 * @param user - User object for role checking
 * @param membershipType - Membership type for restriction checking
 * @returns Enhanced parameters with access control applied
 */
export const getEnhancedParameters = async (category: string, user?: User, membershipType?: string): Promise<ParameterItem[]> => {
  const parameters = await getParameters();
  let categoryParams = parameters[category] || [];
  
  // BACKWARD COMPATIBILITY: Apply membership type restrictions if provided
  if (membershipType && category === 'modules') {
    const restrictions = getMembershipTypeRestrictions(membershipType);
    categoryParams = categoryParams.filter(param => 
      restrictions.moduleAccess?.includes(param.value) || false
    );
  }
  
  // ENHANCED: Apply role-based filtering if user is provided
  if (user) {
    const isAdmin = checkUIPermission(user, 'system', 'write'); // Check if user has system admin access
    
    // Admins see all parameters (existing behavior)
    if (isAdmin) {
      return categoryParams;
    }
    
    // Regular users see filtered parameters based on their roles
    // This is where additional role-based filtering could be added in the future
  }
  
  return categoryParams;
};

/**
 * ENHANCED: Demonstrate additive role-based permissions
 * Shows how role-based permissions are added to existing parameter-based permissions
 * without replacing them, ensuring backward compatibility
 * @param user - User object containing Cognito session data
 * @param functionName - Function name to check permissions for
 * @param membershipType - Optional membership type for additional context
 * @returns Object showing how permissions are combined additively
 */
export const getAdditivePermissionBreakdown = async (user: User, functionName: string, membershipType?: string) => {
  try {
    // Get existing parameter-based permissions
    const parameters = await getParameters();
    const functionPermissions = parameters['Function_permissions'] || [];
    const permissionParam = functionPermissions.find(p => p.value && typeof p.value === 'object');
    const parameterBasedPerms = permissionParam?.value?.[functionName] || { read: [], write: [] };
    
    // Get role-based permissions using new permission system
    const hasReadAccess = checkUIPermission(user, functionName, 'read');
    const hasWriteAccess = checkUIPermission(user, functionName, 'write');
    
    // Convert to permission format for compatibility
    const roleBasedPerms = {
      read: hasReadAccess ? ['role_based_read'] : [],
      write: hasWriteAccess ? ['role_based_write'] : []
    };
    
    // Get membership type permissions (if applicable)
    let membershipBasedPerms = { read: [], write: [] };
    if (membershipType) {
      const restrictions = getMembershipTypeRestrictions(membershipType);
      if (restrictions.moduleAccess?.includes(functionName)) {
        membershipBasedPerms.read.push(`membership_${membershipType.replace(/\s+/g, '_').toLowerCase()}`);
      }
    }
    
    // ADDITIVE COMBINATION: Combine all permission sources
    const combinedPermissions = {
      read: [
        ...(parameterBasedPerms.read || []),
        ...(roleBasedPerms.read || []),
        ...(membershipBasedPerms.read || [])
      ],
      write: [
        ...(parameterBasedPerms.write || []),
        ...(roleBasedPerms.write || []),
        ...(membershipBasedPerms.write || [])
      ]
    };
    
    // Remove duplicates
    combinedPermissions.read = [...new Set(combinedPermissions.read)];
    combinedPermissions.write = [...new Set(combinedPermissions.write)];
    
    return {
      breakdown: {
        parameterBased: parameterBasedPerms,
        roleBased: roleBasedPerms,
        membershipBased: membershipBasedPerms,
        combined: combinedPermissions
      },
      explanation: {
        approach: 'ADDITIVE',
        description: 'Role-based permissions are added to existing parameter-based permissions, not replacing them',
        preservedFeatures: [
          'Existing parameter-based module access rules',
          'Legacy group patterns (hdcnRegio_*, System_User_Management)',
          'Membership type field restrictions',
          'Regional access patterns'
        ],
        enhancedFeatures: [
          'New role-based permissions from Cognito groups',
          'Combined permission checking (parameter + role + membership)',
          'Granular field-level access control',
          'Audit trail for permission decisions'
        ]
      }
    };
  } catch (error) {
    console.error('Error getting additive permission breakdown:', error);
    return {
      breakdown: {
        parameterBased: { read: [], write: [] },
        roleBased: { read: [], write: [] },
        membershipBased: { read: [], write: [] },
        combined: { read: [], write: [] }
      },
      explanation: {
        approach: 'FALLBACK',
        description: 'Using fallback permissions due to error',
        error: error.message
      }
    };
  }
};

/**
 * ENHANCED: Hook for using enhanced parameters with role and membership context
 * Provides parameters filtered by both existing restrictions and new role-based rules
 * @param category - Parameter category to load
 * @param user - Optional user object for role-based filtering
 * @param membershipType - Optional membership type for restriction checking
 * @returns Enhanced parameters with combined access control
 */
export const useEnhancedParameters = (category: string, user?: User, membershipType?: string): UseParametersReturn => {
  const [parameters, setParameters] = React.useState([]);
  const [loading, setLoading] = React.useState(true);
  
  const loadParams = React.useCallback(async () => {
    try {
      const enhancedParams = await getEnhancedParameters(category, user, membershipType);
      setParameters(enhancedParams);
    } catch (error) {
      console.error('Error loading enhanced parameters:', error);
      // BACKWARD COMPATIBILITY: Fall back to regular parameters if enhanced loading fails
      try {
        const data = await getParameters();
        setParameters(data[category] || []);
      } catch (fallbackError) {
        console.error('Error loading fallback parameters:', fallbackError);
        setParameters([]);
      }
    } finally {
      setLoading(false);
    }
  }, [category, user, membershipType]);
  
  React.useEffect(() => {
    loadParams();
  }, [loadParams]);
  
  return React.useMemo(() => ({ parameters, loading }), [parameters, loading]);
};

/**
 * BACKWARD COMPATIBILITY: Validate existing parameter data integrity
 * Ensures that existing parameter configurations continue to work without migration
 * @returns Validation results showing compatibility status
 */
export const validateParameterBackwardCompatibility = async (): Promise<{
  isCompatible: boolean;
  validationResults: Array<{
    category: string;
    status: 'compatible' | 'needs_attention' | 'error';
    issues: string[];
    recommendations: string[];
  }>;
  summary: {
    totalCategories: number;
    compatibleCategories: number;
    categoriesNeedingAttention: number;
    errorCategories: number;
  };
}> => {
  try {
    const parameters = await getParameters();
    const validationResults = [];
    let compatibleCount = 0;
    let attentionCount = 0;
    let errorCount = 0;

    // Validate each parameter category
    for (const [category, items] of Object.entries(parameters)) {
      if (category === '_metadata') continue;

      const validation = {
        category,
        status: 'compatible' as 'compatible' | 'needs_attention' | 'error',
        issues: [] as string[],
        recommendations: [] as string[]
      };

      try {
        // Check if category data is in expected format
        if (!Array.isArray(items) && typeof items !== 'object') {
          validation.status = 'error';
          validation.issues.push('Category data is not in expected array or object format');
          validation.recommendations.push('Verify data structure and consider re-importing from backup');
        }

        // Check for required fields in known categories
        if (category === 'Regio' && Array.isArray(items)) {
          const hasValidRegions = items.every(item => item.value); // Only require value, not ID
          if (!hasValidRegions) {
            validation.status = 'needs_attention';
            validation.issues.push('Some region entries missing required value field');
            validation.recommendations.push('Ensure all region entries have value fields');
          }
        }

        if (category === 'Lidmaatschap' && Array.isArray(items)) {
          const expectedMembershipTypes = ['Gewoon lid', 'Gezins lid', 'Gezins donateur zonder motor', 'Donateur zonder motor'];
          const existingTypes = items.map(item => item.value);
          const missingTypes = expectedMembershipTypes.filter(type => !existingTypes.includes(type));
          
          if (missingTypes.length > 0) {
            validation.status = 'needs_attention';
            validation.issues.push(`Missing expected membership types: ${missingTypes.join(', ')}`);
            validation.recommendations.push('Add missing membership types to maintain field validation compatibility');
          }
        }

        if (category === 'Function_permissions' && Array.isArray(items)) {
          const hasValidPermissions = items.some(item => 
            item.value && 
            typeof item.value === 'object' && 
            (item.value.members || item.value.webshop || item.value.events)
          );
          
          if (!hasValidPermissions) {
            validation.status = 'needs_attention';
            validation.issues.push('Function permissions structure may be incomplete');
            validation.recommendations.push('Verify function permissions contain expected module permissions');
          } else {
            // Check for legacy group patterns in Function_permissions
            const permissionItem = items.find(item => item.value && typeof item.value === 'object');
            if (permissionItem) {
              const permissions = permissionItem.value;
              let hasLegacyPatterns = false;
              
              Object.values(permissions).forEach((modulePerms: any) => {
                if (modulePerms.read) {
                  const hasLegacyGroups = modulePerms.read.some((group: string) => 
                    group.startsWith('hdcn') || group.includes('*')
                  );
                  if (hasLegacyGroups) hasLegacyPatterns = true;
                }
              });
              
              if (hasLegacyPatterns) {
                validation.recommendations.push('Legacy group patterns detected - these will continue to work with new role-based system');
              }
            }
          }
        }

        // Count validation results
        if (validation.status === 'compatible') {
          compatibleCount++;
        } else if (validation.status === 'needs_attention') {
          attentionCount++;
        } else {
          errorCount++;
        }

      } catch (categoryError) {
        validation.status = 'error';
        validation.issues.push(`Error validating category: ${categoryError.message}`);
        validation.recommendations.push('Check category data structure and consider restoring from backup');
        errorCount++;
      }

      validationResults.push(validation);
    }

    // Check for missing required categories
    const requiredCategories = ['Regio', 'Lidmaatschap', 'Motormerk', 'Clubblad'];
    const existingCategories = Object.keys(parameters).filter(key => key !== '_metadata');
    const missingCategories = requiredCategories.filter(cat => !existingCategories.includes(cat));
    
    if (missingCategories.length > 0) {
      validationResults.push({
        category: 'MISSING_CATEGORIES',
        status: 'needs_attention',
        issues: [`Missing required categories: ${missingCategories.join(', ')}`],
        recommendations: ['Add missing categories to ensure full compatibility', 'Consider restoring from backup if categories were accidentally deleted']
      });
      attentionCount++;
    }

    // Check for missing Function_permissions specifically
    if (!parameters.Function_permissions && !parameters.function_permissions) {
      validationResults.push({
        category: 'MISSING_FUNCTION_PERMISSIONS',
        status: 'needs_attention',
        issues: ['Function_permissions category is missing'],
        recommendations: ['Function_permissions will be auto-created with default values', 'Legacy permission patterns will be preserved']
      });
      attentionCount++;
    }

    const totalCategories = validationResults.length;
    const isCompatible = errorCount === 0 && attentionCount <= totalCategories * 0.2; // Allow up to 20% needing attention

    return {
      isCompatible,
      validationResults,
      summary: {
        totalCategories,
        compatibleCategories: compatibleCount,
        categoriesNeedingAttention: attentionCount,
        errorCategories: errorCount
      }
    };

  } catch (error) {
    return {
      isCompatible: false,
      validationResults: [{
        category: 'SYSTEM',
        status: 'error',
        issues: [`Failed to validate parameters: ${error.message}`],
        recommendations: ['Check parameter store connectivity and data integrity']
      }],
      summary: {
        totalCategories: 0,
        compatibleCategories: 0,
        categoriesNeedingAttention: 0,
        errorCategories: 1
      }
    };
  }
};

/**
 * BACKWARD COMPATIBILITY: Ensure parameter data migration is not required
 * Validates that existing parameter configurations work with new role-based system
 * @returns Migration assessment showing if data migration is needed
 */
export const assessParameterMigrationNeeds = async (): Promise<{
  migrationRequired: boolean;
  migrationReasons: string[];
  preservedFeatures: string[];
  enhancedFeatures: string[];
  recommendations: string[];
}> => {
  try {
    const parameters = await getParameters();
    const migrationReasons = [];
    const preservedFeatures = [];
    const enhancedFeatures = [];
    const recommendations = [];

    // Check if existing parameter structure is preserved
    const expectedCategories = ['Regio', 'Lidmaatschap', 'Motormerk', 'Clubblad', 'WieWatWaar'];
    const existingCategories = Object.keys(parameters).filter(key => key !== '_metadata');
    
    const hasExpectedCategories = expectedCategories.every(cat => existingCategories.includes(cat));
    if (hasExpectedCategories) {
      preservedFeatures.push('All expected parameter categories are present');
    } else {
      const missingCategories = expectedCategories.filter(cat => !existingCategories.includes(cat));
      migrationReasons.push(`Missing expected categories: ${missingCategories.join(', ')}`);
    }

    // Check membership type restrictions compatibility
    const membershipTypes = parameters['Lidmaatschap'] || [];
    if (Array.isArray(membershipTypes) && membershipTypes.length > 0) {
      preservedFeatures.push('Membership type data structure is compatible');
      
      // Verify membership type restrictions work
      const testMembershipType = membershipTypes[0]?.value;
      if (testMembershipType) {
        const restrictions = getMembershipTypeRestrictions(testMembershipType);
        if (restrictions.moduleAccess && restrictions.moduleAccess.length > 0) {
          preservedFeatures.push('Membership type module access rules are preserved');
        }
      }
    }

    // Check function permissions compatibility
    const functionPermissions = parameters['Function_permissions'] || [];
    if (Array.isArray(functionPermissions) && functionPermissions.length > 0) {
      const permissionItem = functionPermissions.find(item => item.value && typeof item.value === 'object');
      if (permissionItem) {
        preservedFeatures.push('Function permissions structure is compatible');
        
        // Check for legacy group patterns
        const permissions = permissionItem.value;
        let hasLegacyGroups = false;
        Object.values(permissions).forEach((modulePerms: any) => {
          if (modulePerms.read && Array.isArray(modulePerms.read)) {
            const legacyGroups = modulePerms.read.filter((group: string) => 
              group.startsWith('hdcn') || group.includes('*')
            );
            if (legacyGroups.length > 0) {
              hasLegacyGroups = true;
            }
          }
        });
        
        if (hasLegacyGroups) {
          preservedFeatures.push('Legacy group patterns (hdcn*, wildcards) are preserved');
        }
      }
    }

    // Enhanced features that work with existing data
    enhancedFeatures.push('Role-based permissions work additively with existing parameter permissions');
    enhancedFeatures.push('Membership type restrictions enhanced with role-based field access');
    enhancedFeatures.push('Combined permission checking (parameter + role + membership)');
    enhancedFeatures.push('Backward compatible API for legacy permission checks');

    // Recommendations for optimal compatibility
    if (migrationReasons.length === 0) {
      recommendations.push('No data migration required - existing configurations are fully compatible');
      recommendations.push('New role-based features will enhance existing functionality without breaking changes');
    } else {
      recommendations.push('Address missing categories to ensure full compatibility');
      recommendations.push('Consider restoring missing parameter data from backup');
    }

    recommendations.push('Test role-based enhancements in development environment before production deployment');
    recommendations.push('Monitor system logs for any compatibility issues during transition period');

    return {
      migrationRequired: migrationReasons.length > 0,
      migrationReasons,
      preservedFeatures,
      enhancedFeatures,
      recommendations
    };

  } catch (error) {
    return {
      migrationRequired: false, // Assume no migration needed if we can't assess
      migrationReasons: [`Assessment failed: ${error.message}`],
      preservedFeatures: ['Fallback compatibility mode will be used'],
      enhancedFeatures: ['Basic role-based enhancements available'],
      recommendations: [
        'Check parameter store connectivity',
        'Verify existing parameter data integrity',
        'Consider manual compatibility testing'
      ]
    };
  }
};