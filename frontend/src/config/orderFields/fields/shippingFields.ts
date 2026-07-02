/**
 * Order Field Definitions - Shipping & Delivery Fields
 *
 * Fields with group: 'shipping'
 * Customer info snapshot, delivery address, shipping/pickup tracking.
 *
 * These fields are populated at submit time (snapshot from Member record)
 * and updated during fulfilment (tracking, carrier, timestamps).
 */

import type { OrderFieldDefinition } from '../types';
import { createPermissionConfig } from '../permissions';

export const shippingFields: Record<string, OrderFieldDefinition> = {
  customer_name: {
    key: 'customer_name',
    label: 'Klantnaam',
    dataType: 'string',
    inputType: 'text',
    group: 'shipping',
    order: 1,
    readOnly: true,
    permissions: createPermissionConfig('owner', 'none'),
    helpText: 'Full customer name (voornaam + tussenvoegsel + achternaam), set at submit time.',
    width: 'medium',
  },

  customer_email: {
    key: 'customer_email',
    label: 'E-mail klant',
    dataType: 'string',
    inputType: 'text',
    group: 'shipping',
    order: 2,
    readOnly: true,
    permissions: createPermissionConfig('owner', 'none'),
    helpText: 'Customer email address, copied from member record at submit time.',
    width: 'medium',
  },

  customer_phone: {
    key: 'customer_phone',
    label: 'Telefoon klant',
    dataType: 'string',
    inputType: 'text',
    group: 'shipping',
    order: 3,
    readOnly: true,
    permissions: createPermissionConfig('admin', 'none'),
    helpText: 'Customer phone number (optional), copied from member record at submit time.',
    width: 'small',
  },

  shipping_address: {
    key: 'shipping_address',
    label: 'Afleveradres',
    dataType: 'map',
    inputType: 'json',
    group: 'shipping',
    order: 4,
    readOnly: true,
    permissions: createPermissionConfig('owner', 'none'),
    helpText: 'Delivery address map: {naam, straat, postcode, woonplaats, land}. Pre-filled from member, overridable per order at checkout.',
  },

  pickup_location: {
    key: 'pickup_location',
    label: 'Afhaallocatie',
    dataType: 'string',
    inputType: 'text',
    group: 'shipping',
    order: 5,
    readOnly: true,
    permissions: createPermissionConfig('owner', 'none'),
    helpText: 'Pickup location for event orders (copied from event.location at submit time).',
    width: 'large',
    showWhen: [{ field: 'source_id', operator: 'not_equals', value: 'webshop' }],
  },

  delivery_option: {
    key: 'delivery_option',
    label: 'Leveroptie',
    dataType: 'string',
    inputType: 'text',
    group: 'shipping',
    order: 6,
    readOnly: true,
    permissions: createPermissionConfig('owner', 'none'),
    helpText: 'Selected delivery option label (e.g., "Verzenden per koerier", "Ophalen bij ALV").',
    width: 'medium',
  },

  delivery_cost: {
    key: 'delivery_cost',
    label: 'Verzendkosten',
    dataType: 'number',
    inputType: 'number',
    group: 'shipping',
    order: 7,
    readOnly: true,
    permissions: createPermissionConfig('owner', 'none'),
    helpText: 'Delivery cost in EUR. 0 for pickup options. Included in total_amount.',
    width: 'small',
  },

  tracking_number: {
    key: 'tracking_number',
    label: 'Track & Trace',
    dataType: 'string',
    inputType: 'text',
    group: 'shipping',
    order: 8,
    readOnly: false,
    permissions: createPermissionConfig('admin', 'admin'),
    helpText: 'Shipping tracking number. Required before transitioning to "shipped" status.',
    width: 'medium',
  },

  shipping_carrier: {
    key: 'shipping_carrier',
    label: 'Vervoerder',
    dataType: 'enum',
    inputType: 'select',
    group: 'shipping',
    order: 9,
    readOnly: false,
    enumOptions: ['PostNL', 'DHL', 'DPD', 'Anders'],
    permissions: createPermissionConfig('admin', 'admin'),
    helpText: 'Shipping carrier used for delivery.',
    width: 'small',
  },

  shipped_at: {
    key: 'shipped_at',
    label: 'Verzonden op',
    dataType: 'datetime',
    inputType: 'hidden',
    group: 'shipping',
    order: 10,
    readOnly: true,
    permissions: createPermissionConfig('owner', 'none'),
    helpText: 'ISO 8601 timestamp when order was shipped. Auto-set on transition to "shipped".',
  },

  picked_up_at: {
    key: 'picked_up_at',
    label: 'Afgehaald op',
    dataType: 'datetime',
    inputType: 'hidden',
    group: 'shipping',
    order: 11,
    readOnly: true,
    permissions: createPermissionConfig('owner', 'none'),
    helpText: 'ISO 8601 timestamp when order was picked up at event. Auto-set on transition to "picked_up".',
    showWhen: [{ field: 'source_id', operator: 'not_equals', value: 'webshop' }],
  },

  picked_up_by: {
    key: 'picked_up_by',
    label: 'Uitgereikt door',
    dataType: 'string',
    inputType: 'text',
    group: 'shipping',
    order: 12,
    readOnly: true,
    permissions: createPermissionConfig('admin', 'none'),
    helpText: 'Admin who handed out the order at the event.',
    width: 'medium',
    showWhen: [{ field: 'source_id', operator: 'not_equals', value: 'webshop' }],
  },
};
