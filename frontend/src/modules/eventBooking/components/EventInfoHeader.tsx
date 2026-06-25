/**
 * EventInfoHeader — Compact responsive layout showing event location, dates,
 * countdown, and capacity per product in a single container.
 *
 * - Horizontal layout (>768px): items flow in a row next to the page title
 * - Stacked layout (≤768px): items stack vertically at full width
 * - Capacity displayed as "[remaining] / [total]" per product with finite max_per_event
 * - Capacity section hidden if no product has a finite limit
 * - Loading spinner shown while capacity data loads
 *
 * Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6
 */

import React, { useMemo } from 'react';
import { Badge, Box, Flex, HStack, Spinner, Text, Wrap, WrapItem } from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import { Event } from '../types/eventBooking.types';
import { ProductEffectiveLimit } from '../hooks/useEffectiveLimits';

export interface EventInfoHeaderProps {
  event: Event;
  /** Effective limits per product (from useEffectiveLimits hook) */
  limits?: ProductEffectiveLimit[];
  /** Whether capacity data is currently loading */
  isLimitsLoading?: boolean;
}

const EventInfoHeader: React.FC<EventInfoHeaderProps> = ({
  event,
  limits = [],
  isLimitsLoading = false,
}) => {
  const { t } = useTranslation('eventBooking');

  const daysUntilClose = useMemo(() => {
    const closeDate = new Date(event.registration_close);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    closeDate.setHours(0, 0, 0, 0);
    return Math.ceil((closeDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
  }, [event.registration_close]);

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('nl-NL', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    });
  };

  const hasFiniteLimits = limits.some((l) => l.totalCapacity !== Infinity);

  return (
    <Box p={4} borderWidth={1} borderColor="gray.600" borderRadius="md" bg="gray.800">
      <Flex
        direction={{ base: 'column', md: 'row' }}
        gap={4}
        align={{ base: 'stretch', md: 'center' }}
      >
        {/* Location, dates, countdown */}
        <Wrap spacing={4} flex={1}>
          {event.location && (
            <WrapItem>
              <Text fontSize="sm" color="gray.300">
                📍 {event.location}
              </Text>
            </WrapItem>
          )}
          <WrapItem>
            <Text fontSize="sm" color="gray.300">
              📅 {formatDate(event.start_date)} – {formatDate(event.end_date)}
            </Text>
          </WrapItem>
          {event.status === 'published' && daysUntilClose > 0 && (
            <WrapItem>
              <Text
                fontSize="sm"
                color={daysUntilClose <= 7 ? 'red.300' : 'gray.400'}
              >
                ⏳ {t('info.days_remaining', { count: daysUntilClose })}
              </Text>
            </WrapItem>
          )}
        </Wrap>

        {/* Capacity section */}
        {isLimitsLoading && (
          <HStack spacing={2}>
            <Spinner size="xs" color="orange.300" />
            <Text fontSize="xs" color="gray.400">
              {t('limits.loading')}
            </Text>
          </HStack>
        )}
        {!isLimitsLoading && hasFiniteLimits && (
          <HStack spacing={3} flexWrap="wrap">
            {limits
              .filter((l) => l.totalCapacity !== Infinity)
              .map((limit) => (
                <HStack key={limit.product_id} spacing={1}>
                  <Text fontSize="xs" color="gray.300">
                    {limit.product_name}:
                  </Text>
                  <Badge
                    colorScheme={
                      limit.isExhausted ? 'red' : limit.remaining <= 2 ? 'orange' : 'green'
                    }
                    fontSize="xs"
                    variant="subtle"
                  >
                    {limit.remaining} / {limit.totalCapacity}
                  </Badge>
                </HStack>
              ))}
          </HStack>
        )}
      </Flex>
    </Box>
  );
};

export default EventInfoHeader;
