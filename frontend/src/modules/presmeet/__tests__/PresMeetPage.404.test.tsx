/**
 * Bug condition exploration test for PresMeet 404 handling.
 *
 * Validates: Requirements 1.3
 *
 * This test encodes the EXPECTED behavior after the fix:
 * - When presmeetApi.getOrder rejects with a 404 AxiosError (no order exists),
 *   the PresMeetPage should NOT display an error message.
 *
 * On UNFIXED code, this test MUST FAIL — proving the bug exists.
 * After the fix is applied, this test should PASS.
 *
 * Counterexample (unfixed code): The 404 falls through to the outer catch
 * and setError() is called with "Fout bij laden PresMeet" / network error message.
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock react-i18next
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        'page.title': "Presidents' Meeting",
        'page.title_booking': "Presidents' Meeting Booking",
        'page.error_loading': 'Error loading PresMeet',
        'page.tab_booking': 'Booking',
      };
      return translations[key] ?? key;
    },
    i18n: { language: 'en', changeLanguage: jest.fn() },
  }),
}));

// Mock useAuth — user with valid presmeet access and club assignment
jest.mock('../../../context/AuthProvider', () => ({
  useAuth: () => ({
    user: {
      email: 'president@club.nl',
      sub: 'sub-456',
      groups: ['hdcnLeden', 'Products_Read', 'Regio_Pressmeet'],
      accessToken: 'mock-token',
    },
    isLoading: false,
    isAuthenticated: true,
    error: null,
    signOut: jest.fn(),
  }),
}));

// Create a proper AxiosError-like object for 404
const create404Error = () => {
  const error: any = new Error('Request failed with status code 404');
  error.isAxiosError = true;
  error.response = {
    status: 404,
    data: { message: 'Booking not found' },
    headers: {},
    statusText: 'Not Found',
    config: {},
  };
  error.config = {};
  error.toJSON = () => ({});
  return error;
};

// Mock presmeetApi — getEvent succeeds, getOrder returns 404
jest.mock('../services/presmeetApi', () => ({
  presmeetApi: {
    getEvent: jest.fn().mockResolvedValue([
      {
        event_id: 'pm2027',
        event_type: 'presmeet',
        name: 'PresMeet 2027',
        status: 'open',
        start_date: '2027-06-01',
        end_date: '2027-06-03',
        registration_open: '',
        registration_close: '',
        payment_deadline: '',
        product_ids: [],
        constraints: [],
        created_at: '',
        created_by: '',
      },
    ]),
    getOrder: jest.fn().mockRejectedValue(create404Error()),
    getProducts: jest.fn().mockResolvedValue([]),
  },
  isAuthorizationError: jest.fn().mockReturnValue(false),
}));

// Mock child components to avoid rendering their internals
jest.mock('../components/BookingWizard', () => () => (
  <div data-testid="booking-wizard">BookingWizard</div>
));
jest.mock('../components/OnboardingFlow', () => () => (
  <div data-testid="onboarding-flow">OnboardingFlow</div>
));
jest.mock('../components/PaymentPanel', () => () => (
  <div data-testid="payment-panel">PaymentPanel</div>
));
jest.mock('../components/DelegateManager', () => () => (
  <div data-testid="delegate-manager">DelegateManager</div>
));
jest.mock('../components/BookingSummaryPdf', () => () => (
  <div data-testid="booking-pdf">BookingSummaryPdf</div>
));
jest.mock('../components/ClubLogoUploader', () => ({ clubId, isAdmin }: any) => (
  <div data-testid="club-logo-uploader">ClubLogo</div>
));

// Import component under test AFTER mocks
import PresMeetPage from '../PresMeetPage';

describe('PresMeetPage — Bug condition: 404 when no order exists (Req 1.3)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Re-setup the mock since clearAllMocks resets implementations
    const { presmeetApi } = require('../services/presmeetApi');
    presmeetApi.getEvent.mockResolvedValue([
      {
        event_id: 'pm2027',
        event_type: 'presmeet',
        name: 'PresMeet 2027',
        status: 'open',
        start_date: '2027-06-01',
        end_date: '2027-06-03',
        registration_open: '',
        registration_close: '',
        payment_deadline: '',
        product_ids: [],
        constraints: [],
        created_at: '',
        created_by: '',
      },
    ]);
    presmeetApi.getOrder.mockRejectedValue(create404Error());
    presmeetApi.getProducts.mockResolvedValue([]);
    const { isAuthorizationError } = require('../services/presmeetApi');
    isAuthorizationError.mockReturnValue(false);
  });

  it('does NOT display an error message when getOrder returns 404', async () => {
    /**
     * Bug 1.3: On unfixed code, the 404 from getOrder is NOT caught by
     * the isAuthorizationError check (returns false) and does NOT match
     * the raw 403 check. It falls through to `throw orderErr`, which is
     * caught by the outer catch block and results in setError() being called.
     *
     * EXPECTED (fixed): 404 is treated as "no order yet" — no error shown.
     * ACTUAL (unfixed): Error message "Error loading PresMeet" is displayed.
     */
    render(<PresMeetPage />);

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.queryByRole('status')).not.toBeInTheDocument();
    }, { timeout: 3000 });

    // After loading, there should be NO error alert displayed
    const errorAlerts = screen.queryAllByRole('alert');
    const errorMessages = errorAlerts.filter((alert) => {
      // Check if the alert contains error-related content
      const text = alert.textContent || '';
      return (
        text.includes('Error loading PresMeet') ||
        text.includes('Fout bij laden') ||
        text.includes('Network Error') ||
        text.includes('Booking not found') ||
        text.includes('Request failed')
      );
    });

    expect(errorMessages).toHaveLength(0);
  });

  it('does NOT set error state text on 404 response', async () => {
    render(<PresMeetPage />);

    // Wait for the component to finish loading
    await waitFor(() => {
      expect(screen.queryByRole('status')).not.toBeInTheDocument();
    }, { timeout: 3000 });

    // The page should not contain any error-related text from the 404
    expect(screen.queryByText(/Error loading PresMeet/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Booking not found/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Network Error/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Request failed/i)).not.toBeInTheDocument();
  });
});
