/**
 * EventBookingPage — Generic event booking page that reads event_id from URL params.
 *
 * Route: /events/:eventId/booking
 *
 * This component replaces the hardcoded presmeet event detection by accepting the
 * event_id directly from the route. It loads the event, order, and products using
 * the unified booking API endpoints.
 *
 * Validates: Requirements 6.7, 10.8
 */

import React, { useCallback, useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  Box,
  Container,
  Heading,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
  Spinner,
  Center,
  Alert,
  AlertIcon,
  AlertTitle,
  AlertDescription,
  Text,
  Flex,
  VStack,
  Divider,
} from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../context/AuthProvider';
import { presmeetApi, isAuthorizationError } from './services/presmeetApi';
import { Event, Order, Product } from './types/presmeet.types';
import BookingWizard from './components/BookingWizard';
import OnboardingFlow from './components/OnboardingFlow';
import PaymentPanel from './components/PaymentPanel';
import DelegateManager from './components/DelegateManager';
import BookingSummaryPdf from './components/BookingSummaryPdf';
import ClubLogoUploader from './components/ClubLogoUploader';

/**
 * Check if user has logo upload admin rights.
 */
function isLogoUploadAdmin(groups: string[]): boolean {
  return groups.some((g) =>
    ['Products_CRUD', 'Webshop_Management'].includes(g)
  );
}

const EventBookingPage: React.FC = () => {
  const { t } = useTranslation('presmeet');
  const { user } = useAuth();
  const { eventId } = useParams<{ eventId: string }>();

  // Page-level state
  const [activeEvent, setActiveEvent] = useState<Event | null>(null);
  const [order, setOrder] = useState<Order | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [needsOnboarding, setNeedsOnboarding] = useState(false);

  const userGroups = (user?.groups as string[]) ?? [];
  const isLogoAdmin = isLogoUploadAdmin(userGroups);

  /**
   * Load the event by ID and attempt to load the order.
   * The event_id comes from the URL route param, not from hardcoded detection.
   */
  const loadPageData = useCallback(async () => {
    if (!eventId) {
      setError('No event ID provided in URL');
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    setNeedsOnboarding(false);

    try {
      // Load event info — try fetching events and find the one matching our eventId
      let currentEvent: Event | null = null;

      try {
        const events = await presmeetApi.getEvent();
        currentEvent = events.find((e) => e.event_id === eventId) || null;
      } catch (eventErr: any) {
        // If events endpoint fails (permission issue), construct minimal event from ID
        console.warn('Could not fetch events, proceeding with event_id from URL');
      }

      // If we couldn't find the event from events list, construct a minimal placeholder
      // The order endpoint will validate the event_id server-side
      if (!currentEvent) {
        currentEvent = {
          event_id: eventId,
          event_type: '',
          name: '',
          location: '',
          status: 'open',
          start_date: '',
          end_date: '',
          registration_open: '',
          registration_close: '',
          payment_deadline: '',
          product_ids: [],
          constraints: [],
          created_at: '',
          created_by: '',
        };
      }

      setActiveEvent(currentEvent);

      // Try to load the order for this event
      try {
        const orderData = await presmeetApi.getOrder(eventId);

        if (orderData && (orderData as any).admin_no_club) {
          // Admin has no personal booking
        } else {
          setOrder(orderData);

          // Load products for the event
          const eventProducts = await presmeetApi.getProducts(
            eventId,
            currentEvent.product_ids
          );
          setProducts(eventProducts);
        }
      } catch (orderErr: any) {
        if (isAuthorizationError(orderErr)) {
          const msg = orderErr.message?.toLowerCase() || '';
          if (msg.includes('club') || msg.includes('assignment')) {
            setNeedsOnboarding(true);
          } else {
            setError(orderErr.message);
          }
        } else if (orderErr?.response?.status === 403) {
          const msg = (orderErr?.response?.data?.message || orderErr?.response?.data?.error || '').toLowerCase();
          if (msg.includes('club') || msg.includes('assignment')) {
            setNeedsOnboarding(true);
          } else {
            setError(
              orderErr?.response?.data?.message || orderErr?.response?.data?.error || t('page.error_loading')
            );
          }
        } else if (orderErr?.response?.status === 404) {
          // No order exists yet — valid state
        } else {
          throw orderErr;
        }
      }
    } catch (err: any) {
      const message =
        err?.message || err?.response?.data?.message || t('page.error_loading');
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [eventId, t]);

  useEffect(() => {
    loadPageData();
  }, [loadPageData]);

  /** After onboarding completes, reload page data */
  const handleOnboardingComplete = useCallback(
    async (_clubId: string) => {
      await loadPageData();
    },
    [loadPageData]
  );

  /** Reload order (used after delegate changes or payment) */
  const reloadOrder = useCallback(async () => {
    if (!eventId) return;
    try {
      const orderData = await presmeetApi.getOrder(eventId);
      setOrder(orderData);
    } catch {
      // Silently fail — the user can retry
    }
  }, [eventId]);

  // --- Loading state ---
  if (isLoading) {
    return (
      <Center h="300px">
        <Spinner size="xl" color="orange.400" />
      </Center>
    );
  }

  // --- No event ID ---
  if (!eventId) {
    return (
      <Container maxW="container.lg" py={6}>
        <Alert status="error" borderRadius="md">
          <AlertIcon />
          <Box>
            <AlertTitle>Missing Event</AlertTitle>
            <AlertDescription>No event ID was provided in the URL.</AlertDescription>
          </Box>
        </Alert>
      </Container>
    );
  }

  // --- Error state ---
  if (error && !order && !needsOnboarding) {
    return (
      <Container maxW="container.lg" py={6}>
        <Alert status="error" borderRadius="md">
          <AlertIcon />
          <Box>
            <AlertTitle>{t('page.error_loading')}</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Box>
        </Alert>
      </Container>
    );
  }

  // --- Onboarding flow (no club assignment) ---
  if (needsOnboarding) {
    return (
      <Container maxW="container.xl" py={6}>
        <Heading size="lg" color="orange.400" mb={6}>
          {activeEvent?.name || t('page.title')}
        </Heading>
        <OnboardingFlow
          onComplete={handleOnboardingComplete}
          eventId={eventId}
        />
      </Container>
    );
  }

  // --- Main booking page ---
  const clubId = order?.club_id;
  const eventTitle = activeEvent?.name || t('page.title_booking');

  return (
    <Container maxW="container.xl" py={6}>
      <Flex align="center" gap={3} mb={6}>
        {clubId && (
          <ClubLogoUploader clubId={clubId} isAdmin={isLogoAdmin} />
        )}
        <Heading size="lg" color="orange.400">
          {eventTitle}
        </Heading>
      </Flex>

      {error && (
        <Alert status="warning" mb={4} borderRadius="md">
          <AlertIcon />
          <Text>{error}</Text>
        </Alert>
      )}

      <Tabs colorScheme="orange" variant="enclosed">
        <TabList>
          <Tab>{t('page.tab_booking')}</Tab>
        </TabList>

        <TabPanels>
          <TabPanel px={0}>
            {activeEvent ? (
              <VStack spacing={6} align="stretch">
                <BookingWizard eventId={activeEvent.event_id} />

                {order && (
                  <>
                    <Divider />

                    {order.status !== 'draft' && (
                      <PaymentPanel
                        order={order}
                        onPaymentInitiated={reloadOrder}
                      />
                    )}

                    {user?.email && (
                      <DelegateManager
                        order={order}
                        currentUserEmail={user.email}
                        onDelegateChange={reloadOrder}
                      />
                    )}

                    {products.length > 0 && (
                      <BookingSummaryPdf
                        order={order}
                        event={activeEvent}
                        products={products}
                      />
                    )}
                  </>
                )}
              </VStack>
            ) : (
              <Alert status="info" borderRadius="md">
                <AlertIcon />
                <Text>{t('page.error_loading')}</Text>
              </Alert>
            )}
          </TabPanel>
        </TabPanels>
      </Tabs>
    </Container>
  );
};

export default EventBookingPage;
