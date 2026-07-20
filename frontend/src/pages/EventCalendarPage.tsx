import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Box,
  Container,
  Heading,
  Text,
  Image,
  SimpleGrid,
  VStack,
  HStack,
  FormControl,
  FormLabel,
  Input,
  Button,
  Spinner,
  Center,
  Alert,
  AlertIcon,
} from '@chakra-ui/react';
import { API_CONFIG } from '../config/api';
import { EVENT_TYPES, EVENT_REGIOS } from '../config/eventFields/eventTypes';
import { FilterPanel } from '../components/filters/FilterPanel';
import type { FilterConfig, FilterOption } from '../components/filters/types';
import EventDetailModal from './EventDetailModal';

// --- Types ---

interface PublicEvent {
  event_id: string;
  name: string;
  slug: string;
  event_type: string;
  location: string;
  start_date: string;
  end_date: string;
  poster_url?: string;
  description?: string;
  linked_regio?: string;
  landing_page?: Record<string, any>;
  registration_open?: string;
  registration_close?: string;
  payment_deadline?: string;
}

// --- Component ---

const EventCalendarPage: React.FC = () => {
  const { t } = useTranslation('events');

  const [events, setEvents] = useState<PublicEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<PublicEvent | null>(null);

  // Filters
  const [filterTypes, setFilterTypes] = useState<string[]>([]);
  const [filterRegio, setFilterRegio] = useState<string>('');
  const [filterDateFrom, setFilterDateFrom] = useState<string>('');
  const [filterDateTo, setFilterDateTo] = useState<string>('');

  const abortControllerRef = useRef<AbortController | null>(null);

  const fetchEvents = useCallback(async () => {
    // Abort any in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;
    const timeoutId = setTimeout(() => controller.abort(), 10000);

    try {
      setLoading(true);
      setError(null);
      const baseUrl = API_CONFIG.BASE_URL;
      const response = await fetch(`${baseUrl}/events-public`, { signal: controller.signal });
      clearTimeout(timeoutId);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data: PublicEvent[] = await response.json();
      setEvents(data);
    } catch (err) {
      clearTimeout(timeoutId);
      if (controller.signal.aborted) {
        console.error('Fetch aborted (timeout or unmount):', err);
      } else {
        console.error('Failed to fetch public events:', err);
      }
      // Only set error if this controller hasn't been superseded
      if (abortControllerRef.current === controller) {
        setError(t('calendar.error'));
      }
    } finally {
      if (abortControllerRef.current === controller) {
        setLoading(false);
      }
    }
  }, [t]);

  useEffect(() => {
    fetchEvents();
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [fetchEvents]);

  const handleTypeFilter = useCallback((values: string[]) => {
    setFilterTypes(values);
  }, []);

  const resetFilters = useCallback(() => {
    setFilterTypes([]);
    setFilterRegio('');
    setFilterDateFrom('');
    setFilterDateTo('');
  }, []);

  const filteredEvents = useMemo(() => {
    const today = new Date().toISOString().split('T')[0];

    return events
      .filter(event => {
        // Only future events (end_date >= today)
        if (event.end_date < today) return false;

        // Type filter
        if (filterTypes.length > 0 && !filterTypes.includes(event.event_type)) return false;

        // Region filter
        if (filterRegio && event.linked_regio !== filterRegio) return false;

        // Date range filter
        if (filterDateFrom && event.start_date < filterDateFrom) return false;
        if (filterDateTo && event.start_date > filterDateTo) return false;

        return true;
      })
      .sort((a, b) => a.start_date.localeCompare(b.start_date));
  }, [events, filterTypes, filterRegio, filterDateFrom, filterDateTo]);

  const formatDate = (dateStr: string): string => {
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString(undefined, {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
      });
    } catch {
      return dateStr;
    }
  };

  // Event types for the filter dropdown (exclude 'webshop')
  const typeOptions: FilterOption[] = useMemo(
    () =>
      EVENT_TYPES
        .filter(type => type !== 'webshop')
        .map(type => ({ value: type, label: t(`event_types.${type}`, type) })),
    [t]
  );

  // Region options for the filter dropdown
  const regioOptions: FilterOption[] = useMemo(
    () => EVENT_REGIOS.map(regio => ({ value: regio, label: regio })),
    []
  );

  if (loading) {
    return (
      <Center minH="100vh" bg="black">
        <VStack spacing={4}>
          <Spinner size="xl" color="orange.400" />
          <Text color="gray.400">{t('calendar.loading')}</Text>
        </VStack>
      </Center>
    );
  }

  if (error) {
    return (
      <Box minH="100vh" bg="black" p={8}>
        <Container maxW="container.xl">
          <Alert status="error" bg="red.900" color="white" borderRadius="md">
            <AlertIcon />
            {error}
          </Alert>
          <Button
            mt={4}
            colorScheme="orange"
            onClick={fetchEvents}
          >
            {t('calendar.retry')}
          </Button>
        </Container>
      </Box>
    );
  }

  return (
    <Box minH="100vh" bg="black" color="white" py={{ base: 6, md: 10 }}>
      <Container maxW="container.xl">
        {/* Title */}
        <Heading as="h1" size="xl" color="orange.400" mb={6}>
          {t('calendar.title')}
        </Heading>

        {/* Filters */}
        <HStack spacing={4} mb={8} wrap="wrap" align="end">
          <FilterPanel
            layout="horizontal"
            filters={[
              {
                type: 'multi' as const,
                label: t('calendar.filter.type'),
                options: typeOptions,
                value: filterTypes,
                onChange: (values: string[] | string) => handleTypeFilter(values as string[]),
              } as FilterConfig<any>,
              {
                type: 'single' as const,
                label: t('calendar.filter.region'),
                options: regioOptions,
                value: filterRegio,
                onChange: (v: string | string[]) => setFilterRegio(v as string),
                placeholder: t('calendar.filter.region'),
              } as FilterConfig<any>,
            ]}
          />

          <FormControl w="170px">
            <FormLabel fontSize="xs" color="orange.300" mb={1}>
              {t('calendar.filter.dateFrom')}
            </FormLabel>
            <Input
              type="date"
              value={filterDateFrom}
              onChange={e => setFilterDateFrom(e.target.value)}
              bg="gray.700"
              borderColor="gray.600"
              color="white"
              size="sm"
            />
          </FormControl>

          <FormControl w="170px">
            <FormLabel fontSize="xs" color="orange.300" mb={1}>
              {t('calendar.filter.dateTo')}
            </FormLabel>
            <Input
              type="date"
              value={filterDateTo}
              onChange={e => setFilterDateTo(e.target.value)}
              bg="gray.700"
              borderColor="gray.600"
              color="white"
              size="sm"
            />
          </FormControl>

          <Button
            size="sm"
            variant="ghost"
            colorScheme="orange"
            onClick={resetFilters}
          >
            {t('calendar.filter.reset')}
          </Button>
        </HStack>

        {/* Event Grid */}
        {filteredEvents.length === 0 ? (
          <Center py={16}>
            <Text color="gray.500" fontSize="lg">
              {t('calendar.noEvents')}
            </Text>
          </Center>
        ) : (
          <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={6} alignItems="start">
            {filteredEvents.map(event => (
              <Box
                key={event.event_id}
                bg="gray.900"
                borderRadius="lg"
                overflow="hidden"
                border="1px"
                borderColor="gray.700"
                cursor="pointer"
                transition="all 0.2s"
                _hover={{
                  borderColor: 'orange.400',
                  transform: 'translateY(-2px)',
                  shadow: 'lg',
                }}
                onClick={() => setSelectedEvent(event)}
              >
                {/* Poster — only shown when available */}
                {event.poster_url && (
                  <Image
                    src={event.poster_url}
                    alt={event.name}
                    w="100%"
                    objectFit="contain"
                    bg="gray.800"
                  />
                )}

                {/* Card content */}
                <VStack align="flex-start" p={4} spacing={2}>
                  <Heading as="h3" size="sm" color="orange.300" noOfLines={2}>
                    {event.name}
                  </Heading>
                  <Text fontSize="sm" color="gray.400">
                    {formatDate(event.start_date)}
                  </Text>
                  <Text fontSize="xs" color="gray.500" noOfLines={1}>
                    {event.location || t('calendar.card.noLocation')}
                  </Text>
                </VStack>
              </Box>
            ))}
          </SimpleGrid>
        )}
      </Container>

      {/* Event Detail Modal */}
      <EventDetailModal
        event={selectedEvent}
        isOpen={selectedEvent !== null}
        onClose={() => setSelectedEvent(null)}
      />
    </Box>
  );
};

export default EventCalendarPage;
