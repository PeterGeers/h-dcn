import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

// Mock Chakra UI components
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

// Mock child components
jest.mock('../PasswordlessSignUp', () => ({
  PasswordlessSignUp: () => <div data-testid="passwordless-signup">PasswordlessSignUp</div>,
}));

jest.mock('../PasskeySetup', () => ({
  PasskeySetup: () => <div data-testid="passkey-setup">PasskeySetup</div>,
}));

jest.mock('../MobilePasskeyDebug', () => ({
  MobilePasskeyDebug: () => <div data-testid="mobile-passkey-debug">MobilePasskeyDebug</div>,
}));

jest.mock('../GoogleSignInButton', () => ({
  __esModule: true,
  default: () => <div data-testid="google-signin-button">GoogleSignInButton</div>,
}));

// Mock useAuth hook
const mockSignOut = jest.fn();
jest.mock('../../../hooks/useAuth', () => ({
  useAuth: () => ({
    user: null,
    isLoading: false,
    isAuthenticated: false,
    error: null,
    signOut: mockSignOut,
  }),
}));

// Mock aws-amplify/auth — the component uses dynamic imports
const mockSignIn = jest.fn();
const mockConfirmSignIn = jest.fn();
const mockAmplifySignOut = jest.fn();

jest.mock('aws-amplify/auth', () => ({
  signIn: (...args) => mockSignIn(...args),
  confirmSignIn: (...args) => mockConfirmSignIn(...args),
  signOut: (...args) => mockAmplifySignOut(...args),
}));

import { CustomAuthenticator } from '../CustomAuthenticator';

describe('CustomAuthenticator - Auth Flows', () => {
  const mockChildren = jest.fn().mockReturnValue(<div>Authenticated</div>);

  beforeEach(() => {
    jest.clearAllMocks();
    mockAmplifySignOut.mockResolvedValue(undefined);
    // Mock window.prompt for OTP code entry
    jest.spyOn(window, 'prompt').mockReturnValue(null);
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  /**
   * Validates: Requirements R9.3
   * WebAuthn failure triggers automatic OTP fallback — no error shown to user.
   */
  describe('WebAuthn fallback to EMAIL_OTP (R9.3)', () => {
    it('falls back to EMAIL_OTP when WebAuthn sign-in fails', async () => {
      // First call (WEB_AUTHN) throws — simulating passkey failure
      mockSignIn
        .mockRejectedValueOnce(new Error('WebAuthn not available'))
        // Second call (EMAIL_OTP fallback) succeeds with OTP challenge
        .mockResolvedValueOnce({
          isSignedIn: false,
          nextStep: { signInStep: 'CONFIRM_SIGN_IN_WITH_EMAIL_CODE' },
        });

      // User enters OTP code
      jest.spyOn(window, 'prompt').mockReturnValue('123456');
      mockConfirmSignIn.mockResolvedValue({ isSignedIn: true });

      render(<CustomAuthenticator>{mockChildren}</CustomAuthenticator>);

      // Enter email
      const emailInput = screen.getByPlaceholderText('Voer je e-mailadres in');
      await userEvent.type(emailInput, 'test@example.com');

      // Submit form
      const submitButton = screen.getByRole('button', { name: /inloggen met passkey/i });
      fireEvent.click(submitButton);

      await waitFor(() => {
        // signIn should have been called twice: first WEB_AUTHN, then EMAIL_OTP
        expect(mockSignIn).toHaveBeenCalledTimes(2);

        // First call: WEB_AUTHN attempt
        expect(mockSignIn).toHaveBeenNthCalledWith(1, {
          username: 'test@example.com',
          options: {
            authFlowType: 'USER_AUTH',
            preferredChallenge: 'WEB_AUTHN',
          },
        });

        // Second call: EMAIL_OTP fallback
        expect(mockSignIn).toHaveBeenNthCalledWith(2, {
          username: 'test@example.com',
          options: {
            authFlowType: 'USER_AUTH',
            preferredChallenge: 'EMAIL_OTP',
          },
        });
      });

      // No error should be shown to the user — fallback is silent
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });
  });

  /**
   * Validates: Requirements R9.2
   * Expired OTP code shows "Code verlopen" message and a "Nieuwe code versturen" button.
   */
  describe('Expired OTP shows resend option (R9.2)', () => {
    it('shows resend button when OTP code is expired', async () => {
      // signIn succeeds with OTP challenge
      mockSignIn.mockResolvedValue({
        isSignedIn: false,
        nextStep: { signInStep: 'CONFIRM_SIGN_IN_WITH_EMAIL_CODE' },
      });

      // User enters a code
      jest.spyOn(window, 'prompt').mockReturnValue('expired-code');

      // confirmSignIn throws ExpiredCodeException
      const expiredError = new Error('Code has expired');
      expiredError.name = 'ExpiredCodeException';
      mockConfirmSignIn.mockRejectedValue(expiredError);

      render(<CustomAuthenticator>{mockChildren}</CustomAuthenticator>);

      // Enter email
      const emailInput = screen.getByPlaceholderText('Voer je e-mailadres in');
      await userEvent.type(emailInput, 'test@example.com');

      // Submit form
      const submitButton = screen.getByRole('button', { name: /inloggen met passkey/i });
      fireEvent.click(submitButton);

      // Wait for the error message and resend button to appear
      await waitFor(() => {
        expect(screen.getByText(/Code verlopen/i)).toBeInTheDocument();
      });

      // Resend button should be visible
      expect(screen.getByText('Nieuwe code versturen')).toBeInTheDocument();
    });
  });

  /**
   * Validates: Requirements R9.5
   * Network error during sign-in shows a retry-friendly message.
   */
  describe('Network error shows retry message (R9.5)', () => {
    it('shows network error message when signIn throws NetworkError', async () => {
      // signOut mock (called before signIn to clear stale session)
      mockAmplifySignOut.mockResolvedValue(undefined);

      // Both signIn calls fail with network error (WEB_AUTHN attempt + fallback both fail)
      const networkError = new Error('Network request failed');
      networkError.name = 'NetworkError';
      mockSignIn.mockRejectedValue(networkError);

      render(<CustomAuthenticator>{mockChildren}</CustomAuthenticator>);

      // Enter email
      const emailInput = screen.getByPlaceholderText('Voer je e-mailadres in');
      await userEvent.type(emailInput, 'test@example.com');

      // Submit form
      const submitButton = screen.getByRole('button', { name: /inloggen met passkey/i });
      fireEvent.click(submitButton);

      // Wait for the network error message
      await waitFor(() => {
        expect(
          screen.getByText('Netwerkfout. Controleer je verbinding en probeer opnieuw.')
        ).toBeInTheDocument();
      });
    });
  });
});
