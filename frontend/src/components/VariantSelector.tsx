import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  Box,
  FormControl,
  FormLabel,
  Select,
  Text,
  Badge,
  VStack,
  HStack,
} from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import { VariantSchema, VariantRecord } from '../modules/webshop/types/unifiedProduct.types';
import { sortSizeValues } from '../modules/webshop-management/utils/sizeSorter';
import { deriveAxesFromVariants } from '../utils/variantUtils';

export interface VariantSelectorProps {
  /** Available variant records for the product */
  variants: VariantRecord[];
  /** Callback fired when a variant is resolved (or null if incomplete/no match) */
  onVariantSelect: (variant: VariantRecord | null) => void;
  /** Whether the selector is disabled (e.g., during loading) */
  isDisabled?: boolean;
}

/**
 * Resolves the matching variant based on current axis selections.
 * Returns the variant if all axes are selected and a match exists, null otherwise.
 */
export function resolveVariant(
  selections: Record<string, string>,
  variants: VariantRecord[],
  variantSchema: VariantSchema
): VariantRecord | null {
  const axes = Object.keys(variantSchema);

  // All axes must have a non-empty selection
  const allSelected = axes.every((axis) => selections[axis] && selections[axis] !== '');
  if (!allSelected) return null;

  // Find the variant whose variant_attributes match all selections
  const match = variants.find((variant) =>
    axes.every((axis) => variant.variant_attributes[axis] === selections[axis])
  );

  return match ?? null;
}

/**
 * VariantSelector renders a dropdown/select for each axis derived from active variant records.
 * It manages internal state for selections per axis. When all axes have a selection,
 * it resolves the matching variant and calls onVariantSelect with the result.
 *
 * - Uses deriveAxesFromVariants to compute axis→values map from active variants.
 * - Disables add-to-cart (via onVariantSelect(null)) until all axes are selected.
 * - Shows stock count when a variant is resolved.
 * - Shows "Niet op voorraad" when variant has stock=0 and allow_oversell=false.
 * - Shows "Combinatie niet beschikbaar" when no matching variant exists.
 * - Re-resolves on axis change.
 *
 * Requirements: 5.1, 5.2, 5.3
 */
const VariantSelector: React.FC<VariantSelectorProps> = ({
  variants,
  onVariantSelect,
  isDisabled = false,
}) => {
  const { t } = useTranslation('webshop');

  // Derive the variant schema from active variant records
  const variantSchema = useMemo(() => deriveAxesFromVariants(variants), [variants]);

  const axes = useMemo(() => Object.keys(variantSchema), [variantSchema]);

  // Internal state: one selection per axis
  const [selections, setSelections] = useState<Record<string, string>>({});

  // Reset selections when derived schema changes
  useEffect(() => {
    setSelections({});
  }, [variantSchema]);

  // Whether all axes have a value selected
  const allAxesSelected = useMemo(
    () => axes.length > 0 && axes.every((axis) => selections[axis] && selections[axis] !== ''),
    [axes, selections]
  );

  // Resolve the matching variant when all axes are selected
  const resolvedVariant = useMemo(
    () => (allAxesSelected ? resolveVariant(selections, variants, variantSchema) : null),
    [allAxesSelected, selections, variants, variantSchema]
  );

  // Notify parent of resolved variant (or null)
  useEffect(() => {
    onVariantSelect(resolvedVariant);
  }, [resolvedVariant]); // eslint-disable-line react-hooks/exhaustive-deps

  // Handle axis selection change - re-resolves automatically via useMemo
  const handleAxisChange = useCallback((axis: string, value: string) => {
    setSelections((prev) => ({
      ...prev,
      [axis]: value,
    }));
  }, []);

  // Derived display states
  const isOutOfStock =
    resolvedVariant !== null && resolvedVariant.stock <= 0 && !resolvedVariant.allow_oversell;

  const isCombinationUnavailable = allAxesSelected && resolvedVariant === null;

  return (
    <VStack spacing={3} align="stretch" role="group" aria-label="Variant selectie">
      {axes.map((axis) => (
        <FormControl key={axis} isDisabled={isDisabled}>
          <FormLabel fontSize="sm" fontWeight="medium" mb={1}>
            {axis}
          </FormLabel>
          <Select
            placeholder={t('variant.select_placeholder', { axis: axis.toLowerCase() })}
            value={selections[axis] || ''}
            onChange={(e) => handleAxisChange(axis, e.target.value)}
            aria-label={`Selecteer ${axis}`}
            size="md"
          >
            {sortSizeValues(variantSchema[axis]).map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </Select>
        </FormControl>
      ))}

      {/* Stock display when variant is resolved and available */}
      {resolvedVariant && !isOutOfStock && (
        <HStack aria-live="polite">
          <Badge colorScheme="green" fontSize="xs" px={2} py={0.5} borderRadius="sm">
            {t('variant.in_stock', { count: resolvedVariant.stock })}
          </Badge>
        </HStack>
      )}

      {/* Out of stock message */}
      {isOutOfStock && (
        <Box aria-live="assertive">
          <Badge colorScheme="red" fontSize="xs" px={2} py={0.5} borderRadius="sm">
            {t('variant.out_of_stock')}
          </Badge>
        </Box>
      )}

      {/* Combination unavailable message */}
      {isCombinationUnavailable && (
        <Text color="orange.500" fontSize="sm" aria-live="polite">
          {t('variant.combination_unavailable')}
        </Text>
      )}

      {/* Prompt to select all axes */}
      {!allAxesSelected && axes.length > 0 && (
        <Text color="gray.500" fontSize="xs">
          {t('variant.select_all_prompt')}
        </Text>
      )}
    </VStack>
  );
};

export default VariantSelector;
