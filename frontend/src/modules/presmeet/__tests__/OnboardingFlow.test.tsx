/**
 * OnboardingFlow component tests.
 *
 * Validates: Requirements 2.3, 2.5
 *
 * Tests cover:
 * - Loading spinner on initial render
 * - Club list rendering when registry loads
 * - Club assignment on selection
 * - onComplete callback after successful assignment
 * - 409 conflict message with contact info
 * - Error alert when registry fetch fails
 * - "Choose a different club" button after 409 (allows retry)
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import OnboardingFlow from '../components/OnboardingFlow';
import { ClubRegistry } from '../types/presmeet';

// Mock react-i18next
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, any>) => {
      const translations: Record<string, string> = {
        'onboarding.select_club': 'Select Your Club',
        'onboarding.select_club_desc': 'Choose the club you represent for the Presidents\' Meeting.',
        'onboarding.loading_clubs': 'Loading available clubs...',
        'onboarding.load_failed': 'Failed to load clubs',
        'onboarding.no_clubs': 'No clubs are currently available. Please contact the administrator.',
        'onboarding.club_assigned': 'Club assigned',
        'onboarding.club_assigned_desc': '{{clubName}} assigned successfully.',
        'onboarding.assignment_failed': 'Assignment failed',
        'onboarding.assignment_failed_desc': 'An unexpected error occurred. Please try again.',
        'onboarding.club_already_assigned': 'Club Already Assigned',
        'onboarding.already_assigned_desc': '{{clubName}} already has a registered representative.',
        'onboarding.current_contact': 'Current contact',
        'onboarding.contact_admin': 'If you believe this is incorrect, please contact the PresMeet administrator.',
        'onboarding.choose_different': 'Choose a different club',
        'onboarding.no_logo': 'No logo',
        'onboarding.already_assigned': 'Already assigned',
        'onboarding.assigning': 'Assigning...',
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
const mockGetClubRegistry = jest.fn();
const mockAssignClub = jest.fn();

jest.mock('../services/presmeetApi', () => ({
  presmeetService: {
    getClubRegistry: (...args: any[]) => mockGetClubRegistry(...args),
    assignClub: (...args: any[]) => mockAssignClub(...args),
  },
}));

// Mock Chakra UI useToast
const mockToast = jest.fn();

jest.mock('@chakra-ui/react', () => ({
  Box: ({ children, onClick, ...props }: any) => (
    <div onClick={onClick} data-testid={props['data-testid']} {...props}>{children}</div>
  ),
  Heading: ({ children }: any) => <h2>{children}</h2>,
  Text: ({ children, ...props }: any) => <span {...props}>{children}</span>,
  SimpleGrid: ({ children }: any) => <div data-testid="club-grid">{children}</div>,
  Image: ({ alt }: any) => <img alt={alt} />,
  Button: ({ children, onClick, ...props }: any) => (
    <button onClick={onClick} {...props}>{children}</button>
  ),
  Spinner: ({ ...props }: any) => <div data-testid="loading-spinner" role="status" {...props}>Loading...</div>,
  Alert: ({ children, status }: any) => <div role="alert" data-status={status}>{children}</div>,
  AlertIcon: () => <span data-testid="alert-icon" />,
  AlertTitle: ({ children }: any) => <strong>{children}</strong>,
  AlertDescription: ({ children }: any) => <div>{children}</div>,
  VStack: ({ children }: any) => <div>{children}</div>,
  HStack: ({ children }: any) => <div style={{ display: 'flex' }}>{children}</div>,
  Center: ({ children }: any) => <div>{children}</div>,
  useToast: () => mockToast,
}));

// --- Test data ---

const mockRegistry: ClubRegistry = {
  version: '1.0',
  updated_at: '2025-06-01T10:00:00Z',
  clubs: [
    {
      club_id: 'amsterdam',
      club_name: 'HD Club Amsterdam',
      logo_url: 'https://cdn.h-dcn.nl/clubs/amsterdam.png',
      assigned_member_id: null,
      assigned_contact: null,
      assigned_at: null,
    },
    {
      club_id: 'rotterdam',
      club_name: 'HD Club Rotterdam',
      logo_url: null,
      assigned_member_id: 'existing-member-id',
      assigned_contact: 'rep@rotterdam-hd.nl',
      assigned_at: '2025-01-10T08:00:00Z',
    },
    {
      club_id: 'utrecht',
      club_name: 'HD Club Utrecht',
      logo_url: null,
      assigned_member_id: null,
      assigned_contact: null,
      assigned_at: null,
    },
  ],
};

describe('OnboardingFlow', () => {
  const onComplete = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('shows loading spinner initially', () => {
    // Never resolve the promise to keep loading state
    mockGetClubRegistry.mockReturnValue(new Promise(() => {}));

    render(<OnboardingFlow onComplete={onComplete} />);

    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
    expect(screen.getByText('Loading available clubs...')).toBeInTheDocument();
  });

  it('renders club list when registry loads successfully', async () => {
    mockGetClubRegistry.mockResolvedValue({
      success: true,
      data: mockRegistry,
    });

    await act(async () => {
      render(<OnboardingFlow onComplete={onComplete} />);
    });

    expect(screen.getByText('Select Your Club')).toBeInTheDocument();
    expect(screen.getByText('HD Club Amsterdam')).toBeInTheDocument();
    expect(screen.getByText('HD Club Rotterdam')).toBeInTheDocument();
    expect(screen.getByText('HD Club Utrecht')).toBeInTheDocument();
  });

  it('calls assignClub when a club is clicked', async () => {
    mockGetClubRegistry.mockResolvedValue({
      success: true,
      data: mockRegistry,
    });
    mockAssignClub.mockResolvedValue({
      success: true,
      data: { message: 'Club assigned', club_id: 'amsterdam', member_id: 'member-1' },
    });

    await act(async () => {
      render(<OnboardingFlow onComplete={onComplete} />);
    });

    await act(async () => {
      fireEvent.click(screen.getByText('HD Club Amsterdam'));
    });

    expect(mockAssignClub).toHaveBeenCalledWith('amsterdam');
  });

  it('calls onComplete callback on successful assignment', async () => {
    mockGetClubRegistry.mockResolvedValue({
      success: true,
      data: mockRegistry,
    });
    mockAssignClub.mockResolvedValue({
      success: true,
      data: { message: 'Club assigned', club_id: 'amsterdam', member_id: 'member-1' },
    });

    await act(async () => {
      render(<OnboardingFlow onComplete={onComplete} />);
    });

    await act(async () => {
      fireEvent.click(screen.getByText('HD Club Amsterdam'));
    });

    expect(onComplete).toHaveBeenCalledWith('amsterdam');
  });

  it('shows conflict message with contact info on 409 response', async () => {
    mockGetClubRegistry.mockResolvedValue({
      success: true,
      data: mockRegistry,
    });
    mockAssignClub.mockResolvedValue({
      success: false,
      error: 'Club already assigned',
      data: { assigned_contact: 'rep@rotterdam-hd.nl' },
    });

    await act(async () => {
      render(<OnboardingFlow onComplete={onComplete} />);
    });

    await act(async () => {
      fireEvent.click(screen.getByText('HD Club Rotterdam'));
    });

    expect(screen.getByText('Club Already Assigned')).toBeInTheDocument();
    expect(screen.getByText('rep@rotterdam-hd.nl')).toBeInTheDocument();
    expect(onComplete).not.toHaveBeenCalled();
  });

  it('shows error alert when registry fetch fails', async () => {
    mockGetClubRegistry.mockResolvedValue({
      success: false,
      error: 'Internal server error',
    });

    await act(async () => {
      render(<OnboardingFlow onComplete={onComplete} />);
    });

    expect(screen.getByText('Failed to load clubs')).toBeInTheDocument();
    expect(screen.getByText('Internal server error')).toBeInTheDocument();
  });

  it('shows "Choose a different club" button after 409 and allows retry', async () => {
    mockGetClubRegistry.mockResolvedValue({
      success: true,
      data: mockRegistry,
    });
    mockAssignClub.mockResolvedValue({
      success: false,
      error: 'Club already assigned',
      data: { assigned_contact: 'rep@rotterdam-hd.nl' },
    });

    await act(async () => {
      render(<OnboardingFlow onComplete={onComplete} />);
    });

    // Click an assigned club
    await act(async () => {
      fireEvent.click(screen.getByText('HD Club Rotterdam'));
    });

    // Should show conflict state with dismiss button
    const retryButton = screen.getByText('Choose a different club');
    expect(retryButton).toBeInTheDocument();

    // Click dismiss → should go back to club list
    await act(async () => {
      fireEvent.click(retryButton);
    });

    // Club list should be visible again
    expect(screen.getByText('Select Your Club')).toBeInTheDocument();
    expect(screen.getByText('HD Club Amsterdam')).toBeInTheDocument();
  });
});
