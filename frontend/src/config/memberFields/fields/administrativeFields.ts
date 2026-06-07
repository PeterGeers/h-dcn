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
};
