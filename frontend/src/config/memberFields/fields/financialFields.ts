/**
 * Member Field Definitions - Financial Information
 *
 * Fields with group: 'financial'
 */

import type { FieldDefinition } from '../types';
import { createPermissionConfig } from '../permissions';

export const financialFields: Record<string, FieldDefinition> = {
  bankrekeningnummer: {
    key: 'bankrekeningnummer',
    label: 'IBAN',
    dataType: 'string',
    inputType: 'iban',
    group: 'financial',
    order: 1,
    validation: [
      {
        type: 'required',
        message: 'IBAN is verplicht voor dit lidmaatschapstype',
        condition: { field: 'lidmaatschap', operator: 'contains', value: ['Gewoon lid', 'Gezins lid', 'Donateur', 'Gezins donateur', 'Sponsor'] }
      },
      { type: 'iban', message: 'Voer een geldig IBAN nummer in' },
      { type: 'min_length', value: 15, message: 'IBAN moet minimaal 15 karakters bevatten' },
      { type: 'max_length', value: 34, message: 'IBAN mag maximaal 34 karakters bevatten' }
    ],
    permissions: {
      ...createPermissionConfig('member', 'admin', true),
      regionalRestricted: true
    },
    placeholder: 'NL12ABCD0123456789 of internationaal IBAN',
    helpText: 'Internationaal bankrekeningnummer voor incasso doeleinden'
  },

  betaalwijze: {
    key: 'betaalwijze',
    label: 'Betaalwijze',
    dataType: 'enum',
    inputType: 'select',
    group: 'financial',
    order: 2,
    enumOptions: ['Incasso', 'Overmaking'],
    validation: [
      {
        type: 'required',
        message: 'Betaalwijze is verplicht',
        condition: { field: 'member_id', operator: 'not_exists' } // Only required for new applications
      }
    ],
    permissions: {
      ...createPermissionConfig('member', 'admin', true),
      regionalRestricted: true
    },
    placeholder: 'Selecteer betaalwijze',
    helpText: 'Hoe wilt u uw contributie betalen?',
    width: 'medium'
  },
};
