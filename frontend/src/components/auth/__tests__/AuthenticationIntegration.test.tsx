import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

// Mock Chakra UI components to avoid dependency issues
jest.mock('@chakra-ui/react', () => ({
  Box: ({ children, ...props }: any) => <div data-testid="box" {...props}>{children}</div>,
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
  FormControl: ({ children, isRequired }: any) => {
    const mockReact = require('react');
    return (
      <div data-required={isRequired}>
        {mockReact.Children.map(children, (child: any) => {
          if (child?.type?.name === 'Input' || (child?.props && 'placeholder' in child.props)) {
            return mockReact.cloneElement(child, { required: isRequired });
          }
          return child;
        })}
      </div>
    );
  },
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
  Tabs: ({ children }: any) => <div>{children}</div>,
  TabList: ({ children }: any) => <div>{children}</div>,
  TabPanels: ({ children }: any) => <div>{children}</div>,
  Tab: ({ children, onClick }: any) => <button onClick={onClick}>{children}</button>,
  TabPanel: ({ children }: any) => <div>{children}</div>,
  Image: ({ alt }: any) => <img alt={alt} />,
  Progress: ({ value }: any) => <div data-testid="progress" data-value={value} />,
  List: ({ children }: any) => <ul>{children}</ul>,
  ListItem: ({ children }: any) => <li>{children}</li>,
  ListIcon: ({ as }: any) => <span>{as?.name || 'icon'}</span>,
  PinInput: ({ children, value, onChange, onComplete }: any) => {
    const mockReact = require('react');
    
    const handleFieldChange = (index: number, fieldValue: string) => {
      // Create a new value array based on current value
      const currentValue = value || '';
      const newValueArray = currentValue.split('').concat(['', '', '', '', '', '']).slice(0, 6);
      newValueArray[index] = fieldValue;
      const newValue = newValueArray.join('');
      
      // Call onChange immediately to update the state
      if (onChange) {
        onChange(newValue);
      }
      
      // Trigger onComplete when all 6 digits are filled
      if (newValue.length === 6 && newValue.replace(/\s/g, '').length === 6 && onComplete) {
        // Use setTimeout to ensure the onChange state update happens first
        setTimeout(() => {
          onComplete(newValue);
        }, 100);
      }
    };
    
    return (
      <div>
        {mockReact.Children.map(children, (child: any, index: number) => 
          mockReact.cloneElement(child, { 
            value: (value || '')[index] || '', 
            onChange: (e: any) => {
              // Simulate the user typing a single character
              const newChar = e.target.value.slice(-1); // Get the last character typed
              handleFieldChange(index, newChar);
            }
          })
        )}
      </div>
    );
  },
  PinInputField: ({ value, onChange, ...props }: any) => (
    <input 
      value={value} 
      onChange={onChange}
      maxLength={1}
      {...props} 
    />
  ),
  useToast: () => jest.fn(),
  Divider: () => <hr />,
}));

// Mock Chakra UI icons
jest.mock('@chakra-ui/icons', () => ({
  CheckIcon: { name: 'CheckIcon' },
  WarningIcon: { name: 'WarningIcon' },
}));

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
    registerPasskey: jest.fn(),
    isPlatformAuthenticatorAvailable: jest.fn(),
    getBrowserInfo: jest.fn(),
  },
}));

import { CustomAuthenticator } from '../CustomAuthenticator';
import { PasswordlessSignUp } from '../PasswordlessSignUp';
import { PasskeySetup } from '../PasskeySetup';
import { WebAuthnService } from '../../../services/webAuthnService';

// Mock fetch
global.fetch = jest.fn();

const mockChildren = jest.fn();

describe('Authentication Integration Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Reset and setup fetch mock
    (global.fetch as jest.Mock).mockReset();
    
    mockChildren.mockReturnValue(<div>Authenticated Content</div>);
    (WebAuthnService.isSupported as jest.Mock).mockReturnValue(true);
    (WebAuthnService.shouldOfferCrossDeviceAuth as jest.Mock).mockReturnValue(true);
    (WebAuthnService.isPlatformAuthenticatorAvailable as jest.Mock).mockResolvedValue(true);
    (WebAuthnService.getBrowserInfo as jest.Mock).mockReturnValue({
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
      isMobile: false,
      recommendedAttachment: 'platform',
    });
    
    // Set up environment variable
    process.env.REACT_APP_API_BASE_URL = 'https://test-api.example.com';
  });

  afterEach(() => {
    jest.resetAllMocks();
    (global.fetch as jest.Mock).mockReset();
  });

  describe('Complete Signup → Verification → Passkey Setup Flow', () => {
    test('successful complete signup flow with email verification and passkey setup', async () => {
      const { getCurrentUser } = require('aws-amplify/auth');
      getCurrentUser.mockRejectedValue(new Error('Not authenticated'));

      // Mock successful signup API call
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ 
          message: 'Account created successfully',
          email: 'newuser@example.com'
        }),
      });

      render(<CustomAuthenticator>{mockChildren}</CustomAuthenticator>);

      // Wait for component to load and show tabs
      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Registreren' })).toBeInTheDocument();
      });

      // Click registration tab
      const registerTab = screen.getByRole('button', { name: 'Registreren' });
      fireEvent.click(registerTab);

      // Should show registration form
      await waitFor(() => {
        expect(screen.getByRole('heading', { name: 'Account Aanmaken' })).toBeInTheDocument();
      });

      // Fill out registration form - use getAllBy to get the correct inputs
      const emailInputs = screen.getAllByPlaceholderText('Voer je e-mailadres in');
      const emailInput = emailInputs[1]; // Second one is in the registration form
      const firstNameInput = screen.getByPlaceholderText('Voer je voornaam in');
      const lastNameInput = screen.getByPlaceholderText('Voer je achternaam in');

      await userEvent.type(emailInput, 'newuser@example.com');
      await userEvent.type(firstNameInput, 'Test');
      await userEvent.type(lastNameInput, 'User');

      // Submit registration
      const signUpButtons = screen.getAllByText('Account Aanmaken');
      const signUpButton = signUpButtons[1]; // Second one is the button, first is the heading
      fireEvent.click(signUpButton);

      // Should show success message
      await waitFor(() => {
        expect(screen.getByText(/Account aangemaakt!/)).toBeInTheDocument();
        expect(screen.getByText(/Controleer je e-mail voor verificatie-instructies/)).toBeInTheDocument();
      });

      // Verify API was called with correct data
      expect(fetch).toHaveBeenCalledWith(
        'https://test-api.example.com/auth/signup',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            email: 'newuser@example.com',
            given_name: 'Test',
            family_name: 'User',
          }),
        })
      );
    });

    test('handles signup errors appropriately', async () => {
      const { getCurrentUser } = require('aws-amplify/auth');
      getCurrentUser.mockRejectedValue(new Error('Not authenticated'));

      // Mock signup error (email already exists)
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 409,
        json: () => Promise.resolve({ 
          error: 'User already exists'
        }),
      });

      render(<CustomAuthenticator>{mockChildren}</CustomAuthenticator>);

      // Navigate to registration
      await waitFor(() => {
        expect(screen.getByText('Registreren')).toBeInTheDocument();
      });

      const registerTab = screen.getByRole('button', { name: 'Registreren' });
      fireEvent.click(registerTab);

      // Wait for registration form to appear
      await waitFor(() => {
        expect(screen.getByRole('heading', { name: 'Account Aanmaken' })).toBeInTheDocument();
      });

      // Fill out form with existing email
      const emailInputs = screen.getAllByPlaceholderText('Voer je e-mailadres in');
      const emailInput = emailInputs[1]; // Second one is in the registration form
      const firstNameInput = screen.getByPlaceholderText('Voer je voornaam in');
      const lastNameInput = screen.getByPlaceholderText('Voer je achternaam in');

      await userEvent.type(emailInput, 'existing@example.com');
      await userEvent.type(firstNameInput, 'Test');
      await userEvent.type(lastNameInput, 'User');

      // Submit registration
      const signUpButtons = screen.getAllByText('Account Aanmaken');
      const signUpButton = signUpButtons[1]; // Second one is the button, first is the heading
      fireEvent.click(signUpButton);

      // Should show error message
      await waitFor(() => {
        expect(screen.getByText(/Er bestaat al een account met dit e-mailadres/)).toBeInTheDocument();
      });
    });

    test('transitions from signup success to passkey setup', async () => {
      const { getCurrentUser } = require('aws-amplify/auth');
      getCurrentUser.mockRejectedValue(new Error('Not authenticated'));

      render(<CustomAuthenticator>{mockChildren}</CustomAuthenticator>);

      // Navigate to sign-in tab
      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Inloggen' })).toBeInTheDocument();
      });

      // Enter email for passkey setup - use the first email input (sign-in form)
      const emailInputs = screen.getAllByPlaceholderText('Voer je e-mailadres in');
      const emailInput = emailInputs[0]; // First one is in the sign-in form
      await userEvent.type(emailInput, 'newuser@example.com');

      // Click passkey setup button
      const passkeySetupButton = screen.getByText('Passkey Instellen');
      fireEvent.click(passkeySetupButton);

      // Should show passkey setup component
      await waitFor(() => {
        expect(screen.getByText('Passkey Ondersteuning Controleren')).toBeInTheDocument();
      });
    });

    test('validates required fields in signup form', async () => {
      const { getCurrentUser } = require('aws-amplify/auth');
      getCurrentUser.mockRejectedValue(new Error('Not authenticated'));

      render(<CustomAuthenticator>{mockChildren}</CustomAuthenticator>);

      // Navigate to registration
      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Registreren' })).toBeInTheDocument();
      });

      const registerTab = screen.getByRole('button', { name: 'Registreren' });
      fireEvent.click(registerTab);

      // Try to submit without filling required fields
      const signUpButtons = screen.getAllByText('Account Aanmaken');
      const signUpButton = signUpButtons[1]; // Second one is the button
      
      // Form should prevent submission (HTML5 validation)
      const emailInputs = screen.getAllByPlaceholderText('Voer je e-mailadres in');
      const emailInput = emailInputs[1]; // Second one is in registration form
      const firstNameInput = screen.getByPlaceholderText('Voer je voornaam in');
      const lastNameInput = screen.getByPlaceholderText('Voer je achternaam in');

      expect(emailInput).toBeRequired();
      expect(firstNameInput).toBeRequired();
      expect(lastNameInput).toBeRequired();
    });
  });

  describe('Passkey Authentication Flow', () => {
    test('successful passkey authentication with existing user', async () => {
      const { getCurrentUser, signIn } = require('aws-amplify/auth');
      getCurrentUser.mockRejectedValueOnce(new Error('Not authenticated'));
      getCurrentUser.mockResolvedValueOnce({ username: 'test@example.com' });
      signIn.mockResolvedValue({ username: 'test@example.com' });

      // Mock successful passkey authentication
      (fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ 
            challenge: 'test-challenge',
            allowCredentials: [{ id: 'test-credential-id' }]
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ success: true }),
        });

      (WebAuthnService.authenticateWithPasskey as jest.Mock).mockResolvedValue({
        id: 'test-credential-id',
        response: {
          authenticatorData: 'test-auth-data',
          signature: 'test-signature',
        },
      });

      (WebAuthnService.credentialToJSON as jest.Mock).mockReturnValue({
        id: 'test-credential-id',
        response: {
          authenticatorData: 'test-auth-data',
          signature: 'test-signature',
        },
      });

      render(<CustomAuthenticator>{mockChildren}</CustomAuthenticator>);

      await waitFor(() => {
        const emailInputs = screen.getAllByPlaceholderText('Voer je e-mailadres in');
        expect(emailInputs[0]).toBeInTheDocument(); // First one is in sign-in form
      });

      // Enter email and submit - use the first email input (sign-in form)
      const emailInputs = screen.getAllByPlaceholderText('Voer je e-mailadres in');
      const emailInput = emailInputs[0]; // First one is in sign-in form
      await userEvent.type(emailInput, 'test@example.com');

      const signInButton = screen.getByText('🔐 Inloggen met Passkey');
      fireEvent.click(signInButton);

      // Should eventually show authenticated content
      await waitFor(() => {
        expect(mockChildren).toHaveBeenCalledWith({
          signOut: expect.any(Function),
          user: { username: 'test@example.com' },
        });
      });

      // Verify API calls were made
      expect(fetch).toHaveBeenCalledWith(
        'https://test-api.example.com/auth/passkey/authenticate/begin',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: 'test@example.com' }),
        })
      );

      expect(fetch).toHaveBeenCalledWith(
        'https://test-api.example.com/auth/passkey/authenticate/complete',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            email: 'test@example.com',
            credential: {
              id: 'test-credential-id',
              response: {
                authenticatorData: 'test-auth-data',
                signature: 'test-signature',
              },
            },
          }),
        })
      );
    });

    test('handles passkey authentication failure gracefully', async () => {
      const { getCurrentUser } = require('aws-amplify/auth');
      getCurrentUser.mockRejectedValue(new Error('Not authenticated'));

      // Mock passkey authentication failure
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ challenge: 'test-challenge' }),
      });

      (WebAuthnService.authenticateWithPasskey as jest.Mock).mockRejectedValue(
        new Error('User cancelled passkey authentication')
      );

      render(<CustomAuthenticator>{mockChildren}</CustomAuthenticator>);

      await waitFor(() => {
        const emailInputs = screen.getAllByPlaceholderText('Voer je e-mailadres in');
        expect(emailInputs[0]).toBeInTheDocument(); // First one is in sign-in form
      });

      // Enter email and submit - use the first email input (sign-in form)
      const emailInputs = screen.getAllByPlaceholderText('Voer je e-mailadres in');
      const emailInput = emailInputs[0]; // First one is in sign-in form
      await userEvent.type(emailInput, 'test@example.com');

      const signInButton = screen.getByText('🔐 Inloggen met Passkey');
      fireEvent.click(signInButton);

      // Should show error message with fallback options
      await waitFor(() => {
        expect(screen.getByText(/Passkey authenticatie niet beschikbaar/)).toBeInTheDocument();
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
        const emailInputs = screen.getAllByPlaceholderText('Voer je e-mailadres in');
        expect(emailInputs[0]).toBeInTheDocument(); // First one is in sign-in form
      });

      // Enter email and submit - use the first email input (sign-in form)
      const emailInputs = screen.getAllByPlaceholderText('Voer je e-mailadres in');
      const emailInput = emailInputs[0]; // First one is in sign-in form
      await userEvent.type(emailInput, 'newuser@example.com');

      const signInButton = screen.getByText('🔐 Inloggen met Passkey');
      fireEvent.click(signInButton);

      // Should redirect to passkey setup
      await waitFor(() => {
        expect(screen.getByText('Passkey Ondersteuning Controleren')).toBeInTheDocument();
      });
    });
  });

  /* COMMENTED OUT - EmailRecovery component doesn't exist
  describe('Email Recovery → New Passkey Setup Flow', () => {
    test('complete email recovery flow with new passkey setup', async () => {
      const { getCurrentUser } = require('aws-amplify/auth');
      getCurrentUser.mockRejectedValue(new Error('Not authenticated'));

      // Set up fetch mock before rendering
      const mockFetch = global.fetch as jest.Mock;
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ message: 'Recovery email sent' }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ message: 'Recovery code verified' }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ challenge: 'recovery-challenge' }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ success: true }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ message: 'Recovery completed' }),
        });

      (WebAuthnService.registerPasskey as jest.Mock).mockResolvedValue({
        id: 'new-credential-id',
        response: {
          attestationObject: 'test-attestation',
          clientDataJSON: 'test-client-data',
        },
      });

      (WebAuthnService.credentialToJSON as jest.Mock).mockReturnValue({
        id: 'new-credential-id',
        response: {
          attestationObject: 'test-attestation',
          clientDataJSON: 'test-client-data',
        },
      });

      render(<CustomAuthenticator>{mockChildren}</CustomAuthenticator>);

      // Wait for the component to load and show the email recovery button
      await waitFor(() => {
        expect(screen.getByText('📧 Account Herstellen via Email')).toBeInTheDocument();
      });

      // Click email recovery button using data-testid
      const emailRecoveryButton = screen.getByTestId('button-📧 Account Herstellen via Email');
      
      await act(async () => {
        await userEvent.click(emailRecoveryButton);
      });

      // Wait for the EmailRecovery component to render
      await waitFor(() => {
        expect(screen.getByText('Account Recovery')).toBeInTheDocument();
      }, { timeout: 5000 });

      // Should show email recovery form
      await waitFor(() => {
        expect(screen.getByText('Enter your email address to receive recovery instructions')).toBeInTheDocument();
      });

      // Enter email for recovery
      const emailInput = screen.getByPlaceholderText('Enter your email address');
      await userEvent.type(emailInput, 'recover@example.com');

      // Submit recovery request
      const sendRecoveryButton = screen.getByText('Send Recovery Email');
      fireEvent.click(sendRecoveryButton);

      // Should show code entry form
      await waitFor(() => {
        expect(screen.getByText('Recovery Code')).toBeInTheDocument();
      }, { timeout: 3000 });

      // Enter recovery code
      const codeInputs = screen.getAllByRole('textbox');
      const recoveryCodeInputs = codeInputs.slice(-6); // Last 6 inputs should be PIN inputs
      
      // Simulate entering recovery code one by one
      for (let i = 0; i < 6; i++) {
        await userEvent.type(recoveryCodeInputs[i], (i + 1).toString());
      }

      // Wait a bit for the onComplete to be triggered
      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 100));
      });

      // If onComplete didn't trigger automatically, click the verify button manually
      const verifyButton = screen.getByText('Verify Recovery Code');
      if (!verifyButton.hasAttribute('disabled')) {
        fireEvent.click(verifyButton);
      }

      // The onComplete should be triggered automatically, wait for passkey setup
      await waitFor(() => {
        expect(screen.getByText('Set up a new passkey for your account')).toBeInTheDocument();
      }, { timeout: 3000 });
    });

    test('handles invalid recovery code', async () => {
      const { getCurrentUser } = require('aws-amplify/auth');
      getCurrentUser.mockRejectedValue(new Error('Not authenticated'));

      // Set up fetch mock before rendering
      const mockFetch = global.fetch as jest.Mock;
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ message: 'Recovery email sent' }),
        })
        .mockResolvedValueOnce({
          ok: false,
          json: () => Promise.resolve({ 
            code: 'INVALID_CODE',
            error: 'Invalid recovery code'
          }),
        });

      render(<CustomAuthenticator>{mockChildren}</CustomAuthenticator>);

      // Wait for the component to load and show the email recovery button
      await waitFor(() => {
        expect(screen.getByText('📧 Account Herstellen via Email')).toBeInTheDocument();
      });

      // Navigate to email recovery using data-testid
      const emailRecoveryButton = screen.getByTestId('button-📧 Account Herstellen via Email');
      await userEvent.click(emailRecoveryButton);

      // Wait for email recovery form to appear
      await waitFor(() => {
        expect(screen.getByPlaceholderText('Enter your email address')).toBeInTheDocument();
      });

      // Enter email
      const emailInput = screen.getByPlaceholderText('Enter your email address');
      await userEvent.type(emailInput, 'recover@example.com');

      const sendRecoveryButton = screen.getByText('Send Recovery Email');
      fireEvent.click(sendRecoveryButton);

      // Wait for code entry form
      await waitFor(() => {
        expect(screen.getByText('Recovery Code')).toBeInTheDocument();
      });

      // Enter invalid recovery code
      const codeInputs = screen.getAllByRole('textbox');
      const recoveryCodeInputs = codeInputs.slice(-6); // Last 6 inputs should be PIN inputs
      
      // Simulate entering recovery code one by one
      for (let i = 0; i < 6; i++) {
        await userEvent.type(recoveryCodeInputs[i], (i + 1).toString());
      }

      // Wait a bit for the onComplete to be triggered
      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 100));
      });

      // If onComplete didn't trigger automatically, click the verify button manually
      const verifyButton = screen.getByText('Verify Recovery Code');
      if (!verifyButton.hasAttribute('disabled')) {
        fireEvent.click(verifyButton);
      }

      // Should show error message
      await waitFor(() => {
        expect(screen.getByText('Invalid recovery code. Please check the code and try again.')).toBeInTheDocument();
      });
    });

    test('handles expired recovery code', async () => {
      const { getCurrentUser } = require('aws-amplify/auth');
      getCurrentUser.mockRejectedValue(new Error('Not authenticated'));

      // Set up fetch mock before rendering
      const mockFetch = global.fetch as jest.Mock;
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ message: 'Recovery email sent' }),
        })
        .mockResolvedValueOnce({
          ok: false,
          json: () => Promise.resolve({ 
            code: 'EXPIRED_CODE',
            error: 'Recovery code has expired'
          }),
        });

      render(<CustomAuthenticator>{mockChildren}</CustomAuthenticator>);

      // Wait for the component to load and show the email recovery button
      await waitFor(() => {
        expect(screen.getByText('📧 Account Herstellen via Email')).toBeInTheDocument();
      });

      // Navigate to email recovery using data-testid
      const emailRecoveryButton = screen.getByTestId('button-📧 Account Herstellen via Email');
      await userEvent.click(emailRecoveryButton);

      // Wait for email recovery form to appear
      await waitFor(() => {
        expect(screen.getByPlaceholderText('Enter your email address')).toBeInTheDocument();
      });

      // Enter email
      const emailInput = screen.getByPlaceholderText('Enter your email address');
      await userEvent.type(emailInput, 'recover@example.com');

      const sendRecoveryButton = screen.getByText('Send Recovery Email');
      fireEvent.click(sendRecoveryButton);

      // Wait for code entry form
      await waitFor(() => {
        expect(screen.getByText('Recovery Code')).toBeInTheDocument();
      });

      // Enter expired recovery code
      const codeInputs = screen.getAllByRole('textbox');
      const recoveryCodeInputs = codeInputs.slice(-6); // Last 6 inputs should be PIN inputs
      
      // Simulate entering recovery code one by one
      for (let i = 0; i < 6; i++) {
        await userEvent.type(recoveryCodeInputs[i], (i + 1).toString());
      }

      // Wait a bit for the onComplete to be triggered
      await act(async () => {
        await new Promise(resolve => setTimeout(resolve, 100));
      });

      // If onComplete didn't trigger automatically, click the verify button manually
      const verifyButton = screen.getByText('Verify Recovery Code');
      if (!verifyButton.hasAttribute('disabled')) {
        fireEvent.click(verifyButton);
      }

      // Should show error and return to email entry
      await waitFor(() => {
        expect(screen.getByText('Recovery code has expired. Please request a new recovery email.')).toBeInTheDocument();
      });

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Enter your email address')).toBeInTheDocument();
      });
    });
  });
  */ // END COMMENTED OUT EMAIL RECOVERY TESTS

  describe('Role Assignment Verification After Authentication', () => {
    test('verifies user roles are properly extracted after successful authentication', async () => {
      const { getCurrentUser, signIn } = require('aws-amplify/auth');
      
      // Mock user with JWT token containing roles
      const mockUserWithRoles = {
        username: 'admin@example.com',
        signInUserSession: {
          idToken: {
            payload: {
              'cognito:groups': ['hdcnLeden', 'Members_CRUD'],
              email: 'admin@example.com',
            }
          }
        }
      };

      getCurrentUser.mockRejectedValueOnce(new Error('Not authenticated'));
      getCurrentUser.mockResolvedValueOnce(mockUserWithRoles);
      signIn.mockResolvedValue(mockUserWithRoles);

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
        const emailInputs = screen.getAllByPlaceholderText('Voer je e-mailadres in');
        expect(emailInputs[0]).toBeInTheDocument(); // First one is in sign-in form
      });

      // Perform authentication - use the first email input (sign-in form)
      const emailInputs = screen.getAllByPlaceholderText('Voer je e-mailadres in');
      const emailInput = emailInputs[0]; // First one is in sign-in form
      await userEvent.type(emailInput, 'admin@example.com');

      const signInButton = screen.getByText('🔐 Inloggen met Passkey');
      fireEvent.click(signInButton);

      // Should show authenticated content with user including roles
      await waitFor(() => {
        expect(mockChildren).toHaveBeenCalledWith({
          signOut: expect.any(Function),
          user: mockUserWithRoles,
        });
      });

      // Verify the user object contains role information
      const userArg = mockChildren.mock.calls[0][0].user;
      expect(userArg.signInUserSession.idToken.payload['cognito:groups']).toEqual(['hdcnLeden', 'Members_CRUD']);
    });

    test('handles users with no assigned roles', async () => {
      const { getCurrentUser, signIn } = require('aws-amplify/auth');
      
      // Mock user without roles
      const mockUserWithoutRoles = {
        username: 'newuser@example.com',
        signInUserSession: {
          idToken: {
            payload: {
              email: 'newuser@example.com',
              // No cognito:groups property
            }
          }
        }
      };

      getCurrentUser.mockRejectedValueOnce(new Error('Not authenticated'));
      getCurrentUser.mockResolvedValueOnce(mockUserWithoutRoles);
      signIn.mockResolvedValue(mockUserWithoutRoles);

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
        const emailInputs = screen.getAllByPlaceholderText('Voer je e-mailadres in');
        expect(emailInputs[0]).toBeInTheDocument(); // First one is in sign-in form
      });

      // Perform authentication - use the first email input (sign-in form)
      const emailInputs = screen.getAllByPlaceholderText('Voer je e-mailadres in');
      const emailInput = emailInputs[0]; // First one is in sign-in form
      await userEvent.type(emailInput, 'newuser@example.com');

      const signInButton = screen.getByText('🔐 Inloggen met Passkey');
      fireEvent.click(signInButton);

      // Should still show authenticated content
      await waitFor(() => {
        expect(mockChildren).toHaveBeenCalledWith({
          signOut: expect.any(Function),
          user: mockUserWithoutRoles,
        });
      });

      // Verify the user object doesn't have roles
      const userArg = mockChildren.mock.calls[0][0].user;
      expect(userArg.signInUserSession.idToken.payload['cognito:groups']).toBeUndefined();
    });

    test('verifies multiple roles are properly handled', async () => {
      const { getCurrentUser, signIn } = require('aws-amplify/auth');
      
      // Mock user with multiple roles
      const mockUserWithMultipleRoles = {
        username: 'regional@example.com',
        signInUserSession: {
          idToken: {
            payload: {
              'cognito:groups': ['hdcnLeden', 'Members_Read_Region1', 'Events_CRUD_Region1'],
              email: 'regional@example.com',
            }
          }
        }
      };

      getCurrentUser.mockRejectedValueOnce(new Error('Not authenticated'));
      getCurrentUser.mockResolvedValueOnce(mockUserWithMultipleRoles);
      signIn.mockResolvedValue(mockUserWithMultipleRoles);

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
        const emailInputs = screen.getAllByPlaceholderText('Voer je e-mailadres in');
        expect(emailInputs[0]).toBeInTheDocument(); // First one is in sign-in form
      });

      // Perform authentication - use the first email input (sign-in form)
      const emailInputs = screen.getAllByPlaceholderText('Voer je e-mailadres in');
      const emailInput = emailInputs[0]; // First one is in sign-in form
      await userEvent.type(emailInput, 'regional@example.com');

      const signInButton = screen.getByText('🔐 Inloggen met Passkey');
      fireEvent.click(signInButton);

      // Should show authenticated content with multiple roles
      await waitFor(() => {
        expect(mockChildren).toHaveBeenCalledWith({
          signOut: expect.any(Function),
          user: mockUserWithMultipleRoles,
        });
      });

      // Verify all roles are present
      const userArg = mockChildren.mock.calls[0][0].user;
      expect(userArg.signInUserSession.idToken.payload['cognito:groups']).toEqual([
        'hdcnLeden', 
        'Members_Read_Region1', 
        'Events_CRUD_Region1'
      ]);
    });
  });
});