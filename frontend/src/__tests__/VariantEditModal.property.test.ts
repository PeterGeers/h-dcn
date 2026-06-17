import * as fc from 'fast-check';
import {
  determineFormMode,
  validateAxisInput,
  FormMode,
} from '../modules/products/utils/variantFormHelpers';
import { AdminVariant } from '../modules/webshop-management/types/admin.types';
import { MAX_AXES } from '../config/constants';

// Feature: product-variant-simplification, Property 3: Form mode determined by axis count
// Feature: product-variant-simplification, Property 2: Empty axis name or value is rejected

/**
 * Property-based tests for VariantEditModal helpers:
 * - determineFormMode: maps distinct axis count to form mode
 * - validateAxisInput: rejects empty/whitespace-only inputs
 *
 * Uses fast-check with minimum 100 iterations per property.
 *
 * **Validates: Requirements 3.3, 4.1, 4.2**
 */

const NUM_RUNS = 100;

// --- Generators ---

/**
 * Generator for a non-empty axis name (alphanumeric, 1-15 chars).
 */
const axisNameArb = fc.stringOf(
  fc.constantFrom(...'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'.split('')),
  { minLength: 1, maxLength: 15 },
);

/**
 * Generator for a non-empty axis value (alphanumeric + spaces, 1-15 chars).
 */
const axisValueArb = fc.stringOf(
  fc.constantFrom(...'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 '.split('')),
  { minLength: 1, maxLength: 15 },
);

/**
 * Generator for an AdminVariant with a specific set of axis names.
 * Each axis gets a random value.
 */
const adminVariantWithAxes = (axisNames: string[]): fc.Arbitrary<AdminVariant> =>
  fc.tuple(...axisNames.map(() => axisValueArb)).map((values) => {
    const attrs: Record<string, string> = {};
    axisNames.forEach((name, i) => {
      attrs[name] = values[i];
    });
    return {
      product_id: 'var_test-id',
      parent_id: 'parent-id',
      variant_attributes: attrs,
      stock: 0,
      sold_count: 0,
      allow_oversell: false,
      active: true,
    };
  });

/**
 * Generator for a whitespace-only or empty string.
 */
const whitespaceOrEmptyArb = fc.oneof(
  fc.constant(''),
  fc.stringOf(fc.constantFrom(' ', '\t', '\n', '\r'), { minLength: 1, maxLength: 10 }),
);

/**
 * Generator for a non-empty, non-whitespace-only string (contains at least one visible char).
 */
const nonEmptyNonWhitespaceArb = fc
  .tuple(
    fc.stringOf(fc.constantFrom(' ', '\t'), { minLength: 0, maxLength: 3 }),
    fc.stringOf(
      fc.constantFrom(...'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'.split('')),
      { minLength: 1, maxLength: 15 },
    ),
    fc.stringOf(fc.constantFrom(' ', '\t'), { minLength: 0, maxLength: 3 }),
  )
  .map(([prefix, core, suffix]) => prefix + core + suffix);

// --- Property 3: Form mode determined by axis count ---

describe('determineFormMode property tests', () => {
  /**
   * Property 3a: Zero distinct axes → 'zero-axes'
   *
   * When existingVariants is empty or all variants have empty variant_attributes,
   * the form mode must be 'zero-axes'.
   */
  describe("Property 3a: zero distinct axes returns 'zero-axes'", () => {
    it("returns 'zero-axes' for an empty variants array", () => {
      fc.assert(
        fc.property(fc.constant([]), (variants: AdminVariant[]) => {
          expect(determineFormMode(variants)).toBe('zero-axes');
        }),
        { numRuns: NUM_RUNS },
      );
    });

    it("returns 'zero-axes' when all variants have empty variant_attributes", () => {
      fc.assert(
        fc.property(
          fc.array(adminVariantWithAxes([]), { minLength: 1, maxLength: 10 }),
          (variants) => {
            expect(determineFormMode(variants)).toBe('zero-axes');
          },
        ),
        { numRuns: NUM_RUNS },
      );
    });
  });

  /**
   * Property 3b: Distinct axes >= 1 and < MAX_AXES → 'under-max'
   *
   * When the number of distinct axis names across all variant_attributes
   * is at least 1 but less than MAX_AXES, the form mode must be 'under-max'.
   */
  describe("Property 3b: 1 to MAX_AXES-1 distinct axes returns 'under-max'", () => {
    it("returns 'under-max' when distinct axis count is in [1, MAX_AXES)", () => {
      // Generate exactly 1 axis name (since MAX_AXES = 2, only 1 qualifies for under-max)
      fc.assert(
        fc.property(
          fc.uniqueArray(axisNameArb, { minLength: 1, maxLength: MAX_AXES - 1 }).chain(
            (axisNames) =>
              fc.array(adminVariantWithAxes(axisNames), { minLength: 1, maxLength: 8 }),
          ),
          (variants) => {
            const result = determineFormMode(variants);
            expect(result).toBe('under-max');
          },
        ),
        { numRuns: NUM_RUNS },
      );
    });
  });

  /**
   * Property 3c: Distinct axes >= MAX_AXES → 'at-max'
   *
   * When the number of distinct axis names across all variant_attributes
   * equals or exceeds MAX_AXES, the form mode must be 'at-max'.
   */
  describe("Property 3c: MAX_AXES or more distinct axes returns 'at-max'", () => {
    it("returns 'at-max' when distinct axis count >= MAX_AXES", () => {
      fc.assert(
        fc.property(
          fc.uniqueArray(axisNameArb, { minLength: MAX_AXES, maxLength: MAX_AXES + 2 }).chain(
            (axisNames) =>
              fc.array(adminVariantWithAxes(axisNames), { minLength: 1, maxLength: 8 }),
          ),
          (variants) => {
            const result = determineFormMode(variants);
            expect(result).toBe('at-max');
          },
        ),
        { numRuns: NUM_RUNS },
      );
    });
  });

  /**
   * Property 3d: Form mode is deterministic — same input always yields same result.
   *
   * For any variants array, calling determineFormMode twice returns the same value.
   */
  describe('Property 3d: determineFormMode is deterministic', () => {
    it('same input always produces the same output', () => {
      fc.assert(
        fc.property(
          fc.uniqueArray(axisNameArb, { minLength: 0, maxLength: 4 }).chain((axisNames) =>
            fc.array(adminVariantWithAxes(axisNames), { minLength: 0, maxLength: 8 }),
          ),
          (variants) => {
            const result1 = determineFormMode(variants);
            const result2 = determineFormMode(variants);
            expect(result1).toBe(result2);
          },
        ),
        { numRuns: NUM_RUNS },
      );
    });
  });
});

// --- Property 2: Empty axis name or value is rejected ---

describe('validateAxisInput property tests', () => {
  /**
   * Property 2a: Empty or whitespace-only axis name is rejected
   *
   * For any string that is empty or contains only whitespace as the axis name,
   * validateAxisInput must return false regardless of the value.
   */
  describe('Property 2a: empty/whitespace-only axis name is rejected', () => {
    it('returns false when axis name is empty or whitespace-only', () => {
      fc.assert(
        fc.property(whitespaceOrEmptyArb, fc.string({ minLength: 0, maxLength: 30 }), (axisName, value) => {
          expect(validateAxisInput(axisName, value)).toBe(false);
        }),
        { numRuns: NUM_RUNS },
      );
    });
  });

  /**
   * Property 2b: Empty or whitespace-only value is rejected
   *
   * For any string that is empty or contains only whitespace as the value,
   * validateAxisInput must return false regardless of the axis name.
   */
  describe('Property 2b: empty/whitespace-only value is rejected', () => {
    it('returns false when value is empty or whitespace-only', () => {
      fc.assert(
        fc.property(fc.string({ minLength: 0, maxLength: 30 }), whitespaceOrEmptyArb, (axisName, value) => {
          expect(validateAxisInput(axisName, value)).toBe(false);
        }),
        { numRuns: NUM_RUNS },
      );
    });
  });

  /**
   * Property 2c: Non-empty, non-whitespace inputs are accepted
   *
   * For any axis name and value that contain at least one non-whitespace character,
   * validateAxisInput must return true.
   */
  describe('Property 2c: valid (non-empty, non-whitespace) inputs are accepted', () => {
    it('returns true when both axis name and value have non-whitespace content', () => {
      fc.assert(
        fc.property(nonEmptyNonWhitespaceArb, nonEmptyNonWhitespaceArb, (axisName, value) => {
          expect(validateAxisInput(axisName, value)).toBe(true);
        }),
        { numRuns: NUM_RUNS },
      );
    });
  });
});
