/**
 * DelegateManager component tests.
 *
 * Validates: Requirements 5.1, 5.2, 5.3, 5.5, 5.6, 5.7
 *
 * Tests cover:
 * - Primary delegate sees invite/revoke controls
 * - Non-primary delegate sees read-only view
 * - Inviting a secondary delegate via email (action='invite')
 * - Client-side self-invitation rejection
 * - Pending invitation state display
 * - Revoking pending invitation / removing secondary (draft only)
 * - Version conflict (409) handling with reload toast
 * - Revoke restricted to draft status only
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import DelegateManager from '../DelegateManager';
import { Order } from '../../types/presmeet.types';

// Mock the API functions
const mockManageDelegates = jest.fn();
const mockResendDelegateInvitation = jest.fn();
const mockIsVersionConflict = jest.fn();

jest.mock('../../services/presmeetApi', () => ({
  manageDelegates: (...args: any[]) => mockManageDelegates(...args),
  resendDelegateInvitation: (...args: any[]) => mockResendDelegateInvitation(...args),
  isVersionConflict: (...args: any[]) => mockIsVersionConflict(...args),
}));

// Mock react-i18next
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        'delegate_manager.title': 'Delegates',
        'delegate_manager.primary': 'Primary',
        'delegate_manager.secondary': 'Secondary',
        'delegate_manager.you': '(you)',
        'delegate_manager.no_secondary': 'No secondary delegate assigned',
        'delegate_manager.invite_button': 'Invite',
        'delegate_manager.remove_button': 'Remove',
        'delegate_manager.revoke_button': 'Revoke',
        'delegate_manager.removing': 'Removing...',
        'delegate_manager.revoking': 'Revoking...',
        'delegate_manager.pending': 'Pending',
        'delegate_manager.email_placeholder': 'Email address',
        'delegate_manager.add_description': 'Add a secondary delegate who can also manage this booking',
        'delegate_manager.error_self_invite': 'You cannot invite yourself as a secondary delegate',
        'delegate_manager.error_not_found': 'User not found. Please check the email address.',
        'delegate_manager.error_no_access': 'This user does not have event access.',
        'delegate_manager.error_already_assigned': 'This user is already assigned as a delegate.',
        'delegate_manager.error_generic': 'An unexpected error occurred. Please try again.',
        'delegate_manager.conflict_title': 'Order modified',
        'delegate_manager.conflict_description': 'This order was modified by another delegate. Please reload.',
        'delegate_manager.reload_button': 'Reload',
      };
      return translations[key] || key;
    },
    i18n: { language: 'nl', changeLanguage: jest.fn() },
  }),
}));

// Mock Chakra UI components
const mockToast = jest.fn();
jest.mock('@chakra-ui/react', () => ({
  Alert: ({ children, status }: any) => (
    <div role="alert" data-status={status}>{children}</div>
  ),
  AlertDescription: ({ children }: any) => <span>{children}</span>,
  AlertIcon: () => <span data-testid="alert-icon" />,
  Badge: ({ children, colorScheme }: any) => (
    <span data-testid={`badge-${colorScheme}`}>{children}</span>
  ),
  Box: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  Button: ({ children, onClick, isLoading, isDisabled, ...props }: any) => (
    <button onClick={onClick} disabled={isDisabled || isLoading} {...props}>
      {isLoading ? 'Loading...' : children}
    </button>
  ),
  HStack: ({ children }: any) => <div style={{ display: 'flex' }}>{children}</div>,
  Heading: ({ children }: any) => <h3>{children}</h3>,
  Input: ({ placeholder, value, onChange, onKeyDown, isDisabled, ...props }: any) => (
    <input
      placeholder={placeholder}
      value={value}
      onChange={onChange}
      onKeyDown={onKeyDown}
      disabled={isDisabled}
      data-testid="email-input"
      {...props}
    />
  ),
  InputGroup: ({ children }: any) => <div>{children}</div>,
  InputRightElement: ({ children }: any) => <div>{children}</div>,
  Text: ({ children, as, ...props }: any) => {
    const Tag = as || 'span';
    return <Tag {...props}>{children}</Tag>;
  },
  VStack: ({ children }: any) => <div>{children}</div>,
  useToast: () => mockToast,
}));

jest.mock('@chakra-ui/icons', () => ({
  DeleteIcon: () => <span data-testid="delete-icon" />,
  RepeatIcon: () => <span data-testid="repeat-icon" />,
}));

// --- Test data ---

function createOrder(overrides: Partial<Order> = {}): Order {
  return {
    order_id: 'order-123',
    source_id: 'event-pm2027',
    member_id: 'member-1',
    club_id: 'club-amsterdam',
    event_id: 'event-pm2027',
    event_type: 'presmeet',
    status: 'draft',
    payment_status: 'unpaid',
    total_amount: 150.0,
    total_paid: 0,
    items: [],
    delegates: {
      primary: 'jan@club.nl',
      secondary: null,
      primary_member_id: 'member-1',
    },
    version: 1,
    status_history: [],
    created_at: '2027-01-10T08:00:00Z',
    updated_at: '2027-01-10T08:00:00Z',
    submitted_at: null,
    created_by: 'jan@club.nl',
    ...overrides,
  };
}

describe('DelegateManager', () => {
  const onDelegateChange = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    mockIsVersionConflict.mockReturnValue(false);
  });

  describe('Display', () => {
    it('shows primary delegate with "(you)" label when current user is primary', () => {
      const order = createOrder();

      render(
        <DelegateManager
          order={order}
          currentUserEmail="jan@club.nl"
          onDelegateChange={onDelegateChange}
        />
      );

      expect(screen.getByText('Primary')).toBeInTheDocument();
      expect(screen.getByText('jan@club.nl')).toBeInTheDocument();
      expect(screen.getByText('(you)')).toBeInTheDocument();
    });

    it('shows "No secondary delegate assigned" when no secondary and no pending', () => {
      const order = createOrder();

      render(
        <DelegateManager
          order={order}
          currentUserEmail="jan@club.nl"
          onDelegateChange={onDelegateChange}
        />
      );

      expect(screen.getByText('No secondary delegate assigned')).toBeInTheDocument();
    });

    it('shows linked secondary delegate email', () => {
      const order = createOrder({
        delegates: {
          primary: 'jan@club.nl',
          secondary: 'piet@club.nl',
          primary_member_id: 'member-1',
          secondary_member_id: 'member-2',
        },
      });

      render(
        <DelegateManager
          order={order}
          currentUserEmail="jan@club.nl"
          onDelegateChange={onDelegateChange}
        />
      );

      expect(screen.getByText('piet@club.nl')).toBeInTheDocument();
    });

    it('shows pending invitation state with "Pending" badge', () => {
      const order = createOrder({
        delegates: {
          primary: 'jan@club.nl',
          secondary: null,
          primary_member_id: 'member-1',
          pending_secondary_email: 'piet@club.nl',
        },
      });

      render(
        <DelegateManager
          order={order}
          currentUserEmail="jan@club.nl"
          onDelegateChange={onDelegateChange}
        />
      );

      expect(screen.getByText('piet@club.nl')).toBeInTheDocument();
      expect(screen.getByText('Pending')).toBeInTheDocument();
      expect(screen.getByTestId('badge-yellow')).toBeInTheDocument();
    });
  });

  describe('Primary delegate controls', () => {
    it('shows invite input when primary and no secondary exists', () => {
      const order = createOrder();

      render(
        <DelegateManager
          order={order}
          currentUserEmail="jan@club.nl"
          onDelegateChange={onDelegateChange}
        />
      );

      expect(screen.getByTestId('email-input')).toBeInTheDocument();
      expect(screen.getByText('Invite')).toBeInTheDocument();
    });

    it('shows remove button when primary, draft status, and secondary exists', () => {
      const order = createOrder({
        delegates: {
          primary: 'jan@club.nl',
          secondary: 'piet@club.nl',
          primary_member_id: 'member-1',
          secondary_member_id: 'member-2',
        },
      });

      render(
        <DelegateManager
          order={order}
          currentUserEmail="jan@club.nl"
          onDelegateChange={onDelegateChange}
        />
      );

      expect(screen.getByText('Remove')).toBeInTheDocument();
    });

    it('shows revoke button when primary, draft status, and pending invitation', () => {
      const order = createOrder({
        delegates: {
          primary: 'jan@club.nl',
          secondary: null,
          primary_member_id: 'member-1',
          pending_secondary_email: 'piet@club.nl',
        },
      });

      render(
        <DelegateManager
          order={order}
          currentUserEmail="jan@club.nl"
          onDelegateChange={onDelegateChange}
        />
      );

      expect(screen.getByText('Revoke')).toBeInTheDocument();
    });

    it('does not show invite input when pending invitation exists', () => {
      const order = createOrder({
        delegates: {
          primary: 'jan@club.nl',
          secondary: null,
          primary_member_id: 'member-1',
          pending_secondary_email: 'piet@club.nl',
        },
      });

      render(
        <DelegateManager
          order={order}
          currentUserEmail="jan@club.nl"
          onDelegateChange={onDelegateChange}
        />
      );

      expect(screen.queryByTestId('email-input')).not.toBeInTheDocument();
    });

    it('does not show invite input when secondary is already linked', () => {
      const order = createOrder({
        delegates: {
          primary: 'jan@club.nl',
          secondary: 'piet@club.nl',
          primary_member_id: 'member-1',
          secondary_member_id: 'member-2',
        },
      });

      render(
        <DelegateManager
          order={order}
          currentUserEmail="jan@club.nl"
          onDelegateChange={onDelegateChange}
        />
      );

      expect(screen.queryByTestId('email-input')).not.toBeInTheDocument();
    });
  });

  describe('Draft-only restriction (Req 5.7)', () => {
    it('does not show remove button when order is submitted', () => {
      const order = createOrder({
        status: 'submitted',
        delegates: {
          primary: 'jan@club.nl',
          secondary: 'piet@club.nl',
          primary_member_id: 'member-1',
          secondary_member_id: 'member-2',
        },
      });

      render(
        <DelegateManager
          order={order}
          currentUserEmail="jan@club.nl"
          onDelegateChange={onDelegateChange}
        />
      );

      expect(screen.queryByText('Remove')).not.toBeInTheDocument();
    });

    it('does not show revoke button when order is locked', () => {
      const order = createOrder({
        status: 'locked',
        delegates: {
          primary: 'jan@club.nl',
          secondary: null,
          primary_member_id: 'member-1',
          pending_secondary_email: 'piet@club.nl',
        },
      });

      render(
        <DelegateManager
          order={order}
          currentUserEmail="jan@club.nl"
          onDelegateChange={onDelegateChange}
        />
      );

      expect(screen.queryByText('Revoke')).not.toBeInTheDocument();
    });
  });

  describe('Non-primary (read-only)', () => {
    it('does not show invite input for non-primary user', () => {
      const order = createOrder();

      render(
        <DelegateManager
          order={order}
          currentUserEmail="piet@club.nl"
          onDelegateChange={onDelegateChange}
        />
      );

      expect(screen.queryByTestId('email-input')).not.toBeInTheDocument();
    });

    it('does not show remove button for non-primary user', () => {
      const order = createOrder({
        delegates: {
          primary: 'jan@club.nl',
          secondary: 'piet@club.nl',
          primary_member_id: 'member-1',
          secondary_member_id: 'member-2',
        },
      });

      render(
        <DelegateManager
          order={order}
          currentUserEmail="piet@club.nl"
          onDelegateChange={onDelegateChange}
        />
      );

      expect(screen.queryByText('Remove')).not.toBeInTheDocument();
    });
  });

  describe('Invite delegate (Req 5.1)', () => {
    it('calls manageDelegates with invite action and email on button click', async () => {
      const order = createOrder();
      mockManageDelegates.mockResolvedValue({ order });

      render(
        <DelegateManager
          order={order}
          currentUserEmail="jan@club.nl"
          onDelegateChange={onDelegateChange}
        />
      );

      const input = screen.getByTestId('email-input');
      fireEvent.change(input, { target: { value: 'piet@club.nl' } });

      await act(async () => {
        fireEvent.click(screen.getByText('Invite'));
      });

      expect(mockManageDelegates).toHaveBeenCalledWith('order-123', {
        action: 'invite',
        email: 'piet@club.nl',
      });
      expect(onDelegateChange).toHaveBeenCalled();
    });

    it('calls manageDelegates on Enter key press', async () => {
      const order = createOrder();
      mockManageDelegates.mockResolvedValue({ order });

      render(
        <DelegateManager
          order={order}
          currentUserEmail="jan@club.nl"
          onDelegateChange={onDelegateChange}
        />
      );

      const input = screen.getByTestId('email-input');
      fireEvent.change(input, { target: { value: 'piet@club.nl' } });

      await act(async () => {
        fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });
      });

      expect(mockManageDelegates).toHaveBeenCalledWith('order-123', {
        action: 'invite',
        email: 'piet@club.nl',
      });
    });

    it('clears email input after successful invite', async () => {
      const order = createOrder();
      mockManageDelegates.mockResolvedValue({ order });

      render(
        <DelegateManager
          order={order}
          currentUserEmail="jan@club.nl"
          onDelegateChange={onDelegateChange}
        />
      );

      const input = screen.getByTestId('email-input');
      fireEvent.change(input, { target: { value: 'piet@club.nl' } });

      await act(async () => {
        fireEvent.click(screen.getByText('Invite'));
      });

      expect(input).toHaveValue('');
    });

    it('does not submit when email is empty', async () => {
      const order = createOrder();

      render(
        <DelegateManager
          order={order}
          currentUserEmail="jan@club.nl"
          onDelegateChange={onDelegateChange}
        />
      );

      await act(async () => {
        fireEvent.click(screen.getByText('Invite'));
      });

      expect(mockManageDelegates).not.toHaveBeenCalled();
    });
  });

  describe('Self-invitation rejection (Req 5.2)', () => {
    it('rejects self-invitation client-side without calling API', async () => {
      const order = createOrder();

      render(
        <DelegateManager
          order={order}
          currentUserEmail="jan@club.nl"
          onDelegateChange={onDelegateChange}
        />
      );

      const input = screen.getByTestId('email-input');
      fireEvent.change(input, { target: { value: 'jan@club.nl' } });

      await act(async () => {
        fireEvent.click(screen.getByText('Invite'));
      });

      expect(mockManageDelegates).not.toHaveBeenCalled();
      expect(screen.getByText('You cannot invite yourself as a secondary delegate')).toBeInTheDocument();
    });

    it('rejects self-invitation case-insensitively', async () => {
      const order = createOrder();

      render(
        <DelegateManager
          order={order}
          currentUserEmail="jan@club.nl"
          onDelegateChange={onDelegateChange}
        />
      );

      const input = screen.getByTestId('email-input');
      fireEvent.change(input, { target: { value: 'JAN@CLUB.NL' } });

      await act(async () => {
        fireEvent.click(screen.getByText('Invite'));
      });

      expect(mockManageDelegates).not.toHaveBeenCalled();
      expect(screen.getByText('You cannot invite yourself as a secondary delegate')).toBeInTheDocument();
    });
  });

  describe('Revoke delegate (Req 5.7)', () => {
    it('calls manageDelegates with revoke action on revoke button click', async () => {
      const order = createOrder({
        delegates: {
          primary: 'jan@club.nl',
          secondary: null,
          primary_member_id: 'member-1',
          pending_secondary_email: 'piet@club.nl',
        },
      });
      mockManageDelegates.mockResolvedValue({ order });

      render(
        <DelegateManager
          order={order}
          currentUserEmail="jan@club.nl"
          onDelegateChange={onDelegateChange}
        />
      );

      await act(async () => {
        fireEvent.click(screen.getByText('Revoke'));
      });

      expect(mockManageDelegates).toHaveBeenCalledWith('order-123', {
        action: 'revoke',
      });
      expect(onDelegateChange).toHaveBeenCalled();
    });

    it('calls manageDelegates with revoke action on remove button click', async () => {
      const order = createOrder({
        delegates: {
          primary: 'jan@club.nl',
          secondary: 'piet@club.nl',
          primary_member_id: 'member-1',
          secondary_member_id: 'member-2',
        },
      });
      mockManageDelegates.mockResolvedValue({ order });

      render(
        <DelegateManager
          order={order}
          currentUserEmail="jan@club.nl"
          onDelegateChange={onDelegateChange}
        />
      );

      await act(async () => {
        fireEvent.click(screen.getByText('Remove'));
      });

      expect(mockManageDelegates).toHaveBeenCalledWith('order-123', {
        action: 'revoke',
      });
      expect(onDelegateChange).toHaveBeenCalled();
    });
  });

  describe('Version conflict handling (Req 5.6)', () => {
    it('shows toast on 409 version conflict during invite', async () => {
      const order = createOrder();
      const conflictError = {
        type: 'VERSION_CONFLICT',
        message: 'Version conflict',
        current_version: 5,
      };
      mockIsVersionConflict.mockReturnValue(true);
      mockManageDelegates.mockRejectedValue(conflictError);

      render(
        <DelegateManager
          order={order}
          currentUserEmail="jan@club.nl"
          onDelegateChange={onDelegateChange}
        />
      );

      const input = screen.getByTestId('email-input');
      fireEvent.change(input, { target: { value: 'piet@club.nl' } });

      await act(async () => {
        fireEvent.click(screen.getByText('Invite'));
      });

      expect(mockToast).toHaveBeenCalled();
      expect(onDelegateChange).not.toHaveBeenCalled();
    });

    it('shows toast on 409 version conflict during revoke', async () => {
      const order = createOrder({
        delegates: {
          primary: 'jan@club.nl',
          secondary: null,
          primary_member_id: 'member-1',
          pending_secondary_email: 'piet@club.nl',
        },
      });
      const conflictError = {
        type: 'VERSION_CONFLICT',
        message: 'Version conflict',
        current_version: 5,
      };
      mockIsVersionConflict.mockReturnValue(true);
      mockManageDelegates.mockRejectedValue(conflictError);

      render(
        <DelegateManager
          order={order}
          currentUserEmail="jan@club.nl"
          onDelegateChange={onDelegateChange}
        />
      );

      await act(async () => {
        fireEvent.click(screen.getByText('Revoke'));
      });

      expect(mockToast).toHaveBeenCalled();
      expect(onDelegateChange).not.toHaveBeenCalled();
    });
  });

  describe('Error handling', () => {
    it('shows server error message on 400 response', async () => {
      const order = createOrder();
      mockManageDelegates.mockRejectedValue({
        response: { status: 400, data: { message: 'Already assigned' } },
      });

      render(
        <DelegateManager
          order={order}
          currentUserEmail="jan@club.nl"
          onDelegateChange={onDelegateChange}
        />
      );

      const input = screen.getByTestId('email-input');
      fireEvent.change(input, { target: { value: 'someone@club.nl' } });

      await act(async () => {
        fireEvent.click(screen.getByText('Invite'));
      });

      expect(screen.getByText('Already assigned')).toBeInTheDocument();
    });

    it('clears error when user types in input', async () => {
      const order = createOrder();
      mockManageDelegates.mockRejectedValueOnce({
        response: { status: 404, data: { message: 'User not found' } },
      });

      render(
        <DelegateManager
          order={order}
          currentUserEmail="jan@club.nl"
          onDelegateChange={onDelegateChange}
        />
      );

      const input = screen.getByTestId('email-input');
      fireEvent.change(input, { target: { value: 'bad@club.nl' } });

      await act(async () => {
        fireEvent.click(screen.getByText('Invite'));
      });

      expect(screen.getByText('User not found')).toBeInTheDocument();

      // Typing clears error
      fireEvent.change(input, { target: { value: 'good@club.nl' } });
      expect(screen.queryByText('User not found')).not.toBeInTheDocument();
    });
  });

  describe('Case-insensitive email comparison', () => {
    it('treats uppercase user email as primary', () => {
      const order = createOrder({
        delegates: { primary: 'jan@club.nl', secondary: null, primary_member_id: 'member-1' },
      });

      render(
        <DelegateManager
          order={order}
          currentUserEmail="JAN@CLUB.NL"
          onDelegateChange={onDelegateChange}
        />
      );

      expect(screen.getByText('(you)')).toBeInTheDocument();
      expect(screen.getByTestId('email-input')).toBeInTheDocument();
    });
  });

  describe('No delegates', () => {
    it('renders nothing when order has no delegates field', () => {
      const order = createOrder({ delegates: undefined });

      const { container } = render(
        <DelegateManager
          order={order}
          currentUserEmail="jan@club.nl"
          onDelegateChange={onDelegateChange}
        />
      );

      expect(container.firstChild).toBeNull();
    });
  });
});
