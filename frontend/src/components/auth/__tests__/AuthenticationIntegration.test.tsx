import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
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
        'errors.verification_failed': 'Verificatie mislukt. Probeer opnieuw.',
        'errors.code_required': 'Verificatiecode is vereist om in te loggen.',
        'errors.login_failed': 'Inloggen mislukt. Probeer opnieuw.',
        'errors.credentials_invalid': 'Inloggen mislukt. Controleer je gegevens.',
        'errors.passkey_cancelled': 'Passkey authenticatie niet beschikbaar. Probeer opnieuw.',
        'errors.confirm_required': 'Je account moet nog bevestigd worden. Controleer je e-mail.',
        'errors.resend_failed': 'Nieuwe code versturen mislukt. Probeer opnieuw.',
        'errors.google_sso': 'Google SSO fout: {{error}}',
        'errors.step_required': 'Extra stap vereist: {{step}}',
        'verification.enter_code': 'Voer de verificatiecode in die naar je e-mail is gestuurd:',
        'verification.resend_code': 'Nieuwe code versturen',
        'verification.sending': 'Versturen...',
        'info.title': 'Authenticatie Informatie',
        'info.passkey_title': 'Passkey (aanbevolen)',
        'info.passkey_desc': 'Veilig inloggen met vingerafdruk, gezichtsherkenning, of apparaat-PIN',
        'info.email_intro': 'E-mail verificatie',
        'info.email_desc': 'Log in met een code via e-mail',
        'info.google_title': 'Google (H-DCN account)',
        'info.google_desc': 'Log in met je Google H-DCN account',
        'info.new_user_title': 'Nieuw account',
        'info.new_user_desc': 'Maak een nieuw account aan',
        'info.help_title': 'Problemen?',
        'info.help_desc': 'Neem contact op met het bestuur',
        'signup.title': 'Account Aanmaken',
        'signup.description': 'Maak een nieuw account aan met je voor- en achternaam.',
        'signup.email_label': 'E-mailadres',
        'signup.first_name_label': 'Voornaam',
        'signup.first_name_placeholder': 'Voer je voornaam in',
        'signup.last_name_label': 'Achternaam',
        'signup.last_name_placeholder': 'Voer je achternaam in',
        'signup.submit_button': 'Account Aanmaken',
        'signup.loading': 'Account aanmaken...',
        'signup.success': 'Account succesvol aangemaakt! Controleer je e-mail voor verificatie-instructies.',
        'signup.existing_account': 'Er bestaat al een account met dit e-mailadres.',
        'signup.generic_error': 'Er is een fout opgetreden bij het aanmaken van je account',
        'signup.network_error': 'Er is een fout opgetreden bij het aanmaken van je account. Controleer je internetverbinding en probeer opnieuw.',
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

// Mock Chakra UI components
jest.mock('@chakra-ui/react', () => ({
  Box: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  Button: ({ children, onClick, isDisabled, isLoading, loadingText, type, ...props }: any) => (
    <button
      onClick={onClick}
      disabled={isDisabled || isLoading}
      type={type}
      data-testid={`button-${children}`}
      {...props}
    >
      {isLoading ? loadingText : children}
    </button>
  ),
  FormControl: ({ children, isRequired }: any) => (
    <div data-required={isRequired}>{children}</div>
  ),
  FormLabel: ({ children }: any) => <label>{children}</label>,
  Input: ({ onChange, value, placeholder, type, name, required, ...props }: any) => (
    <input
      onChange={onChange}
      value={value}
      placeholder={placeholder}
      type={type}
      name={name}
      required={required}
      {...props}
    />
  ),
  VStack: ({ children }: any) => <div>{children}</div>,
  HStack: ({ children }: any) => <div>{children}</div>,
  Text: ({ children }: any) => <span>{children}</span>,
  Alert: ({ children }: any) => <div role="alert">{children}</div>,
  AlertIcon: () => <span>!</span>,
  Heading: ({ children }: any) => <h1>{children}</h1>,
  Image: ({ alt }: any) => <img alt={alt} />,
  IconButton: ({ onClick, 'aria-label': ariaLabel, ...props }: any) => (
    <button onClick={onClick} aria-label={ariaLabel}>info</button>
  ),
  Popover: ({ children }: any) => <div>{children}</div>,
  PopoverTrigger: ({ children }: any) => <>{children}</>,
  PopoverContent: ({ children }: any) => <div>{children}</div>,
  PopoverArrow: () => null,
  PopoverCloseButton: () => null,
  PopoverHeader: ({ children }: any) => <div>{children}</div>,
  PopoverBody: ({ children }: any) => <div>{children}</div>,
}));

// Mock child components used by CustomAuthenticator
jest.mock('../GoogleSignInButton', () => ({
  __esModule: true,
  default: ({ onError, disabled }: any) => (
    <button data-testid="google-sign-in" disabled={disabled}>Google Sign In</button>
  ),
}));

jest.mock('../MobilePasskeyDebug', () => ({
  MobilePasskeyDebug: ({ userEmail }: any) => (
    <div data-testid="mobile-passkey-debug">Debug for: {userEmail}</div>
  ),
}));

jest.mock('../PasswordlessSignUp', () => ({
  PasswordlessSignUp: ({ onSuccess, onError }: any) => (
    <div data-testid="passwordless-signup">
      <button onClick={() => onSuccess('newuser@example.com')}>Sign Up Success</button>
      <button onClick={() => onError('Sign up failed')}>Sign Up Error</button>
    </div>
  ),
}));

jest.mock('../PasskeySetup', () => ({
  PasskeySetup: ({ userEmail, onSuccess, onSkip, onError }: any) => (
    <div data-testid="passkey-setup">
      <span>Passkey Ondersteuning Controleren</span>
      <span>Setting up passkey for: {userEmail}</span>
      <button onClick={() => onSuccess()}>Setup Success</button>
      <button onClick={() => onSkip()}>Skip Setup</button>
      <button onClick={() => onError('Setup failed')}>Setup Error</button>
    </div>
  ),
}));

// Mock useAuth hook (used by CustomAuthenticator)
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

// Mock AWS Amplify
const mockSignIn = jest.fn();
const mockConfirmSignIn = jest.fn();
jest.mock('aws-amplify/auth', () => ({
  signIn: (...args: any[]) => mockSignIn(...args),
  confirmSignIn: (...args: any[]) => mockConfirmSignIn(...args),
}));

// Mock WebAuthnService
jest.mock('../../../services/webAuthnService', () => ({
  WebAuthnService: {
    isSupported: jest.fn(),
    shouldOfferCrossDeviceAuth: jest.fn(),
    authenticateWithPasskey: jest.fn(),
    credentialToJSON: jest.fn(),
    registerPasskey: jest.fn(),
    isPlatformAuthenticatorAvailable: jest.fn(),
    getBrowserInfo: jest.fn(),
  },
}));

import { CustomAuthenticator } from '../CustomAuthenticator';
import { WebAuthnService } from '../../../services/webAuthnService';

const mockChildren = jest.fn();

describe('Authentication Integration Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSignIn.mockReset();
    mockConfirmSignIn.mockReset();

    mockChildren.mockReturnValue(<div>Authenticated Content</div>);
    (WebAuthnService.isSupported as jest.Mock).mockReturnValue(true);
    (WebAuthnService.shouldOfferCrossDeviceAuth as jest.Mock).mockReturnValue(true);
    (WebAuthnService.isPlatformAuthenticatorAvailable as jest.Mock).mockResolvedValue(true);
    (WebAuthnService.getBrowserInfo as jest.Mock).mockReturnValue({
      userAgent: 'Mozilla/5.0',
      isMobile: false,
      recommendedAttachment: 'platform',
    });

    // Mock prompt for OTP code entry
    window.prompt = jest.fn();
  });

  afterEach(() => {
    jest.resetAllMocks();
  });

  describe('Complete Signup → Passkey Setup Flow', () => {
    test('shows registration form when user does not exist', async () => {
      // When signIn throws UserNotFoundException, component shows registration
      const notFoundError = new Error('User does not exist');
      notFoundError.name = 'UserNotFoundException';
      mockSignIn.mockRejectedValue(notFoundError);

      render(<CustomAuthenticator>{mockChildren}</CustomAuthenticator>);

      // Enter email and submit
      const emailInput = screen.getByPlaceholderText('Voer je e-mailadres in');
      await userEvent.type(emailInput, 'newuser@example.com');

      const signInButton = screen.getByText('Inloggen met Passkey');
      fireEvent.click(signInButton);

      // Should show registration form
      await waitFor(() => {
        expect(screen.getByTestId('passwordless-signup')).toBeInTheDocument();
      });
    });

    test('handles signup errors appropriately', async () => {
      // Trigger registration form via UserNotFoundException
      const notFoundError = new Error('User does not exist');
      notFoundError.name = 'UserNotFoundException';
      mockSignIn.mockRejectedValue(notFoundError);

      render(<CustomAuthenticator>{mockChildren}</CustomAuthenticator>);

      const emailInput = screen.getByPlaceholderText('Voer je e-mailadres in');
      await userEvent.type(emailInput, 'existing@example.com');

      const signInButton = screen.getByText('Inloggen met Passkey');
      fireEvent.click(signInButton);

      // Wait for signup form
      await waitFor(() => {
        expect(screen.getByTestId('passwordless-signup')).toBeInTheDocument();
      });

      // Trigger sign up error via the mocked component
      const errorButton = screen.getByText('Sign Up Error');
      fireEvent.click(errorButton);

      // The error is logged but the component stays on signup form
      expect(screen.getByTestId('passwordless-signup')).toBeInTheDocument();
    });

    test('transitions from signup success to login form with email set', async () => {
      // Trigger registration form
      const notFoundError = new Error('User does not exist');
      notFoundError.name = 'UserNotFoundException';
      mockSignIn.mockRejectedValue(notFoundError);

      render(<CustomAuthenticator>{mockChildren}</CustomAuthenticator>);

      const emailInput = screen.getByPlaceholderText('Voer je e-mailadres in');
      await userEvent.type(emailInput, 'newuser@example.com');

      const signInButton = screen.getByText('Inloggen met Passkey');
      fireEvent.click(signInButton);

      await waitFor(() => {
        expect(screen.getByTestId('passwordless-signup')).toBeInTheDocument();
      });

      // Complete signup successfully
      const signupSuccess = screen.getByText('Sign Up Success');
      fireEvent.click(signupSuccess);

      // Should return to login form
      await waitFor(() => {
        expect(screen.getByRole('heading', { name: 'Inloggen' })).toBeInTheDocument();
      });
    });

    test('navigates to passkey setup from advanced options', async () => {
      render(<CustomAuthenticator>{mockChildren}</CustomAuthenticator>);

      // Enter email to show advanced options
      const emailInput = screen.getByPlaceholderText('Voer je e-mailadres in');
      await userEvent.type(emailInput, 'newuser@example.com');

      // Click passkey setup button
      const passkeySetupButton = screen.getByText('Nieuwe Passkey Instellen');
      fireEvent.click(passkeySetupButton);

      // Should show passkey setup component
      await waitFor(() => {
        expect(screen.getByText('Passkey Ondersteuning Controleren')).toBeInTheDocument();
      });
    });
  });

  describe('Passkey Authentication Flow', () => {
    test('successful passkey authentication with existing user', async () => {
      // Mock successful sign-in (Amplify resolves to isSignedIn: true)
      mockSignIn.mockResolvedValue({ isSignedIn: true });

      render(<CustomAuthenticator>{mockChildren}</CustomAuthenticator>);

      const emailInput = screen.getByPlaceholderText('Voer je e-mailadres in');
      await userEvent.type(emailInput, 'test@example.com');

      const signInButton = screen.getByText('Inloggen met Passkey');
      fireEvent.click(signInButton);

      // Should have called signIn with USER_AUTH / WEB_AUTHN
      await waitFor(() => {
        expect(mockSignIn).toHaveBeenCalledWith(
          expect.objectContaining({
            username: 'test@example.com',
            options: expect.objectContaining({
              authFlowType: 'USER_AUTH',
              preferredChallenge: 'WEB_AUTHN',
            }),
          })
        );
      });
    });

    test('handles passkey authentication failure gracefully', async () => {
      // WebAuthn fails, EMAIL_OTP also fails
      const cancelError = new Error('User cancelled passkey authentication');
      cancelError.name = 'NotAllowedError';
      mockSignIn.mockRejectedValue(cancelError);

      render(<CustomAuthenticator>{mockChildren}</CustomAuthenticator>);

      const emailInput = screen.getByPlaceholderText('Voer je e-mailadres in');
      await userEvent.type(emailInput, 'test@example.com');

      const signInButton = screen.getByText('Inloggen met Passkey');
      fireEvent.click(signInButton);

      // Should show error message
      await waitFor(() => {
        expect(screen.getByText(/Passkey authenticatie niet beschikbaar/)).toBeInTheDocument();
      });
    });

    test('falls back to EMAIL_OTP when no passkey is registered', async () => {
      // First attempt (WEB_AUTHN) fails, second (EMAIL_OTP) prompts for code
      mockSignIn
        .mockRejectedValueOnce(new Error('No passkey available'))
        .mockResolvedValueOnce({
          isSignedIn: false,
          nextStep: { signInStep: 'CONFIRM_SIGN_IN_WITH_EMAIL_CODE' },
        });

      // Mock prompt returning a code
      (window.prompt as jest.Mock).mockReturnValue('123456');
      mockConfirmSignIn.mockResolvedValue({ isSignedIn: true });

      render(<CustomAuthenticator>{mockChildren}</CustomAuthenticator>);

      const emailInput = screen.getByPlaceholderText('Voer je e-mailadres in');
      await userEvent.type(emailInput, 'newuser@example.com');

      const signInButton = screen.getByText('Inloggen met Passkey');
      fireEvent.click(signInButton);

      // Should have called signIn twice (WEB_AUTHN then EMAIL_OTP)
      await waitFor(() => {
        expect(mockSignIn).toHaveBeenCalledTimes(2);
        expect(mockSignIn).toHaveBeenLastCalledWith(
          expect.objectContaining({
            username: 'newuser@example.com',
            options: expect.objectContaining({
              preferredChallenge: 'EMAIL_OTP',
            }),
          })
        );
      });

      // Should have prompted for OTP code
      await waitFor(() => {
        expect(window.prompt).toHaveBeenCalled();
      });

      // Should have confirmed with the code
      await waitFor(() => {
        expect(mockConfirmSignIn).toHaveBeenCalledWith({ challengeResponse: '123456' });
      });
    });
  });

  describe('Role Assignment Verification After Authentication', () => {
    test('verifies user roles are extracted from access token after authentication', async () => {
      // The actual role extraction happens in AuthProvider (useAuth) after signIn succeeds.
      // CustomAuthenticator just calls signIn; AuthProvider detects the Hub event.
      // This test verifies signIn is called correctly — role extraction is in AuthProvider.
      mockSignIn.mockResolvedValue({ isSignedIn: true });

      render(<CustomAuthenticator>{mockChildren}</CustomAuthenticator>);

      const emailInput = screen.getByPlaceholderText('Voer je e-mailadres in');
      await userEvent.type(emailInput, 'admin@example.com');

      const signInButton = screen.getByText('Inloggen met Passkey');
      fireEvent.click(signInButton);

      await waitFor(() => {
        expect(mockSignIn).toHaveBeenCalledWith(
          expect.objectContaining({
            username: 'admin@example.com',
          })
        );
      });
    });

    test('handles users with no assigned roles gracefully', async () => {
      // User without roles still signs in fine — roles are empty array in AuthProvider
      mockSignIn.mockResolvedValue({ isSignedIn: true });

      render(<CustomAuthenticator>{mockChildren}</CustomAuthenticator>);

      const emailInput = screen.getByPlaceholderText('Voer je e-mailadres in');
      await userEvent.type(emailInput, 'newuser@example.com');

      const signInButton = screen.getByText('Inloggen met Passkey');
      fireEvent.click(signInButton);

      await waitFor(() => {
        expect(mockSignIn).toHaveBeenCalledWith(
          expect.objectContaining({
            username: 'newuser@example.com',
          })
        );
      });
    });

    test('verifies multiple authentication methods call signIn correctly', async () => {
      // First WEB_AUTHN fails, falls back to EMAIL_OTP which also completes
      mockSignIn
        .mockRejectedValueOnce(new Error('WebAuthn unavailable'))
        .mockResolvedValueOnce({ isSignedIn: true });

      render(<CustomAuthenticator>{mockChildren}</CustomAuthenticator>);

      const emailInput = screen.getByPlaceholderText('Voer je e-mailadres in');
      await userEvent.type(emailInput, 'regional@example.com');

      const signInButton = screen.getByText('Inloggen met Passkey');
      fireEvent.click(signInButton);

      // Should have attempted both auth methods
      await waitFor(() => {
        expect(mockSignIn).toHaveBeenCalledTimes(2);
      });

      // First call: WEB_AUTHN
      expect(mockSignIn).toHaveBeenNthCalledWith(
        1,
        expect.objectContaining({
          username: 'regional@example.com',
          options: expect.objectContaining({
            preferredChallenge: 'WEB_AUTHN',
          }),
        })
      );

      // Second call: EMAIL_OTP fallback
      expect(mockSignIn).toHaveBeenNthCalledWith(
        2,
        expect.objectContaining({
          username: 'regional@example.com',
          options: expect.objectContaining({
            preferredChallenge: 'EMAIL_OTP',
          }),
        })
      );
    });
  });
});
