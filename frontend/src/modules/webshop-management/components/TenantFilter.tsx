/**
 * TenantFilter Component
 *
 * Dropdown filter for selecting which tenant's data to display.
 * Used across all webshop management tabs for consistent tenant filtering.
 */

import React from 'react';
import { FormControl, FormLabel, Select } from '@chakra-ui/react';

export interface TenantFilterProps {
  /** Currently selected tenant value */
  value: string;
  /** Callback when tenant selection changes */
  onChange: (value: string) => void;
  /** Optional label for the dropdown (defaults to "Tenant") */
  label?: string;
}

const TENANT_OPTIONS = [
  { value: '', label: 'Alle' },
  { value: 'presmeet', label: 'PresMeet' },
  { value: 'h-dcn', label: 'H-DCN' },
];

export const TenantFilter: React.FC<TenantFilterProps> = ({
  value,
  onChange,
  label = 'Tenant',
}) => {
  return (
    <FormControl maxW="200px">
      <FormLabel fontSize="sm" fontWeight="medium" mb={1}>
        {label}
      </FormLabel>
      <Select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        size="sm"
      >
        {TENANT_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </Select>
    </FormControl>
  );
};

export default TenantFilter;
