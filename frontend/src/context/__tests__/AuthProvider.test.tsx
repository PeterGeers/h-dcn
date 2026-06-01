/**
 * Unit tests for AuthProvider
 *
 * Tests the central authentication state management component.
 * Validates: Requirements R4.1, R4.2, R9.1, R9.4, R10.1, R10.2
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { AuthProvider, useAuth, AuthContextType } from '../AuthProvider';

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
function getHubCallback(): (data: { payload: { event: string; data?: any } }) => void {
  const lastCall = mockHubListen.mock.calls[mockHubListen.mock.calls.length - 1];
  if (!lastCall) throw new Error('Hub.listen was not called');
  return lastCall[1]; // second argument is the callback
}

// --- Test helper ---

function TestConsumer() {
  const auth: AuthContextType = useAuth();
  return (
    <div>
      <span data-testid="user">{auth.user ? JSON.stringify(auth.user) : 'null'}</span>
      <span data-testid="isLoading">{String(auth.isLoading)}</span>
      <span data-testid="isAuthenticated">{String(auth.isAuthenticated)}</span>
      <span data-testid="error">{auth.error ?? 'null'}</span>
      <button data-testid="signout-btn" onClick={auth.signOut}>Sign Out</button>
    </div>
  );
}

function renderWithProvider() {
  return render(
    <AuthProvider>
      <TestConsumer />
    </AuthProvider>
  );
}

// --- Helper to create a mock session ---

function createMockSession({
  email = 'user@h-dcn.nl',
  sub = 'abc-123',
  groups = ['hdcnLeden'] as string[],
  givenName = 'Jan',
  familyName = 'de Vries',
  accessTokenStr = 'mock-access-token-jwt',
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

// --- Tests ---

describe('AuthProvider', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockHubListen.mockReturnValue(() => {}); // unsubscribe noop
    // Reset window.location.href
    Object.defineProperty(window, 'location', {
      value: { href: 'http://localhost:3000', origin: 'http://localhost:3000' },
      writable: true,
    });
  });

  describe('mount with no session', () => {
    it('sets user to null and isLoading to false when no session exists', async () => {
      mockFetchAuthSession.mockResolvedValue({ tokens: undefined } as any);

      renderWithProvider();

      // Initially loading
      expect(screen.getByTestId('isLoading')).toHaveTextContent('true');

      await waitFor(() => {
        expect(screen.getByTestId('isLoading')).toHaveTextContent('false');
      });

      expect(screen.getByTestId('user')).toHaveTextContent('null');
      expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('false');
      expect(screen.getByTestId('error')).toHaveTextContent('null');
    });
  });

  describe('mount with valid session', () => {
    it('extracts email, groups, and accessToken correctly from session tokens', async () => {
      const mockSession = createMockSession({
        email: 'webmaster@h-dcn.nl',
        sub: 'user-sub-456',
        groups: ['hdcnLeden', 'Members_CRUD', 'Regio_All'],
        givenName: 'Pieter',
        familyName: 'Bakker',
        accessTokenStr: 'jwt-token-xyz',
      });
      mockFetchAuthSession.mockResolvedValue(mockSession as any);

      renderWithProvider();

      await waitFor(() => {
        expect(screen.getByTestId('isLoading')).toHaveTextContent('false');
      });

      const userJson = screen.getByTestId('user').textContent!;
      const user = JSON.parse(userJson);

      expect(user.email).toBe('webmaster@h-dcn.nl');
      expect(user.sub).toBe('user-sub-456');
      expect(user.groups).toEqual(['hdcnLeden', 'Members_CRUD', 'Regio_All']);
      expect(user.givenName).toBe('Pieter');
      expect(user.familyName).toBe('Bakker');
      expect(user.accessToken).toBe('jwt-token-xyz');
      expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('true');
    });
  });

  describe('Hub signedIn event', () => {
    it('fetches session and sets user when signedIn event fires', async () => {
      // Start with no session
      mockFetchAuthSession.mockResolvedValueOnce({ tokens: undefined } as any);

      renderWithProvider();

      await waitFor(() => {
        expect(screen.getByTestId('isLoading')).toHaveTextContent('false');
      });

      expect(screen.getByTestId('user')).toHaveTextContent('null');

      // Now simulate a signedIn event with a valid session
      const mockSession = createMockSession();
      mockFetchAuthSession.mockResolvedValueOnce(mockSession as any);

      const hubCb = getHubCallback();
      act(() => {
        hubCb({ payload: { event: 'signedIn' } });
      });

      await waitFor(() => {
        const userJson = screen.getByTestId('user').textContent!;
        expect(userJson).not.toBe('null');
      });

      const user = JSON.parse(screen.getByTestId('user').textContent!);
      expect(user.email).toBe('user@h-dcn.nl');
      expect(user.groups).toEqual(['hdcnLeden']);
      expect(user.accessToken).toBe('mock-access-token-jwt');
    });
  });

  describe('Hub tokenRefresh_failure event', () => {
    it('clears user and sets error message when token refresh fails', async () => {
      // Start with a valid session
      const mockSession = createMockSession();
      mockFetchAuthSession.mockResolvedValueOnce(mockSession as any);

      renderWithProvider();

      await waitFor(() => {
        expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('true');
      });

      // Simulate tokenRefresh_failure
      const hubCb = getHubCallback();
      act(() => {
        hubCb({ payload: { event: 'tokenRefresh_failure' } });
      });

      await waitFor(() => {
        expect(screen.getByTestId('user')).toHaveTextContent('null');
        expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('false');
        expect(screen.getByTestId('error')).toHaveTextContent('Session expired. Please sign in again.');
      });
    });
  });

  describe('Hub signInWithRedirect_failure event', () => {
    it('sets error state with user-friendly message when OAuth sign-in fails', async () => {
      // Start with no session
      mockFetchAuthSession.mockResolvedValueOnce({ tokens: undefined } as any);

      renderWithProvider();

      await waitFor(() => {
        expect(screen.getByTestId('isLoading')).toHaveTextContent('false');
      });

      // Simulate signInWithRedirect_failure (OAuth callback error)
      const hubCb = getHubCallback();
      act(() => {
        hubCb({ payload: { event: 'signInWithRedirect_failure' } });
      });

      await waitFor(() => {
        expect(screen.getByTestId('user')).toHaveTextContent('null');
        expect(screen.getByTestId('error')).toHaveTextContent('Sign-in failed. Please try again.');
      });
    });
  });

  describe('signOut()', () => {
    it('calls Amplify signOut and redirects to Cognito logout endpoint', async () => {
      const mockSession = createMockSession();
      mockFetchAuthSession.mockResolvedValueOnce(mockSession as any);
      mockSignOut.mockResolvedValue(undefined as any);

      renderWithProvider();

      await waitFor(() => {
        expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('true');
      });

      // Click sign out
      await act(async () => {
        screen.getByTestId('signout-btn').click();
      });

      // Verify Amplify signOut was called with global: false
      expect(mockSignOut).toHaveBeenCalledWith({ global: false });

      // Verify redirect to Cognito hosted UI logout
      expect(window.location.href).toContain(
        'https://h-dcn-auth-506221081911.auth.eu-west-1.amazoncognito.com/logout'
      );
      expect(window.location.href).toContain('client_id=6jhvk853b0lfg9q1m861qs0cug');
      expect(window.location.href).toContain('logout_uri=');
    });
  });

  describe('useAuth hook outside provider', () => {
    it('throws an error when used outside AuthProvider', () => {
      // Suppress console.error for this test since React will log the error
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

      expect(() => {
        render(<TestConsumer />);
      }).toThrow('useAuth must be used within an AuthProvider');

      consoleSpy.mockRestore();
    });
  });
});
