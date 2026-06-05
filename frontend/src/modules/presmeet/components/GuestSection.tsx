/**
 * GuestSection — Form section for managing party guests.
 *
 * Each guest has: name and optional t-shirt (gender + size).
 * Combined party attendance (delegates attending party + guests) max 13 (Requirement 2.4).
 * Validates: Requirements 4.2, 4.3
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
import { useTranslation } from 'react-i18next';
import {
  GuestFormData,
  Gender,
  TshirtSize,
  ValidationError,
} from '../types/presmeet';
import { getFieldError } from '../utils/validation';

const TSHIRT_SIZES: TshirtSize[] = ['S', 'M', 'L', 'XL', 'XXL', '3XL', '4XL'];

interface GuestSectionProps {
  guests: GuestFormData[];
  onChange: (guests: GuestFormData[]) => void;
  maxGuests: number;
  currentPartyCount: number;
  maxPartyTotal: number;
  errors: ValidationError[];
  isDisabled?: boolean;
}

const GuestSection: React.FC<GuestSectionProps> = ({
  guests,
  onChange,
  maxGuests,
  currentPartyCount,
  maxPartyTotal,
  errors,
  isDisabled = false,
}) => {
  const { t } = useTranslation('presmeet');

  // Guests always get a party ticket, so party limit applies
  const remainingPartySlots = maxPartyTotal - currentPartyCount;
  const canAdd = guests.length < maxGuests && remainingPartySlots > 0;

  const handleAdd = () => {
    if (!canAdd) return;
    onChange([...guests, { name: '' }]);
  };

  const handleRemove = (index: number) => {
    const updated = guests.filter((_, i) => i !== index);
    onChange(updated);
  };

  const handleNameChange = (index: number, value: string) => {
    const updated = [...guests];
    updated[index] = { ...updated[index], name: value };
    onChange(updated);
  };

  const handleTshirtToggle = (index: number, enabled: boolean) => {
    const updated = [...guests];
    if (enabled) {
      updated[index] = {
        ...updated[index],
        tshirt: { gender: 'male' as Gender, size: 'L' as TshirtSize },
      };
    } else {
      const { tshirt, ...rest } = updated[index];
      updated[index] = rest as GuestFormData;
    }
    onChange(updated);
  };

  const handleTshirtChange = (
    index: number,
    field: 'gender' | 'size',
    value: string
  ) => {
    const updated = [...guests];
    if (updated[index].tshirt) {
      updated[index] = {
        ...updated[index],
        tshirt: { ...updated[index].tshirt!, [field]: value },
      };
    }
    onChange(updated);
  };

  const getDisabledReason = (): string | null => {
    if (guests.length >= maxGuests) return t('guests.max_guests_reached', { count: maxGuests });
    if (remainingPartySlots <= 0) return t('guests.max_party_reached', { count: maxPartyTotal });
    return null;
  };

  return (
    <Box>
      <HStack justify="space-between" mb={4}>
        <Heading size="md">{t('guests.title')}</Heading>
        <Text fontSize="sm" color="gray.400">
          {t('guests.count', { count: guests.length })} | {t('guests.party_tickets', { current: currentPartyCount, max: maxPartyTotal })}
        </Text>
      </HStack>

      <VStack spacing={4} align="stretch">
        {guests.map((guest, index) => {
          const prefix = `guests[${index}]`;
          return (
            <Box
              key={index}
              p={4}
              borderWidth={1}
              borderColor="gray.600"
              borderRadius="md"
            >
              <HStack justify="space-between" mb={3}>
                <Text fontWeight="bold">{t('guests.guest_n', { n: index + 1 })}</Text>
                <IconButton
                  icon={<DeleteIcon />}
                  size="sm"
                  colorScheme="red"
                  variant="ghost"
                  onClick={() => handleRemove(index)}
                  aria-label={t('guests.remove_guest', { n: index + 1 })}
                  isDisabled={isDisabled}
                />
              </HStack>

              <VStack spacing={3} align="stretch">
                <FormControl isInvalid={!!getFieldError(errors, `${prefix}.name`)}>
                  <FormLabel>{t('guests.name')}</FormLabel>
                  <Input
                    value={guest.name}
                    onChange={(e) => handleNameChange(index, e.target.value)}
                    placeholder={t('guests.placeholder_name')}
                    isDisabled={isDisabled}
                  />
                  {getFieldError(errors, `${prefix}.name`) && (
                    <Text color="red.300" fontSize="sm" mt={1}>
                      {getFieldError(errors, `${prefix}.name`)}
                    </Text>
                  )}
                </FormControl>

                <Divider />

                <FormControl>
                  <HStack justify="space-between">
                    <FormLabel mb={0}>{t('guests.order_tshirt')}</FormLabel>
                    <Switch
                      isChecked={!!guest.tshirt}
                      onChange={(e) => handleTshirtToggle(index, e.target.checked)}
                      colorScheme="orange"
                      isDisabled={isDisabled}
                    />
                  </HStack>
                </FormControl>

                {guest.tshirt && (
                  <HStack spacing={3}>
                    <FormControl
                      isInvalid={!!getFieldError(errors, `${prefix}.tshirt.gender`)}
                    >
                      <FormLabel>{t('guests.gender')}</FormLabel>
                      <Select
                        value={guest.tshirt.gender}
                        onChange={(e) =>
                          handleTshirtChange(index, 'gender', e.target.value)
                        }
                        isDisabled={isDisabled}
                        bg="gray.700"
                        color="white"
                        sx={{ option: { bg: '#2D3748', color: 'white' } }}
                      >
                        <option value="male">{t('guests.male')}</option>
                        <option value="female">{t('guests.female')}</option>
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
                      <FormLabel>{t('guests.size')}</FormLabel>
                      <Select
                        value={guest.tshirt.size}
                        onChange={(e) =>
                          handleTshirtChange(index, 'size', e.target.value)
                        }
                        isDisabled={isDisabled}
                        bg="gray.700"
                        color="white"
                        sx={{ option: { bg: '#2D3748', color: 'white' } }}
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
          {t('guests.add_guest')}{getDisabledReason() ? ` (${getDisabledReason()})` : ''}
        </Button>
      </VStack>
    </Box>
  );
};

export default GuestSection;
