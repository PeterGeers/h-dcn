import * as fc from 'fast-check';
import { sortSizeValues, SIZE_ORDER } from '../utils/sizeSorter';

/**
 * Property-based tests for the sizeSorter utility.
 * Uses fast-check with minimum 100 iterations per property.
 */

const RECOGNIZED_SIZES = Object.keys(SIZE_ORDER);
const NUM_RUNS = 100;

/**
 * Helper: checks if a string is numeric (matches sizeSorter's isNumeric logic).
 */
function isNumeric(value: string): boolean {
  return value.trim() !== '' && !isNaN(Number(value));
}

describe('sizeSorter property tests', () => {
  /**
   * Property 1: Size sort preserves set membership
   * Validates: Requirements 5.1, 5.3, 5.5, 5.6
   *
   * For any list of size strings, sortSizeValues returns a list containing
   * exactly the same elements (same length, same multiset of values).
   */
  describe('Property 1: Size sort preserves set membership', () => {
    it('sorted output has same length and same multiset of values as input', () => {
      fc.assert(
        fc.property(fc.array(fc.string()), (values) => {
          const sorted = sortSizeValues(values);

          // Same length
          expect(sorted.length).toBe(values.length);

          // Same multiset: sort both arrays lexicographically and compare
          const inputSorted = [...values].sort();
          const outputSorted = [...sorted].sort();
          expect(outputSorted).toEqual(inputSorted);
        }),
        { numRuns: NUM_RUNS },
      );
    });
  });

  /**
   * Property 2: Recognized sizes precede unrecognized and are in standard order
   * Validates: Requirements 5.1, 5.3, 5.6
   *
   * For any list containing a mix of recognized clothing sizes and unrecognized
   * values, after sorting:
   * (a) all recognized sizes appear before all unrecognized non-numeric values
   * (b) recognized sizes are ordered XXS < XS < S < M < L < XL < XXL < 3XL < 4XL < 5XL
   * (c) unrecognized non-numeric values are in case-insensitive alphabetical order
   */
  describe('Property 2: Recognized sizes precede unrecognized and are in standard order', () => {
    // Generator for recognized size strings (various casings)
    const recognizedSizeArb = fc.constantFrom(...RECOGNIZED_SIZES).map((s) => {
      // Randomly vary casing to test case-insensitive matching
      const variants = [s, s.toUpperCase(), s.charAt(0).toUpperCase() + s.slice(1)];
      return variants[Math.floor(Math.random() * variants.length)];
    });

    // Generator for unrecognized non-numeric strings (alphabetic only, non-empty)
    const unrecognizedArb = fc
      .stringOf(fc.constantFrom(...'abcdefghijklmnopqrstuvwyz'.split('')), { minLength: 1, maxLength: 8 })
      .filter((s) => SIZE_ORDER[s.toLowerCase()] === undefined && !isNumeric(s));

    it('recognized sizes come before unrecognized, in standard order; unrecognized are alphabetical', () => {
      fc.assert(
        fc.property(
          fc.array(recognizedSizeArb, { minLength: 1, maxLength: 10 }),
          fc.array(unrecognizedArb, { minLength: 1, maxLength: 10 }),
          (recognized, unrecognized) => {
            const input = [...recognized, ...unrecognized];
            const sorted = sortSizeValues(input);

            // Classify sorted output
            const sortedRecognized: string[] = [];
            const sortedUnrecognized: string[] = [];
            for (const val of sorted) {
              if (SIZE_ORDER[val.toLowerCase()] !== undefined) {
                sortedRecognized.push(val);
              } else {
                sortedUnrecognized.push(val);
              }
            }

            // (a) All recognized appear before all unrecognized
            const lastRecognizedIdx = sorted.length - 1 - [...sorted].reverse().findIndex(
              (v) => SIZE_ORDER[v.toLowerCase()] !== undefined
            );
            const firstUnrecognizedIdx = sorted.findIndex(
              (v) => SIZE_ORDER[v.toLowerCase()] === undefined
            );
            if (sortedRecognized.length > 0 && sortedUnrecognized.length > 0) {
              expect(lastRecognizedIdx).toBeLessThan(firstUnrecognizedIdx);
            }

            // (b) Recognized sizes are in standard order (XXS → 5XL)
            for (let i = 1; i < sortedRecognized.length; i++) {
              const prev = SIZE_ORDER[sortedRecognized[i - 1].toLowerCase()];
              const curr = SIZE_ORDER[sortedRecognized[i].toLowerCase()];
              expect(prev).toBeLessThanOrEqual(curr);
            }

            // (c) Unrecognized non-numeric values are in case-insensitive alphabetical order
            for (let i = 1; i < sortedUnrecognized.length; i++) {
              const cmp = sortedUnrecognized[i - 1]
                .toLowerCase()
                .localeCompare(sortedUnrecognized[i].toLowerCase());
              expect(cmp).toBeLessThanOrEqual(0);
            }
          },
        ),
        { numRuns: NUM_RUNS },
      );
    });
  });

  /**
   * Property 3: Numeric values sort numerically
   * Validates: Requirements 5.5
   *
   * For any list of numeric string values, sorting places them in ascending
   * numeric order, not lexicographic order (so "9" < "10" < "100").
   */
  describe('Property 3: Numeric values sort numerically', () => {
    // Generator for numeric strings: integers and decimals as strings
    const numericStringArb = fc
      .integer({ min: 0, max: 99999 })
      .map((n) => String(n));

    it('numeric strings are sorted in ascending numeric order', () => {
      fc.assert(
        fc.property(
          fc.array(numericStringArb, { minLength: 1, maxLength: 20 }),
          (numericStrings) => {
            const sorted = sortSizeValues(numericStrings);

            // All values should be numeric, so sorted output equals sorted by Number()
            for (let i = 1; i < sorted.length; i++) {
              expect(Number(sorted[i - 1])).toBeLessThanOrEqual(Number(sorted[i]));
            }
          },
        ),
        { numRuns: NUM_RUNS },
      );
    });
  });

  /**
   * Property 4: Sort is idempotent
   * Validates: Requirements 5.1, 5.2, 5.3, 5.5, 5.6
   *
   * For any list of size values, applying sortSizeValues twice produces the
   * same result as applying it once: sort(sort(xs)) === sort(xs).
   */
  describe('Property 4: Sort is idempotent', () => {
    it('sortSizeValues(sortSizeValues(xs)) equals sortSizeValues(xs) for arbitrary string arrays', () => {
      fc.assert(
        fc.property(fc.array(fc.string()), (values) => {
          const sortedOnce = sortSizeValues(values);
          const sortedTwice = sortSizeValues(sortedOnce);

          expect(sortedTwice).toEqual(sortedOnce);
        }),
        { numRuns: NUM_RUNS },
      );
    });
  });
});
