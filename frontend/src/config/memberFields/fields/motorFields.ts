/**
 * Member Field Definitions - Motor Information
 *
 * Fields with group: 'motor'
 */

import type { FieldDefinition } from '../types';
import { createPermissionConfig } from '../permissions';

export const motorFields: Record<string, FieldDefinition> = {
  motormerk: {
    key: 'motormerk',
    label: 'Motormerk',
    dataType: 'enum',
    inputType: 'select',
    group: 'motor',
    order: 1,
    enumOptions: [
      'Harley-Davidson',
      'Indian',
      'Buell',
      'Eigenbouw'
    ],
    permissions: {
      ...createPermissionConfig('member', 'admin', true),
      membershipTypeRestricted: ['Gewoon lid', 'Gezins lid'],
      regionalRestricted: true
    },
    showWhen: [
      { field: 'lidmaatschap', operator: 'equals', value: 'Gewoon lid' },
      { field: 'lidmaatschap', operator: 'equals', value: 'Gezins lid' }
    ],
    placeholder: 'Selecteer motormerk',
    helpText: 'Merk van uw motor (alleen voor gewone leden)',
    width: 'medium'
  },

  motortype: {
    key: 'motortype',
    label: 'Motortype',
    dataType: 'string',
    inputType: 'text',
    group: 'motor',
    order: 2,
    validation: [
      { type: 'max_length', value: 50, message: 'Motortype mag maximaal 50 karakters bevatten' }
    ],
    permissions: {
      ...createPermissionConfig('member', 'admin', true),
      membershipTypeRestricted: ['Gewoon lid', 'Gezins lid'],
      regionalRestricted: true
    },
    showWhen: [
      { field: 'lidmaatschap', operator: 'equals', value: 'Gewoon lid' },
      { field: 'lidmaatschap', operator: 'equals', value: 'Gezins lid' }
    ],
    placeholder: 'Bijv. Sportster, Street Glide',
    helpText: 'Type/model van uw motor',
    width: 'medium'
  },

  bouwjaar: {
    key: 'bouwjaar',
    label: 'Bouwjaar',
    dataType: 'number',
    inputType: 'number',
    group: 'motor',
    order: 3,
    permissions: {
      ...createPermissionConfig('member', 'admin', true),
      membershipTypeRestricted: ['Gewoon lid', 'Gezins lid'],
      regionalRestricted: true
    },
    validation: [
      { type: 'min', value: 1900, message: 'Bouwjaar moet na 1900 zijn' },
      { type: 'max', value: new Date().getFullYear() + 1, message: 'Bouwjaar mag niet in de toekomst liggen' }
    ],
    showWhen: [
      { field: 'lidmaatschap', operator: 'equals', value: 'Gewoon lid' },
      { field: 'lidmaatschap', operator: 'equals', value: 'Gezins lid' }
    ],
    placeholder: 'Bijv. 2015',
    helpText: 'Bouwjaar van uw motor',
    width: 'small'
  },

  kenteken: {
    key: 'kenteken',
    label: 'Kenteken',
    dataType: 'string',
    inputType: 'text',
    group: 'motor',
    order: 4,
    validation: [
      { type: 'max_length', value: 15, message: 'Kenteken mag maximaal 15 karakters bevatten' }
    ],
    permissions: {
      ...createPermissionConfig('member', 'admin', true),
      membershipTypeRestricted: ['Gewoon lid', 'Gezins lid'],
      regionalRestricted: true
    },
    showWhen: [
      { field: 'lidmaatschap', operator: 'equals', value: 'Gewoon lid' },
      { field: 'lidmaatschap', operator: 'equals', value: 'Gezins lid' }
    ],
    placeholder: '12-ABC-3 of internationaal formaat',
    helpText: 'Kenteken van uw motor',
    width: 'medium'
  },
};
