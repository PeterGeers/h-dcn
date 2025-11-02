import React, { useState } from 'react';
import {
  Box, VStack, HStack, Button, Table, Thead, Tbody, Tr, Th, Td,
  Input, Badge, useToast, Text, IconButton, Stack, useBreakpointValue
} from '@chakra-ui/react';
import { AddIcon, EditIcon, DeleteIcon, SearchIcon, CopyIcon } from '@chakra-ui/icons';
import EventForm from './EventForm';
import CSVExportButton from './CSVExportButton';
import { Event } from '../../../types';
import { getAuthHeadersForGet } from '../../../utils/authHeaders';

interface EventListProps {
  events: Event[];
  onEventUpdate: () => void;
  user: any;
}

function EventList({ events, onEventUpdate, user }: EventListProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState<Event | null>(null);
  const toast = useToast();

  const filteredEvents = events
    .filter(event =>
      (event.title || event.naam)?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (event.location || event.locatie)?.toLowerCase().includes(searchTerm.toLowerCase())
    )
    .sort((a, b) => {
      const dateA = new Date(a.event_date || a.datum_van || '1900-01-01');
      const dateB = new Date(b.event_date || b.datum_van || '1900-01-01');
      return dateB.getTime() - dateA.getTime(); // Newest first
    });

  const handleEdit = (event: Event) => {
    setSelectedEvent(event);
    setIsFormOpen(true);
  };

  const handleDuplicate = (event: Event) => {
    const duplicatedEvent = {
      ...event,
      title: `${getEventField(event, 'naam')} (Kopie)`,
      event_date: '',
      end_date: ''
    };
    delete duplicatedEvent.event_id;
    setSelectedEvent(duplicatedEvent);
    setIsFormOpen(true);
  };

  const handleDelete = async (event: Event) => {
    if (!window.confirm(`Weet je zeker dat je "${getEventField(event, 'naam')}" wilt verwijderen?`)) return;
    
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

  const getEventField = (event: Event, field: string) => {
    // Map backend fields to display values
    const fieldMap = {
      naam: event.title || event.naam || '',
      datum_van: event.event_date || event.datum_van || '',
      datum_tot: event.end_date || event.datum_tot || '',
      locatie: event.location || event.locatie || '',
      regio: event.region || event.regio || '',
      aantal_deelnemers: event.participants || event.aantal_deelnemers || 0,
      kosten: event.cost || event.kosten || 0,
      inkomsten: event.revenue || event.inkomsten || 0
    };
    return fieldMap[field] || '';
  };

  const isMobile = useBreakpointValue({ base: true, md: false });

  return (
    <VStack spacing={6} align="stretch">
      <Stack 
        direction={{ base: 'column', md: 'row' }} 
        spacing={4} 
        justify="space-between"
        align={{ base: 'stretch', md: 'center' }}
      >
        <HStack flex={1}>
          <SearchIcon color="orange.400" />
          <Input
            placeholder="Zoek evenementen..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            bg="gray.800"
            color="white"
            borderColor="orange.400"
          />
        </HStack>
        <HStack spacing={2} justify={{ base: 'center', md: 'flex-end' }}>
          <CSVExportButton data={filteredEvents} filename="evenementen" />
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
              <Th color="orange.300" minW="120px">Naam</Th>
              <Th color="orange.300" minW="100px">Datum</Th>
              <Th color="orange.300" minW="100px" display={{ base: 'none', md: 'table-cell' }}>Locatie</Th>
              <Th color="orange.300" minW="80px" display={{ base: 'none', lg: 'table-cell' }}>Regio</Th>
              <Th color="orange.300" minW="80px" display={{ base: 'none', md: 'table-cell' }}>Deelnemers</Th>
              <Th color="orange.300" minW="80px">Kosten</Th>
              <Th color="orange.300" minW="80px">Inkomsten</Th>
              <Th color="orange.300" minW="80px">Winst</Th>
              <Th color="orange.300" minW="120px" position="sticky" right={0} bg="gray.700">Acties</Th>
            </Tr>
          </Thead>
          <Tbody>
            {filteredEvents.map((event) => {
              const kosten = parseFloat(getEventField(event, 'kosten'));
              const inkomsten = parseFloat(getEventField(event, 'inkomsten'));
              const winst = inkomsten - kosten;
              
              return (
                <Tr key={event.event_id}>
                  <Td color="white" fontSize={{ base: 'xs', md: 'sm' }}>
                    <Text isTruncated maxW="120px">{getEventField(event, 'naam')}</Text>
                  </Td>
                  <Td color="white" fontSize={{ base: 'xs', md: 'sm' }}>
                    {formatDate(getEventField(event, 'datum_van'))}
                    {getEventField(event, 'datum_tot') && getEventField(event, 'datum_tot') !== getEventField(event, 'datum_van') && 
                      ` - ${formatDate(getEventField(event, 'datum_tot'))}`
                    }
                  </Td>
                  <Td color="white" fontSize={{ base: 'xs', md: 'sm' }} display={{ base: 'none', md: 'table-cell' }}>
                    <Text isTruncated maxW="100px">{getEventField(event, 'locatie')}</Text>
                  </Td>
                  <Td color="white" fontSize={{ base: 'xs', md: 'sm' }} display={{ base: 'none', lg: 'table-cell' }}>
                    {getEventField(event, 'regio')}
                  </Td>
                  <Td color="white" fontSize={{ base: 'xs', md: 'sm' }} display={{ base: 'none', md: 'table-cell' }}>
                    {getEventField(event, 'aantal_deelnemers')}
                  </Td>
                  <Td color="white" fontSize={{ base: 'xs', md: 'sm' }}>{formatCurrency(kosten)}</Td>
                  <Td color="white" fontSize={{ base: 'xs', md: 'sm' }}>{formatCurrency(inkomsten)}</Td>
                  <Td>
                    <Badge colorScheme={winst >= 0 ? 'green' : 'red'} fontSize={{ base: 'xs', md: 'sm' }}>
                      {formatCurrency(winst)}
                    </Badge>
                  </Td>
                  <Td position="sticky" right={0} bg="gray.800">
                    <HStack spacing={1}>
                      <IconButton
                        icon={<EditIcon />}
                        size="xs"
                        colorScheme="blue"
                        onClick={() => handleEdit(event)}
                        title="Bewerken"
                        aria-label="Bewerken"
                      />
                      <IconButton
                        icon={<CopyIcon />}
                        size="xs"
                        colorScheme="green"
                        onClick={() => handleDuplicate(event)}
                        title="Dupliceren"
                        aria-label="Dupliceren"
                      />
                      <IconButton
                        icon={<DeleteIcon />}
                        size="xs"
                        colorScheme="red"
                        onClick={() => handleDelete(event)}
                        title="Verwijderen"
                        aria-label="Verwijderen"
                      />
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
      />
    </VStack>
  );
}

export default EventList;