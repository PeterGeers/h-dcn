/**
 * Event Field Definitions - Metadata Fields
 *
 * Fields with group: 'metadata'
 * System-managed fields: timestamps and audit trail.
 */

import type { FieldDefinition } from '../types';
import { createPermissionConfig } from '../permissions';

export const metadataFields: Record<string, FieldDefinition> = {
  created_at: {
    key: 'created_at',
    label: 'Aangemaakt op',
    dataType: 'string',
    inputType: 'hidden',
    group: 'metadata',
    order: 1,
    readOnly: true,
    permissions: createPermissionConfig('admin', 'none'),
    helpText: 'ISO timestamp van aanmaak',
    width: 'medium',
  },

  created_by: {
    key: 'created_by',
    label: 'Aangemaakt door',
    dataType: 'string',
    inputType: 'hidden',
    group: 'metadata',
    order: 2,
    readOnly: true,
    permissions: createPermissionConfig('admin', 'none'),
    helpText: 'E-mailadres van de maker',
    width: 'medium',
  },

  updated_at: {
    key: 'updated_at',
    label: 'Bijgewerkt op',
    dataType: 'string',
    inputType: 'hidden',
    group: 'metadata',
    order: 3,
    readOnly: true,
    permissions: createPermissionConfig('admin', 'none'),
    helpText: 'ISO timestamp van laatste wijziging',
    width: 'medium',
  },

  status_changed_at: {
    key: 'status_changed_at',
    label: 'Status gewijzigd op',
    dataType: 'string',
    inputType: 'hidden',
    group: 'metadata',
    order: 4,
    readOnly: true,
    permissions: createPermissionConfig('admin', 'none'),
    helpText: 'ISO timestamp van laatste statuswijziging',
    width: 'medium',
  },

  status_changed_by: {
    key: 'status_changed_by',
    label: 'Status gewijzigd door',
    dataType: 'string',
    inputType: 'hidden',
    group: 'metadata',
    order: 5,
    readOnly: true,
    permissions: createPermissionConfig('admin', 'none'),
    helpText: 'E-mailadres van wie de status heeft gewijzigd',
    width: 'medium',
  },

  google_calendar_event_id: {
    key: 'google_calendar_event_id',
    label: 'Google Calendar Event ID',
    dataType: 'string',
    inputType: 'hidden',
    group: 'metadata',
    order: 6,
    readOnly: true,
    permissions: createPermissionConfig('system', 'none'),
    helpText: 'Sync state — link naar Google Calendar event',
    width: 'medium',
  },

  import_source: {
    key: 'import_source',
    label: 'Import bron',
    dataType: 'enum',
    inputType: 'hidden',
    group: 'metadata',
    order: 7,
    readOnly: true,
    enumOptions: ['manual', 'google', 'json', 'poster', 'stan'],
    permissions: createPermissionConfig('admin', 'none'),
    helpText: 'Hoe dit event is aangemaakt (bron van import)',
    width: 'medium',
  },
};
