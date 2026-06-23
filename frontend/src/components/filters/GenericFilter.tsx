/**
 * GenericFilter — Single dropdown or multi-select filter control
 *
 * Used inside FilterPanel for dropdown-style filters above the table.
 * Supports single-select (dropdown) and multi-select (checkboxes) modes.
 *
 * Usage:
 *   <GenericFilter
 *     label="Status"
 *     value={filters.status}
 *     options={[{ value: 'active', label: 'Actief' }, { value: 'archived', label: 'Gearchiveerd' }]}
 *     onChange={(v) => setFilter('status', v)}
 *   />
 */

import React from 'react';
import { FormControl, FormLabel, Select } from '@chakra-ui/react';

export interface FilterOption {
  value: string;
  label: string;
}

export interface GenericFilterProps {
  /** Filter label */
  label: string;
  /** Current selected value */
  value: string;
  /** Available options */
  options: FilterOption[];
  /** Callback when selection changes */
  onChange: (value: string) => void;
  /** Placeholder text for empty selection */
  placeholder?: string;
  /** Whether the filter is disabled */
  isDisabled?: boolean;
  /** Width of the filter control */
  width?: string;
  /** "All" option label (default: "Alle") */
  allLabel?: string;
}

export function GenericFilter({
  label,
  value,
  options,
  onChange,
  placeholder,
  isDisabled = false,
  width = '200px',
  allLabel = 'Alle',
}: GenericFilterProps) {
  return (
    <FormControl w={width}>
      <FormLabel fontSize="xs" color="orange.300" mb={1}>
        {label}
      </FormLabel>
      <Select
        size="sm"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        bg="gray.700"
        borderColor="gray.600"
        color="white"
        isDisabled={isDisabled}
        _focus={{ borderColor: 'orange.400' }}
      >
        <option value="" style={{ backgroundColor: '#2D3748', color: 'white' }}>
          {placeholder || allLabel}
        </option>
        {options.map((opt) => (
          <option
            key={opt.value}
            value={opt.value}
            style={{ backgroundColor: '#2D3748', color: 'white' }}
          >
            {opt.label}
          </option>
        ))}
      </Select>
    </FormControl>
  );
}

export default GenericFilter;
