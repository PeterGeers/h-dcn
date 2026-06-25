/**
 * PaymentPanel Component Tests
 *
 * Tests for the payment panel: outstanding amount display, payment status badge,
 * pay button interaction, redirect on success, and error handling.
 *
 * Validates: Requirements 7, 11
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

import { eventBookingApi } from '../services/eventBookingApi';
import PaymentPanel from '../components/PaymentPanel';
import { Order } from '../types/eventBooking.types';

// Mock toast
const mockToast = jest.fn();

// Mock Chakra UI
jest.mock('@chakra-ui/react', () => ({
  Badge: ({ children, colorScheme, ...props }: any) => (
    <span data-testid="payment-badge" data-colorscheme={colorScheme} {...props}>
      {children}
    </span>
  ),
  Box: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  Button: ({ children, isDisabled, isLoading, loadingText, onClick, ...props }: any) => (
    <button
      disabled={isDisabled || isLoading}
      onClick={onClick}
      data-testid="pay-button"
      data-loading={isLoading ? 'true' : 'false'}
      {...props}
    >
      {isLoading ? loadingText : children}
    </button>
  ),
  HStack: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  Heading: ({ children, ...props }: any) => <h2 {...props}>{children}</h2>,
  Text: ({ children, ...props }: any) => <span {...props}>{children}</span>,
  VStack: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  useToast: () => mockToast,
}));

// Mock eventBookingApi
jest.mock('../services/eventBookingApi', () => ({
  eventBookingApi: {
    pay: jest.fn(),
  },
}));

// Mock react-i18next
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, string>) => {
      const translations: Record<string, string> = {
        'payment.title': 'Betaling',
        'payment.total_amount': 'Totaalbedrag',
        'payment.already_paid': 'Reeds betaald',
        'payment.outstanding': 'Openstaand bedrag',
        'payment.redirecting_to_payment': 'Doorsturen naar betaling...',
        'payment.fully_paid_short': 'Volledig betaald',
        'payment.payment_failed': 'Betaling mislukt',
        'payment.payment_error_desc': 'Er is een fout opgetreden bij het starten van de betaling.',
        'payment.status_unpaid': 'Niet betaald',
        'payment.status_partial': 'Deels betaald',
        'payment.status_paid': 'Betaald',
      };
      if (key === 'payment.pay_button' && params?.amount) {
        return `Betaal ${params.amount}`;
      }
      return translations[key] || key;
    },
    i18n: { language: 'nl', changeLanguage: jest.fn() },
  }),
}));

const mockedPay = eventBookingApi.pay as jest.MockedFunction<typeof eventBookingApi.pay>;

// --- Test Fixtures ---

function createOrder(overrides: Partial<Order> = {}): Order {
  return {
    order_id: 'order-123',
    source_id: 'event-456',
    member_id: 'member-1',
    registry_row_id: 'club-abc',
    event_id: 'event-456',
    event_type: 'presmeet',
    status: 'submitted',
    payment_status: 'unpaid',
    total_amount: 450.0,
    total_paid: 0,
    items: [],
    delegates: { primary: 'jan@club.nl', secondary: null },
    version: 1,
    status_history: [],
    created_at: '2027-01-10T08:00:00Z',
    updated_at: '2027-01-10T08:00:00Z',
    submitted_at: '2027-01-15T10:30:00Z',
    created_by: 'jan@club.nl',
    ...overrides,
  };
}

describe('PaymentPanel', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Reset window.location mock
    delete (window as any).location;
    (window as any).location = { href: '' };
  });

  describe('outstanding amount display', () => {
    it('shows the correct outstanding amount when nothing is paid', () => {
      render(<PaymentPanel order={createOrder()} />);
      // total_amount=450, total_paid=0 → outstanding=450
      // The outstanding amount appears multiple times (summary + button), verify at least one
      const matches = screen.getAllByText(/€\s*450,00/);
      expect(matches.length).toBeGreaterThanOrEqual(1);
    });

    it('shows the correct outstanding when partially paid', () => {
      render(
        <PaymentPanel
          order={createOrder({ total_amount: 450, total_paid: 200, payment_status: 'partial' })}
        />
      );
      // outstanding = 450 - 200 = 250
      const matches = screen.getAllByText(/€\s*250,00/);
      expect(matches.length).toBeGreaterThanOrEqual(1);
    });

    it('shows zero outstanding when fully paid', () => {
      render(
        <PaymentPanel
          order={createOrder({ total_amount: 450, total_paid: 450, payment_status: 'paid' })}
        />
      );
      expect(screen.getByText(/€\s*0,00/)).toBeInTheDocument();
    });
  });

  describe('payment status badge', () => {
    it('shows red badge for unpaid', () => {
      render(<PaymentPanel order={createOrder({ payment_status: 'unpaid' })} />);
      const badge = screen.getByTestId('payment-badge');
      expect(badge).toHaveAttribute('data-colorscheme', 'red');
      expect(badge).toHaveTextContent('Niet betaald');
    });

    it('shows yellow badge for partial', () => {
      render(
        <PaymentPanel
          order={createOrder({ payment_status: 'partial', total_paid: 100 })}
        />
      );
      const badge = screen.getByTestId('payment-badge');
      expect(badge).toHaveAttribute('data-colorscheme', 'yellow');
      expect(badge).toHaveTextContent('Deels betaald');
    });

    it('shows green badge for paid', () => {
      render(
        <PaymentPanel
          order={createOrder({ payment_status: 'paid', total_paid: 450 })}
        />
      );
      const badge = screen.getByTestId('payment-badge');
      expect(badge).toHaveAttribute('data-colorscheme', 'green');
      expect(badge).toHaveTextContent('Betaald');
    });
  });

  describe('pay button behavior', () => {
    it('shows pay button with outstanding amount when balance due', () => {
      render(<PaymentPanel order={createOrder()} />);
      const button = screen.getByTestId('pay-button');
      expect(button).toBeEnabled();
      expect(button).toHaveTextContent(/Betaal/);
      expect(button).toHaveTextContent(/€\s*450,00/);
    });

    it('does not show pay button when fully paid', () => {
      render(
        <PaymentPanel
          order={createOrder({ total_amount: 450, total_paid: 450, payment_status: 'paid' })}
        />
      );
      expect(screen.queryByTestId('pay-button')).not.toBeInTheDocument();
    });

    it('shows "Volledig betaald" text when fully paid', () => {
      render(
        <PaymentPanel
          order={createOrder({ total_amount: 450, total_paid: 450, payment_status: 'paid' })}
        />
      );
      expect(screen.getByText('Volledig betaald')).toBeInTheDocument();
    });

    it('does not show pay button or paid message when total_amount is 0', () => {
      render(
        <PaymentPanel
          order={createOrder({ total_amount: 0, total_paid: 0, payment_status: 'unpaid' })}
        />
      );
      // No balance, no button
      expect(screen.queryByTestId('pay-button')).not.toBeInTheDocument();
      // Also should not show "Volledig betaald" since no amount was ever due
      expect(screen.queryByText('Volledig betaald')).not.toBeInTheDocument();
    });
  });

  describe('pay action - success', () => {
    it('redirects to checkout_url on successful payment initiation', async () => {
      mockedPay.mockResolvedValueOnce({
        checkout_url: 'https://checkout.mollie.com/pay/abc123',
        payment_id: 'pay-1',
        amount: 450,
        status: 'pending',
      });

      render(<PaymentPanel order={createOrder()} />);
      fireEvent.click(screen.getByTestId('pay-button'));

      await waitFor(() => {
        expect(window.location.href).toBe('https://checkout.mollie.com/pay/abc123');
      });

      expect(mockedPay).toHaveBeenCalledWith('order-123');
    });
  });

  describe('pay action - error handling', () => {
    it('shows toast on API error without losing page state', async () => {
      mockedPay.mockRejectedValueOnce(new Error('Payment provider unavailable'));

      render(<PaymentPanel order={createOrder()} />);
      fireEvent.click(screen.getByTestId('pay-button'));

      await waitFor(() => {
        expect(mockToast).toHaveBeenCalledWith(
          expect.objectContaining({
            title: 'Betaling mislukt',
            description: 'Payment provider unavailable',
            status: 'error',
          })
        );
      });

      // Button should still be rendered (page state preserved)
      expect(screen.getByTestId('pay-button')).toBeInTheDocument();
      expect(screen.getByTestId('pay-button')).toBeEnabled();
    });

    it('shows generic error message for non-Error exceptions', async () => {
      mockedPay.mockRejectedValueOnce({ type: 'UNKNOWN' });

      render(<PaymentPanel order={createOrder()} />);
      fireEvent.click(screen.getByTestId('pay-button'));

      await waitFor(() => {
        expect(mockToast).toHaveBeenCalledWith(
          expect.objectContaining({
            title: 'Betaling mislukt',
            description: expect.stringContaining('fout opgetreden'),
            status: 'error',
          })
        );
      });
    });

    it('shows loading state while payment is processing', async () => {
      let resolvePayment: (value: any) => void;
      const payPromise = new Promise((resolve) => {
        resolvePayment = resolve;
      });
      mockedPay.mockReturnValueOnce(payPromise as any);

      render(<PaymentPanel order={createOrder()} />);
      fireEvent.click(screen.getByTestId('pay-button'));

      // While loading, button should be disabled
      expect(screen.getByTestId('pay-button')).toBeDisabled();
      expect(screen.getByTestId('pay-button')).toHaveAttribute('data-loading', 'true');

      // Resolve to clean up
      resolvePayment!({
        checkout_url: 'https://checkout.mollie.com/pay/abc',
        payment_id: 'pay-1',
        amount: 450,
        status: 'pending',
      });

      await waitFor(() => {
        expect(window.location.href).toBe('https://checkout.mollie.com/pay/abc');
      });
    });
  });
});
