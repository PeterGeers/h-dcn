import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

// Mock Chakra UI components to avoid dependency issues
jest.mock('@chakra-ui/react', () => ({
  Box: ({ children, ...props }: any) => <div data-testid="box" {...props}>{children}</div>,
  Button: ({ children, onClick, isDisabled, ...props }: any) => (
    <button onClick={onClick} disabled={isDisabled} {...props}>{children}</button>
  ),
  FormControl: ({ children }: any) => <div>{children}</div>,
  FormLabel: ({ children }: any) => <label>{children}</label>,
  Input: ({ onChange, value, placeholder, ...props }: any) => (
    <input onChange={onChange} value={value} placeholder={placeholder} {...props} />
  ),
  VStack: ({ children }: any) => <div>{children}</div>,
  Text: ({ children }: any) => <span>{children}</span>,
  Alert: ({ children }: any) => <div role="alert">{children}</div>,
  AlertIcon: () => <span>!</span>,
  Heading: ({ children }: any) => <h1>{children}</h1>,
  Tabs: ({ children }: any) => <div>{children}</div>,
  TabList: ({ children }: any) => <div>{children}</div>,
  TabPanels: ({ children }: any) => <div>{children}</div>,
  Tab: ({ children, onClick }: any) => <button onClick={onClick}>{children}</button>,
  TabPanel: ({ children }: any) => <div>{children}</div>,
  Image: ({ alt }: any) => <img alt={alt} />,
  Flex: ({ children }: any) => <div>{children}</div>,
  Spacer: () => <div />,
}));

// Mock the auth components
jest.mock('../PasswordlessSignUp', () => ({
  PasswordlessSignUp: ({ onSuccess, onError }: any) => (
    <div>
      <h2>Nieuw Account Aanmaken</h2>
      <button onClick={() => onSuccess('test@example.com')}>Sign Up</button>
    </div>
  ),
}));

jest.mock('../PasskeySetup', () => ({
  PasskeySetup: ({ userEmail, onSuccess, onSkip, onError }: any) => (
    <div>
      <h2>Passkey Instellen</h2>
      <p>Stel een passkey in voor veilig en gemakkelijk inloggen</p>
      <button onClick={() => onSuccess()}>Setup Passkey</button>
      {onSkip && <button onClick={onSkip}>Skip</button>}
    </div>
  ),
}));

jest.mock('../CrossDeviceAuth', () => ({
  CrossDeviceAuth: ({ userEmail, onSuccess, onCancel, onError }: any) => (
    <div>
      <h2>Inloggen met Ander Apparaat</h2>
      <p>Gebruik een passkey die je op een ander apparaat hebt ingesteld</p>
      <button onClick={() => onSuccess({})}>Authenticate</button>
      <button onClick={onCancel}>Cancel</button>
    </div>
  ),
}));

jest.mock('../EmailRecovery', () => ({
  EmailRecovery: ({ onSuccess, onCancel, onError }: any) => (
    <div>
      <h2>Account Recovery</h2>
      <p>Enter your email address to receive recovery instructions</p>
      <button onClick={() => onSuccess()}>Recover</button>
      <button onClick={onCancel}>Cancel</button>
    </div>
  ),
}));

import { CustomAuthenticator } from '../CustomAuthenticator';
import { WebAuthnService } from '../../../services/webAuthnService';

// Mock AWS Amplify
jest.mock('aws-amplify/auth', () => ({
  getCurrentUser: jest.fn(),
  signIn: jest.fn(),
  signOut: jest.fn(),
}));

// Mock WebAuthnService
jest.mock('../../../services/webAuthnService', () => ({
  WebAuthnService: {
    isSupported: jest.fn(),
    shouldOfferCrossDeviceAuth: jest.fn(),
    authenticateWithPasskey: jest.fn(),
    credentialToJSON: jest.fn(),
  },
}));

// Mock fetch
global.fetch = jest.fn();

const mockChildren = jest.fn();

describe('CustomAuthenticator', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockChildren.mockReturnValue(<div>Authenticated Content</div>);
    (WebAuthnService.isSupported as jest.Mock).mockReturnValue(true);
    (WebAuthnService.shouldOfferCrossDeviceAuth as jest.Mock).mockReturnValue(true);
  });

  afterEach(() => {
    jest.resetAllMocks();
  });

  describe('Passwordless Authentication Flow', () => {
    test('renders sign-in form with passwordless options', async () => {
      const { getCurrentUser } = require('aws-amplify/auth');
      getCurrentUser.mockRejectedValue(new Error('Not authenticated'));

      render(<CustomAuthenticator>{mockChildren}</CustomAuthenticator>);

      await waitFor(() => {
        expect(screen.getByText('H-DCN Portal')).toBeInTheDocument();
        expect(screen.getByText('Inloggen')).toBeInTheDocument();
        expect(screen.getByPlaceholderText('Voer je e-mailadres in')).toBeInTheDocument();
        expect(screen.getByText('Inloggen met Passkey')).toBeInTheDocument();
        expect(screen.getByText('Passkey Instellen')).toBeInTheDocument();
        expect(screen.getByText('Cross-Device Authenticatie')).toBeInTheDocument();
        expect(screen.getByText('Account Herstellen via Email')).toBeInTheDocument();
      });
    });

    test('successful passkey authentication flow', async () => {
      const { getCurrentUser, signIn } = require('aws-amplify/auth');
      getCurrentUser.mockRejectedValueOnce(new Error('Not authenticated'));
      getCurrentUser.mockResolvedValueOnce({ username: 'test@example.com' });
      signIn.mockResolvedValue({ username: 'test@example.com' });

      // Mock successful passkey authentication
      (fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ challenge: 'test-challenge' }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ success: true }),
        });

      (WebAuthnService.authenticateWithPasskey as jest.Mock).mockResolvedValue({
        id: 'test-credential-id',
        response: {},
      });

      (WebAuthnService.credentialToJSON as jest.Mock).mockReturnValue({
        id: 'test-credential-id',
        response: {},
      });

      render(<CustomAuthenticator>{mockChildren}</CustomAuthenticator>);

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Voer je e-mailadres in')).toBeInTheDocument();
      });

      // Enter email and submit
      const emailInput = screen.getByPlaceholderText('Voer je e-mailadres in');
      await userEvent.type(emailInput, 'test@example.com');

      const signInButton = screen.getByText('Inloggen met Passkey');
      fireEvent.click(signInButton);

      // Should eventually show authenticated content
      await waitFor(() => {
        expect(mockChildren).toHaveBeenCalledWith({
          signOut: expect.any(Function),
          user: { username: 'test@example.com' },
        });
      });
    });

    test('redirects to passkey setup when no passkey is registered', async () => {
      const { getCurrentUser } = require('aws-amplify/auth');
      getCurrentUser.mockRejectedValue(new Error('Not authenticated'));

      // Mock no passkey registered response
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({ code: 'NO_PASSKEY_REGISTERED' }),
      });

      render(<CustomAuthenticator>{mockChildren}</CustomAuthenticator>);

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Voer je e-mailadres in')).toBeInTheDocument();
      });

      // Enter email and submit
      const emailInput = screen.getByPlaceholderText('Voer je e-mailadres in');
      await userEvent.type(emailInput, 'test@example.com');

      const signInButton = screen.getByText('Inloggen met Passkey');
      fireEvent.click(signInButton);

      // Should redirect to passkey setup
      await waitFor(() => {
        expect(screen.getByText('Passkey Instellen')).toBeInTheDocument();
        expect(screen.getByText('Stel een passkey in voor veilig en gemakkelijk inloggen')).toBeInTheDocument();
      });
    });

    test('shows passkey setup when "Passkey Instellen" button is clicked', async () => {
      const { getCurrentUser } = require('aws-amplify/auth');
      getCurrentUser.mockRejectedValue(new Error('Not authenticated'));

      render(<CustomAuthenticator>{mockChildren}</CustomAuthenticator>);

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Voer je e-mailadres in')).toBeInTheDocument();
      });

      // Enter email
      const emailInput = screen.getByPlaceholderText('Voer je e-mailadres in');
      await userEvent.type(emailInput, 'test@example.com');

      // Click passkey setup button
      const passkeySetupButton = screen.getByText('Passkey Instellen');
      fireEvent.click(passkeySetupButton);

      // Should show passkey setup component
      await waitFor(() => {
        expect(screen.getByText('Passkey Instellen')).toBeInTheDocument();
        expect(screen.getByText('Stel een passkey in voor veilig en gemakkelijk inloggen')).toBeInTheDocument();
      });
    });

    test('shows cross-device authentication when button is clicked', async () => {
      const { getCurrentUser } = require('aws-amplify/auth');
      getCurrentUser.mockRejectedValue(new Error('Not authenticated'));

      render(<CustomAuthenticator>{mockChildren}</CustomAuthenticator>);

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Voer je e-mailadres in')).toBeInTheDocument();
      });

      // Enter email
      const emailInput = screen.getByPlaceholderText('Voer je e-mailadres in');
      await userEvent.type(emailInput, 'test@example.com');

      // Click cross-device auth button
      const crossDeviceButton = screen.getByText('Cross-Device Authenticatie');
      fireEvent.click(crossDeviceButton);

      // Should show cross-device auth component
      await waitFor(() => {
        expect(screen.getByText('Inloggen met Ander Apparaat')).toBeInTheDocument();
        expect(screen.getByText('Gebruik een passkey die je op een ander apparaat hebt ingesteld')).toBeInTheDocument();
      });
    });

    test('shows email recovery when button is clicked', async () => {
      const { getCurrentUser } = require('aws-amplify/auth');
      getCurrentUser.mockRejectedValue(new Error('Not authenticated'));

      render(<CustomAuthenticator>{mockChildren}</CustomAuthenticator>);

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Voer je e-mailadres in')).toBeInTheDocument();
      });

      // Click email recovery button
      const emailRecoveryButton = screen.getByText('Account Herstellen via Email');
      fireEvent.click(emailRecoveryButton);

      // Should show email recovery component
      await waitFor(() => {
        expect(screen.getByText('Account Recovery')).toBeInTheDocument();
        expect(screen.getByText('Enter your email address to receive recovery instructions')).toBeInTheDocument();
      });
    });

    test('requires email for passkey setup', async () => {
      const { getCurrentUser } = require('aws-amplify/auth');
      getCurrentUser.mockRejectedValue(new Error('Not authenticated'));

      render(<CustomAuthenticator>{mockChildren}</CustomAuthenticator>);

      await waitFor(() => {
        expect(screen.getByText('Passkey Instellen')).toBeInTheDocument();
      });

      // Click passkey setup button without entering email
      const passkeySetupButton = screen.getByText('Passkey Instellen');
      fireEvent.click(passkeySetupButton);

      // Should show error message
      await waitFor(() => {
        expect(screen.getByText('Voer eerst je e-mailadres in')).toBeInTheDocument();
      });
    });

    test('requires email for cross-device authentication', async () => {
      const { getCurrentUser } = require('aws-amplify/auth');
      getCurrentUser.mockRejectedValue(new Error('Not authenticated'));

      render(<CustomAuthenticator>{mockChildren}</CustomAuthenticator>);

      await waitFor(() => {
        expect(screen.getByText('Cross-Device Authenticatie')).toBeInTheDocument();
      });

      // Click cross-device auth button without entering email
      const crossDeviceButton = screen.getByText('Cross-Device Authenticatie');
      fireEvent.click(crossDeviceButton);

      // Should show error message
      await waitFor(() => {
        expect(screen.getByText('Voer eerst je e-mailadres in voor cross-device authenticatie')).toBeInTheDocument();
      });
    });

    test('handles passkey authentication errors gracefully', async () => {
      const { getCurrentUser } = require('aws-amplify/auth');
      getCurrentUser.mockRejectedValue(new Error('Not authenticated'));

      // Mock passkey authentication failure
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ challenge: 'test-challenge' }),
      });

      (WebAuthnService.authenticateWithPasskey as jest.Mock).mockRejectedValue(
        new Error('Passkey authentication failed')
      );

      render(<CustomAuthenticator>{mockChildren}</CustomAuthenticator>);

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Voer je e-mailadres in')).toBeInTheDocument();
      });

      // Enter email and submit
      const emailInput = screen.getByPlaceholderText('Voer je e-mailadres in');
      await userEvent.type(emailInput, 'test@example.com');

      const signInButton = screen.getByText('Inloggen met Passkey');
      fireEvent.click(signInButton);

      // Should show error message
      await waitFor(() => {
        expect(screen.getByText(/Passkey authenticatie niet beschikbaar/)).toBeInTheDocument();
      });
    });

    test('shows registration tab and allows user registration', async () => {
      const { getCurrentUser } = require('aws-amplify/auth');
      getCurrentUser.mockRejectedValue(new Error('Not authenticated'));

      render(<CustomAuthenticator>{mockChildren}</CustomAuthenticator>);

      await waitFor(() => {
        expect(screen.getByText('Registreren')).toBeInTheDocument();
      });

      // Click registration tab
      const registerTab = screen.getByText('Registreren');
      fireEvent.click(registerTab);

      // Should show registration form
      await waitFor(() => {
        expect(screen.getByText('Nieuw Account Aanmaken')).toBeInTheDocument();
      });
    });
  });

  describe('Authentication State Management', () => {
    test('shows authenticated content when user is already signed in', async () => {
      const { getCurrentUser } = require('aws-amplify/auth');
      getCurrentUser.mockResolvedValue({ username: 'test@example.com' });

      render(<CustomAuthenticator>{mockChildren}</CustomAuthenticator>);

      await waitFor(() => {
        expect(mockChildren).toHaveBeenCalledWith({
          signOut: expect.any(Function),
          user: { username: 'test@example.com' },
        });
      });
    });

    test('handles sign out correctly', async () => {
      const { getCurrentUser, signOut } = require('aws-amplify/auth');
      getCurrentUser.mockResolvedValue({ username: 'test@example.com' });
      signOut.mockResolvedValue(undefined);

      render(<CustomAuthenticator>{mockChildren}</CustomAuthenticator>);

      await waitFor(() => {
        expect(mockChildren).toHaveBeenCalled();
      });

      // Get the signOut function from the mock call
      const signOutFn = mockChildren.mock.calls[0][0].signOut;
      
      // Call signOut
      await signOutFn();

      // Should call AWS signOut
      expect(signOut).toHaveBeenCalled();
    });
  });

  describe('WebAuthn Support Detection', () => {
    test('adapts UI when WebAuthn is not supported', async () => {
      const { getCurrentUser } = require('aws-amplify/auth');
      getCurrentUser.mockRejectedValue(new Error('Not authenticated'));
      (WebAuthnService.isSupported as jest.Mock).mockReturnValue(false);
      (WebAuthnService.shouldOfferCrossDeviceAuth as jest.Mock).mockReturnValue(false);

      render(<CustomAuthenticator>{mockChildren}</CustomAuthenticator>);

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Voer je e-mailadres in')).toBeInTheDocument();
      });

      // Should still show basic authentication options
      expect(screen.getByText('Inloggen met Passkey')).toBeInTheDocument();
      expect(screen.getByText('Account Herstellen via Email')).toBeInTheDocument();
      
      // Cross-device auth should not be available
      expect(screen.queryByText('Cross-Device Authenticatie')).not.toBeInTheDocument();
    });
  });
});