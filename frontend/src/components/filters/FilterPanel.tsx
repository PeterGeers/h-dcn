/**
 * FilterPanel Component
 *
 * A config-driven container component for organizing multiple filters with
 * flexible layout options. Accepts a `filters` prop array and renders one
 * filter control per entry.
 *
 * Supports horizontal, vertical, and grid layouts with responsive design.
 *
 * @module filters/FilterPanel
 */

import React from 'react';
import {
  Box,
  SimpleGrid,
  HStack,
  VStack,
  FormControl,
  FormLabel,
  Input,
} from '@chakra-ui/react';
import { GenericFilter } from './GenericFilter';
import { GenericMultiFilter } from './GenericMultiFilter';
import type { FilterConfig, FilterPanelLayout, SearchFilterConfig, FilterOption } from './types';

/**
 * FilterPanel props interface
 */
export interface FilterPanelProps {
  /** Array of filter configurations */
  filters: (FilterConfig<any> | SearchFilterConfig)[];

  /** Layout mode for organizing filters (default: 'horizontal') */
  layout?: FilterPanelLayout;

  /** Spacing between filters (default: 4) */
  spacing?: number;

  /** Number of columns for grid layout (default: 2) */
  gridColumns?: number;

  /** Minimum width for each filter in grid layout */
  gridMinWidth?: string;
}

/**
 * FilterPanel - Config-driven container for organizing multiple filters
 *
 * Provides flexible layout options for displaying multiple filter components
 * in a cohesive, responsive interface.
 *
 * **Layout Modes:**
 * - `horizontal`: Filters arranged in a row (HStack, wraps on overflow)
 * - `vertical`: Filters stacked vertically (VStack)
 * - `grid`: Filters arranged in a responsive SimpleGrid
 *
 * @example
 * <FilterPanel
 *   layout="horizontal"
 *   filters={[
 *     { type: 'single', label: 'Status', options: statusOpts, value: v, onChange: fn },
 *     { type: 'search', label: 'Zoeken', value: q, onChange: setQ },
 *   ]}
 * />
 */
export function FilterPanel({
  filters,
  layout = 'horizontal',
  spacing = 4,
  gridColumns = 2,
  gridMinWidth = '200px',
}: FilterPanelProps): React.ReactElement {
  const renderFilter = (
    filter: FilterConfig<any> | SearchFilterConfig,
    index: number
  ) => {
    const key = `filter-${index}-${filter.label}`;

    // Search filter → labelled Input
    if (filter.type === 'search') {
      const searchFilter = filter as SearchFilterConfig;
      return (
        <Box key={key} minW={layout === 'horizontal' ? '200px' : undefined}>
          <FormControl>
            <FormLabel fontSize="xs" color="orange.300" mb={1}>
              {searchFilter.label}
            </FormLabel>
            <Input
              size="sm"
              value={searchFilter.value}
              onChange={(e) => searchFilter.onChange(e.target.value)}
              placeholder={searchFilter.placeholder || ''}
              bg="gray.700"
              borderColor="gray.600"
              color="white"
              _focus={{ borderColor: 'orange.400' }}
            />
          </FormControl>
        </Box>
      );
    }

    // Multi-select filter → GenericMultiFilter
    if (filter.type === 'multi') {
      const multiFilter = filter as FilterConfig<any>;
      const options: FilterOption[] = (multiFilter.options || []).map(
        (opt: any) =>
          typeof opt === 'string' ? { value: opt, label: opt } : opt
      );
      const value: string[] = Array.isArray(multiFilter.value)
        ? multiFilter.value
        : [];

      return (
        <Box key={key} minW={layout === 'horizontal' ? '150px' : undefined}>
          <GenericMultiFilter
            label={multiFilter.label}
            value={value}
            options={options}
            onChange={(values: string[]) => multiFilter.onChange(values)}
            placeholder={multiFilter.placeholder}
            isDisabled={multiFilter.disabled}
          />
        </Box>
      );
    }

    // Single-select filter → GenericFilter
    const singleFilter = filter as FilterConfig<any>;
    const options: FilterOption[] = (singleFilter.options || []).map(
      (opt: any) =>
        typeof opt === 'string' ? { value: opt, label: opt } : opt
    );
    const value: string =
      typeof singleFilter.value === 'string' ? singleFilter.value : '';

    return (
      <Box key={key} minW={layout === 'horizontal' ? '150px' : undefined}>
        <GenericFilter
          label={singleFilter.label}
          value={value}
          options={options}
          onChange={(v: string) => singleFilter.onChange(v)}
          placeholder={singleFilter.placeholder}
          isDisabled={singleFilter.disabled}
        />
      </Box>
    );
  };

  switch (layout) {
    case 'vertical':
      return (
        <VStack spacing={spacing} align="stretch" width="100%">
          {filters.map((filter, index) => renderFilter(filter, index))}
        </VStack>
      );

    case 'grid':
      return (
        <SimpleGrid
          columns={{ base: 1, md: gridColumns }}
          spacing={spacing}
          width="100%"
          minChildWidth={gridMinWidth}
        >
          {filters.map((filter, index) => renderFilter(filter, index))}
        </SimpleGrid>
      );

    case 'horizontal':
    default:
      return (
        <HStack spacing={spacing} wrap="wrap" align="end" width="100%">
          {filters.map((filter, index) => renderFilter(filter, index))}
        </HStack>
      );
  }
}

export default FilterPanel;
