/**
 * Member Field Definitions - Address Information
 *
 * Fields with group: 'address'
 */

import type { FieldDefinition } from '../types';
import { createPermissionConfig } from '../permissions';

export const addressFields: Record<string, FieldDefinition> = {
  straat: {
    key: 'straat',
    label: 'Straat',
    dataType: 'string',
    inputType: 'text',
    group: 'address',
    order: 1,
    validation: [
      { type: 'min_length', value: 3, message: 'Straat moet minimaal 3 karakters bevatten' },
      { type: 'max_length', value: 100, message: 'Straat mag maximaal 100 karakters bevatten' }
    ],
    permissions: {
      ...createPermissionConfig('member', 'admin', true),
      regionalRestricted: true
    },
    placeholder: 'Straatnaam en huisnummer',
    helpText: 'Uw volledige adres (straat + huisnummer)',
    width: 'large'
  },

  postcode: {
    key: 'postcode',
    label: 'Postcode',
    dataType: 'string',
    inputType: 'text',
    group: 'address',
    order: 2,
    validation: [
      // Dutch postcode validation (when land = 'Nederland')
      {
        type: 'pattern',
        value: '^[1-9][0-9]{3}\\s?[A-Z]{2}$',
        message: 'Nederlandse postcode moet format 1234AB hebben',
        condition: { field: 'land', operator: 'equals', value: 'Nederland' }
      },
      // International postcode validation (when land ≠ 'Nederland')
      {
        type: 'min_length',
        value: 3,
        message: 'Postcode moet minimaal 3 karakters bevatten',
        condition: { field: 'land', operator: 'not_equals', value: 'Nederland' }
      },
      {
        type: 'max_length',
        value: 15,
        message: 'Postcode mag maximaal 15 karakters bevatten',
        condition: { field: 'land', operator: 'not_equals', value: 'Nederland' }
      }
    ],
    permissions: {
      ...createPermissionConfig('member', 'admin', true),
      regionalRestricted: true
    },
    placeholder: '1234AB of internationaal formaat',
    helpText: 'Uw postcode',
    width: 'small'
  },

  woonplaats: {
    key: 'woonplaats',
    label: 'Woonplaats',
    dataType: 'string',
    inputType: 'text',
    group: 'address',
    order: 3,
    validation: [
      { type: 'min_length', value: 2, message: 'Woonplaats moet minimaal 2 karakters bevatten' },
      { type: 'max_length', value: 50, message: 'Woonplaats mag maximaal 50 karakters bevatten' }
    ],
    permissions: {
      ...createPermissionConfig('member', 'admin', true),
      regionalRestricted: true
    },
    placeholder: 'Plaatsnaam',
    helpText: 'Uw woonplaats',
    width: 'medium'
  },

  land: {
    key: 'land',
    label: 'Land',
    dataType: 'string',
    inputType: 'text',
    group: 'address',
    order: 4,
    validation: [
      { type: 'min_length', value: 2, message: 'Land moet minimaal 2 karakters bevatten' },
      { type: 'max_length', value: 50, message: 'Land mag maximaal 50 karakters bevatten' }
    ],
    permissions: {
      ...createPermissionConfig('member', 'admin', true),
      regionalRestricted: true
    },
    defaultValue: 'Nederland',
    placeholder: 'Bijv. Nederland, België, Duitsland',
    helpText: 'Het land waar u woont',
    width: 'medium'
  },
};
