/**
 * Property-based tests for useTableSort hook.
 *
 * **Validates: Requirements 1.2**
 *
 * Uses fast-check to verify:
 * 1. Sort stability: null/undefined values always appear at end regardless of direction
 * 2. Length preservation: sortedData always has same length as input
 * 3. Determinism: sorting same data twice produces same result
 * 4. Direction consistency: asc and desc produce reversed orderings (excluding nulls at end)
 */

import * as fc from 'fast-check';
import { renderHook } from '@testing-library/react';
import { useTableSort, compareValues } from '../useTableSort';
import { SortDirection } from '../../components/filters/types';

// ---------- Arbitraries ----------

/** Generates a value that is nullish (null or undefined) */
const nullishArb = fc.constantFrom(null, undefined);

/** Generates a non-null sortable value (number, string, or ISO date) */
const nonNullValueArb = fc.oneof(
  fc.integer({ min: -10000, max: 10000 }),
  fc.string({ minLength: 0, maxLength: 20 }),
  fc.date({ min: new Date('2000-01-01'), max: new Date('2030-12-31') }).map(
    (d) => d.toISOString().split('T')[0]
  )
);

/** Generates a value that may or may not be nullish */
const mixedValueArb = fc.oneof(nonNullValueArb, nullishArb);

/** Generates a sort direction */
const directionArb: fc.Arbitrary<SortDirection> = fc.constantFrom('asc', 'desc');

/** Generates an array of objects with a 'value' field that may contain nulls */
const dataWithNullsArb = fc
  .array(mixedValueArb, { minLength: 0, maxLength: 50 })
  .map((values) => values.map((v, i) => ({ id: i, value: v })));

/** Generates an array of objects with only non-null 'value' fields */
const dataWithoutNullsArb = fc
  .array(nonNullValueArb, { minLength: 0, maxLength: 50 })
  .map((values) => values.map((v, i) => ({ id: i, value: v })));

// ---------- Tests ----------

describe('useTableSort - Property Tests', () => {
  /**
   * **Validates: Requirements 1.2**
   *
   * Property: Null/undefined values always sort to end of sortedData,
   * regardless of sort direction (asc or desc).
   */
  it('null/undefined values always appear at the end regardless of direction', () => {
    fc.assert(
      fc.property(dataWithNullsArb, directionArb, (data, direction) => {
        const { result } = renderHook(() =>
          useTableSort(data, 'value', direction)
        );

        const sorted = result.current.sortedData;
        const nullIndices: number[] = [];
        const nonNullIndices: number[] = [];

        sorted.forEach((item, idx) => {
          if (item.value === null || item.value === undefined) {
            nullIndices.push(idx);
          } else {
            nonNullIndices.push(idx);
          }
        });

        // All null indices must come after all non-null indices
        if (nullIndices.length > 0 && nonNullIndices.length > 0) {
          const lastNonNull = Math.max(...nonNullIndices);
          const firstNull = Math.min(...nullIndices);
          return firstNull > lastNonNull;
        }
        return true;
      }),
      { numRuns: 50 }
    );
  });

  /**
   * **Validates: Requirements 1.2**
   *
   * Property: sortedData always has the same length as the input data array.
   * Sorting never adds or removes elements.
   */
  it('sortedData always preserves array length', () => {
    fc.assert(
      fc.property(dataWithNullsArb, directionArb, (data, direction) => {
        const { result } = renderHook(() =>
          useTableSort(data, 'value', direction)
        );

        return result.current.sortedData.length === data.length;
      }),
      { numRuns: 50 }
    );
  });

  /**
   * **Validates: Requirements 1.2**
   *
   * Property: Sorting the same data twice produces identical results.
   * compareValues is a deterministic comparator.
   */
  it('sorting same data twice produces identical result (determinism)', () => {
    fc.assert(
      fc.property(dataWithNullsArb, directionArb, (data, direction) => {
        const { result: result1 } = renderHook(() =>
          useTableSort(data, 'value', direction)
        );
        const { result: result2 } = renderHook(() =>
          useTableSort(data, 'value', direction)
        );

        const sorted1 = result1.current.sortedData;
        const sorted2 = result2.current.sortedData;

        if (sorted1.length !== sorted2.length) return false;

        for (let i = 0; i < sorted1.length; i++) {
          if (sorted1[i].value !== sorted2[i].value) return false;
        }
        return true;
      }),
      { numRuns: 50 }
    );
  });

  /**
   * **Validates: Requirements 1.2**
   *
   * Property: For data with no null values, sorting asc and desc produces
   * reversed orderings. The non-null portion of asc-sorted data reversed
   * equals the non-null portion of desc-sorted data.
   */
  it('asc and desc produce reversed orderings for non-null data', () => {
    fc.assert(
      fc.property(dataWithoutNullsArb, (data) => {
        const { result: ascResult } = renderHook(() =>
          useTableSort(data, 'value', 'asc')
        );
        const { result: descResult } = renderHook(() =>
          useTableSort(data, 'value', 'desc')
        );

        const ascValues = ascResult.current.sortedData.map((d) => d.value);
        const descValues = descResult.current.sortedData.map((d) => d.value);

        // Reversed asc should equal desc
        const reversedAsc = [...ascValues].reverse();

        if (reversedAsc.length !== descValues.length) return false;

        for (let i = 0; i < reversedAsc.length; i++) {
          if (reversedAsc[i] !== descValues[i]) return false;
        }
        return true;
      }),
      { numRuns: 50 }
    );
  });

  /**
   * **Validates: Requirements 1.2**
   *
   * Property: compareValues is consistent — for any two non-null values a and b,
   * compareValues(a, b) and compareValues(b, a) have opposite signs (or both zero).
   */
  it('compareValues is antisymmetric for non-null values', () => {
    fc.assert(
      fc.property(nonNullValueArb, nonNullValueArb, (a, b) => {
        const ab = compareValues(a, b);
        const ba = compareValues(b, a);

        // Antisymmetry: sign(ab) === -sign(ba)
        if (ab > 0) return ba < 0;
        if (ab < 0) return ba > 0;
        return ba === 0;
      }),
      { numRuns: 50 }
    );
  });
});
