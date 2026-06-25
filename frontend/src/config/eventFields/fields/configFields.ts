/**
 * Event Field Definitions - Configuration Fields
 *
 * Fields with group: 'config'
 * Product association, constraints, and operational settings.
 */

import type { FieldDefinition } from '../types';
import { createPermissionConfig } from '../permissions';

export const configFields: Record<string, FieldDefinition> = {
  product_ids: {
    key: 'product_ids',
    label: 'Producten',
    dataType: 'list',
    inputType: 'multiselect',
    group: 'config',
    order: 1,
    defaultValue: [],
    permissions: createPermissionConfig('admin', 'admin'),
    helpText: 'Lijst van product_ids die aan dit evenement gekoppeld zijn. Bepaalt welke producten zichtbaar zijn in de event-webshop.',
    width: 'full',
  },

  constraints: {
    key: 'constraints',
    label: 'Beperkingen',
    dataType: 'list',
    inputType: 'json',
    group: 'config',
    order: 2,
    defaultValue: [],
    permissions: createPermissionConfig('admin', 'admin'),
    helpText: 'Capaciteitsbeperkingen. Elk item: { key, max, counting_rule }. Counting rules: count_items_by_product, count_distinct_rows, sum_field.',
    width: 'full',
  },
};
