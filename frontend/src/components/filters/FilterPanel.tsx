/**
 * FilterPanel — Container for dropdown/multi-select filters above a table
 *
 * Provides consistent layout and styling for filter controls.
 * Includes a reset button when filters are active.
 *
 * Usage:
 *   <FilterPanel hasActiveFilters={hasActiveFilters} onReset={resetFilters}>
 *     <GenericFilter label="Status" value={filters.status} options={statusOptions} onChange={(v) => setFilter('status', v)} />
 *     <GenericFilter label="Regio" value={filters.regio} options={regioOptions} onChange={(v) => setFilter('regio', v)} />
 *   </FilterPanel>
 */

import React from 'react';
import { HStack, Button, Text } from '@chakra-ui/react';

export interface FilterPanelProps {
  /** Child filter components */
  children: React.ReactNode;
  /** Whether any filter is currently active */
  hasActiveFilters?: boolean;
  /** Callback to reset all filters */
  onReset?: () => void;
  /** Count of filtered results (optional, shown as "X resultaten") */
  filteredCount?: number;
  /** Total count (optional) */
  totalCount?: number;
}

export function FilterPanel({
  children,
  hasActiveFilters = false,
  onReset,
  filteredCount,
  totalCount,
}: FilterPanelProps) {
  return (
    <HStack
      spacing={4}
      mb={4}
      p={3}
      bg="gray.800"
      borderRadius="md"
      border="1px"
      borderColor="gray.600"
      flexWrap="wrap"
      align="flex-end"
    >
      {children}

      {hasActiveFilters && onReset && (
        <Button
          size="sm"
          variant="ghost"
          colorScheme="orange"
          onClick={onReset}
          alignSelf="flex-end"
        >
          Reset
        </Button>
      )}

      {filteredCount !== undefined && totalCount !== undefined && (
        <Text fontSize="xs" color="gray.400" alignSelf="flex-end" ml="auto">
          {filteredCount} / {totalCount} resultaten
        </Text>
      )}
    </HStack>
  );
}

export default FilterPanel;
