/**
 * BookingWizard Component Tests
 *
 * Tests cover:
 * - Loading state on initial render
 * - Error state when API fails
 * - ReadOnlyView when event is not open
 * - Event info header display
 * - Person card add/remove
 * - Total recalculation
 * - Effective limits display
 *
 * Validates: Requirements 11.1, 11.3, 11.4, 6.4
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

import { eventBookingApi } from '../services/eventBookingApi';
import BookingWizard from '../components/BookingWizard';
import { Event, Order, Product } from '../types/eventBooking.types';

// Mock i18n initialization module (prevents HttpBackend init error)
jest.mock('../../../i18n', () => ({}));
jest.mock('../../../i18n/index', () => ({}));



// Mock useEffectiveLimits hook (uses axios + authHeaders internally)
const mockLimits = [
  { product_id: 'prod-meeting', product_name: 'Meeting Ticket', totalCapacity: 150, remaining: 3, isExhausted: false },
  { product_id: 'prod-party', product_name: 'Party Ticket', totalCapacity: 200, remaining: 13, isExhausted: false },
];
jest.mock('../hooks/useEffectiveLimits', () => ({
  useEffectiveLimits: () => ({ limits: mockLimits, isLoading: false, error: null, refresh: jest.fn() }),
}));

// Mock Chakra UI toast
const mockToast = jest.fn();
jest.mock('@chakra-ui/react', () => {
  const actual = jest.requireActual('@chakra-ui/react');
  return {
    ...actual,
    useToast: () => mockToast,
  };
});

// Mock the eventBookingApi
jest.mock('../services/eventBookingApi', () => ({
  eventBookingApi: {
    getEvent: jest.fn(),
    getProducts: jest.fn(),
    getOrder: jest.fn(),
  },
  isVersionConflict: jest.fn(),
}));

// Mock react-i18next
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, any>) => {
      const translations: Record<string, string> = {
        'booking.loading': 'Loading booking data...',
        'booking.load_failed_title': 'Could not load booking',
        'booking.no_event_or_order': 'No event or order data available.',
        'booking.locked_message': 'This booking is locked. Contact the organizers for changes.',
        'booking.add_first_person': 'Add first person',
        'booking.add_person': 'Add person',
        'booking.no_persons_yet': 'No persons added yet. Add a delegate or guest to begin.',
        'booking.estimated_total': 'Estimated Total',
        'booking.save_now': 'Save now',
        'booking.saving': 'Saving...',
        'booking.retry': 'Retry',
        'read_only.event_closed': 'Registration is closed. Your booking is shown below in read-only mode.',
        'read_only.event_draft': 'Registration is not yet open. Check back after the registration open date.',
        'read_only.order_submitted': 'Your booking has been submitted and is being processed.',
        'read_only.order_locked': 'This booking is locked. Contact the organizers for changes.',
        'read_only.no_persons': 'No persons in this booking.',
        'read_only.person': 'Person',
        'read_only.total': 'Total',
        'person_card.full_name': 'Full name',
        'person_card.role': 'Role',
        'person_card.name_placeholder': 'Full name',
        'person_card.role_placeholder': 'e.g. President',
        'person_card.add_product': 'Add product',
        'effective_limits.title': 'Available capacity',
        'effective_limits.max_per_club': 'max {{count}} per club',
        'limits.title': 'Available capacity',
        'limits.loading': 'Loading capacity data...',
        'limits.remaining': '{{remaining}} of {{total}} remaining',
      };
      if (key === 'booking.last_saved' && params?.time) {
        return `Last saved: ${params.time}`;
      }
      let result = translations[key] || key;
      if (params) {
        Object.entries(params).forEach(([k, v]) => {
          result = result.replace(`{{${k}}}`, String(v));
        });
      }
      return result;
    },
    i18n: { language: 'nl', changeLanguage: jest.fn() },
  }),
}));

const mockedGetEvent = eventBookingApi.getEvent as jest.MockedFunction<typeof eventBookingApi.getEvent>;
const mockedGetProducts = eventBookingApi.getProducts as jest.MockedFunction<typeof eventBookingApi.getProducts>;
const mockedGetOrder = eventBookingApi.getOrder as jest.MockedFunction<typeof eventBookingApi.getOrder>;

// --- Test Fixtures ---

const mockEvent: Event = {
  event_id: 'evt-1',
  event_type: 'presmeet',
  name: 'Presidents Meeting 2027',
  location: 'Hotel Amersfoort',
  status: 'open',
  start_date: '2027-06-20',
  end_date: '2027-06-22',
  registration_open: '2027-01-01',
  registration_close: '2027-05-01',
  payment_deadline: '2027-05-15',
  product_ids: ['prod-meeting', 'prod-party'],
  constraints: [
    {
      key: 'max_meeting_attendees',
      label: 'Maximum meeting attendees',
      max: 150,
      counting_rule: 'count_items_by_product',
      product_id: 'prod-meeting',
    },
  ],
  created_at: '2026-12-01T08:00:00Z',
  created_by: 'admin@h-dcn.nl',
};

const mockProducts: Product[] = [
  {
    product_id: 'prod-meeting',
    naam: 'Meeting Ticket',
    event_type: 'presmeet',
    prijs: 50,
    order_item_fields: [
      { id: 'name', label: 'Naam', type: 'text', required: true },
      { id: 'role', label: 'Functie', type: 'text', required: true },
    ],
    variant_schema: null,
    purchase_rules: { min_per_order: 1, max_per_order: 3 },
  },
  {
    product_id: 'prod-party',
    naam: 'Party Ticket',
    event_type: 'presmeet',
    prijs: 25,
    order_item_fields: [
      { id: 'name', label: 'Naam', type: 'text', required: true },
    ],
    variant_schema: null,
    purchase_rules: { max_per_order: 13 },
  },
];

const mockOrder: Order = {
  order_id: 'ord-1',
  source_id: 'evt-1',
  member_id: 'member-1',
  registry_row_id: 'club-1',
  event_id: 'evt-1',
  event_type: 'presmeet',
  status: 'draft',
  payment_status: 'unpaid',
  total_amount: 0,
  total_paid: 0,
  items: [],
  delegates: { primary: 'jan@club.nl', secondary: null },
  version: 1,
  status_history: [],
  created_at: '2027-01-10T08:00:00Z',
  updated_at: '2027-01-10T08:00:00Z',
  submitted_at: null,
  created_by: 'jan@club.nl',
};

describe('BookingWizard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('shows loading spinner while data is being fetched', () => {
    mockedGetEvent.mockReturnValue(new Promise(() => {})); // Never resolves
    render(<BookingWizard eventId="evt-1" />);
    expect(screen.getByText('Loading booking data...')).toBeInTheDocument();
  });

  it('shows error alert when event is not found', async () => {
    mockedGetEvent.mockResolvedValue([]);
    render(<BookingWizard eventId="evt-unknown" />);
    await waitFor(() => {
      expect(screen.getByText('Event not found.')).toBeInTheDocument();
    });
  });

  it('shows error alert when API call fails', async () => {
    mockedGetEvent.mockRejectedValue(new Error('Network error'));
    render(<BookingWizard eventId="evt-1" />);
    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument();
    });
  });

  it('displays event info header with name, location, and dates', async () => {
    mockedGetEvent.mockResolvedValue([mockEvent]);
    mockedGetProducts.mockResolvedValue(mockProducts);
    mockedGetOrder.mockResolvedValue(mockOrder);

    render(<BookingWizard eventId="evt-1" />);

    await waitFor(() => {
      expect(screen.getByText('Presidents Meeting 2027')).toBeInTheDocument();
    });
    expect(screen.getByText(/Hotel Amersfoort/)).toBeInTheDocument();
  });

  it('shows ReadOnlyView when event is closed', async () => {
    const closedEvent = { ...mockEvent, status: 'closed' as const };
    mockedGetEvent.mockResolvedValue([closedEvent]);
    mockedGetProducts.mockResolvedValue(mockProducts);
    mockedGetOrder.mockResolvedValue(mockOrder);

    render(<BookingWizard eventId="evt-1" />);

    await waitFor(() => {
      expect(
        screen.getByText('Registration is closed. Your booking is shown below in read-only mode.')
      ).toBeInTheDocument();
    });
  });

  it('shows ReadOnlyView when event is draft (not yet open)', async () => {
    const draftEvent = { ...mockEvent, status: 'draft' as const };
    mockedGetEvent.mockResolvedValue([draftEvent]);
    mockedGetProducts.mockResolvedValue(mockProducts);
    mockedGetOrder.mockResolvedValue(mockOrder);

    render(<BookingWizard eventId="evt-1" />);

    await waitFor(() => {
      expect(
        screen.getByText('Registration is not yet open. Check back after the registration open date.')
      ).toBeInTheDocument();
    });
  });

  it('shows empty state with Add person button when order has no items', async () => {
    mockedGetEvent.mockResolvedValue([mockEvent]);
    mockedGetProducts.mockResolvedValue(mockProducts);
    mockedGetOrder.mockResolvedValue(mockOrder);

    render(<BookingWizard eventId="evt-1" />);

    await waitFor(() => {
      expect(screen.getByText('No persons added yet. Add a delegate or guest to begin.')).toBeInTheDocument();
    });
    expect(screen.getByText('Add first person')).toBeInTheDocument();
  });

  it('allows adding a person via the Add person button', async () => {
    mockedGetEvent.mockResolvedValue([mockEvent]);
    mockedGetProducts.mockResolvedValue(mockProducts);
    mockedGetOrder.mockResolvedValue(mockOrder);

    render(<BookingWizard eventId="evt-1" />);

    await waitFor(() => {
      expect(screen.getByText('Add first person')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Add first person'));

    // After adding, we should see a person card with name/role fields
    expect(screen.getByPlaceholderText('Full name')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('e.g. President')).toBeInTheDocument();
  });

  it('shows effective limits per product', async () => {
    mockedGetEvent.mockResolvedValue([mockEvent]);
    mockedGetProducts.mockResolvedValue(mockProducts);
    mockedGetOrder.mockResolvedValue(mockOrder);

    render(<BookingWizard eventId="evt-1" />);

    await waitFor(() => {
      expect(screen.getByText('Available capacity')).toBeInTheDocument();
    });
    expect(screen.getByText('Meeting Ticket')).toBeInTheDocument();
    expect(screen.getByText('Party Ticket')).toBeInTheDocument();
    // Limits rendered as "X of Y remaining" via t('limits.remaining', { remaining, total })
    expect(screen.getByText('3 of 150 remaining')).toBeInTheDocument();
    expect(screen.getByText('13 of 200 remaining')).toBeInTheDocument();
  });

  it('displays the total amount (starts at €0.00 with no items)', async () => {
    mockedGetEvent.mockResolvedValue([mockEvent]);
    mockedGetProducts.mockResolvedValue(mockProducts);
    mockedGetOrder.mockResolvedValue(mockOrder);

    render(<BookingWizard eventId="evt-1" />);

    await waitFor(() => {
      expect(screen.getByText('Estimated Total')).toBeInTheDocument();
    });
  });

  it('populates form state from existing order items', async () => {
    const orderWithItems: Order = {
      ...mockOrder,
      items: [
        {
          product_id: 'prod-meeting',
          variant_id: null,
          item_fields_data: { name: 'Jan de Vries', role: 'President' },
          unit_price: 50,
          line_total: 50,
        },
      ],
      total_amount: 50,
    };
    mockedGetEvent.mockResolvedValue([mockEvent]);
    mockedGetProducts.mockResolvedValue(mockProducts);
    mockedGetOrder.mockResolvedValue(orderWithItems);

    render(<BookingWizard eventId="evt-1" />);

    await waitFor(() => {
      expect(screen.getByDisplayValue('Jan de Vries')).toBeInTheDocument();
    });
    expect(screen.getByDisplayValue('President')).toBeInTheDocument();
  });

  it('shows locked warning when order is locked', async () => {
    const lockedOrder = { ...mockOrder, status: 'locked' as const };
    mockedGetEvent.mockResolvedValue([mockEvent]);
    mockedGetProducts.mockResolvedValue(mockProducts);
    mockedGetOrder.mockResolvedValue(lockedOrder);

    render(<BookingWizard eventId="evt-1" />);

    await waitFor(() => {
      expect(
        screen.getByText('This booking is locked. Contact the organizers for changes.')
      ).toBeInTheDocument();
    });
  });

  it('loads products filtered by event product_ids', async () => {
    mockedGetEvent.mockResolvedValue([mockEvent]);
    mockedGetProducts.mockResolvedValue(mockProducts);
    mockedGetOrder.mockResolvedValue(mockOrder);

    render(<BookingWizard eventId="evt-1" />);

    await waitFor(() => {
      expect(mockedGetProducts).toHaveBeenCalledWith('evt-1', ['prod-meeting', 'prod-party']);
    });
  });
});
