/**
 * Order Field Definitions - Metadata Fields
 *
 * Fields with group: 'metadata'
 * Timestamps and audit trail.
 */

import type { OrderFieldDefinition } from '../types';
import { createPermissionConfig } from '../permissions';

export const metadataFields: Record<string, OrderFieldDefinition> = {
  created_at: {
    key: 'created_at',
    label: 'Aangemaakt op',
    dataType: 'datetime',
    inputType: 'hidden',
    group: 'metadata',
    order: 1,
    required: true,
    readOnly: true,
    permissions: createPermissionConfig('owner', 'none'),
    helpText: 'ISO 8601 timestamp when the order was first created',
  },

  updated_at: {
    key: 'updated_at',
    label: 'Bijgewerkt op',
    dataType: 'datetime',
    inputType: 'hidden',
    group: 'metadata',
    order: 2,
    required: true,
    readOnly: true,
    permissions: createPermissionConfig('admin', 'none'),
    helpText: 'ISO 8601 timestamp of last modification',
  },

  submitted_at: {
    key: 'submitted_at',
    label: 'Ingediend op',
    dataType: 'datetime',
    inputType: 'hidden',
    group: 'metadata',
    order: 3,
    readOnly: true,
    permissions: createPermissionConfig('owner', 'none'),
    helpText: 'ISO 8601 timestamp when the order was submitted (null if still draft)',
  },

  created_by: {
    key: 'created_by',
    label: 'Aangemaakt door',
    dataType: 'string',
    inputType: 'hidden',
    group: 'metadata',
    order: 4,
    readOnly: true,
    permissions: createPermissionConfig('admin', 'none'),
    helpText: 'Email of user who created the order (if created by admin on behalf of member)',
  },
};
