import * as fc from 'fast-check';
import { shouldDefaultOpen } from '../modules/products/utils/collapsibleHelpers';

// Feature: product-variant-simplification, Property 7: CollapsibleSection default state follows data

/**
 * Property-based tests for CollapsibleSection default state logic.
 * Uses fast-check with minimum 100 iterations per property.
 *
 * **Validates: Requirements 10.2**
 */

const NUM_RUNS = 100;

// --- Generators ---

/**
 * Generator for a non-empty image URL string (simulates S3 URLs).
 */
const imageUrlArb = fc.stringOf(
  fc.constantFrom(...'abcdefghijklmnopqrstuvwxyz0123456789-_/.'.split('')),
  { minLength: 1, maxLength: 80 },
).map((s) => `https://s3.eu-west-1.amazonaws.com/bucket/${s}`);

/**
 * Generator for a non-empty images array.
 */
const nonEmptyImagesArb = fc.array(imageUrlArb, { minLength: 1, maxLength: 20 });

/**
 * Generator for an empty images array.
 */
const emptyImagesArb = fc.constant([] as string[]);

// --- Property 7: CollapsibleSection default state follows data ---

describe('CollapsibleSection shouldDefaultOpen property tests', () => {
  /**
   * Property 7a: For any non-empty array of strings, shouldDefaultOpen returns true (section expanded).
   */
  describe('Property 7a: Non-empty images array expands the section', () => {
    it('shouldDefaultOpen returns true for any non-empty string array', () => {
      fc.assert(
        fc.property(nonEmptyImagesArb, (images) => {
          expect(shouldDefaultOpen(images)).toBe(true);
        }),
        { numRuns: NUM_RUNS },
      );
    });
  });

  /**
   * Property 7b: For an empty array, shouldDefaultOpen returns false (section collapsed).
   */
  describe('Property 7b: Empty images array collapses the section', () => {
    it('shouldDefaultOpen returns false for an empty array', () => {
      fc.assert(
        fc.property(emptyImagesArb, (images) => {
          expect(shouldDefaultOpen(images)).toBe(false);
        }),
        { numRuns: NUM_RUNS },
      );
    });
  });

  /**
   * Property 7c: For undefined or null, shouldDefaultOpen returns false (section collapsed).
   */
  describe('Property 7c: Undefined/null collapses the section', () => {
    it('shouldDefaultOpen returns false for undefined or null', () => {
      fc.assert(
        fc.property(
          fc.constantFrom(undefined, null),
          (images) => {
            expect(shouldDefaultOpen(images)).toBe(false);
          },
        ),
        { numRuns: NUM_RUNS },
      );
    });
  });

  /**
   * Property 7d: The return value is strictly determined by array length —
   * shouldDefaultOpen(arr) === (arr.length > 0) for any defined array.
   */
  describe('Property 7d: Return value equals (length > 0) for any defined array', () => {
    it('shouldDefaultOpen(arr) === (arr.length > 0) for arbitrary string arrays', () => {
      fc.assert(
        fc.property(
          fc.array(imageUrlArb, { minLength: 0, maxLength: 20 }),
          (images) => {
            expect(shouldDefaultOpen(images)).toBe(images.length > 0);
          },
        ),
        { numRuns: NUM_RUNS },
      );
    });
  });
});
