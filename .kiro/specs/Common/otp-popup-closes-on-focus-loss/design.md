# OTP Popup Closes on Focus Loss — Bugfix Design

## Overview

The `handleOtpCodeEntry()` function in `CustomAuthenticator.tsx` uses `window.prompt()` to collect a 6-digit OTP code from the user. On mobile browsers and some desktop configurations, switching tabs or apps to check email causes the native prompt dialog to close, preventing authentication completion. The fix replaces the synchronous blocking `window.prompt()` with an inline React form rendered within the existing component DOM using Chakra UI, so that the input persists across focus changes.

## Glossary

- **Bug_Condition (C)**: The condition that triggers the bug — `window.prompt()` is used for OTP entry and gets dismissed on focus loss or popup blocking
- **Property (P)**: The desired behavior — an inline OTP input form persists in the DOM regardless of tab/app switching and allows code submission
- **Preservation**: Existing authentication flows (successful OTP submission, expired code handling, network error handling, resend code, passkey-only sign-in) must remain unchanged
- **handleOtpCodeEntry()**: The function in `CustomAuthenticator.tsx` that currently calls `window.prompt()` and then `confirmSignIn()`
- **authState**: The React state variable controlling which view the component renders (`'signIn' | 'signUp' | 'passkeySetup' | 'debug'`); fix adds `'otpEntry'`
- **confirmSignIn**: The AWS Amplify v6 function that submits the OTP challenge response to Cognito

## Bug Details

### Bug Condition

The bug manifests when Cognito returns a `CONFIRM_SIGN_IN_WITH_EMAIL_CODE` challenge and the component calls `window.prompt()` to collect the code. On mobile browsers (iOS Safari, Android Chrome) and some desktop configurations, switching to another tab or app to retrieve the email causes the browser to dismiss the native prompt dialog. The user loses any entered input and cannot complete authentication without restarting the sign-in flow.

**Formal Specification:**

```
FUNCTION isBugCondition(input)
  INPUT: input of type OtpEntryContext
  OUTPUT: boolean

  RETURN input.otpEntryMethod = "window.prompt"
         AND (input.focusLost = true OR input.popupBlocked = true)
END FUNCTION
```

### Examples

- **Mobile Safari**: User taps "Sign In", receives OTP challenge, `prompt()` appears, user swaps to Mail app to copy code → prompt is dismissed → error "code required" with no retry path
- **Android Chrome**: Same flow — switching apps causes Activity lifecycle to dismiss the prompt dialog
- **Desktop with popup blocker**: Some browser extensions or strict popup settings block `window.prompt()` entirely, returning `null` immediately
- **Desktop normal focus loss**: User clicks outside the prompt on some browsers → prompt dismissed, code entry lost

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**

- Successful OTP submission (`confirmSignIn({ challengeResponse: code })`) must continue to authenticate the user
- Expired code errors must continue to show the "code expired" message with a "Resend Code" button
- Network errors during confirmation must continue to display the network error message
- Empty/whitespace code submission must continue to show "code required" error
- Passkey-only sign-in (no OTP step) must continue to authenticate without showing any OTP input
- "Resend Code" must continue to re-initiate the sign-in flow and present a fresh input
- Google SSO flow must remain completely unaffected
- Sign-up flow and passkey setup flow must remain unchanged

**Scope:**
All inputs that do NOT involve the OTP code entry step should be completely unaffected by this fix. This includes:

- Email submission (sign-in form)
- WebAuthn/passkey authentication
- Google SSO authentication
- Sign-up registration flow
- Passkey setup flow
- Debug mode

## Hypothesized Root Cause

Based on the code analysis, the root cause is clear and singular:

1. **Use of `window.prompt()`**: The `handleOtpCodeEntry()` function (line ~99) calls `prompt(t('verification.enter_code'))` which creates a synchronous blocking browser dialog. This dialog is:
   - Dismissed on focus loss in mobile browsers (iOS Safari, Android Chrome)
   - Dismissed when switching apps (mobile Activity/ViewController lifecycle)
   - Potentially blocked by browser extensions or popup blockers
   - Not part of the React component tree (cannot be controlled or persisted by React)

2. **Synchronous blocking pattern**: Because `prompt()` blocks the JavaScript thread, the entire auth flow (`handleOtpCodeEntry` is `async`) is coupled to the prompt being open. Once dismissed, the function receives `null` and shows "code required" with no way to retry without restarting.

3. **No intermediate state**: The component has no `authState` value representing "waiting for OTP input", so once the prompt is dismissed there is no mechanism to re-present the input without re-triggering the entire sign-in flow.

## Correctness Properties

Property 1: Bug Condition - OTP Input Persists Across Focus Loss

_For any_ OTP entry context where the system has received a `CONFIRM_SIGN_IN_WITH_EMAIL_CODE` challenge and the user switches tabs/apps or loses window focus, the fixed component SHALL keep the OTP input form visible and editable in the DOM, preserving any characters already entered.

**Validates: Requirements 2.1, 2.2**

Property 2: Preservation - Existing Auth Flows Unchanged

_For any_ authentication interaction that does NOT involve the OTP code entry display mechanism (successful submission, error handling, resend, passkey auth, Google SSO), the fixed code SHALL produce exactly the same behavior as the original code, preserving all existing functionality.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**

## Fix Implementation

### Changes Required

**File**: `frontend/src/components/auth/CustomAuthenticator.tsx`

**Function**: `handleOtpCodeEntry()` — to be replaced with state transition + inline form

**Specific Changes**:

1. **Add `'otpEntry'` to authState type**: Extend the state union from `'signIn' | 'signUp' | 'passkeySetup' | 'debug'` to include `'otpEntry'`

2. **Add OTP-specific state variables**:
   - `otpCode: string` — the 6-digit input value
   - `otpError: string` — validation/submission error specific to OTP form
   - `otpSubmitting: boolean` — loading state during `confirmSignIn` call

3. **Replace `handleOtpCodeEntry()` body**: Instead of calling `prompt()`, set `authState` to `'otpEntry'`. This transitions the UI to render the inline OTP form.

4. **Add `handleOtpSubmit()` function**: Validates the input (exactly 6 numeric digits), calls `confirmSignIn({ challengeResponse: otpCode })`, handles success/error responses (expired code, network error, generic failure). On error, keeps the form visible for retry.

5. **Add inline OTP form rendering**: When `authState === 'otpEntry'`, render a Chakra UI form with:
   - Instructional `Text` explaining a verification code was sent to email
   - `Input` field (type text, inputMode numeric, maxLength 6, pattern `[0-9]*`)
   - Validation error display (for non-6-digit input)
   - Submit `Button` (disabled during submission, shows loading state)
   - Error `Alert` for expired/network/invalid code errors
   - "Resend Code" `Button` (calls existing `handleResendCode`, resets form state)

6. **Update `handleResendCode()`**: After re-initiating sign-in, instead of calling `handleOtpCodeEntry()` (which would prompt), set `authState` to `'otpEntry'` and clear `otpCode`/`otpError`.

7. **Use i18n translation keys**: All user-facing strings use `t()` from the `'auth'` namespace (keys like `verification.enter_code`, `verification.instructions`, `verification.submit`, `errors.invalid_code_format`).

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code, then verify the fix works correctly and preserves existing behavior.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm that `window.prompt()` is indeed the mechanism used and that it returns `null` when dismissed.

**Test Plan**: Write unit tests that mock `window.prompt` to return `null` (simulating focus-loss dismissal) and verify the component enters an unrecoverable error state. Run on UNFIXED code.

**Test Cases**:

1. **Prompt returns null (focus loss)**: Mock `prompt()` to return `null` → assert "code required" error with no retry mechanism (will fail to provide a good UX on unfixed code)
2. **Prompt returns empty string**: Mock `prompt()` to return `''` → assert same dead-end behavior
3. **Prompt blocked entirely**: Mock `prompt()` to throw → assert component error state
4. **Multiple rapid focus losses**: Simulate prompt returning `null` repeatedly → assert user stuck in error loop

**Expected Counterexamples**:

- `window.prompt()` returns `null` when dismissed on focus loss → user sees "code required" error with no inline retry
- The component has no `'otpEntry'` state → no way to re-present the input form

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed function produces the expected behavior.

**Pseudocode:**

```
FOR ALL input WHERE isBugCondition(input) DO
  result := renderOtpForm(input)
  ASSERT result.inputVisible = true
  ASSERT result.inputEditable = true
  ASSERT result.previousInputPreserved = true
  ASSERT result.submitButtonPresent = true
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed function produces the same result as the original function.

**Pseudocode:**

```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT originalBehavior(input) = fixedBehavior(input)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:

- It generates many random OTP codes and validates that submission logic remains correct
- It catches edge cases in validation (whitespace, non-numeric characters, length boundaries)
- It provides strong guarantees that non-OTP-display auth flows are unchanged

**Test Plan**: Observe behavior on UNFIXED code for successful submissions, error handling, and non-OTP flows, then write property-based tests capturing that behavior.

**Test Cases**:

1. **Successful OTP submission preservation**: Verify that submitting a valid 6-digit code still calls `confirmSignIn` and completes auth
2. **Error handling preservation**: Verify expired code, network error, and invalid code errors still display correctly with retry
3. **Passkey auth preservation**: Verify passkey-only sign-in still works without showing OTP form
4. **Google SSO preservation**: Verify Google sign-in path is completely unaffected
5. **Resend code preservation**: Verify "Resend Code" re-initiates sign-in and presents fresh input

### Unit Tests

- Test that `authState` transitions to `'otpEntry'` when `CONFIRM_SIGN_IN_WITH_EMAIL_CODE` challenge is received
- Test OTP form rendering: input field, submit button, instructional text all present
- Test validation: non-numeric input shows error, <6 digits shows error, >6 digits prevented
- Test successful submission: valid code → `confirmSignIn` called → auth completes
- Test error states: expired code → error + resend button, network error → error + retry, invalid code → error + retry
- Test form persistence: component re-render does not lose input value (simulates focus events)
- Test disabled state: input and button disabled during submission

### Property-Based Tests

- Generate random 6-character strings and verify only strings matching `/^[0-9]{6}$/` pass validation
- Generate random auth states and verify OTP form only renders when `authState === 'otpEntry'`
- Generate random error types and verify correct error messages are displayed for each

### Integration Tests

- Test full sign-in flow: email → WebAuthn fails → OTP challenge → OTP form renders → submit code → authenticated
- Test resend flow: OTP form → resend → new challenge → form clears and reappears
- Test tab switching simulation: OTP form rendered → blur/focus events → form still present with input preserved
