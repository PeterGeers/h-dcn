import React, { useState, useMemo } from 'react';
import {
  Box, VStack, HStack, Button, Table, Thead, Tbody, Tr, Td,
  Badge, Text, Stack, useBreakpointValue, useToast
} from '@chakra-ui/react';
import { AddIcon } from '@chakra-ui/icons';
import EventForm from './EventForm';
import CSVExportButton from './CSVExportButton';
import { Event } from '../../../types';
import { getAuthHeadersForGet } from '../../../utils/authHeaders';
import { FunctionPermissionManager, getUserRoles } from '../../../utils/functionPermissions';
import { useFilterableTable } from '../../../hooks/useFilterableTable';
import { FilterableHeader } from '../../../components/filters';
import { EVENT_TYPE_LABELS, PARTICIPATION_MODE_LABELS } from '../../../config/eventFields/eventTypes';

interface EventListProps {
  events: Event[];
  onEventUpdate: () => void;
  user: any;
  permissionManager?: FunctionPermissionManager | null;
  canWriteEvents?: boolean;
}

const INITIAL_FILTERS = { name: '', start_date: '', location: '', event_type: '', participation: '', status: '', linked_regio: '' };

function EventList({ events, onEventUpdate, user, permissionManager, canWriteEvents = false }: EventListProps) {
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);
  const toast = useToast();

  const userRoles = getUserRoles(user);
  const canExportEvents = permissionManager?.hasFieldAccess('events', 'read', { fieldType: 'export' }) || 
                         permissionManager?.hasAccess('communication', 'write') || false;
  
  const getRegionNumber = (regionName: string): string | null => {
    const regionMap: { [key: string]: string } = {
      'Noord-Holland': '1',
      'Zuid-Holland': '2', 
      'Friesland': '3',
      'Utrecht': '4',
      'Oost': '5',
      'Limburg': '6',
      'Groningen/Drente': '7',
      'Noord-Brabant/Zeeland': '8',
      'Duitsland': '9'
    };
    return regionMap[regionName] || null;
  };

  const handleDelete = async (event: Event) => {
    try {
      const headers = await getAuthHeadersForGet();
      const response = await fetch(`${process.env.REACT_APP_API_BASE_URL}/events/${event.event_id}`, {
        method: 'DELETE',
        headers
      });

      if (response.ok) {
        onEventUpdate();
        toast({ title: 'Evenement verwijderd', status: 'success', duration: 3000 });
      }
    } catch (error: any) {
      toast({ title: 'Fout bij verwijderen', description: error.message, status: 'error', duration: 5000 });
    }
  };

  const handleDuplicate = (event: Event) => {
    const duplicated = {
      ...event,
      name: `${event.name || ''} (Kopie)`,
      start_date: '',
      end_date: '',
      registration_open: '',
      registration_close: '',
    };
    delete duplicated.event_id;
    setSelectedEvent(duplicated);
    setIsFormOpen(true);
  };

  // Check if user has full event access
  const hasFullEventAccess = userRoles.some(role => 
    role === 'Events_CRUD' ||
    role === 'Events_Read' ||
    role === 'Events_Export' ||
    role === 'Regio_All' ||
    role === 'System_User_Management'
  );

  // Pre-filter: permission-based filtering (security — before framework)
  const permissionFilteredEvents = useMemo(() => {
    return events.filter(event => {
      if (hasFullEventAccess || permissionManager?.hasAccess('events', 'read')) return true;
      
      const eventRegion = event.linked_regio;
      if (eventRegion && eventRegion !== 'regio_all') {
        const regionNumber = getRegionNumber(eventRegion);
        if (regionNumber) {
          return userRoles.some(role => role.includes(`Region${regionNumber}`));
        }
      }
      return permissionManager?.hasFieldAccess('events', 'read', { fieldType: 'public' }) || false;
    });
  }, [events, hasFullEventAccess, permissionManager, userRoles]);

  // Transform events to flat records for the framework
  const tableData = useMemo(() => {
    return permissionFilteredEvents.map(event => ({
      ...event,
      name: event.name || '',
      start_date: event.start_date || '',
      location: event.location || '',
      event_type: event.event_type || '',
      participation: event.participation || '',
      status: event.status || '',
      linked_regio: event.linked_regio || '',
    }));
  }, [permissionFilteredEvents]);

  // Framework: filter + sort pipeline
  const { filters, setFilter, handleSort, sortField, sortDirection, processedData } =
    useFilterableTable(tableData, {
      initialFilters: INITIAL_FILTERS,
      defaultSort: { field: 'start_date', direction: 'desc' },
    });

  const filteredEvents = processedData as (Event & Record<string, unknown>)[];

  const handleRowClick = (event: Event) => {
    setSelectedEvent(event);
    setIsFormOpen(true);
  };

  const formatDate = (dateStr: string) => {
    return dateStr ? new Date(dateStr).toLocaleDateString('nl-NL') : '-';
  };

  const isMobile = useBreakpointValue({ base: true, md: false });

  return (
    <VStack spacing={6} align="stretch">
      <Stack 
        direction={{ base: 'column', md: 'row' }} 
        spacing={4} 
        justify="flex-end"
        align={{ base: 'stretch', md: 'center' }}
      >
        <HStack spacing={2} justify={{ base: 'center', md: 'flex-end' }}>
          {canExportEvents && (
            <CSVExportButton data={filteredEvents} filename="evenementen" />
          )}
          {canWriteEvents && (
            <Button
              leftIcon={<AddIcon />}
              colorScheme="orange"
              size={{ base: 'sm', md: 'md' }}
              onClick={() => {
                setSelectedEvent(null);
                setIsFormOpen(true);
              }}
            >
              {isMobile ? 'Nieuw' : 'Nieuw Evenement'}
            </Button>
          )}
        </HStack>
      </Stack>

      <Box 
        bg="gray.800" 
        borderRadius="md" 
        border="1px" 
        borderColor="orange.400" 
        overflow="auto"
        maxW="100%"
      >
        <Table variant="simple" size={{ base: 'sm', md: 'md' }}>
          <Thead bg="gray.700">
            <Tr>
              <FilterableHeader
                label="Naam"
                filterValue={filters.name}
                onFilterChange={(v) => setFilter('name', v)}
                sortable
                sortDirection={sortField === 'name' ? sortDirection : null}
                onSort={() => handleSort('name')}
                w="120px"
              />
              <FilterableHeader
                label="Datum"
                filterValue={filters.start_date}
                onFilterChange={(v) => setFilter('start_date', v)}
                sortable
                sortDirection={sortField === 'start_date' ? sortDirection : null}
                onSort={() => handleSort('start_date')}
                w="100px"
              />
              <FilterableHeader
                label="Locatie"
                filterValue={filters.location}
                onFilterChange={(v) => setFilter('location', v)}
                sortable
                sortDirection={sortField === 'location' ? sortDirection : null}
                onSort={() => handleSort('location')}
                w="100px"
              />
              <FilterableHeader
                label="Type"
                filterValue={filters.event_type}
                onFilterChange={(v) => setFilter('event_type', v)}
                sortable
                sortDirection={sortField === 'event_type' ? sortDirection : null}
                onSort={() => handleSort('event_type')}
                w="80px"
              />
              <FilterableHeader
                label="Deelname"
                filterValue={filters.participation}
                onFilterChange={(v) => setFilter('participation', v)}
                sortable
                sortDirection={sortField === 'participation' ? sortDirection : null}
                onSort={() => handleSort('participation')}
                w="80px"
              />
              <FilterableHeader
                label="Status"
                filterValue={filters.status}
                onFilterChange={(v) => setFilter('status', v)}
                sortable
                sortDirection={sortField === 'status' ? sortDirection : null}
                onSort={() => handleSort('status')}
                w="80px"
              />
              <FilterableHeader
                label="Regio"
                filterValue={filters.linked_regio}
                onFilterChange={(v) => setFilter('linked_regio', v)}
                sortable
                sortDirection={sortField === 'linked_regio' ? sortDirection : null}
                onSort={() => handleSort('linked_regio')}
                w="80px"
              />
            </Tr>
          </Thead>
          <Tbody>
            {filteredEvents.map((event) => (
              <Tr
                key={event.event_id}
                _hover={{ bg: 'gray.600', cursor: 'pointer' }}
                onClick={() => handleRowClick(event as Event)}
              >
                <Td color="white" fontSize={{ base: 'xs', md: 'sm' }}>
                  <Text isTruncated maxW="180px">{event.name || ''}</Text>
                </Td>
                <Td color="white" fontSize={{ base: 'xs', md: 'sm' }}>
                  {formatDate(event.start_date || '')}
                  {event.end_date && event.end_date !== event.start_date && 
                    ` - ${formatDate(event.end_date)}`
                  }
                </Td>
                <Td color="white" fontSize={{ base: 'xs', md: 'sm' }} display={{ base: 'none', md: 'table-cell' }}>
                  <Text isTruncated maxW="120px">{event.location || ''}</Text>
                </Td>
                <Td color="white" fontSize={{ base: 'xs', md: 'sm' }} display={{ base: 'none', md: 'table-cell' }}>
                  {EVENT_TYPE_LABELS[event.event_type as keyof typeof EVENT_TYPE_LABELS] || event.event_type || ''}
                </Td>
                <Td color="white" fontSize={{ base: 'xs', md: 'sm' }} display={{ base: 'none', lg: 'table-cell' }}>
                  {PARTICIPATION_MODE_LABELS[event.participation as keyof typeof PARTICIPATION_MODE_LABELS] || event.participation || ''}
                </Td>
                <Td display={{ base: 'none', lg: 'table-cell' }}>
                  <Badge
                    colorScheme={
                      event.status === 'published' ? 'green' :
                      event.status === 'archived' ? 'gray' : 'yellow'
                    }
                    fontSize={{ base: 'xs', md: 'sm' }}
                  >
                    {event.status || 'draft'}
                  </Badge>
                </Td>
                <Td color="white" fontSize={{ base: 'xs', md: 'sm' }} display={{ base: 'none', lg: 'table-cell' }}>
                  {event.linked_regio || ''}
                </Td>
              </Tr>
            ))}
          </Tbody>
        </Table>
      </Box>

      {filteredEvents.length === 0 && (
        <Text color="gray.400" textAlign="center" py={8}>
          Geen evenementen gevonden
        </Text>
      )}

      <EventForm
        isOpen={isFormOpen}
        onClose={() => {
          setIsFormOpen(false);
          setSelectedEvent(null);
        }}
        event={selectedEvent}
        onSave={onEventUpdate}
        onDelete={handleDelete}
        onDuplicate={handleDuplicate}
        user={user}
        permissionManager={permissionManager}
        canWriteEvents={canWriteEvents}
      />
    </VStack>
  );
}

export default EventList;