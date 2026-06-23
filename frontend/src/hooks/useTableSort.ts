/**
 * useTableSort — Sort state + toggle + comparison logic
 *
 * Provides sort state management with string/number/date comparison.
 * Null/undefined values sort to end regardless of direction.
 *
 * Usage:
 *   const { sortField, sortDirection, handleSort, sortData } = useTableSort({ field: 'name', direction: 'asc' });
 *   const sorted = sortData(data);
 */

import { useState, useCallback, useMemo } from 'react';

export type SortDirection = 'asc' | 'desc';

export interface SortConfig {
  field: string;
  direction: SortDirection;
}

export interface UseTableSortOptions {
  /** Default sort configuration */
  defaultSort?: SortConfig;
}

export interface UseTableSortReturn {
  /** Currently sorted field */
  sortField: string | null;
  /** Current sort direction */
  sortDirection: SortDirection;
  /** Toggle sort on a field (cycles: asc → desc → none) */
  handleSort: (field: string) => void;
  /** Sort data array using current sort config */
  sortData: <R extends Record<string, unknown>>(data: R[]) => R[];
  /** Current sort config (null if no sort active) */
  sortConfig: SortConfig | null;
}

function compareValues(a: unknown, b: unknown, direction: SortDirection): number {
  // Null/undefined sort to end
  if (a === null || a === undefined) return 1;
  if (b === null || b === undefined) return -1;

  const multiplier = direction === 'asc' ? 1 : -1;

  // Number comparison
  if (typeof a === 'number' && typeof b === 'number') {
    return (a - b) * multiplier;
  }

  // String comparison (case-insensitive)
  const strA = String(a).toLowerCase();
  const strB = String(b).toLowerCase();

  // Try date comparison
  if (isDateString(strA) && isDateString(strB)) {
    const dateA = new Date(strA).getTime();
    const dateB = new Date(strB).getTime();
    if (!isNaN(dateA) && !isNaN(dateB)) {
      return (dateA - dateB) * multiplier;
    }
  }

  // Try numeric comparison for string numbers
  const numA = parseFloat(strA);
  const numB = parseFloat(strB);
  if (!isNaN(numA) && !isNaN(numB)) {
    return (numA - numB) * multiplier;
  }

  return strA.localeCompare(strB, 'nl') * multiplier;
}

function isDateString(value: string): boolean {
  return /^\d{4}-\d{2}-\d{2}/.test(value);
}

export function useTableSort(options: UseTableSortOptions = {}): UseTableSortReturn {
  const { defaultSort } = options;
  const [sortConfig, setSortConfig] = useState<SortConfig | null>(defaultSort || null);

  const sortField = sortConfig?.field || null;
  const sortDirection = sortConfig?.direction || 'asc';

  const handleSort = useCallback((field: string) => {
    setSortConfig(current => {
      if (!current || current.field !== field) {
        return { field, direction: 'asc' };
      }
      if (current.direction === 'asc') {
        return { field, direction: 'desc' };
      }
      // Third click: remove sort
      return null;
    });
  }, []);

  const sortData = useCallback(
    <R extends Record<string, unknown>>(data: R[]): R[] => {
      if (!sortConfig) return data;

      return [...data].sort((a, b) => {
        const aVal = a[sortConfig.field];
        const bVal = b[sortConfig.field];
        return compareValues(aVal, bVal, sortConfig.direction);
      });
    },
    [sortConfig]
  );

  return {
    sortField,
    sortDirection,
    handleSort,
    sortData,
    sortConfig,
  };
}
