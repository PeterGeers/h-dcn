/**
 * Unit tests for priceCalculator utility.
 *
 * Tests total calculation, product-based calculation, outstanding balance,
 * and currency formatting.
 *
 * Validates: Requirements 11.5, 11.6, 11.7
 */

import {
  calculateTotal,
  calculateTotalFromProducts,
  calculateOutstanding,
  formatCurrency,
} from '../utils/priceCalculator';
import { OrderItem, Product } from '../types/presmeet.types';

// --- Test fixtures ---

const mockProducts: Product[] = [
  {
    product_id: 'prod-meeting',
    name: 'Meeting Ticket',
    channel: 'presmeet',
    event_type: 'presmeet',
    price: 50,
    order_item_fields: [],
    variant_schema: null,
    purchase_rules: { max_per_club: 3 },
  },
  {
    product_id: 'prod-party',
    name: 'Party Ticket',
    channel: 'presmeet',
    event_type: 'presmeet',
    price: 99.5,
    order_item_fields: [],
    variant_schema: null,
    purchase_rules: { max_per_club: 13 },
  },
  {
    product_id: 'prod-tshirt',
    name: 'T-Shirt',
    channel: 'presmeet',
    event_type: 'presmeet',
    price: 25,
    order_item_fields: [],
    variant_schema: [{ name: 'Size', values: ['S', 'M', 'L'] }],
    purchase_rules: { max_per_club: 13 },
  },
];

function makeItem(overrides: Partial<OrderItem> = {}): OrderItem {
  return {
    product_id: 'prod-meeting',
    variant_id: null,
    item_fields_data: { name: 'Test', role: 'Member' },
    unit_price: 50,
    line_total: 50,
    ...overrides,
  };
}

describe('priceCalculator', () => {
  describe('calculateTotal', () => {
    it('returns 0 for empty items array', () => {
      expect(calculateTotal([])).toBe(0);
    });

    it('sums line_total for a single item', () => {
      const items = [makeItem({ unit_price: 50, line_total: 50 })];
      expect(calculateTotal(items)).toBe(50);
    });

    it('sums line_total across multiple items', () => {
      const items = [
        makeItem({ unit_price: 50, line_total: 50 }),
        makeItem({ product_id: 'prod-party', unit_price: 99.5, line_total: 99.5 }),
        makeItem({ product_id: 'prod-tshirt', unit_price: 25, line_total: 25 }),
      ];
      expect(calculateTotal(items)).toBe(174.5);
    });

    it('falls back to unit_price when line_total is 0', () => {
      const items = [makeItem({ unit_price: 50, line_total: 0 })];
      expect(calculateTotal(items)).toBe(50);
    });

    it('rounds result to 2 decimal places', () => {
      const items = [
        makeItem({ unit_price: 33.33, line_total: 33.33 }),
        makeItem({ unit_price: 33.33, line_total: 33.33 }),
        makeItem({ unit_price: 33.33, line_total: 33.33 }),
      ];
      expect(calculateTotal(items)).toBe(99.99);
    });

    it('handles floating point precision correctly', () => {
      // 0.1 + 0.2 = 0.30000000000000004 in JS
      const items = [
        makeItem({ unit_price: 0.1, line_total: 0.1 }),
        makeItem({ unit_price: 0.2, line_total: 0.2 }),
      ];
      expect(calculateTotal(items)).toBe(0.3);
    });
  });

  describe('calculateTotalFromProducts', () => {
    it('returns 0 for empty items array', () => {
      expect(calculateTotalFromProducts([], mockProducts)).toBe(0);
    });

    it('uses line_total when available', () => {
      const items = [makeItem({ unit_price: 50, line_total: 50 })];
      expect(calculateTotalFromProducts(items, mockProducts)).toBe(50);
    });

    it('falls back to unit_price when line_total is 0', () => {
      const items = [makeItem({ unit_price: 50, line_total: 0 })];
      expect(calculateTotalFromProducts(items, mockProducts)).toBe(50);
    });

    it('falls back to product price when both line_total and unit_price are 0', () => {
      const items = [makeItem({ product_id: 'prod-party', unit_price: 0, line_total: 0 })];
      expect(calculateTotalFromProducts(items, mockProducts)).toBe(99.5);
    });

    it('returns 0 for unknown product with zero prices', () => {
      const items = [makeItem({ product_id: 'unknown', unit_price: 0, line_total: 0 })];
      expect(calculateTotalFromProducts(items, mockProducts)).toBe(0);
    });

    it('sums correctly with mixed price sources', () => {
      const items = [
        makeItem({ product_id: 'prod-meeting', unit_price: 50, line_total: 50 }),
        makeItem({ product_id: 'prod-party', unit_price: 0, line_total: 0 }), // falls back to product price 99.5
        makeItem({ product_id: 'prod-tshirt', unit_price: 25, line_total: 0 }), // uses unit_price
      ];
      expect(calculateTotalFromProducts(items, mockProducts)).toBe(174.5);
    });
  });

  describe('calculateOutstanding', () => {
    it('returns full amount when nothing is paid', () => {
      expect(calculateOutstanding(450, 0)).toBe(450);
    });

    it('returns difference when partially paid', () => {
      expect(calculateOutstanding(450, 200)).toBe(250);
    });

    it('returns 0 when fully paid', () => {
      expect(calculateOutstanding(450, 450)).toBe(0);
    });

    it('returns 0 when overpaid (never negative)', () => {
      expect(calculateOutstanding(450, 500)).toBe(0);
    });

    it('handles decimal amounts correctly', () => {
      expect(calculateOutstanding(99.99, 50.5)).toBe(49.49);
    });
  });

  describe('formatCurrency', () => {
    it('formats zero as EUR', () => {
      const result = formatCurrency(0);
      // nl-NL format uses € symbol and comma for decimals
      expect(result).toContain('€');
      expect(result).toContain('0,00');
    });

    it('formats integer amount with 2 decimals', () => {
      const result = formatCurrency(50);
      expect(result).toContain('€');
      expect(result).toContain('50,00');
    });

    it('formats decimal amount with 2 decimals', () => {
      const result = formatCurrency(99.5);
      expect(result).toContain('€');
      expect(result).toContain('99,50');
    });

    it('formats large amounts correctly', () => {
      const result = formatCurrency(1234.56);
      expect(result).toContain('€');
      expect(result).toContain('1.234,56');
    });

    it('formats negative amounts', () => {
      const result = formatCurrency(-25);
      expect(result).toContain('€');
      expect(result).toContain('25,00');
    });
  });
});
