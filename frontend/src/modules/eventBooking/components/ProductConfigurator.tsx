/**
 * ProductConfigurator — Dynamically renders form fields for a product.
 *
 * Based on the product's order_item_fields definition, renders the appropriate
 * input elements (text, select, number, date). Also handles variant selection
 * using the shared VariantSelector component + useProductVariants hook.
 *
 * Validates: Requirements 7.6, 7.7
 */

import React, { useCallback } from 'react';
import {
  Box,
  FormControl,
  FormErrorMessage,
  FormLabel,
  HStack,
  Image,
  Input,
  NumberDecrementStepper,
  NumberIncrementStepper,
  NumberInput,
  NumberInputField,
  NumberInputStepper,
  Select,
  Spinner,
  Text,
} from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import { OrderItemField, Product } from '../types/eventBooking.types';
import { formatCurrency } from '../utils/priceCalculator';
import { useProductVariants } from '../../../hooks/useProductVariants';
import VariantSelector from '../../../components/VariantSelector';
import { VariantRecord } from '../../webshop/types/unifiedProduct.types';

export interface ProductConfiguratorProps {
  product: Product;
  fields: Record<string, any>;
  variantId: string | null;
  onChange: (fields: Record<string, any>, variantId: string | null) => void;
  isDisabled?: boolean;
  /** Validation errors keyed by field id */
  fieldErrors?: Record<string, string>;
}

/**
 * Check whether a product requires variant selection but doesn't yet have one resolved.
 */
export function isVariantSelectionIncomplete(
  product: Product,
  _fields: Record<string, any>,
  variantId: string | null
): boolean {
  // This is now a simplified check — if the product has is_parent set,
  // it likely has variants. The actual check happens via useProductVariants.
  if (product.is_parent === false) {
    return false;
  }
  // If variantId is provided, selection is complete
  if (variantId) {
    return false;
  }
  // We can't know for sure without variant data, so return true to be safe
  // The component itself will handle the loading state
  return product.is_parent === true;
}

/**
 * Render the appropriate input element for a given field type.
 */
function renderField(
  field: OrderItemField,
  value: any,
  onChange: (value: any) => void,
  isDisabled: boolean
): React.ReactElement {
  switch (field.type) {
    case 'select':
      return (
        <Select
          size="sm"
          value={value || ''}
          onChange={(e) => onChange(e.target.value)}
          isDisabled={isDisabled}
          placeholder={`Select ${field.label}`}
          bg="gray.700"
          color="white"
          borderColor="gray.600"
          _placeholder={{ color: 'gray.400' }}
        >
          {(field.options || []).map((opt) => (
            <option key={opt} value={opt} style={{ backgroundColor: '#2D3748', color: 'white' }}>{opt}</option>
          ))}
        </Select>
      );

    case 'number':
      return (
        <NumberInput
          size="sm"
          value={value ?? ''}
          min={field.min}
          max={field.max}
          onChange={(_, val) => onChange(isNaN(val) ? '' : val)}
          isDisabled={isDisabled}
        >
          <NumberInputField />
          <NumberInputStepper>
            <NumberIncrementStepper />
            <NumberDecrementStepper />
          </NumberInputStepper>
        </NumberInput>
      );

    case 'date':
      return (
        <Input
          size="sm"
          type="date"
          value={value || ''}
          onChange={(e) => onChange(e.target.value)}
          isDisabled={isDisabled}
        />
      );

    case 'text':
    default:
      return (
        <Input
          size="sm"
          value={value || ''}
          onChange={(e) => onChange(e.target.value)}
          isDisabled={isDisabled}
          placeholder={field.label}
        />
      );
  }
}

const ProductConfigurator: React.FC<ProductConfiguratorProps> = ({
  product,
  fields,
  variantId,
  onChange,
  isDisabled = false,
  fieldErrors = {},
}) => {
  const { t } = useTranslation('eventBooking');

  // Fetch variants using the shared hook
  const { variants, loading: loadingVariants, error: variantError, hasVariantAxes } =
    useProductVariants(product.product_id, true);

  // Handle variant selection from the shared VariantSelector
  const handleVariantSelect = useCallback(
    (variant: VariantRecord | null) => {
      const newVariantId = variant?.product_id ?? null;
      // Only trigger onChange if the variant actually changed
      if (newVariantId !== variantId) {
        onChange(fields, newVariantId);
      }
    },
    [fields, variantId, onChange]
  );

  const handleFieldChange = (fieldId: string, value: any) => {
    const updatedFields = { ...fields, [fieldId]: value };
    onChange(updatedFields, variantId);
  };

  // First image URL for thumbnail
  const thumbnailUrl = product.images && product.images.length > 0 ? product.images[0] : null;

  return (
    <Box pl={4} borderLeftWidth={2} borderLeftColor="blue.200" mt={2}>
      <HStack spacing={2} mb={2} align="center">
        {thumbnailUrl && (
          <Image
            src={thumbnailUrl}
            alt={product.naam}
            boxSize="48px"
            objectFit="cover"
            borderRadius="md"
            flexShrink={0}
            onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
          />
        )}
        <Text fontSize="sm" fontWeight="medium">
          {product.naam}
          <Text as="span" color="gray.500" ml={2}>
            {formatCurrency(product.prijs)}
          </Text>
        </Text>
      </HStack>

      {/* Variant selector — uses the shared VariantSelector component */}
      {loadingVariants && (
        <HStack spacing={2} mb={2}>
          <Spinner size="xs" />
          <Text fontSize="xs" color="gray.500">
            {t('product_configurator.loading_variants', { defaultValue: 'Opties laden...' })}
          </Text>
        </HStack>
      )}

      {variantError && (
        <Text fontSize="xs" color="red.500" mb={2}>
          {t('product_configurator.variant_fetch_error', { defaultValue: 'Kon opties niet laden' })}
        </Text>
      )}

      {!loadingVariants && !variantError && hasVariantAxes && (
        <Box mb={2}>
          <VariantSelector
            variants={variants}
            onVariantSelect={handleVariantSelect}
            isDisabled={isDisabled}
            darkMode
            selectedVariantId={variantId}
          />
        </Box>
      )}

      {/* Dynamic fields from order_item_fields (name is auto-filled from person) */}
      {product.order_item_fields && product.order_item_fields.length > 0 &&
        product.order_item_fields
          .filter((field) => field.id !== 'name')
          .map((field) => {
          const error = fieldErrors[field.id];
          return (
            <FormControl key={field.id} mb={2} size="sm" isInvalid={!!error}>
              <FormLabel fontSize="xs">
                {field.label}
                {field.required && <Text as="span" color="red.500"> *</Text>}
              </FormLabel>
              {renderField(field, fields[field.id], (val) => handleFieldChange(field.id, val), isDisabled)}
              {error && <FormErrorMessage fontSize="xs">{error}</FormErrorMessage>}
            </FormControl>
          );
        })
      }
    </Box>
  );
};

export default ProductConfigurator;
