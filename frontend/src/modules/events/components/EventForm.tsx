import React, { useState, useEffect, useMemo } from 'react';
import {
  Modal, ModalOverlay, ModalContent, ModalHeader, ModalBody, ModalFooter, ModalCloseButton,
  VStack, Button, FormControl, FormLabel, Input, Textarea, SimpleGrid, Select,
  Alert, AlertIcon, Text, Accordion, AccordionItem, AccordionButton, AccordionPanel,
  AccordionIcon, Box, HStack
} from '@chakra-ui/react';
import { getAllowedRegions } from '../../../utils/regionalMapping';
import { Event } from '../../../types';
import { getAuthHeaders } from '../../../utils/authHeaders';
import { API_URLS } from '../../../config/api';
import { useErrorHandler, apiCall } from '../../../utils/errorHandler';
import { FunctionPermissionManager, getUserRoles } from '../../../utils/functionPermissions';
import {
  EVENT_TYPES_BY_CATEGORY,
  EVENT_TYPE_LABELS,
  EVENT_CATEGORY_LABELS,
  PARTICIPATION_MODE_LABELS,
  EVENT_REGIOS,
  getCategoryForType,
  EventType,
  EventCategory,
} from '../../../config/eventFields/eventTypes';
import { uploadEventPoster, validatePosterFile } from '../services/eventPosterUpload';
import LandingPageSection, { LandingPageFormData, DEFAULT_LANDING_PAGE } from './LandingPageSection';

// ============================================================================
// TYPES
// ============================================================================

interface EventFormData {
  // core
  name: string;
  event_type: string;
  participation: string;
  start_date: string;
  end_date: string;
  linked_regio: string;
  location: string;
  poster_url: string;
  slug: string;
  // dates (registration)
  registration_open: string;
  registration_close: string;
  payment_deadline: string;
  // config
  product_ids: string;
  // financial
  participants: string;
  cost: string;
  revenue: string;
  notes: string;
  // landing page
  landing_page: LandingPageFormData;
}

interface EventFormProps {
  isOpen: boolean;
  onClose: () => void;
  event?: Event;
  onSave: () => void;
  user?: any;
  permissionManager?: FunctionPermissionManager | null;
}

// ============================================================================
// HELPERS
// ============================================================================

/** Normalize a date/datetime string for datetime-local input (requires yyyy-MM-ddTHH:mm) */
function toDatetimeLocal(value: string | undefined): string {
  if (!value) return '';
  // Already in datetime-local format
  if (value.includes('T')) return value.slice(0, 16);
  // Date-only: append T00:00
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return `${value}T00:00`;
  return value;
}

const EMPTY_FORM: EventFormData = {
  name: '',
  event_type: '',
  participation: 'open',
  start_date: '',
  end_date: '',
  linked_regio: '',
  location: '',
  poster_url: '',
  slug: '',
  registration_open: '',
  registration_close: '',
  payment_deadline: '',
  product_ids: '',
  participants: '',
  cost: '',
  revenue: '',
  notes: '',
  landing_page: { ...DEFAULT_LANDING_PAGE },
};

/** Check if a collapsible section has data (to auto-open it) */
function sectionHasData(formData: EventFormData, section: 'registration' | 'config' | 'financial' | 'landing_page'): boolean {
  switch (section) {
    case 'registration':
      return !!(formData.registration_open || formData.registration_close || formData.payment_deadline);
    case 'config':
      return !!(formData.product_ids);
    case 'financial':
      return !!(formData.participants || formData.cost || formData.revenue || formData.notes);
    case 'landing_page':
      return formData.landing_page.enabled;
  }
}

// ============================================================================
// COMPONENT
// ============================================================================

function EventForm({ isOpen, onClose, event, onSave, user, permissionManager }: EventFormProps) {
  const [formData, setFormData] = useState<EventFormData>({ ...EMPTY_FORM });
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const { handleError, handleSuccess } = useErrorHandler();

  const userRoles = getUserRoles(user || {});
  const canEditFinancials = permissionManager?.hasFieldAccess('events', 'write', { fieldType: 'financial' }) || false;
  const hasFullEventAccess = permissionManager?.hasAccess('events', 'write') || false;

  // Get user's allowed regions - memoized
  const allowedRegions = useMemo(
    () => getAllowedRegions(userRoles, hasFullEventAccess),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [JSON.stringify(userRoles), hasFullEventAccess]
  );

  // Available regions for the dropdown
  const availableRegions = useMemo(() => {
    const allRegions = [...EVENT_REGIOS];
    if (hasFullEventAccess) return allRegions;
    if (allowedRegions.length === 0) return allRegions;
    return allRegions.filter(r => r === 'regio_all' || allowedRegions.includes(r));
  }, [hasFullEventAccess, allowedRegions]);

  // Determine which accordion sections should be open by default
  const defaultOpenSections = useMemo(() => {
    const sections: number[] = [];
    if (!event) {
      // New event: registration section open by default
      sections.push(0);
    } else {
      // Editing: open sections that have data
      if (sectionHasData(formData, 'registration')) sections.push(0);
      if (sectionHasData(formData, 'config')) sections.push(1);
      if (canEditFinancials && sectionHasData(formData, 'financial')) sections.push(2);
      if (sectionHasData(formData, 'landing_page')) sections.push(canEditFinancials ? 3 : 2);
    }
    return sections;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [event?.event_id]);

  // Populate form from existing event
  useEffect(() => {
    if (event) {
      setFormData({
        name: event.name || '',
        event_type: event.event_type || '',
        participation: event.participation || 'open',
        start_date: event.start_date || '',
        end_date: event.end_date || '',
        linked_regio: event.linked_regio || '',
        location: event.location || '',
        poster_url: event.poster_url || '',
        slug: event.slug || '',
        registration_open: toDatetimeLocal(event.registration_open),
        registration_close: toDatetimeLocal(event.registration_close),
        payment_deadline: toDatetimeLocal(event.payment_deadline),
        product_ids: Array.isArray(event.product_ids) ? event.product_ids.join(', ') : '',
        participants: event.participants != null ? String(event.participants) : '',
        cost: event.cost != null ? String(event.cost) : '',
        revenue: event.revenue != null ? String(event.revenue) : '',
        notes: event.notes || '',
        landing_page: event.landing_page
          ? {
              enabled: event.landing_page.enabled ?? false,
              slug: event.landing_page.slug ?? '',
              hero_image_url: event.landing_page.hero_image_url ?? '',
              tagline: event.landing_page.tagline ?? '',
              registration_label: event.landing_page.registration_label ?? 'Register Now',
              logos: event.landing_page.logos ?? [],
              sections: event.landing_page.sections ?? [],
            }
          : { ...DEFAULT_LANDING_PAGE },
      });
    } else {
      // New event: set default region
      const defaultRegion = allowedRegions.length === 1 ? allowedRegions[0] : '';
      setFormData({ ...EMPTY_FORM, linked_regio: defaultRegion });
    }
  }, [event, allowedRegions]);

  const handleChange = (field: keyof EventFormData, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handlePosterUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const validationError = validatePosterFile(file);
    if (validationError) {
      handleError({ status: 400, message: validationError }, 'poster upload');
      return;
    }

    setIsUploading(true);
    try {
      const result = await uploadEventPoster(file, event?.event_id);
      setFormData(prev => ({ ...prev, poster_url: result.url }));
      handleSuccess('Poster succesvol geüpload');
    } catch (error: unknown) {
      handleError(error as any, 'poster upload');
    } finally {
      setIsUploading(false);
      // Reset file input
      e.target.value = '';
    }
  };

  const handleSubmit = async () => {
    // Validate required core fields
    if (!formData.name || !formData.event_type || !formData.start_date || !formData.end_date || !formData.linked_regio) {
      handleError(
        { status: 400, message: 'Naam, type, start- en einddatum, en regio zijn verplicht' },
        'validatie'
      );
      return;
    }

    // Validate regional permissions
    if (allowedRegions.length > 0 && formData.linked_regio !== 'regio_all' && !allowedRegions.includes(formData.linked_regio)) {
      handleError(
        { status: 403, message: 'Je hebt geen rechten om evenementen in deze regio aan te maken' },
        'validatie'
      );
      return;
    }

    setIsLoading(true);
    try {
      const url = event?.event_id
        ? API_URLS.event(event.event_id)
        : API_URLS.events();

      const method = event?.event_id ? 'PUT' : 'POST';

      // Build payload with registry field names
      const payload: Record<string, unknown> = {
        name: formData.name,
        event_type: formData.event_type,
        event_category: getCategoryForType(formData.event_type as EventType),
        participation: formData.participation,
        start_date: formData.start_date,
        end_date: formData.end_date,
        linked_regio: formData.linked_regio,
      };

      // Optional registration dates (only send if filled)
      if (formData.registration_open) payload.registration_open = formData.registration_open;
      if (formData.registration_close) payload.registration_close = formData.registration_close;

      // Optional core fields
      if (formData.location) payload.location = formData.location;
      if (formData.poster_url) payload.poster_url = formData.poster_url;
      if (formData.slug) payload.slug = formData.slug;
      if (formData.payment_deadline) payload.payment_deadline = formData.payment_deadline;

      // Config fields
      if (formData.product_ids) {
        payload.product_ids = formData.product_ids.split(',').map(s => s.trim()).filter(Boolean);
      }

      // Financial fields (send as strings - backend handles Decimal coercion)
      if (formData.participants) payload.participants = formData.participants;
      if (formData.cost) payload.cost = formData.cost;
      if (formData.revenue) payload.revenue = formData.revenue;
      if (formData.notes) payload.notes = formData.notes;

      // Landing page
      payload.landing_page = formData.landing_page;

      const headers = await getAuthHeaders();
      await apiCall<void>(
        fetch(url, { method, headers, body: JSON.stringify(payload) }),
        event?.event_id ? 'bijwerken evenement' : 'aanmaken evenement'
      );

      onSave();
      onClose();
      handleSuccess(
        event?.event_id ? 'Evenement succesvol bijgewerkt' : 'Evenement succesvol aangemaakt'
      );
    } catch (error: unknown) {
      handleError(error as any, 'opslaan evenement');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="xl" scrollBehavior="inside">
      <ModalOverlay />
      <ModalContent bg="gray.800" color="white" border="1px" borderColor="orange.400">
        <ModalHeader color="orange.400">
          {event?.event_id ? 'Evenement Bewerken' : 'Nieuw Evenement'}
        </ModalHeader>
        <ModalCloseButton />
        <ModalBody>
          {allowedRegions.length > 0 && (
            <Alert status="info" mb={4} bg="gray.700" borderRadius="md">
              <AlertIcon />
              <Text fontSize="sm">
                Je kunt evenementen beheren voor: {allowedRegions.join(', ')}
              </Text>
            </Alert>
          )}
          <VStack spacing={4}>
            {/* ============ CORE SECTION (always visible) ============ */}
            <SimpleGrid columns={2} spacing={4} w="full">
              <FormControl isRequired>
                <FormLabel color="orange.300">Eventnaam</FormLabel>
                <Input
                  value={formData.name}
                  onChange={(e) => handleChange('name', e.target.value)}
                  placeholder="Naam van het evenement"
                  bg="gray.700"
                  borderColor="orange.400"
                />
              </FormControl>

              <FormControl isRequired>
                <FormLabel color="orange.300">Type</FormLabel>
                <Select
                  value={formData.event_type}
                  onChange={(e) => handleChange('event_type', e.target.value)}
                  bg="gray.700"
                  borderColor="orange.400"
                  placeholder="Selecteer type..."
                >
                  {(Object.entries(EVENT_TYPES_BY_CATEGORY) as [EventCategory, readonly string[]][]).map(
                    ([category, types]) => (
                      <optgroup key={category} label={EVENT_CATEGORY_LABELS[category]}>
                        {types.map((type) => (
                          <option key={type} value={type} style={{ backgroundColor: '#2D3748', color: 'white' }}>
                            {EVENT_TYPE_LABELS[type as EventType]}
                          </option>
                        ))}
                      </optgroup>
                    )
                  )}
                </Select>
              </FormControl>

              <FormControl isRequired>
                <FormLabel color="orange.300">Deelname</FormLabel>
                <Select
                  value={formData.participation}
                  onChange={(e) => handleChange('participation', e.target.value)}
                  bg="gray.700"
                  borderColor="orange.400"
                >
                  {Object.entries(PARTICIPATION_MODE_LABELS).map(([value, label]) => (
                    <option key={value} value={value} style={{ backgroundColor: '#2D3748', color: 'white' }}>
                      {label}
                    </option>
                  ))}
                </Select>
              </FormControl>

              <FormControl isRequired>
                <FormLabel color="orange.300">Regio</FormLabel>
                <Select
                  value={formData.linked_regio}
                  onChange={(e) => handleChange('linked_regio', e.target.value)}
                  bg="gray.700"
                  borderColor="orange.400"
                  placeholder="Selecteer regio..."
                  isDisabled={allowedRegions.length === 1}
                >
                  {availableRegions.map((region) => (
                    <option key={region} value={region} style={{ backgroundColor: '#2D3748', color: 'white' }}>
                      {region === 'regio_all' ? 'Alle regio\'s (landelijk)' : region}
                    </option>
                  ))}
                </Select>
              </FormControl>

              <FormControl isRequired>
                <FormLabel color="orange.300">Startdatum</FormLabel>
                <Input
                  type="date"
                  value={formData.start_date}
                  onChange={(e) => handleChange('start_date', e.target.value)}
                  bg="gray.700"
                  borderColor="orange.400"
                />
              </FormControl>

              <FormControl isRequired>
                <FormLabel color="orange.300">Einddatum</FormLabel>
                <Input
                  type="date"
                  value={formData.end_date}
                  onChange={(e) => handleChange('end_date', e.target.value)}
                  bg="gray.700"
                  borderColor="orange.400"
                />
              </FormControl>

              <FormControl>
                <FormLabel color="orange.300">Locatie</FormLabel>
                <Input
                  value={formData.location}
                  onChange={(e) => handleChange('location', e.target.value)}
                  placeholder="Bijv. Clubhuis H-DCN, Amsterdam"
                  bg="gray.700"
                  borderColor="orange.400"
                />
              </FormControl>

              <FormControl>
                <FormLabel color="orange.300">Poster / Afbeelding</FormLabel>
                <HStack>
                  <Input
                    value={formData.poster_url}
                    onChange={(e) => handleChange('poster_url', e.target.value)}
                    placeholder="URL of upload een bestand"
                    bg="gray.700"
                    borderColor="orange.400"
                    flex={1}
                  />
                  <Button
                    size="sm"
                    colorScheme="orange"
                    variant="outline"
                    onClick={() => document.getElementById('poster-upload')?.click()}
                    isLoading={isUploading}
                  >
                    Upload
                  </Button>
                  <Input
                    id="poster-upload"
                    type="file"
                    accept=".pdf,.png,.jpg,.jpeg"
                    display="none"
                    onChange={handlePosterUpload}
                  />
                </HStack>
                {formData.poster_url && (
                  <Text fontSize="xs" color="gray.400" mt={1} isTruncated>
                    {formData.poster_url}
                  </Text>
                )}
              </FormControl>
            </SimpleGrid>

            {/* ============ COLLAPSIBLE SECTIONS ============ */}
            <Accordion allowMultiple defaultIndex={defaultOpenSections} w="full">
              {/* --- Registration dates --- */}
              <AccordionItem border="1px" borderColor="gray.600" borderRadius="md" mb={2}>
                <AccordionButton _hover={{ bg: 'gray.700' }}>
                  <HStack flex="1" textAlign="left">
                    <Text fontWeight="bold" color="orange.300">Registratie & Deadlines</Text>
                  </HStack>
                  <AccordionIcon color="orange.300" />
                </AccordionButton>
                <AccordionPanel pb={4}>
                  <SimpleGrid columns={2} spacing={4}>
                    <FormControl>
                      <FormLabel color="orange.300">Registratie open</FormLabel>
                      <Input
                        type="datetime-local"
                        value={formData.registration_open}
                        onChange={(e) => handleChange('registration_open', e.target.value)}
                        bg="gray.700"
                        borderColor="orange.400"
                      />
                    </FormControl>

                    <FormControl>
                      <FormLabel color="orange.300">Registratie sluit</FormLabel>
                      <Input
                        type="datetime-local"
                        value={formData.registration_close}
                        onChange={(e) => handleChange('registration_close', e.target.value)}
                        bg="gray.700"
                        borderColor="orange.400"
                      />
                    </FormControl>

                    <FormControl>
                      <FormLabel color="orange.300">Betaaldeadline</FormLabel>
                      <Input
                        type="datetime-local"
                        value={formData.payment_deadline}
                        onChange={(e) => handleChange('payment_deadline', e.target.value)}
                        bg="gray.700"
                        borderColor="orange.400"
                      />
                    </FormControl>

                    <FormControl>
                      <FormLabel color="orange.300">URL Slug</FormLabel>
                      <Input
                        value={formData.slug}
                        onChange={(e) => handleChange('slug', e.target.value)}
                        placeholder="bijv. presmeet-2026"
                        bg="gray.700"
                        borderColor="orange.400"
                      />
                    </FormControl>
                  </SimpleGrid>
                </AccordionPanel>
              </AccordionItem>

              {/* --- Configuration --- */}
              <AccordionItem border="1px" borderColor="gray.600" borderRadius="md" mb={2}>
                <AccordionButton _hover={{ bg: 'gray.700' }}>
                  <Box flex="1" textAlign="left">
                    <Text fontWeight="bold" color="orange.300">Configuratie</Text>
                  </Box>
                  <AccordionIcon color="orange.300" />
                </AccordionButton>
                <AccordionPanel pb={4}>
                  <FormControl>
                    <FormLabel color="orange.300">Product IDs (kommagescheiden)</FormLabel>
                    <Input
                      value={formData.product_ids}
                      onChange={(e) => handleChange('product_ids', e.target.value)}
                      placeholder="product-id-1, product-id-2"
                      bg="gray.700"
                      borderColor="orange.400"
                    />
                  </FormControl>
                </AccordionPanel>
              </AccordionItem>

              {/* --- Financial (permission-gated) --- */}
              {canEditFinancials && (
                <AccordionItem border="1px" borderColor="gray.600" borderRadius="md" mb={2}>
                  <AccordionButton _hover={{ bg: 'gray.700' }}>
                    <Box flex="1" textAlign="left">
                      <Text fontWeight="bold" color="orange.300">Financieel</Text>
                    </Box>
                    <AccordionIcon color="orange.300" />
                  </AccordionButton>
                  <AccordionPanel pb={4}>
                    <SimpleGrid columns={2} spacing={4}>
                      <FormControl>
                        <FormLabel color="orange.300">Aantal deelnemers</FormLabel>
                        <Input
                          type="number"
                          value={formData.participants}
                          onChange={(e) => handleChange('participants', e.target.value)}
                          placeholder="0"
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
                          placeholder="0.00"
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
                          placeholder="0.00"
                          bg="gray.700"
                          borderColor="orange.400"
                        />
                      </FormControl>
                    </SimpleGrid>

                    <FormControl mt={4}>
                      <FormLabel color="orange.300">Opmerkingen</FormLabel>
                      <Textarea
                        value={formData.notes}
                        onChange={(e) => handleChange('notes', e.target.value)}
                        placeholder="Interne notities over kosten, afspraken, etc."
                        bg="gray.700"
                        borderColor="orange.400"
                        rows={3}
                      />
                    </FormControl>
                  </AccordionPanel>
                </AccordionItem>
              )}

              {/* --- Landing Page --- */}
              <AccordionItem border="1px" borderColor="gray.600" borderRadius="md" mb={2}>
                <AccordionButton _hover={{ bg: 'gray.700' }}>
                  <Box flex="1" textAlign="left">
                    <Text fontWeight="bold" color="orange.300">Landing Page</Text>
                  </Box>
                  <AccordionIcon color="orange.300" />
                </AccordionButton>
                <AccordionPanel pb={4}>
                  <LandingPageSection
                    data={formData.landing_page}
                    onChange={(landingPage) => setFormData(prev => ({ ...prev, landing_page: landingPage }))}
                  />
                </AccordionPanel>
              </AccordionItem>
            </Accordion>
          </VStack>
        </ModalBody>
        <ModalFooter>
          <Button variant="ghost" mr={3} onClick={onClose} color="gray.300">
            Annuleren
          </Button>
          <Button
            colorScheme="orange"
            onClick={handleSubmit}
            isLoading={isLoading}
          >
            {event?.event_id ? 'Bijwerken' : 'Aanmaken'}
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
}

export default EventForm;
