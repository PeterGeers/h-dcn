import React, { useState } from 'react';
import {
  Box, VStack, HStack, Heading, Table, Thead, Tbody, Tr, Th, Td,
  Badge, Button, Select, Text, SimpleGrid, Stat, StatLabel, StatNumber
} from '@chakra-ui/react';
import CSVExportButton from './CSVExportButton';

function FinanceModule({ events, onEventUpdate }) {
  const [statusFilter, setStatusFilter] = useState('all');
  
  // Debug: Log events data
  console.log('📊 FinanceModule - Events data:', events);
  console.log('📊 FinanceModule - Events count:', events.length);

  const eventsWithFinance = events.map(event => {
    const kosten = parseFloat(event.cost || event.kosten || 0);
    const inkomsten = parseFloat(event.revenue || event.inkomsten || 0);
    
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

  const totals = eventsWithFinance.reduce((acc, event) => ({
    kosten: acc.kosten + event.kosten,
    inkomsten: acc.inkomsten + event.inkomsten,
    winst: acc.winst + event.winst
  }), { kosten: 0, inkomsten: 0, winst: 0 });

  const formatCurrency = (amount) => {
    return `€${amount.toFixed(2)}`;
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'betaald': return 'green';
      case 'open': return 'yellow';
      case 'achterstallig': return 'red';
      default: return 'gray';
    }
  };

  const updatePaymentStatus = async (eventId, status) => {
    try {
      const response = await fetch(`https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod/events/${eventId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ betaalstatus: status })
      });

      if (response.ok) {
        onEventUpdate();
      }
    } catch (error) {
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