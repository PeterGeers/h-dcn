/**
 * EffectiveLimits — Shows effective capacity limits per product.
 *
 * Displays "X of Y remaining" for each product based on the dual limits:
 * per-order (max_per_club) and per-event (max_per_event via sold counts).
 *
 * Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 7.8
 */

import React from 'react';
import { Badge, Box, HStack, Spinner, Text, VStack } from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import { ProductEffectiveLimit } from '../hooks/useEffectiveLimits';

export interface EffectiveLimitsProps {
  limits: ProductEffectiveLimit[];
  isLoading: boolean;
}

const EffectiveLimits: React.FC<EffectiveLimitsProps> = ({ limits, isLoading }) => {
  const { t } = useTranslation('eventBooking');

  // Don't render if no limits to show (all products have unlimited capacity)
  const hasFiniteLimits = limits.some((l) => l.totalCapacity !== Infinity);
  if (!hasFiniteLimits && !isLoading) return null;

  return (
    <Box p={3} borderWidth={1} borderRadius="md" bg="blue.50">
      <Text fontSize="sm" fontWeight="medium" mb={2}>
        {t('limits.title')}
      </Text>
      {isLoading ? (
        <HStack spacing={2}>
          <Spinner size="xs" />
          <Text fontSize="xs" color="gray.600">
            {t('limits.loading')}
          </Text>
        </HStack>
      ) : (
        <VStack spacing={1} align="stretch">
          {limits
            .filter((l) => l.totalCapacity !== Infinity)
            .map((limit) => (
              <HStack key={limit.product_id} justify="space-between" fontSize="xs">
                <Text>{limit.product_name}</Text>
                <Badge
                  colorScheme={limit.isExhausted ? 'red' : limit.remaining <= 2 ? 'orange' : 'green'}
                  fontSize="xs"
                  variant="subtle"
                >
                  {t('limits.remaining', {
                    remaining: limit.remaining,
                    total: limit.totalCapacity,
                  })}
                </Badge>
              </HStack>
            ))}
        </VStack>
      )}
    </Box>
  );
};

export default EffectiveLimits;
