import React from 'react';
import { render, screen, act, fireEvent } from '@testing-library/react';
import { ChakraProvider } from '@chakra-ui/react';
import * as fc from 'fast-check';
import { CustomAuthenticator } from '../CustomAuthenticator';

/**
 * Bug Condition Exploration Property Test
 *
 * **Validates: Requirements 1.1, 1.2, 1.3, 2.1, 2.2**
 *
 * Property: When window.prompt() returns null (simulating focus loss / popup blocking)
 * after receiving a CONFIRM_SIGN_IN_WITH_EMAIL_CODE challenge, the component should
 * render an inline OTP input form that persists in the DOM.
 *
 * EXPECTED TO FAIL on unfixed code — the current implementation uses window.prompt()
 * which returns null on focus loss, showing a "code required" error with no inline retry.
 */

// Mock aws-amplify/auth
const mockSignIn = jest.fn();
const mockConfirmSignIn = jest.fn();

jest.mock('aws-amplify/auth', () => ({
  fetchAuthSession: jest.fn().mockResolvedValue({ tokens: undefined }),
  signOut: jest.fn().mockResolvedValue(undefined),
  signIn: (...args: any[]) => mockSignIn(...args),
  confirmSignIn: (...args: any[]) => mockConfirmSignIn(...args),
}));

// Mock aws-amplify/utils
jest.mock('aws-amplify/utils', () => ({
  Hub: {
    listen: jest.fn().mockReturnValue(() => {}),
  },
}));

// Mock useAuth hook
jest.mock('../../../hooks/useAuth', () => ({
  useAuth: () => ({
    user: null,
    isLoading: false,
    isAuthenticated: false,
    error: null,
    signOut: jest.fn(),
  }),
}));

// Mock react-i18next
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: 'nl', changeLanguage: jest.fn() },
  }),
}));

describe('Bug Condition: OTP Prompt Dismissed on Focus Loss', () => {
  let originalPrompt: typeof window.prompt;

  beforeEach(() => {
    originalPrompt = window.prompt;
    jest.clearAllMocks();
  });

  afterEach(() => {
    window.prompt = originalPrompt;
  });

  /**
   * Property 1: When the system receives a CONFIRM_SIGN_IN_WITH_EMAIL_CODE challenge
   * and window.prompt returns null (focus loss), an inline OTP input form should be
   * rendered in the DOM with a text input and submit button.
   *
   * **Validates: Requirements 1.1, 1.2, 1.3, 2.1, 2.2**
   */
  it('should render an inline OTP input form when prompt returns null (focus loss)', async () => {
    await fc.assert(
      fc.asyncProperty(
        // Generate arbitrary 8-digit OTP codes (Cognito sends 8-digit codes)
        fc.stringMatching(/^[0-9]{8}$/),
        // Generate focus-loss scenarios (true = prompt returns null)
        fc.constant(true),
        async (otpCode, focusLost) => {
          // Mock window.prompt to return null (simulating focus loss/popup blocking)
          window.prompt = jest.fn().mockReturnValue(null);

          // Mock signIn to return CONFIRM_SIGN_IN_WITH_EMAIL_CODE challenge
          mockSignIn.mockResolvedValue({
            isSignedIn: false,
            nextStep: {
              signInStep: 'CONFIRM_SIGN_IN_WITH_EMAIL_CODE',
            },
          });

          const { container, unmount } = render(
            <ChakraProvider>
              <CustomAuthenticator>
                {({ signOut, user }) => <div data-testid="authenticated">Authenticated</div>}
              </CustomAuthenticator>
            </ChakraProvider>
          );

          // Fill in email and submit the sign-in form
          const emailInput = container.querySelector('input[type="email"]');
          expect(emailInput).toBeTruthy();

          await act(async () => {
            fireEvent.change(emailInput!, { target: { value: 'test@example.com' } });
          });

          const form = container.querySelector('form');
          await act(async () => {
            fireEvent.submit(form!);
          });

          // Wait for async operations to complete
          await act(async () => {
            await new Promise(resolve => setTimeout(resolve, 100));
          });

          // PROPERTY ASSERTION: After challenge received and prompt returns null,
          // an inline OTP input form should be visible in the DOM
          // Look for an input that could accept OTP code (text/number input with maxLength 6
          // or inputMode numeric, or a dedicated OTP input)
          const otpInput = container.querySelector(
            'input[maxlength="6"], input[inputmode="numeric"], input[data-testid="otp-input"], input[type="text"][pattern]'
          );
          const submitButton = container.querySelector(
            'button[type="submit"]:not([disabled]), button[data-testid="otp-submit"]'
          );

          // The inline OTP form must exist in the DOM
          expect(otpInput).toBeTruthy();
          expect(submitButton).toBeTruthy();

          unmount();
        }
      ),
      { numRuns: 5 } // Keep runs low since we're testing UI rendering
    );
  });

  /**
   * Property 2: The inline OTP input form persists after simulated blur/focus events.
   * After the OTP challenge is received and the form is rendered, switching tabs
   * (blur/focus) should NOT cause the form to disappear.
   *
   * **Validates: Requirements 2.2**
   */
  it('should persist inline OTP input form after blur/focus events', async () => {
    await fc.assert(
      fc.asyncProperty(
        // Generate arbitrary scenarios with different timing
        fc.integer({ min: 50, max: 200 }),
        async (blurDelay) => {
          // Mock window.prompt to return null (simulating focus loss)
          window.prompt = jest.fn().mockReturnValue(null);

          // Mock signIn to return OTP challenge
          mockSignIn.mockResolvedValue({
            isSignedIn: false,
            nextStep: {
              signInStep: 'CONFIRM_SIGN_IN_WITH_EMAIL_CODE',
            },
          });

          const { container, unmount } = render(
            <ChakraProvider>
              <CustomAuthenticator>
                {({ signOut, user }) => <div>Authenticated</div>}
              </CustomAuthenticator>
            </ChakraProvider>
          );

          // Fill in email and submit
          const emailInput = container.querySelector('input[type="email"]');
          await act(async () => {
            fireEvent.change(emailInput!, { target: { value: 'user@h-dcn.nl' } });
          });

          const form = container.querySelector('form');
          await act(async () => {
            fireEvent.submit(form!);
          });

          await act(async () => {
            await new Promise(resolve => setTimeout(resolve, 100));
          });

          // Simulate blur/focus (tab switching)
          await act(async () => {
            fireEvent.blur(window);
            await new Promise(resolve => setTimeout(resolve, blurDelay));
            fireEvent.focus(window);
          });

          // PROPERTY ASSERTION: OTP input form must still be present after blur/focus
          const otpInput = container.querySelector(
            'input[maxlength="6"], input[inputmode="numeric"], input[data-testid="otp-input"], input[type="text"][pattern]'
          );

          expect(otpInput).toBeTruthy();

          unmount();
        }
      ),
      { numRuns: 3 }
    );
  });
});
