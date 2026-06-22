/**
 * Event Field Configuration System - Barrel Export
 *
 * Single source of truth for all Event table fields.
 * Follows the memberFields pattern for schema-driven development.
 *
 * Field groups:
 *   - core: identity, type, location, slug (the essential basics)
 *   - dates: start/end, registration open/close, payment deadline
 *   - config: product_ids, constraints
 *   - financial: participants, cost, revenue, notes (admin-only)
 *   - landing_page: full landing page map + sub-field documentation
 *   - booking: password gate, registry config, claims
 *   - metadata: timestamps, audit trail
 *
 * Usage:
 *   import { EVENT_FIELDS, getEventField, getRequiredFields } from '../config/eventFields';
 */

import type { FieldDefinition } from './types';
import {
  coreFields,
  dateFields,
  configFields,
  financialFields,
  landingPageFields,
  bookingFields,
  metadataFields,
} from './fields';

// ============================================================================
// ASSEMBLED FIELD REGISTRY
// ============================================================================

/**
 * Complete field registry assembled from group-specific partials.
 * This is the single source of truth for Event table fields.
 */
export const EVENT_FIELDS: Record<string, FieldDefinition> = {
  ...coreFields,
  ...dateFields,
  ...configFields,
  ...financialFields,
  ...landingPageFields,
  ...bookingFields,
  ...metadataFields,
};

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Get a single field definition by key.
 */
export const getEventField = (key: string): FieldDefinition | undefined => {
  return EVENT_FIELDS[key];
};

/**
 * Get all required field keys.
 */
export const getRequiredFields = (): string[] => {
  return Object.values(EVENT_FIELDS)
    .filter(f => f.required === true)
    .map(f => f.key);
};

/**
 * Get all updatable field keys (not readOnly, not hidden).
 */
export const getUpdatableFields = (): string[] => {
  return Object.values(EVENT_FIELDS)
    .filter(f => f.readOnly !== true && f.inputType !== 'hidden')
    .map(f => f.key);
};

/**
 * Get fields by group.
 */
export const getFieldsByGroup = (group: string): FieldDefinition[] => {
  return Object.values(EVENT_FIELDS)
    .filter(f => f.group === group)
    .sort((a, b) => a.order - b.order);
};

// ============================================================================
// RE-EXPORTS FROM SUB-MODULES
// ============================================================================

// Types (all interfaces and type aliases)
export * from './types';

// Permissions (createPermissionConfig, ViewLevel, EditLevel)
export * from './permissions';

// Field partials (for direct access when needed)
export {
  coreFields,
  dateFields,
  configFields,
  financialFields,
  landingPageFields,
  bookingFields,
  metadataFields,
} from './fields';
