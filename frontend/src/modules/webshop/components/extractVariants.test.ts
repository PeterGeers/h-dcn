import * as fc from 'fast-check';
import { extractVariants } from './extractVariants';

/**
 * Bug Condition Exploration Property Test
 *
 * **Validates: Requirements 1.1, 1.2**
 *
 * This test encodes the EXPECTED behavior: extractVariants should return
 * response.data.variants (the VariantRecord[] array) when the response
 * has a successful shape with a nested variants array.
 *
 * On UNFIXED code, this test is EXPECTED TO FAIL because the current
 * implementation returns response.data (the entire object) instead of
 * response.data.variants (the array).
 */

// Generator for a single VariantRecord-like object
const variantRecordArb = fc.record({
  variant_id: fc.string({ minLength: 1, maxLength: 20 }),
  product_id: fc.string({ minLength: 1, maxLength: 20 }),
  variant_attributes: fc.dictionary(
    fc.string({ minLength: 1, maxLength: 10 }),
    fc.string({ minLength: 1, maxLength: 20 })
  ),
  stock: fc.integer({ min: 0, max: 1000 }),
  price: fc.float({ min: 0, max: 9999, noNaN: true }),
  allow_oversell: fc.boolean(),
});

// Generator for a successful API response where isBugCondition is true:
// response.success = true AND response.data IS object AND response.data.variants IS array
const bugConditionResponseArb = fc.array(variantRecordArb, { minLength: 0, maxLength: 10 }).chain(
  (variants) =>
    fc.record({
      success: fc.constant(true),
      data: fc.record({
        product_id: fc.string({ minLength: 1, maxLength: 20 }),
        variants: fc.constant(variants),
        total_count: fc.constant(variants.length),
      }),
    })
);

describe('extractVariants - Bug Condition Exploration (Property 1)', () => {
  it('should return response.data.variants array (not response.data object)', () => {
    fc.assert(
      fc.property(bugConditionResponseArb, (response) => {
        const result = extractVariants(response);

        // The expected behavior: extractVariants should return the variants array
        expect(result).toEqual(response.data.variants);
      }),
      { numRuns: 100 }
    );
  });

  it('should always return an array when isBugCondition is true', () => {
    fc.assert(
      fc.property(bugConditionResponseArb, (response) => {
        const result = extractVariants(response);

        // The expected behavior: result must be an array
        expect(Array.isArray(result)).toBe(true);
      }),
      { numRuns: 100 }
    );
  });

  it('should return array with length matching total_count', () => {
    fc.assert(
      fc.property(bugConditionResponseArb, (response) => {
        const result = extractVariants(response);

        // The expected behavior: array length equals total_count
        expect(result.length).toBe(response.data.total_count);
      }),
      { numRuns: 100 }
    );
  });
});
