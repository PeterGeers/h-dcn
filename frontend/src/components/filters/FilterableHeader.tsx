/**
 * FilterableHeader — Table header with inline text filter + sort indicator
 *
 * Replaces standard <Th> with a filterable, sortable column header.
 * Shows a text input for filtering and sort direction indicator.
 *
 * Usage:
 *   <FilterableHeader
 *     label="Naam"
 *     filterValue={filters.name}
 *     onFilterChange={(v) => setFilter('name', v)}
 *     sortable
 *     sortDirection={sortField === 'name' ? sortDirection : null}
 *     onSort={() => handleSort('name')}
 *   />
 */

import React from 'react';
import { Th, VStack, Text, Input, HStack } from '@chakra-ui/react';
import { TriangleUpIcon, TriangleDownIcon } from '@chakra-ui/icons';
import type { SortDirection } from '../../hooks/useTableSort';

export interface FilterableHeaderProps {
  /** Column label */
  label: string;
  /** Current filter value */
  filterValue?: string;
  /** Callback when filter changes */
  onFilterChange?: (value: string) => void;
  /** Whether this column is sortable */
  sortable?: boolean;
  /** Current sort direction (null = not sorted on this column) */
  sortDirection?: SortDirection | null;
  /** Callback when sort is toggled */
  onSort?: () => void;
  /** Minimum width for the column */
  minW?: string;
  /** Whether to show the filter input (default: true) */
  showFilter?: boolean;
  /** Placeholder for filter input */
  placeholder?: string;
  /** Additional Th props */
  display?: Record<string, string> | string;
}

export function FilterableHeader({
  label,
  filterValue = '',
  onFilterChange,
  sortable = false,
  sortDirection = null,
  onSort,
  minW = '100px',
  showFilter = true,
  placeholder,
  display,
}: FilterableHeaderProps) {
  return (
    <Th
      minW={minW}
      color="orange.300"
      verticalAlign="top"
      p={2}
      display={display as any}
    >
      <VStack spacing={1} align="stretch">
        {/* Label + sort indicator */}
        <HStack
          spacing={1}
          cursor={sortable ? 'pointer' : 'default'}
          onClick={sortable ? onSort : undefined}
          _hover={sortable ? { color: 'orange.200' } : undefined}
          userSelect="none"
        >
          <Text fontSize="xs" fontWeight="bold" textTransform="uppercase">
            {label}
          </Text>
          {sortable && sortDirection === 'asc' && (
            <TriangleUpIcon boxSize={3} color="orange.400" />
          )}
          {sortable && sortDirection === 'desc' && (
            <TriangleDownIcon boxSize={3} color="orange.400" />
          )}
        </HStack>

        {/* Filter input */}
        {showFilter && onFilterChange && (
          <Input
            size="xs"
            value={filterValue}
            onChange={(e) => onFilterChange(e.target.value)}
            placeholder={placeholder || `Filter...`}
            bg="gray.700"
            borderColor="gray.600"
            color="white"
            _placeholder={{ color: 'gray.500' }}
            _focus={{ borderColor: 'orange.400' }}
          />
        )}
      </VStack>
    </Th>
  );
}

export default FilterableHeader;
