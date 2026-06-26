import React, { useCallback } from 'react';
import {
  Box,
  FormControl,
  FormLabel,
  FormErrorMessage,
  Input,
  Select,
  NumberInput,
  NumberInputField,
  NumberInputStepper,
  NumberIncrementStepper,
  NumberDecrementStepper,
  Heading,
  VStack,
  Divider,
} from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import type { TFunction } from 'i18next';
import { getValidationMessage } from '../../../utils/validationMessages';
import { OrderItemField, ItemFieldsEntry } from '../types/unifiedProduct.types';

/** Error for a specific field on a specific item */
export interface ItemFieldError {
  /** 0-based item index */
  itemIndex: number;
  /** Field id that failed validation */
  fieldId: string;
  /** Human-readable error message (Dutch) */
  message: string;
}

export interface ItemFieldsFormProps {
  /** Field definitions from the product's order_item_fields */
  fields: OrderItemField[];
  /** Number of items (renders this many sets of fields) */
  quantity: number;
  /** Current field values, one entry per item */
  values: ItemFieldsEntry[];
  /** Called when any field value changes */
  onChange: (values: ItemFieldsEntry[]) => void;
  /** Optional pre-computed errors to display */
  errors?: ItemFieldError[];
  /** Whether to validate on submit (shows errors only when true) */
  validateOnSubmit?: boolean;
}

/**
 * Validates all fields for all items and returns any errors found.
 * Exported for use by parent components (e.g., CheckoutModal).
 * When a `t` function is provided, validation messages are translated via the Validation_Helper.
 */
export function validateItemFields(
  fields: OrderItemField[],
  values: ItemFieldsEntry[],
  quantity: number,
  t?: TFunction
): ItemFieldError[] {
  const errors: ItemFieldError[] = [];

  for (let itemIdx = 0; itemIdx < quantity; itemIdx++) {
    const entry = values[itemIdx];
    const fieldValues = entry?.field_values || {};

    for (const field of fields) {
      const value = fieldValues[field.id] ?? '';
      const fieldErrors = validateSingleField(field, value, itemIdx, t);
      errors.push(...fieldErrors);
    }
  }

  return errors;
}

function validateSingleField(
  field: OrderItemField,
  value: string,
  itemIndex: number,
  t?: TFunction
): ItemFieldError[] {
  const errors: ItemFieldError[] = [];
  const trimmed = typeof value === 'string' ? value.trim() : '';
  const isEmpty = trimmed === '';

  // Required check
  if (field.required && isEmpty) {
    errors.push({
      itemIndex,
      fieldId: field.id,
      message: t
        ? getValidationMessage(t, 'required', { field: field.label })
        : 'Dit veld is verplicht',
    });
    // Don't validate constraints on empty required fields
    return errors;
  }

  // Skip constraint validation for empty non-required fields
  if (isEmpty) {
    return errors;
  }

  const validation = field.validation;

  // Text / email constraints
  if (field.type === 'text' || field.type === 'email') {
    if (validation?.min_length && trimmed.length < validation.min_length) {
      errors.push({
        itemIndex,
        fieldId: field.id,
        message: t
          ? getValidationMessage(t, 'min_length', { count: validation.min_length })
          : `Minimaal ${validation.min_length} tekens`,
      });
    }
    if (validation?.max_length && trimmed.length > validation.max_length) {
      errors.push({
        itemIndex,
        fieldId: field.id,
        message: t
          ? getValidationMessage(t, 'max_length', { count: validation.max_length })
          : `Maximaal ${validation.max_length} tekens`,
      });
    }
    if (validation?.pattern) {
      try {
        const regex = new RegExp(validation.pattern);
        if (!regex.test(trimmed)) {
          errors.push({
            itemIndex,
            fieldId: field.id,
            message: t
              ? getValidationMessage(t, 'pattern')
              : 'Waarde voldoet niet aan het vereiste formaat',
          });
        }
      } catch {
        // Invalid regex pattern in config — skip pattern validation
      }
    }
  }

  // Email format check
  if (field.type === 'email' && trimmed) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(trimmed)) {
      errors.push({
        itemIndex,
        fieldId: field.id,
        message: t
          ? getValidationMessage(t, 'email')
          : 'Ongeldig e-mailadres',
      });
    }
  }

  // Number constraints
  if (field.type === 'number' && trimmed) {
    const numValue = parseFloat(trimmed);
    if (isNaN(numValue)) {
      errors.push({
        itemIndex,
        fieldId: field.id,
        message: t
          ? getValidationMessage(t, 'invalid_number')
          : 'Voer een geldig getal in',
      });
    } else {
      if (validation?.minimum !== undefined && numValue < validation.minimum) {
        errors.push({
          itemIndex,
          fieldId: field.id,
          message: t
            ? getValidationMessage(t, 'min', { value: validation.minimum })
            : `Minimale waarde is ${validation.minimum}`,
        });
      }
      if (validation?.maximum !== undefined && numValue > validation.maximum) {
        errors.push({
          itemIndex,
          fieldId: field.id,
          message: t
            ? getValidationMessage(t, 'max', { value: validation.maximum })
            : `Maximale waarde is ${validation.maximum}`,
        });
      }
    }
  }

  // Select must match one of the options
  if (field.type === 'select' && field.options && trimmed) {
    if (!field.options.includes(trimmed)) {
      errors.push({
        itemIndex,
        fieldId: field.id,
        message: t
          ? getValidationMessage(t, 'invalid_option')
          : 'Selecteer een geldige optie',
      });
    }
  }

  return errors;
}

/**
 * Renders configured fields for each item in the order quantity.
 * Supports text, select, date, number, and email field types.
 * Displays sequential item labels ("Item 1 van 3", "Item 2 van 3").
 * Allows saving with incomplete data — validation only at order submission.
 */
const ItemFieldsForm: React.FC<ItemFieldsFormProps> = ({
  fields,
  quantity,
  values,
  onChange,
  errors = [],
  validateOnSubmit = false,
}) => {
  const { t } = useTranslation('webshop');

  const handleFieldChange = useCallback(
    (itemIndex: number, fieldId: string, newValue: string) => {
      const updatedValues = [...values];

      // Ensure entry exists for this item index
      while (updatedValues.length <= itemIndex) {
        updatedValues.push({ field_values: {} });
      }

      updatedValues[itemIndex] = {
        ...updatedValues[itemIndex],
        field_values: {
          ...updatedValues[itemIndex].field_values,
          [fieldId]: newValue,
        },
      };

      onChange(updatedValues);
    },
    [values, onChange]
  );

  const getFieldError = (itemIndex: number, fieldId: string): string | undefined => {
    if (!validateOnSubmit) return undefined;
    const error = errors.find(
      (e) => e.itemIndex === itemIndex && e.fieldId === fieldId
    );
    return error?.message;
  };

  if (!fields || fields.length === 0 || quantity <= 0) {
    return null;
  }

  return (
    <VStack spacing={4} align="stretch" width="100%">
      {Array.from({ length: quantity }, (_, itemIndex) => (
        <Box
          key={itemIndex}
          p={4}
          borderWidth={1}
          borderColor="gray.600"
          borderRadius="md"
        >
          <Heading as="h4" size="sm" mb={3} color="white">
            {t('item_fields.item_label', { current: itemIndex + 1, total: quantity })}
          </Heading>

          <VStack spacing={3} align="stretch">
            {fields.map((field) => {
              const fieldValue =
                values[itemIndex]?.field_values?.[field.id] ?? '';
              const errorMsg = getFieldError(itemIndex, field.id);

              return (
                <FormControl
                  key={`${itemIndex}-${field.id}`}
                  isInvalid={!!errorMsg}
                  isRequired={field.required}
                >
                  <FormLabel fontSize="sm" color="gray.300">{field.label}</FormLabel>
                  {renderFieldInput(field, fieldValue, itemIndex, handleFieldChange, t)}
                  {errorMsg && (
                    <FormErrorMessage>{errorMsg}</FormErrorMessage>
                  )}
                </FormControl>
              );
            })}
          </VStack>

          {itemIndex < quantity - 1 && <Divider mt={4} />}
        </Box>
      ))}
    </VStack>
  );
};

function renderFieldInput(
  field: OrderItemField,
  value: string,
  itemIndex: number,
  onFieldChange: (itemIndex: number, fieldId: string, value: string) => void,
  t: (key: string) => string
): React.ReactElement {
  const handleChange = (newValue: string) => {
    onFieldChange(itemIndex, field.id, newValue);
  };

  switch (field.type) {
    case 'select':
      return (
        <Select
          placeholder={t('item_fields.select_placeholder')}
          value={value}
          onChange={(e) => handleChange(e.target.value)}
          size="sm"
          bg="gray.700"
          borderColor="gray.600"
          color="white"
        >
          {(field.options || []).map((option) => (
            <option key={option} value={option} style={{ background: '#2D3748', color: 'white' }}>
              {option}
            </option>
          ))}
        </Select>
      );

    case 'number':
      return (
        <NumberInput
          value={value}
          onChange={(valueStr) => handleChange(valueStr)}
          min={field.validation?.minimum}
          max={field.validation?.maximum}
          size="sm"
        >
          <NumberInputField bg="gray.700" borderColor="gray.600" color="white" />
          <NumberInputStepper>
            <NumberIncrementStepper />
            <NumberDecrementStepper />
          </NumberInputStepper>
        </NumberInput>
      );

    case 'date':
      return (
        <Input
          type="date"
          value={value}
          onChange={(e) => handleChange(e.target.value)}
          size="sm"
          bg="gray.700"
          borderColor="gray.600"
          color="white"
        />
      );

    case 'email':
      return (
        <Input
          type="email"
          value={value}
          onChange={(e) => handleChange(e.target.value)}
          placeholder={t('item_fields.email_placeholder')}
          size="sm"
          maxLength={field.validation?.max_length}
          bg="gray.700"
          borderColor="gray.600"
          color="white"
        />
      );

    case 'text':
    default:
      return (
        <Input
          type="text"
          value={value}
          onChange={(e) => handleChange(e.target.value)}
          size="sm"
          maxLength={field.validation?.max_length}
          bg="gray.700"
          borderColor="gray.600"
          color="white"
        />
      );
  }
}

export default ItemFieldsForm;
