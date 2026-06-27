/**
 * Order Field Definitions - Identity Fields
 *
 * Fields with group: 'identity'
 * Primary key and order identification attributes.
 */

import type { OrderFieldDefinition } from '../types';
import { createPermissionConfig } from '../permissions';

export const identityFields: Record<string, OrderFieldDefinition> = {
  order_id: {
    key: 'order_id',
    label: 'Order ID',
    dataType: 'string',
    inputType: 'hidden',
    group: 'identity',
    order: 1,
    required: true,
    readOnly: true,
    permissions: createPermissionConfig('owner', 'none'),
    helpText: 'UUID primary key — auto-generated',
  },

  order_number: {
    key: 'order_number',
    label: 'Ordernummer',
    dataType: 'string',
    inputType: 'text',
    group: 'identity',
    order: 2,
    readOnly: true,
    permissions: createPermissionConfig('owner', 'none'),
    helpText: 'Human-readable order number, generated at submission (e.g., ORD-2026-0001)',
    width: 'medium',
  },

  invoice_number: {
    key: 'invoice_number',
    label: 'Factuurnummer',
    dataType: 'string',
    inputType: 'text',
    group: 'identity',
    order: 3,
    readOnly: false,
    permissions: createPermissionConfig('admin', 'admin'),
    helpText: 'Invoice number assigned by admin, generated via Counters table',
    width: 'medium',
  },

  member_id: {
    key: 'member_id',
    label: 'Lid ID',
    dataType: 'string',
    inputType: 'hidden',
    group: 'identity',
    order: 4,
    required: true,
    readOnly: true,
    permissions: createPermissionConfig('admin', 'none'),
    helpText: 'UUID of the member who owns this order',
  },

  user_email: {
    key: 'user_email',
    label: 'E-mailadres',
    dataType: 'string',
    inputType: 'text',
    group: 'identity',
    order: 5,
    readOnly: true,
    permissions: createPermissionConfig('admin', 'none'),
    helpText: 'Email address of the ordering member',
    width: 'medium',
  },
};
