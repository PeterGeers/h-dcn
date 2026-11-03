import * as fc from 'fast-check';
import { normalizeValues, previewCreateCount } from '../variantBulkHelpers';

// Feature: variant-bulk-generator — property tests for the pure helpers.

/**
 * Property-based tests for variantBulkHelpers.
 * Uses fast-check with a minimum of 100 iterations per property.
 */

const NUM_RUNS = 100;

/**
 * Generator for an arbitrary raw string entry. Mixes alphanumerics, spaces, and
 * whitespace so that trimming, empty/whitespace-only dropping, and de-duplication
 * are all exercised. Includes a bias toward short/empty strings to hit edge cases.
 */
const rawEntryArb = fc.oneof(
  // Plain content (may have surrounding whitespace via the padded variant below).
  fc.stringOf(
    fc.constantFrom(...'abcABC123 \t'.split('')),
    { minLength: 0, maxLength: 10 },
  ),
  // Pure whitespace / empty entries to exercise the drop path.
  fc.stringOf(fc.constantFrom(' ', '\t', '\n'), { minLength: 0, maxLength: 5 }),
);

const rawListArb = fc.array(rawEntryArb, { maxLength: 30 });

describe('variantBulkHelpers property tests', () => {
  /**
   * Property 1 (Normalization): for any list of raw strings, normalizeValues
   * returns each non-empty trimmed value exactly once, in first-seen order, with
   * no empty/whitespace-only entries.
   *
   * **Validates: Requirements 3.4, 3.5**
   */
  it('Property 1: normalizeValues trims, drops empties, de-dups, preserves first-seen order', () => {
    fc.assert(
      fc.property(rawListArb, (raw) => {
        const result = normalizeValues(raw);

        // No empty or whitespace-only entries remain.
        expect(result.every((v) => v.length > 0 && v.trim() === v)).toBe(true);

        // Each value appears exactly once (no duplicates).
        expect(new Set(result).size).toBe(result.length);

        // Independently compute the expected first-seen, trimmed, de-duped order.
        const expected: string[] = [];
        const seen = new Set<string>();
        for (const entry of raw) {
          const trimmed = entry.trim();
          if (trimmed.length === 0) continue;
          if (seen.has(trimmed)) continue;
          seen.add(trimmed);
          expected.push(trimmed);
        }
        expect(result).toEqual(expected);
      }),
      { numRuns: NUM_RUNS },
    );
  });

  /**
   * Property 2 (Preview count): for any requested values and existing values,
   * previewCreateCount equals the number of normalized requested values that are
   * NOT present in the existing set.
   *
   * **Validates: Requirements 3.7, 5.2**
   */
  it('Property 2: previewCreateCount equals normalized requested values absent from existing', () => {
    fc.assert(
      fc.property(rawListArb, fc.array(fc.string(), { maxLength: 30 }), (requested, existing) => {
        const count = previewCreateCount(requested, existing);

        const normalized = normalizeValues(requested);
        const existingSet = new Set(existing);
        const expected = normalized.filter((v) => !existingSet.has(v)).length;

        expect(count).toBe(expected);

        // Sanity bounds: never negative, never more than the distinct requested count.
        expect(count).toBeGreaterThanOrEqual(0);
        expect(count).toBeLessThanOrEqual(normalized.length);
      }),
      { numRuns: NUM_RUNS },
    );
  });
});
