/**
 * EventInfoHeader — Displays event name, location, dates, and days until close.
 *
 * Shows key event information at the top of the booking wizard to give
 * the delegate context about what they're booking for and when registration ends.
 *
 * Validates: Requirement 11.3
 */

import React, { useMemo } from 'react';
import { Box, HStack, Heading, Text } from '@chakra-ui/react';
import { Event } from '../types/eventBooking.types';

export interface EventInfoHeaderProps {
  event: Event;
}

const EventInfoHeader: React.FC<EventInfoHeaderProps> = ({ event }) => {
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

  return (
    <Box p={4} borderWidth={1} borderRadius="md" bg="orange.50">
      <Heading size="md" color="orange.700" mb={2}>
        {event.name}
      </Heading>
      <HStack spacing={4} flexWrap="wrap">
        <Text fontSize="sm" color="gray.700">
          📍 {event.location}
        </Text>
        <Text fontSize="sm" color="gray.700">
          📅 {formatDate(event.start_date)} – {formatDate(event.end_date)}
        </Text>
      </HStack>
      {event.status === 'open' && (
        <Text fontSize="sm" mt={2} color={daysUntilClose <= 7 ? 'red.600' : 'gray.600'}>
          {daysUntilClose > 0
            ? `${daysUntilClose} days until registration close`
            : daysUntilClose === 0
              ? 'Registration closes today!'
              : 'Registration close date has passed'}
        </Text>
      )}
    </Box>
  );
};

export default EventInfoHeader;
