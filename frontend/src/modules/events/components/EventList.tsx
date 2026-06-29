import React, { useState, useMemo } from 'react';
import {
  Box, VStack, HStack, Button, Table, Thead, Tbody, Tr, Td,
  Badge, useToast, Text, IconButton, Stack, useBreakpointValue,
  Tooltip
} from '@chakra-ui/react';
import { AddIcon, EditIcon, DeleteIcon, CopyIcon, ExternalLinkIcon } from '@chakra-ui/icons';
import { useNavigate } from 'react-router-dom';
import EventForm from './EventForm';
import CSVExportButton from './CSVExportButton';
import { Event } from '../../../types';
import { getAuthHeadersForGet } from '../../../utils/authHeaders';
import { FunctionPermissionManager, getUserRoles } from '../../../utils/functionPermissions';
import { useFilterableTable } from '../../../hooks/useFilterableTable';
import { FilterableHeader } from '../../../components/filters';

interface EventListProps {
  events: Event[];
  onEventUpdate: () => void;
  user: any;
  permissionManager?: FunctionPermissionManager | null;
  canWriteEvents?: boolean;
}

const INITIAL_FILTERS = { name: '', start_date: '', location: '', linked_regio: '', participants: '', cost: '', revenue: '' };

function EventList({ events, onEventUpdate, user, permissionManager, canWriteEvents = false }: EventListProps) {
  const navigate = useNavigate();
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);
  const toast = useToast();

  const userRoles = getUserRoles(user);
  const canExportEvents = permissionManager?.hasFieldAccess('events', 'read', { fieldType: 'export' }) || 
                         permissionManager?.hasAccess('communication', 'write') || false;
  
  // Check if user can edit specific events based on regional permissions
  const canEditEvent = (event: Event): boolean => {
    if (!canWriteEvents) return false;
    if (permissionManager?.hasAccess('events', 'write')) return true;
    
    const eventRegion = event.linked_regio;
    if (!eventRegion || eventRegion === 'regio_all') return false;

    const regionNumber = getRegionNumber(eventRegion);
    if (regionNumber) {
      return userRoles.some(role => 
        role.includes(`Region${regionNumber}`) && 
        (role.includes('Chairman') || role.includes('Secretary'))
      );
    }
    return false;
  };

  const canDeleteEvent = (event: Event): boolean => {
    return permissionManager?.hasAccess('events', 'write') || false;
  };

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
      linked_regio: event.linked_regio || '',
      participants: String(event.participants || 0),
      cost: String(event.cost || 0),
      revenue: String(event.revenue || 0),
    }));
  }, [permissionFilteredEvents]);

  // Framework: filter + sort pipeline
  const { filters, setFilter, handleSort, sortField, sortDirection, processedData } =
    useFilterableTable(tableData, {
      initialFilters: INITIAL_FILTERS,
      defaultSort: { field: 'start_date', direction: 'desc' },
    });

  const filteredEvents = processedData as (Event & Record<string, unknown>)[];

  const handleEdit = (event: Event) => {
    if (!canEditEvent(event)) {
      toast({
        title: 'Geen toegang',
        description: 'Je hebt geen rechten om dit evenement te bewerken.',
        status: 'warning',
        duration: 3000,
      });
      return;
    }
    setSelectedEvent(event);
    setIsFormOpen(true);
  };

  const handleDuplicate = (event: Event) => {
    if (!canWriteEvents) {
      toast({
        title: 'Geen toegang',
        description: 'Je hebt geen rechten om evenementen te dupliceren.',
        status: 'warning',
        duration: 3000,
      });
      return;
    }
    const duplicatedEvent = {
      ...event,
      name: `${event.name || ''} (Kopie)`,
      start_date: '',
      end_date: '',
      registration_open: '',
      registration_close: '',
    };
    delete duplicatedEvent.event_id;
    setSelectedEvent(duplicatedEvent);
    setIsFormOpen(true);
  };

  const handleDelete = async (event: Event) => {
    if (!canDeleteEvent(event)) {
      toast({
        title: 'Geen toegang',
        description: 'Je hebt geen rechten om dit evenement te verwijderen.',
        status: 'warning',
        duration: 3000,
      });
      return;
    }
    
    if (!window.confirm(`Weet je zeker dat je "${event.name || ''}" wilt verwijderen?`)) return;
    
    try {
      const headers = await getAuthHeadersForGet();
      const response = await fetch(`${process.env.REACT_APP_API_BASE_URL || 'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod'}/events/${event.event_id}`, {
        method: 'DELETE',
        headers
      });

      if (response.ok) {
        onEventUpdate();
        toast({
          title: 'Evenement verwijderd',
          status: 'success',
          duration: 3000,
        });
      }
    } catch (error: any) {
      toast({
        title: 'Fout bij verwijderen',
        description: error.message,
        status: 'error',
        duration: 5000,
      });
    }
  };

  const formatDate = (dateStr: string) => {
    return dateStr ? new Date(dateStr).toLocaleDateString('nl-NL') : '-';
  };

  const formatCurrency = (amount: string | number) => {
    return amount ? `€${parseFloat(String(amount)).toFixed(2)}` : '€0,00';
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
                minW="120px"
              />
              <FilterableHeader
                label="Datum"
                filterValue={filters.start_date}
                onFilterChange={(v) => setFilter('start_date', v)}
                sortable
                sortDirection={sortField === 'start_date' ? sortDirection : null}
                onSort={() => handleSort('start_date')}
                minW="100px"
              />
              <FilterableHeader
                label="Locatie"
                filterValue={filters.location}
                onFilterChange={(v) => setFilter('location', v)}
                sortable
                sortDirection={sortField === 'location' ? sortDirection : null}
                onSort={() => handleSort('location')}
                minW="100px"
                display={{ base: 'none', md: 'table-cell' }}
              />
              <FilterableHeader
                label="Regio"
                filterValue={filters.linked_regio}
                onFilterChange={(v) => setFilter('linked_regio', v)}
                sortable
                sortDirection={sortField === 'linked_regio' ? sortDirection : null}
                onSort={() => handleSort('linked_regio')}
                minW="80px"
                display={{ base: 'none', lg: 'table-cell' }}
              />
              <FilterableHeader
                label="Deelnemers"
                filterValue={filters.participants}
                onFilterChange={(v) => setFilter('participants', v)}
                sortable
                sortDirection={sortField === 'participants' ? sortDirection : null}
                onSort={() => handleSort('participants')}
                minW="80px"
                display={{ base: 'none', md: 'table-cell' }}
              />
              <FilterableHeader
                label="Kosten"
                filterValue={filters.cost}
                onFilterChange={(v) => setFilter('cost', v)}
                sortable
                sortDirection={sortField === 'cost' ? sortDirection : null}
                onSort={() => handleSort('cost')}
                minW="80px"
              />
              <FilterableHeader
                label="Inkomsten"
                filterValue={filters.revenue}
                onFilterChange={(v) => setFilter('revenue', v)}
                sortable
                sortDirection={sortField === 'revenue' ? sortDirection : null}
                onSort={() => handleSort('revenue')}
                minW="80px"
              />
              <FilterableHeader
                label="Winst"
                sortable
                sortDirection={sortField === 'winst' ? sortDirection : null}
                onSort={() => handleSort('winst')}
                minW="80px"
                showFilter={false}
              />
              <FilterableHeader
                label="Acties"
                minW="120px"
                showFilter={false}
              />
            </Tr>
          </Thead>
          <Tbody>
            {filteredEvents.map((event) => {
              const kosten = parseFloat(String(event.cost || 0));
              const inkomsten = parseFloat(String(event.revenue || 0));
              const winst = inkomsten - kosten;
              
              return (
                <Tr key={event.event_id}>
                  <Td color="white" fontSize={{ base: 'xs', md: 'sm' }}>
                    <Text isTruncated maxW="120px">{event.name || ''}</Text>
                  </Td>
                  <Td color="white" fontSize={{ base: 'xs', md: 'sm' }}>
                    {formatDate(event.start_date || '')}
                    {event.end_date && event.end_date !== event.start_date && 
                      ` - ${formatDate(event.end_date)}`
                    }
                  </Td>
                  <Td color="white" fontSize={{ base: 'xs', md: 'sm' }} display={{ base: 'none', md: 'table-cell' }}>
                    <Text isTruncated maxW="100px">{event.location || ''}</Text>
                  </Td>
                  <Td color="white" fontSize={{ base: 'xs', md: 'sm' }} display={{ base: 'none', lg: 'table-cell' }}>
                    {event.linked_regio || ''}
                  </Td>
                  <Td color="white" fontSize={{ base: 'xs', md: 'sm' }} display={{ base: 'none', md: 'table-cell' }}>
                    {event.participants || 0}
                  </Td>
                  <Td color="white" fontSize={{ base: 'xs', md: 'sm' }}>{formatCurrency(kosten)}</Td>
                  <Td color="white" fontSize={{ base: 'xs', md: 'sm' }}>{formatCurrency(inkomsten)}</Td>
                  <Td>
                    <Badge colorScheme={winst >= 0 ? 'green' : 'red'} fontSize={{ base: 'xs', md: 'sm' }}>
                      {formatCurrency(winst)}
                    </Badge>
                  </Td>
                  <Td>
                    <HStack spacing={1}>
                      {canEditEvent(event as Event) ? (
                        <IconButton
                          icon={<EditIcon />}
                          size="xs"
                          colorScheme="blue"
                          onClick={() => handleEdit(event as Event)}
                          title="Bewerken"
                          aria-label="Bewerken"
                        />
                      ) : (
                        <Tooltip label="Geen rechten om te bewerken">
                          <IconButton
                            icon={<EditIcon />}
                            size="xs"
                            colorScheme="gray"
                            isDisabled
                            title="Geen rechten"
                            aria-label="Geen rechten"
                          />
                        </Tooltip>
                      )}
                      {canWriteEvents ? (
                        <IconButton
                          icon={<CopyIcon />}
                          size="xs"
                          colorScheme="green"
                          onClick={() => handleDuplicate(event as Event)}
                          title="Dupliceren"
                          aria-label="Dupliceren"
                        />
                      ) : (
                        <Tooltip label="Geen rechten om te dupliceren">
                          <IconButton
                            icon={<CopyIcon />}
                            size="xs"
                            colorScheme="gray"
                            isDisabled
                            title="Geen rechten"
                            aria-label="Geen rechten"
                          />
                        </Tooltip>
                      )}
                      {canDeleteEvent(event as Event) ? (
                        <IconButton
                          icon={<DeleteIcon />}
                          size="xs"
                          colorScheme="red"
                          onClick={() => handleDelete(event as Event)}
                          title="Verwijderen"
                          aria-label="Verwijderen"
                        />
                      ) : (
                        <Tooltip label="Geen rechten om te verwijderen">
                          <IconButton
                            icon={<DeleteIcon />}
                            size="xs"
                            colorScheme="gray"
                            isDisabled
                            title="Geen rechten"
                            aria-label="Geen rechten"
                          />
                        </Tooltip>
                      )}
                      {(event as Event & { product_ids?: string[] }).product_ids?.length ? (
                        <Tooltip label="Test booking flow">
                          <IconButton
                            icon={<ExternalLinkIcon />}
                            size="xs"
                            colorScheme="purple"
                            onClick={() => navigate(`/events/${(event as Event).event_id}/booking`)}
                            title="Test booking"
                            aria-label="Test booking flow"
                          />
                        </Tooltip>
                      ) : null}
                    </HStack>
                  </Td>
                </Tr>
              );
            })}
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
        user={user}
        permissionManager={permissionManager}
      />
    </VStack>
  );
}

export default EventList;