/**
 * Order Field Definitions - Source Fields
 *
 * Fields with group: 'source'
 * Identifies the origin of an order (webshop or event) and related context.
 */

import type { OrderFieldDefinition } from '../types';
import { createPermissionConfig } from '../permissions';

export const sourceFields: Record<string, OrderFieldDefinition> = {
  source_id: {
    key: 'source_id',
    label: 'Bron ID',
    dataType: 'string',
    inputType: 'hidden',
    group: 'source',
    order: 1,
    required: true,
    readOnly: true,
    permissions: createPermissionConfig('admin', 'none'),
    helpText: 'Source identifier: "webshop" for webshop orders, or event UUID for event orders',
  },

  event_id: {
    key: 'event_id',
    label: 'Event ID',
    dataType: 'string',
    inputType: 'hidden',
    group: 'source',
    order: 2,
    readOnly: true,
    permissions: createPermissionConfig('admin', 'none'),
    helpText: 'Event UUID (same as source_id for event orders, absent for webshop)',
    showWhen: [{ field: 'source_id', operator: 'not_equals', value: 'webshop' }],
  },

  event_type: {
    key: 'event_type',
    label: 'Event type',
    dataType: 'string',
    inputType: 'text',
    group: 'source',
    order: 3,
    readOnly: true,
    permissions: createPermissionConfig('admin', 'none'),
    helpText: 'Type of event (e.g., PresMeet, Openingsrit)',
    showWhen: [{ field: 'source_id', operator: 'not_equals', value: 'webshop' }],
  },

  registry_row_id: {
    key: 'registry_row_id',
    label: 'Registry Row ID',
    dataType: 'string',
    inputType: 'hidden',
    group: 'source',
    order: 4,
    readOnly: true,
    permissions: createPermissionConfig('admin', 'none'),
    helpText: 'Row-scoped order: identifies the registry row (e.g., club registration row)',
    showWhen: [{ field: 'registry_row_id', operator: 'exists' }],
  },

  registry_row_label: {
    key: 'registry_row_label',
    label: 'Club / Groepsnaam',
    dataType: 'string',
    inputType: 'text',
    group: 'source',
    order: 5,
    readOnly: true,
    permissions: createPermissionConfig('owner', 'none'),
    helpText: 'Display name of the registry row (e.g., club name)',
    showWhen: [{ field: 'registry_row_id', operator: 'exists' }],
    width: 'medium',
  },

  registry_row_logo_url: {
    key: 'registry_row_logo_url',
    label: 'Logo URL',
    dataType: 'string',
    inputType: 'text',
    group: 'source',
    order: 6,
    readOnly: true,
    permissions: createPermissionConfig('owner', 'none'),
    helpText: 'Logo URL for the registry row',
    showWhen: [{ field: 'registry_row_id', operator: 'exists' }],
  },
};
