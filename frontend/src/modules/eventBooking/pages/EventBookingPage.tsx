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
  useToast,
} from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import axios from 'axios';
import { useAuth } from '../../../context/AuthProvider';
import { eventBookingApi, isAuthorizationError } from '../services/eventBookingApi';
import { Event, Order, Product } from '../types/eventBooking.types';
import BookingWizard from '../components/BookingWizard';
import RegistrySelector from '../components/RegistrySelector';
import PaymentPanel from '../components/PaymentPanel';
import DelegateManager from '../components/DelegateManager';
import BookingSummaryPdf from '../components/BookingSummaryPdf';
import RegistryRowLogo from '../components/RegistryRowLogo';
import { getAuthHeaders } from '../../../utils/authHeaders';

const BASE_URL =
  process.env.REACT_APP_API_BASE_URL ||
  'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod';

const EventBookingPage: React.FC = () => {
  const { t } = useTranslation('eventBooking');
  const { user } = useAuth();
  const { eventId } = useParams<{ eventId: string }>();
  const toast = useToast();

  // Page-level state
  const [activeEvent, setActiveEvent] = useState<Event | null>(null);
  const [order, setOrder] = useState<Order | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [needsOnboarding, setNeedsOnboarding] = useState(false);

  /**
   * Check if the current user is a delegate on this order (can upload logo).
   */
  const isDelegate = useCallback((): boolean => {
    if (!order || !user?.email) return false;
    const delegates = order.delegates;
    if (!delegates) return false;
    const email = user.email.toLowerCase();
    const primary = (delegates.primary || '').toLowerCase();
    const secondary = (delegates.secondary || '').toLowerCase();
    return email === primary || email === secondary;
  }, [order, user?.email]);

  /**
   * Upload logo for the registry row via /events/{event_id}/registry-logo.
   */
  const handleLogoUpload = useCallback(async (file: File) => {
    if (!eventId || !order?.registry_row_id) return;

    try {
      const reader = new FileReader();
      const base64 = await new Promise<string>((resolve, reject) => {
        reader.onload = () => {
          const result = reader.result as string;
          // Strip data URL prefix (data:image/png;base64,...)
          const base64Data = result.split(',')[1] || result;
          resolve(base64Data);
        };
        reader.onerror = reject;
        reader.readAsDataURL(file);
      });

      const headers = await getAuthHeaders();
      const response = await axios.post(
        `${BASE_URL}/events/${eventId}/registry-logo`,
        {
          image_data: base64,
          row_id: order.registry_row_id,
          content_type: file.type || 'image/png',
        },
        { headers }
      );

      const logoUrl = response.data?.logo_url;
      if (logoUrl && order) {
        setOrder({ ...order, registry_row_logo_url: logoUrl });
      }

      toast({
        title: t('page.logo_uploaded'),
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
    } catch (err: any) {
      const msg = err?.response?.data?.error || 'Upload failed';
      toast({
        title: msg,
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  }, [eventId, order, toast, t]);

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
        const events = await eventBookingApi.getEvent();
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
        const orderData = await eventBookingApi.getOrder(eventId);

        if (orderData && (orderData as any).admin_no_club) {
          // Admin has no personal booking
        } else {
          setOrder(orderData);

          // Load products for the event
          const eventProducts = await eventBookingApi.getProducts(
            eventId,
            currentEvent.product_ids
          );
          setProducts(eventProducts);
        }
      } catch (orderErr: any) {
        if (isAuthorizationError(orderErr)) {
          const errorCode = (orderErr as any)?.error_code;
          if (errorCode === 'REGISTRY_ROW_REQUIRED') {
            setNeedsOnboarding(true);
          } else {
            setError(orderErr.message);
          }
        } else if (orderErr?.response?.status === 403) {
          const errorCode = orderErr?.response?.data?.error_code;
          if (errorCode === 'REGISTRY_ROW_REQUIRED') {
            setNeedsOnboarding(true);
          } else {
            const msg = orderErr?.response?.data?.message || orderErr?.response?.data?.error;
            setError(msg || t('page.error_loading'));
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

  /** After registry row selection completes, reload page data */
  const handleRegistryRowSelected = useCallback(
    async (_rowId: string, _rowLabel: string) => {
      await loadPageData();
    },
    [loadPageData]
  );

  /** Reload order (used after delegate changes or payment) */
  const reloadOrder = useCallback(async () => {
    if (!eventId) return;
    try {
      const orderData = await eventBookingApi.getOrder(eventId);
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

  // --- Registry row selection (no registry_row_id on member) ---
  if (needsOnboarding) {
    return (
      <Container maxW="container.xl" py={6}>
        <Heading size="lg" color="orange.400" mb={6}>
          {activeEvent?.name || t('page.title')}
        </Heading>
        <RegistrySelector
          eventId={eventId}
          sessionToken={user?.accessToken || ''}
          rowLabel={activeEvent?.registry_config?.row_label}
          userEmail={user?.email}
          onSelectRow={handleRegistryRowSelected}
        />
      </Container>
    );
  }

  // --- Main booking page ---
  const registryRowLabel = order?.registry_row_label;
  const registryRowLogoUrl = order?.registry_row_logo_url;
  const eventTitle = activeEvent?.name || t('page.title_booking');

  return (
    <Container maxW="container.xl" py={6}>
      <Flex align="center" gap={3} mb={6}>
        {order?.registry_row_id && (
          <RegistryRowLogo
            logoUrl={registryRowLogoUrl}
            label={registryRowLabel}
            isAdmin={isDelegate()}
            onUpload={handleLogoUpload}
          />
        )}
        <Box>
          <Heading size="lg" color="orange.400">
            {eventTitle}
          </Heading>
          {registryRowLabel && (
            <Text fontSize="md" color="gray.300">
              {registryRowLabel}
            </Text>
          )}
        </Box>
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
                <BookingWizard eventId={activeEvent.event_id} onSubmitted={reloadOrder} />

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
