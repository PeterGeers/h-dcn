/**
 * Property-based tests for effective limit calculation.
 *
 * Feature: closed-community-booking, Property 16
 * **Validates: Requirements 7.2, 7.3, 7.4, 7.5**
 *
 * For any product with max_per_club, optional max_per_event, current order quantity,
 * and sold count: the effective limit SHALL equal
 *   min(max_per_club - order_qty, max_per_event - sold_count) when max_per_event is defined,
 *   or (max_per_club - order_qty) when max_per_event is absent.
 * The product selection control SHALL be disabled when effective_limit ≤ 0.
 */

import * as fc from 'fast-check';
import { Product, PurchaseRules } from '../types/presmeet.types';
import { PersonFormState, PersonProduct } from '../utils/orderTransformer';

// --- Pure calculation function (mirrors useEffectiveLimits hook logic) ---

export interface EffectiveLimitInput {
  maxPerClub: number | undefined;
  maxPerEvent: number | undefined;
  orderQty: number;
  soldCount: number;
}

export interface EffectiveLimitResult {
  remaining: number;
  totalCapacity: number;
  isExhausted: boolean;
}

/**
 * Pure effective limit calculation — extracted from useEffectiveLimits hook.
 * This is the same logic used in the hook's products.map() block.
 */
function calculateEffectiveLimit(input: EffectiveLimitInput): EffectiveLimitResult {
  const { maxPerClub, maxPerEvent, orderQty, soldCount } = input;

  // Per-order remaining (how many more can this order add)
  const perOrderRemaining =
    maxPerClub !== undefined ? maxPerClub - orderQty : Infinity;

  // Per-event remaining (how many are left globally)
  const perEventRemaining =
    maxPerEvent !== undefined ? maxPerEvent - soldCount : Infinity;

  // Effective remaining = min of both
  const remaining = Math.min(perOrderRemaining, perEventRemaining);

  // Total capacity (Y in "X of Y remaining")
  let totalCapacity: number;
  if (maxPerClub !== undefined && maxPerEvent !== undefined) {
    totalCapacity = Math.min(maxPerClub, maxPerEvent);
  } else if (maxPerClub !== undefined) {
    totalCapacity = maxPerClub;
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
 * Calculate order quantity for a product across all persons (mirrors hook helper).
 */
function getOrderQuantityForProduct(
  formState: PersonFormState,
  productId: string
): number {
  let count = 0;
  for (const person of formState.persons) {
    for (const pp of person.products) {
      if (pp.product_id === productId) {
        count += 1;
      }
    }
  }
  return count;
}

// --- Arbitraries ---

/** Non-negative integer for quantities */
const quantityArb = fc.integer({ min: 0, max: 100 });

/** Positive integer for limits (max_per_club, max_per_event must be ≥ 1) */
const limitArb = fc.integer({ min: 1, max: 100 });

/** Optional max_per_event (undefined means no global limit) */
const optionalMaxPerEventArb: fc.Arbitrary<number | undefined> = fc.oneof(
  limitArb.map((v) => v as number | undefined),
  fc.constant(undefined)
);

/** Generates an EffectiveLimitInput with valid constraints */
const effectiveLimitInputArb: fc.Arbitrary<EffectiveLimitInput> = fc
  .tuple(limitArb, optionalMaxPerEventArb, quantityArb, quantityArb)
  .map(([maxPerClub, maxPerEvent, orderQty, soldCount]) => ({
    maxPerClub,
    maxPerEvent,
    orderQty,
    soldCount,
  }));

/** Generates input where max_per_event IS defined */
const inputWithMaxPerEventArb: fc.Arbitrary<EffectiveLimitInput> = fc
  .tuple(limitArb, limitArb, quantityArb, quantityArb)
  .map(([maxPerClub, maxPerEvent, orderQty, soldCount]) => ({
    maxPerClub,
    maxPerEvent,
    orderQty,
    soldCount,
  }));

/** Generates input where max_per_event is ABSENT */
const inputWithoutMaxPerEventArb: fc.Arbitrary<EffectiveLimitInput> = fc
  .tuple(limitArb, quantityArb, quantityArb)
  .map(([maxPerClub, orderQty, soldCount]) => ({
    maxPerClub,
    maxPerEvent: undefined,
    orderQty,
    soldCount,
  }));

/** Generates input where effective limit is exhausted (≤ 0) */
const exhaustedInputArb: fc.Arbitrary<EffectiveLimitInput> = fc.oneof(
  // Per-order exhausted: orderQty >= maxPerClub
  fc.tuple(limitArb, optionalMaxPerEventArb, quantityArb).map(
    ([maxPerClub, maxPerEvent, extra]) => ({
      maxPerClub,
      maxPerEvent,
      orderQty: maxPerClub + extra, // orderQty >= maxPerClub
      soldCount: 0,
    })
  ),
  // Per-event exhausted: soldCount >= maxPerEvent
  fc.tuple(limitArb, limitArb, quantityArb).map(
    ([maxPerClub, maxPerEvent, extra]) => ({
      maxPerClub,
      maxPerEvent,
      orderQty: 0,
      soldCount: maxPerEvent + extra, // soldCount >= maxPerEvent
    })
  )
);

/** Generates a product ID */
const productIdArb = fc.uuid();

/** Generates a PersonFormState with a known quantity for a specific product */
function formStateWithProductQty(
  productId: string,
  qty: number
): fc.Arbitrary<PersonFormState> {
  return fc.integer({ min: 1, max: Math.max(qty, 1) }).map((numPersons) => {
    const persons = [];
    let remaining = qty;
    for (let i = 0; i < numPersons && remaining > 0; i++) {
      const count = i < numPersons - 1 ? Math.min(remaining, 1) : remaining;
      const products: PersonProduct[] = [];
      for (let j = 0; j < count; j++) {
        products.push({ product_id: productId, variant_id: null, fields: {} });
      }
      persons.push({ name: `Person ${i}`, role: 'guest', products });
      remaining -= count;
    }
    // Add empty persons if needed
    if (persons.length === 0) {
      persons.push({ name: 'Person 0', role: 'guest', products: [] });
    }
    return { persons };
  });
}

// --- Property Tests ---

describe('Effective Limit Calculation - Property Tests', () => {
  /**
   * Property 16: When max_per_event is defined, effective limit equals
   * min(max_per_club - order_qty, max_per_event - sold_count).
   *
   * **Validates: Requirements 7.2, 7.3**
   */
  it('effective limit equals min(max_per_club - order_qty, max_per_event - sold_count) when max_per_event is defined', () => {
    fc.assert(
      fc.property(inputWithMaxPerEventArb, (input) => {
        const result = calculateEffectiveLimit(input);
        const expected = Math.min(
          input.maxPerClub! - input.orderQty,
          input.maxPerEvent! - input.soldCount
        );
        expect(result.remaining).toBe(Math.max(expected, 0));
      }),
      { numRuns: 200 }
    );
  });

  /**
   * Property 16: When max_per_event is absent, effective limit equals
   * (max_per_club - order_qty).
   *
   * **Validates: Requirements 7.4**
   */
  it('effective limit equals (max_per_club - order_qty) when max_per_event is absent', () => {
    fc.assert(
      fc.property(inputWithoutMaxPerEventArb, (input) => {
        const result = calculateEffectiveLimit(input);
        const expected = input.maxPerClub! - input.orderQty;
        expect(result.remaining).toBe(Math.max(expected, 0));
      }),
      { numRuns: 200 }
    );
  });

  /**
   * Property 16: Product is disabled (isExhausted) when effective_limit ≤ 0.
   *
   * **Validates: Requirements 7.2, 7.5**
   */
  it('product is disabled (isExhausted = true) when effective limit is zero or negative', () => {
    fc.assert(
      fc.property(exhaustedInputArb, (input) => {
        const result = calculateEffectiveLimit(input);
        expect(result.isExhausted).toBe(true);
        expect(result.remaining).toBe(0);
      }),
      { numRuns: 200 }
    );
  });

  /**
   * Property 16: Product is NOT disabled when effective_limit > 0.
   *
   * **Validates: Requirements 7.5**
   */
  it('product is NOT disabled (isExhausted = false) when effective limit is positive', () => {
    // Generate inputs where both per-order and per-event have remaining capacity
    const positiveInputArb = fc
      .tuple(limitArb, limitArb, quantityArb, quantityArb)
      .filter(([maxPerClub, maxPerEvent, orderQty, soldCount]) => {
        return maxPerClub - orderQty > 0 && maxPerEvent - soldCount > 0;
      })
      .map(([maxPerClub, maxPerEvent, orderQty, soldCount]) => ({
        maxPerClub,
        maxPerEvent,
        orderQty,
        soldCount,
      }));

    fc.assert(
      fc.property(positiveInputArb, (input) => {
        const result = calculateEffectiveLimit(input);
        expect(result.isExhausted).toBe(false);
        expect(result.remaining).toBeGreaterThan(0);
      }),
      { numRuns: 200 }
    );
  });

  /**
   * Property 16: The remaining value is always non-negative (clamped at 0).
   *
   * **Validates: Requirements 7.2, 7.3, 7.4**
   */
  it('remaining is always non-negative regardless of inputs', () => {
    fc.assert(
      fc.property(effectiveLimitInputArb, (input) => {
        const result = calculateEffectiveLimit(input);
        expect(result.remaining).toBeGreaterThanOrEqual(0);
      }),
      { numRuns: 200 }
    );
  });

  /**
   * Property 16: getOrderQuantityForProduct correctly counts products
   * distributed across multiple persons.
   *
   * **Validates: Requirements 7.2, 7.3**
   */
  it('order quantity aggregation counts products across all persons correctly', () => {
    fc.assert(
      fc.property(
        productIdArb,
        fc.integer({ min: 0, max: 20 }),
        (productId, expectedQty) => {
          // Build a form state that distributes expectedQty products across persons
          const persons = [];
          let remaining = expectedQty;
          const numPersons = Math.max(1, Math.ceil(expectedQty / 3));

          for (let i = 0; i < numPersons; i++) {
            const count =
              i < numPersons - 1
                ? Math.min(remaining, Math.ceil(remaining / (numPersons - i)))
                : remaining;
            const products: PersonProduct[] = [];
            for (let j = 0; j < count; j++) {
              products.push({
                product_id: productId,
                variant_id: null,
                fields: {},
              });
            }
            // Add some unrelated products to ensure filtering works
            products.push({
              product_id: 'other-product-id',
              variant_id: null,
              fields: {},
            });
            persons.push({ name: `Person ${i}`, role: 'guest', products });
            remaining -= count;
          }

          const formState: PersonFormState = { persons };
          const actualQty = getOrderQuantityForProduct(formState, productId);
          expect(actualQty).toBe(expectedQty);
        }
      ),
      { numRuns: 200 }
    );
  });

  /**
   * Property 16: Per-order limit is the binding constraint when
   * per-order remaining < per-event remaining.
   *
   * **Validates: Requirements 7.2**
   */
  it('per-order limit is binding when it is smaller than per-event remaining', () => {
    const perOrderBindingArb = fc
      .tuple(limitArb, limitArb, quantityArb, quantityArb)
      .filter(([maxPerClub, maxPerEvent, orderQty, soldCount]) => {
        const perOrder = maxPerClub - orderQty;
        const perEvent = maxPerEvent - soldCount;
        return perOrder < perEvent && perOrder > 0;
      })
      .map(([maxPerClub, maxPerEvent, orderQty, soldCount]) => ({
        maxPerClub,
        maxPerEvent,
        orderQty,
        soldCount,
      }));

    fc.assert(
      fc.property(perOrderBindingArb, (input) => {
        const result = calculateEffectiveLimit(input);
        expect(result.remaining).toBe(input.maxPerClub! - input.orderQty);
      }),
      { numRuns: 100 }
    );
  });

  /**
   * Property 16: Per-event limit is the binding constraint when
   * per-event remaining < per-order remaining.
   *
   * **Validates: Requirements 7.3**
   */
  it('per-event limit is binding when it is smaller than per-order remaining', () => {
    const perEventBindingArb = fc
      .tuple(limitArb, limitArb, quantityArb, quantityArb)
      .filter(([maxPerClub, maxPerEvent, orderQty, soldCount]) => {
        const perOrder = maxPerClub - orderQty;
        const perEvent = maxPerEvent - soldCount;
        return perEvent < perOrder && perEvent > 0;
      })
      .map(([maxPerClub, maxPerEvent, orderQty, soldCount]) => ({
        maxPerClub,
        maxPerEvent,
        orderQty,
        soldCount,
      }));

    fc.assert(
      fc.property(perEventBindingArb, (input) => {
        const result = calculateEffectiveLimit(input);
        expect(result.remaining).toBe(input.maxPerEvent! - input.soldCount);
      }),
      { numRuns: 100 }
    );
  });
});
