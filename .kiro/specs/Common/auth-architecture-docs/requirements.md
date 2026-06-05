# Requirements Document

## Introduction

This feature creates two authentication reference documents and cleans up obsolete spec directories. The steering document provides a concise quick-reference for developers (like the existing `tech.md` and `aws-dynamodb.md` steering docs). The architecture document provides the comprehensive deep-dive with diagrams, full lifecycle, and detailed explanations. Together they replace the need to read multiple obsolete spec files.

## Glossary

- **Steering_Document**: A short markdown file in `.kiro/steering/` (max ~60-80 lines) providing key rules, constraints, and pitfalls for a specific domain. Written for quick scanning during development.
- **Architecture_Document**: A comprehensive markdown file in `docs/` providing full architectural detail including diagrams, lifecycle flows, configuration values, and file locations.
- **Cognito_Pool**: The AWS Cognito User Pool (`eu-west-1_fcUkvwjH5`) that stores user accounts, credentials, and group memberships.
- **Auth_Utils_Layer**: The shared Lambda Layer (`backend/layers/auth-layer/python/shared/auth_utils.py`) providing JWT validation and permission checking for all backend handlers.
- **Cognito_Trigger**: A Lambda function invoked by Cognito at specific points in the authentication lifecycle (PreSignUp, PostAuthentication, PostConfirmation, CustomMessage, UserMigration).
- **AuthProvider**: The React context provider (`frontend/src/context/AuthProvider.tsx`) that manages authentication state via Amplify v6.
- **Obsolete_Spec**: A spec directory in `.kiro/specs/` that documents an approach or fix that has been fully superseded by the unified-auth-flow implementation.

## Requirements

### Requirement 1: Create Authentication Steering Document

**User Story:** As a developer, I want a concise authentication steering document matching the style of existing steering docs, so that I can quickly look up auth rules, constraints, and pitfalls without reading a full architecture document.

#### Acceptance Criteria

1. THE Steering_Document SHALL be created at the path `.kiro/steering/authentication.md`
2. THE Steering_Document SHALL be no longer than 80 lines, matching the concise style of `tech.md` and `aws-dynamodb.md`
3. THE Steering_Document SHALL include a brief summary of the two login paths (Passkey/Email OTP and Google SSO) converging through Amplify v6
4. THE Steering_Document SHALL list key Cognito config values (Pool ID, App Client ID, WebAuthn RP ID, auth flows) in a compact format
5. THE Steering_Document SHALL document the standard backend auth pattern (extract credentials → validate permissions → business logic)
6. THE Steering_Document SHALL include a "Critical Rules" or "Pitfalls" section listing common mistakes and constraints (Cognito not in CloudFormation, FORCE_CHANGE_PASSWORD issue, Google SSO sign-out requirement, verzoek_lid cleanup)
7. THE Steering_Document SHALL reference the Architecture_Document for full details
8. THE Steering_Document SHALL be written in English using bullet points, headers, and code blocks — no prose paragraphs

### Requirement 2: Create Authentication Architecture Document

**User Story:** As a developer, I want a comprehensive authentication architecture document, so that I can understand the full auth system including diagrams, lifecycle flows, all configuration values, and file locations.

#### Acceptance Criteria

1. THE Architecture_Document SHALL be created at the path `docs/authentication-architecture.md`
2. THE Architecture_Document SHALL include an ASCII architecture diagram showing the flow from login through session creation to API calls
3. THE Architecture_Document SHALL document the Cognito_Pool configuration including pool ID, App Client ID, Cognito domain, WebAuthn RP ID, pool tier, OAuth callback URLs, OAuth scopes, identity providers, and enabled auth flows
4. THE Architecture_Document SHALL list all file locations for auth-related frontend code (AuthProvider, CustomAuthenticator, GroupAccessGuard, useAuth hook, aws-exports)
5. THE Architecture_Document SHALL list all file locations for auth-related backend code (Auth_Utils_Layer, all Cognito_Trigger handlers)
6. THE Architecture_Document SHALL document each Cognito_Trigger with its trigger source, purpose, and key behavior
7. THE Architecture_Document SHALL describe the complete user lifecycle from signup through verzoek_lid group assignment, admin approval, hdcnLeden group assignment, and role assignment
8. THE Architecture_Document SHALL describe the AuthProvider component responsibilities, the `useAuth()` hook interface, and GroupAccessGuard behavior
9. THE Architecture_Document SHALL document the Auth_Utils_Layer functions (`extract_user_credentials`, `validate_permissions_with_regions`) and the role-to-permission mapping
10. THE Architecture*Document SHALL describe the regional access control model (Regio_All, Regio*\* roles)
11. THE Architecture_Document SHALL document all known pitfalls with detailed explanations and solutions (FORCE_CHANGE_PASSWORD, Google identity linking race conditions, verzoek_lid cleanup, Cognito not in CloudFormation, access token JWT requirements, Google SSO sign-out)
12. THE Architecture*Document SHALL document Cognito groups and their meanings (hdcnLeden, verzoek_lid, System_CRUD, Members_CRUD, Regio*\*, etc.)
13. THE Architecture_Document SHALL be written in English

### Requirement 3: Remove Obsolete Passkey-Cognito-Fix Spec

**User Story:** As a developer, I want obsolete specs removed, so that I do not waste time reading outdated documentation that contradicts the current implementation.

#### Acceptance Criteria

1. WHEN the Steering_Document and Architecture_Document are complete, THE cleanup process SHALL delete the directory `.kiro/specs/passkey-cognito-fix/` and all its contents
2. THE cleanup process SHALL verify that the directory `.kiro/specs/passkey-cognito-fix/` no longer exists after deletion

### Requirement 4: Remove Obsolete Cognito-Authentication Spec

**User Story:** As a developer, I want the outdated cognito-authentication spec removed, so that its references to old pool IDs, DIY passkey implementations, and obsolete migration strategies do not cause confusion.

#### Acceptance Criteria

1. WHEN the Steering_Document and Architecture_Document are complete, THE cleanup process SHALL delete the directory `.kiro/specs/cognito-authentication/` and all its contents
2. THE cleanup process SHALL verify that the directory `.kiro/specs/cognito-authentication/` no longer exists after deletion

### Requirement 5: Preserve Current Unified-Auth-Flow Spec

**User Story:** As a developer, I want the unified-auth-flow spec preserved, so that the authoritative implementation record remains available.

#### Acceptance Criteria

1. THE cleanup process SHALL NOT modify or delete any files in `.kiro/specs/unified-auth-flow/`
2. AFTER cleanup, THE directory `.kiro/specs/unified-auth-flow/` SHALL still contain its design.md and requirements.md files

### Requirement 6: Remove Outdated Authentication Documentation Directory

**User Story:** As a developer, I want the outdated `docs/authentication/` directory removed, so that I do not encounter documentation referencing old pool IDs, old client IDs, old CloudFront domains, DIY passkey implementations, and obsolete role names that contradict the current architecture.

#### Acceptance Criteria

1. WHEN the Architecture_Document is complete at `docs/authentication-architecture.md`, THE cleanup process SHALL delete the directory `docs/authentication/` and all its contents (cognito-configuration.md, google-sso-setup.md, login-screen-improvements.md, passkey-implementation.md, troubleshooting.md, user-management.md)
2. THE cleanup process SHALL verify that the directory `docs/authentication/` no longer exists after deletion
3. THE cleanup process SHALL NOT create any new files inside the `docs/authentication/` path — the new Architecture_Document is placed at `docs/authentication-architecture.md` (at the docs root, not in the deleted subdirectory)

## Out of Scope

- Changes to any authentication code (frontend or backend)
- Changes to Cognito User Pool configuration
- Changes to Lambda triggers or the auth_utils layer
- Creating new authentication features
- Modifying the unified-auth-flow spec content
