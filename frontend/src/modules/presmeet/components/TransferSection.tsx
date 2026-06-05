/**
 * TransferSection — Form section for managing airport transfers.
 *
 * Each transfer has: direction, airport, flight number, date, time, persons.
 * Max 20 transfers per club (Requirement 2.4).
 * Validates: Requirements 4.4, 8.4, 8.5
 */

import React from 'react';
import {
  Box,
  Button,
  FormControl,
  FormLabel,
  Input,
  Select,
  VStack,
  HStack,
  IconButton,
  Heading,
  Text,
  NumberInput,
  NumberInputField,
  NumberInputStepper,
  NumberIncrementStepper,
  NumberDecrementStepper,
} from '@chakra-ui/react';
import { AddIcon, DeleteIcon } from '@chakra-ui/icons';
import { useTranslation } from 'react-i18next';
import {
  TransferFormData,
  TransferDirection,
  Airport,
  ValidationError,
} from '../types/presmeet';
import { getFieldError } from '../utils/validation';

interface TransferSectionProps {
  transfers: TransferFormData[];
  onChange: (transfers: TransferFormData[]) => void;
  maxTransfers: number;
  eventStartDate?: string;
  eventEndDate?: string;
  errors: ValidationError[];
  isDisabled?: boolean;
}

const TransferSection: React.FC<TransferSectionProps> = ({
  transfers,
  onChange,
  maxTransfers,
  eventStartDate,
  eventEndDate,
  errors,
  isDisabled = false,
}) => {
  const { t } = useTranslation('presmeet');

  const AIRPORTS: { value: Airport; label: string }[] = [
    { value: 'AMS', label: t('transfers.airport_ams') },
    { value: 'RTM', label: t('transfers.airport_rtm') },
    { value: 'EIN', label: t('transfers.airport_ein') },
  ];

  const DIRECTIONS: { value: TransferDirection; label: string }[] = [
    { value: 'pickup', label: t('transfers.direction_pickup') },
    { value: 'dropoff', label: t('transfers.direction_dropoff') },
  ];

  const canAdd = transfers.length < maxTransfers;

  const handleAdd = () => {
    if (!canAdd) return;
    onChange([
      ...transfers,
      {
        direction: 'pickup' as TransferDirection,
        airport: 'AMS' as Airport,
        flight: '',
        date: eventStartDate || '',
        time: '',
        persons: 1,
      },
    ]);
  };

  const handleRemove = (index: number) => {
    const updated = transfers.filter((_, i) => i !== index);
    onChange(updated);
  };

  const handleChange = (index: number, field: keyof TransferFormData, value: any) => {
    const updated = [...transfers];
    updated[index] = { ...updated[index], [field]: value };
    onChange(updated);
  };

  return (
    <Box>
      <HStack justify="space-between" mb={4}>
        <Heading size="md">{t('transfers.title')}</Heading>
        <Text fontSize="sm" color="gray.400">
          {transfers.length} / {maxTransfers}
        </Text>
      </HStack>

      <VStack spacing={4} align="stretch">
        {transfers.map((transfer, index) => {
          const prefix = `transfers[${index}]`;
          return (
            <Box
              key={index}
              p={4}
              borderWidth={1}
              borderColor="gray.600"
              borderRadius="md"
            >
              <HStack justify="space-between" mb={3}>
                <Text fontWeight="bold">{t('transfers.transfer_n', { n: index + 1 })}</Text>
                <IconButton
                  icon={<DeleteIcon />}
                  size="sm"
                  colorScheme="red"
                  variant="ghost"
                  onClick={() => handleRemove(index)}
                  aria-label={t('transfers.remove_transfer', { n: index + 1 })}
                  isDisabled={isDisabled}
                />
              </HStack>

              <VStack spacing={3} align="stretch">
                <HStack spacing={3}>
                  <FormControl
                    isInvalid={!!getFieldError(errors, `${prefix}.direction`)}
                  >
                    <FormLabel>{t('transfers.direction')}</FormLabel>
                    <Select
                      value={transfer.direction}
                      onChange={(e) =>
                        handleChange(index, 'direction', e.target.value)
                      }
                      isDisabled={isDisabled}
                      bg="gray.700"
                      color="white"
                      sx={{ option: { bg: '#2D3748', color: 'white' } }}
                    >
                      {DIRECTIONS.map((d) => (
                        <option key={d.value} value={d.value}>
                          {d.label}
                        </option>
                      ))}
                    </Select>
                    {getFieldError(errors, `${prefix}.direction`) && (
                      <Text color="red.300" fontSize="sm" mt={1}>
                        {getFieldError(errors, `${prefix}.direction`)}
                      </Text>
                    )}
                  </FormControl>

                  <FormControl
                    isInvalid={!!getFieldError(errors, `${prefix}.airport`)}
                  >
                    <FormLabel>{t('transfers.airport')}</FormLabel>
                    <Select
                      value={transfer.airport}
                      onChange={(e) =>
                        handleChange(index, 'airport', e.target.value)
                      }
                      isDisabled={isDisabled}
                      bg="gray.700"
                      color="white"
                      sx={{ option: { bg: '#2D3748', color: 'white' } }}
                    >
                      {AIRPORTS.map((a) => (
                        <option key={a.value} value={a.value}>
                          {a.label}
                        </option>
                      ))}
                    </Select>
                    {getFieldError(errors, `${prefix}.airport`) && (
                      <Text color="red.300" fontSize="sm" mt={1}>
                        {getFieldError(errors, `${prefix}.airport`)}
                      </Text>
                    )}
                  </FormControl>
                </HStack>

                <FormControl
                  isInvalid={!!getFieldError(errors, `${prefix}.flight`)}
                >
                  <FormLabel>{t('transfers.flight_number')}</FormLabel>
                  <Input
                    value={transfer.flight}
                    onChange={(e) => handleChange(index, 'flight', e.target.value)}
                    placeholder={t('transfers.placeholder_flight')}
                    maxLength={10}
                    isDisabled={isDisabled}
                  />
                  {getFieldError(errors, `${prefix}.flight`) && (
                    <Text color="red.300" fontSize="sm" mt={1}>
                      {getFieldError(errors, `${prefix}.flight`)}
                    </Text>
                  )}
                </FormControl>

                <HStack spacing={3}>
                  <FormControl
                    isInvalid={!!getFieldError(errors, `${prefix}.date`)}
                  >
                    <FormLabel>{t('transfers.date')}</FormLabel>
                    <Input
                      type="date"
                      value={transfer.date}
                      onChange={(e) => handleChange(index, 'date', e.target.value)}
                      min={eventStartDate}
                      max={eventEndDate}
                      isDisabled={isDisabled}
                    />
                    {getFieldError(errors, `${prefix}.date`) && (
                      <Text color="red.300" fontSize="sm" mt={1}>
                        {getFieldError(errors, `${prefix}.date`)}
                      </Text>
                    )}
                  </FormControl>

                  <FormControl
                    isInvalid={!!getFieldError(errors, `${prefix}.time`)}
                  >
                    <FormLabel>{t('transfers.time')}</FormLabel>
                    <Input
                      type="time"
                      value={transfer.time}
                      onChange={(e) => handleChange(index, 'time', e.target.value)}
                      isDisabled={isDisabled}
                    />
                    {getFieldError(errors, `${prefix}.time`) && (
                      <Text color="red.300" fontSize="sm" mt={1}>
                        {getFieldError(errors, `${prefix}.time`)}
                      </Text>
                    )}
                  </FormControl>

                  <FormControl
                    isInvalid={!!getFieldError(errors, `${prefix}.persons`)}
                  >
                    <FormLabel>{t('transfers.persons')}</FormLabel>
                    <NumberInput
                      value={transfer.persons}
                      min={1}
                      max={50}
                      onChange={(_, valueNumber) =>
                        handleChange(index, 'persons', valueNumber)
                      }
                      isDisabled={isDisabled}
                    >
                      <NumberInputField />
                      <NumberInputStepper>
                        <NumberIncrementStepper />
                        <NumberDecrementStepper />
                      </NumberInputStepper>
                    </NumberInput>
                    {getFieldError(errors, `${prefix}.persons`) && (
                      <Text color="red.300" fontSize="sm" mt={1}>
                        {getFieldError(errors, `${prefix}.persons`)}
                      </Text>
                    )}
                  </FormControl>
                </HStack>
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
          {t('transfers.add_transfer')}{!canAdd ? ` ${t('transfers.max_reached', { count: maxTransfers })}` : ''}
        </Button>
      </VStack>
    </Box>
  );
};

export default TransferSection;
