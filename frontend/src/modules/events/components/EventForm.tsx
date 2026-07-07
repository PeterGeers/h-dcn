import React, { useState, useEffect, useMemo } from 'react';
import {
  Modal, ModalOverlay, ModalContent, ModalHeader, ModalBody, ModalFooter, ModalCloseButton,
  VStack, Button, Alert, AlertIcon, Text, Accordion, AccordionItem, AccordionButton,
  AccordionPanel, AccordionIcon, Box, HStack,
} from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import { getAllowedRegions } from '../../../utils/regionalMapping';
import { Event } from '../../../types';
import { getAuthHeaders } from '../../../utils/authHeaders';
import { API_URLS } from '../../../config/api';
import { useErrorHandler, apiCall } from '../../../utils/errorHandler';
import { FunctionPermissionManager, getUserRoles } from '../../../utils/functionPermissions';
import { scanProducts } from '../../products/api/productApi';
import {
  EVENT_REGIOS,
  getCategoryForType,
  EventType,
} from '../../../config/eventFields/eventTypes';
import { uploadEventPoster, validatePosterFile } from '../services/eventPosterUpload';
import { PosterAnalysisResult } from '../../../services/posterAnalysisService';
import PosterAnalyzer from './PosterAnalyzer';
import LandingPageSection, { LandingPageFormData, DEFAULT_LANDING_PAGE } from './LandingPageSection';
import EventCoreSection from './EventCoreSection';
import EventRegistrationSection from './EventRegistrationSection';
import EventConfigSection from './EventConfigSection';
import EventFinancialSection from './EventFinancialSection';

// ============================================================================
// TYPES
// ============================================================================

interface EventFormData {
  // core
  name: string;
  event_type: string;
  participation: string;
  status: string;
  start_date: string;
  end_date: string;
  linked_regio: string;
  location: string;
  poster_url: string;
  slug: string;
  description: string;
  // dates (registration)
  registration_open: string;
  registration_close: string;
  payment_deadline: string;
  // config
  product_ids: string[];
  // booking
  event_password: string;
  registry_s3_path: string;
  registry_row_label: string;
  registry_claim_mode: string;
  registry_allow_logo_upload: boolean;
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
  if (value.includes('T')) return value.slice(0, 16);
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return `${value}T00:00`;
  return value;
}

const EMPTY_FORM: EventFormData = {
  name: '',
  event_type: '',
  participation: 'open',
  status: 'draft',
  start_date: '',
  end_date: '',
  linked_regio: '',
  location: '',
  poster_url: '',
  slug: '',
  description: '',
  registration_open: '',
  registration_close: '',
  payment_deadline: '',
  product_ids: [],
  event_password: '',
  registry_s3_path: '',
  registry_row_label: 'club',
  registry_claim_mode: 'first_come_first_served',
  registry_allow_logo_upload: false,
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
      return !!(formData.product_ids.length > 0 || formData.event_password || formData.registry_s3_path);
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
  const [availableProducts, setAvailableProducts] = useState<{ product_id: string; naam: string; groep?: string }[]>([]);
  const [productsLoading, setProductsLoading] = useState(false);
  const { handleError, handleSuccess } = useErrorHandler();
  const { t } = useTranslation('events');

  const userRoles = getUserRoles(user || {});
  const canEditFinancials = permissionManager?.hasFieldAccess('events', 'write', { fieldType: 'financial' }) || false;
  const hasFullEventAccess = permissionManager?.hasAccess('events', 'write') || false;

  const allowedRegions = useMemo(
    () => getAllowedRegions(userRoles, hasFullEventAccess),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [JSON.stringify(userRoles), hasFullEventAccess]
  );

  // Load available products when modal opens
  useEffect(() => {
    if (isOpen && availableProducts.length === 0) {
      setProductsLoading(true);
      scanProducts()
        .then((res: any) => {
          const products = (res.data || [])
            .filter((p: any) => p.is_parent !== false)
            .map((p: any) => ({ product_id: p.product_id, naam: p.naam || p.name || p.product_id, groep: p.groep }))
            .sort((a: any, b: any) => (a.naam || '').localeCompare(b.naam || ''));
          setAvailableProducts(products);
        })
        .catch(() => { /* silently fail — field will show IDs only */ })
        .finally(() => setProductsLoading(false));
    }
  }, [isOpen, availableProducts.length]);

  const availableRegions = useMemo(() => {
    const allRegions = [...EVENT_REGIOS];
    if (hasFullEventAccess) return allRegions;
    if (allowedRegions.length === 0) return allRegions;
    return allRegions.filter(r => r === 'regio_all' || allowedRegions.includes(r));
  }, [hasFullEventAccess, allowedRegions]);

  const defaultOpenSections = useMemo(() => {
    const sections: number[] = [];
    if (!event) {
      sections.push(0);
    } else {
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
        status: event.status || 'published',
        start_date: toDatetimeLocal(event.start_date),
        end_date: toDatetimeLocal(event.end_date),
        linked_regio: event.linked_regio || '',
        location: event.location || '',
        poster_url: event.poster_url || '',
        slug: event.slug || '',
        description: event.description || '',
        registration_open: toDatetimeLocal(event.registration_open),
        registration_close: toDatetimeLocal(event.registration_close),
        payment_deadline: toDatetimeLocal(event.payment_deadline),
        product_ids: Array.isArray(event.product_ids) ? event.product_ids : [],
        event_password: '',
        registry_s3_path: event.registry_config?.s3_path || '',
        registry_row_label: event.registry_config?.row_label || 'club',
        registry_claim_mode: event.registry_config?.claim_mode || 'first_come_first_served',
        registry_allow_logo_upload: event.registry_config?.allow_logo_upload ?? false,
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

    const validationError = validatePosterFile(file, t);
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
      e.target.value = '';
    }
  };

  const handlePosterAnalysis = async (data: PosterAnalysisResult, file: File) => {
    setFormData(prev => ({
      ...prev,
      name: data.name || prev.name,
      start_date: data.start_date ? toDatetimeLocal(data.start_date) : prev.start_date,
      end_date: data.end_date ? toDatetimeLocal(data.end_date) : prev.end_date,
      location: data.location || prev.location,
    }));

    // Also upload the poster image to S3 so poster_url gets set
    const validationError = validatePosterFile(file, t);
    if (validationError) {
      // File not suitable for upload (e.g. too large) — metadata already prefilled, skip upload
      return;
    }

    setIsUploading(true);
    try {
      const result = await uploadEventPoster(file, event?.event_id);
      setFormData(prev => ({ ...prev, poster_url: result.url }));
    } catch {
      // Upload failed — metadata is still prefilled; user can manually upload later
    } finally {
      setIsUploading(false);
    }
  };

  const handleSubmit = async () => {
    if (!formData.name || !formData.event_type || !formData.start_date || !formData.end_date || !formData.linked_regio) {
      handleError(
        { status: 400, message: 'Naam, type, start- en einddatum, en regio zijn verplicht' },
        'validatie'
      );
      return;
    }

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

      const payload: Record<string, unknown> = {
        name: formData.name,
        event_type: formData.event_type,
        event_category: getCategoryForType(formData.event_type as EventType),
        participation: formData.participation,
        status: formData.status,
        start_date: formData.start_date,
        end_date: formData.end_date,
        linked_regio: formData.linked_regio,
      };

      if (formData.registration_open) payload.registration_open = formData.registration_open;
      if (formData.registration_close) payload.registration_close = formData.registration_close;
      if (formData.location) payload.location = formData.location;
      if (formData.poster_url) payload.poster_url = formData.poster_url;
      if (formData.slug) payload.slug = formData.slug;
      if (formData.description) payload.description = formData.description;
      if (formData.payment_deadline) payload.payment_deadline = formData.payment_deadline;

      if (formData.product_ids.length > 0) {
        payload.product_ids = formData.product_ids;
      }

      if (formData.event_password) {
        payload.event_password = formData.event_password;
      }

      if (formData.registry_s3_path || formData.registry_row_label !== 'club' || formData.registry_claim_mode !== 'first_come_first_served' || formData.registry_allow_logo_upload) {
        payload.registry_config = {
          s3_path: formData.registry_s3_path,
          row_label: formData.registry_row_label || 'club',
          claim_mode: formData.registry_claim_mode || 'first_come_first_served',
          allow_logo_upload: formData.registry_allow_logo_upload,
        };
      }

      if (formData.participants) payload.participants = formData.participants;
      if (formData.cost) payload.cost = formData.cost;
      if (formData.revenue) payload.revenue = formData.revenue;
      if (formData.notes) payload.notes = formData.notes;

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
            <EventCoreSection
              formData={formData}
              availableRegions={availableRegions}
              allowedRegions={allowedRegions}
              isUploading={isUploading}
              onChange={(field, value) => handleChange(field as keyof EventFormData, value)}
              onPosterUpload={handlePosterUpload}
            />

            {/* ============ POSTER ANALYSIS (new events only) ============ */}
            {!event && (
              <PosterAnalyzer onAnalysisComplete={handlePosterAnalysis} />
            )}

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
                  <EventRegistrationSection
                    formData={formData}
                    onChange={(field, value) => handleChange(field as keyof EventFormData, value)}
                  />
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
                  <EventConfigSection
                    formData={formData}
                    availableProducts={availableProducts}
                    productsLoading={productsLoading}
                    isEditing={!!event?.event_id}
                    onChange={(field, value) => handleChange(field as keyof EventFormData, value)}
                    onProductIdsChange={(ids) => setFormData(prev => ({ ...prev, product_ids: ids }))}
                    onRegistryLogoToggle={(checked) => setFormData(prev => ({ ...prev, registry_allow_logo_upload: checked }))}
                  />
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
                    <EventFinancialSection
                      formData={formData}
                      onChange={(field, value) => handleChange(field as keyof EventFormData, value)}
                    />
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
