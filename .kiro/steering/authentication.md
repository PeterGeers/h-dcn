# Authentication

Quick-reference for the H-DCN authentication system (Cognito + Amplify v6).

## Login Paths

- **Passkey / Email OTP**: Native Cognito WebAuthn or email-based one-time password
- **Google SSO**: Google Workspace identity provider linked to Cognito
- Both paths converge through **AWS Amplify v6** on the frontend (`AuthProvider` context)

## Cognito Configuration

| Setting        | Value                        |
| -------------- | ---------------------------- |
| Pool ID        | `eu-west-1_fcUkvwjH5`        |
| App Client ID  | `6jhvk853b0lfg9q1m861qs0cug` |
| Pool Tier      | PLUS (WebAuthn/passkeys)     |
| WebAuthn RP ID | `h-dcn.nl`                   |
| Region         | eu-west-1                    |

- Auth flows: `ALLOW_USER_AUTH`, `ALLOW_REFRESH_TOKEN_AUTH`, `ALLOW_USER_SRP_AUTH`, `ALLOW_CUSTOM_AUTH`
- Cognito pool is managed **outside** CloudFormation (created manually)

## Backend Auth Pattern

Every protected Lambda handler follows this sequence:

```python
user_email, user_roles, error = extract_user_credentials(event)
if error:
    return error

permission_error = validate_permissions_with_regions(user_roles, required_permission, user_email)
if permission_error:
    return permission_error

# Business logic here
```

- Source: `backend/layers/auth-layer/python/shared/auth_utils.py`
- Frontend sends **access token** (not ID token) in `Authorization: Bearer <jwt>` header

## Critical Rules

- **Never add Cognito pool to CloudFormation** — managed externally, previous deploy deleted prod data
- **FORCE_CHANGE_PASSWORD**: Users stuck in this state cannot sign in with passkeys; must complete password change first
- **Google SSO sign-out**: Amplify `signOut()` does not clear Google session; users must also sign out of Google or use `globalSignOut`
- **verzoek_lid cleanup**: After admin approves a member, remove them from `verzoek_lid` group (not automatic)
- **Access token required**: Backend expects `cognito:groups` claim which is only in the access token JWT, not the ID token
- **Google identity linking**: Race condition possible if user signs up with email then tries Google SSO — handle via `cognito_pre_signup` trigger

## Reference

- Full architecture details: [`docs/authentication-architecture.md`](../../docs/authentication-architecture.md)
