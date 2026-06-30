/**
 * Order Field Configuration System - Barrel Export
 *
 * Single source of truth for all Orders DynamoDB table fields.
 * Follows the eventFields pattern for schema-driven development.
 *
 * Field groups:
 *   - identity: order_id, order_number, invoice_number, member_id, user_email
 *   - source: source_id, event_id, event_type, registry_row_*
 *   - status: status, payment_status, status_history, version
 *   - financial: total_amount, total_paid, amount_paid, payments
 *   - items: items[], persons[]
 *   - delegates: delegates map (row-scoped orders)
 *   - metadata: created_at, updated_at, submitted_at, created_by
 *
 * Architecture decision: Orders replace Carts table.
 * See: docs/decisions/orders-replace-carts.md
 *
 * Usage:
 *   import { ORDER_FIELDS, getOrderField, getRequiredFields } from '../config/orderFields';
 */

import type { OrderFieldDefinition } from './types';
import {
  identityFields,
  sourceFields,
  statusFields,
  financialFields,
  itemFields,
  delegateFields,
  metadataFields,
} from './fields';

// ============================================================================
// ASSEMBLED FIELD REGISTRY
// ============================================================================

/**
 * Complete field registry assembled from group-specific partials.
 * This is the single source of truth for Orders table fields.
 */
export const ORDER_FIELDS: Record<string, OrderFieldDefinition> = {
  ...identityFields,
  ...sourceFields,
  ...statusFields,
  ...financialFields,
  ...itemFields,
  ...delegateFields,
  ...metadataFields,
};

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Get a single field definition by key.
 */
export const getOrderField = (key: string): OrderFieldDefinition | undefined => {
  return ORDER_FIELDS[key];
};

/**
 * Get all required field keys.
 */
export const getRequiredFields = (): string[] => {
  return Object.values(ORDER_FIELDS)
    .filter(f => f.required === true)
    .map(f => f.key);
};

/**
 * Get all updatable field keys (not readOnly, not hidden).
 */
export const getUpdatableFields = (): string[] => {
  return Object.values(ORDER_FIELDS)
    .filter(f => f.readOnly !== true && f.inputType !== 'hidden')
    .map(f => f.key);
};

/**
 * Get fields by group.
 */
export const getFieldsByGroup = (group: string): OrderFieldDefinition[] => {
  return Object.values(ORDER_FIELDS)
    .filter(f => f.group === group)
    .sort((a, b) => a.order - b.order);
};

/**
 * Get all field keys that are admin-only (not viewable by owner/members).
 */
export const getAdminOnlyFields = (): string[] => {
  return Object.values(ORDER_FIELDS)
    .filter(f => f.permissions && !f.permissions.view.includes('hdcnLeden'))
    .map(f => f.key);
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
  identityFields,
  sourceFields,
  statusFields,
  financialFields,
  itemFields,
  delegateFields,
  metadataFields,
} from './fields';
