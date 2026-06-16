import React, { useCallback, useMemo, useState } from 'react';
import {
  Box,
  VStack,
  HStack,
  Input,
  Button,
  IconButton,
  Text,
  FormControl,
  FormErrorMessage,
  Tag,
  TagLabel,
  TagCloseButton,
  Badge,
  useToast,
} from '@chakra-ui/react';
import { AddIcon, DeleteIcon, ArrowUpIcon, ArrowDownIcon } from '@chakra-ui/icons';
import { VariantSchema } from '../../webshop/types/unifiedProduct.types';

const MAX_AXES = 5;
const MAX_VALUES_PER_AXIS = 20;
const MAX_COMBINATIONS = 100;

export interface VariantSchemaEditorProps {
  value: VariantSchema;
  onChange: (schema: VariantSchema) => void;
  errors?: Record<string, string>;
  /** Product ID - required for bidirectional sync API calls */
  productId?: string;
  /** Called when schema is saved (top-down sync). If provided, shows a "Sync varianten" button. */
  onSyncSchema?: (schema: VariantSchema) => Promise<void>;
  /** Called when a variant value tag is clicked — opens variant edit modal for that value */
  onVariantClick?: (axisName: string, value: string) => void;
}

/**
 * Visual editor for variant schema axes and values.
 * Allows admins to add up to 5 axes, each with up to 20 values.
 * Validates axis name uniqueness, value uniqueness per axis,
 * and displays an error when total combinations exceed 100.
 *
 * Supports bidirectional sync:
 * - Top-down: editing the schema and clicking "Sync varianten" regenerates variants via API
 * - Bottom-up: adding/removing individual variants updates the schema via API
 */
const VariantSchemaEditor: React.FC<VariantSchemaEditorProps> = ({
  value,
  onChange,
  errors,
  productId,
  onSyncSchema,
  onVariantClick,
}) => {
  const axes = useMemo(() => {
    return Object.entries(value).map(([name, vals]) => [
      name,
      Array.isArray(vals) ? vals : [String(vals)],
    ] as [string, string[]]);
  }, [value]);

  const totalCombinations = useMemo(() => {
    if (axes.length === 0) return 0;
    return axes.reduce((product, [, values]) => {
      return product * (values.length || 1);
    }, 1);
  }, [axes]);

  const combinationsExceeded = totalCombinations > MAX_COMBINATIONS;

  const getValidationErrors = useCallback((): Record<string, string> => {
    const localErrors: Record<string, string> = {};
    const axisNames = axes.map(([name]) => name.trim().toLowerCase());

    axes.forEach(([name, values], index) => {
      // Axis name validation
      if (!name.trim()) {
        localErrors[`axis_${index}_name`] = 'Asnaam mag niet leeg zijn';
      } else {
        const duplicateIndex = axisNames.indexOf(name.trim().toLowerCase());
        if (duplicateIndex !== -1 && duplicateIndex !== index) {
          localErrors[`axis_${index}_name`] = 'Asnaam moet uniek zijn';
        }
      }

      // Values validation
      const trimmedValues = values.map((v) => v.trim().toLowerCase());
      values.forEach((val, vIndex) => {
        if (!val.trim()) {
          localErrors[`axis_${index}_value_${vIndex}`] = 'Waarde mag niet leeg zijn';
        } else {
          const dupIdx = trimmedValues.indexOf(val.trim().toLowerCase());
          if (dupIdx !== -1 && dupIdx !== vIndex) {
            localErrors[`axis_${index}_value_${vIndex}`] = 'Waarde moet uniek zijn binnen de as';
          }
        }
      });
    });

    return localErrors;
  }, [axes]);

  const validationErrors = useMemo(() => getValidationErrors(), [getValidationErrors]);
  const allErrors = { ...validationErrors, ...errors };

  const updateSchema = useCallback(
    (newAxes: [string, string[]][]) => {
      const newSchema: VariantSchema = {};
      newAxes.forEach(([name, values]) => {
        newSchema[name] = values;
      });
      onChange(newSchema);
    },
    [onChange]
  );

  const addAxis = () => {
    if (axes.length >= MAX_AXES) return;
    const newAxes: [string, string[]][] = [...axes, ['', []]];
    updateSchema(newAxes);
  };

  const removeAxis = (index: number) => {
    const newAxes = axes.filter((_, i) => i !== index);
    updateSchema(newAxes);
  };

  const renameAxis = (index: number, newName: string) => {
    const newAxes: [string, string[]][] = axes.map(([name, values], i) =>
      i === index ? [newName, values] : [name, values]
    );
    updateSchema(newAxes);
  };

  const moveAxis = (index: number, direction: 'up' | 'down') => {
    const newAxes = [...axes];
    const targetIndex = direction === 'up' ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= newAxes.length) return;
    [newAxes[index], newAxes[targetIndex]] = [newAxes[targetIndex], newAxes[index]];
    updateSchema(newAxes);
  };

  const addValue = (axisIndex: number, newValue: string) => {
    if (!newValue.trim()) return;
    const [, values] = axes[axisIndex];
    if (values.length >= MAX_VALUES_PER_AXIS) return;
    const newAxes: [string, string[]][] = axes.map(([n, v], i) =>
      i === axisIndex ? [n, [...v, newValue.trim()]] : [n, v]
    );
    updateSchema(newAxes);
  };

  const removeValue = (axisIndex: number, valueIndex: number) => {
    const newAxes: [string, string[]][] = axes.map(([axisName, values], i) =>
      i === axisIndex ? [axisName, values.filter((_, vi) => vi !== valueIndex)] : [axisName, values]
    );
    updateSchema(newAxes);
  };

  return (
    <VStack align="stretch" spacing={4}>
      {combinationsExceeded && (
        <Badge colorScheme="red" p={2} borderRadius="md" fontSize="sm">
          Te veel combinaties: {totalCombinations} (maximaal {MAX_COMBINATIONS})
        </Badge>
      )}

      {axes.length > 0 && !combinationsExceeded && (
        <Text fontSize="sm" color="gray.400">
          Totaal combinaties: {totalCombinations}
        </Text>
      )}

      {axes.map(([name, values], axisIndex) => (
        <Box
          key={axisIndex}
          p={4}
          borderWidth="1px"
          borderRadius="md"
          borderColor="gray.600"
        >
          <HStack mb={3} spacing={2}>
            <FormControl isInvalid={!!allErrors[`axis_${axisIndex}_name`]} flex={1}>
              <Input
                placeholder="Asnaam (bijv. Maat, Kleur)"
                value={name}
                onChange={(e) => renameAxis(axisIndex, e.target.value)}
                size="sm"
                maxLength={50}
                bg="gray.700"
                color="white"
                borderColor="gray.500"
                _placeholder={{ color: 'gray.400' }}
              />
              <FormErrorMessage fontSize="xs">
                {allErrors[`axis_${axisIndex}_name`]}
              </FormErrorMessage>
            </FormControl>

            <IconButton
              aria-label="As omhoog"
              icon={<ArrowUpIcon />}
              size="sm"
              variant="ghost"
              isDisabled={axisIndex === 0}
              onClick={() => moveAxis(axisIndex, 'up')}
            />
            <IconButton
              aria-label="As omlaag"
              icon={<ArrowDownIcon />}
              size="sm"
              variant="ghost"
              isDisabled={axisIndex === axes.length - 1}
              onClick={() => moveAxis(axisIndex, 'down')}
            />
            <IconButton
              aria-label="As verwijderen"
              icon={<DeleteIcon />}
              size="sm"
              variant="ghost"
              colorScheme="red"
              onClick={() => removeAxis(axisIndex)}
            />
          </HStack>

          <Box mb={2}>
            <HStack flexWrap="wrap" spacing={2} mb={2}>
              {values.map((val, valIndex) => (
                <Tag
                  key={valIndex}
                  size="md"
                  variant="solid"
                  colorScheme="blue"
                  cursor={onVariantClick ? 'pointer' : 'default'}
                  _hover={onVariantClick ? { opacity: 0.8 } : undefined}
                  onClick={() => onVariantClick && onVariantClick(name, val)}
                >
                  <TagLabel>{val}</TagLabel>
                  <TagCloseButton onClick={(e) => { e.stopPropagation(); removeValue(axisIndex, valIndex); }} />
                </Tag>
              ))}
            </HStack>

            {values.length < MAX_VALUES_PER_AXIS && (
              <ValueInput
                axisIndex={axisIndex}
                onAdd={addValue}
                error={
                  Object.keys(allErrors).find((k) =>
                    k.startsWith(`axis_${axisIndex}_value_`)
                  )
                    ? 'Controleer waarden op duplicaten of lege velden'
                    : undefined
                }
              />
            )}
            {values.length >= MAX_VALUES_PER_AXIS && (
              <Text fontSize="xs" color="orange.700">
                Maximaal {MAX_VALUES_PER_AXIS} waarden per as
              </Text>
            )}
          </Box>
        </Box>
      ))}

      <Button
        leftIcon={<AddIcon />}
        onClick={addAxis}
        size="sm"
        variant="outline"
        isDisabled={axes.length >= MAX_AXES}
      >
        As toevoegen
      </Button>

      {axes.length >= MAX_AXES && (
        <Text fontSize="xs" color="orange.700">
          Maximaal {MAX_AXES} assen
        </Text>
      )}

      {/* Top-down sync button: save schema and regenerate variants */}
      {onSyncSchema && axes.length > 0 && !combinationsExceeded && (
        <SyncSchemaButton
          schema={value}
          onSyncSchema={onSyncSchema}
          hasErrors={Object.keys(validationErrors).length > 0}
        />
      )}
    </VStack>
  );
};

interface ValueInputProps {
  axisIndex: number;
  onAdd: (axisIndex: number, value: string) => void;
  error?: string;
}

/**
 * Input field with "add" button for adding values to an axis.
 * Clears the input on successful add.
 */
const ValueInput: React.FC<ValueInputProps> = ({ axisIndex, onAdd, error }) => {
  const [inputValue, setInputValue] = React.useState('');

  const handleAdd = () => {
    if (inputValue.trim()) {
      onAdd(axisIndex, inputValue);
      setInputValue('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAdd();
    }
  };

  return (
    <FormControl isInvalid={!!error}>
      <HStack>
        <Input
          placeholder="Waarde toevoegen"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          size="sm"
          maxLength={100}
          bg="gray.700"
          color="white"
          borderColor="gray.500"
          _placeholder={{ color: 'gray.400' }}
        />
        <Button size="sm" onClick={handleAdd} colorScheme="orange" variant="ghost">
          Toevoegen
        </Button>
      </HStack>
      {error && <FormErrorMessage fontSize="xs">{error}</FormErrorMessage>}
    </FormControl>
  );
};

/**
 * Button that triggers top-down schema sync (regenerates variants from schema).
 */
interface SyncSchemaButtonProps {
  schema: VariantSchema;
  onSyncSchema: (schema: VariantSchema) => Promise<void>;
  hasErrors: boolean;
}

const SyncSchemaButton: React.FC<SyncSchemaButtonProps> = ({ schema, onSyncSchema, hasErrors }) => {
  const [isSyncing, setIsSyncing] = useState(false);
  const toast = useToast();

  const handleSync = async () => {
    if (hasErrors) return;
    setIsSyncing(true);
    try {
      await onSyncSchema(schema);
      toast({
        title: 'Varianten gesynchroniseerd',
        description: 'Het variant schema is opgeslagen en de varianten zijn bijgewerkt.',
        status: 'success',
        duration: 3000,
      });
    } catch (err: any) {
      toast({
        title: 'Sync mislukt',
        description: err?.response?.data?.error || err?.message || 'Onbekende fout',
        status: 'error',
        duration: 5000,
      });
    } finally {
      setIsSyncing(false);
    }
  };

  return (
    <Button
      size="sm"
      colorScheme="teal"
      onClick={handleSync}
      isLoading={isSyncing}
      loadingText="Synchroniseren..."
      isDisabled={hasErrors}
    >
      Sync varianten
    </Button>
  );
};

export default VariantSchemaEditor;
