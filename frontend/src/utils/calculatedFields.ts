/**
 * Calculated Fields Engine for H-DCN Member System
 * 
 * This module provides a generic system for computing calculated fields based on
 * the memberFields.ts configuration. It implements all the compute functions
 * referenced in the field definitions and provides utilities for processing
 * member data with calculated fields.
 * 
 * Usage:
 * - computeCalculatedFields(member): Process a single member object
 * - computeCalculatedFieldsForArray(members): Process an array of members
 * - getCalculatedFieldValue(member, fieldKey): Get a single calculated field value
 */

import { MEMBER_FIELDS, type FieldDefinition } from '../config/memberFields';
import { Member } from '../types/index';

// ============================================================================
// TYPES
// ============================================================================

// Member type is imported from ../types/index

// ============================================================================
// COMPUTE FUNCTION REGISTRY
// ============================================================================

/**
 * Registry of all compute functions referenced in memberFields.ts
 * Each function takes source values as parameters and returns the computed value
 */
const COMPUTE_FUNCTIONS: Record<string, (...args: any[]) => any> = {
  /**
   * Concatenates name parts with spaces, filtering out empty values
   * Used for: korte_naam field
   * @param voornaam - First name
   * @param tussenvoegsel - Middle name/prefix (optional)
   * @param achternaam - Last name
   * @returns Combined full name
   */
  concatenateName: (
    voornaam: string = '',
    tussenvoegsel: string = '',
    achternaam: string = ''
  ): string => {
    return [voornaam, tussenvoegsel, achternaam]
      .filter(Boolean) // Remove empty/null/undefined values
      .join(' ')
      .trim();
  },

  /**
   * Calculates current age from birth date with proper leap year and month/day handling
   * Used for: leeftijd field
   * @param geboortedatum - Birth date in ISO format (YYYY-MM-DD)
   * @returns Age in years, or null if invalid date
   */
  calculateAge: (geboortedatum: string): number | null => {
    if (!geboortedatum) return null;
    
    const birthDate = new Date(geboortedatum);
    
    // Check if date is valid
    if (isNaN(birthDate.getTime())) return null;
    
    const today = new Date();
    
    // Basic year difference
    let age = today.getFullYear() - birthDate.getFullYear();
    
    // Adjust for month and day precision
    const monthDiff = today.getMonth() - birthDate.getMonth();
    
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
      age--;
    }
    
    return Math.max(0, age); // Ensure non-negative age
  },

  /**
   * Extracts day and month from birth date in Dutch format
   * Used for: verjaardag field
   * @param geboortedatum - Birth date in ISO format (YYYY-MM-DD)
   * @returns Formatted birthday string (e.g., "september 26"), or empty string if invalid
   */
  extractBirthday: (geboortedatum: string): string => {
    if (!geboortedatum) return '';
    
    const date = new Date(geboortedatum);
    
    // Check if date is valid
    if (isNaN(date.getTime())) return '';
    
    // Dutch month names
    const months = [
      'januari', 'februari', 'maart', 'april', 'mei', 'juni',
      'juli', 'augustus', 'september', 'oktober', 'november', 'december'
    ];
    
    const monthName = months[date.getMonth()];
    const day = date.getDate();
    
    return `${monthName} ${day}`;
  },

  /**
   * Calculates years of membership from start date to current date
   * Used for: jaren_lid field
   * @param ingangsdatum - Membership start date in ISO format (YYYY-MM-DD)
   * @returns Years of membership, or null if invalid date
   */
  yearsDifference: (ingangsdatum: string): number | null => {
    if (!ingangsdatum) return null;
    
    const startDate = new Date(ingangsdatum);
    
    // Check if date is valid
    if (isNaN(startDate.getTime())) return null;
    
    const today = new Date();
    
    // Basic year difference
    let years = today.getFullYear() - startDate.getFullYear();
    
    // Adjust for month and day precision
    const monthDiff = today.getMonth() - startDate.getMonth();
    
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < startDate.getDate())) {
      years--;
    }
    
    return Math.max(0, years); // Ensure non-negative years
  },

  /**
   * Extracts year from date
   * Used for: aanmeldingsjaar field
   * @param date - Date in ISO format (YYYY-MM-DD)
   * @returns Year as number, or null if invalid date
   */
  year: (date: string): number | null => {
    if (!date) return null;
    const dateObj = new Date(date);
    
    // Check if date is valid
    if (isNaN(dateObj.getTime())) return null;
    
    return dateObj.getFullYear();
  },

  /**
   * Auto-generates next available member number
   * Used for: lidnummer field
   * Note: This is a placeholder implementation. In practice, this would need
   * access to existing members to calculate the next available number.
   * @returns Next member number (placeholder implementation returns 0)
   */
  nextLidnummer: (): number => {
    // This is a placeholder implementation
    // In practice, this would need access to existing members to find the highest
    // existing lidnummer and return highest + 1
    console.warn('nextLidnummer function called - this requires access to existing member data');
    return 0;
  }
};

// ============================================================================
// CORE COMPUTATION FUNCTIONS
// ============================================================================

/**
 * Computes a single calculated field value based on field definition
 * @param field - Field definition from memberFields.ts
 * @param member - Member object containing source data
 * @returns Computed field value
 */
export function computeFieldValue(field: FieldDefinition, member: Member): any {
  // If not a computed field, return the existing value
  if (!field.computed || !field.computeFunction) {
    return member[field.key];
  }

  // Get the compute function
  const computeFunction = COMPUTE_FUNCTIONS[field.computeFunction];
  if (!computeFunction) {
    console.warn(`Compute function '${field.computeFunction}' not found for field '${field.key}'`);
    return member[field.key];
  }

  // Prepare source values
  let sourceValues: any[];
  
  if (Array.isArray(field.computeFrom)) {
    // Multiple source fields
    sourceValues = field.computeFrom.map(sourceKey => member[sourceKey]);
  } else if (field.computeFrom) {
    // Single source field
    sourceValues = [member[field.computeFrom]];
  } else {
    // No source fields (e.g., nextLidnummer)
    sourceValues = [];
  }

  try {
    // Call the compute function with source values
    return computeFunction(...sourceValues);
  } catch (error) {
    console.error(`Error computing field '${field.key}':`, error);
    return member[field.key]; // Return original value on error
  }
}

/**
 * Processes a single member object and computes all calculated fields
 * @param member - Member object to process
 * @returns Member object with calculated fields computed
 */
export function computeCalculatedFields(member: Member): Member {
  if (!member) return member;

  // Create a copy to avoid mutating the original
  const processedMember = { ...member };

  // Process all computed fields from MEMBER_FIELDS
  Object.values(MEMBER_FIELDS)
    .filter(field => field.computed)
    .forEach(field => {
      processedMember[field.key] = computeFieldValue(field, member);
    });

  return processedMember;
}

/**
 * Processes an array of member objects and computes calculated fields for each
 * @param members - Array of member objects to process
 * @returns Array of member objects with calculated fields computed
 */
export function computeCalculatedFieldsForArray(members: Member[]): Member[] {
  if (!Array.isArray(members)) return members;
  
  return members.map(member => computeCalculatedFields(member));
}

/**
 * Gets the value of a specific calculated field for a member
 * @param member - Member object
 * @param fieldKey - Key of the field to compute
 * @returns Computed field value
 */
export function getCalculatedFieldValue(member: Member, fieldKey: string): any {
  const field = MEMBER_FIELDS[fieldKey];
  if (!field) {
    console.warn(`Field definition not found for key: ${fieldKey}`);
    return member[fieldKey];
  }

  if (!field.computed) {
    // Not a computed field, return existing value
    return member[fieldKey];
  }

  return computeFieldValue(field, member);
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Gets all computed field keys from memberFields.ts
 * @returns Array of computed field keys
 */
export function getComputedFieldKeys(): string[] {
  return Object.values(MEMBER_FIELDS)
    .filter(field => field.computed)
    .map(field => field.key);
}

/**
 * Checks if a field is computed
 * @param fieldKey - Field key to check
 * @returns True if field is computed
 */
export function isComputedField(fieldKey: string): boolean {
  const field = MEMBER_FIELDS[fieldKey];
  return field?.computed === true;
}

/**
 * Gets the source fields for a computed field
 * @param fieldKey - Computed field key
 * @returns Array of source field keys
 */
export function getSourceFields(fieldKey: string): string[] {
  const field = MEMBER_FIELDS[fieldKey];
  if (!field?.computed || !field.computeFrom) return [];

  if (Array.isArray(field.computeFrom)) {
    return field.computeFrom;
  } else {
    return [field.computeFrom];
  }
}

/**
 * Validates that all required compute functions are implemented
 * @returns Object with validation results
 */
export function validateComputeFunctions(): {
  valid: boolean;
  missing: string[];
  implemented: string[];
} {
  const computedFields = Object.values(MEMBER_FIELDS).filter(field => field.computed);
  const requiredFunctions = [...new Set(computedFields.map(field => field.computeFunction).filter(Boolean))];
  const implementedFunctions = Object.keys(COMPUTE_FUNCTIONS);
  const missing = requiredFunctions.filter(func => !implementedFunctions.includes(func!));

  return {
    valid: missing.length === 0,
    missing,
    implemented: implementedFunctions
  };
}

// ============================================================================
// BACKWARDS COMPATIBILITY HELPERS
// ============================================================================

/**
 * Helper function for backwards compatibility with existing manual calculations
 * Provides the same interface as existing manual name concatenation
 * @param member - Member object
 * @returns Full name string
 */
export function getMemberFullName(member: Member): string {
  return getCalculatedFieldValue(member, 'korte_naam') || '';
}

/**
 * Helper function for backwards compatibility with existing manual calculations
 * Provides the same interface as existing manual age calculation
 * @param member - Member object
 * @returns Age in years, or null if no valid birth date
 */
export function getMemberAge(member: Member): number | null {
  return getCalculatedFieldValue(member, 'leeftijd');
}

/**
 * Helper function to get member birthday in Dutch format
 * @param member - Member object
 * @returns Birthday string (e.g., "september 26")
 */
export function getMemberBirthday(member: Member): string {
  return getCalculatedFieldValue(member, 'verjaardag') || '';
}

/**
 * Helper function to get years of membership
 * @param member - Member object
 * @returns Years of membership, or null if no valid start date
 */
export function getMemberYearsOfMembership(member: Member): number | null {
  return getCalculatedFieldValue(member, 'jaren_lid');
}

/**
 * Helper function to get membership start year
 * @param member - Member object
 * @returns Year of membership start, or null if no valid start date
 */
export function getMemberStartYear(member: Member): number | null {
  return getCalculatedFieldValue(member, 'aanmeldingsjaar');
}

// ============================================================================
// DEVELOPMENT UTILITIES
// ============================================================================

/**
 * Development utility to test all compute functions with sample data
 * @returns Test results
 */
export function testComputeFunctions(): Record<string, any> {
  const sampleMember: Member = {
    id: 'test-sample',
    name: 'Jan van der Berg',
    email: 'jan.vandenberg@example.com',
    region: 'Noord-Holland',
    membershipType: 'individual',
    voornaam: 'Jan',
    tussenvoegsel: 'van der',
    achternaam: 'Berg',
    geboortedatum: '1978-09-26',
    tijdstempel: '2018-04-01',
    ingangsdatum: '2018-04-01'
  };

  const results: Record<string, any> = {};
  
  // Test each computed field
  Object.values(MEMBER_FIELDS)
    .filter(field => field.computed)
    .forEach(field => {
      try {
        results[field.key] = computeFieldValue(field, sampleMember);
      } catch (error) {
        results[field.key] = `ERROR: ${error}`;
      }
    });

  return results;
}

/**
 * Development utility to log computed field information
 */
export function logComputedFieldsInfo(): void {
  console.group('🔧 Calculated Fields Engine Info');
  
  const validation = validateComputeFunctions();
  console.log('✅ Validation:', validation);
  
  const computedFields = getComputedFieldKeys();
  console.log('📊 Computed Fields:', computedFields);
  
  const testResults = testComputeFunctions();
  console.log('🧪 Test Results:', testResults);
  
  console.groupEnd();
}