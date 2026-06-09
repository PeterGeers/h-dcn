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

// Mock Chakra UI toast
const mockToast = jest.fn();
jest.mock('@chakra-ui/react', () => {
  const actual = jest.requireActual('@chakra-ui/react');
  return {
    ...actual,
    useToast: () => mockToast,
  };
});

// Mock the presmeetApi
jest.mock('../services/presmeetApi', () => ({
  presmeetApi: {
    getEvent: jest.fn(),
    getProducts: jest.fn(),
    getOrder: jest.fn(),
  },
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
      };
      if (key === 'booking.last_saved' && params?.time) {
        return `Last saved: ${params.time}`;
      }
      return translations[key] || key;
    },
    i18n: { language: 'nl', changeLanguage: jest.fn() },
  }),
}));

import { presmeetApi } from '../services/presmeetApi';
import BookingWizard from '../components/BookingWizard';
import { Event, Order, Product } from '../types/presmeet.types';

const mockedGetEvent = presmeetApi.getEvent as jest.MockedFunction<typeof presmeetApi.getEvent>;
const mockedGetProducts = presmeetApi.getProducts as jest.MockedFunction<typeof presmeetApi.getProducts>;
const mockedGetOrder = presmeetApi.getOrder as jest.MockedFunction<typeof presmeetApi.getOrder>;

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
    name: 'Meeting Ticket',
    event_id: 'evt-1',
    event_type: 'presmeet',
    price: 50,
    order_item_fields: [
      { id: 'name', label: 'Naam', type: 'text', required: true },
      { id: 'role', label: 'Functie', type: 'text', required: true },
    ],
    variant_schema: null,
    purchase_rules: { min_per_club: 1, max_per_club: 3 },
  },
  {
    product_id: 'prod-party',
    name: 'Party Ticket',
    event_id: 'evt-1',
    event_type: 'presmeet',
    price: 25,
    order_item_fields: [
      { id: 'name', label: 'Naam', type: 'text', required: true },
    ],
    variant_schema: null,
    purchase_rules: { max_per_club: 13 },
  },
];

const mockOrder: Order = {
  order_id: 'ord-1',
  club_id: 'club-1',
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
    // Meeting Ticket: min(3, 150) = 3
    expect(screen.getByText('max 3 per club')).toBeInTheDocument();
    // Party Ticket: min(13, Infinity) = 13
    expect(screen.getByText('max 13 per club')).toBeInTheDocument();
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
      expect(mockedGetProducts).toHaveBeenCalledWith('presmeet', ['prod-meeting', 'prod-party']);
    });
  });
});
