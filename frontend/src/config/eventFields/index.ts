/**
 * Event Field Configuration System - Barrel Export
 *
 * Single source of truth for all Event table fields.
 * Follows the memberFields pattern for schema-driven development.
 *
 * Usage:
 *   import { EVENT_FIELDS, coreFields, bookingFields } from '../config/eventFields';
 */

import type { FieldDefinition } from './types';
import { coreFields, bookingFields } from './fields';

// ============================================================================
// ASSEMBLED FIELD REGISTRY
// ============================================================================

/**
 * Complete field registry assembled from group-specific partials.
 * This is the single source of truth for Event table fields.
 */
export const EVENT_FIELDS: Record<string, FieldDefinition> = {
  ...coreFields,
  ...bookingFields,
};

// ============================================================================
// RE-EXPORTS FROM SUB-MODULES
// ============================================================================

// Types (all interfaces and type aliases)
export * from './types';

// Permissions (createPermissionConfig, ViewLevel, EditLevel)
export * from './permissions';

// Field partials (for direct access when needed)
export { coreFields, bookingFields } from './fields';
