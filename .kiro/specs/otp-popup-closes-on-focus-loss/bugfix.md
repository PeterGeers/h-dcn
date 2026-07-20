# Bugfix Requirements Document

## Introduction

When users sign in with a passkey on a new platform (or as a new user), Cognito sends a 6-digit email OTP code. The current implementation uses `window.prompt()` to collect this code. On mobile browsers (iOS Safari, Android) and some desktop configurations, switching to another tab or app to retrieve the email causes the native prompt dialog to close. The user loses the input and cannot complete authentication.

The root cause is `handleOtpCodeEntry()` in `CustomAuthenticator.tsx` using `prompt()` — a blocking synchronous browser dialog that gets dismissed on focus loss, especially on mobile platforms.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN the user is prompted for an OTP code via `window.prompt()` AND switches to another browser tab or app to check their email THEN the system dismisses the prompt dialog and the user cannot enter the code

1.2 WHEN the user is prompted for an OTP code via `window.prompt()` AND a browser extension or popup blocker interferes THEN the system either blocks the prompt or returns null, preventing code entry

1.3 WHEN the user dismisses or loses the `window.prompt()` dialog (intentionally or via focus loss) THEN the system shows an error "code required" with no way to re-enter the code without restarting the entire sign-in flow

### Expected Behavior (Correct)

2.1 WHEN the system receives a `CONFIRM_SIGN_IN_WITH_EMAIL_CODE` challenge from Cognito, THE system SHALL render an inline OTP input form (a text input field restricted to 6 numeric digits and a submit button) within the existing login page DOM, replacing the `window.prompt()` call

2.2 WHILE the inline OTP input form is displayed AND the user switches to another browser tab or app and returns, THE system SHALL keep the OTP input form and any previously entered characters visible and editable in the page

2.3 WHEN the inline OTP input form is displayed, THE system SHALL show instructional text indicating that a verification code was sent to the user's email address

2.4 WHILE the system is awaiting the `confirmSignIn` response after the user submits the OTP code, THE system SHALL disable the submit button and input field to prevent duplicate submissions

2.5 IF the user submits a value that is not exactly 6 numeric digits (0-9), THEN THE system SHALL display a validation error and keep the input form visible so the user can correct and resubmit

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a valid 6-digit OTP code is submitted, THE system SHALL CONTINUE TO call `confirmSignIn({ challengeResponse: code })` and complete authentication on success

3.2 WHEN an expired OTP code is submitted, THE system SHALL CONTINUE TO show a code expired error with a resend option

3.3 WHEN the user submits an empty code (input field is blank or contains only whitespace), THE system SHALL CONTINUE TO show the "code required" error and keep the OTP input form visible for retry

3.4 WHEN the WebAuthn passkey sign-in succeeds without requiring an OTP step, THE system SHALL CONTINUE TO authenticate without showing any OTP input

3.5 WHEN a network error occurs during OTP confirmation, THE system SHALL CONTINUE TO show the network error message and keep the OTP input form visible for retry

3.6 WHEN the user clicks "Resend Code", THE system SHALL CONTINUE TO re-initiate the sign-in flow and present a fresh OTP input form with the input field cleared

---

## Bug Condition (Formal)

```pascal
FUNCTION isBugCondition(X)
  INPUT: X of type OtpEntryContext
  OUTPUT: boolean

  RETURN X.otpEntryMethod = "window.prompt" AND (X.focusLost = true OR X.popupBlocked = true)
END FUNCTION
```

```pascal
// Property: Fix Checking - OTP input persists across focus changes
FOR ALL X WHERE isBugCondition(X) DO
  result ← showOtpInput'(X)
  ASSERT result.inputVisible = true AND result.userCanEnterCode = true
END FOR
```

```pascal
// Property: Preservation Checking - Existing auth flows unchanged
FOR ALL X WHERE NOT isBugCondition(X) DO
  ASSERT F(X) = F'(X)
END FOR
```
