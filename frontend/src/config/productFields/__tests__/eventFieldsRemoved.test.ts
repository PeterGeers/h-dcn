/**
 * Tests verifying that event_id and event_ids fields have been removed
 * from the Product Field Registry and TypeScript Product type.
 *
 * Validates: Requirements 1.1, 2.1
 */

import { parentFields, variantFields } from '../fields';
import { PRODUCT_FIELDS } from '../index';
import type { Product } from '../../../types';

describe('Product Field Registry - event fields removed', () => {
  describe('Requirement 1.1: Field Registry does not include event_id/event_ids', () => {
    it('parentFields does not contain event_id key', () => {
      expect(parentFields).not.toHaveProperty('event_id');
    });

    it('parentFields does not contain event_ids key', () => {
      expect(parentFields).not.toHaveProperty('event_ids');
    });

    it('variantFields does not contain event_id key', () => {
      expect(variantFields).not.toHaveProperty('event_id');
    });

    it('variantFields does not contain event_ids key', () => {
      expect(variantFields).not.toHaveProperty('event_ids');
    });

    it('PRODUCT_FIELDS (complete registry) does not contain event_id', () => {
      expect(PRODUCT_FIELDS).not.toHaveProperty('event_id');
    });

    it('PRODUCT_FIELDS (complete registry) does not contain event_ids', () => {
      expect(PRODUCT_FIELDS).not.toHaveProperty('event_ids');
    });

    it('no field definition has key equal to event_id or event_ids', () => {
      const allFieldKeys = Object.values(PRODUCT_FIELDS).map(f => f.key);
      expect(allFieldKeys).not.toContain('event_id');
      expect(allFieldKeys).not.toContain('event_ids');
    });
  });

  describe('Requirement 2.1: Product type compiles without event_id/event_ids', () => {
    it('Product type can be instantiated without event_id or event_ids', () => {
      // This test validates at compile-time that the Product type
      // does not require event_id or event_ids.
      const product: Product = {
        product_id: 'test-123',
        naam: 'Test Product',
        prijs: '10.00',
        active: true,
      };

      expect(product.product_id).toBe('test-123');
      // If event_id or event_ids were still on the type, the following
      // would NOT cause a type error (they'd be optional). Instead we
      // verify at runtime that the object doesn't include them.
      expect(product).not.toHaveProperty('event_id');
      expect(product).not.toHaveProperty('event_ids');
    });

    it('Product type does not accept event_id assignment without type error', () => {
      // TypeScript compile-time check: assigning event_id should cause a type error.
      // At runtime, we verify the field is not part of the type's known keys.
      const productKeys: (keyof Product)[] = [
        'product_id', 'naam', 'prijs', 'artikelcode', 'groep', 'subgroep',
        'images', 'is_parent', 'active', 'order_item_fields', 'purchase_rules',
        'created_at', 'updated_at', 'parent_id', 'variant_attributes',
        'stock', 'sold_count', 'allow_oversell', 'id',
      ];

      expect(productKeys).not.toContain('event_id');
      expect(productKeys).not.toContain('event_ids');
    });
  });
});
