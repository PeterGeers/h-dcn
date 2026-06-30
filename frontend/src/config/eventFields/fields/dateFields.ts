/**
 * Event Field Definitions - Date Fields
 *
 * Fields with group: 'dates'
 * Registration and payment date fields (optional group).
 * Note: start_date and end_date are in coreFields (always visible).
 *
 * Date ordering constraint (validated by backend):
 *   registration_open < registration_close <= start_date <= end_date
 */

import type { FieldDefinition } from '../types';
import { createPermissionConfig } from '../permissions';

export const dateFields: Record<string, FieldDefinition> = {
  registration_open: {
    key: 'registration_open',
    label: 'Registratie open',
    dataType: 'date',
    inputType: 'datetime',
    group: 'dates',
    order: 1,
    required: true,
    validation: [
      { type: 'required', message: 'Registratie open datum is verplicht' },
    ],
    permissions: createPermissionConfig('public', 'admin'),
    displayFormat: 'dd-MM-yyyy HH:mm',
    helpText: 'Datum/tijd vanaf wanneer registratie mogelijk is. Moet vóór registration_close.',
    width: 'medium',
  },

  registration_close: {
    key: 'registration_close',
    label: 'Registratie sluit',
    dataType: 'date',
    inputType: 'datetime',
    group: 'dates',
    order: 2,
    required: true,
    validation: [
      { type: 'required', message: 'Registratie sluit datum is verplicht' },
    ],
    permissions: createPermissionConfig('public', 'admin'),
    displayFormat: 'dd-MM-yyyy HH:mm',
    helpText: 'Datum/tijd tot wanneer registratie mogelijk is. Moet <= start_date.',
    width: 'medium',
  },

  payment_deadline: {
    key: 'payment_deadline',
    label: 'Betaaldeadline',
    dataType: 'date',
    inputType: 'datetime',
    group: 'dates',
    order: 3,
    permissions: createPermissionConfig('admin', 'admin'),
    displayFormat: 'dd-MM-yyyy HH:mm',
    helpText: 'Uiterste betaaldatum. Optioneel — als leeg geldt geen deadline.',
    width: 'medium',
  },
};
