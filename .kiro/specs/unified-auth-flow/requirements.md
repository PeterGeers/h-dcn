# Requirements: Unified Authentication Flow

## Core Concept

Two login paths, one outcome.

```
PATH 1: Passkey                         PATH 2: Google SSO
───────────────                         ────────────────
User enters email                       User clicks "Google"
  │                                       │
  ├─ Has passkey → WebAuthn               └─ Google authenticates
  │                                          Cognito links to user
  └─ No passkey → Email OTP code             (email verified by Google)
     (verifies email ownership +
      one-time, to set up passkey)
  │                                       │
  ▼                                       ▼
┌─────────────────────────────────────────────────────┐
│                                                     │
│  OUTCOME: Identified user with valid credentials    │
│  - verified email (unique identifier)               │
│  - groups (permissions/roles)                       │
│  - valid JWT token for API calls                    │
│                                                     │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
                 App starts with
                 correct permissions
```

## What's Broken

Google SSO bypasses Amplify. The resulting token has no `cognito:groups`. So an admin user (webmaster@h-dcn.nl) logging in via Google gets treated as unknown — redirected to the new member application form.

## Requirements

### R1: Two login paths, one outcome — with verified email

- R1.1: Passkey login (with Email OTP fallback) results in an Amplify session with a JWT containing `cognito:groups` and a verified email.
- R1.2: Google SSO login results in the same Amplify session with a JWT containing `cognito:groups` and a verified email (Google guarantees email ownership).
- R1.3: After authentication (either path), the app receives: verified `email`, `groups[]`, and a valid `accessToken` — always the same structure.
- R1.4: A user cannot reach the app without a verified email address. Email verification is inherent to both paths: Path 1 verifies via the OTP code sent to the email; Path 2 is verified by Google.

### R2: Google SSO must go through Amplify

- R2.1: "Login with Google" uses Amplify's `signInWithRedirect({ provider: 'Google' })`.
- R2.2: Amplify handles the OAuth callback, token exchange, and session storage automatically.
- R2.3: Amplify config (`aws-exports.ts`) includes an `oauth` section with Cognito domain, callback URLs, and Google as provider.
- R2.4: The manual OAuth flow (OAuthCallback.tsx, manual token exchange, hardcoded groups fallback) is removed.

### R3: Passkey with Email OTP fallback (email verification built-in)

- R3.1: User enters email → system tries WebAuthn (passkey) first.
- R3.2: If WebAuthn fails → automatic fallback to Email OTP. The OTP code sent to the email serves as email verification — proving the user owns that address.
- R3.3: After first successful Email OTP login → offer passkey registration for future logins.
- R3.4: Passkey registration can be skipped.
- R3.5: A passkey can only be registered after the email is verified (i.e., after successful OTP login). No passkey without proven email ownership.

### R4: Session is the single source of truth

- R4.1: Auth state comes from `fetchAuthSession()` — not from localStorage.
- R4.2: User groups come from the access token payload — not from manual JWT decoding or hardcoded fallbacks.
- R4.3: API calls use the access token from `fetchAuthSession()` — not from localStorage.
- R4.4: Token refresh is handled automatically by Amplify.

### R5: Cognito app client configuration

- R5.1: App client supports OAuth authorization_code flow with Google as identity provider.
- R5.2: Access tokens issued via OAuth are JWTs (not opaque) containing `cognito:groups`.
- R5.3: Callback URLs include production (`https://portal.h-dcn.nl/`) and development (`http://localhost:3000/`).

### R6: What gets removed

- R6.1: `OAuthCallback.tsx` — Amplify handles the callback.
- R6.2: Manual URL construction in `GoogleSignInButton.tsx` — replaced by `signInWithRedirect()`.
- R6.3: localStorage auth state (`hdcn_auth_user`, `hdcn_auth_tokens`) — Amplify manages the session.
- R6.4: The non-existent backend call to `/hdcn-cognito-admin/get-user-groups`.
- R6.5: Hardcoded group assignments per email (webmaster fallback).
- R6.6: Duplicate JWT decoding in GroupAccessGuard, Dashboard, authHeaders — replaced by one central source.

### R7: What stays the same

- R7.1: Login page UI (email field, passkey button, Google button).
- R7.2: Cognito triggers (PreSignUp links Google to native user, PostAuthentication assigns groups).
- R7.3: Backend JWT validation (shared auth_utils layer).
- R7.4: PasskeySetup component (already uses `associateWebAuthnCredential()`).

### R9: Error handling — user-facing feedback

- R9.1: If Google SSO fails (user denies consent, Google is unreachable, or Cognito rejects the token), the user is returned to the login page with a clear error message — not a blank screen or infinite spinner.
- R9.2: If Email OTP delivery fails or the code expires, the user can request a new code without re-entering their email.
- R9.3: If WebAuthn fails (hardware not available, user cancels), the system falls back to Email OTP automatically — no manual intervention required.
- R9.4: If `fetchAuthSession()` fails during an active session (token refresh failure, user revoked from Cognito), the user is redirected to the login page with a message indicating they need to sign in again.
- R9.5: Network errors during authentication show a retry-friendly message, not a technical error dump.

### R10: Sign-out behavior

- R10.1: Sign-out clears the local Amplify session (tokens, user data).
- R10.2: For Google SSO users, sign-out also ends the Cognito hosted UI session (prevents auto-re-login via cached Cognito session cookie).
- R10.3: After sign-out, the user is returned to the login page and must explicitly choose a login method again — no automatic re-authentication.

### Out of scope

- Changes to Cognito User Pool configuration (triggers, groups, users) beyond what's needed for OAuth.
- Changes to DynamoDB data or member records.
- Adding new login methods.
- Changes to admin panel or user management.

### R8: Handover to app — acceptance criteria

- R8.1: After authentication, GroupAccessGuard continues to correctly route users based on `cognito:groups` from the JWT — existing routing logic must keep working.
- R8.2: After authentication, new user registration flow (PasswordlessSignUp → verzoek_lid group assignment) continues to work for users who don't yet have an account.
- R8.3: The JWT provided to the app contains all information needed for these app-level decisions — no additional backend calls required to determine user permissions.

## Summary

One change with big impact: **route Google SSO through Amplify** instead of handling it manually. Everything else (session management, group extraction, token refresh) then works automatically — just like it already does for Passkey/Email OTP.
