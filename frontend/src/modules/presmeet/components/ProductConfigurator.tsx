/**
 * ProductConfigurator — Dynamically renders form fields for a product.
 *
 * Based on the product's order_item_fields definition, renders the appropriate
 * input elements (text, select, number, date). Also handles variant selection
 * if the product has a variant_schema.
 *
 * Validates: Requirement 11.1 (product configurator per person)
 */

import React from 'react';
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
import { OrderItemField, Product } from '../types/presmeet.types';
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
  const handleFieldChange = (fieldId: string, value: any) => {
    onChange({ ...fields, [fieldId]: value }, variantId);
  };

  return (
    <Box pl={4} borderLeftWidth={2} borderLeftColor="blue.200" mt={2}>
      <Text fontSize="sm" fontWeight="medium" mb={2}>
        {product.name}
        <Text as="span" color="gray.500" ml={2}>
          {formatCurrency(product.price)}
        </Text>
      </Text>

      {/* Variant selector (if product has variants) */}
      {product.variant_schema && product.variant_schema.length > 0 && (
        <Box mb={3}>
          {product.variant_schema.map((axis) => (
            <FormControl key={axis.name} mb={2} size="sm">
              <FormLabel fontSize="xs">{axis.name}</FormLabel>
              <Select
                size="sm"
                value={fields[`_variant_${axis.name}`] || ''}
                onChange={(e) => handleFieldChange(`_variant_${axis.name}`, e.target.value)}
                isDisabled={isDisabled}
                placeholder={`Select ${axis.name}`}
              >
                {axis.values.map((v) => (
                  <option key={v} value={v}>{v}</option>
                ))}
              </Select>
            </FormControl>
          ))}
        </Box>
      )}

      {/* Dynamic fields from order_item_fields */}
      {product.order_item_fields.map((field) => {
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
      })}
    </Box>
  );
};

export default ProductConfigurator;
