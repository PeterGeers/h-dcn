/**
 * ChannelFilter Component
 *
 * Dropdown filter for selecting which channel's data to display.
 * Used across all webshop management tabs for consistent channel filtering.
 */

import React from 'react';
import { FormControl, FormLabel, Select } from '@chakra-ui/react';

export interface ChannelFilterProps {
  /** Currently selected channel value */
  value: string;
  /** Callback when channel selection changes */
  onChange: (value: string) => void;
  /** Optional label for the dropdown (defaults to "Channel") */
  label?: string;
}

const CHANNEL_OPTIONS = [
  { value: '', label: 'Alle' },
  { value: 'presmeet', label: 'PresMeet' },
  { value: 'h-dcn', label: 'H-DCN' },
];

export const ChannelFilter: React.FC<ChannelFilterProps> = ({
  value,
  onChange,
  label = 'Channel',
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
        {CHANNEL_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </Select>
    </FormControl>
  );
};

/** @deprecated Use ChannelFilter instead */
export const TenantFilter = ChannelFilter;
/** @deprecated Use ChannelFilterProps instead */
export type TenantFilterProps = ChannelFilterProps;

export default ChannelFilter;
