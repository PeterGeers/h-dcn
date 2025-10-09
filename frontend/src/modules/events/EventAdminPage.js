import React, { useState, useEffect } from 'react';
import {
  Box, VStack, HStack, Heading, Tabs, TabList, TabPanels, Tab, TabPanel,
  useToast, Spinner, Text
} from '@chakra-ui/react';
import EventList from './components/EventList';
import FinanceModule from './components/FinanceModule';
import AnalyticsDashboard from './components/AnalyticsDashboard';

function EventAdminPage({ user }) {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const toast = useToast();

  useEffect(() => {
    loadEvents();
  }, []);

  const loadEvents = async () => {
    try {
      const response = await fetch('https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod/events');
      if (response.ok) {
        const data = await response.json();
        setEvents(data);
      }
    } catch (error) {
      toast({
        title: 'Fout bij laden evenementen',
        description: error.message,
        status: 'error',
        duration: 5000,
      });
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