/**
 * GenericFilter — Single dropdown filter control with optional option groups
 *
 * Used inside FilterPanel for dropdown-style filters above the table.
 * Supports flat options or grouped options (optgroup).
 *
 * Usage (flat):
 *   <GenericFilter
 *     label="Status"
 *     value={filters.status}
 *     options={[{ value: 'active', label: 'Actief' }, { value: 'archived', label: 'Gearchiveerd' }]}
 *     onChange={(v) => setFilter('status', v)}
 *   />
 *
 * Usage (grouped):
 *   <GenericFilter
 *     label="Type"
 *     value={filters.type}
 *     groups={[
 *       { label: 'Vergaderingen', options: [{ value: 'alv', label: 'ALV' }] },
 *       { label: 'Ritten', options: [{ value: 'openingsrit', label: 'Openingsrit' }] },
 *     ]}
 *     onChange={(v) => setFilter('type', v)}
 *   />
 */

import React from 'react';
import { FormControl, FormLabel, Select } from '@chakra-ui/react';

export interface FilterOption {
  value: string;
  label: string;
}

export interface FilterOptionGroup {
  /** Group label (rendered as optgroup label) */
  label: string;
  /** Options within this group */
  options: FilterOption[];
}

export interface GenericFilterProps {
  /** Filter label */
  label: string;
  /** Current selected value */
  value: string;
  /** Flat list of options (use this OR groups, not both) */
  options?: FilterOption[];
  /** Grouped options with optgroup labels (use this OR options, not both) */
  groups?: FilterOptionGroup[];
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
  /** Border color override (default: "gray.600") */
  borderColor?: string;
}

const OPTION_STYLE = { backgroundColor: '#2D3748', color: 'white' };

export function GenericFilter({
  label,
  value,
  options,
  groups,
  onChange,
  placeholder,
  isDisabled = false,
  width = '200px',
  allLabel = 'Alle',
  borderColor = 'gray.600',
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
        borderColor={borderColor}
        color="white"
        isDisabled={isDisabled}
        _focus={{ borderColor: 'orange.400' }}
        sx={{
          option: { background: '#2D3748', color: 'white' },
          optgroup: { background: '#2D3748', color: '#A0AEC0', fontStyle: 'normal' },
        }}
      >
        <option value="" style={OPTION_STYLE}>
          {placeholder || allLabel}
        </option>
        {groups
          ? groups.map((group) => (
              <optgroup key={group.label} label={group.label}>
                {group.options.map((opt) => (
                  <option key={opt.value} value={opt.value} style={OPTION_STYLE}>
                    {opt.label}
                  </option>
                ))}
              </optgroup>
            ))
          : options?.map((opt) => (
              <option key={opt.value} value={opt.value} style={OPTION_STYLE}>
                {opt.label}
              </option>
            ))}
      </Select>
    </FormControl>
  );
}

export default GenericFilter;
