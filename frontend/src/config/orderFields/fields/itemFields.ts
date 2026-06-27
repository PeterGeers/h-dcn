/**
 * Order Field Definitions - Item Fields
 *
 * Fields with group: 'items'
 * Order line items and persons structure.
 *
 * Note: `items` is a list of maps. Each item contains:
 *   - product_id: string
 *   - variant_id: string | null
 *   - quantity: number (webshop) or implicit 1 (event)
 *   - unit_price: number
 *   - line_total: number
 *   - item_fields_data: map (custom fields per product's order_item_fields)
 *   - variant_attributes: map (denormalized from variant record)
 *   - person_index: number (for event booking with persons structure)
 */

import type { OrderFieldDefinition } from '../types';
import { createPermissionConfig } from '../permissions';

export const itemFields: Record<string, OrderFieldDefinition> = {
  items: {
    key: 'items',
    label: 'Bestelregels',
    dataType: 'list',
    inputType: 'json',
    group: 'items',
    order: 1,
    required: true,
    defaultValue: [],
    permissions: createPermissionConfig('owner', 'owner'),
    helpText: 'List of order line items. Each item: {product_id, variant_id, quantity, unit_price, line_total, item_fields_data, variant_attributes}',
  },

  persons: {
    key: 'persons',
    label: 'Personen',
    dataType: 'list',
    inputType: 'json',
    group: 'items',
    order: 2,
    defaultValue: [],
    permissions: createPermissionConfig('owner', 'owner'),
    helpText: 'List of persons for event booking: {name, person_index}. Items reference persons via person_index.',
    showWhen: [{ field: 'source_id', operator: 'not_equals', value: 'webshop' }],
  },
};
