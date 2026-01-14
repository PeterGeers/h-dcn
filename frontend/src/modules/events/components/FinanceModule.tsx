import React, { useState } from 'react';
import {
  Box, VStack, HStack, Heading, Table, Thead, Tbody, Tr, Th, Td,
  Badge, Button, Select, Text, SimpleGrid, Stat, StatLabel, StatNumber,
  Alert, AlertIcon
} from '@chakra-ui/react';
import CSVExportButton from './CSVExportButton';
import { Event } from '../../../types';
import { getAuthHeaders } from '../../../utils/authHeaders';
import { FunctionPermissionManager, getUserRoles } from '../../../utils/functionPermissions';

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

  const eventsWithFinance: ProcessedEvent[] = events.map(event => {
    const kosten = parseFloat(String(event.cost || event.kosten || 0));
    const inkomsten = parseFloat(String(event.revenue || event.inkomsten || 0));
    
    const processedEvent = {
      ...event,
      naam: event.title || event.naam,
      datum_van: event.event_date || event.datum_van,
      kosten: kosten,
      inkomsten: inkomsten,
      winst: inkomsten - kosten,
      betaalstatus: event.betaalstatus || 'open',
      factuurnummer: event.factuurnummer || '-'
    };
    
    return processedEvent;
  });

  const filteredEvents = statusFilter === 'all' 
    ? eventsWithFinance 
    : eventsWithFinance.filter(event => event.betaalstatus === statusFilter);

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
          <Select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            bg="gray.800"
            color="orange.400"
            borderColor="orange.400"
            maxW="200px"
          >
            <option value="all">Alle statussen</option>
            <option value="open">Open</option>
            <option value="betaald">Betaald</option>
            <option value="achterstallig">Achterstallig</option>
          </Select>
          <CSVExportButton 
            data={filteredEvents} 
            filename="financien"
            columns={['naam', 'datum_van', 'kosten', 'inkomsten', 'winst', 'betaalstatus', 'factuurnummer']}
            disabled={!canExportFinancials}
            title={!canExportFinancials ? 'Geen rechten om financiële gegevens te exporteren' : ''}
          />
        </HStack>
      </HStack>

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
              <Th color="orange.300">Evenement</Th>
              <Th color="orange.300">Datum</Th>
              <Th color="orange.300">Kosten</Th>
              <Th color="orange.300">Inkomsten</Th>
              <Th color="orange.300">Winst</Th>
              <Th color="orange.300">Betaalstatus</Th>
              <Th color="orange.300">Factuurnummer</Th>
              <Th color="orange.300">Acties</Th>
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