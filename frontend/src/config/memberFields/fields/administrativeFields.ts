/**
 * Member Field Definitions - Administrative Information
 *
 * Fields with group: 'administrative'
 */

import type { FieldDefinition } from '../types';
import { createPermissionConfig } from '../permissions';

export const administrativeFields: Record<string, FieldDefinition> = {
  aanmeldingsjaar: {
    key: 'aanmeldingsjaar',
    label: 'Aanmeldingsjaar',
    dataType: 'number',
    inputType: 'number',
    group: 'administrative',
    order: 1,
    permissions: createPermissionConfig('admin', 'none', false),
    computed: true,
    computeFrom: 'tijdstempel',
    computeFunction: 'year',
    helpText: 'Automatisch berekend uit Lid sinds datum'
  },

  datum_ondertekening: {
    key: 'datum_ondertekening',
    label: 'Datum ondertekening',
    dataType: 'date',
    inputType: 'date',
    group: 'administrative',
    order: 4,
    permissions: createPermissionConfig('admin', 'admin', false),
    displayFormat: 'dd-MM-yyyy'
  },

  created_at: {
    key: 'created_at',
    label: 'Record aangemaakt',
    dataType: 'date',
    inputType: 'date',
    group: 'administrative',
    order: 5,
    permissions: createPermissionConfig('system', 'none', false),
    displayFormat: 'dd-MM-yyyy HH:mm:ss',
    helpText: 'Technische datum wanneer record is aangemaakt'
  },

  updated_at: {
    key: 'updated_at',
    label: 'Laatst bijgewerkt',
    dataType: 'date',
    inputType: 'date',
    group: 'administrative',
    order: 6,
    permissions: createPermissionConfig('system', 'none', false),
    displayFormat: 'dd-MM-yyyy HH:mm:ss',
    helpText: 'Technische datum wanneer record laatst is bijgewerkt'
  },

  notities: {
    key: 'notities',
    label: 'Notities',
    dataType: 'string',
    inputType: 'textarea',
    group: 'administrative',
    order: 7,
    validation: [
      { type: 'max_length', value: 1000, message: 'Notities mogen maximaal 1000 karakters bevatten' }
    ],
    permissions: createPermissionConfig('admin', 'admin', false),
    helpText: 'Interne notities voor administratieve doeleinden'
  },

  // Welcome pack tracking fields (set by workflow system on activation)
  welcome_pack_status: {
    key: 'welcome_pack_status',
    label: 'Welkomstpakket',
    dataType: 'enum',
    inputType: 'select',
    group: 'administrative',
    order: 10,
    enumOptions: ['pending', 'sent', 'not_applicable'],
    permissions: createPermissionConfig('admin', 'none', false),
    helpText: 'Status van het welkomstpakket (ingesteld door workflow)',
    width: 'medium'
  },

  welcome_pack_sent_date: {
    key: 'welcome_pack_sent_date',
    label: 'Welkomstpakket verzonden op',
    dataType: 'date',
    inputType: 'date',
    group: 'administrative',
    order: 11,
    permissions: createPermissionConfig('admin', 'none', false),
    displayFormat: 'dd-MM-yyyy',
    helpText: 'Datum waarop het welkomstpakket is verzonden',
    showWhen: [
      { field: 'welcome_pack_status', operator: 'equals', value: 'sent' }
    ]
  },

  welcome_pack_sent_by: {
    key: 'welcome_pack_sent_by',
    label: 'Welkomstpakket verzonden door',
    dataType: 'string',
    inputType: 'text',
    group: 'administrative',
    order: 12,
    permissions: createPermissionConfig('admin', 'none', false),
    helpText: 'Admin die het welkomstpakket als verzonden heeft gemarkeerd',
    showWhen: [
      { field: 'welcome_pack_status', operator: 'equals', value: 'sent' }
    ]
  },
};
