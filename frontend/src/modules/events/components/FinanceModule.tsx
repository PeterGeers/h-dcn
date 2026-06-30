import React, { useState, useMemo } from 'react';
import {
  Box, VStack, HStack, Heading, Table, Thead, Tbody, Tr, Td,
  Badge, Select, Text, SimpleGrid, Stat, StatLabel, StatNumber,
} from '@chakra-ui/react';
import CSVExportButton from './CSVExportButton';
import { Event } from '../../../types';
import { getAuthHeaders } from '../../../utils/authHeaders';
import { FunctionPermissionManager, getUserRoles } from '../../../utils/functionPermissions';
import { useFilterableTable } from '../../../hooks/useFilterableTable';
import { FilterableHeader } from '../../../components/filters';
import { FilterPanel, GenericFilter } from '../../../components/filters';

interface ProcessedEvent extends Event {
  naam: string;
  datum_van: string;
  kosten: number;
  inkomsten: number;
  winst: number;
  betaalstatus: string;
  factuurnummer: string;
}

interface FinanceTotals {
  kosten: number;
  inkomsten: number;
  winst: number;
}

interface FinanceModuleProps {
  events: Event[];
  onEventUpdate: () => void;
  permissionManager?: FunctionPermissionManager | null;
  user?: any;
}

function FinanceModule({ events, onEventUpdate, permissionManager, user }: FinanceModuleProps) {
  const [statusFilter, setStatusFilter] = useState('all');
  
  // Debug: Log events data
  console.log('📊 FinanceModule - Events data:', events);
  console.log('📊 FinanceModule - Events count:', events.length);

  // Get user roles for permission checks within the component
  const userRoles = user ? getUserRoles(user) : [];
  
  // Check edit and export permissions for conditional rendering within the module
  const hasEditFinancialRole = userRoles.some(role => 
    role === 'Events_CRUD' ||
    role === 'System_User_Management'
  );
  
  const canEditFinancials = permissionManager?.hasFieldAccess('events', 'write', { fieldType: 'financial' }) || hasEditFinancialRole;
  
  const hasExportRole = userRoles.some(role => 
    role === 'Events_CRUD' ||
    role === 'Events_Export' ||
    role === 'System_User_Management' ||
    role === 'Communication_Export'
  );
  
  const canExportFinancials = permissionManager?.hasFieldAccess('events', 'read', { fieldType: 'export' }) || 
                             permissionManager?.hasAccess('communication', 'write') || 
                             hasExportRole;

  // Access check is now handled by FunctionGuard wrapper - no need for duplicate check here

  const eventsWithFinance: ProcessedEvent[] = useMemo(() => events.map(event => {
    const kosten = parseFloat(String(event.cost || 0));
    const inkomsten = parseFloat(String(event.revenue || 0));
    
    return {
      ...event,
      naam: event.name || '',
      datum_van: event.start_date || '',
      kosten: kosten,
      inkomsten: inkomsten,
      winst: inkomsten - kosten,
      betaalstatus: 'open',
      factuurnummer: '-'
    };
  }), [events]);

  // Pre-filter by status dropdown (before framework)
  const preFilteredEvents = useMemo(() => {
    if (statusFilter === 'all') return eventsWithFinance;
    return eventsWithFinance.filter(event => event.betaalstatus === statusFilter);
  }, [eventsWithFinance, statusFilter]);

  const INITIAL_FILTERS = { naam: '', datum_van: '', kosten: '', inkomsten: '', winst: '' };

  // Framework: filter + sort on pre-filtered data
  const { filters, setFilter, handleSort, sortField, sortDirection, processedData, hasActiveFilters, resetFilters } =
    useFilterableTable(preFilteredEvents as unknown as Record<string, unknown>[], {
      initialFilters: INITIAL_FILTERS,
      defaultSort: { field: 'datum_van', direction: 'desc' },
    });

  const filteredEvents = processedData as unknown as ProcessedEvent[];

  const totals: FinanceTotals = eventsWithFinance.reduce((acc, event) => ({
    kosten: acc.kosten + event.kosten,
    inkomsten: acc.inkomsten + event.inkomsten,
    winst: acc.winst + event.winst
  }), { kosten: 0, inkomsten: 0, winst: 0 });

  const formatCurrency = (amount: number) => {
    return `€${amount.toFixed(2)}`;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'betaald': return 'green';
      case 'open': return 'yellow';
      case 'achterstallig': return 'red';
      default: return 'gray';
    }
  };

  const updatePaymentStatus = async (eventId: string, status: string) => {
    if (!canEditFinancials) {
      console.warn('User does not have permission to edit financial data');
      return;
    }
    
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`${process.env.REACT_APP_API_BASE_URL || 'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod'}/events/${eventId}`, {
        method: 'PATCH',
        headers,
        body: JSON.stringify({ betaalstatus: status })
      });

      if (response.ok) {
        onEventUpdate();
      }
    } catch (error: any) {
      console.error('Error updating payment status:', error);
    }
  };

  return (
    <VStack spacing={6} align="stretch">
      <HStack justify="space-between">
        <Heading size="lg" color="orange.400">Financieel Overzicht</Heading>
        <HStack>
          <CSVExportButton 
            data={filteredEvents} 
            filename="financien"
            columns={['naam', 'datum_van', 'kosten', 'inkomsten', 'winst', 'betaalstatus', 'factuurnummer']}
            disabled={!canExportFinancials}
            title={!canExportFinancials ? 'Geen rechten om financiële gegevens te exporteren' : ''}
          />
        </HStack>
      </HStack>

      {/* Filter Panel */}
      <FilterPanel
        hasActiveFilters={statusFilter !== 'all' || hasActiveFilters}
        onReset={() => { setStatusFilter('all'); resetFilters(); }}
        filteredCount={filteredEvents.length}
        totalCount={eventsWithFinance.length}
      >
        <GenericFilter
          label="Betaalstatus"
          value={statusFilter === 'all' ? '' : statusFilter}
          options={[
            { value: 'open', label: 'Open' },
            { value: 'betaald', label: 'Betaald' },
            { value: 'achterstallig', label: 'Achterstallig' },
          ]}
          onChange={(v) => setStatusFilter(v || 'all')}
          placeholder="Alle statussen"
        />
      </FilterPanel>

      {/* Financial Summary */}
      <SimpleGrid columns={3} spacing={6}>
        <Box bg="gray.800" p={6} borderRadius="md" border="1px" borderColor="red.400">
          <Stat>
            <StatLabel color="red.300">Totale Kosten</StatLabel>
            <StatNumber color="red.400">{formatCurrency(totals.kosten)}</StatNumber>
          </Stat>
        </Box>
        <Box bg="gray.800" p={6} borderRadius="md" border="1px" borderColor="green.400">
          <Stat>
            <StatLabel color="green.300">Totale Inkomsten</StatLabel>
            <StatNumber color="green.400">{formatCurrency(totals.inkomsten)}</StatNumber>
          </Stat>
        </Box>
        <Box bg="gray.800" p={6} borderRadius="md" border="1px" borderColor={totals.winst >= 0 ? "green.400" : "red.400"}>
          <Stat>
            <StatLabel color={totals.winst >= 0 ? "green.300" : "red.300"}>Totale Winst</StatLabel>
            <StatNumber color={totals.winst >= 0 ? "green.400" : "red.400"}>
              {formatCurrency(totals.winst)}
            </StatNumber>
          </Stat>
        </Box>
      </SimpleGrid>

      {/* Events Table */}
      <Box bg="gray.800" borderRadius="md" border="1px" borderColor="orange.400" overflow="hidden">
        <Table variant="simple">
          <Thead bg="gray.700">
            <Tr>
              <FilterableHeader
                label="Evenement"
                filterValue={filters.naam}
                onFilterChange={(v) => setFilter('naam', v)}
                sortable
                sortDirection={sortField === 'naam' ? sortDirection : null}
                onSort={() => handleSort('naam')}
                minW="150px"
              />
              <FilterableHeader
                label="Datum"
                filterValue={filters.datum_van}
                onFilterChange={(v) => setFilter('datum_van', v)}
                sortable
                sortDirection={sortField === 'datum_van' ? sortDirection : null}
                onSort={() => handleSort('datum_van')}
                minW="100px"
              />
              <FilterableHeader
                label="Kosten"
                filterValue={filters.kosten}
                onFilterChange={(v) => setFilter('kosten', v)}
                sortable
                sortDirection={sortField === 'kosten' ? sortDirection : null}
                onSort={() => handleSort('kosten')}
                minW="100px"
              />
              <FilterableHeader
                label="Inkomsten"
                filterValue={filters.inkomsten}
                onFilterChange={(v) => setFilter('inkomsten', v)}
                sortable
                sortDirection={sortField === 'inkomsten' ? sortDirection : null}
                onSort={() => handleSort('inkomsten')}
                minW="100px"
              />
              <FilterableHeader
                label="Winst"
                filterValue={filters.winst}
                onFilterChange={(v) => setFilter('winst', v)}
                sortable
                sortDirection={sortField === 'winst' ? sortDirection : null}
                onSort={() => handleSort('winst')}
                minW="100px"
              />
              <FilterableHeader
                label="Status"
                showFilter={false}
                sortable
                sortDirection={sortField === 'betaalstatus' ? sortDirection : null}
                onSort={() => handleSort('betaalstatus')}
                minW="100px"
              />
              <FilterableHeader
                label="Factuurnr"
                showFilter={false}
                minW="100px"
              />
              <FilterableHeader
                label="Acties"
                showFilter={false}
                minW="120px"
              />
            </Tr>
          </Thead>
          <Tbody>
            {filteredEvents.map((event) => (
              <Tr key={event.event_id}>
                <Td color="white">{event.naam}</Td>
                <Td color="white">
                  {event.datum_van ? new Date(event.datum_van).toLocaleDateString('nl-NL') : '-'}
                </Td>
                <Td color="white">{formatCurrency(event.kosten)}</Td>
                <Td color="white">{formatCurrency(event.inkomsten)}</Td>
                <Td>
                  <Badge colorScheme={event.winst >= 0 ? 'green' : 'red'}>
                    {formatCurrency(event.winst)}
                  </Badge>
                </Td>
                <Td>
                  <Badge colorScheme={getStatusColor(event.betaalstatus)}>
                    {event.betaalstatus}
                  </Badge>
                </Td>
                <Td color="white">{event.factuurnummer}</Td>
                <Td>
                  {canEditFinancials ? (
                    <Select
                      size="sm"
                      value={event.betaalstatus}
                      onChange={(e) => updatePaymentStatus(event.event_id, e.target.value)}
                      bg="gray.700"
                      color="white"
                      borderColor="orange.400"
                    >
                      <option value="open">Open</option>
                      <option value="betaald">Betaald</option>
                      <option value="achterstallig">Achterstallig</option>
                    </Select>
                  ) : (
                    <Text color="gray.400" fontSize="sm">Alleen lezen</Text>
                  )}
                </Td>
              </Tr>
            ))}
          </Tbody>
        </Table>
      </Box>

      {filteredEvents.length === 0 && (
        <Text color="gray.400" textAlign="center" py={8}>
          Geen evenementen gevonden voor de geselecteerde filter
        </Text>
      )}
    </VStack>
  );
}

export default FinanceModule;