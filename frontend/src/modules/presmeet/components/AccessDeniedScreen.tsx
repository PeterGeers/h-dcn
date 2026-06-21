/**
 * AccessDeniedScreen — Shown when an authenticated user navigates to the
 * Booking_Form without event access (event_id not in allowed_events).
 *
 * - If the event has a landing page (landing_page_enabled + slug), show a link
 *   to /events/:slug/info so the user can register.
 * - If no landing page, instruct the user to contact the event organizer.
 *
 * Validates: Requirements 19.1, 19.2, 19.3
 */

import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  Box,
  Button,
  Heading,
  Icon,
  Text,
  VStack,
} from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import { WarningTwoIcon } from '@chakra-ui/icons';

export interface AccessDeniedScreenProps {
  /** Event URL slug — used to link to the landing/registration page */
  slug?: string;
  /** Whether the event has a landing page enabled */
  landingPageEnabled?: boolean;
  /** Event display name (optional, for context) */
  eventName?: string;
}

const AccessDeniedScreen: React.FC<AccessDeniedScreenProps> = ({
  slug,
  landingPageEnabled,
  eventName,
}) => {
  const { t } = useTranslation('eventBooking');

  const hasLandingPage = !!landingPageEnabled && !!slug;

  return (
    <Box maxW="lg" mx="auto" py={12} px={4} textAlign="center">
      <VStack spacing={6}>
        <Icon as={WarningTwoIcon} boxSize={12} color="orange.400" />

        <Heading size="lg">
          {t('access_denied.title')}
        </Heading>

        <Text color="gray.600" fontSize="md">
          {t('access_denied.message', { eventName: eventName || '' })}
        </Text>

        {hasLandingPage ? (
          <Button
            as={RouterLink}
            to={`/events/${slug}/info`}
            colorScheme="blue"
            size="lg"
          >
            {t('access_denied.register_link')}
          </Button>
        ) : (
          <Text color="gray.500" fontSize="sm">
            {t('access_denied.contact_organizer')}
          </Text>
        )}
      </VStack>
    </Box>
  );
};

export default AccessDeniedScreen;
