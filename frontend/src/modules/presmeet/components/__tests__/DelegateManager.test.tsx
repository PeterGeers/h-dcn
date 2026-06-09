/**
 * DelegateManager component tests.
 *
 * Validates: Requirements 12.6, 12.7, 12.8
 *
 * Tests cover:
 * - Primary delegate sees add/remove controls
 * - Non-primary delegate sees read-only view
 * - Adding a secondary delegate via email
 * - Removing a secondary delegate
 * - Error display for API failures (404, 403, 400)
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import DelegateManager from '../DelegateManager';
import { Order } from '../../types/presmeet.types';

// Mock the manageDelegates function from the API client
const mockManageDelegates = jest.fn();

jest.mock('../../services/presmeetApi', () => ({
  manageDelegates: (...args: any[]) => mockManageDelegates(...args),
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
        'delegate_manager.add_button': 'Add',
        'delegate_manager.remove_button': 'Remove',
        'delegate_manager.removing': 'Removing...',
        'delegate_manager.email_placeholder': 'Email address',
        'delegate_manager.add_description': 'Add a secondary delegate who can also manage this booking',
      };
      return translations[key] || key;
    },
    i18n: { language: 'nl', changeLanguage: jest.fn() },
  }),
}));

// Mock Chakra UI components
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
}));

jest.mock('@chakra-ui/icons', () => ({
  DeleteIcon: () => <span data-testid="delete-icon" />,
}));

// --- Test data ---

function createOrder(overrides: Partial<Order> = {}): Order {
  return {
    order_id: 'order-123',
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

    it('shows "No secondary delegate assigned" when secondary is null', () => {
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

    it('shows secondary delegate email when one is assigned', () => {
      const order = createOrder({
        delegates: { primary: 'jan@club.nl', secondary: 'piet@club.nl' },
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
  });

  describe('Primary delegate controls', () => {
    it('shows add input when primary and no secondary exists', () => {
      const order = createOrder();

      render(
        <DelegateManager
          order={order}
          currentUserEmail="jan@club.nl"
          onDelegateChange={onDelegateChange}
        />
      );

      expect(screen.getByTestId('email-input')).toBeInTheDocument();
      expect(screen.getByText('Add')).toBeInTheDocument();
    });

    it('shows remove button when primary and secondary exists', () => {
      const order = createOrder({
        delegates: { primary: 'jan@club.nl', secondary: 'piet@club.nl' },
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

    it('does not show add input when secondary is already assigned', () => {
      const order = createOrder({
        delegates: { primary: 'jan@club.nl', secondary: 'piet@club.nl' },
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

  describe('Non-primary (read-only)', () => {
    it('does not show add input for non-primary user', () => {
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
        delegates: { primary: 'jan@club.nl', secondary: 'piet@club.nl' },
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

    it('does not show "(you)" for non-primary user on primary label', () => {
      const order = createOrder();

      render(
        <DelegateManager
          order={order}
          currentUserEmail="piet@club.nl"
          onDelegateChange={onDelegateChange}
        />
      );

      expect(screen.queryByText('(you)')).not.toBeInTheDocument();
    });
  });

  describe('Add delegate', () => {
    it('calls manageDelegates with add action and email on button click', async () => {
      const order = createOrder();
      mockManageDelegates.mockResolvedValue({
        ...order,
        delegates: { primary: 'jan@club.nl', secondary: 'piet@club.nl' },
      });

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
        fireEvent.click(screen.getByText('Add'));
      });

      expect(mockManageDelegates).toHaveBeenCalledWith('order-123', {
        action: 'add',
        email: 'piet@club.nl',
      });
      expect(onDelegateChange).toHaveBeenCalled();
    });

    it('calls manageDelegates on Enter key press', async () => {
      const order = createOrder();
      mockManageDelegates.mockResolvedValue(order);

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
        action: 'add',
        email: 'piet@club.nl',
      });
    });

    it('clears email input after successful add', async () => {
      const order = createOrder();
      mockManageDelegates.mockResolvedValue(order);

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
        fireEvent.click(screen.getByText('Add'));
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
        fireEvent.click(screen.getByText('Add'));
      });

      expect(mockManageDelegates).not.toHaveBeenCalled();
    });
  });

  describe('Remove delegate', () => {
    it('calls manageDelegates with remove action on button click', async () => {
      const order = createOrder({
        delegates: { primary: 'jan@club.nl', secondary: 'piet@club.nl' },
      });
      mockManageDelegates.mockResolvedValue({
        ...order,
        delegates: { primary: 'jan@club.nl', secondary: null },
      });

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
        action: 'remove',
      });
      expect(onDelegateChange).toHaveBeenCalled();
    });
  });

  describe('Error handling', () => {
    it('shows "User not found" error on 404 response', async () => {
      const order = createOrder();
      mockManageDelegates.mockRejectedValue({
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
      fireEvent.change(input, { target: { value: 'nobody@club.nl' } });

      await act(async () => {
        fireEvent.click(screen.getByText('Add'));
      });

      expect(screen.getByText('User not found')).toBeInTheDocument();
      expect(onDelegateChange).not.toHaveBeenCalled();
    });

    it('shows "No PresMeet access" error on 403 response', async () => {
      const order = createOrder();
      mockManageDelegates.mockRejectedValue({
        response: { status: 403, data: { message: 'No PresMeet access' } },
      });

      render(
        <DelegateManager
          order={order}
          currentUserEmail="jan@club.nl"
          onDelegateChange={onDelegateChange}
        />
      );

      const input = screen.getByTestId('email-input');
      fireEvent.change(input, { target: { value: 'noaccess@club.nl' } });

      await act(async () => {
        fireEvent.click(screen.getByText('Add'));
      });

      expect(screen.getByText('No PresMeet access')).toBeInTheDocument();
    });

    it('shows "Already assigned" error on 400 response', async () => {
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
      fireEvent.change(input, { target: { value: 'jan@club.nl' } });

      await act(async () => {
        fireEvent.click(screen.getByText('Add'));
      });

      expect(screen.getByText('Already assigned')).toBeInTheDocument();
    });

    it('clears error on next successful action', async () => {
      const order = createOrder();

      // First call fails
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
        fireEvent.click(screen.getByText('Add'));
      });

      expect(screen.getByText('User not found')).toBeInTheDocument();

      // Second call succeeds
      mockManageDelegates.mockResolvedValueOnce(order);
      fireEvent.change(input, { target: { value: 'good@club.nl' } });

      await act(async () => {
        fireEvent.click(screen.getByText('Add'));
      });

      expect(screen.queryByText('User not found')).not.toBeInTheDocument();
    });
  });

  describe('Case-insensitive email comparison', () => {
    it('treats uppercase user email as primary', () => {
      const order = createOrder({
        delegates: { primary: 'jan@club.nl', secondary: null },
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
});
