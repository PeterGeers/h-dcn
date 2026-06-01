/**
 * Integration test for session continuity
 *
 * Tests that the AuthProvider correctly maintains session state across
 * page refreshes and handles token refresh failures gracefully.
 *
 * Validates: Requirements R4.1, R4.4, R9.4
 *
 * - R4.1: Auth state comes from fetchAuthSession() — not from localStorage
 * - R4.4: Token refresh is handled automatically by Amplify
 * - R9.4: If fetchAuthSession() fails during an active session (token refresh failure),
 *          the user is redirected to login with a message
 */

import React from 'react';
import { render, screen, waitFor, act, cleanup } from '@testing-library/react';
import '@testing-library/jest-dom';
import { AuthProvider, useAuth, AuthContextType } from '../../context/AuthProvider';

// --- Mocks ---

const mockFetchAuthSession = jest.fn();
const mockSignOut = jest.fn();
const mockHubListen = jest.fn();

jest.mock('aws-amplify/auth', () => ({
  fetchAuthSession: (...args) => mockFetchAuthSession(...args),
  signOut: (...args) => mockSignOut(...args),
}));

jest.mock('aws-amplify/utils', () => ({
  Hub: {
    listen: (...args) => mockHubListen(...args),
  },
}));

// Helper to get the captured Hub callback
function getHubCallback() {
  const lastCall = mockHubListen.mock.calls[mockHubListen.mock.calls.length - 1];
  if (!lastCall) throw new Error('Hub.listen was not called');
  return lastCall[1];
}

// --- Test consumer component ---

function TestConsumer() {
  const auth = useAuth();
  return (
    <div>
      <span data-testid="user">{auth.user ? JSON.stringify(auth.user) : 'null'}</span>
      <span data-testid="isLoading">{String(auth.isLoading)}</span>
      <span data-testid="isAuthenticated">{String(auth.isAuthenticated)}</span>
      <span data-testid="error">{auth.error ?? 'null'}</span>
    </div>
  );
}

// --- Helper to create a mock session ---

function createMockSession({
  email = 'webmaster@h-dcn.nl',
  sub = 'user-sub-789',
  groups = ['hdcnLeden', 'Members_CRUD'],
  givenName = 'Pieter',
  familyName = 'Bakker',
  accessTokenStr = 'valid-access-token-jwt',
} = {}) {
  return {
    tokens: {
      accessToken: {
        payload: {
          'cognito:groups': groups,
          sub,
        },
        toString: () => accessTokenStr,
      },
      idToken: {
        payload: {
          email,
          given_name: givenName,
          family_name: familyName,
        },
      },
    },
  };
}

// --- Integration Tests ---

describe('Session Continuity Integration Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockHubListen.mockReturnValue(() => {}); // unsubscribe noop
    Object.defineProperty(window, 'location', {
      value: { href: 'http://localhost:3000', origin: 'http://localhost:3000' },
      writable: true,
    });
  });

  afterEach(() => {
    cleanup();
  });

  describe('Page refresh with valid session → user remains authenticated (R4.1, R4.4)', () => {
    it('maintains authentication across mount/unmount/remount (simulated page refresh)', async () => {
      const mockSession = createMockSession();

      // First mount: fetchAuthSession returns a valid session
      mockFetchAuthSession.mockResolvedValue(mockSession);

      const { unmount } = render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      );

      // Wait for initial session load
      await waitFor(() => {
        expect(screen.getByTestId('isLoading')).toHaveTextContent('false');
      });

      // Verify user is set after initial mount
      expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('true');
      const userJson = screen.getByTestId('user').textContent;
      const user = JSON.parse(userJson!);
      expect(user.email).toBe('webmaster@h-dcn.nl');
      expect(user.sub).toBe('user-sub-789');
      expect(user.groups).toEqual(['hdcnLeden', 'Members_CRUD']);
      expect(user.accessToken).toBe('valid-access-token-jwt');

      // Verify fetchAuthSession was called on mount
      expect(mockFetchAuthSession).toHaveBeenCalledTimes(1);

      // Unmount (simulates page navigation away or refresh start)
      unmount();

      // Remount (simulates page refresh completing — new component tree)
      // fetchAuthSession should be called again and return the same valid session
      mockFetchAuthSession.mockResolvedValue(mockSession);

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      );

      // Wait for session load on remount
      await waitFor(() => {
        expect(screen.getByTestId('isLoading')).toHaveTextContent('false');
      });

      // Verify fetchAuthSession was called again on remount
      expect(mockFetchAuthSession).toHaveBeenCalledTimes(2);

      // Verify user is still authenticated with the same data
      expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('true');
      const userJsonAfterRefresh = screen.getByTestId('user').textContent;
      const userAfterRefresh = JSON.parse(userJsonAfterRefresh!);
      expect(userAfterRefresh.email).toBe('webmaster@h-dcn.nl');
      expect(userAfterRefresh.sub).toBe('user-sub-789');
      expect(userAfterRefresh.groups).toEqual(['hdcnLeden', 'Members_CRUD']);
      expect(userAfterRefresh.accessToken).toBe('valid-access-token-jwt');
    });

    it('picks up refreshed tokens after page refresh (R4.4)', async () => {
      // First mount: original token
      const originalSession = createMockSession({
        accessTokenStr: 'original-token-v1',
      });
      mockFetchAuthSession.mockResolvedValue(originalSession);

      const { unmount } = render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('isLoading')).toHaveTextContent('false');
      });

      const user1 = JSON.parse(screen.getByTestId('user').textContent!);
      expect(user1.accessToken).toBe('original-token-v1');

      unmount();

      // Remount: Amplify has refreshed the token in the background
      const refreshedSession = createMockSession({
        accessTokenStr: 'refreshed-token-v2',
      });
      mockFetchAuthSession.mockResolvedValue(refreshedSession);

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('isLoading')).toHaveTextContent('false');
      });

      // User should have the refreshed token
      const user2 = JSON.parse(screen.getByTestId('user').textContent!);
      expect(user2.accessToken).toBe('refreshed-token-v2');
      expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('true');
    });
  });

  describe('Token refresh failure → user redirected to login with message (R9.4)', () => {
    it('clears user and sets error message on tokenRefresh_failure Hub event', async () => {
      // Start with a valid session
      const mockSession = createMockSession();
      mockFetchAuthSession.mockResolvedValue(mockSession);

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('true');
      });

      // Verify user is set
      const user = JSON.parse(screen.getByTestId('user').textContent!);
      expect(user.email).toBe('webmaster@h-dcn.nl');

      // Simulate Hub tokenRefresh_failure event
      // (Amplify fires this when it cannot refresh the expired token)
      const hubCallback = getHubCallback();
      act(() => {
        hubCallback({ payload: { event: 'tokenRefresh_failure' } });
      });

      // User should be cleared and error message set
      await waitFor(() => {
        expect(screen.getByTestId('user')).toHaveTextContent('null');
        expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('false');
        expect(screen.getByTestId('error')).toHaveTextContent('Session expired. Please sign in again.');
      });
    });

    it('handles fetchAuthSession throwing an error during session check', async () => {
      // fetchAuthSession throws (e.g., network error during token refresh)
      mockFetchAuthSession.mockRejectedValue(new Error('Network error'));

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('isLoading')).toHaveTextContent('false');
      });

      // User should be null with an error message
      expect(screen.getByTestId('user')).toHaveTextContent('null');
      expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('false');
      expect(screen.getByTestId('error')).toHaveTextContent('Session expired. Please sign in again.');
    });

    it('transitions from authenticated to unauthenticated on token refresh failure', async () => {
      // Start authenticated
      const mockSession = createMockSession();
      mockFetchAuthSession.mockResolvedValue(mockSession);

      render(
        <AuthProvider>
          <TestConsumer />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('true');
      });

      // Verify the full transition: authenticated → tokenRefresh_failure → unauthenticated with message
      expect(screen.getByTestId('error')).toHaveTextContent('null');

      const hubCallback = getHubCallback();
      act(() => {
        hubCallback({ payload: { event: 'tokenRefresh_failure' } });
      });

      await waitFor(() => {
        // All three conditions must be true simultaneously
        expect(screen.getByTestId('user')).toHaveTextContent('null');
        expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('false');
        expect(screen.getByTestId('error')).not.toHaveTextContent('null');
      });

      // Error message should be user-friendly (not a technical error)
      const errorText = screen.getByTestId('error').textContent;
      expect(errorText).toContain('Session expired');
      expect(errorText).toContain('sign in');
    });
  });
});
