/**
 * AuthProvider - Central authentication state management for H-DCN
 *
 * Single source of truth for auth state using Amplify v6's fetchAuthSession().
 * Listens to Hub auth events for real-time session updates.
 *
 * Requirements: R4.1, R4.2, R4.4, R9.1, R9.4, R9.5, R10.1, R10.2, R10.3
 */

import React, { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react';
import { fetchAuthSession, signOut as amplifySignOut } from 'aws-amplify/auth';
import { Hub } from 'aws-amplify/utils';
import { HDCNGroup } from '../types/user';

// --- Interfaces ---

export interface AuthUser {
  email: string;
  givenName?: string;
  familyName?: string;
  sub: string;
  groups: HDCNGroup[];
  accessToken: string;
}

export interface AuthContextType {
  user: AuthUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  error: string | null;
  signOut: () => Promise<void>;
}

// --- Constants ---

const COGNITO_DOMAIN = 'h-dcn-auth-506221081911.auth.eu-west-1.amazoncognito.com';
const CLIENT_ID = '6jhvk853b0lfg9q1m861qs0cug';

// --- Context ---

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// --- Provider ---

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  /**
   * Extract user info from the current Amplify session tokens.
   * Groups come from accessToken payload, email/name from idToken payload.
   */
  const loadSession = useCallback(async () => {
    try {
      const session = await fetchAuthSession();

      if (!session.tokens) {
        // No session — user needs to log in
        setUser(null);
        setError(null);
        return;
      }

      const accessToken = session.tokens.accessToken;
      const idToken = session.tokens.idToken;

      if (!accessToken || !idToken) {
        setUser(null);
        setError(null);
        return;
      }

      const groups = (accessToken.payload?.['cognito:groups'] as HDCNGroup[] | undefined) ?? [];
      const email = idToken.payload?.email as string;
      const givenName = idToken.payload?.given_name as string | undefined;
      const familyName = idToken.payload?.family_name as string | undefined;
      const sub = accessToken.payload?.sub as string;

      if (!email || !sub) {
        setUser(null);
        setError('Invalid session: missing user identity.');
        return;
      }

      setUser({
        email,
        givenName,
        familyName,
        sub,
        groups,
        accessToken: accessToken.toString(),
      });
      setError(null);
    } catch (err) {
      console.error('AuthProvider: failed to load session', err);
      setUser(null);
      setError('Session expired. Please sign in again.');
    }
  }, []);

  /**
   * Sign out: clear local Amplify session, then redirect to Cognito hosted UI
   * logout endpoint to clear the Cognito session cookie (prevents auto-re-login
   * for Google SSO users).
   */
  const handleSignOut = useCallback(async () => {
    try {
      await amplifySignOut({ global: false });
    } catch (err) {
      console.error('AuthProvider: signOut error', err);
    }
    // Redirect to Cognito hosted UI logout to clear session cookie
    const logoutUri = encodeURIComponent(window.location.origin + '/');
    window.location.href = `https://${COGNITO_DOMAIN}/logout?client_id=${CLIENT_ID}&logout_uri=${logoutUri}`;
  }, []);

  // --- On mount: check for existing session ---
  useEffect(() => {
    const init = async () => {
      setIsLoading(true);
      await loadSession();
      setIsLoading(false);
    };
    init();
  }, [loadSession]);

  // --- Hub event listener ---
  useEffect(() => {
    const unsubscribe = Hub.listen('auth', ({ payload }) => {
      switch (payload.event) {
        case 'signedIn':
          // User just signed in (either path) — load session
          loadSession();
          break;

        case 'signedOut':
          // Session cleared locally
          setUser(null);
          setError(null);
          break;

        case 'tokenRefresh':
          // Tokens refreshed silently — update accessToken in state
          loadSession();
          break;

        case 'tokenRefresh_failure':
          // Token refresh failed — session is no longer valid
          setUser(null);
          setError('Session expired. Please sign in again.');
          break;

        case 'signInWithRedirect_failure':
          // OAuth callback error (user denied consent, Cognito rejected token)
          setUser(null);
          setError('Sign-in failed. Please try again.');
          break;

        default:
          break;
      }
    });

    return unsubscribe;
  }, [loadSession]);

  const value: AuthContextType = {
    user,
    isLoading,
    isAuthenticated: user !== null,
    error,
    signOut: handleSignOut,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

// --- Hook ---

/**
 * useAuth hook — access auth state from AuthProvider context.
 * Must be used within an <AuthProvider> tree.
 */
export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export { AuthContext };
