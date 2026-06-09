/**
 * BookingForm component tests.
 *
 * Validates: Requirements 4.1–4.5, 8.1, 8.2, 8.6
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import BookingForm from '../components/BookingForm';
import { ProductTypeConfig, BookingFormData } from '../types/presmeet';

// Mock react-i18next
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, any>) => {
      const translations: Record<string, string> = {
        'booking_form.save_draft': 'Save Draft',
        'booking_form.submit_booking': 'Submit Booking',
        'booking_form.booking_locked': 'This booking is locked and cannot be modified.',
        'booking_form.estimated_total': 'Estimated Total',
        'booking_form.summary': '{{delegates}} delegate(s) · {{party}} party ticket(s) · {{tshirts}} t-shirt(s) · {{transfers}} transfer(s)',
        'booking_form.draft_saved': 'Draft saved',
        'booking_form.validation_errors': 'Validation errors',
        'booking_form.min_delegates': 'At least {{count}} delegate is required',
        'booking_form.max_tshirts': 'Maximum {{count}} t-shirts allowed',
      };
      let result = translations[key] ?? key;
      if (params) {
        Object.entries(params).forEach(([k, v]) => {
          result = result.replace(`{{${k}}}`, String(v));
        });
      }
      return result;
    },
    i18n: { language: 'en', changeLanguage: jest.fn() },
  }),
}));

// Mock presmeetService
const mockSaveBooking = jest.fn();
const mockSubmitBooking = jest.fn();

jest.mock('../services/presmeetApi', () => ({
  presmeetService: {
    saveBooking: (...args: any[]) => mockSaveBooking(...args),
    submitBooking: (...args: any[]) => mockSubmitBooking(...args),
  },
}));

// Mock Chakra UI with functional form elements
jest.mock('@chakra-ui/react', () => ({
  Box: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  VStack: ({ children }: any) => <div>{children}</div>,
  HStack: ({ children }: any) => <div style={{ display: 'flex' }}>{children}</div>,
  Text: ({ children }: any) => <span>{children}</span>,
  Heading: ({ children }: any) => <h2>{children}</h2>,
  Divider: () => <hr />,
  Button: ({ children, onClick, isDisabled, isLoading, ...props }: any) => (
    <button onClick={onClick} disabled={isDisabled || isLoading} {...props}>
      {children}
    </button>
  ),
  Alert: ({ children }: any) => <div role="alert">{children}</div>,
  AlertIcon: () => <span />,
  useToast: () => jest.fn(),
}));

// Mock child section components to simplify rendering
jest.mock('../components/DelegateSection', () => {
  return function MockDelegateSection(props: any) {
    return <div data-testid="delegate-section">Delegate Section (max: {props.maxDelegates})</div>;
  };
});

jest.mock('../components/GuestSection', () => {
  return function MockGuestSection(props: any) {
    return <div data-testid="guest-section">Guest Section</div>;
  };
});

jest.mock('../components/TransferSection', () => {
  return function MockTransferSection(props: any) {
    return <div data-testid="transfer-section">Transfer Section</div>;
  };
});

const defaultConfig: ProductTypeConfig[] = [
  {
    product_type: 'meeting_ticket',
    max_per_club: 3,
    min_per_club: 1,
    unit_price: 50,
    required_attributes: {},
  },
  {
    product_type: 'party_ticket',
    max_per_club: 13,
    min_per_club: 0,
    unit_price: 99.5,
    required_attributes: {},
  },
  {
    product_type: 'tshirt',
    max_per_club: 13,
    min_per_club: 0,
    unit_price: 25,
    required_attributes: {},
  },
  {
    product_type: 'airport_transfer',
    max_per_club: 20,
    min_per_club: 0,
    unit_price: 5,
    required_attributes: {},
  },
];

describe('BookingForm', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders delegate, guest, and transfer sections', () => {
    render(
      <BookingForm
        config={defaultConfig}
        eventStartDate="2025-09-15"
        eventEndDate="2025-09-18"
      />
    );

    expect(screen.getByTestId('delegate-section')).toBeInTheDocument();
    expect(screen.getByTestId('guest-section')).toBeInTheDocument();
    expect(screen.getByTestId('transfer-section')).toBeInTheDocument();
  });

  it('"Save Draft" button calls saveBooking API', async () => {
    mockSaveBooking.mockResolvedValue({ success: true });

    render(
      <BookingForm
        config={defaultConfig}
        eventStartDate="2025-09-15"
        eventEndDate="2025-09-18"
      />
    );

    const saveButton = screen.getByText('Save Draft');
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(mockSaveBooking).toHaveBeenCalledWith({
        delegates: [],
        guests: [],
        transfers: [],
      });
    });
  });

  it('"Submit" validates before submitting', async () => {
    // With min_per_club=1 for meeting_ticket and no delegates,
    // the form should NOT call submitBooking because validation fails.
    mockSaveBooking.mockResolvedValue({ success: true });
    mockSubmitBooking.mockResolvedValue({ success: true });

    render(
      <BookingForm
        config={defaultConfig}
        eventStartDate="2025-09-15"
        eventEndDate="2025-09-18"
      />
    );

    const submitButton = screen.getByText('Submit Booking');
    fireEvent.click(submitButton);

    // Validation should fail (no delegates), so submitBooking should NOT be called
    await waitFor(() => {
      expect(mockSubmitBooking).not.toHaveBeenCalled();
    });
  });

  it('"Submit" calls API when form data is valid', async () => {
    mockSaveBooking.mockResolvedValue({ success: true });
    mockSubmitBooking.mockResolvedValue({ success: true });

    const initialFormData: BookingFormData = {
      delegates: [{ name: 'Jan de Vries', role: 'President', attend_party: false }],
      guests: [],
      transfers: [],
    };

    render(
      <BookingForm
        config={defaultConfig}
        eventStartDate="2025-09-15"
        eventEndDate="2025-09-18"
        initialFormData={initialFormData}
      />
    );

    const submitButton = screen.getByText('Submit Booking');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockSaveBooking).toHaveBeenCalled();
      expect(mockSubmitBooking).toHaveBeenCalled();
    });
  });

  it('shows locked alert when order is locked', () => {
    render(
      <BookingForm
        config={defaultConfig}
        existingBooking={{
          order_id: 'order-1',
          club_id: 'club_123',
          channel: 'presmeet',
          source: 'presmeet',
          status: 'locked',
          payment_status: 'unpaid',
          items: [],
          total_amount: 0,
          created_at: '2025-01-01T00:00:00Z',
          updated_at: '2025-01-01T00:00:00Z',
          submitted_at: null,
        }}
      />
    );

    expect(screen.getByText(/locked and cannot be modified/i)).toBeInTheDocument();
  });
});
