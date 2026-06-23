/**
 * useFilterableTable — Composed hook: filter → sort pipeline
 *
 * Combines useColumnFilters and useTableSort into a single hook
 * for the most common table use case.
 *
 * Pipeline order: filter first → then sort (fixed order).
 *
 * Usage:
 *   const { filters, setFilter, handleSort, sortField, sortDirection, processedData } =
 *     useFilterableTable(data, { initialFilters: { name: '', status: '' }, defaultSort: { field: 'name', direction: 'asc' } });
 */

import { useMemo } from 'react';
import { useColumnFilters, UseColumnFiltersOptions } from './useColumnFilters';
import { useTableSort, UseTableSortOptions, SortDirection, SortConfig } from './useTableSort';

export interface UseFilterableTableOptions<T extends Record<string, string>> {
  /** Initial filter values */
  initialFilters: T;
  /** Default sort configuration */
  defaultSort?: SortConfig;
  /** Debounce delay for filters in ms (default: 150) */
  debounceMs?: number;
}

export interface UseFilterableTableReturn<T extends Record<string, string>, R extends Record<string, unknown>> {
  // Filter state
  filters: T;
  setFilter: (key: keyof T, value: string) => void;
  resetFilters: () => void;
  hasActiveFilters: boolean;

  // Sort state
  sortField: string | null;
  sortDirection: SortDirection;
  handleSort: (field: string) => void;
  sortConfig: SortConfig | null;

  // Processed data (filtered + sorted)
  processedData: R[];

  // Counts
  totalCount: number;
  filteredCount: number;
}

export function useFilterableTable<
  T extends Record<string, string>,
  R extends Record<string, unknown>
>(
  data: R[],
  options: UseFilterableTableOptions<T>
): UseFilterableTableReturn<T, R> {
  const { initialFilters, defaultSort, debounceMs } = options;

  // Filter layer
  const filterOptions: UseColumnFiltersOptions<T> = { initialFilters, debounceMs };
  const { filters, setFilter, resetFilters, filterData, hasActiveFilters } = useColumnFilters(filterOptions);

  // Sort layer
  const { sortField, sortDirection, handleSort, sortData, sortConfig } = useTableSort({ defaultSort });

  // Pipeline: filter → sort
  const processedData = useMemo(() => {
    const filtered = filterData(data);
    return sortData(filtered);
  }, [data, filterData, sortData]);

  return {
    filters,
    setFilter,
    resetFilters,
    hasActiveFilters,
    sortField,
    sortDirection,
    handleSort,
    sortConfig,
    processedData,
    totalCount: data.length,
    filteredCount: processedData.length,
  };
}

// Re-export types for convenience
export type { SortDirection, SortConfig } from './useTableSort';
