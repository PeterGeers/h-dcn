import React, { useState, useEffect } from 'react';
import {
  Modal, ModalOverlay, ModalContent, ModalHeader, ModalBody, ModalFooter, ModalCloseButton,
  VStack, Button, FormControl, FormLabel, Input, Textarea, SimpleGrid, useToast, Select,
  Alert, AlertIcon, Text
} from '@chakra-ui/react';
import { MEMBER_FIELDS } from '../../../config/memberFields';
import { getAllowedRegions } from '../../../utils/regionalMapping';
import { Event } from '../../../types';
import { getAuthHeaders } from '../../../utils/authHeaders';
import { API_URLS } from '../../../config/api';
import { useErrorHandler, apiCall } from '../../../utils/errorHandler';
import { FunctionPermissionManager, getUserRoles } from '../../../utils/functionPermissions';

interface EventFormData {
  title: string;
  event_date: string;
  end_date: string;
  location: string;
  region: string;
  participants: string;
  cost: string;
  revenue: string;
  notes: string;
}

interface EventFormProps {
  isOpen: boolean;
  onClose: () => void;
  event?: Event;
  onSave: () => void;
  user?: any;
  permissionManager?: FunctionPermissionManager | null;
}

function EventForm({ isOpen, onClose, event, onSave, user, permissionManager }: EventFormProps) {
  const [formData, setFormData] = useState<EventFormData>({
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
  const { handleError, handleSuccess } = useErrorHandler();
  
  // Get regions from memberFields instead of parameters
  const regioField = MEMBER_FIELDS['regio'];
  const regions = regioField?.enumOptions?.map((value, index) => ({ 
    id: String(index + 1), 
    value 
  })) || [];

  const userRoles = getUserRoles(user || {});
  const canEditFinancials = permissionManager?.hasFieldAccess('events', 'write', { fieldType: 'financial' }) || false;
  const hasFullEventAccess = permissionManager?.hasAccess('events', 'write') || false;
  
  // Get user's allowed regions for regional users
  const allowedRegions = getAllowedRegions(userRoles, hasFullEventAccess);

  useEffect(() => {
    if (event) {
      setFormData({
        title: event.title || event.naam || '',
        event_date: event.event_date || event.datum_van || '',
        end_date: event.end_date || event.datum_tot || '',
        location: event.location || event.locatie || '',
        region: event.region || event.regio || '',
        participants: String(event.participants || event.aantal_deelnemers || ''),
        cost: String(event.cost || event.kosten || ''),
        revenue: String(event.revenue || event.inkomsten || ''),
        notes: event.notes || event.opmerkingen || ''
      });
    } else {
      // For new events, set default region for regional users
      const defaultRegion = allowedRegions.length === 1 ? allowedRegions[0] : '';
      setFormData({
        title: '',
        event_date: '',
        end_date: '',
        location: '',
        region: defaultRegion,
        participants: '',
        cost: '',
        revenue: '',
        notes: ''
      });
    }
  }, [event, allowedRegions]);

  const handleChange = (field: keyof EventFormData, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleSubmit = async () => {
    if (!formData.title || !formData.event_date) {
      handleError({ status: 400, message: 'Naam en startdatum zijn verplicht' }, 'validatie');
      return;
    }

    // Validate regional permissions
    if (allowedRegions.length > 0 && formData.region && !allowedRegions.includes(formData.region)) {
      handleError({ status: 403, message: 'Je hebt geen rechten om evenementen in deze regio aan te maken' }, 'validatie');
      return;
    }

    setIsLoading(true);
    try {
      const url = event && event.event_id
        ? API_URLS.event(event.event_id)
        : API_URLS.events();
      
      const method = event && event.event_id ? 'PUT' : 'POST';
      
      const payload = {
        ...formData,
        participants: formData.participants ? String(formData.participants) : '',
        cost: formData.cost ? String(formData.cost) : '',
        revenue: formData.revenue ? String(formData.revenue) : ''
      };
      
      const headers = await getAuthHeaders();
      await apiCall<void>(
        fetch(url, { method, headers, body: JSON.stringify(payload) }),
        event && event.event_id ? 'bijwerken evenement' : 'aanmaken evenement'
      );
      
      onSave();
      onClose();
      handleSuccess(
        event && event.event_id ? 'Evenement succesvol bijgewerkt' : 'Evenement succesvol aangemaakt'
      );
    } catch (error: any) {
      handleError(error, 'opslaan evenement');
    } finally {
      setIsLoading(false);
    }
  };

  // Filter regions based on user permissions
  const availableRegions = hasFullEventAccess 
    ? regions 
    : regions.filter(region => allowedRegions.length === 0 || allowedRegions.includes(region.value));

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="xl">
      <ModalOverlay />
      <ModalContent bg="gray.800" color="white" border="1px" borderColor="orange.400">
        <ModalHeader color="orange.400">
          {event && event.event_id ? 'Evenement Bewerken' : 'Nieuw Evenement'}
        </ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          {allowedRegions.length > 0 && (
            <Alert status="info" mb={4}>
              <AlertIcon />
              <Text fontSize="sm">
                Je kunt alleen evenementen beheren voor: {allowedRegions.join(', ')}
              </Text>
            </Alert>
          )}
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
                  isDisabled={allowedRegions.length === 1} // Disable if user can only access one region
                >
                  {availableRegions.map((region, index) => (
                    <option key={region.id || region.value || index} value={region.value} style={{backgroundColor: '#2D3748', color: 'white'}}>
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
                  isDisabled={!canEditFinancials}
                  title={!canEditFinancials ? 'Geen rechten om financiële gegevens te bewerken' : ''}
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
                  isDisabled={!canEditFinancials}
                  title={!canEditFinancials ? 'Geen rechten om financiële gegevens te bewerken' : ''}
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