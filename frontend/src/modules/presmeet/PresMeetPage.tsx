/**
 * PresMeetPage — Main page for the PresMeet booking module (v3).
 *
 * Features:
 * - Loads current active event via presmeetApi.getEvent('presmeet')
 * - Shows OnboardingFlow if user has no club assignment (403 from getOrder)
 * - Booking wizard: BookingWizard, PaymentPanel, DelegateManager, BookingSummaryPdf
 * - Admin functionality moved to unified Webshop Beheer page (WebshopManagementPage)
 * - ClubLogoUploader in header
 *
 * Validates: Requirements 5.1, 5.2, 5.3, 10.1, 10.2, 10.5, 10.11
 */

import React, { useCallback, useEffect, useState } from 'react';
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
 * Only requires Products_CRUD or Webshop_Management role (no region needed).
 */
function isLogoUploadAdmin(groups: string[]): boolean {
  return groups.some((g) =>
    ['Products_CRUD', 'Webshop_Management'].includes(g)
  );
}

const PresMeetPage: React.FC = () => {
  const { t } = useTranslation('presmeet');
  const { user } = useAuth();

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
   * Load the active event and attempt to load the order.
   * If getOrder returns 403 with "Missing club assignment", show onboarding.
   */
  const loadPageData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setNeedsOnboarding(false);

    try {
      // Try to get presmeet events. If user lacks events_read permission,
      // fall back to using the order endpoint directly with a known event ID.
      let currentEvent: Event | null = null;

      try {
        const events = await presmeetApi.getEvent('presmeet');
        const openEvent = events.find((e) => e.status === 'open');
        const fallbackEvent = events.length > 0
          ? events.sort((a, b) => (b.start_date || '').localeCompare(a.start_date || ''))[0]
          : null;
        currentEvent = openEvent || fallbackEvent || null;
      } catch (eventErr: any) {
        // If 403 on events endpoint, try loading order directly with known event ID
        // The presmeet_get_order handler will return event info in its response
        console.warn('Could not fetch events (likely permission), trying direct order load');
      }

      if (!currentEvent) {
        // Fallback: try to get order without knowing the event ID
        // Use a well-known event ID if available from environment
        const fallbackEventId = process.env.REACT_APP_PRESMEET_EVENT_ID || 'pm2027-event';
        currentEvent = {
          event_id: fallbackEventId,
          event_type: 'presmeet',
          name: 'Presidents Meeting 2027',
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
        const orderData = await presmeetApi.getOrder(currentEvent.event_id);

        // Admin without personal club gets a special response (not a real order)
        if (orderData && (orderData as any).admin_no_club) {
          // Admin has no personal booking — they can manage orders via Webshop Beheer
        } else {
          setOrder(orderData);

          // Load products for the event
          const eventProducts = await presmeetApi.getProducts(
            'presmeet',
            currentEvent.product_ids
          );
          setProducts(eventProducts);
        }
      } catch (orderErr: any) {
        if (isAuthorizationError(orderErr)) {
          // 403 — check specific error message
          const msg = orderErr.message?.toLowerCase() || '';
          if (msg.includes('club') || msg.includes('assignment')) {
            setNeedsOnboarding(true);
          } else if (msg.includes('presmeet access required')) {
            // User lacks Regio_Pressmeet or Regio_All
            setError(orderErr.message);
          } else {
            setError(orderErr.message);
          }
        } else if (orderErr?.response?.status === 403) {
          // Fallback: check raw 403 response message
          const msg = (orderErr?.response?.data?.message || orderErr?.response?.data?.error || '').toLowerCase();
          if (msg.includes('club') || msg.includes('assignment')) {
            setNeedsOnboarding(true);
          } else {
            setError(
              orderErr?.response?.data?.message || orderErr?.response?.data?.error || t('page.error_loading')
            );
          }
        } else if (orderErr?.response?.status === 404) {
          // No order exists yet — valid state, show empty booking
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
  }, [t]);

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
    if (!activeEvent) return;
    try {
      const orderData = await presmeetApi.getOrder(activeEvent.event_id);
      setOrder(orderData);
    } catch {
      // Silently fail — the user can retry
    }
  }, [activeEvent]);

  // --- Loading state ---
  if (isLoading) {
    return (
      <Center h="300px">
        <Spinner size="xl" color="orange.400" />
      </Center>
    );
  }

  // --- Error state (no event or fatal error) ---
  if (error && !activeEvent && !needsOnboarding) {
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

  // --- Permission denied or no order loaded (don't render BookingWizard) ---
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
          {t('page.title')}
        </Heading>
        <OnboardingFlow
          onComplete={handleOnboardingComplete}
          eventId={activeEvent?.event_id}
        />
      </Container>
    );
  }

  // --- Main booking page ---
  const clubId = order?.club_id;

  return (
    <Container maxW="container.xl" py={6}>
      <Flex align="center" gap={3} mb={6}>
        {clubId && (
          <ClubLogoUploader clubId={clubId} isAdmin={isLogoAdmin} />
        )}
        <Heading size="lg" color="orange.400">
          {t('page.title_booking')}
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
          {/* Booking Tab */}
          <TabPanel px={0}>
            {activeEvent ? (
              <VStack spacing={6} align="stretch">
                <BookingWizard eventId={activeEvent.event_id} />

                {order && (
                  <>
                    <Divider />

                    {/* Payment Panel */}
                    {order.status !== 'draft' && (
                      <PaymentPanel
                        order={order}
                        onPaymentInitiated={reloadOrder}
                      />
                    )}

                    {/* Delegate Manager */}
                    {user?.email && (
                      <DelegateManager
                        order={order}
                        currentUserEmail={user.email}
                        onDelegateChange={reloadOrder}
                      />
                    )}

                    {/* PDF Download */}
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
                <Text>
                  {t('page.error_loading')}
                </Text>
              </Alert>
            )}
          </TabPanel>
        </TabPanels>
      </Tabs>
    </Container>
  );
};

export default PresMeetPage;
