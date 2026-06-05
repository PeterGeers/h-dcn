/**
 * Integration Test: Google SSO Flow
 *
 * Tests the full Google SSO authentication flow through AuthProvider + CustomAuthenticator:
 * 1. User clicks Google button → signInWithRedirect → Hub fires signedIn → AuthProvider loads session → user authenticated with groups
 * 2. User clicks Google button → OAuth fails → Hub fires signInWithRedirect_failure → error message shown on login page
 *
 * Requirements: R1.2, R1.3, R2.1, R2.2, R9.1
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock react-i18next
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, string>) => {
      const translations: Record<string, string> = {
        'login.title': 'Inloggen',
        'login.welcome': 'Welkom bij het H-DCN Portaal',
        'login.email_placeholder': 'Voer je e-mailadres in',
        'login.passkey_button': 'Inloggen met Passkey',
        'login.google_button': 'Inloggen met Google',
        'login.loading': 'Inloggen...',
        'login.or_use': 'of gebruik',
        'login.advanced_options': 'Geavanceerde opties',
        'login.setup_new_passkey': 'Nieuwe Passkey Instellen',
        'login.debug_passkey': 'Debug Passkey Problemen',
        'errors.network': 'Netwerkfout. Controleer je verbinding en probeer opnieuw.',
        'errors.code_expired': 'Code verlopen. Vraag een nieuwe code aan.',
        'errors.login_failed': 'Inloggen mislukt. Probeer opnieuw.',
        'errors.google_sso': 'Google SSO fout: {{error}}',
        'errors.step_required': 'Extra stap vereist: {{step}}',
        'verification.enter_code': 'Voer de verificatiecode in die naar je e-mail is gestuurd:',
        'verification.resend_code': 'Nieuwe code versturen',
        'verification.sending': 'Versturen...',
        'info.title': 'Authenticatie Informatie',
        'info.passkey_title': 'Passkey (aanbevolen)',
        'info.passkey_desc': 'Veilig inloggen met vingerafdruk, gezichtsherkenning, of apparaat-PIN',
        'signup.title': 'Account Aanmaken',
        'signup.back_to_login': 'Terug naar inloggen',
      };
      let value = translations[key] || key;
      if (params) {
        Object.entries(params).forEach(([k, v]) => {
          value = value.replace(`{{${k}}}`, v);
        });
      }
      return value;
    },
    i18n: { language: 'nl', changeLanguage: jest.fn() },
  }),
}));

// --- Mock aws-amplify/auth ---
const mockSignInWithRedirect = jest.fn();
const mockFetchAuthSession = jest.fn();
const mockSignOut = jest.fn();

jest.mock('aws-amplify/auth', () => ({
  signInWithRedirect: (...args) => mockSignInWithRedirect(...args),
  fetchAuthSession: (...args) => mockFetchAuthSession(...args),
  signOut: (...args) => mockSignOut(...args),
  signIn: jest.fn(),
  confirmSignIn: jest.fn(),
}));

// --- Mock aws-amplify/utils (Hub) ---
let hubAuthCallback = null;

jest.mock('aws-amplify/utils', () => ({
  Hub: {
    listen: (channel, callback) => {
      if (channel === 'auth') {
        hubAuthCallback = callback;
      }
      // Return unsubscribe function
      return () => {
        hubAuthCallback = null;
      };
    },
  },
}));

// --- Mock Chakra UI ---
jest.mock('@chakra-ui/react', () => ({
  Box: (props) => <div {...props}>{props.children}</div>,
  Button: (props) => (
    <button onClick={props.onClick} disabled={props.isDisabled || props.isLoading} type={props.type} data-testid={props['data-testid']}>
      {props.isLoading ? props.loadingText : props.children}
    </button>
  ),
  FormControl: (props) => <div>{props.children}</div>,
  Input: (props) => (
    <input onChange={props.onChange} value={props.value} placeholder={props.placeholder} name={props.name} type={props.type} />
  ),
  VStack: (props) => <div>{props.children}</div>,
  HStack: (props) => <div>{props.children}</div>,
  Text: (props) => <span>{props.children}</span>,
  Alert: (props) => <div role="alert" data-status={props.status}>{props.children}</div>,
  AlertIcon: () => <span>!</span>,
  Heading: (props) => <h1>{props.children}</h1>,
  Image: (props) => <img alt={props.alt} />,
  IconButton: (props) => (
    <button aria-label={props['aria-label']} onClick={props.onClick} />
  ),
  Popover: (props) => <div>{props.children}</div>,
  PopoverTrigger: (props) => <div>{props.children}</div>,
  PopoverContent: (props) => <div>{props.children}</div>,
  PopoverArrow: () => null,
  PopoverCloseButton: () => null,
  PopoverHeader: (props) => <div>{props.children}</div>,
  PopoverBody: (props) => <div>{props.children}</div>,
}));

// --- Mock child components ---
jest.mock('../../components/auth/PasswordlessSignUp', () => ({
  PasswordlessSignUp: () => <div data-testid="passwordless-signup">PasswordlessSignUp</div>,
}));

jest.mock('../../components/auth/PasskeySetup', () => ({
  PasskeySetup: () => <div data-testid="passkey-setup">PasskeySetup</div>,
}));

jest.mock('../../components/auth/MobilePasskeyDebug', () => ({
  MobilePasskeyDebug: () => <div data-testid="mobile-passkey-debug">MobilePasskeyDebug</div>,
}));

// --- Import components under test ---
import { AuthProvider, useAuth } from '../../context/AuthProvider';
import { CustomAuthenticator } from '../../components/auth/CustomAuthenticator';

// Helper to simulate Hub events
function simulateHubEvent(event, data) {
  if (hubAuthCallback) {
    act(() => {
      hubAuthCallback({ payload: { event, data } });
    });
  }
}

// Helper to create a mock session with tokens
function createMockSession(email, groups, sub = 'user-sub-123') {
  return {
    tokens: {
      accessToken: {
        payload: {
          'cognito:groups': groups,
          sub: sub,
        },
        toString: () => 'mock-access-token-jwt',
      },
      idToken: {
        payload: {
          email: email,
          given_name: 'Test',
          family_name: 'User',
        },
      },
    },
  };
}

describe('Google SSO Flow - Integration', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    hubAuthCallback = null;
    // Default: no session on mount (user not logged in)
    mockFetchAuthSession.mockResolvedValue({ tokens: undefined });
    mockSignOut.mockResolvedValue(undefined);
    // Mock window.location for sign-out redirect
    delete (window as any).location;
    (window as any).location = { href: '', origin: 'http://localhost:3000' };
  });

  /**
   * Validates: Requirements R1.2, R1.3, R2.1, R2.2
   *
   * Full happy path: User clicks Google → signInWithRedirect called →
   * Hub fires 'signedIn' → AuthProvider fetches session → user is authenticated with groups.
   */
  describe('Happy path: Google SSO → signedIn → user authenticated with groups', () => {
    it('renders login page, clicks Google, receives signedIn event, and shows authenticated content', async () => {
      const AuthenticatedContent = () => {
        const { user, isAuthenticated } = useAuth();
        if (isAuthenticated && user) {
          return (
            <div data-testid="authenticated">
              <span data-testid="user-email">{user.email}</span>
              <span data-testid="user-groups">{user.groups.join(',')}</span>
              <span data-testid="user-token">{user.accessToken}</span>
            </div>
          );
        }
        return null;
      };

      // Render the full tree: AuthProvider → CustomAuthenticator → content
      render(
        <AuthProvider>
          <CustomAuthenticator>
            {({ signOut, user }) => (
              <div>
                <div data-testid="child-content">Authenticated Child</div>
                <AuthenticatedContent />
              </div>
            )}
          </CustomAuthenticator>
        </AuthProvider>
      );

      // Wait for initial loading to complete (no session → login page shown)
      await waitFor(() => {
        expect(screen.getByText('Inloggen met Google')).toBeInTheDocument();
      });

      // User clicks the Google sign-in button
      const googleButton = screen.getByText('Inloggen met Google');
      fireEvent.click(googleButton);

      // signInWithRedirect should have been called with Google provider
      await waitFor(() => {
        expect(mockSignInWithRedirect).toHaveBeenCalledWith({ provider: 'Google' });
      });

      // Now simulate: after OAuth redirect completes, Amplify fires 'signedIn' Hub event
      // At this point, fetchAuthSession should return a valid session
      const mockSession = createMockSession(
        'webmaster@h-dcn.nl',
        ['hdcnLeden', 'Members_CRUD', 'Regio_All'],
        'google-user-sub-456'
      );
      mockFetchAuthSession.mockResolvedValue(mockSession);

      // Fire the Hub signedIn event
      simulateHubEvent('signedIn', {});

      // AuthProvider should now load the session and set the user
      await waitFor(() => {
        expect(screen.getByTestId('authenticated')).toBeInTheDocument();
      });

      // Verify user data is correctly extracted from tokens
      expect(screen.getByTestId('user-email')).toHaveTextContent('webmaster@h-dcn.nl');
      expect(screen.getByTestId('user-groups')).toHaveTextContent('hdcnLeden,Members_CRUD,Regio_All');
      expect(screen.getByTestId('user-token')).toHaveTextContent('mock-access-token-jwt');

      // The authenticated child content should be rendered
      expect(screen.getByTestId('child-content')).toHaveTextContent('Authenticated Child');
    });
  });

  /**
   * Validates: Requirements R9.1
   *
   * Error path: User clicks Google → OAuth fails → Hub fires 'signInWithRedirect_failure' →
   * error message is shown on the login page.
   */
  describe('Error path: Google SSO failure → error message on login page', () => {
    it('shows error message when Hub fires signInWithRedirect_failure', async () => {
      render(
        <AuthProvider>
          <CustomAuthenticator>
            {({ signOut, user }) => (
              <div data-testid="child-content">Authenticated Child</div>
            )}
          </CustomAuthenticator>
        </AuthProvider>
      );

      // Wait for initial loading to complete (login page shown)
      await waitFor(() => {
        expect(screen.getByText('Inloggen met Google')).toBeInTheDocument();
      });

      // User clicks Google button
      const googleButton = screen.getByText('Inloggen met Google');
      fireEvent.click(googleButton);

      // signInWithRedirect is called
      await waitFor(() => {
        expect(mockSignInWithRedirect).toHaveBeenCalledWith({ provider: 'Google' });
      });

      // Simulate OAuth failure: Hub fires signInWithRedirect_failure
      // fetchAuthSession still returns no session
      mockFetchAuthSession.mockResolvedValue({ tokens: undefined });

      simulateHubEvent('signInWithRedirect_failure', {
        error: new Error('User denied consent'),
      });

      // AuthProvider should set error state, which CustomAuthenticator displays via useAuth().error
      // The AuthProvider sets error to 'Sign-in failed. Please try again.' on signInWithRedirect_failure
      await waitFor(() => {
        expect(screen.getByText('Sign-in failed. Please try again.')).toBeInTheDocument();
      });

      // User should still see the login page (not authenticated content)
      expect(screen.queryByTestId('child-content')).not.toBeInTheDocument();

      // The error should be displayed in an alert
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });

    it('shows error message when signInWithRedirect throws immediately', async () => {
      // signInWithRedirect throws (e.g., misconfigured Amplify)
      mockSignInWithRedirect.mockRejectedValue(new Error('OAuth not configured'));

      render(
        <AuthProvider>
          <CustomAuthenticator>
            {({ signOut, user }) => (
              <div data-testid="child-content">Authenticated Child</div>
            )}
          </CustomAuthenticator>
        </AuthProvider>
      );

      // Wait for login page
      await waitFor(() => {
        expect(screen.getByText('Inloggen met Google')).toBeInTheDocument();
      });

      // Click Google button — this time signInWithRedirect throws
      const googleButton = screen.getByText('Inloggen met Google');
      fireEvent.click(googleButton);

      // GoogleSignInButton catches the error and calls onError
      // CustomAuthenticator shows it as "Google SSO fout: ..."
      await waitFor(() => {
        expect(screen.getByText(/Google SSO fout: OAuth not configured/)).toBeInTheDocument();
      });

      // User remains on login page
      expect(screen.queryByTestId('child-content')).not.toBeInTheDocument();
    });
  });
});
