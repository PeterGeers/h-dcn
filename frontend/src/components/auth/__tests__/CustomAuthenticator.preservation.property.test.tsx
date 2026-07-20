import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { ChakraProvider } from '@chakra-ui/react';
import * as fc from 'fast-check';
import { CustomAuthenticator } from '../CustomAuthenticator';

/**
 * Property 2: Preservation — Existing Auth Flows Unchanged
 *
 * Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6
 *
 * These property-based tests capture the baseline behavior that MUST be preserved
 * after the OTP bug fix. The code path changed from window.prompt() to an inline
 * OTP form, but the preservation properties still hold:
 * - Valid 6-digit code → confirmSignIn called with that code
 * - Invalid/empty code → validation error shown
 * - Expired code → code_expired error + resend option
 * - Network error → network error shown
 * - Non-OTP flows → no OTP form rendered
 */

// --- Mocks ---

const mockSignIn = jest.fn();
const mockConfirmSignIn = jest.fn();

jest.mock('aws-amplify/auth', () => ({
  signIn: (...args: any[]) => mockSignIn(...args),
  confirmSignIn: (...args: any[]) => mockConfirmSignIn(...args),
}));

jest.mock('aws-amplify/utils', () => ({
  Hub: {
    listen: jest.fn().mockReturnValue(() => {}),
  },
}));

jest.mock('../../../hooks/useAuth', () => ({
  useAuth: () => ({
    user: null,
    isLoading: false,
    isAuthenticated: false,
    error: null,
    signOut: jest.fn(),
  }),
}));

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: 'nl', changeLanguage: jest.fn() },
  }),
}));

// --- Helpers ---

function renderAuthenticator() {
  return render(
    <ChakraProvider>
      <CustomAuthenticator>
        {({ signOut, user }) => <div data-testid="authenticated">Authenticated</div>}
      </CustomAuthenticator>
    </ChakraProvider>
  );
}

async function submitSignInForm(container: HTMLElement, email: string) {
  const emailInput = container.querySelector('input[name="email"]') as HTMLInputElement;
  fireEvent.change(emailInput, { target: { value: email } });

  const form = emailInput.closest('form')!;
  await act(async () => {
    fireEvent.submit(form);
  });
}

/**
 * After sign-in triggers OTP challenge, the inline OTP form is rendered.
 * This helper types the code into the OTP input and clicks submit.
 */
async function submitOtpCode(code: string) {
  const otpInput = await screen.findByTestId('otp-input');
  fireEvent.change(otpInput, { target: { value: code } });

  const submitBtn = screen.getByTestId('otp-submit');
  await act(async () => {
    fireEvent.click(submitBtn);
  });
}

// --- Arbitraries ---

/** Generates valid 6-digit OTP codes (strings matching /^[0-9]{6}$/) */
const validOtpCodeArb = fc.stringOf(
  fc.constantFrom('0', '1', '2', '3', '4', '5', '6', '7', '8', '9'),
  { minLength: 6, maxLength: 6 }
);

// --- Property Tests ---

describe('CustomAuthenticator Preservation Properties', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Property 2.1: Valid 6-digit OTP codes call confirmSignIn with correct challengeResponse', () => {
    /**
     * **Validates: Requirements 3.1**
     *
     * For all strings matching /^[0-9]{6}$/, when the user submits the code
     * via the inline OTP form, confirmSignIn is called with that code as challengeResponse.
     */
    it('for all valid 6-digit codes, confirmSignIn is called with that code', async () => {
      await fc.assert(
        fc.asyncProperty(validOtpCodeArb, async (code) => {
          jest.clearAllMocks();

          // Mock signIn to trigger OTP challenge
          mockSignIn.mockRejectedValueOnce(new Error('WebAuthn not available'));
          mockSignIn.mockResolvedValueOnce({
            isSignedIn: false,
            nextStep: { signInStep: 'CONFIRM_SIGN_IN_WITH_EMAIL_CODE' },
          });

          // Mock confirmSignIn to succeed
          mockConfirmSignIn.mockResolvedValueOnce({ isSignedIn: true });

          const { unmount, container } = renderAuthenticator();
          await submitSignInForm(container, 'test@example.com');

          // Wait for the OTP form to appear
          await screen.findByTestId('otp-input');

          // Type the code and submit
          await submitOtpCode(code);

          // Wait for confirmSignIn to be called
          await waitFor(() => {
            expect(mockConfirmSignIn).toHaveBeenCalled();
          });

          // Verify confirmSignIn was called with the exact code
          expect(mockConfirmSignIn).toHaveBeenCalledWith({ challengeResponse: code });

          unmount();
        }),
        { numRuns: 20 }
      );
    });
  });

  describe('Property 2.2: Empty/invalid code submission shows validation error', () => {
    /**
     * **Validates: Requirements 3.3**
     *
     * When the user submits an empty or invalid code via the inline form,
     * a validation error is displayed and confirmSignIn is NOT called.
     * (Previously this was tested via window.prompt returning null/empty.)
     */
    it('when empty or invalid code is submitted, validation error is shown', async () => {
      const invalidValues = ['', '   ', '12345', 'abcdef', '12345a'];

      for (const invalidValue of invalidValues) {
        jest.clearAllMocks();

        mockSignIn.mockRejectedValueOnce(new Error('WebAuthn not available'));
        mockSignIn.mockResolvedValueOnce({
          isSignedIn: false,
          nextStep: { signInStep: 'CONFIRM_SIGN_IN_WITH_EMAIL_CODE' },
        });

        const { unmount, container } = renderAuthenticator();
        await submitSignInForm(container, 'test@example.com');

        // Wait for the OTP form to appear
        await screen.findByTestId('otp-input');

        // Submit with the invalid value
        await submitOtpCode(invalidValue);

        // Wait for the validation error to appear
        await waitFor(() => {
          expect(screen.getByText('errors.invalid_code_format')).toBeInTheDocument();
        });

        // confirmSignIn should NOT be called when code is invalid
        expect(mockConfirmSignIn).not.toHaveBeenCalled();

        unmount();
      }
    });
  });

  describe('Property 2.3: Expired code triggers code_expired error with resend option', () => {
    /**
     * **Validates: Requirements 3.2**
     *
     * When confirmSignIn throws a code expired error, the component shows
     * the "code expired" error message and provides a resend option.
     */
    it('for valid codes where confirmSignIn throws expired error, code_expired is shown', async () => {
      await fc.assert(
        fc.asyncProperty(validOtpCodeArb, async (code) => {
          jest.clearAllMocks();

          mockSignIn.mockRejectedValueOnce(new Error('WebAuthn not available'));
          mockSignIn.mockResolvedValueOnce({
            isSignedIn: false,
            nextStep: { signInStep: 'CONFIRM_SIGN_IN_WITH_EMAIL_CODE' },
          });

          // Mock confirmSignIn to throw expired code error
          const expiredError = new Error('Code has expired');
          expiredError.name = 'ExpiredCodeException';
          mockConfirmSignIn.mockRejectedValueOnce(expiredError);

          const { unmount, container } = renderAuthenticator();
          await submitSignInForm(container, 'test@example.com');

          // Wait for the OTP form to appear
          await screen.findByTestId('otp-input');

          // Submit a valid code
          await submitOtpCode(code);

          await waitFor(() => {
            expect(screen.getByText('errors.code_expired')).toBeInTheDocument();
          });

          // Resend code button should be visible
          expect(screen.getByText('verification.resend_code')).toBeInTheDocument();

          unmount();
        }),
        { numRuns: 10 }
      );
    });
  });

  describe('Property 2.4: Network error during confirmation shows network error', () => {
    /**
     * **Validates: Requirements 3.5**
     *
     * When confirmSignIn throws a network error, the component shows
     * the network error message.
     */
    it('for valid codes where confirmSignIn throws network error, errors.network_error is shown', async () => {
      await fc.assert(
        fc.asyncProperty(validOtpCodeArb, async (code) => {
          jest.clearAllMocks();

          mockSignIn.mockRejectedValueOnce(new Error('WebAuthn not available'));
          mockSignIn.mockResolvedValueOnce({
            isSignedIn: false,
            nextStep: { signInStep: 'CONFIRM_SIGN_IN_WITH_EMAIL_CODE' },
          });

          // Mock confirmSignIn to throw network error
          const networkError = new Error('Failed to fetch');
          networkError.name = 'NetworkError';
          mockConfirmSignIn.mockRejectedValueOnce(networkError);

          const { unmount, container } = renderAuthenticator();
          await submitSignInForm(container, 'test@example.com');

          // Wait for the OTP form to appear
          await screen.findByTestId('otp-input');

          // Submit a valid code
          await submitOtpCode(code);

          await waitFor(() => {
            expect(screen.getByText('errors.network_error')).toBeInTheDocument();
          });

          unmount();
        }),
        { numRuns: 10 }
      );
    });
  });

  describe('Property 2.5: Passkey-only sign-in authenticates without OTP form', () => {
    /**
     * **Validates: Requirements 3.4**
     *
     * For auth flows that do NOT produce CONFIRM_SIGN_IN_WITH_EMAIL_CODE challenge
     * (passkey succeeds directly), no OTP input form is rendered.
     */
    it('when passkey sign-in succeeds directly, no OTP form is shown and auth completes', async () => {
      jest.clearAllMocks();

      // Mock signIn to succeed immediately (passkey success)
      mockSignIn.mockResolvedValueOnce({
        isSignedIn: true,
      });

      const { container } = renderAuthenticator();
      await submitSignInForm(container, 'passkey-user@example.com');

      // Wait for the flow to complete
      await waitFor(() => {
        expect(mockSignIn).toHaveBeenCalled();
      });

      // No OTP form should be rendered
      expect(screen.queryByTestId('otp-input')).not.toBeInTheDocument();
      // confirmSignIn should not be called for direct passkey auth
      expect(mockConfirmSignIn).not.toHaveBeenCalled();
    });

    it('for arbitrary non-OTP challenge steps, no OTP form is rendered', async () => {
      const nonOtpSteps = [
        'CONFIRM_SIGN_UP',
      ];

      for (const step of nonOtpSteps) {
        jest.clearAllMocks();

        // First signIn call (WebAuthn) fails, second (EMAIL_OTP fallback) returns non-OTP step
        mockSignIn.mockRejectedValueOnce(new Error('WebAuthn not available'));
        mockSignIn.mockResolvedValueOnce({
          isSignedIn: false,
          nextStep: { signInStep: step },
        });

        const { unmount, container } = renderAuthenticator();
        await submitSignInForm(container, 'user@example.com');

        await waitFor(() => {
          expect(mockSignIn).toHaveBeenCalledTimes(2);
        });

        // No OTP form for non-OTP steps
        expect(screen.queryByTestId('otp-input')).not.toBeInTheDocument();

        unmount();
      }
    });
  });
});
