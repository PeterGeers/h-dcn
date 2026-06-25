/**
 * useEffectiveLimits Hook Unit Tests
 *
 * Tests for the effective limits calculation logic, focusing on
 * max_per_order reading from purchase_rules.
 *
 * Validates: Requirements 5.5
 */

import { Product, PurchaseRules } from '../types/eventBooking.types';
import { PersonFormState } from '../utils/orderTransformer';

/**
 * Pure calculation function extracted from useEffectiveLimits hook logic.
 * This mirrors the products.map() block in the hook.
 */
function calculateEffectiveLimit(
  product: Product,
  formState: PersonFormState,
  soldCount: number
): { remaining: number; totalCapacity: number; isExhausted: boolean } {
  const maxPerOrder = product.purchase_rules?.max_per_order;
  const maxPerEvent = product.purchase_rules?.max_per_event;

  // Calculate order quantity for this product
  let orderQty = 0;
  for (const person of formState.persons) {
    for (const pp of person.products) {
      if (pp.product_id === product.product_id) {
        orderQty += 1;
      }
    }
  }

  // Per-order remaining
  const perOrderRemaining =
    maxPerOrder !== undefined ? maxPerOrder - orderQty : Infinity;

  // Per-event remaining
  const perEventRemaining =
    maxPerEvent !== undefined ? maxPerEvent - soldCount : Infinity;

  // Effective remaining = min of both
  const remaining = Math.min(perOrderRemaining, perEventRemaining);

  // Total capacity
  let totalCapacity: number;
  if (maxPerOrder !== undefined && maxPerEvent !== undefined) {
    totalCapacity = Math.min(maxPerOrder, maxPerEvent);
  } else if (maxPerOrder !== undefined) {
    totalCapacity = maxPerOrder;
  } else if (maxPerEvent !== undefined) {
    totalCapacity = maxPerEvent;
  } else {
    totalCapacity = Infinity;
  }

  return {
    remaining: Math.max(remaining, 0),
    totalCapacity,
    isExhausted: remaining <= 0,
  };
}

/**
 * Helper to create a Product with given purchase_rules.
 */
function makeProduct(
  productId: string,
  purchaseRules: PurchaseRules
): Product {
  return {
    product_id: productId,
    naam: 'Test Product',
    event_type: 'closed',
    prijs: 10,
    order_item_fields: [],
    variant_schema: null,
    purchase_rules: purchaseRules,
  };
}

/** Empty form state (no products in order). */
const emptyFormState: PersonFormState = {
  persons: [{ name: 'Test', role: 'guest', products: [] }],
};

describe('useEffectiveLimits - max_per_order reading', () => {
  // --- Requirement 5.5: max_per_order is read correctly ---

  it('reads max_per_order correctly from product.purchase_rules', () => {
    const product = makeProduct('prod-1', { max_per_order: 5 });
    const result = calculateEffectiveLimit(product, emptyFormState, 0);

    expect(result.remaining).toBe(5);
    expect(result.totalCapacity).toBe(5);
    expect(result.isExhausted).toBe(false);
  });

  it('reads max_per_order=1 correctly (minimum boundary)', () => {
    const product = makeProduct('prod-1', { max_per_order: 1 });
    const result = calculateEffectiveLimit(product, emptyFormState, 0);

    expect(result.remaining).toBe(1);
    expect(result.totalCapacity).toBe(1);
  });

  it('reads max_per_order with high value correctly', () => {
    const product = makeProduct('prod-1', { max_per_order: 9999 });
    const result = calculateEffectiveLimit(product, emptyFormState, 0);

    expect(result.remaining).toBe(9999);
    expect(result.totalCapacity).toBe(9999);
  });

  // --- Requirement 5.5: absent max_per_order means unlimited ---

  it('treats absent max_per_order as unlimited (remaining = Infinity)', () => {
    const product = makeProduct('prod-1', {});
    const result = calculateEffectiveLimit(product, emptyFormState, 0);

    expect(result.remaining).toBe(Infinity);
    expect(result.totalCapacity).toBe(Infinity);
    expect(result.isExhausted).toBe(false);
  });

  it('treats purchase_rules with only min_per_order as unlimited max', () => {
    const product = makeProduct('prod-1', { min_per_order: 2 });
    const result = calculateEffectiveLimit(product, emptyFormState, 0);

    expect(result.remaining).toBe(Infinity);
    expect(result.totalCapacity).toBe(Infinity);
  });

  // --- Effective limit decreases as order quantity increases ---

  it('decreases remaining when order already contains products', () => {
    const product = makeProduct('prod-1', { max_per_order: 5 });
    const formState: PersonFormState = {
      persons: [{
        name: 'Test',
        role: 'guest',
        products: [
          { product_id: 'prod-1', variant_id: null, fields: {} },
          { product_id: 'prod-1', variant_id: null, fields: {} },
        ],
      }],
    };

    const result = calculateEffectiveLimit(product, formState, 0);

    expect(result.remaining).toBe(3); // 5 - 2 = 3
    expect(result.isExhausted).toBe(false);
  });

  it('is exhausted when order quantity equals max_per_order', () => {
    const product = makeProduct('prod-1', { max_per_order: 2 });
    const formState: PersonFormState = {
      persons: [{
        name: 'Test',
        role: 'guest',
        products: [
          { product_id: 'prod-1', variant_id: null, fields: {} },
          { product_id: 'prod-1', variant_id: null, fields: {} },
        ],
      }],
    };

    const result = calculateEffectiveLimit(product, formState, 0);

    expect(result.remaining).toBe(0);
    expect(result.isExhausted).toBe(true);
  });

  // --- Dual constraint: min(max_per_order, max_per_event) ---

  it('uses the lower of max_per_order and max_per_event as effective constraint', () => {
    const product = makeProduct('prod-1', {
      max_per_order: 10,
      max_per_event: 3,
    });

    const result = calculateEffectiveLimit(product, emptyFormState, 0);

    expect(result.remaining).toBe(3); // min(10-0, 3-0) = 3
    expect(result.totalCapacity).toBe(3); // min(10, 3)
  });

  it('max_per_event sold count reduces remaining when max_per_order is higher', () => {
    const product = makeProduct('prod-1', {
      max_per_order: 10,
      max_per_event: 20,
    });

    const result = calculateEffectiveLimit(product, emptyFormState, 15);

    expect(result.remaining).toBe(5); // min(10-0, 20-15) = 5
  });
});
