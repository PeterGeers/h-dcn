# Design: Unified Authentication Flow

## Overview

Route all authentication through Amplify v6 so both login paths (Passkey/OTP and Google SSO) produce the same outcome: an Amplify-managed session with a JWT containing verified email and `cognito:groups`.

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│ Login Page (CustomAuthenticator)                                  │
│                                                                  │
│  ┌─────────────────────┐       ┌──────────────────────────┐     │
│  │ Passkey / Email OTP │       │ Google SSO               │     │
│  │                     │       │                          │     │
│  │ signIn({            │       │ signInWithRedirect({     │     │
│  │   username: email,  │       │   provider: 'Google'    │     │
│  │   authFlowType:     │       │ })                      │     │
│  │     'USER_AUTH',    │       │                          │     │
│  │   preferredChallenge│       │ Amplify handles:         │     │
│  │     'WEB_AUTHN'     │       │ - redirect to Google     │     │
│  │ })                  │       │ - callback processing    │     │
│  │                     │       │ - token exchange         │     │
│  │ fallback: EMAIL_OTP │       │ - session storage        │     │
│  └──────────┬──────────┘       └────────────┬─────────────┘     │
│             │                                │                   │
│             └────────────┬───────────────────┘                   │
│                          │                                       │
│                          ▼                                       │
│             ┌────────────────────────┐                           │
│             │ Amplify Session        │                           │
│             │ fetchAuthSession()     │                           │
│             │                        │                           │
│             │ → accessToken (JWT)    │                           │
│             │   - cognito:groups     │                           │
│             │   - sub                │                           │
│             │ → idToken (JWT)        │                           │
│             │   - email (verified)   │                           │
│             │   - given_name         │                           │
│             │   - family_name        │                           │
│             └───────────┬────────────┘                           │
│                         │                                        │
└─────────────────────────┼────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────────┐
│ AuthProvider (new)                                                │
│                                                                  │
│ Calls fetchAuthSession() + getCurrentUser()                      │
│ Produces typed AuthUser:                                         │
│   { email, givenName, familyName, sub, groups[], accessToken }   │
│                                                                  │
│ Provides via React Context to all children                       │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│ App (GroupAccessGuard → Dashboard → Pages)                       │
│                                                                  │
│ Uses useAuth() hook → gets AuthUser from context                 │
│ API calls: Bearer {authUser.accessToken}                         │
└──────────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. Amplify Configuration (`aws-exports.ts`)

Add OAuth section to existing config:

```typescript
const awsconfig = {
  Auth: {
    Cognito: {
      userPoolId: "eu-west-1_fcUkvwjH5",
      userPoolClientId: "6jhvk853b0lfg9q1m861qs0cug",
      loginWith: {
        oauth: {
          domain: "h-dcn-auth-506221081911.auth.eu-west-1.amazoncognito.com",
          scopes: ["openid", "email", "profile"],
          redirectSignIn: [
            "https://portal.h-dcn.nl/",
            "http://localhost:3000/",
          ],
          redirectSignOut: [
            "https://portal.h-dcn.nl/",
            "http://localhost:3000/",
          ],
          responseType: "code",
          providers: ["Google"],
        },
      },
    },
  },
};
```

### 2. AuthProvider (new component)

Replaces the session-checking logic currently scattered across CustomAuthenticator, GroupAccessGuard, Dashboard, and authHeaders.

```typescript
interface AuthUser {
  email: string;
  givenName?: string;
  familyName?: string;
  sub: string;
  groups: string[];
  accessToken: string;
}

interface AuthContextType {
  user: AuthUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  signOut: () => Promise<void>;
}
```

Responsibilities:

- On mount: call `fetchAuthSession()` to check for existing session
- Listen to Amplify Hub `auth` events (see Hub Events section below)
- Extract user info from tokens (email from ID token, groups from access token)
- Provide `AuthUser` via context
- Handle sign-out (calls Amplify `signOut({ global: false })` + Cognito hosted UI logout)

### 2a. Hub Event Handling

AuthProvider listens to `Hub.listen('auth', callback)` and reacts to these events:

| Hub Event              | Action                                                                 |
| ---------------------- | ---------------------------------------------------------------------- |
| `signedIn`             | Call `fetchAuthSession()` → extract tokens → set `AuthUser` in state   |
| `signedOut`            | Clear `AuthUser` from state → redirect to login page                   |
| `tokenRefresh`         | Update `accessToken` in state (silent, no UI change)                   |
| `tokenRefresh_failure` | Clear `AuthUser` → redirect to login with "session expired" message    |
| `signInWithRedirect`   | (Amplify internal) Triggers `signedIn` after successful OAuth callback |

The `signedIn` event is the key for Google SSO: after Amplify processes the OAuth callback and exchanges the authorization code for tokens, it fires `signedIn`. AuthProvider then picks up the session — no custom callback handling needed.

### 2b. Token Extraction

```typescript
const session = await fetchAuthSession();
const accessToken = session.tokens?.accessToken;
const idToken = session.tokens?.idToken;

const groups = (accessToken?.payload?.["cognito:groups"] as string[]) ?? [];
const email = idToken?.payload?.email as string;
const givenName = idToken?.payload?.given_name as string | undefined;
const familyName = idToken?.payload?.family_name as string | undefined;
const sub = accessToken?.payload?.sub as string;
```

### 2c. Error Handling in AuthProvider

```typescript
// On mount and after Hub events
try {
  const session = await fetchAuthSession();
  if (!session.tokens) {
    // No session — user needs to log in
    setUser(null);
    return;
  }
  // Extract and set user...
} catch (error) {
  // Session fetch failed — treat as unauthenticated
  setUser(null);
  setError("Session expired. Please sign in again.");
}
```

For OAuth callback errors (user denies consent, Cognito rejects token), Amplify redirects back to the app with error parameters in the URL. AuthProvider detects this via `Hub.listen('auth', { payload: { event: 'signIn_failure' } })` and surfaces the error message.

### 2d. Sign-Out Flow

```typescript
const handleSignOut = async () => {
  await signOut({ global: false }); // Clear local Amplify session
  // Redirect to Cognito hosted UI logout to clear the Cognito session cookie
  // This prevents Google SSO users from being auto-re-authenticated
  window.location.href = `https://${cognitoDomain}/logout?client_id=${clientId}&logout_uri=${encodeURIComponent(window.location.origin + "/")}`;
};
```

Why not just `signOut()`? For Google SSO users, Amplify's local sign-out clears the app session, but the Cognito hosted UI still has a session cookie. On next login attempt, clicking "Google" would auto-authenticate without prompting — confusing if the user intended to switch accounts. The hosted UI logout endpoint clears that cookie.

### 3. GoogleSignInButton (simplified)

```typescript
const handleGoogleSignIn = async () => {
  await signInWithRedirect({ provider: "Google" });
};
```

That's it. No URL construction, no domain lookup, no manual redirect. Amplify handles everything.

### 4. CustomAuthenticator (simplified)

Keeps:

- Login form UI (email input, passkey button, Google button)
- Passkey/OTP sign-in logic (already uses Amplify `signIn()`)
- Registration form for new users
- Passkey setup offer after first OTP login

Removes:

- `checkAuthState()` localStorage logic → replaced by AuthProvider
- `shouldBypassAuth()` for `/auth/callback` → Amplify handles callback
- `handleGoogleAuthSuccess()` → not needed, Hub listener handles it
- localStorage read/write for auth state

### 5. API calls (authHeaders.ts / ApiService)

```typescript
export const getAuthHeaders = async (): Promise<Record<string, string>> => {
  const session = await fetchAuthSession();
  const token = session.tokens?.accessToken?.toString();

  if (!token) throw new Error("Not authenticated");

  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  };
};
```

No localStorage, no manual JWT decoding for groups.

## Files Changed

| File                      | Action   | Reason                                                 |
| ------------------------- | -------- | ------------------------------------------------------ |
| `aws-exports.ts`          | Modify   | Add Amplify v6 Auth/OAuth config                       |
| `index.tsx`               | Modify   | Update `Amplify.configure()` call for new config shape |
| `AuthProvider.tsx`        | Create   | Central session management via Amplify                 |
| `useAuth.ts`              | Rewrite  | Returns AuthUser from AuthProvider context             |
| `CustomAuthenticator.tsx` | Simplify | Remove localStorage logic, keep login UI               |
| `GoogleSignInButton.tsx`  | Simplify | Use `signInWithRedirect()`                             |
| `OAuthCallback.tsx`       | Delete   | Amplify handles callback                               |
| `authHeaders.ts`          | Simplify | Get token from `fetchAuthSession()`                    |
| `ApiService.ts`           | Simplify | Get token from `fetchAuthSession()`                    |
| `GroupAccessGuard.tsx`    | Simplify | Get groups from `useAuth()` hook                       |
| `Dashboard.tsx`           | Simplify | Get groups from `useAuth()` hook                       |
| `App.tsx`                 | Modify   | Remove `/auth/callback` route, wrap with AuthProvider  |

## Cognito App Client Changes (AWS Console/CLI)

The app client `6jhvk853b0lfg9q1m861qs0cug` needs:

1. **Allowed OAuth Flows**: `code` (authorization code)
2. **Allowed OAuth Scopes**: `openid`, `email`, `profile`
3. **Callback URLs**: `https://portal.h-dcn.nl/`, `http://localhost:3000/`
4. **Sign-out URLs**: `https://portal.h-dcn.nl/`, `http://localhost:3000/`
5. **Supported Identity Providers**: `Google`, `Cognito`

These may already be partially configured (Google SSO was working before via manual flow). Verify and update as needed.

## Cognito Configuration Drift Detection

Since the Cognito User Pool and app client are managed outside CloudFormation (to avoid accidental deletion), a verification script provides drift detection without IaC ownership risk.

### `scripts/verify_cognito_oauth.py`

A Python script that calls `describe-user-pool-client` and asserts the expected OAuth settings match. Run it in CI or manually after deploys.

```python
"""
Verify Cognito app client OAuth configuration matches expected settings.
Run: python scripts/verify_cognito_oauth.py [--profile nonprofit-deploy]
Exit code 0 = all good, 1 = drift detected.
"""
import boto3
import sys
import argparse

EXPECTED = {
    "user_pool_id": "eu-west-1_fcUkvwjH5",
    "client_id": "6jhvk853b0lfg9q1m861qs0cug",
    "allowed_oauth_flows": ["code"],
    "allowed_oauth_scopes": {"openid", "email", "profile"},
    "callback_urls": {"https://portal.h-dcn.nl/", "http://localhost:3000/"},
    "logout_urls": {"https://portal.h-dcn.nl/", "http://localhost:3000/"},
    "supported_identity_providers": {"Google", "COGNITO"},
    "allowed_oauth_flows_user_pool_client": True,
}

def verify(profile=None):
    session = boto3.Session(profile_name=profile, region_name="eu-west-1")
    client = session.client("cognito-idp")

    resp = client.describe_user_pool_client(
        UserPoolId=EXPECTED["user_pool_id"],
        ClientId=EXPECTED["client_id"],
    )
    cfg = resp["UserPoolClient"]

    errors = []

    if not cfg.get("AllowedOAuthFlowsUserPoolClient"):
        errors.append("OAuth is DISABLED on app client")

    if set(cfg.get("AllowedOAuthFlows", [])) != set(EXPECTED["allowed_oauth_flows"]):
        errors.append(f"OAuth flows: got {cfg.get('AllowedOAuthFlows')}, expected {EXPECTED['allowed_oauth_flows']}")

    if set(cfg.get("AllowedOAuthScopes", [])) != EXPECTED["allowed_oauth_scopes"]:
        errors.append(f"OAuth scopes: got {cfg.get('AllowedOAuthScopes')}, expected {EXPECTED['allowed_oauth_scopes']}")

    if set(cfg.get("CallbackURLs", [])) != EXPECTED["callback_urls"]:
        errors.append(f"Callback URLs: got {cfg.get('CallbackURLs')}, expected {EXPECTED['callback_urls']}")

    if set(cfg.get("LogoutURLs", [])) != EXPECTED["logout_urls"]:
        errors.append(f"Logout URLs: got {cfg.get('LogoutURLs')}, expected {EXPECTED['logout_urls']}")

    if set(cfg.get("SupportedIdentityProviders", [])) != EXPECTED["supported_identity_providers"]:
        errors.append(f"IdPs: got {cfg.get('SupportedIdentityProviders')}, expected {EXPECTED['supported_identity_providers']}")

    if errors:
        print("❌ Cognito OAuth config DRIFT DETECTED:")
        for e in errors:
            print(f"   - {e}")
        return 1
    else:
        print("✅ Cognito OAuth config matches expected settings")
        return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="nonprofit-deploy")
    args = parser.parse_args()
    sys.exit(verify(args.profile))
```

This script can be:

- Run manually: `python scripts/verify_cognito_oauth.py`
- Added to CI as a post-deploy check
- Used as a pre-flight check before frontend deploys

| File                              | Action | Reason                                              |
| --------------------------------- | ------ | --------------------------------------------------- |
| `scripts/verify_cognito_oauth.py` | Create | Drift detection for manually-managed Cognito config |

## Migration Strategy

1. Deploy new auth code
2. Users with old localStorage sessions: on next visit, `fetchAuthSession()` returns no session → shown login page → they re-authenticate → new Amplify session created
3. No data loss — user accounts, groups, and member records are unchanged in Cognito/DynamoDB

## Error Handling Strategy

| Scenario                          | User Experience                                                        | Technical Handling                                               |
| --------------------------------- | ---------------------------------------------------------------------- | ---------------------------------------------------------------- |
| Google denies consent             | Returned to login page with "Google sign-in was cancelled"             | Hub `signIn_failure` event → AuthProvider sets error state       |
| Cognito rejects Google token      | Returned to login page with "Authentication failed. Please try again." | Hub `signIn_failure` event → AuthProvider sets error state       |
| OTP code expired                  | "Code expired" message + "Resend code" button                          | `confirmSignIn` throws → CustomAuthenticator shows resend option |
| WebAuthn cancelled/unavailable    | Automatic fallback to OTP — user sees OTP input                        | `signIn` challenge response indicates fallback → send EMAIL_OTP  |
| Token refresh fails mid-session   | Redirect to login with "Session expired" toast                         | Hub `tokenRefresh_failure` → AuthProvider clears state           |
| Network error during auth         | "Network error. Check your connection and try again."                  | Catch block in signIn/AuthProvider → show retry-friendly message |
| fetchAuthSession returns no token | Login page shown (normal unauthenticated state)                        | AuthProvider sets `user: null`, `isLoading: false`               |

## Risks

| Risk                                                     | Mitigation                                                                                                                    |
| -------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| Cognito access token is opaque (not JWT) for OAuth flows | Verify app client config: if `openid` scope is included and no resource server custom scopes are used, Cognito issues JWTs    |
| Google identity not linked to native user                | PreSignUp trigger already handles this — verify it's attached to the pool                                                     |
| `cognito:groups` not in access token                     | Groups are included automatically when user is member of Cognito groups — PostAuthentication trigger ensures group membership |
| Amplify Hub listener doesn't fire on OAuth callback      | Test with `Hub.listen('auth', ...)` — well-documented Amplify v6 pattern                                                      |
