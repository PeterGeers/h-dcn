/**
 * useColumnFilters — Filter state + debounced substring matching
 *
 * Provides filter state management with case-insensitive substring matching.
 * Debounced for performance (150ms default).
 *
 * Usage:
 *   const { filters, setFilter, resetFilters, filterData } = useColumnFilters(INITIAL_FILTERS);
 *   const filtered = filterData(data);
 */

import { useState, useCallback, useMemo, useRef, useEffect } from 'react';

export interface UseColumnFiltersOptions<T extends Record<string, string>> {
  /** Initial filter values (all empty strings) */
  initialFilters: T;
  /** Debounce delay in ms (default: 150) */
  debounceMs?: number;
}

export interface UseColumnFiltersReturn<T extends Record<string, string>> {
  /** Current filter values */
  filters: T;
  /** Set a single filter value */
  setFilter: (key: keyof T, value: string) => void;
  /** Reset all filters to initial values */
  resetFilters: () => void;
  /** Filter data array using current filters */
  filterData: <R extends Record<string, unknown>>(data: R[]) => R[];
  /** Whether any filter is active */
  hasActiveFilters: boolean;
}

export function useColumnFilters<T extends Record<string, string>>(
  options: UseColumnFiltersOptions<T>
): UseColumnFiltersReturn<T> {
  const { initialFilters, debounceMs = 150 } = options;
  const [filters, setFilters] = useState<T>({ ...initialFilters });
  const [debouncedFilters, setDebouncedFilters] = useState<T>({ ...initialFilters });
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Debounce filter updates
  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      setDebouncedFilters({ ...filters });
    }, debounceMs);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [filters, debounceMs]);

  const setFilter = useCallback((key: keyof T, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  }, []);

  const resetFilters = useCallback(() => {
    setFilters({ ...initialFilters });
  }, [initialFilters]);

  const hasActiveFilters = useMemo(
    () => Object.values(debouncedFilters).some(v => v !== ''),
    [debouncedFilters]
  );

  const filterData = useCallback(
    <R extends Record<string, unknown>>(data: R[]): R[] => {
      if (!hasActiveFilters) return data;

      return data.filter(row => {
        return Object.entries(debouncedFilters).every(([key, filterValue]) => {
          if (!filterValue) return true; // Empty filter = pass

          const cellValue = row[key];
          // If field doesn't exist on row, pass (not excluded)
          if (cellValue === undefined || cellValue === null) return true;

          const cellStr = String(cellValue).toLowerCase();
          const filterStr = (filterValue as string).toLowerCase();
          return cellStr.includes(filterStr);
        });
      });
    },
    [debouncedFilters, hasActiveFilters]
  );

  return { filters, setFilter, resetFilters, filterData, hasActiveFilters };
}
