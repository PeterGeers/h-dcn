# Implementation Plan: Authentication Architecture Documentation

## Overview

Create two authentication reference documents (steering + architecture) and clean up obsolete specs/docs. All tasks involve creating or deleting files — no application code changes.

## Tasks

- [x] 1. Create the authentication steering document
  - [x] 1.1 Create `.kiro/steering/authentication.md` with all required sections
    - Include title and one-line purpose
    - Login paths summary (Passkey/Email OTP + Google SSO → Amplify v6)
    - Cognito config values (Pool ID `eu-west-1_fcUkvwjH5`, Client ID `6jhvk853b0lfg9q1m861qs0cug`, WebAuthn RP ID `h-dcn.nl`, auth flows)
    - Backend auth pattern (`extract_user_credentials` → `validate_permissions_with_regions` → business logic)
    - Critical rules / pitfalls section
    - Reference link to `docs/authentication-architecture.md`
    - Must be ≤ 80 lines, English, bullet points/headers/code blocks only — no prose paragraphs
    - Match style of existing `tech.md` and `aws-dynamodb.md`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8_

- [x] 2. Create the authentication architecture document
  - [x] 2.1 Create `docs/authentication-architecture.md` with overview and architecture diagram
    - System overview and summary
    - ASCII architecture diagram showing login → session → API call flow
    - _Requirements: 2.1, 2.2_

  - [x] 2.2 Add Cognito Pool configuration section
    - Pool ID, App Client ID, Cognito domain, WebAuthn RP ID, pool tier (PLUS)
    - OAuth callback URLs, OAuth scopes, identity providers
    - Enabled auth flows (ALLOW_USER_AUTH, ALLOW_REFRESH_TOKEN_AUTH, ALLOW_USER_SRP_AUTH, ALLOW_CUSTOM_AUTH)
    - _Requirements: 2.3_

  - [x] 2.3 Add frontend and backend file locations
    - Frontend: AuthProvider, CustomAuthenticator, GroupAccessGuard, useAuth hook, aws-exports
    - Backend: Auth_Utils_Layer (`backend/layers/auth-layer/python/shared/auth_utils.py`), all Cognito trigger handlers (`cognito_pre_signup`, `cognito_post_authentication`, `cognito_post_confirmation`, `cognito_custom_message`, `cognito_user_migration`, `cognito_role_assignment`)
    - _Requirements: 2.4, 2.5_

  - [x] 2.4 Add Cognito triggers documentation
    - Document each trigger: trigger source, purpose, key behavior
    - Triggers: PreSignUp, PostAuthentication, PostConfirmation, CustomMessage, UserMigration
    - _Requirements: 2.6_

  - [x] 2.5 Add user lifecycle and auth component documentation
    - Complete user lifecycle: signup → verzoek_lid → admin approval → hdcnLeden → role assignment
    - AuthProvider responsibilities, `useAuth()` hook interface, GroupAccessGuard behavior
    - Auth_Utils_Layer functions and role-to-permission mapping
    - _Requirements: 2.7, 2.8, 2.9_

  - [x] 2.6 Add regional access control, Cognito groups, and pitfalls sections
    - Regional access control model (Regio*All, Regio*\* roles)
    - Cognito groups and meanings (hdcnLeden, verzoek*lid, System_CRUD, Members_CRUD, Regio*\*, etc.)
    - Known pitfalls with explanations and solutions (FORCE_CHANGE_PASSWORD, Google identity linking race conditions, verzoek_lid cleanup, Cognito not in CloudFormation, access token JWT requirements, Google SSO sign-out)
    - Document must be written in English
    - _Requirements: 2.10, 2.11, 2.12, 2.13_

- [x] 3. Checkpoint - Review documents before cleanup
  - Ensure steering document is ≤ 80 lines and matches existing steering doc style
  - Ensure architecture document contains all 12 required sections
  - Ask the user if questions arise.

- [x] 4. Clean up obsolete specs and documentation
  - [x] 4.1 Delete `.kiro/specs/passkey-cognito-fix/` directory and all contents
    - Verify the directory no longer exists after deletion
    - _Requirements: 3.1, 3.2_

  - [x] 4.2 Delete `.kiro/specs/cognito-authentication/` directory and all contents
    - Verify the directory no longer exists after deletion
    - _Requirements: 4.1, 4.2_

  - [x] 4.3 Delete `docs/authentication/` directory and all contents
    - Contains: cognito-configuration.md, google-sso-setup.md, login-screen-improvements.md, passkey-implementation.md, troubleshooting.md, user-management.md
    - Verify the directory no longer exists after deletion
    - Verify no new files were created inside `docs/authentication/` path
    - _Requirements: 6.1, 6.2, 6.3_

  - [x] 4.4 Verify `.kiro/specs/unified-auth-flow/` is preserved
    - Confirm `design.md` and `requirements.md` still exist in that directory
    - Confirm no files were modified or deleted
    - _Requirements: 5.1, 5.2_

- [x] 5. Final checkpoint - Verify all deliverables
  - Ensure steering document exists at `.kiro/steering/authentication.md`
  - Ensure architecture document exists at `docs/authentication-architecture.md`
  - Ensure all three obsolete directories are removed
  - Ensure unified-auth-flow spec is untouched
  - Ask the user if questions arise.

## Notes

- This is a documentation-only feature — no application code changes are involved
- Property-based testing is not applicable (static markdown files, no code logic)
- Cleanup tasks (4.1–4.3) must only run AFTER documents are created and reviewed
- The architecture document lives at `docs/authentication-architecture.md` (root of docs/), NOT inside the deleted `docs/authentication/` subdirectory
- All Cognito config values should be sourced from the existing `aws-dynamodb.md` steering doc and `backend/template.yaml`

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "2.1"] },
    { "id": 1, "tasks": ["2.2", "2.3"] },
    { "id": 2, "tasks": ["2.4", "2.5"] },
    { "id": 3, "tasks": ["2.6"] },
    { "id": 4, "tasks": ["4.1", "4.2", "4.3"] },
    { "id": 5, "tasks": ["4.4"] }
  ]
}
```
