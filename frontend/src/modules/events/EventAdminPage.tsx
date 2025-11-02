import React, { useState, useEffect } from 'react';
import {
  Box, VStack, HStack, Heading, Tabs, TabList, TabPanels, Tab, TabPanel,
  useToast, Spinner, Text
} from '@chakra-ui/react';
import EventList from './components/EventList';
import FinanceModule from './components/FinanceModule';
import AnalyticsDashboard from './components/AnalyticsDashboard';
import { getAuthHeadersForGet } from '../../utils/authHeaders';
import { API_URLS } from '../../config/api';
import { useErrorHandler, apiCall } from '../../utils/errorHandler';

interface User {
  attributes?: {
    email?: string;
    given_name?: string;
  };
}

interface EventAdminPageProps {
  user: User;
}

interface Event {
  event_id?: string;
  name?: string;
  event_date?: string;
  datum_van?: string;
  location?: string;
  locatie?: string;
  participants?: string | number;
  aantal_deelnemers?: string | number;
  revenue?: string | number;
  inkomsten?: string | number;
  cost?: string | number;
  kosten?: string | number;
}

function EventAdminPage({ user }: EventAdminPageProps) {
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const { handleError } = useErrorHandler();

  useEffect(() => {
    loadEvents();
  }, []);

  const loadEvents = async () => {
    try {
      const headers = await getAuthHeadersForGet();
      const data = await apiCall<Event[]>(
        fetch(API_URLS.events(), { headers }),
        'laden evenementen'
      );
      setEvents(data);
    } catch (error: any) {
      handleError(error, 'laden evenementen');
    } finally {
      setLoading(false);
    }
  };

  const handleEventUpdate = () => {
    loadEvents();
  };

  if (loading) {
    return (
      <Box p={6} textAlign="center">
        <Spinner size="xl" color="orange.400" />
        <Text mt={4} color="orange.400">Evenementen laden...</Text>
      </Box>
    );
  }

  return (
    <Box p={6} bg="black" minH="100vh">
      <VStack spacing={6} align="stretch">
        <Heading color="orange.400">Evenementenadministratie</Heading>
        
        <Tabs colorScheme="orange" variant="enclosed">
          <TabList>
            <Tab color="orange.400" _selected={{ bg: 'orange.400', color: 'black' }}>
              Evenementen
            </Tab>
            <Tab color="orange.400" _selected={{ bg: 'orange.400', color: 'black' }}>
              Financiën
            </Tab>
            <Tab color="orange.400" _selected={{ bg: 'orange.400', color: 'black' }}>
              Analytics
            </Tab>
          </TabList>

          <TabPanels>
            <TabPanel p={0} pt={6}>
              <EventList 
                events={events} 
                onEventUpdate={handleEventUpdate}
                user={user}
              />
            </TabPanel>
            <TabPanel p={0} pt={6}>
              <FinanceModule 
                events={events}
                onEventUpdate={handleEventUpdate}
              />
            </TabPanel>
            <TabPanel p={0} pt={6}>
              <AnalyticsDashboard events={events} />
            </TabPanel>
          </TabPanels>
        </Tabs>
      </VStack>
    </Box>
  );
}

export default EventAdminPage;