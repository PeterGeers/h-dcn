/**
 * Order Field Definitions - Status Fields
 *
 * Fields with group: 'status'
 * Order lifecycle status and payment tracking.
 */

import type { OrderFieldDefinition } from '../types';
import { ALL_ORDER_STATUSES, PAYMENT_STATUSES } from '../types';
import { createPermissionConfig } from '../permissions';

export const statusFields: Record<string, OrderFieldDefinition> = {
  status: {
    key: 'status',
    label: 'Orderstatus',
    dataType: 'enum',
    inputType: 'select',
    group: 'status',
    order: 1,
    required: true,
    enumOptions: ALL_ORDER_STATUSES,
    defaultValue: 'draft',
    permissions: createPermissionConfig('owner', 'admin'),
    helpText: 'Current order lifecycle status. Members see their status; only admins can change it.',
    width: 'medium',
  },

  payment_status: {
    key: 'payment_status',
    label: 'Betaalstatus',
    dataType: 'enum',
    inputType: 'select',
    group: 'status',
    order: 2,
    enumOptions: PAYMENT_STATUSES,
    defaultValue: 'unpaid',
    permissions: createPermissionConfig('owner', 'admin'),
    helpText: 'Payment tracking: unpaid → partial → paid',
    width: 'medium',
  },

  status_history: {
    key: 'status_history',
    label: 'Statusgeschiedenis',
    dataType: 'list',
    inputType: 'json',
    group: 'status',
    order: 3,
    readOnly: true,
    permissions: createPermissionConfig('admin', 'none'),
    helpText: 'Array of {from, to, at, by, source} status transition records',
  },

  version: {
    key: 'version',
    label: 'Versie',
    dataType: 'number',
    inputType: 'hidden',
    group: 'status',
    order: 4,
    required: true,
    readOnly: true,
    defaultValue: 1,
    permissions: createPermissionConfig('admin', 'none'),
    helpText: 'Optimistic locking version — incremented on each update',
  },
};
