# Authentication Architecture

## Overview

The H-DCN portal uses AWS Cognito as its identity provider, supporting two login paths: WebAuthn passkeys / email OTP (native Cognito) and Google SSO (OAuth identity provider). The frontend is a React SPA using AWS Amplify v6 for session management, while the backend consists of Python Lambda functions behind API Gateway, each protected by a shared auth layer that validates JWT access tokens and enforces role-based permissions with regional scoping.

Key characteristics:

- **Identity store**: Cognito User Pool `eu-west-1_fcUkvwjH5` (PLUS tier, WebAuthn enabled)
- **Frontend auth**: Amplify v6 `fetchAuthSession()` with Hub event listeners for real-time state
- **Backend auth**: Shared Lambda Layer decodes access token JWT, extracts `cognito:groups`, and validates permissions
- **Access control**: Role-based with regional scoping (users may only access members in their allowed regions)
- **Session tokens**: Cognito issues ID token, access token, and refresh token; backend requires the access token

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           H-DCN Authentication Flow                          │
└─────────────────────────────────────────────────────────────────────────────┘

  ┌──────────┐         ┌─────────────────────────────────────────────┐
  │   User   │         │              AWS Cognito                     │
  │ (Browser)│         │         eu-west-1_fcUkvwjH5                  │
  └────┬─────┘         │                                             │
       │                │  ┌───────────────┐  ┌───────────────────┐  │
       │  Login Path 1  │  │ WebAuthn /    │  │  Google SSO       │  │
       ├───────────────►│  │ Email OTP     │  │  (OAuth Provider) │  │
       │  (Passkey/OTP) │  │ (USER_AUTH)   │  │  (Redirect Flow)  │  │
       │                │  └───────┬───────┘  └────────┬──────────┘  │
       │  Login Path 2  │          │                   │             │
       ├───────────────►│          └─────────┬─────────┘             │
       │  (Google SSO)  │                    │                       │
       │                │                    ▼                       │
       │                │  ┌─────────────────────────────────────┐  │
       │                │  │  Issue Tokens:                       │  │
       │                │  │  • ID Token (user attributes)       │  │
       │                │  │  • Access Token (cognito:groups)    │  │
       │                │  │  • Refresh Token                    │  │
       │                │  └──────────────────┬──────────────────┘  │
       │                │                     │                      │
       │                │  ┌──────────────────┼──────────────────┐  │
       │                │  │  Lambda Triggers: │                  │  │
       │                │  │  • PreSignUp     ▼                  │  │
       │                │  │  • PostAuthentication               │  │
       │                │  │  • PostConfirmation                 │  │
       │                │  │  • CustomMessage                    │  │
       │                │  │  • UserMigration                    │  │
       │                │  └─────────────────────────────────────┘  │
       │                └─────────────────────┬───────────────────────┘
       │                                      │
       │                                      ▼
       │                ┌─────────────────────────────────────────────┐
       │                │           Frontend (React + Amplify v6)      │
       │◄───────────────│                                             │
       │  Authenticated │  • AuthProvider (context, Hub listener)     │
       │                │  • fetchAuthSession() → tokens              │
       │                │  • useAuth() hook → user, groups, signOut   │
       │                │  • GroupAccessGuard (route protection)       │
       │                │  • Stores access token for API calls        │
       │                └──────────────────────┬──────────────────────┘
       │                                       │
       │                                       │ Authorization: Bearer <access_token>
       │                                       ▼
       │                ┌─────────────────────────────────────────────┐
       │                │           API Gateway (REST)                 │
       │                │           api.h-dcn.nl                       │
       │                └──────────────────────┬──────────────────────┘
       │                                       │
       │                                       ▼
       │                ┌─────────────────────────────────────────────┐
       │                │           Lambda Function                    │
       │                │                                             │
       │                │  ┌───────────────────────────────────────┐  │
       │                │  │  Auth Layer (shared/auth_utils.py)    │  │
       │                │  │                                       │  │
       │                │  │  1. extract_user_credentials(event)   │  │
       │                │  │     → Decode JWT access token         │  │
       │                │  │     → Extract email + cognito:groups  │  │
       │                │  │                                       │  │
       │                │  │  2. validate_permissions_with_regions │  │
       │                │  │     → Check required permission       │  │
       │                │  │     → Enforce regional scoping        │  │
       │                │  └───────────────────────────────────────┘  │
       │                │                                             │
       │                │  ┌───────────────────────────────────────┐  │
       │                │  │  Business Logic                       │  │
       │  ◄─────────────│  │  → DynamoDB (Members, Events, etc.)  │  │
       │  API Response  │  └───────────────────────────────────────┘  │
       │                └─────────────────────────────────────────────┘
```

### Flow Summary

1. **Login**: User authenticates via passkey/email OTP or Google SSO redirect
2. **Token issuance**: Cognito issues ID, access, and refresh tokens; triggers fire (PreSignUp, PostAuthentication, etc.)
3. **Session management**: Amplify v6 stores tokens, AuthProvider exposes state via `useAuth()` hook
4. **API call**: Frontend sends access token as `Authorization: Bearer` header
5. **Backend validation**: Auth layer decodes JWT, extracts groups, validates permissions with regional scoping
6. **Business logic**: Handler executes after auth passes, queries DynamoDB, returns response

## Cognito Pool Configuration

The Cognito User Pool is managed **outside CloudFormation** (created manually in the AWS Console). Never add it as a CloudFormation resource without `DeletionPolicy: Retain`.

### Pool Settings

| Setting         | Value                            |
| --------------- | -------------------------------- |
| Pool Name       | H-DCN-Authentication-Pool        |
| Pool ID         | `eu-west-1_fcUkvwjH5`            |
| App Client ID   | `6jhvk853b0lfg9q1m861qs0cug`     |
| App Client Name | H-DCN-Web-Client                 |
| Pool Tier       | PLUS (WebAuthn/passkeys enabled) |
| WebAuthn RP ID  | `h-dcn.nl`                       |
| Region          | eu-west-1 (Ireland)              |
| AWS Account     | 506221081911 (Nonprofit)         |

### Cognito Domain

| Setting | Value                                                      |
| ------- | ---------------------------------------------------------- |
| Domain  | `h-dcn-auth-506221081911.auth.eu-west-1.amazoncognito.com` |
| Type    | Amazon Cognito prefix domain                               |

The domain is used for the hosted UI (OAuth authorize/token endpoints, logout endpoint).

### OAuth Configuration

| Setting       | Value                                                |
| ------------- | ---------------------------------------------------- |
| Response Type | `code` (Authorization Code Grant)                    |
| Scopes        | `openid`, `email`, `profile`                         |
| Callback URLs | `https://portal.h-dcn.nl/`, `http://localhost:3000/` |
| Sign-out URLs | `https://portal.h-dcn.nl/`, `http://localhost:3000/` |

### Identity Providers

| Provider | Type   | Notes                                        |
| -------- | ------ | -------------------------------------------- |
| Cognito  | Native | Email/password, WebAuthn passkeys, Email OTP |
| Google   | OAuth  | Google Workspace SSO for staff members       |

Google SSO uses `signInWithRedirect` via Amplify v6. After redirect, Cognito issues tokens and fires the PostAuthentication trigger.

### Enabled Auth Flows

| Auth Flow                  | Purpose                                             |
| -------------------------- | --------------------------------------------------- |
| `ALLOW_USER_AUTH`          | WebAuthn passkeys and email OTP (choice-based auth) |
| `ALLOW_REFRESH_TOKEN_AUTH` | Silent token refresh using refresh token            |
| `ALLOW_USER_SRP_AUTH`      | Secure Remote Password protocol (password-based)    |
| `ALLOW_CUSTOM_AUTH`        | Custom authentication challenges (Lambda triggers)  |

The `USER_AUTH` flow is the primary login method, enabling Cognito to offer passkeys or email OTP as first-factor options. `USER_SRP_AUTH` is retained for backward compatibility with password-based accounts (e.g., users in `FORCE_CHANGE_PASSWORD` state).

## File Locations

### Frontend (React + TypeScript)

| Component           | Path                                                   | Purpose                                                       |
| ------------------- | ------------------------------------------------------ | ------------------------------------------------------------- |
| AuthProvider        | `frontend/src/context/AuthProvider.tsx`                | React context managing auth state via Amplify v6 Hub events   |
| CustomAuthenticator | `frontend/src/components/auth/CustomAuthenticator.tsx` | Custom login UI wrapping Amplify Authenticator                |
| GroupAccessGuard    | `frontend/src/components/common/GroupAccessGuard.tsx`  | Route-level guard restricting access by Cognito group         |
| useAuth hook        | `frontend/src/hooks/useAuth.ts`                        | Hook exposing user, groups, signOut from AuthProvider context |
| aws-exports         | `frontend/src/aws-exports.ts`                          | Amplify configuration (Cognito pool, region, OAuth settings)  |

### Backend (Python / AWS SAM)

#### Shared Auth Layer

| File                 | Path                                                              | Purpose                                                     |
| -------------------- | ----------------------------------------------------------------- | ----------------------------------------------------------- |
| auth_utils           | `backend/layers/auth-layer/python/shared/auth_utils.py`           | JWT validation, permission checking, CORS, response helpers |
| maintenance_fallback | `backend/layers/auth-layer/python/shared/maintenance_fallback.py` | Graceful fallback when auth layer is unavailable            |

#### Cognito Trigger Handlers

All triggers live under `backend/handler/` with one folder per function. Each contains an `app.py` entry point.

| Trigger            | Path                                                 | Cognito Event                                                |
| ------------------ | ---------------------------------------------------- | ------------------------------------------------------------ |
| PreSignUp          | `backend/handler/cognito_pre_signup/app.py`          | Fires before user creation — handles Google identity linking |
| PostAuthentication | `backend/handler/cognito_post_authentication/app.py` | Fires after successful login — syncs user attributes         |
| PostConfirmation   | `backend/handler/cognito_post_confirmation/app.py`   | Fires after email verification — assigns initial group       |
| CustomMessage      | `backend/handler/cognito_custom_message/app.py`      | Customizes verification/invitation emails                    |
| UserMigration      | `backend/handler/cognito_user_migration/app.py`      | Migrates users from legacy pool on first login               |
| RoleAssignment     | `backend/handler/cognito_role_assignment/app.py`     | Assigns Cognito groups/roles to users                        |

## Cognito Triggers

Cognito invokes Lambda triggers at specific points in the authentication lifecycle. Each trigger receives an event from Cognito and must return the (possibly modified) event object. Errors are logged but generally should not block the user flow.

### PreSignUp

| Property       | Value                                                               |
| -------------- | ------------------------------------------------------------------- |
| Handler        | `backend/handler/cognito_pre_signup/app.py`                         |
| Trigger Source | `PreSignUp_ExternalProvider`                                        |
| Purpose        | Link federated (Google) identities to existing native Cognito users |

**Key Behavior:**

- Only acts on external provider sign-ups (trigger source `PreSignUp_ExternalProvider`); passes through for native sign-ups
- Searches for an existing native user with the same email using `list_users` with email filter
- If a native user exists, calls `admin_link_provider_for_user` to link the Google identity to the native account — this prevents duplicate accounts
- Parses the federated username format (`Google_<id>`) to extract provider name and user ID
- Sets `autoConfirmUser = True` and `autoVerifyEmail = True` for all external provider sign-ups
- Handles `InvalidParameterException` gracefully (provider already linked)
- On any error, returns the event unchanged to avoid blocking sign-up

### PostAuthentication

| Property       | Value                                                                                                             |
| -------------- | ----------------------------------------------------------------------------------------------------------------- |
| Handler        | `backend/handler/cognito_post_authentication/app.py`                                                              |
| Trigger Source | `PostAuthentication_Authentication`                                                                               |
| Purpose        | Ensure users have appropriate Cognito groups after login, especially Google SSO users who bypass PostConfirmation |

**Key Behavior:**

- Fires after every successful authentication (both native and Google SSO)
- Checks the user's current Cognito groups via `admin_list_groups_for_user`
- Determines if role assignment is needed when:
  - User has no groups at all
  - User only has auto-generated federated identity groups (e.g., `_Google`)
  - User is missing both `hdcnLeden` and `verzoek_lid` groups
- If role assignment is needed, looks up the user's email in the Members DynamoDB table
- If member status is `active` or `approved`, adds the user to the `hdcnLeden` group
- Logs a structured `ROLE_ASSIGNMENT_DECISION` audit entry for every login
- On error, returns the event unchanged to avoid blocking authentication

### PostConfirmation

| Property       | Value                                                                      |
| -------------- | -------------------------------------------------------------------------- |
| Handler        | `backend/handler/cognito_post_confirmation/app.py`                         |
| Trigger Source | `PostConfirmation_ConfirmSignUp`, `PostConfirmation_ConfirmForgotPassword` |
| Purpose        | Assign initial Cognito group to newly confirmed users and notify admins    |

**Key Behavior:**

- Handles two trigger sources:
  - `PostConfirmation_ConfirmSignUp` — new user email verification complete
  - `PostConfirmation_ConfirmForgotPassword` — password recovery confirmation
- For new sign-ups:
  - Checks if user already exists in the Members DynamoDB table
  - If member status is `active` or `approved`, adds user to `hdcnLeden` group
  - If member is not approved or not found, no role is assigned (user must wait for admin approval)
  - Sends admin notification about the new signup
  - Logs a structured `ROLE_ASSIGNMENT_DECISION` audit entry
- For password recovery: logs the event and sends admin security notification
- On error, returns the event unchanged to avoid blocking confirmation

### CustomMessage

| Property       | Value                                                                                                                                                                                                 |
| -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Handler        | `backend/handler/cognito_custom_message/app.py`                                                                                                                                                       |
| Trigger Source | `CustomMessage_AdminCreateUser`, `CustomMessage_ResendCode`, `CustomMessage_ForgotPassword`, `CustomMessage_UpdateUserAttribute`, `CustomMessage_VerifyUserAttribute`, `CustomMessage_Authentication` |
| Purpose        | Customize Cognito email messages with Dutch language templates and H-DCN branding                                                                                                                     |

**Key Behavior:**

- Replaces Cognito's default email templates with custom Dutch-language messages
- Uses a `template_service` module for rendering HTML email templates (welcome, resend-code)
- Generates inline text emails for other message types (forgot password, attribute verification, authentication codes)
- Each message type has its own handler function with appropriate subject line and body
- Includes organization details from environment variables (`ORGANIZATION_NAME`, `ORGANIZATION_WEBSITE`, `ORGANIZATION_EMAIL`, `ORGANIZATION_SHORT_NAME`)
- Falls back to a generic verification message for unrecognized trigger sources
- On error, returns the original event unchanged to avoid blocking the message delivery

### UserMigration

| Property       | Value                                                                                 |
| -------------- | ------------------------------------------------------------------------------------- |
| Handler        | `backend/handler/cognito_user_migration/app.py`                                       |
| Trigger Source | `UserMigration_Authentication`, `UserMigration_ForgotPassword`                        |
| Purpose        | Transparently migrate users from the legacy Cognito pool (old account) on first login |

**Key Behavior:**

- Handles migration from old pool `eu-west-1_OAT3oPCIm` (account 344561557829) to current pool
- For `UserMigration_Authentication`:
  1. Validates credentials against old pool via `admin_initiate_auth` (ADMIN_USER_PASSWORD_AUTH flow)
  2. Retrieves user attributes from old pool via `admin_get_user`
  3. Retrieves group memberships from old pool via `admin_list_groups_for_user`
  4. Returns user data with `finalUserStatus = CONFIRMED` and `messageAction = SUPPRESS`
  5. Passes group memberships via `clientMetadata.migratedGroups` for downstream processing
- For `UserMigration_ForgotPassword`:
  - Retrieves user attributes and groups from old pool (no credential validation needed)
  - Returns user data so Cognito can create the account and send the reset email
- Migrates standard attributes (`email`, `name`, `given_name`, `family_name`, `phone_number`) and custom attributes
- Sets `email_verified = true` for all migrated users
- On error, re-raises the exception (signals Cognito to return "user not found")

### Note on RoleAssignment Handler

The `cognito_role_assignment` handler (`backend/handler/cognito_role_assignment/app.py`) is **not** a standard Cognito trigger. It is invoked by DynamoDB Streams (when member status changes) or via direct API calls from administrators. It manages Cognito group assignments based on member approval status changes (see [User Lifecycle](#user-lifecycle) section).

## User Lifecycle

The complete user lifecycle from signup to full portal access:

```
┌──────────┐     ┌──────────────┐     ┌─────────────────┐     ┌────────────────┐     ┌─────────────────┐
│  Signup  │────►│ Email Verify │────►│ PostConfirmation │────►│ Admin Approval │────►│ Role Assignment │
│          │     │              │     │ (no group or     │     │                │     │                 │
│ Cognito  │     │ Cognito      │     │  hdcnLeden)      │     │ Manual action  │     │ Cognito groups  │
└──────────┘     └──────────────┘     └─────────────────┘     └────────────────┘     └─────────────────┘
```

### Step-by-Step Flow

| Step | Action                                          | System   | Result                                               |
| ---- | ----------------------------------------------- | -------- | ---------------------------------------------------- |
| 1    | User signs up (email + password or Google SSO)  | Cognito  | Account created, email verification sent             |
| 2    | User verifies email (clicks link)               | Cognito  | `PostConfirmation_ConfirmSignUp` trigger fires       |
| 3    | PostConfirmation checks Members table           | Lambda   | Looks up user email in DynamoDB Members table        |
| 4a   | If member status is `active`/`approved`         | Lambda   | User added to `hdcnLeden` group immediately          |
| 4b   | If member not found or not approved             | Lambda   | No group assigned — user has no portal access        |
| 5    | Admin reviews new signup notification           | Manual   | Admin sees notification, reviews application         |
| 6    | Admin approves member (sets status to `active`) | Admin UI | Member status updated in DynamoDB                    |
| 7    | RoleAssignment handler fires (DynamoDB Stream)  | Lambda   | Adds user to `hdcnLeden`, removes from `verzoek_lid` |
| 8    | Admin assigns regional roles                    | Manual   | Admin adds `Regio_*` and permission groups as needed |

### Key Points

- **New applicants without a Members record** get no Cognito groups — they cannot access the portal beyond the application form
- **The `verzoek_lid` group** is assigned to applicants who have submitted a membership application but are not yet approved. It grants access only to the application form and account page
- **Admin approval is manual** — there is no automatic approval flow
- **The `hdcnLeden` group** is the base member group granting webshop access, event viewing, and self-service profile management
- **Regional roles** (e.g., `Regio_Noord`, `Regio_All`) and permission roles (e.g., `Members_CRUD`) are assigned separately by administrators after the member is in `hdcnLeden`
- **Google SSO users** bypass PostConfirmation (no email verification needed). The PostAuthentication trigger handles their group assignment on first login instead

## Frontend Auth Components

### AuthProvider

**File:** `frontend/src/context/AuthProvider.tsx`

The AuthProvider is the single source of truth for authentication state in the React application. It wraps the entire app and exposes auth state via React Context.

**Responsibilities:**

- Calls `fetchAuthSession()` (Amplify v6) on mount to check for an existing session
- Listens to Amplify Hub `auth` events for real-time state updates:
  - `signedIn` — reloads session (both login paths)
  - `signedOut` — clears user state
  - `tokenRefresh` — updates access token in state
  - `tokenRefresh_failure` — clears session, shows error
  - `signInWithRedirect_failure` — clears session, shows OAuth error
- Extracts user data from tokens:
  - `cognito:groups` from the **access token** payload
  - `email`, `given_name`, `family_name` from the **ID token** payload
  - `sub` (user ID) from the access token payload
- Provides `signOut()` that clears the local Amplify session AND redirects to the Cognito hosted UI logout endpoint (required for Google SSO users to clear the Cognito session cookie)

**Exported interface (`AuthContextType`):**

```typescript
interface AuthContextType {
  user: AuthUser | null; // Current user or null if not authenticated
  isLoading: boolean; // True during initial session check
  isAuthenticated: boolean; // Shorthand for user !== null
  error: string | null; // Error message (expired session, failed login)
  signOut: () => Promise<void>; // Sign out and redirect to Cognito logout
}

interface AuthUser {
  email: string;
  givenName?: string;
  familyName?: string;
  sub: string; // Cognito user ID
  groups: HDCNGroup[]; // Cognito groups from access token
  accessToken: string; // Raw access token JWT for API calls
}
```

### useAuth() Hook

**File:** `frontend/src/hooks/useAuth.ts`

A convenience re-export of the `useAuth` hook from AuthProvider. The canonical implementation lives in `AuthProvider.tsx`.

**Usage:**

```typescript
import { useAuth } from '../hooks/useAuth';

function MyComponent() {
  const { user, isAuthenticated, isLoading, error, signOut } = useAuth();

  if (isLoading) return <Spinner />;
  if (!isAuthenticated) return null;

  // Access user groups
  const isAdmin = user.groups.includes('System_CRUD');
  const userRegions = user.groups.filter(g => g.startsWith('Regio_'));
}
```

**Rules:**

- Must be called within an `<AuthProvider>` tree (throws if context is undefined)
- Groups come from the access token — never from localStorage or manual JWT decoding
- The `accessToken` field is the raw JWT string for use in `Authorization: Bearer` headers

### GroupAccessGuard

**File:** `frontend/src/components/common/GroupAccessGuard.tsx`

A route-level guard that restricts portal access based on the user's Cognito group membership. It wraps the main application routes.

**Behavior:**

| User State                                    | Allowed Routes                                                          | Blocked Route Behavior                                                       |
| --------------------------------------------- | ----------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| Loading (`isLoading = true`)                  | —                                                                       | Renders nothing (AuthProvider handles loading UI)                            |
| Not authenticated (`user = null`)             | —                                                                       | Renders nothing (CustomAuthenticator handles login)                          |
| No groups (`groups = []`)                     | `/`, `/new-member-application`, `/application-submitted`                | Shows "Account in behandeling" message with sign-out button                  |
| Applicant (`verzoek_lid` only)                | `/`, `/new-member-application`, `/application-submitted`, `/my-account` | Shows "Aanvraag wordt beoordeeld" message with link to view/edit application |
| Full member (any group besides `verzoek_lid`) | All routes                                                              | Renders children normally                                                    |

**Key Points:**

- Uses `useAuth()` hook — no direct JWT decoding or localStorage access
- A user with `verzoek_lid` AND another group (e.g., `hdcnLeden`) is treated as a full member (`hasFullAccess = true`)
- The guard does not handle authentication (login/logout) — only authorization (group-based access)
- Blocked users see Dutch-language messages explaining their status and next steps

## Auth Utils Layer

**File:** `backend/layers/auth-layer/python/shared/auth_utils.py`

The shared Lambda Layer providing authentication and authorization for all backend handlers. Every protected endpoint imports from this module.

### `extract_user_credentials(event)`

Extracts and validates user identity from the Lambda event's Authorization header.

**Input:** Lambda event object (must contain `headers.Authorization` with a Bearer JWT)

**Process:**

1. Extracts `Authorization` header from the event
2. Validates `Bearer ` prefix
3. Splits JWT into 3 parts (header.payload.signature)
4. Base64-decodes the payload
5. Extracts `email` (or `username` / `cognito:username` as fallback)
6. Extracts `cognito:groups` from the payload
7. Optionally reads `X-Enhanced-Groups` header (frontend credential combination)

**Returns:** `(user_email, user_roles, error_response)`

| Outcome            | Return Value                                                  |
| ------------------ | ------------------------------------------------------------- |
| Success            | `("user@example.com", ["hdcnLeden", "Regio_All"], None)`      |
| Missing header     | `(None, None, {statusCode: 401, ...})`                        |
| Invalid JWT format | `(None, None, {statusCode: 401, ...})`                        |
| System error       | `(None, None, {statusCode: 503, ...})` — maintenance fallback |

### `validate_permissions_with_regions(user_roles, required_permissions, user_email, resource_context)`

Validates that the user has the required permissions AND appropriate regional access.

**Input:**

| Parameter              | Type              | Description                                             |
| ---------------------- | ----------------- | ------------------------------------------------------- |
| `user_roles`           | `list`            | User's Cognito groups (from `extract_user_credentials`) |
| `required_permissions` | `list` or `str`   | Permission(s) needed for the operation                  |
| `user_email`           | `str` (optional)  | For audit logging                                       |
| `resource_context`     | `dict` (optional) | Context about the resource being accessed               |

**Authorization logic:**

1. **System admins** (`System_CRUD`, `System_User_Management`) → full access, all regions
2. **Permission check** → maps user's roles to permissions via `role_permissions` dict
3. **Regional check:**
   - If user has `Regio_*` roles → regional access (even if also in `hdcnLeden`)
   - If user has only `hdcnLeden` / `verzoek_lid` → basic member access (no regional admin)
   - Otherwise → access denied (permission requires region assignment)

**Returns:** `(is_authorized, error_response, regional_access_info)`

| Outcome                   | Return Value                                                                                            |
| ------------------------- | ------------------------------------------------------------------------------------------------------- |
| Authorized (admin)        | `(True, None, {has_full_access: True, allowed_regions: ['all'], access_type: 'admin'})`                 |
| Authorized (regional)     | `(True, None, {has_full_access: False, allowed_regions: ['Noord', 'Midden'], access_type: 'regional'})` |
| Authorized (basic member) | `(True, None, {has_full_access: False, allowed_regions: [], access_type: 'basic_member'})`              |
| Denied                    | `(False, {statusCode: 403, ...}, None)`                                                                 |

### Role-to-Permission Mapping

The `role_permissions` dictionary in `auth_utils.py` defines which Cognito groups grant which permissions:

| Cognito Group            | Granted Permissions                                                                                                                                                                                                                                                                                          |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `System_CRUD`            | `*` (full access to everything)                                                                                                                                                                                                                                                                              |
| `System_User_Management` | `users_manage`, `roles_assign`                                                                                                                                                                                                                                                                               |
| `System_Logs_Read`       | `logs_read`, `audit_read`                                                                                                                                                                                                                                                                                    |
| `Members_CRUD`           | `members_create`, `members_read`, `members_update`, `members_delete`, `members_export`                                                                                                                                                                                                                       |
| `Members_Read`           | `members_read`, `members_list`                                                                                                                                                                                                                                                                               |
| `Members_Export`         | `members_export`, `members_read`                                                                                                                                                                                                                                                                             |
| `Events_CRUD`            | `events_create`, `events_read`, `events_update`, `events_delete`, `events_export`                                                                                                                                                                                                                            |
| `Events_Read`            | `events_read`, `events_list`                                                                                                                                                                                                                                                                                 |
| `Events_Export`          | `events_export`, `events_read`                                                                                                                                                                                                                                                                               |
| `Products_CRUD`          | `products_create`, `products_read`, `products_update`, `products_delete`, `products_export`                                                                                                                                                                                                                  |
| `Products_Read`          | `products_read`, `products_list`                                                                                                                                                                                                                                                                             |
| `Products_Export`        | `products_export`, `products_read`                                                                                                                                                                                                                                                                           |
| `Communication_CRUD`     | `communication_create`, `communication_read`, `communication_update`, `communication_delete`                                                                                                                                                                                                                 |
| `Communication_Read`     | `communication_read`                                                                                                                                                                                                                                                                                         |
| `Communication_Export`   | `communication_export`, `communication_read`                                                                                                                                                                                                                                                                 |
| `Members_Status_Approve` | `members_status_change`                                                                                                                                                                                                                                                                                      |
| `Webshop_Management`     | `products_create`, `products_read`, `products_update`, `products_delete`, `orders_manage`, `webshop_access`                                                                                                                                                                                                  |
| `hdcnLeden`              | `profile_read`, `profile_update_own`, `members_self_read`, `members_self_update`, `events_read`, `events_list`, `products_read`, `products_list`, `webshop_access`, `carts_create`, `carts_read`, `carts_update`, `carts_delete`, `orders_create`, `orders_read_own`, `payments_create`, `payments_read_own` |
| `verzoek_lid`            | `members_self_read`, `members_self_create`, `members_self_update`                                                                                                                                                                                                                                            |

**Important:** Regional roles (`Regio_All`, `Regio_Noord`, `Regio_Midden`, etc.) do NOT grant permissions by themselves. They define the geographic scope of the permissions granted by other roles. A user needs both a permission role (e.g., `Members_CRUD`) AND a regional role (e.g., `Regio_All`) to perform administrative actions.

### Standard Backend Auth Pattern

Every protected Lambda handler follows this pattern:

```python
from shared.auth_utils import (
    extract_user_credentials,
    validate_permissions_with_regions,
    create_success_response,
    create_error_response
)

def lambda_handler(event, context):
    # 1. Extract and validate user identity
    user_email, user_roles, error = extract_user_credentials(event)
    if error:
        return error

    # 2. Check permissions and regional access
    is_authorized, error_response, regional_info = validate_permissions_with_regions(
        user_roles, ['members_read'], user_email, {'operation': 'get_members'}
    )
    if not is_authorized:
        return error_response

    # 3. Use regional_info to filter data
    if not regional_info['has_full_access']:
        # Filter results to user's allowed regions
        allowed_regions = regional_info['allowed_regions']

    # 4. Business logic
    ...
```

## Regional Access Control

The H-DCN portal uses a two-dimensional access control model: **permission roles** define what a user can do, and **regional roles** define which geographic scope they can do it in. Both dimensions are represented as Cognito groups.

### How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│  Access = Permission Role + Regional Role                        │
│                                                                   │
│  Example: Members_CRUD + Regio_Noord                             │
│  → Can create/read/update/delete members in region "Noord" only  │
│                                                                   │
│  Example: Members_CRUD + Regio_All                               │
│  → Can create/read/update/delete members in ALL regions          │
│                                                                   │
│  Example: hdcnLeden (no Regio_* role)                            │
│  → Basic member: self-service only, no admin access              │
└─────────────────────────────────────────────────────────────────┘
```

### Regional Roles

| Role           | Scope                                                       |
| -------------- | ----------------------------------------------------------- |
| `Regio_All`    | National access — equivalent to all regions combined        |
| `Regio_Noord`  | Access limited to members/data in region "Noord"            |
| `Regio_Midden` | Access limited to members/data in region "Midden"           |
| `Regio_Zuid`   | Access limited to members/data in region "Zuid"             |
| `Regio_<name>` | Any other region — pattern is always `Regio_` + region name |

A user can have multiple regional roles (e.g., `Regio_Noord` + `Regio_Midden`) to access multiple regions without having full national access.

### Authorization Logic in `validate_permissions_with_regions`

The function `validate_permissions_with_regions` in `auth_utils.py` evaluates access in this order:

1. **System admins** (`System_CRUD`, `System_User_Management`) → full access, all regions, no further checks
2. **Permission check** → user's roles are mapped to permissions via the `role_permissions` dict. If the user lacks the required permission, access is denied immediately.
3. **Regional check** (only if permission check passes):
   - If user has any `Regio_*` roles → regional access is determined by those roles (even if user also has `hdcnLeden`)
   - `Regio_All` → `has_full_access: True`, `allowed_regions: ['all']`
   - Specific `Regio_<name>` roles → `has_full_access: False`, `allowed_regions: ['Noord', ...]`
   - If user has only `hdcnLeden` / `verzoek_lid` (no `Regio_*`) → basic member access, no regional admin capabilities
   - If user has a permission role but no regional role → access denied with message "Permission requires region assignment"

### Key Rule

**Regional roles do NOT grant permissions by themselves.** They only define geographic scope. A user with `Regio_All` but no permission role (like `Members_CRUD`) cannot perform admin operations — they are just a basic member with national scope metadata.

### Data Filtering

Handlers use the `regional_access_info` returned by `validate_permissions_with_regions` to filter query results:

```python
is_authorized, error_response, regional_info = validate_permissions_with_regions(
    user_roles, ['members_read'], user_email
)

if not regional_info['has_full_access']:
    # Filter DynamoDB results to only include members in allowed regions
    allowed_regions = regional_info['allowed_regions']
    members = [m for m in all_members if m.get('regio') in allowed_regions]
```

The `check_regional_data_access(user_roles, data_region)` helper can also be used for single-record access checks.

## Cognito Groups

All authorization in the H-DCN system is driven by Cognito group membership. Groups are stored in the `cognito:groups` claim of the access token JWT.

### Group Categories

#### Base Member Groups

| Group         | Purpose                                                                                                                                                          |
| ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `hdcnLeden`   | Base member group. Grants webshop access, event viewing, self-service profile management.                                                                        |
| `verzoek_lid` | Applicant group. Assigned to users who submitted a membership application but are not yet approved. Grants access only to the application form and account page. |

#### System Administration Groups

| Group                    | Purpose                                                      |
| ------------------------ | ------------------------------------------------------------ |
| `System_CRUD`            | Full system access — wildcard (`*`) permission on everything |
| `System_User_Management` | Can manage users and assign roles                            |
| `System_Logs_Read`       | Read-only access to logs and audit trails                    |

#### Domain Permission Groups

| Group                    | Purpose                                                   |
| ------------------------ | --------------------------------------------------------- |
| `Members_CRUD`           | Full CRUD on member records (within regional scope)       |
| `Members_Read`           | Read-only access to member records                        |
| `Members_Export`         | Can export member data (also grants read)                 |
| `Members_Status_Approve` | Can change member status (approve/reject applications)    |
| `Events_CRUD`            | Full CRUD on events                                       |
| `Events_Read`            | Read-only access to events                                |
| `Events_Export`          | Can export event data                                     |
| `Products_CRUD`          | Full CRUD on webshop products                             |
| `Products_Read`          | Read-only access to products                              |
| `Products_Export`        | Can export product data                                   |
| `Communication_CRUD`     | Full CRUD on communications                               |
| `Communication_Read`     | Read-only access to communications                        |
| `Communication_Export`   | Can export communication data                             |
| `Webshop_Management`     | Combined product CRUD + order management + webshop access |

#### Regional Scope Groups

| Group          | Purpose                                |
| -------------- | -------------------------------------- |
| `Regio_All`    | National scope — access to all regions |
| `Regio_Noord`  | Scope limited to region "Noord"        |
| `Regio_Midden` | Scope limited to region "Midden"       |
| `Regio_Zuid`   | Scope limited to region "Zuid"         |
| `Regio_<name>` | Scope limited to the named region      |

### Typical Group Combinations

| User Type              | Groups                                             |
| ---------------------- | -------------------------------------------------- |
| New applicant          | `verzoek_lid`                                      |
| Regular member         | `hdcnLeden`                                        |
| Regional admin         | `hdcnLeden`, `Members_CRUD`, `Regio_Noord`         |
| National admin         | `hdcnLeden`, `Members_CRUD`, `Regio_All`           |
| Webmaster / superadmin | `hdcnLeden`, `System_CRUD`                         |
| Event manager          | `hdcnLeden`, `Events_CRUD`, `Regio_All`            |
| Member approver        | `hdcnLeden`, `Members_Status_Approve`, `Regio_All` |

### Group Assignment

- **`verzoek_lid`**: Assigned when a user submits a membership application (or manually by admin)
- **`hdcnLeden`**: Assigned by the PostConfirmation or PostAuthentication trigger when the user's Members record has status `active`/`approved`, or by the RoleAssignment handler when admin approves
- **Permission groups** (`Members_CRUD`, `Events_CRUD`, etc.): Assigned manually by administrators
- **Regional groups** (`Regio_*`): Assigned manually by administrators based on the user's organizational role

## Known Pitfalls

### 1. FORCE_CHANGE_PASSWORD State

**Problem:** Users created by an admin (via `admin_create_user`) start in the `FORCE_CHANGE_PASSWORD` state. While in this state, they cannot use WebAuthn passkeys or email OTP — only password-based login (`USER_SRP_AUTH`) works.

**Why it happens:** Cognito requires the user to complete the `NEW_PASSWORD_REQUIRED` challenge before the account is fully confirmed. The `USER_AUTH` flow (which enables passkeys/OTP) is not available until the account reaches `CONFIRMED` status.

**Solution:** The user must complete a password change first (via the hosted UI or a custom change-password flow). After that, the account moves to `CONFIRMED` and all auth flows become available. Alternatively, use the `fix_force_password_change.py` script to administratively set a password and confirm the user.

**Detection:** Check user status via `aws cognito-idp admin-get-user`. If `UserStatus` is `FORCE_CHANGE_PASSWORD`, the user is stuck.

---

### 2. Google Identity Linking Race Condition

**Problem:** A user signs up with email/password (native account), then later tries to log in with Google SSO using the same email. Without handling, Cognito would create a second, separate account for the Google identity — resulting in duplicate accounts with different group memberships and attributes.

**Why it happens:** Cognito treats native and federated identities as separate users by default. The Google sign-in creates a new user with username `Google_<id>` that has no connection to the existing native user.

**Solution:** The `cognito_pre_signup` Lambda trigger (trigger source `PreSignUp_ExternalProvider`) handles this:

1. Detects that the sign-up is from an external provider
2. Searches for an existing native user with the same email via `list_users`
3. If found, calls `admin_link_provider_for_user` to link the Google identity to the native account
4. Sets `autoConfirmUser = True` and `autoVerifyEmail = True`
5. Handles `InvalidParameterException` gracefully (provider already linked)

After linking, the user can log in with either method and shares the same attributes, groups, and `custom:member_id`.

**Remaining risk:** There is a brief window between the `list_users` check and the `admin_link_provider_for_user` call where a race condition could theoretically occur if two sign-ups happen simultaneously. In practice this is extremely unlikely for a club portal.

---

### 3. verzoek_lid Cleanup After Approval

**Problem:** When an admin approves a member and the RoleAssignment handler adds them to `hdcnLeden`, the user should also be removed from `verzoek_lid`. This removal is not automatic in all flows.

**Why it happens:** The RoleAssignment handler (triggered by DynamoDB Streams on member status change) handles the removal. However, if the admin manually adds the user to `hdcnLeden` via the Cognito console or a different code path, the `verzoek_lid` group may not be removed.

**Impact:** A user with both `verzoek_lid` and `hdcnLeden` is treated as a full member by the GroupAccessGuard (it checks for any group besides `verzoek_lid`). So functionally there is no access issue — but the stale group creates confusion in admin views and audit logs.

**Solution:** Always use the standard approval flow (update member status in DynamoDB → RoleAssignment handler fires → adds `hdcnLeden` + removes `verzoek_lid`). If manual intervention is needed, remember to remove `verzoek_lid` explicitly.

---

### 4. Cognito User Pool Not in CloudFormation

**Problem:** The Cognito User Pool (`eu-west-1_fcUkvwjH5`) is managed outside CloudFormation/SAM. Adding it as a CloudFormation resource without `DeletionPolicy: Retain` will delete the pool (and all user accounts) on the next stack update or deletion.

**Why it happened:** A previous deployment included the Cognito pool as a CloudFormation resource. When the stack was updated, CloudFormation replaced the pool — deleting all production user accounts, credentials, and group memberships.

**Solution:** Never add the Cognito pool, DynamoDB tables, or S3 data buckets to the SAM template as managed resources. They are referenced via parameters:

```yaml
# In template.yaml — reference only, never create
Parameters:
  ExistingUserPoolId:
    Type: String
    Default: eu-west-1_fcUkvwjH5
  ExistingUserPoolClientId:
    Type: String
    Default: 6jhvk853b0lfg9q1m861qs0cug
```

Lambda triggers are attached to the pool via SAM events, but the pool itself is not a stack resource.

---

### 5. Access Token JWT Requirements

**Problem:** The backend expects the `cognito:groups` claim to determine user permissions. This claim is only present in the **access token**, not in the ID token. Sending the wrong token type results in empty groups and permission denied errors.

**Why it matters:** Cognito issues three tokens — ID token, access token, and refresh token. The ID token contains user attributes (`email`, `name`, etc.) but does NOT include `cognito:groups`. The access token contains `cognito:groups` but fewer user attributes.

**Frontend requirement:** The frontend must send the access token (not the ID token) in the `Authorization: Bearer` header:

```typescript
// Correct — uses access token
const session = await fetchAuthSession();
const accessToken = session.tokens?.accessToken?.toString();
headers["Authorization"] = `Bearer ${accessToken}`;

// WRONG — ID token does not contain cognito:groups
const idToken = session.tokens?.idToken?.toString();
```

**Backend extraction:** `extract_user_credentials` decodes the JWT payload and reads `cognito:groups`. If this field is missing (because an ID token was sent), the user appears to have no groups and all permission checks fail.

---

### 6. Google SSO Sign-Out

**Problem:** Calling Amplify's `signOut()` clears the local Amplify session and Cognito tokens, but does NOT clear the Google session. The next time the user visits the login page, Google SSO may automatically re-authenticate them without prompting for credentials.

**Why it happens:** Amplify `signOut()` only revokes the Cognito session. The Google OAuth session (managed by Google's servers) remains active in the browser. When the user clicks "Sign in with Google" again, Google recognizes the existing session and immediately redirects back with a new authorization code.

**Solution:** The AuthProvider's `signOut()` function redirects to the Cognito hosted UI logout endpoint after clearing the local session:

```
https://h-dcn-auth-506221081911.auth.eu-west-1.amazoncognito.com/logout?
  client_id=6jhvk853b0lfg9q1m861qs0cug&
  logout_uri=https://portal.h-dcn.nl/
```

This clears the Cognito session cookie. For a complete sign-out that also clears the Google session, the user must manually sign out of their Google account, or the app can use `globalSignOut` (which revokes all tokens but still doesn't clear Google's session).

**Practical impact:** For a club portal, this is acceptable behavior. Users who want a full sign-out can sign out of Google separately. The Cognito logout endpoint ensures that a new Cognito session requires re-authentication.
