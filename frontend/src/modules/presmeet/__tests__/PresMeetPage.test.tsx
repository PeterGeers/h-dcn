/**
 * PresMeetPage unit tests — Admin role check visibility.
 *
 * Tests that only users with the correct management role + region role combo
 * see the Admin tab in the PresMeet page.
 *
 * Validates: Requirements 5.1, 5.3
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock useAuth to provide controlled user groups
const mockUseAuth = jest.fn();
jest.mock('../../../context/AuthProvider', () => ({
  useAuth: () => mockUseAuth(),
}));

// Mock usePresMeetBooking to provide default state (not loading, no onboarding)
jest.mock('../hooks/usePresMeetBooking', () => ({
  usePresMeetBooking: () => ({
    config: { event: { start_date: '2025-09-01', end_date: '2025-09-03' }, product_types: [] },
    booking: null,
    formData: { delegates: [], guests: [], transfers: [] },
    productTypes: [],
    isLoading: false,
    isSaving: false,
    isSubmitting: false,
    error: null,
    needsOnboarding: false,
    loadBooking: jest.fn(),
    reloadAll: jest.fn(),
    saveBooking: jest.fn(),
    submitBooking: jest.fn(),
    initiatePayment: jest.fn(),
  }),
}));

// Mock child components to avoid rendering their internals
jest.mock('../components/BookingForm', () => () => <div data-testid="booking-form">BookingForm</div>);
jest.mock('../components/BookingOverview', () => () => <div data-testid="booking-overview">BookingOverview</div>);
jest.mock('../components/AdminDashboard', () => () => <div data-testid="admin-dashboard">AdminDashboard</div>);
jest.mock('../components/OnboardingFlow', () => () => <div data-testid="onboarding-flow">OnboardingFlow</div>);

// Mock Chakra UI components to render testable HTML
jest.mock('@chakra-ui/react', () => ({
  Box: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  Container: ({ children }: any) => <div>{children}</div>,
  Heading: ({ children }: any) => <h1>{children}</h1>,
  Tabs: ({ children }: any) => <div>{children}</div>,
  TabList: ({ children }: any) => <div role="tablist">{children}</div>,
  TabPanels: ({ children }: any) => <div>{children}</div>,
  Tab: ({ children }: any) => <button role="tab">{children}</button>,
  TabPanel: ({ children }: any) => <div role="tabpanel">{children}</div>,
  Spinner: () => <span data-testid="spinner">Loading...</span>,
  Center: ({ children }: any) => <div>{children}</div>,
  Alert: ({ children }: any) => <div role="alert">{children}</div>,
  AlertIcon: () => <span />,
  AlertTitle: ({ children }: any) => <strong>{children}</strong>,
  AlertDescription: ({ children }: any) => <span>{children}</span>,
  Text: ({ children }: any) => <span>{children}</span>,
}));

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

describe('PresMeetPage — Admin tab visibility', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('shows Admin tab for user with Products_CRUD + Regio_Pressmeet', () => {
    setupAuth(['hdcnLeden', 'Products_CRUD', 'Regio_Pressmeet']);
    render(<PresMeetPage />);

    const tabs = screen.getAllByRole('tab');
    const tabTexts = tabs.map((t) => t.textContent);
    expect(tabTexts).toContain('Admin');
  });

  it('shows Admin tab for user with Products_Read + Regio_Pressmeet', () => {
    setupAuth(['hdcnLeden', 'Products_Read', 'Regio_Pressmeet']);
    render(<PresMeetPage />);

    const tabs = screen.getAllByRole('tab');
    const tabTexts = tabs.map((t) => t.textContent);
    expect(tabTexts).toContain('Admin');
  });

  it('shows Admin tab for user with Webshop_Management + Regio_All', () => {
    setupAuth(['hdcnLeden', 'Webshop_Management', 'Regio_All']);
    render(<PresMeetPage />);

    const tabs = screen.getAllByRole('tab');
    const tabTexts = tabs.map((t) => t.textContent);
    expect(tabTexts).toContain('Admin');
  });

  it('does NOT show Admin tab for user with Products_CRUD but NO region role', () => {
    setupAuth(['hdcnLeden', 'Products_CRUD']);
    render(<PresMeetPage />);

    const tabs = screen.getAllByRole('tab');
    const tabTexts = tabs.map((t) => t.textContent);
    expect(tabTexts).not.toContain('Admin');
  });

  it('does NOT show Admin tab for user with Regio_Pressmeet but NO management role', () => {
    setupAuth(['hdcnLeden', 'Regio_Pressmeet']);
    render(<PresMeetPage />);

    const tabs = screen.getAllByRole('tab');
    const tabTexts = tabs.map((t) => t.textContent);
    expect(tabTexts).not.toContain('Admin');
  });

  it('does NOT show Admin tab for user with no relevant roles', () => {
    setupAuth(['hdcnLeden']);
    render(<PresMeetPage />);

    const tabs = screen.getAllByRole('tab');
    const tabTexts = tabs.map((t) => t.textContent);
    expect(tabTexts).not.toContain('Admin');
  });
});
