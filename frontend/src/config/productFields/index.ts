/**
 * Product Field Configuration System - Barrel Export
 *
 * Central registry for the Producten DynamoDB table.
 * This is the SINGLE SOURCE OF TRUTH for product field names, types, and validation.
 *
 * Usage:
 *   import { PRODUCT_FIELDS, getProductField, getUpdatableFields } from '../config/productFields';
 */

import type { ProductFieldDefinition } from './types';
import { parentFields, variantFields } from './fields';

// ============================================================================
// ASSEMBLED FIELD REGISTRY
// ============================================================================

/**
 * Complete product field registry — all fields for both parent and variant records.
 */
export const PRODUCT_FIELDS: Record<string, ProductFieldDefinition> = {
  ...parentFields,
  ...variantFields,
};

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Get a single field definition by key.
 */
export const getProductField = (key: string): ProductFieldDefinition | undefined => {
  return PRODUCT_FIELDS[key];
};

/**
 * Get all field keys that are allowed to be updated (editable !== false).
 * Use this to build UPDATABLE_FIELDS lists in backend handlers.
 */
export const getUpdatableFields = (recordType?: 'parent' | 'variant'): string[] => {
  return Object.values(PRODUCT_FIELDS)
    .filter(f => f.editable !== false)
    .filter(f => !recordType || f.recordType === recordType || f.recordType === 'both')
    .map(f => f.key);
};

/**
 * Get all required field keys for a given record type.
 */
export const getRequiredFields = (recordType: 'parent' | 'variant'): string[] => {
  return Object.values(PRODUCT_FIELDS)
    .filter(f => f.required === true)
    .filter(f => f.recordType === recordType || f.recordType === 'both')
    .map(f => f.key);
};

/**
 * Get fields by group.
 */
export const getFieldsByGroup = (group: string, recordType?: 'parent' | 'variant'): ProductFieldDefinition[] => {
  return Object.values(PRODUCT_FIELDS)
    .filter(f => f.group === group)
    .filter(f => !recordType || f.recordType === recordType || f.recordType === 'both')
    .sort((a, b) => a.order - b.order);
};

// ============================================================================
// RE-EXPORTS
// ============================================================================

export * from './types';
export { parentFields, variantFields } from './fields';
