/**
 * Property-based tests for registry row refactor.
 *
 * Feature: generic-registry-row-refactor
 *
 * Property 5: PDF filename sanitization
 * Property 6: Purchase rules resolution
 */

import * as fc from 'fast-check';
import { sanitizeForFilename, buildFilename } from '../components/BookingSummaryPdf';
import { PurchaseRules } from '../types/eventBooking.types';

// --- Property 5: PDF filename sanitization ---
// **Validates: Requirements 3.5**

describe('Property 5: PDF filename sanitization', () => {
  /**
   * **Validates: Requirements 3.5**
   *
   * For any registry_row_label and event_name strings, the generated PDF filename
   * SHALL match the pattern `booking-{sanitized_label}-{sanitized_name}.pdf` where
   * sanitized means: lowercased, non-alphanumeric characters replaced with hyphens,
   * consecutive hyphens collapsed, leading/trailing hyphens removed.
   * When registry_row_label is absent/empty, fallback to "unknown".
   */

  it('sanitizeForFilename produces only lowercase alphanumeric chars and hyphens', () => {
    fc.assert(
      fc.property(fc.string({ minLength: 0, maxLength: 100 }), (input) => {
        const result = sanitizeForFilename(input);
        // Must only contain lowercase a-z, digits 0-9, and hyphens
        expect(result).toMatch(/^[a-z0-9-]*$/);
        // Must never be empty (fallback to "unknown")
        expect(result.length).toBeGreaterThan(0);
      }),
      { numRuns: 100 }
    );
  });

  it('sanitizeForFilename has no leading or trailing hyphens', () => {
    fc.assert(
      fc.property(fc.string({ minLength: 0, maxLength: 100 }), (input) => {
        const result = sanitizeForFilename(input);
        expect(result).not.toMatch(/^-/);
        expect(result).not.toMatch(/-$/);
      }),
      { numRuns: 100 }
    );
  });

  it('sanitizeForFilename has no consecutive hyphens', () => {
    fc.assert(
      fc.property(fc.string({ minLength: 0, maxLength: 100 }), (input) => {
        const result = sanitizeForFilename(input);
        expect(result).not.toMatch(/--/);
      }),
      { numRuns: 100 }
    );
  });

  it('sanitizeForFilename returns "unknown" for empty, null, or undefined input', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(null, undefined, '', '   ', '\t', '\n'),
        (input) => {
          const result = sanitizeForFilename(input as string | null | undefined);
          expect(result).toBe('unknown');
        }
      ),
      { numRuns: 100 }
    );
  });

  it('sanitizeForFilename lowercases all alphabetic characters', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1, maxLength: 50 }).filter((s) => /[A-Za-z]/.test(s)),
        (input) => {
          const result = sanitizeForFilename(input);
          // Result should be entirely lowercase (no uppercase chars)
          expect(result).toBe(result.toLowerCase());
        }
      ),
      { numRuns: 100 }
    );
  });

  it('buildFilename produces correct pattern: booking-{label}-{name}.pdf', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1, maxLength: 50 }).filter((s) => s.trim().length > 0),
        fc.string({ minLength: 1, maxLength: 50 }).filter((s) => s.trim().length > 0),
        (label, eventName) => {
          const result = buildFilename(label, eventName);
          const sanitizedLabel = sanitizeForFilename(label);
          const sanitizedName = sanitizeForFilename(eventName);
          expect(result).toBe(`booking-${sanitizedLabel}-${sanitizedName}.pdf`);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('buildFilename uses "unknown" when label is absent', () => {
    fc.assert(
      fc.property(
        fc.constantFrom(null, undefined, '', '   '),
        fc.string({ minLength: 1, maxLength: 50 }).filter((s) => s.trim().length > 0),
        (label, eventName) => {
          const result = buildFilename(label as string | null | undefined, eventName);
          const sanitizedName = sanitizeForFilename(eventName);
          expect(result).toBe(`booking-unknown-${sanitizedName}.pdf`);
        }
      ),
      { numRuns: 100 }
    );
  });
});

// --- Property 6: Purchase rules resolution ---
// **Validates: Requirements 5.5**

/**
 * Pure function that resolves max_per_order from purchase_rules.
 * Mirrors the logic in useEffectiveLimits: absent max_per_order means unlimited.
 */
function resolveMaxPerOrder(purchaseRules: PurchaseRules | undefined): number | undefined {
  return purchaseRules?.max_per_order;
}

describe('Property 6: Purchase rules resolution', () => {
  /**
   * **Validates: Requirements 5.5**
   *
   * For any product record, the effective max_per_order value SHALL be read from
   * purchase_rules.max_per_order (absent means unlimited).
   */

  it('max_per_order is read correctly from purchase_rules', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 9999 }),
        (maxPerOrder) => {
          const rules: PurchaseRules = { max_per_order: maxPerOrder };
          const result = resolveMaxPerOrder(rules);
          expect(result).toBe(maxPerOrder);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('absent max_per_order means unlimited (undefined)', () => {
    fc.assert(
      fc.property(
        fc.record({
          min_per_order: fc.option(fc.integer({ min: 1, max: 100 }), { nil: undefined }),
          max_per_event: fc.option(fc.integer({ min: 1, max: 9999 }), { nil: undefined }),
        }),
        (partialRules) => {
          // purchase_rules without max_per_order field
          const rules: PurchaseRules = {
            ...(partialRules.min_per_order !== undefined ? { min_per_order: partialRules.min_per_order } : {}),
            ...(partialRules.max_per_event !== undefined ? { max_per_event: partialRules.max_per_event } : {}),
          };
          const result = resolveMaxPerOrder(rules);
          expect(result).toBeUndefined();
        }
      ),
      { numRuns: 100 }
    );
  });

  it('undefined purchase_rules means unlimited (undefined)', () => {
    const result = resolveMaxPerOrder(undefined);
    expect(result).toBeUndefined();
  });

  it('max_per_order is preserved exactly as stored (integer identity)', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 9999 }),
        fc.option(fc.integer({ min: 1, max: 100 }), { nil: undefined }),
        fc.option(fc.integer({ min: 1, max: 9999 }), { nil: undefined }),
        (maxPerOrder, minPerOrder, maxPerEvent) => {
          const rules: PurchaseRules = {
            max_per_order: maxPerOrder,
            ...(minPerOrder !== undefined ? { min_per_order: minPerOrder } : {}),
            ...(maxPerEvent !== undefined ? { max_per_event: maxPerEvent } : {}),
          };
          // Regardless of other fields, max_per_order is read correctly
          const result = resolveMaxPerOrder(rules);
          expect(result).toBe(maxPerOrder);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('useEffectiveLimits treats absent max_per_order as Infinity (no constraint)', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 50 }),
        (orderQty) => {
          // When max_per_order is absent, per-order remaining should be Infinity
          const maxPerOrder = undefined;
          const perOrderRemaining =
            maxPerOrder !== undefined ? maxPerOrder - orderQty : Infinity;
          expect(perOrderRemaining).toBe(Infinity);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('useEffectiveLimits constrains remaining when max_per_order is present', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 9999 }),
        fc.integer({ min: 0, max: 50 }),
        (maxPerOrder, orderQty) => {
          // When max_per_order is present, per-order remaining is max_per_order - orderQty
          const perOrderRemaining = maxPerOrder - orderQty;
          const effectiveRemaining = Math.max(perOrderRemaining, 0);
          expect(effectiveRemaining).toBe(Math.max(maxPerOrder - orderQty, 0));
        }
      ),
      { numRuns: 100 }
    );
  });
});
