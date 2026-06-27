/**
 * Order Field Definitions - Financial Fields
 *
 * Fields with group: 'financial'
 * Monetary totals and payment tracking.
 *
 * IMPORTANT: Financial fields MUST be stored as DynamoDB Number type (Decimal).
 * See steering/schema-driven.md §6.
 */

import type { OrderFieldDefinition } from '../types';
import { createPermissionConfig } from '../permissions';

export const financialFields: Record<string, OrderFieldDefinition> = {
  total_amount: {
    key: 'total_amount',
    label: 'Totaalbedrag',
    dataType: 'number',
    inputType: 'number',
    group: 'financial',
    order: 1,
    readOnly: true,
    permissions: createPermissionConfig('owner', 'none'),
    helpText: 'Calculated total: sum of all line items (unit_price × quantity). Stored as DynamoDB Number.',
    width: 'small',
  },

  total_paid: {
    key: 'total_paid',
    label: 'Totaal betaald',
    dataType: 'number',
    inputType: 'number',
    group: 'financial',
    order: 2,
    readOnly: true,
    defaultValue: 0,
    permissions: createPermissionConfig('owner', 'none'),
    helpText: 'Sum of all confirmed payments. Updated by pay_order handler.',
    width: 'small',
  },

  amount_paid: {
    key: 'amount_paid',
    label: 'Bedrag betaald',
    dataType: 'number',
    inputType: 'number',
    group: 'financial',
    order: 3,
    readOnly: true,
    defaultValue: 0,
    permissions: createPermissionConfig('admin', 'none'),
    helpText: 'Alias/legacy field for total_paid — used in some admin views',
    width: 'small',
  },

  payments: {
    key: 'payments',
    label: 'Betalingen',
    dataType: 'list',
    inputType: 'json',
    group: 'financial',
    order: 4,
    readOnly: true,
    permissions: createPermissionConfig('admin', 'none'),
    helpText: 'Array of payment records: {payment_id, amount, date, description, recorded_by, created_at}',
  },
};
