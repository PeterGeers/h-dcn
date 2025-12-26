import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { CustomAuthenticator } from '../CustomAuthenticator';

// Mock Chakra UI components
jest.mock('@chakra-ui/react', () => ({
  Box: ({ children, ...props }: any) => <div data-testid="box" {...props}>{children}</div>,
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
  Heading: ({ children }: any) => <h1>{children}</h1>,
  Tabs: ({ children }: any) => <div>{children}</div>,
  TabList: ({ children }: any) => <div>{children}</div>,
  TabPanels: ({ children }: any) => <div>{children}</div>,
  Tab: ({ children, onClick }: any) => <button onClick={onClick}>{children}</button>,
  TabPanel: ({ children }: any) => <div>{children}</div>,
  Image: ({ src, alt, ...props }: any) => <img src={src} alt={alt} {...props} />,
}));

// Mock the passwordless components
jest.mock('../PasswordlessSignUp', () => ({
  PasswordlessSignUp: ({ onSuccess, onError }: any) => (
    <div data-testid="passwordless-signup">
      <button onClick={() => onSuccess('test@example.com')}>Sign Up Success</button>
      <button onClick={() => onError('Sign up failed')}>Sign Up Error</button>
    </div>
  )
}));

jest.mock('../PasskeySetup', () => ({
  PasskeySetup: ({ userEmail, onSuccess, onSkip, onError }: any) => (
    <div data-testid="passkey-setup">
      <span>Setting up passkey for: {userEmail}</span>
      <button onClick={() => onSuccess({ tokens: { AccessToken: 'mock-token' }, user: { email: userEmail } })}>
        Setup Success
      </button>
      <button onClick={() => onSkip()}>Skip Setup</button>
      <button onClick={() => onError('Setup failed')}>Setup Error</button>
    </div>
  )
}));

jest.mock('../CrossDeviceAuth', () => ({
  CrossDeviceAuth: ({ userEmail, onSuccess, onCancel, onError }: any) => (
    <div data-testid="cross-device-auth">
      <span>Cross-device auth for: {userEmail}</span>
      <button onClick={() => onSuccess({ tokens: { AccessToken: 'mock-token' }, user: { email: userEmail } })}>
        Auth Success
      </button>
      <button onClick={() => onCancel()}>Cancel</button>
      <button onClick={() => onError('Auth failed')}>Auth Error</button>
    </div>
  )
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
  )
}));

// Mock WebAuthn service
jest.mock('../../../services/webAuthnService', () => ({
  WebAuthnService: {
    isSupported: jest.fn(() => true),
    shouldOfferCrossDeviceAuth: jest.fn(() => true),
    authenticateWithPasskey: jest.fn(),
    credentialToJSON: jest.fn(() => ({ id: 'mock-credential' })),
  }
}));

// Import the mocked service for easier access in tests
import { WebAuthnService } from '../../../services/webAuthnService';
const mockWebAuthnService = WebAuthnService as jest.Mocked<typeof WebAuthnService>;

// Mock fetch
global.fetch = jest.fn();

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock
});

describe('Passwordless Authentication Flow', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (global.fetch as jest.Mock).mockReset();
    localStorageMock.getItem.mockReturnValue(null);
    
    // Reset WebAuthn service mocks
    mockWebAuthnService.isSupported.mockReturnValue(true);
    mockWebAuthnService.shouldOfferCrossDeviceAuth.mockReturnValue(true);
    mockWebAuthnService.authenticateWithPasskey.mockResolvedValue({
      id: 'mock-credential-id',
      response: { signature: 'mock-signature' }
    });
  });

  test('should render sign in form initially', () => {
    render(
      <CustomAuthenticator>
        {({ signOut, user }) => <div data-testid="authenticated">Authenticated</div>}
      </CustomAuthenticator>
    );

    expect(screen.getByText('H-DCN Portal')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Inloggen' })).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Voer je e-mailadres in')).toBeInTheDocument();
  });

  test('should handle successful passkey authentication', async () => {
    // Mock successful passkey authentication
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ challenge: 'mock-challenge' })
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          tokens: {
            AccessToken: 'mock-access-token',
            IdToken: 'mock-id-token',
            RefreshToken: 'mock-refresh-token',
            AccessTokenPayload: { exp: Date.now() / 1000 + 3600 }
          },
          user: {
            email: 'test@example.com',
            given_name: 'Test',
            family_name: 'User'
          }
        })
      });

    render(
      <CustomAuthenticator>
        {({ signOut, user }) => <div data-testid="authenticated">Authenticated: {user?.attributes?.email}</div>}
      </CustomAuthenticator>
    );

    // Enter email
    const emailInput = screen.getByTestId('input-email');
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });

    // Click sign in button
    const signInButton = screen.getByTestId('button-🔐-inloggen-met-passkey');
    fireEvent.click(signInButton);

    // Wait for authentication to complete
    await waitFor(() => {
      expect(screen.getByTestId('authenticated')).toBeInTheDocument();
    });

    expect(screen.getByText('Authenticated: test@example.com')).toBeInTheDocument();
    expect(localStorageMock.setItem).toHaveBeenCalledWith('hdcn_auth_user', expect.any(String));
    expect(localStorageMock.setItem).toHaveBeenCalledWith('hdcn_auth_tokens', expect.any(String));
  });

  test('should handle no passkey registered scenario', async () => {
    // Mock no passkey registered response
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      json: () => Promise.resolve({ code: 'NO_PASSKEY_REGISTERED' })
    });

    render(
      <CustomAuthenticator>
        {({ signOut, user }) => <div data-testid="authenticated">Authenticated</div>}
      </CustomAuthenticator>
    );

    // Enter email
    const emailInput = screen.getByTestId('input-email');
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });

    // Click sign in button
    const signInButton = screen.getByTestId('button-🔐-inloggen-met-passkey');
    fireEvent.click(signInButton);

    // Should show passkey setup
    await waitFor(() => {
      expect(screen.getByTestId('passkey-setup')).toBeInTheDocument();
    }, { timeout: 3000 });

    expect(screen.getByText('Setting up passkey for: test@example.com')).toBeInTheDocument();
  });

  test('should handle passkey setup flow', async () => {
    // Mock no passkey registered response
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      json: () => Promise.resolve({ code: 'NO_PASSKEY_REGISTERED' })
    });

    render(
      <CustomAuthenticator>
        {({ signOut, user }) => <div data-testid="authenticated">Authenticated: {user?.attributes?.email}</div>}
      </CustomAuthenticator>
    );

    // Enter email and trigger passkey setup
    const emailInput = screen.getByTestId('input-email');
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });

    const signInButton = screen.getByTestId('button-🔐-inloggen-met-passkey');
    fireEvent.click(signInButton);

    await waitFor(() => {
      expect(screen.getByTestId('passkey-setup')).toBeInTheDocument();
    }, { timeout: 3000 });

    // Complete passkey setup successfully
    const setupSuccessButton = screen.getByText('Setup Success');
    fireEvent.click(setupSuccessButton);

    // Should be authenticated after setup
    await waitFor(() => {
      expect(screen.getByTestId('authenticated')).toBeInTheDocument();
    }, { timeout: 3000 });

    expect(screen.getByText('Authenticated: test@example.com')).toBeInTheDocument();
  });

  test('should handle cross-device authentication', async () => {
    render(
      <CustomAuthenticator>
        {({ signOut, user }) => <div data-testid="authenticated">Authenticated: {user?.attributes?.email}</div>}
      </CustomAuthenticator>
    );

    // Enter email
    const emailInput = screen.getByTestId('input-email');
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });

    // Click cross-device auth button (using the actual button text)
    const crossDeviceButton = screen.getByText('Cross-Device Authenticatie');
    fireEvent.click(crossDeviceButton);

    // Should show cross-device auth component
    await waitFor(() => {
      expect(screen.getByTestId('cross-device-auth')).toBeInTheDocument();
    }, { timeout: 3000 });

    expect(screen.getByText('Cross-device auth for: test@example.com')).toBeInTheDocument();

    // Complete cross-device auth successfully
    const authSuccessButton = screen.getByText('Auth Success');
    fireEvent.click(authSuccessButton);

    // Should be authenticated
    await waitFor(() => {
      expect(screen.getByTestId('authenticated')).toBeInTheDocument();
    }, { timeout: 3000 });

    expect(screen.getByText('Authenticated: test@example.com')).toBeInTheDocument();
  });

  test('should handle email recovery flow', async () => {
    render(
      <CustomAuthenticator>
        {({ signOut, user }) => <div data-testid="authenticated">Authenticated: {user?.attributes?.email}</div>}
      </CustomAuthenticator>
    );

    // Click email recovery button
    const recoveryButton = screen.getByTestId('button-📧-account-herstellen-via-email');
    fireEvent.click(recoveryButton);

    // Should show email recovery component
    await waitFor(() => {
      expect(screen.getByTestId('email-recovery')).toBeInTheDocument();
    });

    // Complete recovery successfully
    const recoverySuccessButton = screen.getByText('Recovery Success');
    fireEvent.click(recoverySuccessButton);

    // Should be authenticated
    await waitFor(() => {
      expect(screen.getByTestId('authenticated')).toBeInTheDocument();
    });

    expect(screen.getByText('Authenticated: recovered@example.com')).toBeInTheDocument();
  });

  test('should handle sign out', async () => {
    // Mock stored authentication data
    localStorageMock.getItem
      .mockReturnValueOnce(JSON.stringify({
        username: 'test@example.com',
        attributes: { email: 'test@example.com' }
      }))
      .mockReturnValueOnce(JSON.stringify({
        AccessToken: 'mock-token',
        AccessTokenPayload: { exp: Date.now() / 1000 + 3600 }
      }));

    render(
      <CustomAuthenticator>
        {({ signOut, user }) => (
          <div>
            <div data-testid="authenticated">Authenticated: {user?.attributes?.email}</div>
            <button onClick={signOut} data-testid="sign-out-button">Sign Out</button>
          </div>
        )}
      </CustomAuthenticator>
    );

    // Should be authenticated initially
    expect(screen.getByTestId('authenticated')).toBeInTheDocument();

    // Click sign out
    const signOutButton = screen.getByTestId('sign-out-button');
    fireEvent.click(signOutButton);

    // Should return to sign in form - use a more specific selector
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Inloggen' })).toBeInTheDocument();
    }, { timeout: 3000 });

    expect(localStorageMock.removeItem).toHaveBeenCalledWith('hdcn_auth_user');
    expect(localStorageMock.removeItem).toHaveBeenCalledWith('hdcn_auth_tokens');
  });

  test('should handle expired tokens', async () => {
    // Mock expired token
    localStorageMock.getItem
      .mockReturnValueOnce(JSON.stringify({
        username: 'test@example.com',
        attributes: { email: 'test@example.com' }
      }))
      .mockReturnValueOnce(JSON.stringify({
        AccessToken: 'expired-token',
        AccessTokenPayload: { exp: Date.now() / 1000 - 3600 } // Expired 1 hour ago
      }));

    render(
      <CustomAuthenticator>
        {({ signOut, user }) => <div data-testid="authenticated">Authenticated</div>}
      </CustomAuthenticator>
    );

    // Should show sign in form due to expired token - use a more specific selector
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Inloggen' })).toBeInTheDocument();
    }, { timeout: 3000 });

    expect(localStorageMock.removeItem).toHaveBeenCalledWith('hdcn_auth_user');
    expect(localStorageMock.removeItem).toHaveBeenCalledWith('hdcn_auth_tokens');
  });

  test('should handle signup flow', async () => {
    render(
      <CustomAuthenticator>
        {({ signOut, user }) => <div data-testid="authenticated">Authenticated</div>}
      </CustomAuthenticator>
    );

    // Click on Registreren tab
    const registerTab = screen.getByText('Registreren');
    fireEvent.click(registerTab);

    // Should show signup component
    expect(screen.getByTestId('passwordless-signup')).toBeInTheDocument();

    // Complete signup successfully
    const signupSuccessButton = screen.getByText('Sign Up Success');
    fireEvent.click(signupSuccessButton);

    // Should remain on sign in form but with email set - use a more specific selector
    expect(screen.getByRole('heading', { name: 'Inloggen' })).toBeInTheDocument();
  });
});