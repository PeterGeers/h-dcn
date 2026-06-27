/**
 * Order Field Definitions - Delegate Fields
 *
 * Fields with group: 'delegates'
 * Delegation / shared access for row-scoped event orders.
 *
 * Row-scoped orders (e.g., club registrations) support a primary and
 * optional secondary delegate who can both manage the order.
 */

import type { OrderFieldDefinition } from '../types';
import { createPermissionConfig } from '../permissions';

export const delegateFields: Record<string, OrderFieldDefinition> = {
  delegates: {
    key: 'delegates',
    label: 'Gemachtigden',
    dataType: 'map',
    inputType: 'json',
    group: 'delegates',
    order: 1,
    permissions: createPermissionConfig('owner', 'owner'),
    helpText: 'Delegate map: {primary, secondary, primary_member_id, secondary_member_id, pending_secondary_email}',
    showWhen: [{ field: 'registry_row_id', operator: 'exists' }],
  },
};
