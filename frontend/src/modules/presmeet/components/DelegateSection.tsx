/**
 * DelegateSection — Form section for managing delegates (meeting ticket holders).
 *
 * Each delegate has: name, role, party attendance toggle, and optional t-shirt.
 * Max 3 delegates per club (Requirement 2.4).
 * Validates: Requirements 4.1, 4.3, 4.8, 4.9
 */

import React from 'react';
import {
  Box,
  Button,
  FormControl,
  FormLabel,
  Input,
  Select,
  Switch,
  VStack,
  HStack,
  IconButton,
  Heading,
  Text,
  Divider,
} from '@chakra-ui/react';
import { AddIcon, DeleteIcon } from '@chakra-ui/icons';
import {
  DelegateFormData,
  Gender,
  TshirtSize,
  ValidationError,
} from '../types/presmeet';
import { getFieldError } from '../utils/validation';

const TSHIRT_SIZES: TshirtSize[] = ['S', 'M', 'L', 'XL', 'XXL', '3XL', '4XL'];

interface DelegateSectionProps {
  delegates: DelegateFormData[];
  onChange: (delegates: DelegateFormData[]) => void;
  maxDelegates: number;
  errors: ValidationError[];
  isDisabled?: boolean;
}

const DelegateSection: React.FC<DelegateSectionProps> = ({
  delegates,
  onChange,
  maxDelegates,
  errors,
  isDisabled = false,
}) => {
  const canAdd = delegates.length < maxDelegates;

  const handleAdd = () => {
    if (!canAdd) return;
    onChange([
      ...delegates,
      { name: '', role: '', attend_party: false },
    ]);
  };

  const handleRemove = (index: number) => {
    const updated = delegates.filter((_, i) => i !== index);
    onChange(updated);
  };

  const handleChange = (index: number, field: keyof DelegateFormData, value: any) => {
    const updated = [...delegates];
    updated[index] = { ...updated[index], [field]: value };
    onChange(updated);
  };

  const handleTshirtToggle = (index: number, enabled: boolean) => {
    const updated = [...delegates];
    if (enabled) {
      updated[index] = {
        ...updated[index],
        tshirt: { gender: 'male' as Gender, size: 'L' as TshirtSize },
      };
    } else {
      const { tshirt, ...rest } = updated[index];
      updated[index] = rest as DelegateFormData;
    }
    onChange(updated);
  };

  const handleTshirtChange = (
    index: number,
    field: 'gender' | 'size',
    value: string
  ) => {
    const updated = [...delegates];
    if (updated[index].tshirt) {
      updated[index] = {
        ...updated[index],
        tshirt: { ...updated[index].tshirt!, [field]: value },
      };
    }
    onChange(updated);
  };

  return (
    <Box>
      <HStack justify="space-between" mb={4}>
        <Heading size="md">Delegates</Heading>
        <Text fontSize="sm" color="gray.400">
          {delegates.length} / {maxDelegates}
        </Text>
      </HStack>

      <VStack spacing={4} align="stretch">
        {delegates.map((delegate, index) => {
          const prefix = `delegates[${index}]`;
          return (
            <Box
              key={index}
              p={4}
              borderWidth={1}
              borderColor="gray.600"
              borderRadius="md"
            >
              <HStack justify="space-between" mb={3}>
                <Text fontWeight="bold">Delegate {index + 1}</Text>
                <IconButton
                  icon={<DeleteIcon />}
                  size="sm"
                  colorScheme="red"
                  variant="ghost"
                  onClick={() => handleRemove(index)}
                  aria-label={`Remove delegate ${index + 1}`}
                  isDisabled={isDisabled}
                />
              </HStack>

              <VStack spacing={3} align="stretch">
                <FormControl isInvalid={!!getFieldError(errors, `${prefix}.name`)}>
                  <FormLabel>Name</FormLabel>
                  <Input
                    value={delegate.name}
                    onChange={(e) => handleChange(index, 'name', e.target.value)}
                    placeholder="Full name"
                    isDisabled={isDisabled}
                  />
                  {getFieldError(errors, `${prefix}.name`) && (
                    <Text color="red.300" fontSize="sm" mt={1}>
                      {getFieldError(errors, `${prefix}.name`)}
                    </Text>
                  )}
                </FormControl>

                <FormControl isInvalid={!!getFieldError(errors, `${prefix}.role`)}>
                  <FormLabel>Role</FormLabel>
                  <Input
                    value={delegate.role}
                    onChange={(e) => handleChange(index, 'role', e.target.value)}
                    placeholder="e.g. President, Secretary"
                    isDisabled={isDisabled}
                  />
                  {getFieldError(errors, `${prefix}.role`) && (
                    <Text color="red.300" fontSize="sm" mt={1}>
                      {getFieldError(errors, `${prefix}.role`)}
                    </Text>
                  )}
                </FormControl>

                <FormControl>
                  <HStack justify="space-between">
                    <FormLabel mb={0}>Attend party</FormLabel>
                    <Switch
                      isChecked={delegate.attend_party}
                      onChange={(e) =>
                        handleChange(index, 'attend_party', e.target.checked)
                      }
                      colorScheme="orange"
                      isDisabled={isDisabled}
                    />
                  </HStack>
                </FormControl>

                <Divider />

                <FormControl>
                  <HStack justify="space-between">
                    <FormLabel mb={0}>Order t-shirt</FormLabel>
                    <Switch
                      isChecked={!!delegate.tshirt}
                      onChange={(e) => handleTshirtToggle(index, e.target.checked)}
                      colorScheme="orange"
                      isDisabled={isDisabled}
                    />
                  </HStack>
                </FormControl>

                {delegate.tshirt && (
                  <HStack spacing={3}>
                    <FormControl
                      isInvalid={!!getFieldError(errors, `${prefix}.tshirt.gender`)}
                    >
                      <FormLabel>Gender</FormLabel>
                      <Select
                        value={delegate.tshirt.gender}
                        onChange={(e) =>
                          handleTshirtChange(index, 'gender', e.target.value)
                        }
                        isDisabled={isDisabled}
                      >
                        <option value="male">Male</option>
                        <option value="female">Female</option>
                      </Select>
                      {getFieldError(errors, `${prefix}.tshirt.gender`) && (
                        <Text color="red.300" fontSize="sm" mt={1}>
                          {getFieldError(errors, `${prefix}.tshirt.gender`)}
                        </Text>
                      )}
                    </FormControl>

                    <FormControl
                      isInvalid={!!getFieldError(errors, `${prefix}.tshirt.size`)}
                    >
                      <FormLabel>Size</FormLabel>
                      <Select
                        value={delegate.tshirt.size}
                        onChange={(e) =>
                          handleTshirtChange(index, 'size', e.target.value)
                        }
                        isDisabled={isDisabled}
                      >
                        {TSHIRT_SIZES.map((size) => (
                          <option key={size} value={size}>
                            {size}
                          </option>
                        ))}
                      </Select>
                      {getFieldError(errors, `${prefix}.tshirt.size`) && (
                        <Text color="red.300" fontSize="sm" mt={1}>
                          {getFieldError(errors, `${prefix}.tshirt.size`)}
                        </Text>
                      )}
                    </FormControl>
                  </HStack>
                )}
              </VStack>
            </Box>
          );
        })}

        <Button
          leftIcon={<AddIcon />}
          onClick={handleAdd}
          isDisabled={!canAdd || isDisabled}
          variant="outline"
          colorScheme="orange"
          size="sm"
        >
          Add Delegate{!canAdd && ` (max ${maxDelegates} reached)`}
        </Button>
      </VStack>
    </Box>
  );
};

export default DelegateSection;
