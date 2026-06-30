/**
 * Event Field Definitions - Configuration Fields
 *
 * Fields with group: 'config'
 * Product association, constraints, and operational settings.
 */

import type { FieldDefinition } from '../types';
import { createPermissionConfig } from '../permissions';
import { ORDER_FLOWS } from '../eventTypes';

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

  order_flow: {
    key: 'order_flow',
    label: 'Bestelflow',
    dataType: 'enum',
    inputType: 'select',
    group: 'config',
    order: 2,
    required: true,
    enumOptions: [...ORDER_FLOWS],
    defaultValue: 'catalog',
    permissions: createPermissionConfig('admin', 'admin'),
    helpText: 'Catalog: webshop-achtige productlijst. Attendee: per deelnemer artikelen selecteren (registry-based).',
    width: 'medium',
  },

  allowed_membership_types: {
    key: 'allowed_membership_types',
    label: 'Toegestane lidmaatschapstypen',
    dataType: 'list',
    inputType: 'multiselect',
    group: 'config',
    order: 3,
    defaultValue: [],
    permissions: createPermissionConfig('admin', 'admin'),
    helpText: 'Alleen relevant bij participation=members. Leeg = alle typen toegestaan. Vul in om te beperken tot specifieke lidmaatschapstypen.',
    width: 'full',
    showWhen: [{ field: 'participation', operator: 'equals', value: 'members' }],
  },

  constraints: {
    key: 'constraints',
    label: 'Beperkingen',
    dataType: 'list',
    inputType: 'json',
    group: 'config',
    order: 4,
    defaultValue: [],
    permissions: createPermissionConfig('admin', 'admin'),
    helpText: 'Capaciteitsbeperkingen. Elk item: { key, max, counting_rule }. Counting rules: count_items_by_product, count_distinct_rows, sum_field.',
    width: 'full',
  },
};
