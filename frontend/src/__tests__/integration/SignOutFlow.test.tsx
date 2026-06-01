/**
 * Integration test for sign-out flow
 *
 * Tests the complete sign-out lifecycle:
 * 1. Start with an authenticated user (valid session)
 * 2. Call signOut from the auth context
 * 3. Verify Amplify's signOut was called with { global: false }
 * 4. Verify redirect to Cognito hosted UI logout URL
 * 5. After sign-out, verify user state is null (no auto-re-auth)
 *
 * Requirements: R10.1, R10.2, R10.3
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { AuthProvider, useAuth } from '../../context/AuthProvider';

// --- Mocks ---

const mockFetchAuthSession = jest.fn();
const mockSignOut = jest.fn();
const mockHubListen = jest.fn();

jest.mock('aws-amplify/auth', () => ({
  fetchAuthSession: function() { return mockFetchAuthSession.apply(null, arguments); },
  signOut: function() { return mockSignOut.apply(null, arguments); },
}));

jest.mock('aws-amplify/utils', () => ({
  Hub: {
    listen: function() { return mockHubListen.apply(null, arguments); },
  },
}));

// --- Test consumer component ---

function SignOutTestConsumer() {
  const auth = useAuth();
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

function renderWithAuth() {
  return render(
    <AuthProvider>
      <SignOutTestConsumer />
    </AuthProvider>
  );
}

// --- Helper to create a mock authenticated session ---

function createAuthenticatedSession() {
  return {
    tokens: {
      accessToken: {
        payload: {
          'cognito:groups': ['hdcnLeden', 'Members_CRUD', 'Regio_Utrecht'],
          sub: 'user-sub-789',
        },
        toString: () => 'valid-access-token-jwt',
      },
      idToken: {
        payload: {
          email: 'lid@h-dcn.nl',
          given_name: 'Klaas',
          family_name: 'Jansen',
        },
      },
    },
  };
}

// Helper to get the captured Hub callback
function getHubCallback() {
  const lastCall = mockHubListen.mock.calls[mockHubListen.mock.calls.length - 1];
  if (!lastCall) throw new Error('Hub.listen was not called');
  return lastCall[1];
}

// --- Tests ---

describe('Sign-Out Flow Integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockHubListen.mockReturnValue(() => {}); // unsubscribe noop
    mockSignOut.mockResolvedValue(undefined);
    // Set up window.location mock
    Object.defineProperty(window, 'location', {
      value: { href: 'http://localhost:3000/dashboard', origin: 'http://localhost:3000' },
      writable: true,
    });
  });

  describe('Sign-out clears local session and redirects to Cognito hosted UI logout (R10.1, R10.2)', () => {
    it('calls Amplify signOut with { global: false } to clear local session', async () => {
      mockFetchAuthSession.mockResolvedValue(createAuthenticatedSession());

      renderWithAuth();

      // Wait for authenticated state
      await waitFor(() => {
        expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('true');
      });

      // Verify user is set before sign-out
      const userBefore = JSON.parse(screen.getByTestId('user').textContent!);
      expect(userBefore.email).toBe('lid@h-dcn.nl');
      expect(userBefore.groups).toEqual(['hdcnLeden', 'Members_CRUD', 'Regio_Utrecht']);

      // Trigger sign-out
      await act(async () => {
        screen.getByTestId('signout-btn').click();
      });

      // Verify Amplify signOut was called with global: false (R10.1)
      expect(mockSignOut).toHaveBeenCalledTimes(1);
      expect(mockSignOut).toHaveBeenCalledWith({ global: false });
    });

    it('redirects to Cognito hosted UI logout URL after clearing local session (R10.2)', async () => {
      mockFetchAuthSession.mockResolvedValue(createAuthenticatedSession());

      renderWithAuth();

      await waitFor(() => {
        expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('true');
      });

      // Trigger sign-out
      await act(async () => {
        screen.getByTestId('signout-btn').click();
      });

      // Verify redirect to Cognito hosted UI logout endpoint
      const locationHref = window.location.href;
      expect(locationHref).toContain(
        'https://h-dcn-auth-506221081911.auth.eu-west-1.amazoncognito.com/logout'
      );
      expect(locationHref).toContain('client_id=6jhvk853b0lfg9q1m861qs0cug');
      expect(locationHref).toContain('logout_uri=');
      // The logout_uri should be the encoded origin + /
      expect(locationHref).toContain(encodeURIComponent('http://localhost:3000/'));
    });

    it('sign-out still redirects even if Amplify signOut throws an error', async () => {
      mockFetchAuthSession.mockResolvedValue(createAuthenticatedSession());
      mockSignOut.mockRejectedValue(new Error('Network error during signOut'));

      // Suppress console.error for this test
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

      renderWithAuth();

      await waitFor(() => {
        expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('true');
      });

      // Trigger sign-out
      await act(async () => {
        screen.getByTestId('signout-btn').click();
      });

      // Even if signOut throws, redirect should still happen (graceful degradation)
      expect(window.location.href).toContain(
        'https://h-dcn-auth-506221081911.auth.eu-west-1.amazoncognito.com/logout'
      );

      consoleSpy.mockRestore();
    });
  });

  describe('After sign-out, user sees login page with no auto-re-auth (R10.3)', () => {
    it('user state is null after Hub signedOut event fires', async () => {
      mockFetchAuthSession.mockResolvedValue(createAuthenticatedSession());

      renderWithAuth();

      // Wait for authenticated state
      await waitFor(() => {
        expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('true');
      });

      // Simulate the Hub signedOut event (fired by Amplify after signOut completes)
      const hubCb = getHubCallback();
      act(() => {
        hubCb({ payload: { event: 'signedOut' } });
      });

      // After signedOut event, user should be null (no auto-re-auth)
      await waitFor(() => {
        expect(screen.getByTestId('user')).toHaveTextContent('null');
        expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('false');
      });
    });

    it('no automatic re-authentication occurs after sign-out', async () => {
      // Start authenticated
      mockFetchAuthSession.mockResolvedValueOnce(createAuthenticatedSession());

      renderWithAuth();

      await waitFor(() => {
        expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('true');
      });

      // Simulate signedOut Hub event
      const hubCb = getHubCallback();
      act(() => {
        hubCb({ payload: { event: 'signedOut' } });
      });

      await waitFor(() => {
        expect(screen.getByTestId('user')).toHaveTextContent('null');
      });

      // Verify fetchAuthSession is NOT called again after signedOut
      // (no auto-re-auth attempt)
      const callCountAfterSignOut = mockFetchAuthSession.mock.calls.length;

      // Wait a tick to ensure no async re-auth is triggered
      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 50));
      });

      expect(mockFetchAuthSession.mock.calls.length).toBe(callCountAfterSignOut);
      expect(screen.getByTestId('user')).toHaveTextContent('null');
      expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('false');
      expect(screen.getByTestId('error')).toHaveTextContent('null');
    });

    it('complete sign-out flow: authenticated → signOut → redirect + user cleared', async () => {
      mockFetchAuthSession.mockResolvedValue(createAuthenticatedSession());

      renderWithAuth();

      // Step 1: Verify user is authenticated
      await waitFor(() => {
        expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('true');
      });

      const user = JSON.parse(screen.getByTestId('user').textContent!);
      expect(user.email).toBe('lid@h-dcn.nl');
      expect(user.sub).toBe('user-sub-789');
      expect(user.accessToken).toBe('valid-access-token-jwt');

      // Step 2: Trigger sign-out
      await act(async () => {
        screen.getByTestId('signout-btn').click();
      });

      // Step 3: Verify Amplify signOut called correctly
      expect(mockSignOut).toHaveBeenCalledWith({ global: false });

      // Step 4: Verify redirect to Cognito logout
      expect(window.location.href).toContain(
        'h-dcn-auth-506221081911.auth.eu-west-1.amazoncognito.com/logout'
      );

      // Step 5: Simulate Hub signedOut event (would fire in real flow)
      const hubCb = getHubCallback();
      act(() => {
        hubCb({ payload: { event: 'signedOut' } });
      });

      // Step 6: Verify user is cleared — no auto-re-auth
      await waitFor(() => {
        expect(screen.getByTestId('user')).toHaveTextContent('null');
        expect(screen.getByTestId('isAuthenticated')).toHaveTextContent('false');
        expect(screen.getByTestId('error')).toHaveTextContent('null');
      });
    });
  });
});
