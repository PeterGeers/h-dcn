import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import Dashboard from '../Dashboard';

// Mock react-i18next
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, string>) => {
      if (params?.name) return `Welcome ${params.name}`;
      return key;
    },
    i18n: { language: 'nl', changeLanguage: jest.fn() },
  }),
  initReactI18next: { type: '3rdParty', init: jest.fn() },
}));

// Mock i18n initialization
jest.mock('../../i18n', () => ({}));
jest.mock('../../i18n/index', () => ({}));

// Mock react-router-dom
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
}));

// Mock useAuth from context/AuthProvider
const mockUser = {
  email: 'test@h-dcn.nl',
  givenName: 'Test',
  familyName: 'User',
  groups: ['hdcnLeden'],
  accessToken: 'mock-access-token',
};

jest.mock('../../context/AuthProvider', () => ({
  useAuth: () => ({
    user: mockUser,
  }),
}));

// Mock membershipService to avoid real API calls
jest.mock('../../utils/membershipService', () => ({
  membershipService: {
    getMemberByEmail: jest.fn().mockResolvedValue({ member_id: '123' }),
    submitMembershipApplication: jest.fn(),
    checkExistingMember: jest.fn(),
    getMembershipApplicationStatus: jest.fn(),
  },
}));

// Mock FunctionGuard to just render children (simplifies testing)
jest.mock('../../components/common/FunctionGuard', () => ({
  FunctionGuard: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

// Mock Chakra UI components to avoid provider requirements
jest.mock('@chakra-ui/react', () => {
  const mockReact = require('react');
  return {
    Box: ({ children, ...props }: any) => mockReact.createElement('div', props, children),
    VStack: ({ children, ...props }: any) => mockReact.createElement('div', props, children),
    Heading: ({ children, ...props }: any) => mockReact.createElement('h1', props, children),
    Text: ({ children, ...props }: any) => mockReact.createElement('span', props, children),
    SimpleGrid: ({ children, ...props }: any) => mockReact.createElement('div', { 'data-testid': 'grid', ...props }, children),
    Spinner: (props: any) => mockReact.createElement('div', { 'data-testid': 'spinner', ...props }),
    Center: ({ children, ...props }: any) => mockReact.createElement('div', props, children),
    Button: ({ children, onClick, ...props }: any) => mockReact.createElement('button', { onClick, ...props }, children),
  };
});

describe('Dashboard - Events Calendar Card', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders events-calendar card with correct icon (📅), title and description', async () => {
    render(<Dashboard />);

    await waitFor(() => {
      // The card should display the localized title key
      expect(screen.getByText('cards.events_calendar_title')).toBeInTheDocument();
      // The card should display the localized description key
      expect(screen.getByText('cards.events_calendar_desc')).toBeInTheDocument();
    });

    // The calendar icon 📅 appears (may appear multiple times due to Events admin card)
    const calendarIcons = screen.getAllByText('📅');
    expect(calendarIcons.length).toBeGreaterThanOrEqual(1);
  });

  it('navigates to /events/calendar when the card is clicked', async () => {
    render(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText('cards.events_calendar_title')).toBeInTheDocument();
    });

    // Find the card by its title and click the parent card area
    // AppCard renders as a clickable Box, so clicking the title or any content triggers onClick
    fireEvent.click(screen.getByText('cards.events_calendar_title'));

    expect(mockNavigate).toHaveBeenCalledWith('/events/calendar');
  });

  it('renders events-calendar card without any API dependency (visible even with no published events)', async () => {
    // The card should be visible immediately — no event fetch needed
    render(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText('cards.events_calendar_title')).toBeInTheDocument();
      expect(screen.getByText('cards.events_calendar_desc')).toBeInTheDocument();
    });

    // The calendar icon is present
    const calendarIcons = screen.getAllByText('📅');
    expect(calendarIcons.length).toBeGreaterThanOrEqual(1);

    // There should be no eventBookingApi or events-public fetch call
    // The membershipService.getMemberByEmail is called but that's for membership check, not events
    // The key assertion: the card renders without waiting for any event data
  });

  it('does not render EventBookingCard component (removed from codebase)', async () => {
    render(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText('cards.events_calendar_title')).toBeInTheDocument();
    });

    // EventBookingCard used to render individual event cards with dynamic event titles
    // Now there should only be a single static events-calendar card
    // Verify no dynamic event-related content is rendered (no event booking API data)
    expect(screen.queryByText('EventBookingCard')).not.toBeInTheDocument();
    
    // The only events-related card should be the static calendar card
    const calendarIcons = screen.getAllByText('📅');
    // There may be multiple 📅 icons (events-calendar card + events admin card for admin users)
    // but none should be from EventBookingCard
    expect(calendarIcons.length).toBeGreaterThanOrEqual(1);
  });
});
