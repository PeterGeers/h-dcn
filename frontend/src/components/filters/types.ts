/**
 * Filter Type Definitions
 * 
 * This module provides TypeScript type definitions for the generic filter system.
 * These types enable type-safe filter configurations across the application.
 * 
 * @module filters/types
 */

/**
 * Filter type enumeration
 * Defines the available filter interaction modes
 */
export type FilterType = 'single' | 'multi' | 'range' | 'search';

/**
 * Base filter configuration interface
 * 
 * @template T - The type of data being filtered (e.g., string, object)
 */
export interface FilterConfig<T> {
  /** Filter interaction type */
  type: FilterType;
  
  /** Display label for the filter */
  label: string;
  
  /** Available options to select from */
  options: T[];
  
  /** Current selected value(s) - single value or array depending on type */
  value: T | T[];
  
  /** Callback when selection changes */
  onChange: (value: T | T[]) => void;
  
  /** Optional custom renderer for options */
  renderOption?: (option: T) => React.ReactNode;
  
  /** Optional function to extract display label from option */
  getOptionLabel?: (option: T) => string;
  
  /** Optional function to extract unique value from option */
  getOptionValue?: (option: T) => string;
  
  /** Optional placeholder text */
  placeholder?: string;
  
  /** Optional size variant */
  size?: 'sm' | 'md' | 'lg';
  
  /** Optional disabled state */
  disabled?: boolean;
  
  /** Optional loading state */
  isLoading?: boolean;
  
  /** Optional error message */
  error?: string | null;
  
  /** Treat empty selection as a valid choice (show orange background) */
  treatEmptyAsSelected?: boolean;
}


/**
 * Single-select filter configuration
 * 
 * Type-safe variant that enforces single value selection.
 * Use this when only one option can be selected at a time.
 * 
 * @template T - The type of data being filtered
 */
export interface SingleSelectFilterConfig<T> extends Omit<FilterConfig<T>, 'type' | 'value' | 'onChange'> {
  /** Filter type - always 'single' */
  type: 'single';
  
  /** Single selected value */
  value: T;
  
  /** Callback when selection changes - receives single value */
  onChange: (value: T) => void;
}

/**
 * Multi-select filter configuration
 * 
 * Type-safe variant that enforces array value selection.
 * Use this when multiple options can be selected simultaneously.
 * 
 * @template T - The type of data being filtered
 */
export interface MultiSelectFilterConfig<T> extends Omit<FilterConfig<T>, 'type' | 'value' | 'onChange'> {
  /** Filter type - always 'multi' */
  type: 'multi';
  
  /** Array of selected values */
  value: T[];
  
  /** Callback when selection changes - receives array of values */
  onChange: (values: T[]) => void;
}

/**
 * Range filter configuration
 * 
 * Type-safe variant for range-based filtering (e.g., date ranges, numeric ranges).
 * 
 * @template T - The type of data being filtered (typically number or Date)
 */
export interface RangeFilterConfig<T> extends Omit<FilterConfig<T>, 'type' | 'value' | 'onChange' | 'options'> {
  /** Filter type - always 'range' */
  type: 'range';
  
  /** Range value with min and max */
  value: { min: T; max: T };
  
  /** Callback when range changes */
  onChange: (value: { min: T; max: T }) => void;
  
  /** Optional minimum allowed value */
  minValue?: T;
  
  /** Optional maximum allowed value */
  maxValue?: T;
}

/**
 * Search filter configuration
 * 
 * Type-safe variant for text-based search filtering.
 */
export interface SearchFilterConfig extends Omit<FilterConfig<string>, 'type' | 'value' | 'onChange' | 'options'> {
  /** Filter type - always 'search' */
  type: 'search';
  
  /** Current search term */
  value: string;
  
  /** Callback when search term changes */
  onChange: (value: string) => void;
  
  /** Optional debounce delay in milliseconds */
  debounceMs?: number;
  
  /** Optional minimum character count before triggering search */
  minChars?: number;
}

/**
 * Filter panel layout options
 */
export type FilterPanelLayout = 'horizontal' | 'vertical' | 'grid';

/**
 * Filter panel configuration
 * 
 * Container configuration for multiple filters.
 */
export interface FilterPanelConfig {
  /** Array of filter configurations */
  filters: FilterConfig<any>[];
  
  /** Layout mode for the filter panel */
  layout?: FilterPanelLayout;
  
  /** Size variant for all filters */
  size?: 'sm' | 'md' | 'lg';
  
  /** Optional spacing between filters */
  spacing?: number;
  
  /** Optional disabled state for all filters */
  disabled?: boolean;
}

/**
 * Year generation mode for dynamic year options
 */
export type YearGenerationMode = 'historical' | 'future' | 'combined' | 'rolling';

/**
 * Year generation configuration
 * 
 * Configuration for generating year options dynamically.
 */
export interface YearGenerationConfig {
  /** Year generation mode */
  mode: YearGenerationMode;
  
  /** Historical years from database (for 'historical' and 'combined' modes) */
  historicalYears?: string[];
  
  /** Number of future years to generate (for 'future', 'combined', and 'rolling' modes) */
  futureCount?: number;
  
  /** Number of past years to include (for 'rolling' mode) */
  pastCount?: number;
}

/**
 * Filter option with label and value
 * 
 * Generic option type for filters that need separate display and value.
 */
export interface FilterOption {
  /** Unique value for the option */
  value: string;
  
  /** Display label for the option */
  label: string;
}

/**
 * Grouped filter options
 * 
 * Groups multiple FilterOption items under a label for grouped dropdowns.
 */
export interface FilterOptionGroup {
  /** Group label */
  label: string;
  
  /** Options within this group */
  options: FilterOption[];
}

// =============================================================================
// Table Filter Framework v2 — Type Definitions
// =============================================================================

/**
 * Column filter state: maps column keys to filter strings.
 * Used by `useColumnFilters` to track the current text filter value per column.
 */
export type ColumnFilterState = Record<string, string>;

/**
 * Sort direction for table column sorting.
 */
export type SortDirection = 'asc' | 'desc';

/**
 * Sort configuration specifying which field to sort and in which direction.
 */
export interface SortConfig {
  /** The column/field key to sort by */
  field: string;
  /** Sort direction */
  direction: SortDirection;
}

/**
 * Props for the FilterableHeader component.
 *
 * Renders a `<Th>` element with a column label, optional sort indicator,
 * and optional text filter `<Input>`. Used in the hybrid approach where
 * text search filters live inside column headers.
 */
export interface FilterableHeaderProps {
  /** Column label text */
  label: string;
  /** Current filter value (omit to disable filter input) */
  filterValue?: string;
  /** Callback when filter value changes */
  onFilterChange?: (value: string) => void;
  /** Enable sort indicator (default: false) */
  sortable?: boolean;
  /** Current sort direction for this column (null = not active) */
  sortDirection?: SortDirection | null;
  /** Callback when sort is toggled */
  onSort?: () => void;
  /** Placeholder text for filter input */
  placeholder?: string;
  /** Right-align for numeric columns */
  isNumeric?: boolean;
  /** Optional width constraint for the column (e.g., "60px", "120px") */
  w?: string;
  /** Optional min-width constraint for the column */
  minW?: string;
  /** Optional max-width constraint for the column */
  maxW?: string;
  /** Responsive display prop (e.g., { base: 'none', md: 'table-cell' }) */
  display?: string | Record<string, string>;
}

/**
 * Props for the GenericMultiFilter component.
 *
 * A checkbox-based multi-select dropdown using Chakra UI Menu components.
 */
export interface GenericMultiFilterProps {
  /** Filter label (rendered as FormLabel above trigger) */
  label: string;
  /** Currently selected values */
  value: string[];
  /** Available options */
  options: FilterOption[];
  /** Callback when selection changes */
  onChange: (values: string[]) => void;
  /** Placeholder when 0 selected (default: 'Alle') */
  placeholder?: string;
  /** Disabled state */
  isDisabled?: boolean;
  /** Trigger button width */
  width?: string;
}

/**
 * Options for the `useColumnFilters` hook.
 */
export interface UseColumnFiltersOptions {
  /** Debounce delay in milliseconds (default: 150) */
  debounceMs?: number;
}
