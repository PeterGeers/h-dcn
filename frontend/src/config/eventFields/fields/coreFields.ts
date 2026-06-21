/**
 * Event Field Definitions - Core Fields
 *
 * Fields with group: 'core'
 * These are the fundamental event record attributes.
 */

import type { FieldDefinition } from '../types';
import { createPermissionConfig } from '../permissions';

export const coreFields: Record<string, FieldDefinition> = {
  event_id: {
    key: 'event_id',
    label: 'Event ID',
    dataType: 'string',
    inputType: 'text',
    group: 'core',
    order: 1,
    required: true,
    readOnly: true,
    permissions: createPermissionConfig('admin', 'none'),
    helpText: 'Unique identifier for the event (auto-generated)',
    width: 'medium',
  },

  name: {
    key: 'name',
    label: 'Eventnaam',
    dataType: 'string',
    inputType: 'text',
    group: 'core',
    order: 2,
    required: true,
    validation: [
      { type: 'required', message: 'Eventnaam is verplicht' },
      { type: 'min_length', value: 1, message: 'Eventnaam moet minimaal 1 karakter bevatten' },
      { type: 'max_length', value: 200, message: 'Eventnaam mag maximaal 200 karakters bevatten' },
    ],
    permissions: createPermissionConfig('public', 'admin'),
    placeholder: 'Naam van het evenement',
    helpText: 'Publieke naam van het evenement',
    width: 'large',
  },

  event_type: {
    key: 'event_type',
    label: 'Type evenement',
    dataType: 'string',
    inputType: 'text',
    group: 'core',
    order: 3,
    required: true,
    validation: [
      { type: 'required', message: 'Event type is verplicht' },
    ],
    permissions: createPermissionConfig('admin', 'admin'),
    placeholder: 'Bijv. presmeet, ride, meeting',
    helpText: 'Categorie/type van het evenement',
    width: 'medium',
  },

  status: {
    key: 'status',
    label: 'Status',
    dataType: 'enum',
    inputType: 'select',
    group: 'core',
    order: 4,
    required: true,
    enumOptions: ['draft', 'open', 'closed', 'archived'],
    defaultValue: 'draft',
    permissions: createPermissionConfig('admin', 'admin'),
    helpText: 'Huidige status van het evenement',
    width: 'small',
  },

  start_date: {
    key: 'start_date',
    label: 'Startdatum',
    dataType: 'date',
    inputType: 'date',
    group: 'core',
    order: 5,
    required: true,
    validation: [
      { type: 'required', message: 'Startdatum is verplicht' },
    ],
    permissions: createPermissionConfig('public', 'admin'),
    displayFormat: 'dd-MM-yyyy',
    helpText: 'Startdatum van het evenement',
    width: 'medium',
  },

  end_date: {
    key: 'end_date',
    label: 'Einddatum',
    dataType: 'date',
    inputType: 'date',
    group: 'core',
    order: 6,
    required: true,
    validation: [
      { type: 'required', message: 'Einddatum is verplicht' },
    ],
    permissions: createPermissionConfig('public', 'admin'),
    displayFormat: 'dd-MM-yyyy',
    helpText: 'Einddatum van het evenement',
    width: 'medium',
  },

  slug: {
    key: 'slug',
    label: 'URL Slug',
    dataType: 'string',
    inputType: 'text',
    group: 'core',
    order: 7,
    validation: [
      { type: 'pattern', value: '^[a-z0-9]+(?:-[a-z0-9]+)*$', message: 'Slug mag alleen lowercase letters, cijfers en hyphens bevatten' },
      { type: 'max_length', value: 100, message: 'Slug mag maximaal 100 karakters bevatten' },
    ],
    permissions: createPermissionConfig('public', 'admin'),
    placeholder: 'bijv. presmeet-2026',
    helpText: 'URL-friendly identifier voor routes (bijv. /events/presmeet-2026/register)',
    width: 'medium',
  },
};
