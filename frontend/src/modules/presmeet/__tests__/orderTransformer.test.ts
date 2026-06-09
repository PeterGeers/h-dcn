/**
 * Unit tests for orderTransformer utility.
 *
 * Tests the bidirectional transformation between person-centric form state
 * and the flat order items array used by the backend API.
 *
 * Validates: Requirements 11.5, 11.6, 11.7
 */

import {
  formStateToOrderItems,
  orderItemsToFormState,
  PersonFormState,
} from '../utils/orderTransformer';
import { OrderItem, Product } from '../types/presmeet.types';

// --- Test fixtures ---

const mockProducts: Product[] = [
  {
    product_id: 'prod-meeting',
    name: 'Meeting Ticket PM2027',
    event_id: 'evt-pm2027',
    event_type: 'presmeet',
    price: 50,
    order_item_fields: [
      { id: 'name', label: 'Naam', type: 'text', required: true },
      { id: 'role', label: 'Functie', type: 'text', required: true },
    ],
    variant_schema: null,
    purchase_rules: { min_per_club: 1, max_per_club: 3, order_mode: 'persistent' },
  },
  {
    product_id: 'prod-party',
    name: 'Party Ticket PM2027',
    event_id: 'evt-pm2027',
    event_type: 'presmeet',
    price: 99.5,
    order_item_fields: [
      { id: 'name', label: 'Naam', type: 'text', required: true },
      { id: 'person_type', label: 'Type', type: 'select', required: true, options: ['delegate', 'guest'] },
    ],
    variant_schema: null,
    purchase_rules: { max_per_club: 13, order_mode: 'persistent' },
  },
  {
    product_id: 'prod-tshirt',
    name: 'T-Shirt PM2027',
    event_id: 'evt-pm2027',
    event_type: 'presmeet',
    price: 25,
    order_item_fields: [
      { id: 'person_name', label: 'Naam persoon', type: 'text', required: true },
    ],
    variant_schema: [
      { name: 'Size', values: ['S', 'M', 'L', 'XL', 'XXL'] },
      { name: 'Gender', values: ['Male', 'Female'] },
    ],
    purchase_rules: { max_per_club: 13, order_mode: 'persistent' },
  },
];

describe('orderTransformer', () => {
  describe('formStateToOrderItems', () => {
    it('returns empty array for empty form state', () => {
      const formState: PersonFormState = { persons: [] };
      const result = formStateToOrderItems(formState, mockProducts);
      expect(result).toEqual([]);
    });

    it('transforms a single person with one product into one order item', () => {
      const formState: PersonFormState = {
        persons: [
          {
            name: 'Jan de Vries',
            role: 'President',
            products: [
              { product_id: 'prod-meeting', variant_id: null, fields: {} },
            ],
          },
        ],
      };

      const result = formStateToOrderItems(formState, mockProducts);

      expect(result).toHaveLength(1);
      expect(result[0]).toEqual({
        product_id: 'prod-meeting',
        variant_id: null,
        item_fields_data: { name: 'Jan de Vries', role: 'President' },
        unit_price: 50,
        line_total: 50,
      });
    });

    it('transforms a single person with multiple products into multiple items', () => {
      const formState: PersonFormState = {
        persons: [
          {
            name: 'Alice',
            role: 'Secretary',
            products: [
              { product_id: 'prod-meeting', variant_id: null, fields: {} },
              { product_id: 'prod-party', variant_id: null, fields: { person_type: 'delegate' } },
            ],
          },
        ],
      };

      const result = formStateToOrderItems(formState, mockProducts);

      expect(result).toHaveLength(2);
      expect(result[0].product_id).toBe('prod-meeting');
      expect(result[0].unit_price).toBe(50);
      expect(result[1].product_id).toBe('prod-party');
      expect(result[1].unit_price).toBe(99.5);
      expect(result[1].item_fields_data.person_type).toBe('delegate');
    });

    it('transforms multiple persons into a flat items array', () => {
      const formState: PersonFormState = {
        persons: [
          {
            name: 'Jan',
            role: 'President',
            products: [
              { product_id: 'prod-meeting', variant_id: null, fields: {} },
            ],
          },
          {
            name: 'Piet',
            role: 'Treasurer',
            products: [
              { product_id: 'prod-meeting', variant_id: null, fields: {} },
              { product_id: 'prod-party', variant_id: null, fields: { person_type: 'delegate' } },
            ],
          },
        ],
      };

      const result = formStateToOrderItems(formState, mockProducts);

      expect(result).toHaveLength(3);
      expect(result[0].item_fields_data.name).toBe('Jan');
      expect(result[1].item_fields_data.name).toBe('Piet');
      expect(result[2].item_fields_data.name).toBe('Piet');
    });

    it('includes variant_id when product has variants', () => {
      const formState: PersonFormState = {
        persons: [
          {
            name: 'Jan',
            role: 'President',
            products: [
              {
                product_id: 'prod-tshirt',
                variant_id: 'variant-m-male',
                fields: { person_name: 'Jan' },
              },
            ],
          },
        ],
      };

      const result = formStateToOrderItems(formState, mockProducts);

      expect(result).toHaveLength(1);
      expect(result[0].variant_id).toBe('variant-m-male');
      expect(result[0].unit_price).toBe(25);
    });

    it('merges product-specific fields with person name and role in item_fields_data', () => {
      const formState: PersonFormState = {
        persons: [
          {
            name: 'Alice',
            role: 'Secretary',
            products: [
              {
                product_id: 'prod-party',
                variant_id: null,
                fields: { person_type: 'delegate', dietary: 'vegetarian' },
              },
            ],
          },
        ],
      };

      const result = formStateToOrderItems(formState, mockProducts);

      expect(result[0].item_fields_data).toEqual({
        name: 'Alice',
        role: 'Secretary',
        person_type: 'delegate',
        dietary: 'vegetarian',
      });
    });

    it('uses price 0 for unknown product_id', () => {
      const formState: PersonFormState = {
        persons: [
          {
            name: 'Jan',
            role: 'President',
            products: [
              { product_id: 'unknown-product', variant_id: null, fields: {} },
            ],
          },
        ],
      };

      const result = formStateToOrderItems(formState, mockProducts);

      expect(result[0].unit_price).toBe(0);
      expect(result[0].line_total).toBe(0);
    });
  });

  describe('orderItemsToFormState', () => {
    it('returns empty persons array for empty items', () => {
      const result = orderItemsToFormState([]);
      expect(result.persons).toEqual([]);
    });

    it('groups items by person name', () => {
      const items: OrderItem[] = [
        {
          product_id: 'prod-meeting',
          variant_id: null,
          item_fields_data: { name: 'Jan', role: 'President' },
          unit_price: 50,
          line_total: 50,
        },
        {
          product_id: 'prod-party',
          variant_id: null,
          item_fields_data: { name: 'Jan', role: 'President', person_type: 'delegate' },
          unit_price: 99.5,
          line_total: 99.5,
        },
      ];

      const result = orderItemsToFormState(items);

      expect(result.persons).toHaveLength(1);
      expect(result.persons[0].name).toBe('Jan');
      expect(result.persons[0].role).toBe('President');
      expect(result.persons[0].products).toHaveLength(2);
    });

    it('creates separate person entries for different names', () => {
      const items: OrderItem[] = [
        {
          product_id: 'prod-meeting',
          variant_id: null,
          item_fields_data: { name: 'Jan', role: 'President' },
          unit_price: 50,
          line_total: 50,
        },
        {
          product_id: 'prod-meeting',
          variant_id: null,
          item_fields_data: { name: 'Piet', role: 'Treasurer' },
          unit_price: 50,
          line_total: 50,
        },
      ];

      const result = orderItemsToFormState(items);

      expect(result.persons).toHaveLength(2);
      expect(result.persons[0].name).toBe('Jan');
      expect(result.persons[1].name).toBe('Piet');
    });

    it('extracts product-specific fields (excludes name and role)', () => {
      const items: OrderItem[] = [
        {
          product_id: 'prod-party',
          variant_id: null,
          item_fields_data: { name: 'Alice', role: 'Secretary', person_type: 'delegate' },
          unit_price: 99.5,
          line_total: 99.5,
        },
      ];

      const result = orderItemsToFormState(items);

      expect(result.persons[0].products[0].fields).toEqual({ person_type: 'delegate' });
      // name and role should NOT be in the product fields
      expect(result.persons[0].products[0].fields).not.toHaveProperty('name');
      expect(result.persons[0].products[0].fields).not.toHaveProperty('role');
    });

    it('preserves variant_id in reconstructed form state', () => {
      const items: OrderItem[] = [
        {
          product_id: 'prod-tshirt',
          variant_id: 'variant-l-female',
          item_fields_data: { name: 'Alice', role: 'Secretary', person_name: 'Alice' },
          unit_price: 25,
          line_total: 25,
        },
      ];

      const result = orderItemsToFormState(items);

      expect(result.persons[0].products[0].variant_id).toBe('variant-l-female');
      expect(result.persons[0].products[0].product_id).toBe('prod-tshirt');
    });

    it('handles items with empty name gracefully', () => {
      const items: OrderItem[] = [
        {
          product_id: 'prod-meeting',
          variant_id: null,
          item_fields_data: { role: 'Unknown' },
          unit_price: 50,
          line_total: 50,
        },
      ];

      const result = orderItemsToFormState(items);

      expect(result.persons).toHaveLength(1);
      expect(result.persons[0].name).toBe('');
      expect(result.persons[0].role).toBe('Unknown');
    });
  });

  describe('round-trip transformation', () => {
    it('form → items → form preserves person structure', () => {
      const originalFormState: PersonFormState = {
        persons: [
          {
            name: 'Jan de Vries',
            role: 'President',
            products: [
              { product_id: 'prod-meeting', variant_id: null, fields: {} },
              { product_id: 'prod-party', variant_id: null, fields: { person_type: 'delegate' } },
            ],
          },
          {
            name: 'Piet Jansen',
            role: 'Treasurer',
            products: [
              { product_id: 'prod-meeting', variant_id: null, fields: {} },
            ],
          },
        ],
      };

      const items = formStateToOrderItems(originalFormState, mockProducts);
      const reconstructed = orderItemsToFormState(items);

      expect(reconstructed.persons).toHaveLength(2);
      expect(reconstructed.persons[0].name).toBe('Jan de Vries');
      expect(reconstructed.persons[0].role).toBe('President');
      expect(reconstructed.persons[0].products).toHaveLength(2);
      expect(reconstructed.persons[1].name).toBe('Piet Jansen');
      expect(reconstructed.persons[1].role).toBe('Treasurer');
      expect(reconstructed.persons[1].products).toHaveLength(1);
    });
  });
});
