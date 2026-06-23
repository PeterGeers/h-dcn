/**
 * EventInfoHeader — Displays event location, dates, and days until close.
 *
 * The event name/title is rendered by the parent page (EventBookingPage),
 * so this component only shows supplementary info: location, dates, countdown.
 *
 * Validates: Requirement 11.3
 */

import React, { useMemo } from 'react';
import { Box, HStack, Text } from '@chakra-ui/react';
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
    <Box p={4} borderWidth={1} borderColor="gray.600" borderRadius="md" bg="gray.800">
      <HStack spacing={4} flexWrap="wrap">
        {event.location && (
          <Text fontSize="sm" color="gray.300">
            📍 {event.location}
          </Text>
        )}
        <Text fontSize="sm" color="gray.300">
          📅 {formatDate(event.start_date)} – {formatDate(event.end_date)}
        </Text>
      </HStack>
      {event.status === 'published' && daysUntilClose > 0 && (
        <Text fontSize="sm" mt={2} color={daysUntilClose <= 7 ? 'red.300' : 'gray.400'}>
          Nog {daysUntilClose} dagen om te registreren
        </Text>
      )}
    </Box>
  );
};

export default EventInfoHeader;
