import * as fc from 'fast-check';
import { extractVariants } from './extractVariants';

/**
 * Preservation Property Test (Property 2)
 *
 * **Validates: Requirements 3.1, 3.2, 3.3, 3.4**
 *
 * This test verifies that for all NON-bug-condition inputs where the original
 * code ALREADY returns a valid result (an array or []), the fixed extraction
 * logic produces the SAME result as the original (unfixed) logic.
 *
 * Genuinely non-problematic inputs:
 * - null / undefined responses → both return []
 * - Direct array responses (Array.isArray(response) === true) → both return the array
 * - Objects where response.data is null/undefined/falsy → both return []
 *
 * NOTE: Objects where response.data is a truthy non-array object are NOT included
 * because the original code incorrectly returns that object (a different manifestation
 * of the same bug). Those are NOT behavior worth preserving.
 *
 * The UNFIXED code: Array.isArray(response) ? response : response?.data || []
 * The FIXED code:   Array.isArray(response) ? response : response?.data?.variants || []
 *
 * For genuinely non-problematic inputs, both must produce identical results.
 */

/**
 * The original (unfixed) extraction logic - replicates current behavior.
 */
function extractVariants_original(response: any): any {
  const variantData = Array.isArray(response) ? response : response?.data || [];
  return variantData;
}

/**
 * The fixed extraction logic - what the code will become after the fix.
 */
function extractVariants_fixed(response: any): any {
  const variantData = Array.isArray(response) ? response : response?.data?.variants || [];
  return variantData;
}

// --- Generators for genuinely non-problematic inputs ---
// These are inputs where the original code correctly returns [] or a proper array.

// Generator: null response → both return []
const nullResponseArb = fc.constant(null);

// Generator: undefined response → both return []
const undefinedResponseArb = fc.constant(undefined);

// Generator: direct array response (Array.isArray(response) === true) → both return the array
const directArrayResponseArb = fc.array(
  fc.record({
    variant_id: fc.string({ minLength: 1, maxLength: 20 }),
    product_id: fc.string({ minLength: 1, maxLength: 20 }),
    variant_attributes: fc.dictionary(
      fc.string({ minLength: 1, maxLength: 10 }),
      fc.string({ minLength: 1, maxLength: 20 })
    ),
    stock: fc.integer({ min: 0, max: 1000 }),
    price: fc.float({ min: 0, max: 9999, noNaN: true }),
    allow_oversell: fc.boolean(),
  }),
  { minLength: 0, maxLength: 5 }
);

// Generator: object with data = null → both return []
const dataNullResponseArb = fc.record({
  success: fc.boolean(),
  data: fc.constant(null),
});

// Generator: object with data = undefined → both return []
const dataUndefinedResponseArb = fc.record({
  success: fc.boolean(),
  data: fc.constant(undefined),
});

// Generator: object with no data property at all → both return []
const noDataPropertyArb = fc.record({
  success: fc.boolean(),
  error: fc.option(fc.string({ minLength: 1, maxLength: 50 }), { nil: undefined }),
});

// Generator: object where data is a falsy value (0, "", false, NaN) → both return []
const dataFalsyArb = fc.record({
  success: fc.boolean(),
  data: fc.oneof(
    fc.constant(0),
    fc.constant(''),
    fc.constant(false)
  ),
});

// Combined generator for all genuinely non-problematic inputs
const nonProblematicResponseArb = fc.oneof(
  nullResponseArb,
  undefinedResponseArb,
  directArrayResponseArb,
  dataNullResponseArb,
  dataUndefinedResponseArb,
  noDataPropertyArb,
  dataFalsyArb
);

describe('extractVariants - Preservation Property (Property 2)', () => {
  it('original and fixed produce identical results for all genuinely non-problematic inputs', () => {
    fc.assert(
      fc.property(nonProblematicResponseArb, (response) => {
        const originalResult = extractVariants_original(response);
        const fixedResult = extractVariants_fixed(response);

        expect(fixedResult).toEqual(originalResult);
      }),
      { numRuns: 200 }
    );
  });

  it('extractVariants (unfixed) returns [] for null response', () => {
    fc.assert(
      fc.property(nullResponseArb, (response) => {
        const result = extractVariants(response);
        expect(result).toEqual([]);
      }),
      { numRuns: 10 }
    );
  });

  it('extractVariants (unfixed) returns [] for undefined response', () => {
    fc.assert(
      fc.property(undefinedResponseArb, (response) => {
        const result = extractVariants(response);
        expect(result).toEqual([]);
      }),
      { numRuns: 10 }
    );
  });

  it('extractVariants (unfixed) returns the array directly when response is an array', () => {
    fc.assert(
      fc.property(directArrayResponseArb, (response) => {
        const result = extractVariants(response);
        expect(result).toEqual(response);
        expect(Array.isArray(result)).toBe(true);
      }),
      { numRuns: 100 }
    );
  });

  it('extractVariants (unfixed) returns [] when response.data is null', () => {
    fc.assert(
      fc.property(dataNullResponseArb, (response) => {
        const result = extractVariants(response);
        expect(result).toEqual([]);
      }),
      { numRuns: 50 }
    );
  });

  it('extractVariants (unfixed) returns [] when response.data is undefined', () => {
    fc.assert(
      fc.property(dataUndefinedResponseArb, (response) => {
        const result = extractVariants(response);
        expect(result).toEqual([]);
      }),
      { numRuns: 50 }
    );
  });

  it('fixed logic also returns [] for null/undefined responses (matches original)', () => {
    fc.assert(
      fc.property(
        fc.oneof(nullResponseArb, undefinedResponseArb),
        (response) => {
          const fixedResult = extractVariants_fixed(response);
          expect(fixedResult).toEqual([]);
        }
      ),
      { numRuns: 20 }
    );
  });

  it('fixed logic returns array directly when response is array (matches original)', () => {
    fc.assert(
      fc.property(directArrayResponseArb, (response) => {
        const fixedResult = extractVariants_fixed(response);
        expect(fixedResult).toEqual(response);
      }),
      { numRuns: 100 }
    );
  });

  it('fixed logic returns [] when response.data is falsy (matches original [])', () => {
    fc.assert(
      fc.property(dataFalsyArb, (response) => {
        const originalResult = extractVariants_original(response);
        const fixedResult = extractVariants_fixed(response);

        expect(fixedResult).toEqual(originalResult);
        expect(fixedResult).toEqual([]);
      }),
      { numRuns: 50 }
    );
  });
});
