/**
 * GenericMultiFilter — Checkbox-based multi-select dropdown filter
 *
 * Placeholder implementation. Full implementation in task 2.3.
 *
 * Uses Chakra UI Menu components for a checkbox multi-select dropdown.
 * Trigger button displays count of selected items or placeholder when empty.
 */

import React from 'react';
import {
  FormControl,
  FormLabel,
  Menu,
  MenuButton,
  MenuList,
  MenuOptionGroup,
  MenuItemOption,
  Button,
} from '@chakra-ui/react';
import { ChevronDownIcon } from '@chakra-ui/icons';
import { useTranslation } from 'react-i18next';
import type { GenericMultiFilterProps } from './types';

export function GenericMultiFilter({
  label,
  value,
  options,
  onChange,
  placeholder,
  isDisabled = false,
  width = '200px',
}: GenericMultiFilterProps): React.ReactElement {
  const { t } = useTranslation('common');

  const displayText =
    value.length === 0
      ? placeholder || t('alle', 'Alle')
      : t('nSelected', { count: value.length });

  return (
    <FormControl w={width}>
      <FormLabel fontSize="xs" color="orange.300" mb={1}>
        {label}
      </FormLabel>
      <Menu closeOnSelect={false}>
        <MenuButton
          as={Button}
          size="sm"
          rightIcon={<ChevronDownIcon />}
          bg="gray.700"
          borderColor="gray.600"
          borderWidth="1px"
          color="white"
          fontWeight="normal"
          isDisabled={isDisabled}
          w="100%"
          textAlign="left"
          _hover={{ bg: 'gray.600' }}
          _active={{ bg: 'gray.600' }}
          aria-label={`${label}: ${displayText}`}
        >
          {displayText}
        </MenuButton>
        <MenuList bg="gray.700" borderColor="gray.600">
          <MenuOptionGroup
            type="checkbox"
            value={value}
            onChange={(values) => onChange(values as string[])}
          >
            {options.map((opt) => (
              <MenuItemOption
                key={opt.value}
                value={opt.value}
                bg="gray.700"
                color="white"
                _hover={{ bg: 'gray.600' }}
              >
                {opt.label}
              </MenuItemOption>
            ))}
          </MenuOptionGroup>
        </MenuList>
      </Menu>
    </FormControl>
  );
}

export default GenericMultiFilter;
