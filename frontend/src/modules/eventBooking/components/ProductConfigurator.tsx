/**
 * ProductConfigurator — Dynamically renders form fields for a product.
 *
 * Based on the product's order_item_fields definition, renders the appropriate
 * input elements (text, select, number, date). Also handles variant selection
 * if the product has a variant_schema — resolving axis selections to a valid
 * variant_id before the line can be committed.
 *
 * Validates: Requirements 7.6, 7.7
 */

import React, { useMemo } from 'react';
import {
  Box,
  FormControl,
  FormErrorMessage,
  FormLabel,
  Input,
  NumberDecrementStepper,
  NumberIncrementStepper,
  NumberInput,
  NumberInputField,
  NumberInputStepper,
  Select,
  Text,
} from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import { OrderItemField, Product, ProductVariant } from '../types/eventBooking.types';
import { formatCurrency } from '../utils/priceCalculator';

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
 * Resolve variant axis selections to a valid variant_id.
 *
 * Given the user's axis selections (stored as _variant_<axisName> in fields),
 * find the matching variant from the product's variants list.
 *
 * @returns The matching variant_id, or null if not all axes are selected or no match found.
 */
export function resolveVariantId(
  fields: Record<string, any>,
  variantSchema: { name: string; values: string[] }[],
  variants: ProductVariant[]
): string | null {
  if (!variantSchema || variantSchema.length === 0 || !variants || variants.length === 0) {
    return null;
  }

  // Collect the current selection for each axis
  const selections: Record<string, string> = {};
  for (const axis of variantSchema) {
    const value = fields[`_variant_${axis.name}`];
    if (!value || value === '') {
      return null; // Not all axes selected yet
    }
    selections[axis.name] = value;
  }

  // Find the variant whose variant_attributes match all selections
  const match = variants.find((variant) =>
    variantSchema.every(
      (axis) => variant.variant_attributes[axis.name] === selections[axis.name]
    )
  );

  return match?.variant_id ?? null;
}

/**
 * Check whether a product requires variant selection but doesn't yet have one resolved.
 */
export function isVariantSelectionIncomplete(
  product: Product,
  fields: Record<string, any>,
  variantId: string | null
): boolean {
  if (!product.variant_schema || product.variant_schema.length === 0) {
    return false;
  }
  if (!product.variants || product.variants.length === 0) {
    // No variants available — cannot resolve, treat as incomplete
    return true;
  }
  return variantId === null;
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
        >
          {(field.options || []).map((opt) => (
            <option key={opt} value={opt}>{opt}</option>
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

  const hasVariantSchema = product.variant_schema && product.variant_schema.length > 0;
  const hasVariants = product.variants && product.variants.length > 0;

  // Resolve variant_id from current axis selections
  const resolvedVariantId = useMemo(() => {
    if (!hasVariantSchema || !hasVariants) return null;
    return resolveVariantId(
      fields,
      product.variant_schema!,
      product.variants!
    );
  }, [fields, hasVariantSchema, hasVariants, product.variant_schema, product.variants]);

  // Determine if variant selection is incomplete (all axes must be selected)
  const variantIncomplete = useMemo(() => {
    if (!hasVariantSchema) return false;
    return resolvedVariantId === null;
  }, [hasVariantSchema, resolvedVariantId]);

  // Check if all axes are selected but no matching variant exists
  const allAxesSelected = useMemo(() => {
    if (!hasVariantSchema || !product.variant_schema) return false;
    return product.variant_schema.every(
      (axis) => fields[`_variant_${axis.name}`] && fields[`_variant_${axis.name}`] !== ''
    );
  }, [hasVariantSchema, product.variant_schema, fields]);

  const combinationInvalid = allAxesSelected && resolvedVariantId === null && hasVariants;

  const handleFieldChange = (fieldId: string, value: any) => {
    const updatedFields = { ...fields, [fieldId]: value };

    // If this is a variant axis change, re-resolve the variant_id
    if (fieldId.startsWith('_variant_') && hasVariantSchema && hasVariants) {
      const newVariantId = resolveVariantId(
        updatedFields,
        product.variant_schema!,
        product.variants!
      );
      onChange(updatedFields, newVariantId);
    } else {
      onChange(updatedFields, variantId);
    }
  };

  return (
    <Box pl={4} borderLeftWidth={2} borderLeftColor="blue.200" mt={2}>
      <Text fontSize="sm" fontWeight="medium" mb={2}>
        {product.naam}
        <Text as="span" color="gray.500" ml={2}>
          {formatCurrency(product.prijs)}
        </Text>
      </Text>

      {/* Variant selector (if product has variant_schema) */}
      {hasVariantSchema && product.variant_schema!.map((axis) => (
        <FormControl key={axis.name} mb={2} size="sm">
          <FormLabel fontSize="xs">{axis.name}</FormLabel>
          <Select
            size="sm"
            value={fields[`_variant_${axis.name}`] || ''}
            onChange={(e) => handleFieldChange(`_variant_${axis.name}`, e.target.value)}
            isDisabled={isDisabled}
            placeholder={t('product_configurator.select_variant', { axis: axis.name })}
          >
            {axis.values.map((v) => (
              <option key={v} value={v}>{v}</option>
            ))}
          </Select>
        </FormControl>
      ))}

      {/* Variant resolution feedback */}
      {hasVariantSchema && variantIncomplete && !combinationInvalid && (
        <Text fontSize="xs" color="orange.500" mb={2}>
          {t('product_configurator.select_all_variants')}
        </Text>
      )}
      {combinationInvalid && (
        <Text fontSize="xs" color="red.500" mb={2}>
          {t('product_configurator.variant_unavailable')}
        </Text>
      )}

      {/* Dynamic fields from order_item_fields */}
      {product.order_item_fields && product.order_item_fields.length > 0 &&
        product.order_item_fields.map((field) => {
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
