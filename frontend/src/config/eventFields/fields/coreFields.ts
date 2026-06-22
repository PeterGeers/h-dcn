/**
 * Event Field Definitions - Core Fields
 *
 * Fields with group: 'core'
 * These are the fundamental event record attributes (identity + type).
 */

import type { FieldDefinition } from '../types';
import { createPermissionConfig } from '../permissions';
import { EVENT_CATEGORIES, EVENT_TYPES, PARTICIPATION_MODES, EVENT_REGIOS } from '../eventTypes';

export const coreFields: Record<string, FieldDefinition> = {
  event_id: {
    key: 'event_id',
    label: 'Event ID',
    dataType: 'string',
    inputType: 'hidden',
    group: 'core',
    order: 1,
    required: true,
    readOnly: true,
    permissions: createPermissionConfig('admin', 'none'),
    helpText: 'UUID primary key — auto-generated',
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
    dataType: 'enum',
    inputType: 'select',
    group: 'core',
    order: 3,
    required: true,
    enumOptions: [...EVENT_TYPES],
    validation: [
      { type: 'required', message: 'Event type is verplicht' },
    ],
    permissions: createPermissionConfig('admin', 'admin'),
    placeholder: 'Selecteer type',
    helpText: 'Specifiek type evenement (bijv. PresMeet, ALV, Openingsrit).',
    width: 'medium',
  },

  event_category: {
    key: 'event_category',
    label: 'Categorie',
    dataType: 'enum',
    inputType: 'select',
    group: 'core',
    order: 4,
    required: true,
    enumOptions: [...EVENT_CATEGORIES],
    validation: [
      { type: 'required', message: 'Event categorie is verplicht' },
    ],
    permissions: createPermissionConfig('admin', 'admin'),
    placeholder: 'Selecteer categorie',
    helpText: 'Hoofdcategorie: Vergaderingen, Rallies, Ritten, of Overig. Wordt automatisch afgeleid van event_type.',
    width: 'medium',
  },

  participation: {
    key: 'participation',
    label: 'Deelname',
    dataType: 'enum',
    inputType: 'select',
    group: 'core',
    order: 5,
    required: true,
    enumOptions: [...PARTICIPATION_MODES],
    defaultValue: 'open',
    validation: [
      { type: 'required', message: 'Deelname modus is verplicht' },
    ],
    permissions: createPermissionConfig('admin', 'admin'),
    placeholder: 'Open of besloten',
    helpText: 'Open: iedereen kan deelnemen. Besloten: alleen leden of genodigden.',
    width: 'medium',
  },

  linked_regio: {
    key: 'linked_regio',
    label: 'Gekoppelde regio',
    dataType: 'enum',
    inputType: 'select',
    group: 'core',
    order: 6,
    required: true,
    enumOptions: [...EVENT_REGIOS],
    validation: [
      { type: 'required', message: 'Regio is verplicht' },
    ],
    permissions: createPermissionConfig('admin', 'admin'),
    placeholder: 'Selecteer regio',
    helpText: 'Regio waaraan dit evenement gekoppeld is. Bepaalt wie het event mag bewerken: regio-vertegenwoordiger of Regio_All/Events_CRUD.',
    width: 'medium',
  },

  status: {
    key: 'status',
    label: 'Status',
    dataType: 'enum',
    inputType: 'select',
    group: 'core',
    order: 7,
    required: true,
    enumOptions: ['draft', 'open', 'closed', 'archived'],
    defaultValue: 'draft',
    readOnly: true,
    permissions: createPermissionConfig('admin', 'admin'),
    helpText: 'Huidige status. Transitions: draft→open→closed→(open). Beheerd via status-endpoint.',
    width: 'small',
  },

  location: {
    key: 'location',
    label: 'Locatie',
    dataType: 'string',
    inputType: 'text',
    group: 'core',
    order: 8,
    validation: [
      { type: 'max_length', value: 300, message: 'Locatie mag maximaal 300 karakters bevatten' },
    ],
    permissions: createPermissionConfig('public', 'admin'),
    placeholder: 'Bijv. Clubhuis H-DCN, Amsterdam',
    helpText: 'Locatie van het evenement',
    width: 'large',
  },

  slug: {
    key: 'slug',
    label: 'URL Slug',
    dataType: 'string',
    inputType: 'text',
    group: 'core',
    order: 9,
    validation: [
      { type: 'pattern', value: '^[a-z0-9]+(?:-[a-z0-9]+)*$', message: 'Slug mag alleen lowercase letters, cijfers en hyphens bevatten' },
      { type: 'max_length', value: 100, message: 'Slug mag maximaal 100 karakters bevatten' },
    ],
    permissions: createPermissionConfig('public', 'admin'),
    placeholder: 'bijv. presmeet-2026',
    helpText: 'URL-friendly identifier voor routes (bijv. /events/presmeet-2026/register)',
    width: 'medium',
  },

  poster_url: {
    key: 'poster_url',
    label: 'Poster / Afbeelding',
    dataType: 'string',
    inputType: 'text',
    group: 'core',
    order: 10,
    permissions: createPermissionConfig('public', 'admin'),
    placeholder: 'https://...',
    helpText: 'URL naar poster of afbeelding van het evenement (PDF, PNG, JPG). Wordt geüpload naar S3.',
    width: 'large',
  },

  start_date: {
    key: 'start_date',
    label: 'Startdatum',
    dataType: 'date',
    inputType: 'date',
    group: 'core',
    order: 11,
    required: true,
    validation: [
      { type: 'required', message: 'Startdatum is verplicht' },
    ],
    permissions: createPermissionConfig('public', 'admin'),
    displayFormat: 'dd-MM-yyyy',
    helpText: 'Startdatum van het evenement. Moet >= registration_close.',
    width: 'medium',
  },

  end_date: {
    key: 'end_date',
    label: 'Einddatum',
    dataType: 'date',
    inputType: 'date',
    group: 'core',
    order: 12,
    required: true,
    validation: [
      { type: 'required', message: 'Einddatum is verplicht' },
    ],
    permissions: createPermissionConfig('public', 'admin'),
    displayFormat: 'dd-MM-yyyy',
    helpText: 'Einddatum van het evenement. Moet >= start_date.',
    width: 'medium',
  },
};
