/**
 * PresMeetPage unit tests — Validates that Admin tab is no longer present.
 *
 * Admin functionality has been moved to the unified Webshop Beheer page
 * (WebshopManagementPage). The PresMeet page only contains the booking wizard.
 *
 * Validates: Requirements 10.5, 10.11, 12.6
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock react-i18next
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, fallback?: string) => {
      const translations: Record<string, string> = {
        'page.title': "Presidents' Meeting",
        'page.title_booking': "Presidents' Meeting Booking",
        'page.error_loading': 'Error loading PresMeet',
        'page.tab_booking': 'Booking',
        'page.tab_admin': 'Admin',
      };
      return translations[key] ?? fallback ?? key;
    },
    i18n: { language: 'en', changeLanguage: jest.fn() },
  }),
}));

// Mock useAuth to provide controlled user groups
const mockUseAuth = jest.fn();
jest.mock('../../../context/AuthProvider', () => ({
  useAuth: () => mockUseAuth(),
}));

// Mock presmeetApi
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
    getOrder: jest.fn().mockResolvedValue({
      order_id: 'order-1',
      club_id: 'club-1',
      event_id: 'pm2027',
      status: 'draft',
      items: [],
    }),
    getProducts: jest.fn().mockResolvedValue([]),
  },
  isAuthorizationError: jest.fn().mockReturnValue(false),
}));

// Mock child components to avoid rendering their internals
jest.mock('../components/BookingWizard', () => () => <div data-testid="booking-wizard">BookingWizard</div>);
jest.mock('../components/OnboardingFlow', () => () => <div data-testid="onboarding-flow">OnboardingFlow</div>);
jest.mock('../components/PaymentPanel', () => () => <div data-testid="payment-panel">PaymentPanel</div>);
jest.mock('../components/DelegateManager', () => () => <div data-testid="delegate-manager">DelegateManager</div>);
jest.mock('../components/BookingSummaryPdf', () => () => <div data-testid="booking-pdf">BookingSummaryPdf</div>);
jest.mock('../components/ClubLogoUploader', () => ({ clubId, isAdmin }: any) => (
  <div data-testid="club-logo-uploader">ClubLogo</div>
));

// Import the component under test AFTER mocks are set up
import PresMeetPage from '../PresMeetPage';

function setupAuth(groups: string[]) {
  mockUseAuth.mockReturnValue({
    user: { email: 'test@test.nl', sub: 'sub-123', groups, accessToken: 'token' },
    isLoading: false,
    isAuthenticated: true,
    error: null,
    signOut: jest.fn(),
  });
}

describe('PresMeetPage — Admin tab removed (unified in Webshop Beheer)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('does NOT render Admin tab for user with Products_CRUD + Regio_Pressmeet', () => {
    setupAuth(['hdcnLeden', 'Products_CRUD', 'Regio_Pressmeet']);
    const { container } = render(<PresMeetPage />);

    // At no point during rendering (loading or loaded) should Admin appear
    expect(container.textContent).not.toContain('Admin');
  });

  it('does NOT render Admin tab for user with Webshop_Management + Regio_All', () => {
    setupAuth(['hdcnLeden', 'Webshop_Management', 'Regio_All']);
    const { container } = render(<PresMeetPage />);

    expect(container.textContent).not.toContain('Admin');
  });

  it('does not render AdminDashboard or AdminRouter component', () => {
    setupAuth(['hdcnLeden', 'Products_CRUD', 'Regio_Pressmeet']);
    render(<PresMeetPage />);

    // AdminRouter and AdminDashboard should never be rendered
    expect(screen.queryByTestId('admin-dashboard')).not.toBeInTheDocument();
  });
});
