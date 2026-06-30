/**
 * EventInfoHeader — Compact responsive layout showing event location, dates,
 * countdown, and capacity per product in a single container.
 *
 * - Horizontal layout (>768px): left column (info) + right column (capacity)
 * - Stacked layout (≤768px): items stack vertically at full width
 * - Both columns use single-line items with no extra spacing
 * - Capacity displayed as "[remaining] / [total]" per product with finite max_per_event
 * - Capacity section hidden if no product has a finite limit
 * - Loading spinner shown while capacity data loads
 * - Smart date format: "15 – 18 september 2027" (same month), "28 september – 2 oktober 2027" (different month)
 *
 * Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6
 */

import React, { useMemo } from 'react';
import { Badge, Box, Flex, HStack, Spinner, Text, VStack } from '@chakra-ui/react';
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

/**
 * Smart date range formatting:
 * - Same day: "15 september 2027"
 * - Same month: "15 – 18 september 2027"
 * - Same year, different month: "28 september – 2 oktober 2027"
 * - Different year: "28 december 2027 – 2 januari 2028"
 */
function formatDateRange(startStr: string, endStr: string): string {
  const start = new Date(startStr);
  const end = new Date(endStr);

  if (isNaN(start.getTime()) || isNaN(end.getTime())) return '';

  const sDay = start.getDate();
  const eDay = end.getDate();
  const sMonth = start.toLocaleDateString('nl-NL', { month: 'long' });
  const eMonth = end.toLocaleDateString('nl-NL', { month: 'long' });
  const sYear = start.getFullYear();
  const eYear = end.getFullYear();

  if (sYear === eYear && start.getMonth() === end.getMonth() && sDay === eDay) {
    return `${sDay} ${sMonth} ${sYear}`;
  }
  if (sYear === eYear && start.getMonth() === end.getMonth()) {
    return `${sDay} – ${eDay} ${sMonth} ${sYear}`;
  }
  if (sYear === eYear) {
    return `${sDay} ${sMonth} – ${eDay} ${eMonth} ${sYear}`;
  }
  return `${sDay} ${sMonth} ${sYear} – ${eDay} ${eMonth} ${eYear}`;
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

  const dateRange = useMemo(
    () => formatDateRange(event.start_date, event.end_date),
    [event.start_date, event.end_date]
  );

  const hasFiniteLimits = limits.some((l) => l.totalCapacity !== Infinity);

  return (
    <Box p={3} borderWidth={1} borderColor="gray.600" borderRadius="md" bg="gray.800">
      <Flex
        direction={{ base: 'column', md: 'row' }}
        gap={3}
        align={{ base: 'stretch', md: 'flex-start' }}
      >
        {/* Left: Location, dates, countdown — compact list */}
        <VStack spacing={0} align="flex-start" flex={1}>
          {event.location && (
            <Text fontSize="sm" color="gray.300">📍 {event.location}</Text>
          )}
          {dateRange && (
            <Text fontSize="sm" color="gray.300">📅 {dateRange}</Text>
          )}
          {event.status === 'published' && daysUntilClose > 0 && (
            <Text fontSize="sm" color={daysUntilClose <= 7 ? 'red.300' : 'gray.400'}>
              ⏳ {t('info.days_remaining', { count: daysUntilClose })}
            </Text>
          )}
        </VStack>

        {/* Right: Capacity per product — compact list */}
        {isLimitsLoading && (
          <HStack spacing={2}>
            <Spinner size="xs" color="orange.300" />
            <Text fontSize="xs" color="gray.400">{t('limits.loading')}</Text>
          </HStack>
        )}
        {!isLimitsLoading && hasFiniteLimits && (
          <VStack spacing={0} align="flex-start">
            {limits
              .filter((l) => l.totalCapacity !== Infinity)
              .map((limit) => (
                <HStack key={limit.product_id} spacing={1}>
                  <Text fontSize="xs" color="gray.300">{limit.product_name}:</Text>
                  <Badge
                    colorScheme={limit.isExhausted ? 'red' : limit.remaining <= 2 ? 'orange' : 'green'}
                    fontSize="xs"
                    variant="subtle"
                  >
                    {limit.remaining} / {limit.totalCapacity}
                  </Badge>
                </HStack>
              ))}
          </VStack>
        )}
      </Flex>
    </Box>
  );
};

export default EventInfoHeader;
