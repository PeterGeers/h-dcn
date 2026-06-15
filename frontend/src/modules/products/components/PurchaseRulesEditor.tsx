import React, { useCallback, useMemo } from 'react';
import {
  FormControl,
  FormLabel,
  FormErrorMessage,
  NumberInput,
  NumberInputField,
  NumberInputStepper,
  NumberIncrementStepper,
  NumberDecrementStepper,
  Switch,
  Select,
  VStack,
  HStack,
  Text,
} from '@chakra-ui/react';
import { PurchaseRules, OrderMode } from '../../webshop/types/unifiedProduct.types';
import { ORDER_MODE_OPTIONS, DEFAULT_ORDER_MODE, PURCHASE_RULES_LIMITS } from '../config/purchaseRulesConfig';

export interface PurchaseRulesEditorProps {
  /** Current purchase rules values */
  value: PurchaseRules;
  /** Callback when any field changes */
  onChange: (rules: PurchaseRules) => void;
  /** Optional field-level errors (keyed by field name) */
  errors?: Partial<Record<keyof PurchaseRules | 'min_max_club', string>>;
}

/**
 * PurchaseRulesEditor provides admin form inputs for configuring purchase rules
 * on a product: max_per_order, max_per_member, max_per_club, min_per_club,
 * requires_membership toggle, and order_mode select.
 *
 * All numeric fields are optional — empty means no constraint.
 * Validates that min_per_club ≤ max_per_club when both are set.
 *
 * Requirements: 13.1, 13.4, 13.5
 */
const PurchaseRulesEditor: React.FC<PurchaseRulesEditorProps> = ({
  value,
  onChange,
  errors,
}) => {
  const handleNumberChange = useCallback(
    (field: 'max_per_order' | 'max_per_member' | 'max_per_club' | 'min_per_club') =>
      (valueStr: string) => {
        const num = valueStr === '' ? undefined : parseInt(valueStr, 10);
        const updated: PurchaseRules = {
          ...value,
          [field]: isNaN(num as number) ? undefined : num,
        };
        onChange(updated);
      },
    [value, onChange]
  );

  const handleMembershipToggle = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      onChange({ ...value, requires_membership: e.target.checked });
    },
    [value, onChange]
  );

  const handleOrderModeChange = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      onChange({ ...value, order_mode: e.target.value as OrderMode });
    },
    [value, onChange]
  );

  // Validate min_per_club ≤ max_per_club
  const minMaxError = useMemo(() => {
    if (
      value.min_per_club != null &&
      value.max_per_club != null &&
      value.min_per_club > value.max_per_club
    ) {
      return 'Minimum per club kan niet hoger zijn dan maximum per club';
    }
    return errors?.min_max_club || undefined;
  }, [value.min_per_club, value.max_per_club, errors?.min_max_club]);

  return (
    <VStack spacing={4} align="stretch" w="100%">
      {/* Max per bestelling */}
      <FormControl isInvalid={!!errors?.max_per_order}>
        <FormLabel fontSize="sm" color="gray.300">Max per bestelling</FormLabel>
        <NumberInput
          min={PURCHASE_RULES_LIMITS.min}
          max={PURCHASE_RULES_LIMITS.max}
          value={value.max_per_order ?? ''}
          onChange={handleNumberChange('max_per_order')}
          size="sm"
        >
          <NumberInputField placeholder="Geen limiet" color="white" bg="gray.700" borderColor="gray.600" _placeholder={{ color: 'gray.400' }} />
          <NumberInputStepper>
            <NumberIncrementStepper />
            <NumberDecrementStepper />
          </NumberInputStepper>
        </NumberInput>
        {errors?.max_per_order && (
          <FormErrorMessage>{errors.max_per_order}</FormErrorMessage>
        )}
      </FormControl>

      {/* Max per lid */}
      <FormControl isInvalid={!!errors?.max_per_member}>
        <FormLabel fontSize="sm" color="gray.300">Max per lid</FormLabel>
        <NumberInput
          min={PURCHASE_RULES_LIMITS.min}
          max={PURCHASE_RULES_LIMITS.max}
          value={value.max_per_member ?? ''}
          onChange={handleNumberChange('max_per_member')}
          size="sm"
        >
          <NumberInputField placeholder="Geen limiet" color="white" bg="gray.700" borderColor="gray.600" _placeholder={{ color: 'gray.400' }} />
          <NumberInputStepper>
            <NumberIncrementStepper />
            <NumberDecrementStepper />
          </NumberInputStepper>
        </NumberInput>
        {errors?.max_per_member && (
          <FormErrorMessage>{errors.max_per_member}</FormErrorMessage>
        )}
      </FormControl>

      {/* Max per club */}
      <FormControl isInvalid={!!errors?.max_per_club || !!minMaxError}>
        <FormLabel fontSize="sm" color="gray.300">Max per club</FormLabel>
        <NumberInput
          min={PURCHASE_RULES_LIMITS.min}
          max={PURCHASE_RULES_LIMITS.max}
          value={value.max_per_club ?? ''}
          onChange={handleNumberChange('max_per_club')}
          size="sm"
        >
          <NumberInputField placeholder="Geen limiet" color="white" bg="gray.700" borderColor="gray.600" _placeholder={{ color: 'gray.400' }} />
          <NumberInputStepper>
            <NumberIncrementStepper />
            <NumberDecrementStepper />
          </NumberInputStepper>
        </NumberInput>
        {errors?.max_per_club && (
          <FormErrorMessage>{errors.max_per_club}</FormErrorMessage>
        )}
      </FormControl>

      {/* Min per club */}
      <FormControl isInvalid={!!errors?.min_per_club || !!minMaxError}>
        <FormLabel fontSize="sm" color="gray.300">Min per club</FormLabel>
        <NumberInput
          min={PURCHASE_RULES_LIMITS.min}
          max={PURCHASE_RULES_LIMITS.max}
          value={value.min_per_club ?? ''}
          onChange={handleNumberChange('min_per_club')}
          size="sm"
        >
          <NumberInputField placeholder="Geen minimum" color="white" bg="gray.700" borderColor="gray.600" _placeholder={{ color: 'gray.400' }} />
          <NumberInputStepper>
            <NumberIncrementStepper />
            <NumberDecrementStepper />
          </NumberInputStepper>
        </NumberInput>
        {errors?.min_per_club && (
          <FormErrorMessage>{errors.min_per_club}</FormErrorMessage>
        )}
        {minMaxError && !errors?.min_per_club && (
          <Text color="red.500" fontSize="xs" mt={1}>
            {minMaxError}
          </Text>
        )}
      </FormControl>

      {/* Lidmaatschap vereist */}
      <FormControl>
        <HStack justify="space-between">
          <FormLabel fontSize="sm" color="gray.300" mb={0}>
            Lidmaatschap vereist
          </FormLabel>
          <Switch
            size="sm"
            isChecked={value.requires_membership ?? false}
            onChange={handleMembershipToggle}
          />
        </HStack>
      </FormControl>

      {/* Bestelmodus */}
      <FormControl>
        <FormLabel fontSize="sm" color="gray.300">Bestelmodus</FormLabel>
        <Select
          size="sm"
          value={value.order_mode ?? DEFAULT_ORDER_MODE}
          onChange={handleOrderModeChange}
          color="white"
          bg="gray.700"
          borderColor="gray.600"
        >
          {ORDER_MODE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value} style={{ background: '#2D3748', color: 'white' }}>
              {option.label}
            </option>
          ))}
        </Select>
      </FormControl>
    </VStack>
  );
};

export default PurchaseRulesEditor;
