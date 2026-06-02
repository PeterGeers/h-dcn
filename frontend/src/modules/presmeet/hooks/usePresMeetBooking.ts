/**
 * usePresMeetBooking — State management hook for the PresMeet booking module.
 *
 * Responsibilities:
 * - Load config on mount (product type rules + event info)
 * - Load existing booking on mount
 * - Provide save/submit methods
 * - Initiate payment flow
 * - Track loading/error state
 * - Extract form data from booking items for editing
 *
 * Validates: Requirements 3.1, 3.4, 3.8, 7.7
 */

import { useState, useEffect, useCallback } from 'react';
import { presmeetService } from '../services/presmeetApi';
import {
  PresMeetConfig,
  PresMeetBooking,
  BookingFormData,
  DelegateFormData,
  GuestFormData,
  TransferFormData,
  ProductTypeConfig,
  PaymentSession,
} from '../types/presmeet';

export interface UsePresMeetBookingReturn {
  // Data
  config: PresMeetConfig | null;
  booking: PresMeetBooking | null;
  formData: BookingFormData;
  productTypes: ProductTypeConfig[];

  // State
  isLoading: boolean;
  isSaving: boolean;
  isSubmitting: boolean;
  error: string | null;
  needsOnboarding: boolean;

  // Actions
  loadBooking: () => Promise<void>;
  reloadAll: () => Promise<void>;
  saveBooking: (data: BookingFormData) => Promise<boolean>;
  submitBooking: () => Promise<boolean>;
  initiatePayment: () => Promise<PaymentSession | null>;
}

/**
 * Extract BookingFormData from existing booking cart items.
 * Maps cart items back to the form structure for editing.
 */
function extractFormDataFromBooking(booking: PresMeetBooking | null): BookingFormData {
  const empty: BookingFormData = { delegates: [], guests: [], transfers: [] };
  if (!booking || !booking.items || booking.items.length === 0) {
    return empty;
  }

  const items = booking.items;

  // Build delegates from meeting_ticket items
  const meetingTickets = items.filter((i) => i.product_type === 'meeting_ticket');
  const partyTickets = items.filter((i) => i.product_type === 'party_ticket');
  const tshirts = items.filter((i) => i.product_type === 'tshirt');
  const transfers = items.filter((i) => i.product_type === 'airport_transfer');

  const delegates: DelegateFormData[] = meetingTickets.map((ticket) => {
    const name = ticket.attributes.name || '';
    const role = ticket.attributes.role || '';

    // Check if this delegate has a party ticket
    const hasPartyTicket = partyTickets.some(
      (pt) => pt.attributes.name === name && pt.attributes.person_type === 'delegate'
    );

    // Check if this delegate has a tshirt
    const delegateTshirt = tshirts.find((t) => t.attributes.name === name);

    const delegate: DelegateFormData = {
      name,
      role,
      attend_party: hasPartyTicket,
    };

    if (delegateTshirt) {
      delegate.tshirt = {
        gender: delegateTshirt.attributes.gender || 'male',
        size: delegateTshirt.attributes.size || 'L',
      };
    }

    return delegate;
  });

  // Build guests from party_tickets with person_type "guest"
  const guestTickets = partyTickets.filter(
    (pt) => pt.attributes.person_type === 'guest'
  );
  const guests: GuestFormData[] = guestTickets.map((ticket) => {
    const name = ticket.attributes.name || '';
    const guestTshirt = tshirts.find((t) => t.attributes.name === name);

    const guest: GuestFormData = { name };

    if (guestTshirt) {
      guest.tshirt = {
        gender: guestTshirt.attributes.gender || 'male',
        size: guestTshirt.attributes.size || 'L',
      };
    }

    return guest;
  });

  // Build transfers from airport_transfer items
  const transferData: TransferFormData[] = transfers.map((t) => ({
    direction: t.attributes.direction || 'pickup',
    airport: t.attributes.airport || 'AMS',
    flight: t.attributes.flight || '',
    date: t.attributes.date || '',
    time: t.attributes.time || '',
    persons: t.attributes.persons || 1,
  }));

  return { delegates, guests, transfers: transferData };
}

export function usePresMeetBooking(): UsePresMeetBookingReturn {
  const [config, setConfig] = useState<PresMeetConfig | null>(null);
  const [booking, setBooking] = useState<PresMeetBooking | null>(null);
  const [formData, setFormData] = useState<BookingFormData>({
    delegates: [],
    guests: [],
    transfers: [],
  });
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [needsOnboarding, setNeedsOnboarding] = useState(false);

  const productTypes = config?.product_types ?? [];

  // Load config on mount
  const loadConfig = useCallback(async () => {
    try {
      const response = await presmeetService.getConfig();
      if (response.success && response.data) {
        setConfig(response.data);
      } else {
        setError(response.error || 'Failed to load configuration');
      }
    } catch (err) {
      setError('Failed to load configuration');
    }
  }, []);

  // Load existing booking
  const loadBooking = useCallback(async () => {
    try {
      const response = await presmeetService.getBooking();
      if (response.success && response.data) {
        setNeedsOnboarding(false);
        setBooking(response.data);
        setFormData(extractFormDataFromBooking(response.data));
      } else if (response.error?.includes('Missing club assignment')) {
        // User has no club_id assigned — show onboarding flow
        setNeedsOnboarding(true);
        setBooking(null);
        setFormData({ delegates: [], guests: [], transfers: [] });
      } else if (response.error?.includes('404') || response.error?.includes('not found')) {
        // No booking yet — that's fine
        setNeedsOnboarding(false);
        setBooking(null);
        setFormData({ delegates: [], guests: [], transfers: [] });
      } else {
        // Don't treat 404 as error for initial load
        setNeedsOnboarding(false);
        setBooking(null);
        setFormData({ delegates: [], guests: [], transfers: [] });
      }
    } catch (err) {
      // No booking exists yet — not an error
      setBooking(null);
      setFormData({ delegates: [], guests: [], transfers: [] });
    }
  }, []);

  // Initial load
  useEffect(() => {
    const init = async () => {
      setIsLoading(true);
      setError(null);
      await loadConfig();
      await loadBooking();
      setIsLoading(false);
    };
    init();
  }, [loadConfig, loadBooking]);

  // Reload all state (used after onboarding completes)
  const reloadAll = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setNeedsOnboarding(false);
    await loadConfig();
    await loadBooking();
    setIsLoading(false);
  }, [loadConfig, loadBooking]);

  // Save booking as draft
  const saveBooking = useCallback(async (data: BookingFormData): Promise<boolean> => {
    setIsSaving(true);
    setError(null);
    try {
      const response = await presmeetService.saveBooking(data);
      if (response.success) {
        // Reload booking to get updated server state
        await loadBooking();
        setIsSaving(false);
        return true;
      } else {
        setError(response.error || 'Failed to save booking');
        setIsSaving(false);
        return false;
      }
    } catch (err) {
      setError('Failed to save booking');
      setIsSaving(false);
      return false;
    }
  }, [loadBooking]);

  // Submit booking
  const submitBooking = useCallback(async (): Promise<boolean> => {
    setIsSubmitting(true);
    setError(null);
    try {
      const response = await presmeetService.submitBooking();
      if (response.success) {
        await loadBooking();
        setIsSubmitting(false);
        return true;
      } else {
        setError(response.error || 'Failed to submit booking');
        setIsSubmitting(false);
        return false;
      }
    } catch (err) {
      setError('Failed to submit booking');
      setIsSubmitting(false);
      return false;
    }
  }, [loadBooking]);

  // Initiate Mollie payment
  const initiatePayment = useCallback(async (): Promise<PaymentSession | null> => {
    if (!booking) {
      setError('No booking available for payment');
      return null;
    }
    try {
      const response = await presmeetService.createPayment(booking.order_id);
      if (response.success && response.data) {
        return response.data;
      } else {
        setError(response.error || 'Failed to initiate payment');
        return null;
      }
    } catch (err) {
      setError('Failed to initiate payment');
      return null;
    }
  }, [booking]);

  return {
    config,
    booking,
    formData,
    productTypes,
    isLoading,
    isSaving,
    isSubmitting,
    error,
    needsOnboarding,
    loadBooking,
    reloadAll,
    saveBooking,
    submitBooking,
    initiatePayment,
  };
}
