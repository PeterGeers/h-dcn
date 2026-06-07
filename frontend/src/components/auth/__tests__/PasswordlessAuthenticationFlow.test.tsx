import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
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
        'login.setup_new_passkey': 'Passkey Instellen',
        'login.debug_passkey': 'Debug Passkey Problemen',
        'errors.network': 'Netwerkfout. Controleer je verbinding en probeer opnieuw.',
        'errors.code_expired': 'Code verlopen. Vraag een nieuwe code aan.',
        'errors.verification_failed': 'Verificatie mislukt. Probeer opnieuw.',
        'errors.code_required': 'Verificatiecode is vereist om in te loggen.',
        'errors.login_failed': 'Inloggen mislukt. Probeer opnieuw.',
        'errors.credentials_invalid': 'Inloggen mislukt. Controleer je gegevens.',
        'errors.passkey_cancelled': 'Passkey authenticatie geannuleerd. Probeer opnieuw.',
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
      data-testid={`button-${children?.toString().replace(/\s+/g, '-').toLowerCase()}`}
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
      data-testid={`input-${name}`}
      {...props} 
    />
  ),
  VStack: ({ children }: any) => <div>{children}</div>,
  HStack: ({ children }: any) => <div>{children}</div>,
  Text: ({ children }: any) => <span>{children}</span>,
  Alert: ({ children }: any) => <div role="alert">{children}</div>,
  AlertIcon: () => <span>!</span>,
  Heading: ({ children, ...props }: any) => <h1>{children}</h1>,
  Image: ({ src, alt, ...props }: any) => <img src={src} alt={alt} {...props} />,
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

// Mock child components
jest.mock('../PasswordlessSignUp', () => ({
  PasswordlessSignUp: ({ onSuccess, onError }: any) => (
    <div data-testid="passwordless-signup">
      <button onClick={() => onSuccess('test@example.com')}>Sign Up Success</button>
      <button onClick={() => onError('Sign up failed')}>Sign Up Error</button>
    </div>
  ),
}));

jest.mock('../PasskeySetup', () => ({
  PasskeySetup: ({ userEmail, onSuccess, onSkip, onError }: any) => (
    <div data-testid="passkey-setup">
      <span>Setting up passkey for: {userEmail}</span>
      <button onClick={() => onSuccess()}>Setup Success</button>
      <button onClick={() => onSkip()}>Skip Setup</button>
      <button onClick={() => onError('Setup failed')}>Setup Error</button>
    </div>
  ),
}));

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

jest.mock('../EmailRecovery', () => ({
  EmailRecovery: ({ onSuccess, onCancel, onError }: any) => (
    <div data-testid="email-recovery">
      <button onClick={() => onSuccess({ tokens: { AccessToken: 'mock-token' }, user: { email: 'recovered@example.com' } })}>
        Recovery Success
      </button>
      <button onClick={() => onCancel()}>Cancel Recovery</button>
      <button onClick={() => onError('Recovery failed')}>Recovery Error</button>
    </div>
  ),
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

// Mock aws-amplify/auth
const mockSignIn = jest.fn();
const mockConfirmSignIn = jest.fn();
jest.mock('aws-amplify/auth', () => ({
  signIn: (...args: any[]) => mockSignIn(...args),
  confirmSignIn: (...args: any[]) => mockConfirmSignIn(...args),
}));

import { CustomAuthenticator } from '../CustomAuthenticator';

describe('Passwordless Authentication Flow', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSignIn.mockReset();
    mockConfirmSignIn.mockReset();
    // Mock prompt for OTP code entry
    window.prompt = jest.fn();
  });

  test('should render sign in form initially', () => {
    render(
      <CustomAuthenticator>
        {({ signOut, user }) => <div data-testid="authenticated">Authenticated</div>}
      </CustomAuthenticator>
    );

    expect(screen.getByText('Welkom bij het H-DCN Portaal')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Inloggen' })).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Voer je e-mailadres in')).toBeInTheDocument();
  });

  test('should show passkey sign in button', () => {
    render(
      <CustomAuthenticator>
        {({ signOut, user }) => <div data-testid="authenticated">Authenticated</div>}
      </CustomAuthenticator>
    );

    expect(screen.getByText('Inloggen met Passkey')).toBeInTheDocument();
  });

  test('should show Google sign in option', () => {
    render(
      <CustomAuthenticator>
        {({ signOut, user }) => <div data-testid="authenticated">Authenticated</div>}
      </CustomAuthenticator>
    );

    expect(screen.getByTestId('google-sign-in')).toBeInTheDocument();
  });

  test('should show advanced options when email is entered', () => {
    render(
      <CustomAuthenticator>
        {({ signOut, user }) => <div data-testid="authenticated">Authenticated</div>}
      </CustomAuthenticator>
    );

    // Enter email
    const emailInput = screen.getByTestId('input-email');
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });

    // Advanced options should appear
    expect(screen.getByText('Geavanceerde opties')).toBeInTheDocument();
    expect(screen.getByText('Passkey Instellen')).toBeInTheDocument();
  });

  test('should navigate to passkey setup when clicking setup button', () => {
    render(
      <CustomAuthenticator>
        {({ signOut, user }) => <div data-testid="authenticated">Authenticated</div>}
      </CustomAuthenticator>
    );

    // Enter email to show advanced options
    const emailInput = screen.getByTestId('input-email');
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });

    // Click passkey setup
    const setupButton = screen.getByText('Passkey Instellen');
    fireEvent.click(setupButton);

    // Should show passkey setup component
    expect(screen.getByTestId('passkey-setup')).toBeInTheDocument();
    expect(screen.getByText('Setting up passkey for: test@example.com')).toBeInTheDocument();
  });

  test('should handle successful passkey sign-in via Amplify', async () => {
    // Mock signIn resolving to isSignedIn: true
    mockSignIn.mockResolvedValue({ isSignedIn: true });

    render(
      <CustomAuthenticator>
        {({ signOut, user }) => <div data-testid="authenticated">Authenticated</div>}
      </CustomAuthenticator>
    );

    // Enter email
    const emailInput = screen.getByTestId('input-email');
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });

    // Submit the form (click passkey button which is the submit button)
    const signInButton = screen.getByText('Inloggen met Passkey');
    fireEvent.click(signInButton);

    // Should have called signIn with WEB_AUTHN
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

  test('should fallback to EMAIL_OTP when WebAuthn fails', async () => {
    // First signIn (WEB_AUTHN) fails, second (EMAIL_OTP) succeeds with OTP step
    mockSignIn
      .mockRejectedValueOnce(new Error('WebAuthn not available'))
      .mockResolvedValueOnce({
        isSignedIn: false,
        nextStep: { signInStep: 'CONFIRM_SIGN_IN_WITH_EMAIL_CODE' },
      });

    // Mock prompt returning a code
    (window.prompt as jest.Mock).mockReturnValue('123456');
    mockConfirmSignIn.mockResolvedValue({ isSignedIn: true });

    render(
      <CustomAuthenticator>
        {({ signOut, user }) => <div data-testid="authenticated">Authenticated</div>}
      </CustomAuthenticator>
    );

    // Enter email and submit
    const emailInput = screen.getByTestId('input-email');
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    const signInButton = screen.getByText('Inloggen met Passkey');
    fireEvent.click(signInButton);

    // Should have called signIn twice — first WEB_AUTHN, then EMAIL_OTP
    await waitFor(() => {
      expect(mockSignIn).toHaveBeenCalledTimes(2);
      expect(mockSignIn).toHaveBeenLastCalledWith(
        expect.objectContaining({
          username: 'test@example.com',
          options: expect.objectContaining({
            preferredChallenge: 'EMAIL_OTP',
          }),
        })
      );
    });
  });

  test('should show error on NotAuthorizedException', async () => {
    const notAuthError = new Error('User is not authorized');
    notAuthError.name = 'NotAuthorizedException';
    mockSignIn.mockRejectedValue(notAuthError);

    render(
      <CustomAuthenticator>
        {({ signOut, user }) => <div data-testid="authenticated">Authenticated</div>}
      </CustomAuthenticator>
    );

    const emailInput = screen.getByTestId('input-email');
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    const signInButton = screen.getByText('Inloggen met Passkey');
    fireEvent.click(signInButton);

    await waitFor(() => {
      expect(screen.getByText('Inloggen mislukt. Controleer je gegevens.')).toBeInTheDocument();
    });
  });

  test('should show registration form when user does not exist', async () => {
    const notFoundError = new Error('User does not exist');
    notFoundError.name = 'UserNotFoundException';
    mockSignIn.mockRejectedValue(notFoundError);

    render(
      <CustomAuthenticator>
        {({ signOut, user }) => <div data-testid="authenticated">Authenticated</div>}
      </CustomAuthenticator>
    );

    const emailInput = screen.getByTestId('input-email');
    fireEvent.change(emailInput, { target: { value: 'newuser@example.com' } });
    const signInButton = screen.getByText('Inloggen met Passkey');
    fireEvent.click(signInButton);

    // Should show the signup component
    await waitFor(() => {
      expect(screen.getByTestId('passwordless-signup')).toBeInTheDocument();
    });
  });

  test('should show error when passkey is cancelled', async () => {
    const cancelError = new Error('User cancelled');
    cancelError.name = 'NotAllowedError';
    mockSignIn.mockRejectedValue(cancelError);

    render(
      <CustomAuthenticator>
        {({ signOut, user }) => <div data-testid="authenticated">Authenticated</div>}
      </CustomAuthenticator>
    );

    const emailInput = screen.getByTestId('input-email');
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    const signInButton = screen.getByText('Inloggen met Passkey');
    fireEvent.click(signInButton);

    await waitFor(() => {
      expect(screen.getByText('Passkey authenticatie geannuleerd. Probeer opnieuw.')).toBeInTheDocument();
    });
  });
});
