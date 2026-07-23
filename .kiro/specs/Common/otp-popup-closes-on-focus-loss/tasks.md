# Implementation Plan

## Overview

Replace `window.prompt()` OTP code entry in `CustomAuthenticator.tsx` with an inline Chakra UI form that persists across tab/app switches. Uses the bug condition methodology: explore the bug with tests first, write preservation tests, implement the fix, then validate.

## Tasks

- [x] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - OTP Prompt Dismissed on Focus Loss
  - **IMPORTANT**: Write this property-based test BEFORE implementing the fix
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - **Scoped PBT Approach**: Scope the property to the concrete failing case — when `handleOtpCodeEntry()` is invoked and `window.prompt()` returns `null` (simulating focus loss/popup blocking), the component should render an inline OTP input form that persists in the DOM
  - Test file: `frontend/src/components/auth/__tests__/CustomAuthenticator.otpBugCondition.property.test.tsx`
  - Use `fast-check` to generate arbitrary 6-digit OTP codes and focus-loss scenarios
  - Mock `window.prompt` to return `null` (simulating dismissal on focus loss)
  - Mock Amplify `signIn` to return `CONFIRM_SIGN_IN_WITH_EMAIL_CODE` challenge
  - Assert: after challenge received, an inline OTP input form is rendered (input field + submit button visible in DOM)
  - Assert: the input form persists after simulated blur/focus events
  - Run test on UNFIXED code with: `npx react-scripts test --watchAll=false --testPathPattern="CustomAuthenticator.otpBugCondition.property"`
  - **EXPECTED OUTCOME**: Test FAILS (unfixed code uses `window.prompt()` instead of inline form — no OTP input element exists in the DOM after prompt returns null)
  - Document counterexamples: `window.prompt()` returns `null` on focus loss → component shows "code required" error with no inline retry mechanism
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Existing Auth Flows Unchanged
  - **IMPORTANT**: Follow observation-first methodology
  - Test file: `frontend/src/components/auth/__tests__/CustomAuthenticator.preservation.property.test.tsx`
  - Use `fast-check` for property-based testing
  - Observe on UNFIXED code: (1) submitting a valid 6-digit code calls `confirmSignIn({ challengeResponse: code })` and completes auth, (2) expired code triggers "code expired" error with resend option, (3) network error during confirmation shows network error message, (4) empty/whitespace code submission shows "code required" error, (5) passkey-only sign-in (no OTP step) authenticates without showing OTP UI
  - Write property-based tests: (1) for all strings matching `/^[0-9]{6}$/`, `confirmSignIn` is called with that code as `challengeResponse`, (2) for all strings NOT matching `/^[0-9]{6}$/` (non-numeric, wrong length, whitespace), validation rejects and form remains visible, (3) for all auth flows that do NOT produce `CONFIRM_SIGN_IN_WITH_EMAIL_CODE` challenge, no OTP input is rendered
  - Run tests on UNFIXED code with: `npx react-scripts test --watchAll=false --testPathPattern="CustomAuthenticator.preservation.property"`
  - **EXPECTED OUTCOME**: Tests PASS (confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

- [x] 3. Fix for OTP popup closes on focus loss
  - [x] 3.1 Extend `authState` type and add OTP state variables
    - Add `'otpEntry'` to the authState union type: `'signIn' | 'signUp' | 'passkeySetup' | 'debug' | 'otpEntry'`
    - Add state variables: `otpCode: string`, `otpError: string`, `otpSubmitting: boolean`
    - _Bug_Condition: isBugCondition(input) where input.otpEntryMethod = "window.prompt" AND (input.focusLost = true OR input.popupBlocked = true)_
    - _Requirements: 2.1_

  - [x] 3.2 Replace `handleOtpCodeEntry()` with state transition
    - Remove `window.prompt()` call from `handleOtpCodeEntry()`
    - Instead, set `authState` to `'otpEntry'` to transition UI to inline OTP form
    - Clear any previous `otpCode` and `otpError` state
    - _Bug_Condition: isBugCondition(input) — eliminates window.prompt entirely_
    - _Expected_Behavior: When CONFIRM_SIGN_IN_WITH_EMAIL_CODE challenge received, render inline OTP form in DOM_
    - _Preservation: Non-OTP auth flows (passkey, Google SSO, sign-up) remain unaffected_
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2_

  - [x] 3.3 Implement `handleOtpSubmit()` function
    - Validate input: exactly 6 numeric digits (`/^[0-9]{6}$/`), show validation error if invalid
    - Set `otpSubmitting: true`, disable input and button
    - Call `confirmSignIn({ challengeResponse: otpCode })`
    - On success: complete authentication (existing flow)
    - On expired code error: show "code expired" message with resend option
    - On network error: show network error, keep form visible for retry
    - On generic failure: show error, keep form visible for retry
    - Set `otpSubmitting: false` after response
    - _Expected_Behavior: Valid 6-digit code submitted → confirmSignIn called → auth completes on success_
    - _Preservation: Error handling matches existing behavior (expired, network, invalid codes)_
    - _Requirements: 2.4, 2.5, 3.1, 3.2, 3.3, 3.5_

  - [x] 3.4 Add inline OTP form rendering (Chakra UI)
    - Render when `authState === 'otpEntry'`
    - Instructional `Text` component: verification code sent to email (use `t('verification.instructions')`)
    - `Input` field: type text, inputMode numeric, maxLength 6, pattern `[0-9]*`, autoFocus
    - Validation error display below input (for non-6-digit input)
    - Submit `Button`: disabled during submission, shows loading spinner via `isLoading` prop
    - Error `Alert` for expired/network/invalid code errors
    - "Resend Code" `Button`: calls existing resend flow, clears form state
    - All strings use `useTranslation('auth')` with appropriate keys
    - _Expected_Behavior: Inline form persists in DOM regardless of tab/app switching_
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 3.5 Update `handleResendCode()` for inline flow
    - After re-initiating sign-in, set `authState` to `'otpEntry'` (not calling `handleOtpCodeEntry`)
    - Clear `otpCode` and `otpError` state for fresh input
    - _Preservation: Resend behavior unchanged — re-initiates sign-in and presents fresh input_
    - _Requirements: 3.6_

  - [x] 3.6 Add translation keys to all 8 locales
    - Add keys to `frontend/src/locales/{lang}/auth.json` AND `frontend/public/locales/{lang}/auth.json` for all 8 languages (nl, en, de, fr, es, it, da, sv)
    - Keys to add: `verification.instructions`, `verification.submit`, `verification.resend`, `errors.invalid_code_format`, `errors.code_expired`, `errors.network_error`
    - _Requirements: 2.3, 2.5_

  - [x] 3.7 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - OTP Input Persists Across Focus Loss
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior (inline OTP form in DOM)
    - When this test passes, it confirms the expected behavior is satisfied
    - Run: `npx react-scripts test --watchAll=false --testPathPattern="CustomAuthenticator.otpBugCondition.property"`
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed — inline form now renders instead of window.prompt)
    - _Requirements: 2.1, 2.2_

  - [x] 3.8 Verify preservation tests still pass
    - **Property 2: Preservation** - Existing Auth Flows Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run: `npx react-scripts test --watchAll=false --testPathPattern="CustomAuthenticator.preservation.property"`
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all preservation tests still pass after fix (no regressions in OTP submission, error handling, passkey auth)

- [x] 4. Checkpoint - Ensure all tests pass
  - Run type check: `npx tsc --noEmit` (from frontend/)
  - Run ESLint on modified file: `npx eslint src/components/auth/CustomAuthenticator.tsx`
  - Run bug condition test: `npx react-scripts test --watchAll=false --testPathPattern="CustomAuthenticator.otpBugCondition.property"`
  - Run preservation test: `npx react-scripts test --watchAll=false --testPathPattern="CustomAuthenticator.preservation.property"`
  - Verify all translations are present in all 8 locales (both src/ and public/)
  - Ensure all tests pass, ask the user if questions arise.

## Task Dependency Graph

## Task Dependency Graph

```json
{
  "waves": [
    ["1", "2"],
    ["3.1"],
    ["3.2"],
    ["3.3"],
    ["3.4"],
    ["3.5"],
    ["3.6"],
    ["3.7"],
    ["3.8"],
    ["4"]
  ]
}
```

## Notes

- Tests 1 and 2 can be written in parallel (no dependency between them)
- Task 1 is expected to FAIL on unfixed code (confirms bug exists) — do not attempt to fix
- Task 2 must PASS on unfixed code (captures baseline behavior to preserve)
- All frontend commands run from `frontend/` directory
- Translation keys must be added to both `src/locales/` and `public/locales/` (runtime loads from public/)
