/**
 * Event Field Definitions - Financial Fields
 *
 * Fields with group: 'financial'
 * Cost tracking, revenue, and participant count for event administration.
 * These fields are admin-only and not shown to participants.
 */

import type { FieldDefinition } from '../types';
import { createPermissionConfig } from '../permissions';

export const financialFields: Record<string, FieldDefinition> = {
  participants: {
    key: 'participants',
    label: 'Aantal deelnemers',
    dataType: 'number',
    inputType: 'number',
    group: 'financial',
    order: 1,
    permissions: createPermissionConfig('admin', 'admin'),
    placeholder: '0',
    helpText: 'Werkelijk aantal deelnemers aan het evenement.',
    width: 'small',
  },

  cost: {
    key: 'cost',
    label: 'Kosten',
    dataType: 'number',
    inputType: 'number',
    group: 'financial',
    order: 2,
    permissions: createPermissionConfig('admin', 'admin'),
    placeholder: '0.00',
    helpText: 'Totale kosten van het evenement in euro.',
    width: 'small',
  },

  revenue: {
    key: 'revenue',
    label: 'Inkomsten',
    dataType: 'number',
    inputType: 'number',
    group: 'financial',
    order: 3,
    permissions: createPermissionConfig('admin', 'admin'),
    placeholder: '0.00',
    helpText: 'Totale inkomsten van het evenement in euro.',
    width: 'small',
  },

  notes: {
    key: 'notes',
    label: 'Opmerkingen',
    dataType: 'string',
    inputType: 'textarea',
    group: 'financial',
    order: 4,
    permissions: createPermissionConfig('admin', 'admin'),
    placeholder: 'Interne notities over kosten, afspraken, etc.',
    helpText: 'Interne opmerkingen (alleen zichtbaar voor admins).',
    width: 'full',
  },
};
