/**
 * BookingForm — Multi-step booking form composing delegate, guest, and transfer sections.
 *
 * Features:
 * - Save Draft (persists without validation, Req 8.6)
 * - Submit Booking (validates all fields, Req 8.1, 8.2)
 * - Enforces max_per_club limits in UI (Req 4.9)
 * - Displays inline validation errors (Req 8.2)
 *
 * Validates: Requirements 4.1–4.9, 8.1, 8.2, 8.6
 */

import React, { useState, useCallback, useMemo } from 'react';
import {
  Box,
  Button,
  VStack,
  HStack,
  Heading,
  Text,
  Divider,
  useToast,
  Alert,
  AlertIcon,
} from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import {
  ProductTypeConfig,
  BookingFormData,
  DelegateFormData,
  GuestFormData,
  TransferFormData,
  ValidationError,
  PresMeetBooking,
} from '../types/presmeet';
import { presmeetService } from '../services/presmeetApi';
import {
  validateDelegate,
  validateGuest,
  validateTransfer,
} from '../utils/validation';
import DelegateSection from './DelegateSection';
import GuestSection from './GuestSection';
import TransferSection from './TransferSection';

interface BookingFormProps {
  config: ProductTypeConfig[];
  eventStartDate?: string;
  eventEndDate?: string;
  existingBooking?: PresMeetBooking | null;
  initialFormData?: BookingFormData;
  onSaved?: () => void;
  onSubmitted?: () => void;
}

/** Default max limits from Requirement 2.4 */
const DEFAULT_LIMITS = {
  meeting_ticket: 3,
  party_ticket: 13,
  tshirt: 13,
  airport_transfer: 20,
};

function getMaxPerClub(
  config: ProductTypeConfig[],
  productType: string
): number {
  const cfg = config.find((c) => c.product_type === productType);
  return cfg?.max_per_club ?? DEFAULT_LIMITS[productType as keyof typeof DEFAULT_LIMITS] ?? 10;
}

/**
 * Calculate the estimated cart total from form data.
 * meeting_ticket: €50, party_ticket: €99.50, tshirt: €25, airport_transfer: persons × €5
 */
function calculateTotal(formData: BookingFormData, config: ProductTypeConfig[]): number {
  const prices = {
    meeting_ticket: config.find((c) => c.product_type === 'meeting_ticket')?.unit_price ?? 50,
    party_ticket: config.find((c) => c.product_type === 'party_ticket')?.unit_price ?? 99.5,
    tshirt: config.find((c) => c.product_type === 'tshirt')?.unit_price ?? 25,
    airport_transfer: config.find((c) => c.product_type === 'airport_transfer')?.unit_price ?? 5,
  };

  const meetingTotal = formData.delegates.length * prices.meeting_ticket;
  const partyDelegates = formData.delegates.filter((d) => d.attend_party).length;
  const partyTotal = (partyDelegates + formData.guests.length) * prices.party_ticket;

  const tshirtCount =
    formData.delegates.filter((d) => d.tshirt).length +
    formData.guests.filter((g) => g.tshirt).length;
  const tshirtTotal = tshirtCount * prices.tshirt;

  const transferTotal = formData.transfers.reduce(
    (sum, t) => sum + (t.persons || 0) * prices.airport_transfer,
    0
  );

  return meetingTotal + partyTotal + tshirtTotal + transferTotal;
}

const BookingForm: React.FC<BookingFormProps> = ({
  config,
  eventStartDate,
  eventEndDate,
  existingBooking,
  initialFormData,
  onSaved,
  onSubmitted,
}) => {
  const { t } = useTranslation('presmeet');
  const toast = useToast();

  const [formData, setFormData] = useState<BookingFormData>(
    initialFormData ?? {
      delegates: [],
      guests: [],
      transfers: [],
    }
  );

  const [errors, setErrors] = useState<ValidationError[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isLocked = existingBooking?.status === 'locked';

  // Limits
  const maxDelegates = getMaxPerClub(config, 'meeting_ticket');
  const maxPartyTotal = getMaxPerClub(config, 'party_ticket');
  const maxTshirts = getMaxPerClub(config, 'tshirt');
  const maxTransfers = getMaxPerClub(config, 'airport_transfer');

  // Current party ticket count (delegates attending party + guests)
  const currentPartyCount = useMemo(() => {
    const delegatesAtParty = formData.delegates.filter((d) => d.attend_party).length;
    return delegatesAtParty + formData.guests.length;
  }, [formData.delegates, formData.guests]);

  // Current tshirt count
  const currentTshirtCount = useMemo(() => {
    return (
      formData.delegates.filter((d) => d.tshirt).length +
      formData.guests.filter((g) => g.tshirt).length
    );
  }, [formData.delegates, formData.guests]);

  // Max guests is limited by party_ticket max minus delegates already attending party
  const maxGuests = useMemo(() => {
    const delegatesAtParty = formData.delegates.filter((d) => d.attend_party).length;
    return Math.min(
      maxPartyTotal - delegatesAtParty,
      maxPartyTotal // absolute cap
    );
  }, [formData.delegates, maxPartyTotal]);

  // Estimated total
  const estimatedTotal = useMemo(() => calculateTotal(formData, config), [formData, config]);

  const handleDelegatesChange = useCallback((delegates: DelegateFormData[]) => {
    setFormData((prev) => ({ ...prev, delegates }));
    // Clear delegate errors when modifying
    setErrors((prev) => prev.filter((e) => !e.field.startsWith('delegates')));
  }, []);

  const handleGuestsChange = useCallback((guests: GuestFormData[]) => {
    setFormData((prev) => ({ ...prev, guests }));
    setErrors((prev) => prev.filter((e) => !e.field.startsWith('guests')));
  }, []);

  const handleTransfersChange = useCallback((transfers: TransferFormData[]) => {
    setFormData((prev) => ({ ...prev, transfers }));
    setErrors((prev) => prev.filter((e) => !e.field.startsWith('transfers')));
  }, []);

  /**
   * Validate all form data. Returns true if valid.
   */
  const validateAll = (): boolean => {
    const allErrors: ValidationError[] = [];

    // Validate delegates
    formData.delegates.forEach((delegate, i) => {
      allErrors.push(...validateDelegate(delegate, i));
    });

    // Validate guests
    formData.guests.forEach((guest, i) => {
      allErrors.push(...validateGuest(guest, i));
    });

    // Validate transfers
    formData.transfers.forEach((transfer, i) => {
      allErrors.push(...validateTransfer(transfer, i, eventStartDate, eventEndDate));
    });

    // Check min delegates (Req 8.3: at least 1 meeting_ticket)
    const minDelegates = config.find((c) => c.product_type === 'meeting_ticket')?.min_per_club ?? 1;
    if (formData.delegates.length < minDelegates) {
      allErrors.push({
        field: 'delegates',
        message: t('booking_form.min_delegates', { count: minDelegates }),
        constraint: 'min_per_club',
      });
    }

    // Check tshirt max
    if (currentTshirtCount > maxTshirts) {
      allErrors.push({
        field: 'tshirts',
        message: t('booking_form.max_tshirts', { count: maxTshirts }),
        constraint: 'max_per_club',
      });
    }

    setErrors(allErrors);
    return allErrors.length === 0;
  };

  /**
   * Save as draft — no validation required (Req 8.6).
   */
  const handleSaveDraft = async () => {
    setIsSaving(true);
    try {
      const response = await presmeetService.saveBooking(formData);
      if (response.success) {
        toast({
          title: t('booking_form.draft_saved'),
          description: t('booking_form.draft_saved_desc'),
          status: 'success',
          duration: 3000,
        });
        onSaved?.();
      } else {
        toast({
          title: t('booking_form.save_failed'),
          description: response.error || t('booking_form.save_failed_desc'),
          status: 'error',
          duration: 5000,
        });
      }
    } catch (err) {
      toast({
        title: t('booking_form.save_failed'),
        description: t('booking_form.network_error'),
        status: 'error',
        duration: 5000,
      });
    } finally {
      setIsSaving(false);
    }
  };

  /**
   * Submit booking — validates all fields first.
   */
  const handleSubmit = async () => {
    const isValid = validateAll();
    if (!isValid) {
      toast({
        title: t('booking_form.validation_errors'),
        description: t('booking_form.validation_errors_desc'),
        status: 'warning',
        duration: 4000,
      });
      return;
    }

    setIsSubmitting(true);
    try {
      // Save first, then submit
      const saveResponse = await presmeetService.saveBooking(formData);
      if (!saveResponse.success) {
        toast({
          title: t('booking_form.save_failed'),
          description: saveResponse.error || t('booking_form.save_failed_desc'),
          status: 'error',
          duration: 5000,
        });
        return;
      }

      const submitResponse = await presmeetService.submitBooking();
      if (submitResponse.success) {
        toast({
          title: t('booking_form.booking_submitted'),
          description: t('booking_form.booking_submitted_desc'),
          status: 'success',
          duration: 4000,
        });
        setErrors([]);
        onSubmitted?.();
      } else {
        toast({
          title: t('booking_form.submission_failed'),
          description: submitResponse.error || t('booking_form.submission_failed_desc'),
          status: 'error',
          duration: 5000,
        });
      }
    } catch (err) {
      toast({
        title: t('booking_form.submission_failed'),
        description: t('booking_form.network_error'),
        status: 'error',
        duration: 5000,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  // Global-level errors (not field-specific)
  const globalErrors = errors.filter(
    (e) => e.field === 'delegates' || e.field === 'tshirts'
  );

  return (
    <Box>
      <VStack spacing={6} align="stretch">
        {isLocked && (
          <Alert status="warning" borderRadius="md">
            <AlertIcon />
            {t('booking_form.booking_locked')}
          </Alert>
        )}

        {globalErrors.length > 0 && (
          <Alert status="error" borderRadius="md">
            <AlertIcon />
            <VStack align="start" spacing={1}>
              {globalErrors.map((e, i) => (
                <Text key={i}>{e.message}</Text>
              ))}
            </VStack>
          </Alert>
        )}

        {/* Delegates Section */}
        <DelegateSection
          delegates={formData.delegates}
          onChange={handleDelegatesChange}
          maxDelegates={maxDelegates}
          errors={errors}
          isDisabled={isLocked}
        />

        <Divider />

        {/* Guests Section */}
        <GuestSection
          guests={formData.guests}
          onChange={handleGuestsChange}
          maxGuests={maxGuests}
          currentPartyCount={currentPartyCount}
          maxPartyTotal={maxPartyTotal}
          errors={errors}
          isDisabled={isLocked}
        />

        <Divider />

        {/* Transfers Section */}
        <TransferSection
          transfers={formData.transfers}
          onChange={handleTransfersChange}
          maxTransfers={maxTransfers}
          eventStartDate={eventStartDate}
          eventEndDate={eventEndDate}
          errors={errors}
          isDisabled={isLocked}
        />

        <Divider />

        {/* Estimated Total */}
        <Box p={4} borderWidth={1} borderColor="gray.600" borderRadius="md">
          <HStack justify="space-between">
            <Heading size="sm">{t('booking_form.estimated_total')}</Heading>
            <Text fontSize="lg" fontWeight="bold">
              €{estimatedTotal.toFixed(2)}
            </Text>
          </HStack>
          <Text fontSize="xs" color="gray.400" mt={1}>
            {t('booking_form.summary', {
              delegates: formData.delegates.length,
              party: currentPartyCount,
              tshirts: currentTshirtCount,
              transfers: formData.transfers.length,
            })}
          </Text>
        </Box>

        {/* Action Buttons */}
        <HStack spacing={4} justify="flex-end">
          <Button
            variant="outline"
            colorScheme="orange"
            onClick={handleSaveDraft}
            isLoading={isSaving}
            isDisabled={isLocked || isSubmitting}
          >
            {t('booking_form.save_draft')}
          </Button>
          <Button
            colorScheme="orange"
            onClick={handleSubmit}
            isLoading={isSubmitting}
            isDisabled={isLocked || isSaving}
          >
            {t('booking_form.submit_booking')}
          </Button>
        </HStack>
      </VStack>
    </Box>
  );
};

export default BookingForm;
