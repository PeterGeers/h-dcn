import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Select,
  Progress,
  Stat,
  StatLabel,
  StatNumber,
  StatGroup,
  Grid,
  GridItem,
  Button,
  VStack,
  HStack,
  Text,
  Heading,
  Spinner,
  Alert,
  AlertIcon,
  useToast,
} from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import { presmeetApi } from '../services/presmeetApi';
import { Event, Constraint, ReportResponse } from '../types/presmeet.types';
import { formatCurrency } from '../utils/priceCalculator';

/**
 * Constraint progress data combining the event constraint definition
 * with the current count from the overview report.
 */
interface ConstraintProgress {
  key: string;
  label: string;
  current: number;
  max: number;
}

/**
 * Payment summary data extracted from the financial report.
 */
interface PaymentSummary {
  totalCharged: number;
  totalPaid: number;
  totalOutstanding: number;
  fullyPaidClubs: number;
  totalClubs: number;
}

const EMPTY_PAYMENT_SUMMARY: PaymentSummary = {
  totalCharged: 0,
  totalPaid: 0,
  totalOutstanding: 0,
  fullyPaidClubs: 0,
  totalClubs: 0,
};

/**
 * Admin Event Dashboard — shows registration progress, constraint utilization,
 * and payment status for a selected PresMeet event.
 *
 * Requirements: 13
 */
const EventDashboard: React.FC = () => {
  const { t } = useTranslation('presmeet');
  const [events, setEvents] = useState<Event[]>([]);
  const [selectedEventId, setSelectedEventId] = useState<string>('');
  const [constraints, setConstraints] = useState<ConstraintProgress[]>([]);
  const [paymentSummary, setPaymentSummary] = useState<PaymentSummary>(EMPTY_PAYMENT_SUMMARY);
  const [loading, setLoading] = useState(false);
  const [eventsLoading, setEventsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  // Load all presmeet events on mount
  useEffect(() => {
    const loadEvents = async () => {
      setEventsLoading(true);
      try {
        const eventList = await presmeetApi.getEvent('presmeet');
        setEvents(eventList);
        // Auto-select the first event if available
        if (eventList.length > 0) {
          setSelectedEventId(eventList[0].event_id);
        }
      } catch (err) {
        toast({
          title: t('admin.failed_load_events'),
          status: 'error',
          duration: 5000,
        });
      } finally {
        setEventsLoading(false);
      }
    };

    loadEvents();
  }, [toast]);

  // Load dashboard data when selected event changes
  const loadDashboardData = useCallback(async () => {
    if (!selectedEventId) return;

    setLoading(true);
    setError(null);

    try {
      const selectedEvent = events.find((e) => e.event_id === selectedEventId);

      // Fetch overview and financial reports in parallel
      const [overviewResult, financialResult] = await Promise.all([
        presmeetApi.getReport({ type: 'overview', event_id: selectedEventId }),
        presmeetApi.getReport({ type: 'financial', event_id: selectedEventId }),
      ]);

      // Parse constraint progress from overview data
      const constraintProgress = parseConstraintProgress(
        selectedEvent?.constraints || [],
        overviewResult
      );
      setConstraints(constraintProgress);

      // Parse payment summary from financial data
      const payment = parsePaymentSummary(financialResult);
      setPaymentSummary(payment);
    } catch (err) {
      setError(t('admin.failed_load_dashboard'));
      setConstraints([]);
      setPaymentSummary(EMPTY_PAYMENT_SUMMARY);
    } finally {
      setLoading(false);
    }
  }, [selectedEventId, events]);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  const handleEventChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedEventId(e.target.value);
  };

  /**
   * Navigate to a report view with optional filters.
   */
  const navigateToReport = (
    reportType: string,
    statusFilter?: string,
    paymentStatusFilter?: string
  ) => {
    const params = new URLSearchParams();
    params.set('event_id', selectedEventId);
    params.set('type', reportType);
    if (statusFilter) params.set('status', statusFilter);
    if (paymentStatusFilter) params.set('payment_status', paymentStatusFilter);

    // Navigate using window.location for now; can be replaced with react-router navigate
    window.location.hash = `#/admin/presmeet/reports?${params.toString()}`;
  };

  if (eventsLoading) {
    return (
      <Box textAlign="center" py={10}>
        <Spinner size="xl" />
        <Text mt={4}>{t('admin.loading_events')}</Text>
      </Box>
    );
  }

  return (
    <VStack spacing={6} align="stretch">
      <Heading size="lg">{t('admin.dashboard_title')}</Heading>

      {/* Event Selector */}
      <Box bg="white" p={5} borderRadius="md" borderWidth={1}>
        <Text fontWeight="medium" mb={2}>
          {t('admin.select_event')}
        </Text>
        <Select
          placeholder={t('admin.select_event_placeholder')}
          value={selectedEventId}
          onChange={handleEventChange}
          maxW="400px"
        >
          {events.map((event) => (
            <option key={event.event_id} value={event.event_id}>
              {event.name} ({event.status})
            </option>
          ))}
        </Select>
      </Box>

      {error && (
        <Alert status="error" borderRadius="md">
          <AlertIcon />
          {error}
        </Alert>
      )}

      {loading && (
        <Box textAlign="center" py={6}>
          <Spinner size="lg" />
          <Text mt={2}>{t('admin.loading_dashboard')}</Text>
        </Box>
      )}

      {!loading && selectedEventId && (
        <>
          {/* Constraint Progress Bars */}
          <Box bg="white" p={5} borderRadius="md" borderWidth={1}>
            <Heading size="md" mb={4}>
              {t('admin.registration_progress')}
            </Heading>
            {constraints.length === 0 ? (
              <Text color="gray.500">{t('admin.no_constraints')}</Text>
            ) : (
              <VStack spacing={4} align="stretch">
                {constraints.map((constraint) => (
                  <Box key={constraint.key}>
                    <HStack justify="space-between" mb={1}>
                      <Text fontSize="sm" fontWeight="medium">
                        {constraint.label}
                      </Text>
                      <Text fontSize="sm" color="gray.600">
                        {constraint.current}/{constraint.max}
                      </Text>
                    </HStack>
                    <Progress
                      value={constraint.max > 0 ? (constraint.current / constraint.max) * 100 : 0}
                      size="md"
                      colorScheme={
                        constraint.current >= constraint.max
                          ? 'red'
                          : constraint.current >= constraint.max * 0.8
                          ? 'yellow'
                          : 'green'
                      }
                      borderRadius="md"
                      aria-label={`${constraint.label}: ${constraint.current} of ${constraint.max}`}
                    />
                  </Box>
                ))}
              </VStack>
            )}
          </Box>

          {/* Payment Summary */}
          <Box bg="white" p={5} borderRadius="md" borderWidth={1}>
            <Heading size="md" mb={4}>
              {t('admin.payment_summary')}
            </Heading>
            <StatGroup>
              <Stat>
                <StatLabel>{t('admin.total_charged')}</StatLabel>
                <StatNumber>{formatCurrency(paymentSummary.totalCharged)}</StatNumber>
              </Stat>
              <Stat>
                <StatLabel>{t('admin.total_paid')}</StatLabel>
                <StatNumber color={paymentSummary.totalPaid > 0 ? 'green.600' : undefined}>
                  {formatCurrency(paymentSummary.totalPaid)}
                </StatNumber>
              </Stat>
              <Stat>
                <StatLabel>{t('admin.outstanding')}</StatLabel>
                <StatNumber color={paymentSummary.totalOutstanding > 0 ? 'red.600' : undefined}>
                  {formatCurrency(paymentSummary.totalOutstanding)}
                </StatNumber>
              </Stat>
              <Stat>
                <StatLabel>{t('admin.fully_paid_clubs')}</StatLabel>
                <StatNumber>
                  {paymentSummary.fullyPaidClubs}/{paymentSummary.totalClubs}
                </StatNumber>
              </Stat>
            </StatGroup>
          </Box>

          {/* Report Navigation */}
          <Box bg="white" p={5} borderRadius="md" borderWidth={1}>
            <Heading size="md" mb={4}>
              {t('admin.reports')}
            </Heading>
            <Grid templateColumns={{ base: '1fr', md: 'repeat(3, 1fr)', lg: 'repeat(4, 1fr)' }} gap={3}>
              <GridItem>
                <Button
                  w="100%"
                  colorScheme="blue"
                  variant="outline"
                  onClick={() => navigateToReport('attendees')}
                >
                  Attendees
                </Button>
              </GridItem>
              <GridItem>
                <Button
                  w="100%"
                  colorScheme="blue"
                  variant="outline"
                  onClick={() => navigateToReport('party')}
                >
                  Party
                </Button>
              </GridItem>
              <GridItem>
                <Button
                  w="100%"
                  colorScheme="blue"
                  variant="outline"
                  onClick={() => navigateToReport('tshirts')}
                >
                  T-Shirts
                </Button>
              </GridItem>
              <GridItem>
                <Button
                  w="100%"
                  colorScheme="blue"
                  variant="outline"
                  onClick={() => navigateToReport('pickups')}
                >
                  Pickups
                </Button>
              </GridItem>
              <GridItem>
                <Button
                  w="100%"
                  colorScheme="blue"
                  variant="outline"
                  onClick={() => navigateToReport('dropoffs')}
                >
                  Dropoffs
                </Button>
              </GridItem>
              <GridItem>
                <Button
                  w="100%"
                  colorScheme="blue"
                  variant="outline"
                  onClick={() => navigateToReport('financial')}
                >
                  Financial
                </Button>
              </GridItem>
              <GridItem>
                <Button
                  w="100%"
                  colorScheme="blue"
                  variant="outline"
                  onClick={() => navigateToReport('overview')}
                >
                  Overview
                </Button>
              </GridItem>
            </Grid>

            {/* Filter shortcuts */}
            <Heading size="sm" mt={6} mb={3}>
              {t('admin.quick_filters')}
            </Heading>
            <Grid templateColumns={{ base: '1fr', md: 'repeat(2, 1fr)', lg: 'repeat(3, 1fr)' }} gap={3}>
              <GridItem>
                <Button
                  w="100%"
                  size="sm"
                  variant="ghost"
                  colorScheme="orange"
                  onClick={() => navigateToReport('overview', 'draft')}
                >
                  {t('admin.draft_orders')}
                </Button>
              </GridItem>
              <GridItem>
                <Button
                  w="100%"
                  size="sm"
                  variant="ghost"
                  colorScheme="blue"
                  onClick={() => navigateToReport('overview', 'submitted')}
                >
                  {t('admin.submitted_orders')}
                </Button>
              </GridItem>
              <GridItem>
                <Button
                  w="100%"
                  size="sm"
                  variant="ghost"
                  colorScheme="green"
                  onClick={() => navigateToReport('overview', 'locked')}
                >
                  {t('admin.locked_orders')}
                </Button>
              </GridItem>
              <GridItem>
                <Button
                  w="100%"
                  size="sm"
                  variant="ghost"
                  colorScheme="red"
                  onClick={() => navigateToReport('financial', undefined, 'unpaid')}
                >
                  {t('admin.unpaid_orders')}
                </Button>
              </GridItem>
              <GridItem>
                <Button
                  w="100%"
                  size="sm"
                  variant="ghost"
                  colorScheme="yellow"
                  onClick={() => navigateToReport('financial', undefined, 'partial')}
                >
                  {t('admin.partially_paid')}
                </Button>
              </GridItem>
              <GridItem>
                <Button
                  w="100%"
                  size="sm"
                  variant="ghost"
                  colorScheme="green"
                  onClick={() => navigateToReport('financial', undefined, 'paid')}
                >
                  {t('admin.fully_paid')}
                </Button>
              </GridItem>
            </Grid>
          </Box>
        </>
      )}

      {!loading && !selectedEventId && events.length === 0 && (
        <Alert status="info" borderRadius="md">
          <AlertIcon />
          {t('admin.no_events')}
        </Alert>
      )}
    </VStack>
  );
};

// --- Helper Functions ---

/**
 * Parse constraint progress from the overview report data.
 * Maps event constraints to their current utilization values.
 */
function parseConstraintProgress(
  eventConstraints: Constraint[],
  overviewReport: ReportResponse
): ConstraintProgress[] {
  const reportData = overviewReport.data || [];

  return eventConstraints.map((constraint) => {
    // Look for matching constraint data in the report
    const matchingEntry = reportData.find(
      (entry: Record<string, any>) => entry.constraint_key === constraint.key
    );

    return {
      key: constraint.key,
      label: constraint.label,
      current: matchingEntry?.current ?? 0,
      max: constraint.max,
    };
  });
}

/**
 * Parse payment summary from the financial report data.
 * Extracts totals and fully-paid club count.
 */
function parsePaymentSummary(financialReport: ReportResponse): PaymentSummary {
  const reportData = financialReport.data || [];

  // The financial report may include summary totals in the data array
  // or as aggregated fields. Handle both patterns.
  if (reportData.length === 0) {
    return EMPTY_PAYMENT_SUMMARY;
  }

  // Check if the report has a summary entry
  const summaryEntry = reportData.find(
    (entry: Record<string, any>) => entry.type === 'summary' || entry.is_summary
  );

  if (summaryEntry) {
    return {
      totalCharged: summaryEntry.total_charged ?? 0,
      totalPaid: summaryEntry.total_paid ?? 0,
      totalOutstanding: summaryEntry.total_outstanding ?? 0,
      fullyPaidClubs: summaryEntry.fully_paid_clubs ?? 0,
      totalClubs: summaryEntry.total_clubs ?? 0,
    };
  }

  // Fall back to computing from individual order entries
  let totalCharged = 0;
  let totalPaid = 0;
  let totalOutstanding = 0;
  let fullyPaidClubs = 0;

  for (const entry of reportData) {
    const charged = entry.total_amount ?? entry.total_charged ?? 0;
    const paid = entry.total_paid ?? 0;
    totalCharged += charged;
    totalPaid += paid;
    totalOutstanding += charged - paid;
    if (paid >= charged && charged > 0) {
      fullyPaidClubs++;
    }
  }

  return {
    totalCharged,
    totalPaid,
    totalOutstanding,
    fullyPaidClubs,
    totalClubs: reportData.length,
  };
}

export default EventDashboard;
