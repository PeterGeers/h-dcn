import React, { useState, useEffect } from 'react';
import {
  Box, VStack, HStack, Heading, Tabs, TabList, TabPanels, Tab, TabPanel,
  useToast, Spinner, Text, Alert, AlertIcon, Button
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

  // Enhanced role-based access checks for events
  const hasEventsReadRole = userRoles.some(role => 
    role === 'hdcnAdmins' ||
    role === 'Events_Read_All' ||
    role === 'Events_CRUD_All' ||
    role === 'Events_Export_All' ||
    role === 'Webmaster' ||
    role === 'Tour_Commissioner' ||
    role === 'National_Chairman' ||
    role === 'National_Secretary' ||
    role === 'Vice_Chairman' ||
    role === 'Club_Magazine_Editorial' ||
    role.includes('Regional_Chairman_') ||
    role.includes('Regional_Secretary_') ||
    role.includes('Regional_Volunteer_')
  );

  const hasEventsWriteRole = userRoles.some(role => 
    role === 'hdcnAdmins' ||
    role === 'Events_CRUD_All' ||
    role === 'Webmaster' ||
    role === 'Tour_Commissioner' ||
    role.includes('Regional_Chairman_')
  );

  const hasFinancialAccess = userRoles.some(role => 
    role === 'hdcnAdmins' ||
    role === 'Events_CRUD_All' ||
    role === 'Webmaster' ||
    role === 'National_Chairman' ||
    role === 'National_Secretary' ||
    role === 'National_Treasurer' ||
    role.includes('Regional_Treasurer_')
  );

  // Enhanced role-based functionality checks
  const hasEventsFullAccess = userRoles.some(role => 
    role === 'hdcnAdmins' ||
    role === 'Events_CRUD_All' ||
    role === 'Webmaster' ||
    role === 'Tour_Commissioner'
  );

  const hasEventsExportAccess = userRoles.some(role => 
    role === 'hdcnAdmins' ||
    role === 'Events_CRUD_All' ||
    role === 'Events_Export_All' ||
    role === 'Webmaster' ||
    role === 'Tour_Commissioner' ||
    role === 'National_Secretary' ||
    role === 'Club_Magazine_Editorial' ||
    role.includes('Regional_Secretary_')
  );

  const hasEventsAnalyticsAccess = userRoles.some(role => 
    role === 'hdcnAdmins' ||
    role === 'Events_CRUD_All' ||
    role === 'Events_Read_All' ||
    role === 'Webmaster' ||
    role === 'Tour_Commissioner' ||
    role === 'National_Chairman' ||
    role === 'National_Secretary' ||
    role.includes('Regional_Chairman_')
  );

  const finalCanReadEvents = canReadEvents || hasEventsReadRole;
  const finalCanWriteEvents = canWriteEvents || hasEventsWriteRole;
  const finalCanViewFinancials = canViewFinancials || hasFinancialAccess;
  const finalCanExportEvents = hasEventsExportAccess;
  const finalCanViewAnalytics = hasEventsAnalyticsAccess;

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
  if (!finalCanReadEvents) {
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
          <Text color="gray.400" fontSize="xs">
            Vereiste rollen: Events_Read_All, Events_CRUD_All, Webmaster, Tour_Commissioner, National_Chairman, Regional_Chairman, of andere event-gerelateerde rollen
          </Text>
        </VStack>
      </Box>
    );
  }

  return (
    <Box p={6} bg="black" minH="100vh">
      <VStack spacing={6} align="stretch">
        <Heading color="orange.400">Evenementenadministratie</Heading>
        
        {/* Enhanced functionality for different admin roles */}
        {hasEventsFullAccess && (
          <Box bg="gray.800" p={4} borderRadius="md" border="1px" borderColor="green.400" mb={4}>
            <Text color="green.400" fontWeight="bold" mb={3}>
              🎯 Geavanceerd Evenementenbeheer (Events_CRUD_All / Tour_Commissioner)
            </Text>
            <HStack spacing={4} wrap="wrap">
              <Button
                size="sm"
                colorScheme="green"
                onClick={() => {
                  // Bulk event operations
                  const upcomingEvents = events.filter(e => {
                    const eventDate = new Date(e.event_date || e.datum_van);
                    return eventDate > new Date();
                  });
                  console.log(`📅 ${upcomingEvents.length} aankomende evenementen gevonden`);
                }}
              >
                📅 Bulk Evenement Beheer
              </Button>
              <Button
                size="sm"
                colorScheme="blue"
                onClick={() => {
                  // Event template creation
                  console.log('📋 Evenement sjablonen functionaliteit');
                }}
              >
                📋 Evenement Sjablonen
              </Button>
              <Button
                size="sm"
                colorScheme="purple"
                onClick={() => {
                  // Advanced event analytics
                  const eventStats = {
                    totaal: events.length,
                    aankomend: events.filter(e => new Date(e.event_date || e.datum_van) > new Date()).length,
                    afgelopen: events.filter(e => new Date(e.event_date || e.datum_van) < new Date()).length
                  };
                  console.log('📊 Evenement statistieken:', eventStats);
                }}
              >
                📊 Geavanceerde Analytics
              </Button>
            </HStack>
          </Box>
        )}

        {(finalCanExportEvents && !hasEventsFullAccess) && (
          <Box bg="gray.800" p={4} borderRadius="md" border="1px" borderColor="blue.400" mb={4}>
            <Text color="blue.400" fontWeight="bold" mb={3}>
              📧 Evenement Communicatie & Export
            </Text>
            <HStack spacing={4} wrap="wrap">
              <Button
                size="sm"
                colorScheme="blue"
                onClick={() => {
                  // Export event participant lists
                  console.log('📧 Deelnemerslijsten export functionaliteit');
                }}
              >
                📧 Export Deelnemerslijsten
              </Button>
              <Button
                size="sm"
                colorScheme="teal"
                onClick={() => {
                  // Event newsletter content
                  console.log('📰 Evenement nieuwsbrief content');
                }}
              >
                📰 Nieuwsbrief Content
              </Button>
            </HStack>
          </Box>
        )}

        {(finalCanViewAnalytics && !hasEventsFullAccess && !finalCanExportEvents) && (
          <Box bg="gray.800" p={4} borderRadius="md" border="1px" borderColor="yellow.400" mb={4}>
            <Text color="yellow.400" fontWeight="bold" mb={3}>
              📈 Evenement Overzicht & Rapportage
            </Text>
            <HStack spacing={4} wrap="wrap">
              <Button
                size="sm"
                colorScheme="yellow"
                onClick={() => {
                  // Event overview for management
                  const eventOverview = events.map(e => ({
                    naam: e.name,
                    datum: e.event_date || e.datum_van,
                    locatie: e.location || e.locatie,
                    deelnemers: e.participants || e.aantal_deelnemers
                  }));
                  console.log('📋 Evenement overzicht:', eventOverview);
                }}
              >
                📋 Evenement Overzicht
              </Button>
              <Button
                size="sm"
                colorScheme="orange"
                onClick={() => {
                  // Regional event summary
                  console.log('🗺️ Regionale evenement samenvatting');
                }}
              >
                🗺️ Regionale Samenvatting
              </Button>
            </HStack>
          </Box>
        )}
        
        <Tabs colorScheme="orange" variant="enclosed">
          <TabList>
            <Tab color="orange.400" _selected={{ bg: 'orange.400', color: 'black' }}>
              Evenementen
            </Tab>
            {finalCanViewFinancials && (
              <Tab color="orange.400" _selected={{ bg: 'orange.400', color: 'black' }}>
                Financiën
              </Tab>
            )}
            {finalCanViewAnalytics && (
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
                canWriteEvents={finalCanWriteEvents}
              />
            </TabPanel>
            {finalCanViewFinancials && (
              <TabPanel p={0} pt={6}>
                <FinanceModule 
                  events={events}
                  onEventUpdate={handleEventUpdate}
                  permissionManager={permissionManager}
                />
              </TabPanel>
            )}
            {finalCanViewAnalytics && (
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