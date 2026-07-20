/**
 * Table Filter Framework — Barrel Export
 *
 * Provides consistent, reusable filter and sort components for all tables.
 * Eliminates ~590 lines of boilerplate per table.
 *
 * Usage:
 *   import { FilterableHeader, FilterPanel, GenericFilter, GenericMultiFilter, YearFilter } from '../../components/filters';
 */

// Components
export { FilterableHeader } from './FilterableHeader';
export { FilterPanel } from './FilterPanel';
export { GenericFilter } from './GenericFilter';
export { GenericMultiFilter } from './GenericMultiFilter';
export { YearFilter } from './YearFilter';

// Component prop types
export type { FilterableHeaderProps, GenericMultiFilterProps } from './types';
export type { FilterPanelProps } from './FilterPanel';
export type { GenericFilterProps } from './GenericFilter';
export type { YearFilterProps } from './YearFilter';

// Shared filter option types
export type { FilterOption, FilterOptionGroup } from './types';

// Shared framework types
export type {
  FilterType,
  FilterConfig,
  SingleSelectFilterConfig,
  MultiSelectFilterConfig,
  SearchFilterConfig,
  SortDirection,
  SortConfig,
  ColumnFilterState,
  UseColumnFiltersOptions,
  FilterPanelLayout,
} from './types';
