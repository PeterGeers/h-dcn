/**
 * Property-based tests for optimistic locking (version check logic).
 *
 * Feature: closed-community-booking, Property 11
 * **Validates: Requirements 5.5, 5.6**
 *
 * Property 11: Optimistic Locking
 * For any order with version V, a save request specifying version V SHALL succeed
 * (and increment to V+1), while a save request specifying any version ≠ V SHALL
 * be rejected with a version conflict error.
 */

import * as fc from 'fast-check';
import {
  checkVersion,
  simulateSaveSequence,
  VersionCheckInput,
} from '../utils/versionCheck';

// --- Arbitraries ---

/** Non-negative integer for version numbers (realistic range) */
const versionArb = fc.integer({ min: 0, max: 10000 });

/** Version that matches the current (always succeeds) */
const matchingVersionInputArb: fc.Arbitrary<VersionCheckInput> = versionArb.map(
  (v) => ({ currentVersion: v, requestVersion: v })
);

/** Version that does NOT match the current (always fails) */
const mismatchedVersionInputArb: fc.Arbitrary<VersionCheckInput> = fc
  .tuple(versionArb, versionArb)
  .filter(([current, request]) => current !== request)
  .map(([currentVersion, requestVersion]) => ({ currentVersion, requestVersion }));

/** Any valid version check input */
const anyVersionInputArb: fc.Arbitrary<VersionCheckInput> = fc
  .tuple(versionArb, versionArb)
  .map(([currentVersion, requestVersion]) => ({ currentVersion, requestVersion }));

/** Sequence of consecutive saves (all correct versions) */
const consecutiveSaveCountArb = fc.integer({ min: 1, max: 20 });

// --- Property Tests ---

describe('Optimistic Locking - Property Tests', () => {
  /**
   * Property 11: A save request specifying the current version V SHALL succeed
   * and increment the version to V+1.
   *
   * **Validates: Requirements 5.5**
   */
  it('save with matching version always succeeds and increments to V+1', () => {
    fc.assert(
      fc.property(matchingVersionInputArb, (input) => {
        const result = checkVersion(input);

        expect(result.accepted).toBe(true);
        expect(result.newVersion).toBe(input.currentVersion + 1);
        expect(result.error).toBeNull();
      }),
      { numRuns: 200 }
    );
  });

  /**
   * Property 11: A save request specifying any version ≠ V SHALL be rejected
   * with a version conflict error.
   *
   * **Validates: Requirements 5.5, 5.6**
   */
  it('save with mismatched version always fails with VERSION_CONFLICT', () => {
    fc.assert(
      fc.property(mismatchedVersionInputArb, (input) => {
        const result = checkVersion(input);

        expect(result.accepted).toBe(false);
        expect(result.newVersion).toBeNull();
        expect(result.error).toBe('VERSION_CONFLICT');
      }),
      { numRuns: 200 }
    );
  });

  /**
   * Property 11: The result is always deterministic — same input produces
   * same output (accepted or rejected) regardless of call order.
   *
   * **Validates: Requirements 5.5**
   */
  it('version check is deterministic (same input → same result)', () => {
    fc.assert(
      fc.property(anyVersionInputArb, (input) => {
        const result1 = checkVersion(input);
        const result2 = checkVersion(input);

        expect(result1).toEqual(result2);
      }),
      { numRuns: 200 }
    );
  });

  /**
   * Property 11: For any version V, exactly one of two outcomes occurs:
   * accepted (when request === current) or rejected (when request !== current).
   * There is no third outcome.
   *
   * **Validates: Requirements 5.5, 5.6**
   */
  it('result is strictly binary: accepted XOR rejected for any input', () => {
    fc.assert(
      fc.property(anyVersionInputArb, (input) => {
        const result = checkVersion(input);

        // Exactly one of accepted/rejected
        if (input.requestVersion === input.currentVersion) {
          expect(result.accepted).toBe(true);
          expect(result.error).toBeNull();
        } else {
          expect(result.accepted).toBe(false);
          expect(result.error).toBe('VERSION_CONFLICT');
        }
      }),
      { numRuns: 200 }
    );
  });

  /**
   * Property 11: A sequence of saves each using the correct (current) version
   * SHALL all succeed, and the final version SHALL equal initialVersion + N.
   *
   * **Validates: Requirements 5.5**
   */
  it('N consecutive saves with correct versions all succeed and final version = initial + N', () => {
    fc.assert(
      fc.property(versionArb, consecutiveSaveCountArb, (initialVersion, n) => {
        // Build a sequence where each request uses the correct version
        const requestVersions: number[] = [];
        for (let i = 0; i < n; i++) {
          requestVersions.push(initialVersion + i);
        }

        const results = simulateSaveSequence(initialVersion, requestVersions);

        // All should succeed
        expect(results.every((r) => r.accepted)).toBe(true);

        // Final version should be initialVersion + n
        const lastResult = results[results.length - 1];
        expect(lastResult.newVersion).toBe(initialVersion + n);
      }),
      { numRuns: 200 }
    );
  });

  /**
   * Property 11: A stale version (any version < current) after another delegate
   * has saved SHALL always be rejected.
   *
   * **Validates: Requirements 5.6**
   */
  it('stale version after concurrent save is always rejected', () => {
    fc.assert(
      fc.property(
        versionArb,
        fc.integer({ min: 1, max: 50 }),
        (initialVersion, advanceBy) => {
          // Simulate: another delegate saved `advanceBy` times
          const currentVersion = initialVersion + advanceBy;

          // Our save attempt uses the stale version
          const result = checkVersion({
            currentVersion,
            requestVersion: initialVersion,
          });

          expect(result.accepted).toBe(false);
          expect(result.error).toBe('VERSION_CONFLICT');
        }
      ),
      { numRuns: 200 }
    );
  });

  /**
   * Property 11: A future version (> current) is also rejected — only exact
   * match is accepted.
   *
   * **Validates: Requirements 5.5**
   */
  it('future version (greater than current) is also rejected', () => {
    fc.assert(
      fc.property(
        versionArb,
        fc.integer({ min: 1, max: 100 }),
        (currentVersion, offset) => {
          const result = checkVersion({
            currentVersion,
            requestVersion: currentVersion + offset,
          });

          expect(result.accepted).toBe(false);
          expect(result.error).toBe('VERSION_CONFLICT');
        }
      ),
      { numRuns: 200 }
    );
  });

  /**
   * Property 11: In a mixed sequence of saves (some correct, some stale),
   * only saves with the correct version succeed.
   *
   * **Validates: Requirements 5.5, 5.6**
   */
  it('mixed sequence: only saves with correct version at time of check succeed', () => {
    // Generate a sequence mixing correct and stale versions
    const mixedSequenceArb = fc.tuple(
      versionArb,
      fc.array(
        fc.record({
          useCorrectVersion: fc.boolean(),
          offset: fc.integer({ min: 1, max: 10 }),
        }),
        { minLength: 1, maxLength: 10 }
      )
    );

    fc.assert(
      fc.property(mixedSequenceArb, ([initialVersion, steps]) => {
        let currentVersion = initialVersion;

        for (const step of steps) {
          const requestVersion = step.useCorrectVersion
            ? currentVersion
            : currentVersion + step.offset; // always wrong (offset ≥ 1)

          const result = checkVersion({ currentVersion, requestVersion });

          if (step.useCorrectVersion) {
            expect(result.accepted).toBe(true);
            expect(result.newVersion).toBe(currentVersion + 1);
            currentVersion = result.newVersion!;
          } else {
            expect(result.accepted).toBe(false);
            expect(result.error).toBe('VERSION_CONFLICT');
            // Version does NOT advance on failure
          }
        }
      }),
      { numRuns: 200 }
    );
  });
});
