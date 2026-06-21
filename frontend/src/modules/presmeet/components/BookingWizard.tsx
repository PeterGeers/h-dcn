/**
 * BookingWizard — Main v3 booking wizard container.
 *
 * Orchestrates loading, state management, and child components for the
 * person-centric PresMeet booking flow. Replaces the legacy BookingForm
 * with a unified product/event architecture.
 *
 * Features:
 * - Loads event + products + order on mount
 * - Displays event info: name, location, dates, days until close
 * - ReadOnlyView when event is not open
 * - Person cards with add/remove based on max_per_club
 * - Product configurator per person (dynamically renders order_item_fields)
 * - Effective limits display: min(max_per_club, event_remaining)
 * - Total recalculation within 500ms (useMemo)
 * - Save action with optimistic locking (version conflict detection)
 * - Submit with client-side required field validation + inline errors
 * - Server validation error display per field/item
 * - Debounced auto-save (3s after last change)
 * - Form state preserved on any failure
 *
 * Validates: Requirements 11.1, 11.3, 11.4, 11.6, 11.8, 11.9, 6.4
 */

import React, { useCallback, useEffect, useMemo, useState, useRef } from 'react';
import {
  Alert,
  AlertDescription,
  AlertIcon,
  AlertTitle,
  Box,
  Button,
  Center,
  Divider,
  Flex,
  HStack,
  Spinner,
  Text,
  VStack,
  useToast,
} from '@chakra-ui/react';
import { AddIcon, CheckIcon, RepeatIcon } from '@chakra-ui/icons';
import { useTranslation } from 'react-i18next';
import { Event, Order, Product, ValidationError } from '../types/presmeet.types';
import { presmeetApi, isVersionConflict } from '../services/presmeetApi';
import {
  PersonFormState,
  PersonFormEntry,
  formStateToOrderItems,
  orderItemsToFormState,
} from '../utils/orderTransformer';
import {
  calculateTotalFromProducts,
  formatCurrency,
} from '../utils/priceCalculator';
import { useAutoSave } from '../hooks/useAutoSave';
import { useEffectiveLimits } from '../hooks/useEffectiveLimits';
import ReadOnlyView from './ReadOnlyView';
import PersonCard from './PersonCard';
import EventInfoHeader from './EventInfoHeader';
import EffectiveLimits from './EffectiveLimits';
import SubmitPanel from './SubmitPanel';
import SaveStatusIndicator from './SaveStatusIndicator';

// --- Props ---

export interface BookingWizardProps {
  /** The event ID to load the booking for */
  eventId: string;
  /** Delegate's name from Member record — pre-fills first person (Req 6.3) */
  delegateName?: string;
}

// --- Component ---

const BookingWizard: React.FC<BookingWizardProps> = ({ eventId, delegateName }) => {
  const { t } = useTranslation('eventBooking');

  // --- State ---
  const [event, setEvent] = useState<Event | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [order, setOrder] = useState<Order | null>(null);
  const [formState, setFormState] = useState<PersonFormState>({ persons: [] });
  const [version, setVersion] = useState<number>(1);

  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Submit state
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [serverErrors, setServerErrors] = useState<ValidationError[]>([]);
  /** Per-person field errors from client-side validation: personIndex → productIndex → fieldId → message */
  const [fieldErrors, setFieldErrors] = useState<
    Record<number, Record<number, Record<string, string>>>
  >({});
  /** Per-person person-level errors: personIndex → fieldId → message */
  const [personErrors, setPersonErrors] = useState<
    Record<number, Record<string, string>>
  >({});

  const toast = useToast();
  const hasLoadedRef = useRef(false);

  /** Whether the order is locked (no editing allowed for delegates) */
  const isLocked = order?.status === 'locked';

  // --- Effective limits (dual constraint: per-order + per-event) ---
  const { limits: effectiveLimits, isLoading: isLimitsLoading, refresh: refreshLimits } =
    useEffectiveLimits(eventId, formState, products);

  // --- Load event, products, and order on mount ---

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setLoadError(null);

    try {
      // Load event(s) and find the one matching our eventId
      const events = await presmeetApi.getEvent();
      const currentEvent = events.find((e) => e.event_id === eventId);

      if (!currentEvent) {
        setLoadError('Event not found.');
        setIsLoading(false);
        return;
      }
      setEvent(currentEvent);

      // Load products linked to this event
      const eventProducts = await presmeetApi.getProducts(
        eventId,
        currentEvent.product_ids
      );
      setProducts(eventProducts);

      // Load or create order for this event
      const orderData = await presmeetApi.getOrder(eventId);
      setOrder(orderData);
      setVersion(orderData.version);

      // Convert order items to person-centric form state
      const initialFormState = orderItemsToFormState(orderData.items);

      // Pre-fill first person with delegate's name if no persons exist (Req 6.3)
      if (initialFormState.persons.length === 0 && delegateName) {
        initialFormState.persons.push({
          name: delegateName.trim(),
          role: '',
          products: [],
        });
      }

      setFormState(initialFormState);
    } catch (err: any) {
      const message =
        err?.message || err?.response?.data?.message || 'Failed to load booking data.';
      setLoadError(message);
    } finally {
      setIsLoading(false);
      hasLoadedRef.current = true;
    }
  }, [eventId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // --- Total calculation (recalculates on every form change, < 500ms via useMemo) ---

  const totalAmount = useMemo(() => {
    if (products.length === 0) return 0;
    const items = formStateToOrderItems(formState, products);
    return calculateTotalFromProducts(items, products);
  }, [formState, products]);

  // --- Person management ---

  /** Overall max persons = max of all product max_per_club values, minimum 1 (Req 6.1) */
  const maxPersons = useMemo(() => {
    if (products.length === 0) return 1;
    return Math.max(
      1,
      ...products.map((p) => p.purchase_rules?.max_per_club ?? 20)
    );
  }, [products]);

  const canAddPerson = formState.persons.length < maxPersons;

  const handleAddPerson = useCallback(() => {
    if (!canAddPerson) return;
    const newPerson: PersonFormEntry = {
      name: '',
      role: '',
      products: [],
    };
    setFormState((prev) => ({
      persons: [...prev.persons, newPerson],
    }));
  }, [canAddPerson]);

  const handleRemovePerson = useCallback((index: number) => {
    // Prevent removal of first person (Req 6.3)
    if (index === 0) return;
    setFormState((prev) => ({
      persons: prev.persons.filter((_, i) => i !== index),
    }));
  }, []);

  const handleUpdatePerson = useCallback(
    (index: number, updatedPerson: PersonFormEntry) => {
      setFormState((prev) => ({
        persons: prev.persons.map((p, i) => (i === index ? updatedPerson : p)),
      }));
    },
    []
  );

  // --- Save logic ---

  const handleSave = useCallback(async (): Promise<boolean> => {
    if (!order) return false;
    setIsSaving(true);
    setSaveError(null);

    try {
      const items = formStateToOrderItems(formState, products);
      const updatedOrder = await presmeetApi.saveOrder(order.order_id, {
        items,
        version,
      });
      setOrder(updatedOrder);
      setVersion(updatedOrder.version);
      // Refresh sold counts after successful save to reflect latest state
      refreshLimits();
      return true;
    } catch (err: any) {
      if (isVersionConflict(err)) {
        setSaveError(
          `This booking was modified elsewhere (version ${err.current_version}). Please reload to see the latest changes.`
        );
      } else {
        const message =
          err?.message || 'Failed to save. Your changes are preserved locally.';
        setSaveError(message);
      }
      return false;
    } finally {
      setIsSaving(false);
    }
  }, [order, formState, products, version, refreshLimits]);

  // --- Auto-save (debounced, 3s after last change, retry after 30s on failure) ---

  const { saveStatus, lastSavedAt, notifyChange, saveNow } = useAutoSave(handleSave, {
    delay: 3000,
    enabled: !!order && event?.status === 'open',
    retryDelay: 30000,
  });

  // Notify auto-save on form state changes (skip initial load)
  const isFirstRender = useRef(true);
  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }
    if (hasLoadedRef.current) {
      notifyChange();
    }
  }, [formState, notifyChange]);

  // --- Reload after version conflict ---

  const handleReload = useCallback(async () => {
    setSaveError(null);
    await loadData();
  }, [loadData]);

  // --- Client-side validation (Requirement 11.9) ---

  /**
   * Validate all required fields in order_item_fields are populated.
   * Returns true if valid, false otherwise. Sets inline errors on fields.
   */
  const validateFormForSubmit = useCallback((): boolean => {
    const newFieldErrors: Record<number, Record<number, Record<string, string>>> = {};
    const newPersonErrors: Record<number, Record<string, string>> = {};
    let hasErrors = false;

    for (let pIdx = 0; pIdx < formState.persons.length; pIdx++) {
      const person = formState.persons[pIdx];

      // Validate person-level required fields (name is always required)
      if (!person.name || person.name.trim().length === 0) {
        if (!newPersonErrors[pIdx]) newPersonErrors[pIdx] = {};
        newPersonErrors[pIdx].name = 'Name is required';
        hasErrors = true;
      }

      // Validate product fields against their definitions
      for (let prodIdx = 0; prodIdx < person.products.length; prodIdx++) {
        const personProduct = person.products[prodIdx];
        const productDef = products.find(
          (p) => p.product_id === personProduct.product_id
        );
        if (!productDef) continue;

        for (const field of productDef.order_item_fields) {
          if (!field.required) continue;

          // Skip name and role — they're handled at person level
          if (field.id === 'name' || field.id === 'role') continue;

          const value = personProduct.fields[field.id];
          const isEmpty =
            value === undefined ||
            value === null ||
            (typeof value === 'string' && value.trim().length === 0);

          if (isEmpty) {
            if (!newFieldErrors[pIdx]) newFieldErrors[pIdx] = {};
            if (!newFieldErrors[pIdx][prodIdx]) newFieldErrors[pIdx][prodIdx] = {};
            newFieldErrors[pIdx][prodIdx][field.id] = `${field.label} is required`;
            hasErrors = true;
          }
        }
      }
    }

    setFieldErrors(newFieldErrors);
    setPersonErrors(newPersonErrors);
    return !hasErrors;
  }, [formState, products]);

  /** Whether there are any active validation errors */
  const hasValidationErrors = useMemo(() => {
    return (
      Object.keys(fieldErrors).length > 0 ||
      Object.keys(personErrors).length > 0
    );
  }, [fieldErrors, personErrors]);

  /**
   * Map a flat item_index (from the backend error response) back to
   * the person/product indices in our form state.
   */
  const mapItemIndexToPersonProduct = useCallback(
    (itemIndex: number): { personIdx: number; productIdx: number } | null => {
      let currentIndex = 0;
      for (let pIdx = 0; pIdx < formState.persons.length; pIdx++) {
        const person = formState.persons[pIdx];
        for (let prodIdx = 0; prodIdx < person.products.length; prodIdx++) {
          if (currentIndex === itemIndex) {
            return { personIdx: pIdx, productIdx: prodIdx };
          }
          currentIndex++;
        }
      }
      return null;
    },
    [formState]
  );

  // --- Submit logic (Requirement 11.9) ---

  const handleSubmit = useCallback(async () => {
    if (!order) return;

    // Clear previous errors
    setSubmitError(null);
    setServerErrors([]);

    // Client-side validation first
    const isValid = validateFormForSubmit();
    if (!isValid) {
      setSubmitError('Please fill in all required fields before submitting.');
      return;
    }

    setIsSubmitting(true);

    try {
      // Save first to ensure latest state is persisted
      const items = formStateToOrderItems(formState, products);
      const savedOrder = await presmeetApi.saveOrder(order.order_id, {
        items,
        version,
      });
      setVersion(savedOrder.version);

      // Then submit
      const submittedOrder = await presmeetApi.submitOrder(order.order_id);
      setOrder(submittedOrder);
      setVersion(submittedOrder.version);

      toast({
        title: 'Booking submitted',
        description: 'Your booking has been submitted successfully.',
        status: 'success',
        duration: 5000,
        isClosable: true,
      });
    } catch (err: any) {
      // Handle version conflict
      if (isVersionConflict(err)) {
        setSaveError(
          `This booking was modified elsewhere (version ${err.current_version}). Please reload to see the latest changes.`
        );
        return;
      }

      // Handle server validation errors (400 with errors array)
      if (err?.response?.status === 400 && err?.response?.data?.errors) {
        const errors: ValidationError[] = err.response.data.errors;
        setServerErrors(errors);
        setSubmitError('Submission failed — the server found validation errors.');

        // Map server errors to inline field errors
        const newFieldErrors: Record<number, Record<number, Record<string, string>>> = {};
        for (const serverErr of errors) {
          // Map item_index back to person/product index
          const mapping = mapItemIndexToPersonProduct(serverErr.item_index);
          if (mapping) {
            const { personIdx, productIdx } = mapping;
            if (!newFieldErrors[personIdx]) newFieldErrors[personIdx] = {};
            if (!newFieldErrors[personIdx][productIdx])
              newFieldErrors[personIdx][productIdx] = {};
            newFieldErrors[personIdx][productIdx][serverErr.field] = serverErr.message;
          }
        }
        setFieldErrors(newFieldErrors);
        return;
      }

      // Generic error (preserve form state — no data loss)
      const message =
        err?.response?.data?.message ||
        err?.message ||
        'Submission failed. Your data is preserved — please try again.';
      setSubmitError(message);
    } finally {
      setIsSubmitting(false);
    }
  }, [order, formState, products, version, validateFormForSubmit, toast, mapItemIndexToPersonProduct]);

  // Clear validation errors when user edits form
  const handleUpdatePersonWithClear = useCallback(
    (index: number, updatedPerson: PersonFormEntry) => {
      handleUpdatePerson(index, updatedPerson);
      // Clear errors for this person on edit
      setFieldErrors((prev) => {
        const next = { ...prev };
        delete next[index];
        return next;
      });
      setPersonErrors((prev) => {
        const next = { ...prev };
        delete next[index];
        return next;
      });
    },
    [handleUpdatePerson]
  );

  // --- Render ---

  // Loading state
  if (isLoading) {
    return (
      <Center py={12}>
        <VStack spacing={4}>
          <Spinner size="xl" color="orange.500" />
          <Text color="gray.600">{t('booking.loading')}</Text>
        </VStack>
      </Center>
    );
  }

  // Load error
  if (loadError) {
    return (
      <Alert status="error" borderRadius="md">
        <AlertIcon />
        <Box>
          <AlertTitle>{t('booking.load_failed_title')}</AlertTitle>
          <AlertDescription>{loadError}</AlertDescription>
        </Box>
        <Button
          ml="auto"
          size="sm"
          leftIcon={<RepeatIcon />}
          onClick={loadData}
        >
          {t('booking.retry')}
        </Button>
      </Alert>
    );
  }

  // No event / order fallback
  if (!event || !order) {
    return (
      <Alert status="warning" borderRadius="md">
        <AlertIcon />
        <AlertDescription>{t('booking.no_event_or_order')}</AlertDescription>
      </Alert>
    );
  }

  // Event is not open → read-only view
  if (event.status !== 'open') {
    return (
      <VStack spacing={6} align="stretch">
        <EventInfoHeader event={event} />
        <ReadOnlyView order={order} event={event} products={products} />
      </VStack>
    );
  }

  // --- Active booking view ---

  return (
    <VStack spacing={6} align="stretch">
      {/* Event info panel */}
      <EventInfoHeader event={event} />

      {/* Effective limits */}
      {products.length > 0 && (
        <EffectiveLimits
          limits={effectiveLimits}
          isLoading={isLimitsLoading}
        />
      )}

      {/* Save error alert */}
      {saveError && (
        <Alert status="error" borderRadius="md">
          <AlertIcon />
          <Box flex={1}>
            <AlertDescription>{saveError}</AlertDescription>
          </Box>
          {saveError.includes('modified elsewhere') && (
            <Button size="sm" leftIcon={<RepeatIcon />} onClick={handleReload}>
              Reload
            </Button>
          )}
        </Alert>
      )}

      {/* Locked order warning */}
      {isLocked && (
        <Alert status="warning" borderRadius="md">
          <AlertIcon />
          <AlertDescription>
            {t('booking.locked_message')}
          </AlertDescription>
        </Alert>
      )}

      {/* Person cards */}
      <VStack spacing={4} align="stretch">
        {formState.persons.map((person, idx) => (
          <PersonCard
            key={idx}
            person={person}
            personIndex={idx}
            products={products}
            onUpdate={handleUpdatePersonWithClear}
            onRemove={handleRemovePerson}
            isDisabled={isSaving || isSubmitting || isLocked}
            fieldErrors={fieldErrors[idx]}
            personErrors={personErrors[idx]}
            effectiveLimits={effectiveLimits}
          />
        ))}
      </VStack>

      {/* Add person button */}
      {canAddPerson && (
        <Button
          leftIcon={<AddIcon />}
          variant="outline"
          colorScheme="blue"
          size="sm"
          onClick={handleAddPerson}
          isDisabled={isSaving || isLocked}
        >
          {formState.persons.length === 0 ? t('booking.add_first_person') : t('booking.add_person')}
        </Button>
      )}

      {formState.persons.length === 0 && (
        <Text color="gray.500" fontSize="sm" textAlign="center">
          {t('booking.no_persons_yet')}
        </Text>
      )}

      <Divider />

      {/* Total display */}
      <Flex justify="space-between" align="center" p={4} bg="gray.50" borderRadius="md">
        <Text fontWeight="bold" fontSize="lg">
          {t('booking.estimated_total')}
        </Text>
        <Text fontWeight="bold" fontSize="xl" color="orange.600">
          {formatCurrency(totalAmount)}
        </Text>
      </Flex>

      {/* Submit panel */}
      {!isLocked && (
        <SubmitPanel
          orderStatus={order.status}
          isSubmitting={isSubmitting}
          hasErrors={hasValidationErrors}
          submitError={submitError}
          serverErrors={serverErrors}
          onSubmit={handleSubmit}
          isDisabled={isSaving || isLocked}
        />
      )}

      {/* Save status indicator */}
      <HStack justify="space-between" fontSize="xs" color="gray.500">
        <SaveStatusIndicator status={saveStatus} lastSavedAt={lastSavedAt} />
        <Button
          size="xs"
          variant="ghost"
          leftIcon={<CheckIcon />}
          onClick={saveNow}
          isLoading={isSaving}
          isDisabled={isSaving}
        >
          {t('booking.save_now')}
        </Button>
      </HStack>
    </VStack>
  );
};

export default BookingWizard;
