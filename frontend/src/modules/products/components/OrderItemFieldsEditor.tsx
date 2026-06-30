import React, { useCallback } from 'react';
import {
  Box,
  Button,
  FormControl,
  FormLabel,
  FormErrorMessage,
  IconButton,
  Input,
  Select,
  Switch,
  VStack,
  HStack,
  Text,
  Heading,
  Tag,
  TagLabel,
  TagCloseButton,
  Wrap,
  WrapItem,
} from '@chakra-ui/react';
import { AddIcon, DeleteIcon } from '@chakra-ui/icons';
import type { TFunction } from 'i18next';
import {
  OrderItemField,
  OrderItemFieldType,
  OrderItemFieldValidation,
} from '../../webshop/types/unifiedProduct.types';
import { getValidationMessage } from '../../../utils/validationMessages';

// --- Constants ---

const MAX_FIELDS = 20;

const FIELD_TYPES: { value: OrderItemFieldType; label: string }[] = [
  { value: 'text', label: 'Tekst' },
  { value: 'select', label: 'Selectie' },
  { value: 'date', label: 'Datum' },
  { value: 'number', label: 'Getal' },
  { value: 'email', label: 'E-mail' },
];

// --- Props ---

export interface OrderItemFieldsEditorProps {
  /** Current field definitions */
  value: OrderItemField[];
  /** Called when fields change */
  onChange: (fields: OrderItemField[]) => void;
  /** Optional validation errors keyed by field index + property */
  errors?: Record<string, string>;
}

// --- Helpers ---

/** Convert label text to a kebab-case id */
function toSnakeCase(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s_]/g, '')
    .replace(/[\s-]+/g, '_')
    .replace(/_+/g, '_')
    .replace(/^_|_$/g, '')
    .slice(0, 50);
}

/** Create an empty field definition */
function createEmptyField(): OrderItemField {
  return {
    id: '',
    label: '',
    type: 'text',
    required: false,
  };
}

/** Validate all fields and return errors keyed by `${index}.${property}` */
export function validateOrderItemFields(
  fields: OrderItemField[],
  t?: TFunction
): Record<string, string> {
  const errors: Record<string, string> = {};
  const seenIds = new Set<string>();

  fields.forEach((field, index) => {
    // Label required
    if (!field.label.trim()) {
      errors[`${index}.label`] = t
        ? getValidationMessage(t, 'required', { field: 'Label' })
        : 'Label is verplicht';
    }

    // ID required
    if (!field.id.trim()) {
      errors[`${index}.id`] = t
        ? getValidationMessage(t, 'required', { field: 'ID' })
        : 'ID is verplicht';
    } else if (seenIds.has(field.id)) {
      errors[`${index}.id`] = t
        ? t('validation.unique', { field: 'ID', defaultValue: 'ID moet uniek zijn' })
        : 'ID moet uniek zijn';
    } else {
      seenIds.add(field.id);
    }

    // Select must have at least one option
    if (field.type === 'select') {
      if (!field.options || field.options.length === 0) {
        errors[`${index}.options`] = t
          ? t('validation.select_min_options', { count: 1, defaultValue: 'Selectie moet minimaal 1 optie hebben' })
          : 'Selectie moet minimaal 1 optie hebben';
      }
    }
  });

  return errors;
}

// --- Component ---

/**
 * Admin form builder for up to 20 order item field definitions.
 * Each field has: id, label, type, required toggle, type-specific validation constraints,
 * and an options editor for select-type fields.
 */
const OrderItemFieldsEditor: React.FC<OrderItemFieldsEditorProps> = ({
  value,
  onChange,
  errors = {},
}) => {
  const handleAddField = useCallback(() => {
    if (value.length >= MAX_FIELDS) return;
    onChange([...value, createEmptyField()]);
  }, [value, onChange]);

  const handleRemoveField = useCallback(
    (index: number) => {
      const updated = value.filter((_, i) => i !== index);
      onChange(updated);
    },
    [value, onChange]
  );

  const handleFieldChange = useCallback(
    (index: number, updates: Partial<OrderItemField>) => {
      const updated = value.map((field, i) =>
        i === index ? { ...field, ...updates } : field
      );
      onChange(updated);
    },
    [value, onChange]
  );

  const handleLabelChange = useCallback(
    (index: number, label: string) => {
      const field = value[index];
      const autoId = !field.id || field.id === toSnakeCase(field.label);
      const updates: Partial<OrderItemField> = { label };
      if (autoId) {
        updates.id = toSnakeCase(label);
      }
      handleFieldChange(index, updates);
    },
    [value, handleFieldChange]
  );

  const handleTypeChange = useCallback(
    (index: number, type: OrderItemFieldType) => {
      const updates: Partial<OrderItemField> = { type };
      // Reset type-specific props when switching types
      if (type !== 'select') {
        updates.options = undefined;
      }
      if (type === 'select' && !value[index].options) {
        updates.options = [];
      }
      // Reset validation constraints that don't apply to new type
      if (type === 'number') {
        updates.validation = {
          minimum: value[index].validation?.minimum,
          maximum: value[index].validation?.maximum,
        };
      } else if (type === 'text' || type === 'email') {
        updates.validation = {
          min_length: value[index].validation?.min_length,
          max_length: value[index].validation?.max_length,
          pattern: value[index].validation?.pattern,
        };
      } else {
        updates.validation = undefined;
      }
      handleFieldChange(index, updates);
    },
    [value, handleFieldChange]
  );

  return (
    <VStack spacing={4} align="stretch" width="100%">
      <HStack justify="space-between">
        <Heading as="h4" size="sm" color="gray.200">
          Velden ({value.length}/{MAX_FIELDS})
        </Heading>
        <Button
          size="sm"
          leftIcon={<AddIcon />}
          colorScheme="orange"
          variant="outline"
          onClick={handleAddField}
          isDisabled={value.length >= MAX_FIELDS}
        >
          Veld toevoegen
        </Button>
      </HStack>

      {value.length === 0 && (
        <Text color="gray.400" fontSize="sm" fontStyle="italic">
          Nog geen velden gedefinieerd. Klik op "Veld toevoegen" om te beginnen.
        </Text>
      )}

      {value.map((field, index) => (
        <FieldEditor
          key={index}
          field={field}
          index={index}
          errors={errors}
          onLabelChange={(label) => handleLabelChange(index, label)}
          onIdChange={(id) => handleFieldChange(index, { id })}
          onTypeChange={(type) => handleTypeChange(index, type)}
          onRequiredChange={(required) => handleFieldChange(index, { required })}
          onValidationChange={(validation) =>
            handleFieldChange(index, { validation })
          }
          onOptionsChange={(options) => handleFieldChange(index, { options })}
          onRemove={() => handleRemoveField(index)}
        />
      ))}

      {value.length >= MAX_FIELDS && (
        <Text color="orange.300" fontSize="sm">
          Maximum aantal velden ({MAX_FIELDS}) bereikt.
        </Text>
      )}
    </VStack>
  );
};

// --- Single Field Editor ---

interface FieldEditorProps {
  field: OrderItemField;
  index: number;
  errors: Record<string, string>;
  onLabelChange: (label: string) => void;
  onIdChange: (id: string) => void;
  onTypeChange: (type: OrderItemFieldType) => void;
  onRequiredChange: (required: boolean) => void;
  onValidationChange: (validation: OrderItemFieldValidation | undefined) => void;
  onOptionsChange: (options: string[] | undefined) => void;
  onRemove: () => void;
}

const FieldEditor: React.FC<FieldEditorProps> = ({
  field,
  index,
  errors,
  onLabelChange,
  onIdChange,
  onTypeChange,
  onRequiredChange,
  onValidationChange,
  onOptionsChange,
  onRemove,
}) => {
  return (
    <Box
      p={4}
      borderWidth={1}
      borderColor="gray.600"
      borderRadius="md"
      bg="gray.800"
    >
      <HStack justify="space-between" mb={3}>
        <Text fontWeight="bold" color="gray.200" fontSize="sm">
          Veld {index + 1}
        </Text>
        <IconButton
          aria-label="Veld verwijderen"
          icon={<DeleteIcon />}
          size="xs"
          colorScheme="red"
          variant="ghost"
          onClick={onRemove}
        />
      </HStack>

      <VStack spacing={3} align="stretch">
        {/* Label */}
        <FormControl isInvalid={!!errors[`${index}.label`]}>
          <FormLabel fontSize="xs" color="gray.400">
            Label
          </FormLabel>
          <Input
            size="sm"
            value={field.label}
            onChange={(e) => onLabelChange(e.target.value)}
            placeholder="Bijv. Naam deelnemer"
            maxLength={200}
            bg="gray.700"
            borderColor="gray.600"
          />
          {errors[`${index}.label`] && (
            <FormErrorMessage>{errors[`${index}.label`]}</FormErrorMessage>
          )}
        </FormControl>

        {/* ID */}
        <FormControl isInvalid={!!errors[`${index}.id`]}>
          <FormLabel fontSize="xs" color="gray.400">
            ID (automatisch of handmatig)
          </FormLabel>
          <Input
            size="sm"
            value={field.id}
            onChange={(e) => onIdChange(e.target.value)}
            placeholder="bijv. naam-deelnemer"
            maxLength={50}
            bg="gray.700"
            borderColor="gray.600"
            fontFamily="mono"
            fontSize="xs"
          />
          {errors[`${index}.id`] && (
            <FormErrorMessage>{errors[`${index}.id`]}</FormErrorMessage>
          )}
        </FormControl>

        {/* Type + Required row */}
        <HStack spacing={4} align="end">
          <FormControl flex={1}>
            <FormLabel fontSize="xs" color="gray.400">
              Type
            </FormLabel>
            <Select
              size="sm"
              value={field.type}
              onChange={(e) =>
                onTypeChange(e.target.value as OrderItemFieldType)
              }
              bg="gray.700"
              borderColor="gray.600"
              color="white"
            >
              {FIELD_TYPES.map((ft) => (
                <option key={ft.value} value={ft.value} style={{ backgroundColor: '#2D3748', color: 'white' }}>
                  {ft.label}
                </option>
              ))}
            </Select>
          </FormControl>

          <FormControl display="flex" alignItems="center" width="auto">
            <FormLabel fontSize="xs" color="gray.400" mb={0} mr={2}>
              Verplicht
            </FormLabel>
            <Switch
              size="sm"
              colorScheme="orange"
              isChecked={field.required}
              onChange={(e) => onRequiredChange(e.target.checked)}
            />
          </FormControl>
        </HStack>

        {/* Type-specific validation constraints */}
        {(field.type === 'text' || field.type === 'email') && (
          <TextValidationInputs
            validation={field.validation}
            onChange={onValidationChange}
          />
        )}
        {field.type === 'number' && (
          <NumberValidationInputs
            validation={field.validation}
            onChange={onValidationChange}
          />
        )}

        {/* Select options editor */}
        {field.type === 'select' && (
          <OptionsEditor
            options={field.options || []}
            onChange={onOptionsChange}
            error={errors[`${index}.options`]}
          />
        )}
      </VStack>
    </Box>
  );
};

// --- Validation Constraint Inputs ---

interface TextValidationProps {
  validation?: OrderItemFieldValidation;
  onChange: (validation: OrderItemFieldValidation | undefined) => void;
}

const TextValidationInputs: React.FC<TextValidationProps> = ({
  validation,
  onChange,
}) => {
  const handleChange = (key: keyof OrderItemFieldValidation, rawValue: string) => {
    const current = validation || {};
    let updated: OrderItemFieldValidation;

    if (key === 'pattern') {
      updated = { ...current, [key]: rawValue || undefined };
    } else {
      const numVal = rawValue ? parseInt(rawValue, 10) : undefined;
      updated = { ...current, [key]: isNaN(numVal as number) ? undefined : numVal };
    }

    // Clean up empty validation object
    const hasValues = Object.values(updated).some((v) => v !== undefined);
    onChange(hasValues ? updated : undefined);
  };

  return (
    <Box pl={2} borderLeft="2px" borderColor="gray.600">
      <Text fontSize="xs" color="gray.500" mb={2}>
        Validatie
      </Text>
      <HStack spacing={3}>
        <FormControl>
          <FormLabel fontSize="xs" color="gray.500">
            Min. lengte
          </FormLabel>
          <Input
            size="xs"
            type="number"
            min={1}
            max={1000}
            value={validation?.min_length ?? ''}
            onChange={(e) => handleChange('min_length', e.target.value)}
            bg="gray.700"
            borderColor="gray.600"
          />
        </FormControl>
        <FormControl>
          <FormLabel fontSize="xs" color="gray.500">
            Max. lengte
          </FormLabel>
          <Input
            size="xs"
            type="number"
            min={1}
            max={1000}
            value={validation?.max_length ?? ''}
            onChange={(e) => handleChange('max_length', e.target.value)}
            bg="gray.700"
            borderColor="gray.600"
          />
        </FormControl>
      </HStack>
      <FormControl mt={2}>
        <FormLabel fontSize="xs" color="gray.500">
          Patroon (regex)
        </FormLabel>
        <Input
          size="xs"
          value={validation?.pattern ?? ''}
          onChange={(e) => handleChange('pattern', e.target.value)}
          placeholder="bijv. ^[A-Z].*"
          bg="gray.700"
          borderColor="gray.600"
          fontFamily="mono"
        />
      </FormControl>
    </Box>
  );
};

interface NumberValidationProps {
  validation?: OrderItemFieldValidation;
  onChange: (validation: OrderItemFieldValidation | undefined) => void;
}

const NumberValidationInputs: React.FC<NumberValidationProps> = ({
  validation,
  onChange,
}) => {
  const handleChange = (key: 'minimum' | 'maximum', rawValue: string) => {
    const current = validation || {};
    const numVal = rawValue ? parseFloat(rawValue) : undefined;
    const updated = {
      ...current,
      [key]: isNaN(numVal as number) ? undefined : numVal,
    };

    const hasValues = Object.values(updated).some((v) => v !== undefined);
    onChange(hasValues ? updated : undefined);
  };

  return (
    <Box pl={2} borderLeft="2px" borderColor="gray.600">
      <Text fontSize="xs" color="gray.500" mb={2}>
        Validatie
      </Text>
      <HStack spacing={3}>
        <FormControl>
          <FormLabel fontSize="xs" color="gray.500">
            Minimum
          </FormLabel>
          <Input
            size="xs"
            type="number"
            value={validation?.minimum ?? ''}
            onChange={(e) => handleChange('minimum', e.target.value)}
            bg="gray.700"
            borderColor="gray.600"
          />
        </FormControl>
        <FormControl>
          <FormLabel fontSize="xs" color="gray.500">
            Maximum
          </FormLabel>
          <Input
            size="xs"
            type="number"
            value={validation?.maximum ?? ''}
            onChange={(e) => handleChange('maximum', e.target.value)}
            bg="gray.700"
            borderColor="gray.600"
          />
        </FormControl>
      </HStack>
    </Box>
  );
};

// --- Options Editor for Select Fields ---

interface OptionsEditorProps {
  options: string[];
  onChange: (options: string[] | undefined) => void;
  error?: string;
}

const OptionsEditor: React.FC<OptionsEditorProps> = ({
  options,
  onChange,
  error,
}) => {
  const [newOption, setNewOption] = React.useState('');

  const handleAddOption = () => {
    const trimmed = newOption.trim();
    if (!trimmed) return;
    if (options.includes(trimmed)) return;
    onChange([...options, trimmed]);
    setNewOption('');
  };

  const handleRemoveOption = (index: number) => {
    const updated = options.filter((_, i) => i !== index);
    onChange(updated.length > 0 ? updated : []);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAddOption();
    }
  };

  return (
    <FormControl isInvalid={!!error}>
      <Box pl={2} borderLeft="2px" borderColor="gray.600">
        <Text fontSize="xs" color="gray.500" mb={2}>
          Opties
        </Text>

        {options.length > 0 && (
          <Wrap spacing={1} mb={2}>
            {options.map((option, i) => (
              <WrapItem key={i}>
                <Tag size="sm" colorScheme="orange" variant="subtle">
                  <TagLabel>{option}</TagLabel>
                  <TagCloseButton onClick={() => handleRemoveOption(i)} />
                </Tag>
              </WrapItem>
            ))}
          </Wrap>
        )}

        <HStack>
          <Input
            size="xs"
            value={newOption}
            onChange={(e) => setNewOption(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Nieuwe optie..."
            bg="gray.700"
            borderColor="gray.600"
          />
          <IconButton
            aria-label="Optie toevoegen"
            icon={<AddIcon />}
            size="xs"
            colorScheme="orange"
            variant="outline"
            onClick={handleAddOption}
            isDisabled={!newOption.trim()}
          />
        </HStack>

        {error && <FormErrorMessage>{error}</FormErrorMessage>}
      </Box>
    </FormControl>
  );
};

export default OrderItemFieldsEditor;
