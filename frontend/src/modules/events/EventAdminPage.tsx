import React, { useState, useEffect } from 'react';
import {
  Box, VStack, HStack, Heading, Tabs, TabList, TabPanels, Tab, TabPanel,
  useToast, Spinner, Text, Alert, AlertIcon
} from '@chakra-ui/react';
import EventList from './components/EventList';
import FinanceModule from './components/FinanceModule';
import AnalyticsDashboard from './components/AnalyticsDashboard';
import { getAuthHeadersForGet } from '../../utils/authHeaders';
import { API_URLS } from '../../config/api';
import { useErrorHandler, apiCall } from '../../utils/errorHandler';
import { FunctionPermissionManager, getUserRoles } from '../../utils/functionPermissions';

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
  const [permissionManager, setPermissionManager] = useState<FunctionPermissionManager | null>(null);
  const [permissionsLoading, setPermissionsLoading] = useState(true);
  const { handleError } = useErrorHandler();

  useEffect(() => {
    loadEvents();
    loadPermissions();
  }, []);

  const loadPermissions = async () => {
    try {
      const manager = await FunctionPermissionManager.create(user);
      setPermissionManager(manager);
    } catch (error) {
      console.error('Failed to load permissions:', error);
    } finally {
      setPermissionsLoading(false);
    }
  };

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

  // Check if user has access to events module
  const canReadEvents = permissionManager?.hasAccess('events', 'read') || false;
  const canWriteEvents = permissionManager?.hasAccess('events', 'write') || false;
  const canViewFinancials = permissionManager?.hasFieldAccess('events', 'read', { fieldType: 'financial' }) || false;
  const userRoles = getUserRoles(user);

  if (loading || permissionsLoading) {
    return (
      <Box p={6} textAlign="center">
        <Spinner size="xl" color="orange.400" />
        <Text mt={4} color="orange.400">
          {permissionsLoading ? 'Machtigingen laden...' : 'Evenementen laden...'}
        </Text>
      </Box>
    );
  }

  // If user doesn't have read access to events, show access denied
  if (!canReadEvents) {
    return (
      <Box p={6} bg="black" minH="100vh">
        <VStack spacing={6} align="center">
          <Heading color="orange.400">Evenementenadministratie</Heading>
          <Alert status="warning" bg="orange.100" color="black">
            <AlertIcon />
            Je hebt geen toegang tot de evenementenadministratie. Neem contact op met een beheerder als je toegang nodig hebt.
          </Alert>
          <Text color="gray.400" fontSize="sm">
            Huidige rollen: {userRoles.length > 0 ? userRoles.join(', ') : 'Geen rollen toegewezen'}
          </Text>
        </VStack>
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
            {canViewFinancials && (
              <Tab color="orange.400" _selected={{ bg: 'orange.400', color: 'black' }}>
                Financiën
              </Tab>
            )}
            {canReadEvents && (
              <Tab color="orange.400" _selected={{ bg: 'orange.400', color: 'black' }}>
                Analytics
              </Tab>
            )}
          </TabList>

          <TabPanels>
            <TabPanel p={0} pt={6}>
              <EventList 
                events={events} 
                onEventUpdate={handleEventUpdate}
                user={user}
                permissionManager={permissionManager}
                canWriteEvents={canWriteEvents}
              />
            </TabPanel>
            {canViewFinancials && (
              <TabPanel p={0} pt={6}>
                <FinanceModule 
                  events={events}
                  onEventUpdate={handleEventUpdate}
                  permissionManager={permissionManager}
                />
              </TabPanel>
            )}
            {canReadEvents && (
              <TabPanel p={0} pt={6}>
                <AnalyticsDashboard 
                  events={events} 
                  permissionManager={permissionManager}
                />
              </TabPanel>
            )}
          </TabPanels>
        </Tabs>
      </VStack>
    </Box>
  );
}

export default EventAdminPage;