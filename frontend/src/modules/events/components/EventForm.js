import React, { useState, useEffect } from 'react';
import {
  Modal, ModalOverlay, ModalContent, ModalHeader, ModalBody, ModalFooter, ModalCloseButton,
  VStack, Button, FormControl, FormLabel, Input, Textarea, SimpleGrid, useToast, Select
} from '@chakra-ui/react';
import { useParameters } from '../../../utils/parameterService';

function EventForm({ isOpen, onClose, event, onSave }) {
  const [formData, setFormData] = useState({
    title: '',
    event_date: '',
    end_date: '',
    location: '',
    region: '',
    participants: '',
    cost: '',
    revenue: '',
    notes: ''
  });
  const [isLoading, setIsLoading] = useState(false);
  const toast = useToast();
  const { parameters: regions, loading: regionsLoading } = useParameters('Regio');

  useEffect(() => {
    if (event) {
      setFormData({
        title: event.title || event.naam || '',
        event_date: event.event_date || event.datum_van || '',
        end_date: event.end_date || event.datum_tot || '',
        location: event.location || event.locatie || '',
        region: event.region || event.regio || '',
        participants: event.participants || event.aantal_deelnemers || '',
        cost: event.cost || event.kosten || '',
        revenue: event.revenue || event.inkomsten || '',
        notes: event.notes || event.opmerkingen || ''
      });
    } else {
      setFormData({
        title: '',
        event_date: '',
        end_date: '',
        location: '',
        region: '',
        participants: '',
        cost: '',
        revenue: '',
        notes: ''
      });
    }
  }, [event]);

  const handleChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleSubmit = async () => {
    if (!formData.title || !formData.event_date) {
      toast({
        title: 'Vereiste velden',
        description: 'Naam en startdatum zijn verplicht',
        status: 'error',
        duration: 3000,
      });
      return;
    }

    setIsLoading(true);
    try {
      const url = event && event.event_id
        ? `https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod/events/${event.event_id}`
        : 'https://i3if973sp5.execute-api.eu-west-1.amazonaws.com/prod/events';
      
      const method = event && event.event_id ? 'PUT' : 'POST';
      
      // Convert numeric values to strings for backend compatibility
      const payload = {
        ...formData,
        participants: formData.participants ? String(formData.participants) : '',
        cost: formData.cost ? String(formData.cost) : '',
        revenue: formData.revenue ? String(formData.revenue) : ''
      };
      
      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (response.ok) {
        onSave();
        onClose();
        toast({
          title: event && event.event_id ? 'Evenement bijgewerkt' : 'Evenement aangemaakt',
          status: 'success',
          duration: 3000,
        });
      }
    } catch (error) {
      toast({
        title: 'Fout bij opslaan',
        description: error.message,
        status: 'error',
        duration: 5000,
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="xl">
      <ModalOverlay />
      <ModalContent bg="gray.800" color="white" border="1px" borderColor="orange.400">
        <ModalHeader color="orange.400">
          {event && event.event_id ? 'Evenement Bewerken' : 'Nieuw Evenement'}
        </ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          <VStack spacing={4}>
            <SimpleGrid columns={2} spacing={4} w="full">
              <FormControl isRequired>
                <FormLabel color="orange.300">Naam</FormLabel>
                <Input
                  value={formData.title}
                  onChange={(e) => handleChange('title', e.target.value)}
                  bg="gray.700"
                  borderColor="orange.400"
                />
              </FormControl>
              
              <FormControl>
                <FormLabel color="orange.300">Locatie</FormLabel>
                <Input
                  value={formData.location}
                  onChange={(e) => handleChange('location', e.target.value)}
                  bg="gray.700"
                  borderColor="orange.400"
                />
              </FormControl>

              <FormControl>
                <FormLabel color="orange.300">Regio</FormLabel>
                <Select
                  value={formData.region}
                  onChange={(e) => handleChange('region', e.target.value)}
                  bg="gray.700"
                  borderColor="orange.400"
                  placeholder="Selecteer regio..."
                >
                  {regions.map((region) => (
                    <option key={region.id} value={region.value} style={{backgroundColor: '#2D3748', color: 'white'}}>
                      {region.value}
                    </option>
                  ))}
                </Select>
              </FormControl>

              <FormControl isRequired>
                <FormLabel color="orange.300">Datum van</FormLabel>
                <Input
                  type="date"
                  value={formData.event_date}
                  onChange={(e) => handleChange('event_date', e.target.value)}
                  bg="gray.700"
                  borderColor="orange.400"
                />
              </FormControl>

              <FormControl>
                <FormLabel color="orange.300">Datum tot</FormLabel>
                <Input
                  type="date"
                  value={formData.end_date}
                  onChange={(e) => handleChange('end_date', e.target.value)}
                  bg="gray.700"
                  borderColor="orange.400"
                />
              </FormControl>

              <FormControl>
                <FormLabel color="orange.300">Aantal deelnemers</FormLabel>
                <Input
                  type="number"
                  value={formData.participants}
                  onChange={(e) => handleChange('participants', e.target.value)}
                  bg="gray.700"
                  borderColor="orange.400"
                />
              </FormControl>

              <FormControl>
                <FormLabel color="orange.300">Kosten (€)</FormLabel>
                <Input
                  type="number"
                  step="0.01"
                  value={formData.cost}
                  onChange={(e) => handleChange('cost', e.target.value)}
                  bg="gray.700"
                  borderColor="orange.400"
                />
              </FormControl>

              <FormControl>
                <FormLabel color="orange.300">Inkomsten (€)</FormLabel>
                <Input
                  type="number"
                  step="0.01"
                  value={formData.revenue}
                  onChange={(e) => handleChange('revenue', e.target.value)}
                  bg="gray.700"
                  borderColor="orange.400"
                />
              </FormControl>
            </SimpleGrid>

            <FormControl>
              <FormLabel color="orange.300">Opmerkingen</FormLabel>
              <Textarea
                value={formData.notes}
                onChange={(e) => handleChange('notes', e.target.value)}
                bg="gray.700"
                borderColor="orange.400"
                rows={3}
              />
            </FormControl>
          </VStack>
        </ModalBody>
        <ModalFooter>
          <Button variant="ghost" mr={3} onClick={onClose}>
            Annuleren
          </Button>
          <Button
            colorScheme="orange"
            onClick={handleSubmit}
            isLoading={isLoading}
          >
            {event && event.event_id ? 'Bijwerken' : 'Aanmaken'}
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
}

export default EventForm;