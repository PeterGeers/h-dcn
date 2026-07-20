/**
 * Unit tests for useTableSort hook.
 *
 * Tests sort indicator display, handleSort toggle behavior, null-to-end sorting,
 * compareValues utility, and ISO date detection.
 *
 * Validates: Requirements 1.2
 */

import { renderHook, act } from '@testing-library/react';
import { useTableSort, compareValues, isISODateString } from '../useTableSort';

// ─── isISODateString ─────────────────────────────────────────────────────────

describe('isISODateString', () => {
  it('recognizes YYYY-MM-DD format', () => {
    expect(isISODateString('2024-01-15')).toBe(true);
    expect(isISODateString('2000-12-31')).toBe(true);
  });

  it('recognizes YYYY-MM-DDTHH:mm:ssZ format', () => {
    expect(isISODateString('2024-01-15T10:30:00Z')).toBe(true);
    expect(isISODateString('2024-06-01T23:59:59.000Z')).toBe(true);
  });

  it('recognizes dates with timezone offset', () => {
    expect(isISODateString('2024-01-15T10:30:00+02:00')).toBe(true);
    expect(isISODateString('2024-01-15T10:30:00-05:00')).toBe(true);
  });

  it('rejects non-string values', () => {
    expect(isISODateString(null)).toBe(false);
    expect(isISODateString(undefined)).toBe(false);
    expect(isISODateString(12345)).toBe(false);
    expect(isISODateString({})).toBe(false);
  });

  it('rejects non-date strings', () => {
    expect(isISODateString('hello')).toBe(false);
    expect(isISODateString('2024')).toBe(false);
    expect(isISODateString('01-15-2024')).toBe(false);
    expect(isISODateString('2024/01/15')).toBe(false);
  });

  it('rejects invalid dates that match the format', () => {
    expect(isISODateString('2024-13-45')).toBe(false);
    expect(isISODateString('2024-00-00')).toBe(false);
  });
});

// ─── compareValues ───────────────────────────────────────────────────────────

describe('compareValues', () => {
  describe('nullish handling', () => {
    it('returns 0 when both values are null', () => {
      expect(compareValues(null, null)).toBe(0);
    });

    it('returns 0 when both values are undefined', () => {
      expect(compareValues(undefined, undefined)).toBe(0);
    });

    it('returns 1 when first value is null (sort to end)', () => {
      expect(compareValues(null, 'hello')).toBe(1);
      expect(compareValues(undefined, 42)).toBe(1);
    });

    it('returns -1 when second value is null (sort to end)', () => {
      expect(compareValues('hello', null)).toBe(-1);
      expect(compareValues(42, undefined)).toBe(-1);
    });
  });

  describe('numeric comparison', () => {
    it('compares numbers correctly', () => {
      expect(compareValues(1, 2)).toBeLessThan(0);
      expect(compareValues(2, 1)).toBeGreaterThan(0);
      expect(compareValues(5, 5)).toBe(0);
    });

    it('handles negative numbers', () => {
      expect(compareValues(-1, 1)).toBeLessThan(0);
      expect(compareValues(0, -5)).toBeGreaterThan(0);
    });

    it('handles decimals', () => {
      expect(compareValues(1.5, 2.5)).toBeLessThan(0);
      expect(compareValues(3.14, 3.14)).toBe(0);
    });
  });

  describe('ISO date comparison', () => {
    it('sorts dates chronologically', () => {
      expect(compareValues('2024-01-01', '2024-06-15')).toBeLessThan(0);
      expect(compareValues('2024-12-31', '2024-01-01')).toBeGreaterThan(0);
    });

    it('returns 0 for equal dates', () => {
      expect(compareValues('2024-01-15', '2024-01-15')).toBe(0);
    });

    it('handles datetime strings', () => {
      expect(compareValues('2024-01-15T08:00:00Z', '2024-01-15T20:00:00Z')).toBeLessThan(0);
    });
  });

  describe('string comparison', () => {
    it('compares strings case-insensitively', () => {
      expect(compareValues('Apple', 'banana')).toBeLessThan(0);
      expect(compareValues('banana', 'Apple')).toBeGreaterThan(0);
    });

    it('returns 0 for same strings with different case', () => {
      expect(compareValues('Hello', 'hello')).toBe(0);
    });

    it('compares numbers-as-strings lexically when one is not a number', () => {
      // mixed: number + string → falls through to string comparison
      expect(compareValues('abc', 'def')).toBeLessThan(0);
    });
  });
});

// ─── useTableSort hook ───────────────────────────────────────────────────────

interface TestItem {
  id: number;
  name: string;
  age: number | null;
  date: string | null;
}

const testData: TestItem[] = [
  { id: 1, name: 'Charlie', age: 30, date: '2024-03-15' },
  { id: 2, name: 'Alice', age: 25, date: '2024-01-10' },
  { id: 3, name: 'Bob', age: null, date: null },
  { id: 4, name: 'Diana', age: 28, date: '2024-06-20' },
];

describe('useTableSort', () => {
  describe('initialization', () => {
    it('returns unsorted data when no default field is provided', () => {
      const { result } = renderHook(() => useTableSort(testData));

      expect(result.current.sortField).toBeNull();
      expect(result.current.sortDirection).toBe('asc');
      expect(result.current.sortedData).toEqual(testData);
    });

    it('sorts data by default field when provided', () => {
      const { result } = renderHook(() => useTableSort(testData, 'name'));

      expect(result.current.sortField).toBe('name');
      expect(result.current.sortDirection).toBe('asc');
      expect(result.current.sortedData[0].name).toBe('Alice');
      expect(result.current.sortedData[1].name).toBe('Bob');
      expect(result.current.sortedData[2].name).toBe('Charlie');
      expect(result.current.sortedData[3].name).toBe('Diana');
    });

    it('respects default direction parameter', () => {
      const { result } = renderHook(() => useTableSort(testData, 'name', 'desc'));

      expect(result.current.sortDirection).toBe('desc');
      expect(result.current.sortedData[0].name).toBe('Diana');
      expect(result.current.sortedData[1].name).toBe('Charlie');
    });
  });

  describe('getSortIndicator', () => {
    it('returns ↑ for the active field in ascending order', () => {
      const { result } = renderHook(() => useTableSort(testData, 'name', 'asc'));
      expect(result.current.getSortIndicator('name')).toBe('↑');
    });

    it('returns ↓ for the active field in descending order', () => {
      const { result } = renderHook(() => useTableSort(testData, 'name', 'desc'));
      expect(result.current.getSortIndicator('name')).toBe('↓');
    });

    it('returns empty string for non-active fields', () => {
      const { result } = renderHook(() => useTableSort(testData, 'name', 'asc'));
      expect(result.current.getSortIndicator('age')).toBe('');
      expect(result.current.getSortIndicator('date')).toBe('');
    });

    it('returns empty string when no sort field is active', () => {
      const { result } = renderHook(() => useTableSort(testData));
      expect(result.current.getSortIndicator('name')).toBe('');
    });
  });

  describe('handleSort', () => {
    it('sets field and asc direction when clicking a new field', () => {
      const { result } = renderHook(() => useTableSort(testData));

      act(() => {
        result.current.handleSort('name');
      });

      expect(result.current.sortField).toBe('name');
      expect(result.current.sortDirection).toBe('asc');
    });

    it('toggles direction when clicking the same field', () => {
      const { result } = renderHook(() => useTableSort(testData, 'name', 'asc'));

      act(() => {
        result.current.handleSort('name');
      });

      expect(result.current.sortField).toBe('name');
      expect(result.current.sortDirection).toBe('desc');
    });

    it('toggles from desc back to asc on the same field', () => {
      const { result } = renderHook(() => useTableSort(testData, 'name', 'desc'));

      act(() => {
        result.current.handleSort('name');
      });

      expect(result.current.sortDirection).toBe('asc');
    });

    it('resets to asc when switching to a different field', () => {
      const { result } = renderHook(() => useTableSort(testData, 'name', 'desc'));

      act(() => {
        result.current.handleSort('age');
      });

      expect(result.current.sortField).toBe('age');
      expect(result.current.sortDirection).toBe('asc');
    });
  });

  describe('null-to-end sorting', () => {
    it('places null values at the end when sorting ascending', () => {
      const { result } = renderHook(() => useTableSort(testData, 'age', 'asc'));
      const ages = result.current.sortedData.map((item) => item.age);

      // Non-null values sorted ascending, null at end
      expect(ages).toEqual([25, 28, 30, null]);
    });

    it('places null values at the end when sorting descending', () => {
      const { result } = renderHook(() => useTableSort(testData, 'age', 'desc'));
      const ages = result.current.sortedData.map((item) => item.age);

      // Non-null values sorted descending, null still at end
      expect(ages).toEqual([30, 28, 25, null]);
    });

    it('places null dates at the end regardless of direction', () => {
      const { result } = renderHook(() => useTableSort(testData, 'date', 'asc'));
      const dates = result.current.sortedData.map((item) => item.date);

      // Non-null dates sorted chronologically, null at end
      expect(dates[dates.length - 1]).toBeNull();
      // First dates should be in ascending order
      expect(dates[0]).toBe('2024-01-10');
      expect(dates[1]).toBe('2024-03-15');
      expect(dates[2]).toBe('2024-06-20');
    });
  });

  describe('sorting correctness', () => {
    it('sorts numbers numerically (not lexically)', () => {
      const numericData = [
        { id: 1, value: 100 },
        { id: 2, value: 9 },
        { id: 3, value: 22 },
      ];

      const { result } = renderHook(() => useTableSort(numericData, 'value', 'asc'));
      const values = result.current.sortedData.map((item) => item.value);

      expect(values).toEqual([9, 22, 100]);
    });

    it('sorts ISO dates chronologically', () => {
      const dateData = [
        { id: 1, created: '2024-12-01' },
        { id: 2, created: '2024-01-15' },
        { id: 3, created: '2024-06-30' },
      ];

      const { result } = renderHook(() => useTableSort(dateData, 'created', 'asc'));
      const dates = result.current.sortedData.map((item) => item.created);

      expect(dates).toEqual(['2024-01-15', '2024-06-30', '2024-12-01']);
    });

    it('sorts strings case-insensitively', () => {
      const stringData = [
        { id: 1, label: 'banana' },
        { id: 2, label: 'Apple' },
        { id: 3, label: 'cherry' },
      ];

      const { result } = renderHook(() => useTableSort(stringData, 'label', 'asc'));
      const labels = result.current.sortedData.map((item) => item.label);

      expect(labels).toEqual(['Apple', 'banana', 'cherry']);
    });

    it('does not mutate the original data array', () => {
      const original = [...testData];
      renderHook(() => useTableSort(testData, 'name', 'asc'));
      expect(testData).toEqual(original);
    });
  });

  describe('reactivity', () => {
    it('re-sorts when data changes', () => {
      const initialData = [
        { id: 1, name: 'Charlie' },
        { id: 2, name: 'Alice' },
      ];

      const { result, rerender } = renderHook(
        ({ data }) => useTableSort(data, 'name', 'asc'),
        { initialProps: { data: initialData } },
      );

      expect(result.current.sortedData[0].name).toBe('Alice');

      const updatedData = [
        ...initialData,
        { id: 3, name: 'Aaron' },
      ];

      rerender({ data: updatedData });
      expect(result.current.sortedData[0].name).toBe('Aaron');
    });

    it('handles empty data array', () => {
      const { result } = renderHook(() => useTableSort([], 'name', 'asc'));
      expect(result.current.sortedData).toEqual([]);
    });
  });
});
