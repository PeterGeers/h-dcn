/**
 * YearFilter — Year-specific dropdown filter
 *
 * Generates year options dynamically from a start year to the current year.
 * Commonly used for filtering events, orders, or members by year.
 *
 * Usage:
 *   <YearFilter value={filters.year} onChange={(v) => setFilter('year', v)} startYear={2020} />
 */

import React, { useMemo } from 'react';
import { GenericFilter } from './GenericFilter';
import type { FilterOption } from './GenericFilter';

export interface YearFilterProps {
  /** Current selected year (empty string = all) */
  value: string;
  /** Callback when year changes */
  onChange: (value: string) => void;
  /** First year to show (default: 2020) */
  startYear?: number;
  /** Last year to show (default: current year + 1) */
  endYear?: number;
  /** Label (default: "Jaar") */
  label?: string;
  /** Whether disabled */
  isDisabled?: boolean;
}

export function YearFilter({
  value,
  onChange,
  startYear = 2020,
  endYear,
  label = 'Jaar',
  isDisabled = false,
}: YearFilterProps) {
  const options: FilterOption[] = useMemo(() => {
    const end = endYear || new Date().getFullYear() + 1;
    const years: FilterOption[] = [];
    for (let year = end; year >= startYear; year--) {
      years.push({ value: String(year), label: String(year) });
    }
    return years;
  }, [startYear, endYear]);

  return (
    <GenericFilter
      label={label}
      value={value}
      options={options}
      onChange={onChange}
      placeholder="Alle jaren"
      isDisabled={isDisabled}
      width="140px"
    />
  );
}

export default YearFilter;
