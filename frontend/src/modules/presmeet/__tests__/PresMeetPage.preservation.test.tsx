/**
 * Preservation tests for PresMeetPage — existing 200/403 handling unchanged.
 *
 * **Validates: Requirements 3.3, 3.4, 3.5**
 *
 * Property 4: Preservation - PresMeet existing order retrieval unchanged
 *
 * These tests verify CURRENT behavior that must be preserved after the fix:
 * - When a club HAS an existing order → 200 response loads correctly
 * - When user lacks PresMeet access → 403 "PresMeet access required" shows error
 * - When user has no club assignment → 403 triggers onboarding flow
 *
 * These tests MUST PASS on unfixed code — they establish baseline behavior.
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
const mockUseAuth = jest.fn();
jest.mock('../../../context/AuthProvider', () => ({
  useAuth: () => mockUseAuth(),
}));

// Mock presmeetApi
const mockGetEvent = jest.fn();
const mockGetOrder = jest.fn();
const mockGetProducts = jest.fn();
const mockIsAuthorizationError = jest.fn();

jest.mock('../services/presmeetApi', () => ({
  presmeetApi: {
    getEvent: (...args: any[]) => mockGetEvent(...args),
    getOrder: (...args: any[]) => mockGetOrder(...args),
    getProducts: (...args: any[]) => mockGetProducts(...args),
  },
  isAuthorizationError: (...args: any[]) => mockIsAuthorizationError(...args),
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

function setupAuth(groups: string[] = ['hdcnLeden', 'Products_Read', 'Regio_Pressmeet']) {
  mockUseAuth.mockReturnValue({
    user: {
      email: 'president@club.nl',
      sub: 'sub-456',
      groups,
      accessToken: 'mock-token',
    },
    isLoading: false,
    isAuthenticated: true,
    error: null,
    signOut: jest.fn(),
  });
}

const mockEvent = {
  event_id: 'pm2027',
  event_type: 'presmeet',
  name: 'PresMeet 2027',
  status: 'open',
  start_date: '2027-06-01',
  end_date: '2027-06-03',
  registration_open: '',
  registration_close: '',
  payment_deadline: '',
  product_ids: ['prod-1', 'prod-2'],
  constraints: [],
  created_at: '',
  created_by: '',
};

const mockOrder = {
  order_id: 'order-123',
  club_id: 'club-abc',
  event_id: 'pm2027',
  status: 'draft',
  items: [
    { product_id: 'prod-1', quantity: 2, unit_price: 50 },
  ],
  version: 1,
};

describe('PresMeetPage — Preservation: 200 response loads correctly (Req 3.3)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setupAuth();
    mockGetEvent.mockResolvedValue([mockEvent]);
    mockGetOrder.mockResolvedValue(mockOrder);
    mockGetProducts.mockResolvedValue([
      { product_id: 'prod-1', name: 'Dinner Ticket', price: 50 },
      { product_id: 'prod-2', name: 'T-shirt', price: 25 },
    ]);
    mockIsAuthorizationError.mockReturnValue(false);
  });

  it('renders the booking page with order data on successful 200 response', async () => {
    render(<PresMeetPage />);

    // Wait for loading to complete and BookingWizard to appear
    await waitFor(() => {
      expect(screen.getByTestId('booking-wizard')).toBeInTheDocument();
    }, { timeout: 3000 });

    // No error should be displayed
    expect(screen.queryByText(/Error loading PresMeet/i)).not.toBeInTheDocument();

    // The booking title should be visible
    expect(screen.getByText("Presidents' Meeting Booking")).toBeInTheDocument();
  });

  it('does NOT show onboarding flow when order exists', async () => {
    render(<PresMeetPage />);

    await waitFor(() => {
      expect(screen.getByTestId('booking-wizard')).toBeInTheDocument();
    }, { timeout: 3000 });

    // Onboarding should NOT be shown
    expect(screen.queryByTestId('onboarding-flow')).not.toBeInTheDocument();
  });

  it('calls getOrder with the correct event_id', async () => {
    render(<PresMeetPage />);

    await waitFor(() => {
      expect(mockGetOrder).toHaveBeenCalledWith('pm2027');
    }, { timeout: 3000 });
  });
});

describe('PresMeetPage — Preservation: 403 authorization error handling (Req 3.4)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    setupAuth();
    mockGetEvent.mockResolvedValue([mockEvent]);
    mockGetProducts.mockResolvedValue([]);
  });

  it('displays error when user lacks PresMeet access (403 "PresMeet access required")', async () => {
    // Simulate the interceptor transforming 403 into AuthorizationError
    const authError = {
      type: 'AUTHORIZATION_ERROR',
      message: 'PresMeet access required',
      status: 403,
    };
    mockGetOrder.mockRejectedValue(authError);
    mockIsAuthorizationError.mockReturnValue(true);

    render(<PresMeetPage />);

    // Wait for error to be displayed
    await waitFor(() => {
      expect(screen.getByText(/PresMeet access required/i)).toBeInTheDocument();
    }, { timeout: 3000 });

    // Should NOT show onboarding
    expect(screen.queryByTestId('onboarding-flow')).not.toBeInTheDocument();
  });

  it('shows onboarding flow when 403 indicates missing club assignment (isAuthorizationError path)', async () => {
    // Simulate the interceptor transforming 403 into AuthorizationError with club message
    const authError = {
      type: 'AUTHORIZATION_ERROR',
      message: 'Missing club assignment',
      status: 403,
    };
    mockGetOrder.mockRejectedValue(authError);
    mockIsAuthorizationError.mockReturnValue(true);

    render(<PresMeetPage />);

    // Wait for onboarding flow to appear
    await waitFor(() => {
      expect(screen.getByTestId('onboarding-flow')).toBeInTheDocument();
    }, { timeout: 3000 });

    // Error message should NOT be displayed — onboarding handles it
    expect(screen.queryByText(/Missing club assignment/i)).not.toBeInTheDocument();
  });

  it('shows onboarding flow when raw 403 response contains club assignment message', async () => {
    // Simulate raw 403 that wasn't transformed by the interceptor
    const rawError: any = new Error('Request failed with status code 403');
    rawError.isAxiosError = true;
    rawError.response = {
      status: 403,
      data: { message: 'Missing club assignment' },
      headers: {},
      statusText: 'Forbidden',
      config: {},
    };
    rawError.config = {};
    mockGetOrder.mockRejectedValue(rawError);
    mockIsAuthorizationError.mockReturnValue(false);

    render(<PresMeetPage />);

    // Wait for onboarding flow to appear
    await waitFor(() => {
      expect(screen.getByTestId('onboarding-flow')).toBeInTheDocument();
    }, { timeout: 3000 });
  });

  it('displays error for raw 403 without club assignment message', async () => {
    // Simulate raw 403 with generic permission message
    const rawError: any = new Error('Request failed with status code 403');
    rawError.isAxiosError = true;
    rawError.response = {
      status: 403,
      data: { message: 'PresMeet access required' },
      headers: {},
      statusText: 'Forbidden',
      config: {},
    };
    rawError.config = {};
    mockGetOrder.mockRejectedValue(rawError);
    mockIsAuthorizationError.mockReturnValue(false);

    render(<PresMeetPage />);

    // Wait for error to be displayed
    await waitFor(() => {
      expect(screen.getByText(/PresMeet access required/i)).toBeInTheDocument();
    }, { timeout: 3000 });

    // Should NOT show onboarding for non-club errors
    expect(screen.queryByTestId('onboarding-flow')).not.toBeInTheDocument();
  });
});
