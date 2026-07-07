/**
 * Table Filter Framework — Barrel Export
 *
 * Provides consistent, reusable filter and sort components for all tables.
 * Eliminates ~590 lines of boilerplate per table.
 *
 * Usage:
 *   import { FilterableHeader, FilterPanel, GenericFilter, YearFilter } from '../../components/filters';
 */

export { FilterableHeader } from './FilterableHeader';
export type { FilterableHeaderProps } from './FilterableHeader';

export { FilterPanel } from './FilterPanel';
export type { FilterPanelProps } from './FilterPanel';

export { GenericFilter } from './GenericFilter';
export type { GenericFilterProps, FilterOption, FilterOptionGroup } from './GenericFilter';

export { YearFilter } from './YearFilter';
export type { YearFilterProps } from './YearFilter';
