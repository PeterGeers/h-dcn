# Implementation Plan: Unified Authentication Flow

## Overview

Route Google SSO through Amplify v6's `signInWithRedirect` so both login paths (Passkey/OTP and Google SSO) produce the same Amplify-managed session. Replace scattered localStorage-based auth logic with a central AuthProvider that uses `fetchAuthSession()` as the single source of truth.

## Tasks

- [x] 1. Update Amplify configuration with OAuth settings
  - [x] 1.1 Add OAuth section to `aws-exports.ts`
    - Add `loginWith.oauth` block with Cognito domain, scopes, redirect URLs, responseType `code`, and Google provider
    - Ensure the config shape matches Amplify v6 `ResourcesConfig` format
    - _Requirements: R2.3, R5.1, R5.2, R5.3_

  - [x] 1.2 Update `Amplify.configure()` call in `index.tsx`
    - Ensure `Amplify.configure(awsconfig)` correctly picks up the new OAuth config
    - Verify no duplicate or conflicting configuration exists
    - _Requirements: R2.2, R2.3_

- [x] 2. Create AuthProvider and useAuth hook
  - [x] 2.1 Create `AuthProvider.tsx` in `src/context/`
    - Define `AuthUser` interface: `{ email, givenName?, familyName?, sub, groups[], accessToken }`
    - Define `AuthContextType`: `{ user, isLoading, isAuthenticated, error, signOut }`
    - On mount: call `fetchAuthSession()` to check for existing session
    - Extract user info from tokens (email from ID token, groups from access token)
    - Listen to Hub `auth` events: `signedIn`, `signedOut`, `tokenRefresh`, `tokenRefresh_failure`, `signIn_failure`
    - Handle OAuth callback errors (user denies consent, Cognito rejects token) via `signIn_failure` Hub event
    - Implement sign-out: clear local Amplify session + redirect to Cognito hosted UI logout endpoint
    - _Requirements: R4.1, R4.2, R4.4, R9.1, R9.4, R9.5, R10.1, R10.2, R10.3_

  - [x] 2.2 Rewrite `useAuth.ts` hook in `src/hooks/`
    - Return `AuthContextType` from AuthProvider context
    - Throw clear error if used outside AuthProvider
    - _Requirements: R4.1, R4.2_

  - [x]\* 2.3 Write unit tests for AuthProvider
    - Test: mount with no session → `user: null`, `isLoading: false`
    - Test: mount with valid session → extracts email, groups, accessToken correctly
    - Test: Hub `signedIn` event → fetches session and sets user
    - Test: Hub `tokenRefresh_failure` → clears user, sets error message
    - Test: Hub `signIn_failure` → sets error state with user-friendly message
    - Test: `signOut()` calls Amplify signOut and redirects to Cognito logout
    - _Requirements: R4.1, R4.2, R9.1, R9.4, R10.1, R10.2_

- [x] 3. Simplify GoogleSignInButton
  - [x] 3.1 Replace manual OAuth URL construction in `GoogleSignInButton.tsx` with `signInWithRedirect({ provider: 'Google' })`
    - Remove domain lookup, manual redirect URL construction
    - Single async call: `await signInWithRedirect({ provider: 'Google' })`
    - _Requirements: R2.1, R2.2, R6.2_

  - [x]\* 3.2 Write unit test for GoogleSignInButton
    - Test: clicking button calls `signInWithRedirect` with `{ provider: 'Google' }`
    - _Requirements: R2.1_

- [x] 4. Simplify CustomAuthenticator
  - [x] 4.1 Remove localStorage auth logic from `CustomAuthenticator.tsx`
    - Remove `checkAuthState()` localStorage reads
    - Remove `shouldBypassAuth()` for `/auth/callback` route
    - Remove `handleGoogleAuthSuccess()` callback handler
    - Remove localStorage writes (`hdcn_auth_user`, `hdcn_auth_tokens`)
    - Keep: login form UI, passkey/OTP sign-in logic, registration form, passkey setup offer
    - _Requirements: R6.3, R6.5, R7.1, R3.1, R3.2, R3.3, R3.4_

  - [x] 4.2 Add error handling for OTP and WebAuthn failures
    - On OTP code expired: show "Code expired" message + "Resend code" button without re-entering email
    - On WebAuthn cancelled/unavailable: automatic fallback to EMAIL_OTP challenge
    - On network error: show retry-friendly message
    - _Requirements: R9.2, R9.3, R9.5_

  - [x]\* 4.3 Write unit tests for CustomAuthenticator auth flows
    - Test: WebAuthn failure triggers automatic OTP fallback
    - Test: expired OTP shows resend option
    - Test: network error shows retry message
    - _Requirements: R9.2, R9.3, R9.5_

- [x] 5. Checkpoint - Core auth components
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Update API layer and consuming components
  - [x] 6.1 Simplify `authHeaders.ts` to use `fetchAuthSession()`
    - Replace localStorage token reads with `fetchAuthSession().tokens.accessToken`
    - Remove manual JWT decoding
    - Throw clear error when not authenticated
    - _Requirements: R4.3, R6.6_

  - [x] 6.2 Simplify `GroupAccessGuard.tsx` to use `useAuth()` hook
    - Get groups from `useAuth().user.groups` instead of manual JWT decoding or localStorage
    - Keep existing routing logic based on group membership
    - _Requirements: R8.1, R4.2, R6.6_

  - [x] 6.3 Simplify `Dashboard.tsx` (pages) to use `useAuth()` hook
    - Replace any direct token/group extraction with `useAuth()` context
    - _Requirements: R4.2, R6.6_

  - [x]\* 6.4 Write unit tests for authHeaders
    - Test: returns Bearer token from fetchAuthSession
    - Test: throws error when no session exists
    - _Requirements: R4.3_

- [x] 7. Wire AuthProvider into App and remove dead code
  - [x] 7.1 Wrap App with AuthProvider in `App.tsx`
    - Add `<AuthProvider>` as wrapper around the app's component tree
    - Remove `/auth/callback` route (no longer needed)
    - _Requirements: R2.4, R6.1_

  - [x] 7.2 Delete `OAuthCallback.tsx`
    - Remove the file `src/components/auth/OAuthCallback.tsx`
    - Remove any imports referencing it
    - _Requirements: R6.1_

  - [x] 7.3 Remove localStorage auth artifacts
    - Remove any remaining reads/writes of `hdcn_auth_user` and `hdcn_auth_tokens` across the codebase
    - Remove hardcoded group assignments per email (webmaster fallback)
    - Remove the non-existent backend call to `/hdcn-cognito-admin/get-user-groups`
    - _Requirements: R6.3, R6.4, R6.5_

  - [x] 7.4 Create Cognito OAuth verification script
    - Create `scripts/verify_cognito_oauth.py` that calls `describe-user-pool-client` and asserts expected OAuth settings
    - Checks: OAuth enabled, flows=`code`, scopes=`openid/email/profile`, callback URLs, logout URLs, identity providers=`Google/COGNITO`
    - Exit code 0 = config matches, exit code 1 = drift detected
    - Accepts `--profile` argument (default: `nonprofit-deploy`)
    - _Requirements: R5.1, R5.2, R5.3_

- [x] 8. Checkpoint - Full integration
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Integration tests
  - [x]\* 9.1 Write integration test for Google SSO flow
    - Test: `signInWithRedirect` → Hub `signedIn` event → AuthProvider sets user with groups
    - Test: OAuth error → Hub `signIn_failure` → error message shown on login page
    - _Requirements: R1.2, R1.3, R2.1, R2.2, R9.1_

  - [x]\* 9.2 Write integration test for sign-out flow
    - Test: sign-out clears local session and redirects to Cognito hosted UI logout
    - Test: after sign-out, user sees login page (no auto-re-auth)
    - _Requirements: R10.1, R10.2, R10.3_

  - [x]\* 9.3 Write integration test for session continuity
    - Test: page refresh with valid session → user remains authenticated
    - Test: token refresh failure → user redirected to login with message
    - _Requirements: R4.1, R4.4, R9.4_

- [x] 10. Final checkpoint
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- The design has no Correctness Properties section, so no property-based tests are included
- Backend Cognito triggers (PreSignUp, PostAuthentication) are unchanged — they already handle Google identity linking and group assignment (R7.2)
- Backend JWT validation (shared auth_utils layer) is unchanged (R7.3)
- Cognito app client configuration (R5.1, R5.2, R5.3) should be verified in AWS Console before starting implementation — this is infrastructure config, not code

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "2.1"] },
    { "id": 2, "tasks": ["2.2", "2.3", "3.1"] },
    { "id": 3, "tasks": ["3.2", "4.1"] },
    { "id": 4, "tasks": ["4.2", "4.3"] },
    { "id": 5, "tasks": ["6.1", "6.2", "6.3"] },
    { "id": 6, "tasks": ["6.4", "7.1"] },
    { "id": 7, "tasks": ["7.2", "7.3", "7.4"] },
    { "id": 8, "tasks": ["9.1", "9.2", "9.3"] }
  ]
}
