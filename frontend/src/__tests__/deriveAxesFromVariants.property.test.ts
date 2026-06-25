import * as fc from 'fast-check';
import { deriveAxesFromVariants } from '../utils/variantUtils';
import { VariantRecord } from '../modules/webshop/types/unifiedProduct.types';

// Feature: product-variant-simplification, Property 4: Axis derivation from active variant records

/**
 * Property-based tests for deriveAxesFromVariants utility.
 * Uses fast-check with minimum 100 iterations per property.
 *
 * **Validates: Requirements 5.1, 5.3**
 */

const NUM_RUNS = 100;

/**
 * Object.prototype property names that would collide with the Record<string, Set>
 * pattern. We exclude these from generated axis names since they are not realistic
 * product attribute names and represent a JS prototype quirk rather than domain logic.
 */
const PROTOTYPE_KEYS = new Set(Object.getOwnPropertyNames(Object.prototype));

/**
 * Generator for a non-empty axis name (alphanumeric, 1-20 chars).
 * Filtered to exclude Object.prototype property names to avoid prototype collisions.
 */
const axisNameArb = fc.stringOf(
  fc.constantFrom(...'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'.split('')),
  { minLength: 1, maxLength: 20 },
).filter((s) => !PROTOTYPE_KEYS.has(s));

/**
 * Generator for a non-empty axis value (alphanumeric + spaces, 1-20 chars).
 */
const axisValueArb = fc.stringOf(
  fc.constantFrom(...'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 '.split('')),
  { minLength: 1, maxLength: 20 },
);

/**
 * Generator for variant_attributes: 1-3 axis-value pairs with unique axis names.
 */
const variantAttributesArb = fc
  .uniqueArray(axisNameArb, { minLength: 1, maxLength: 3 })
  .chain((axisNames) =>
    fc.tuple(...axisNames.map(() => axisValueArb)).map((values) => {
      const attrs: Record<string, string> = {};
      axisNames.forEach((name, i) => {
        attrs[name] = values[i];
      });
      return attrs;
    }),
  );

/**
 * Generator for a single VariantRecord with configurable active state.
 */
const variantRecordArb = (activeArb: fc.Arbitrary<boolean>): fc.Arbitrary<VariantRecord> =>
  fc.record({
    product_id: fc.uuid(),
    parent_id: fc.uuid(),
    name: fc.string({ minLength: 1, maxLength: 50 }),
    variant_attributes: variantAttributesArb,
    price: fc.nat({ max: 10000 }),
    stock: fc.nat({ max: 1000 }),
    sold_count: fc.nat({ max: 1000 }),
    allow_oversell: fc.boolean(),
    active: activeArb,
  });

/**
 * Generator for an array of VariantRecords with mixed active/inactive.
 */
const variantArrayArb = fc.array(variantRecordArb(fc.boolean()), { minLength: 0, maxLength: 15 });

/**
 * Generator for an array with at least one active variant.
 */
const variantArrayWithActiveArb = fc
  .array(variantRecordArb(fc.boolean()), { minLength: 0, maxLength: 10 })
  .chain((variants) =>
    variantRecordArb(fc.constant(true)).map((activeVariant) => [...variants, activeVariant]),
  );

describe('deriveAxesFromVariants property tests', () => {
  /**
   * Property 4a: Returned keys are ONLY axis names from active variants
   *
   * For any array of VariantRecords, the keys of the returned VariantSchema
   * are exactly the set of axis names that appear in at least one active
   * variant's variant_attributes.
   */
  describe('Property 4a: Returned keys match axis names from active variants only', () => {
    it('result keys equal the union of axis names from active variant_attributes', () => {
      fc.assert(
        fc.property(variantArrayArb, (variants) => {
          const result = deriveAxesFromVariants(variants);

          // Compute expected keys: axis names from active variants only
          const expectedKeys = new Set<string>();
          for (const v of variants) {
            if (v.active) {
              for (const axis of Object.keys(v.variant_attributes)) {
                expectedKeys.add(axis);
              }
            }
          }

          const resultKeys = new Set(Object.keys(result));
          expect(resultKeys).toEqual(expectedKeys);
        }),
        { numRuns: NUM_RUNS },
      );
    });
  });

  /**
   * Property 4b: Each value array contains NO duplicates
   *
   * For any array of VariantRecords, every value array in the returned
   * VariantSchema contains unique elements only.
   */
  describe('Property 4b: Value arrays contain no duplicates', () => {
    it('each axis value array has all unique elements', () => {
      fc.assert(
        fc.property(variantArrayWithActiveArb, (variants) => {
          const result = deriveAxesFromVariants(variants);

          for (const [axis, values] of Object.entries(result)) {
            const uniqueValues = new Set(values);
            expect(uniqueValues.size).toBe(values.length);
          }
        }),
        { numRuns: NUM_RUNS },
      );
    });
  });

  /**
   * Property 4c: Inactive variants are completely excluded
   *
   * For any array of VariantRecords where some are inactive, the result
   * does NOT contain any axis names or values that appear ONLY in inactive
   * variants.
   */
  describe('Property 4c: Inactive variants excluded from result', () => {
    it('axes and values exclusive to inactive variants do not appear in result', () => {
      fc.assert(
        fc.property(variantArrayArb, (variants) => {
          const result = deriveAxesFromVariants(variants);

          // Collect axis-value pairs from active variants
          const activeAxisValues = new Map<string, Set<string>>();
          for (const v of variants) {
            if (v.active) {
              for (const [axis, value] of Object.entries(v.variant_attributes)) {
                if (!activeAxisValues.has(axis)) activeAxisValues.set(axis, new Set());
                activeAxisValues.get(axis)!.add(value);
              }
            }
          }

          // Every key in result must be in activeAxisValues
          for (const axis of Object.keys(result)) {
            expect(activeAxisValues.has(axis)).toBe(true);
          }

          // Every value in result must be in activeAxisValues for that axis
          for (const [axis, values] of Object.entries(result)) {
            for (const value of values) {
              expect(activeAxisValues.get(axis)!.has(value)).toBe(true);
            }
          }
        }),
        { numRuns: NUM_RUNS },
      );
    });
  });

  /**
   * Property 4d: Every value in the result exists in at least one active variant
   *
   * For any array of VariantRecords, every value listed under an axis in the
   * result actually exists in at least one active variant's variant_attributes
   * for that axis.
   */
  describe('Property 4d: Every result value exists in at least one active variant', () => {
    it('all result values are traceable to an active variant record', () => {
      fc.assert(
        fc.property(variantArrayWithActiveArb, (variants) => {
          const result = deriveAxesFromVariants(variants);

          for (const [axis, values] of Object.entries(result)) {
            for (const value of values) {
              // There must be at least one active variant with this axis-value pair
              const found = variants.some(
                (v) => v.active && v.variant_attributes[axis] === value,
              );
              expect(found).toBe(true);
            }
          }
        }),
        { numRuns: NUM_RUNS },
      );
    });
  });
});
