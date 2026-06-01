# Design Document

## Overview

This feature creates two complementary authentication reference documents and performs cleanup of obsolete specs and docs. The deliverables are:

1. **Steering Document** (`.kiro/steering/authentication.md`) — A concise quick-reference (≤80 lines) for developers, matching the style of existing steering docs like `tech.md` and `aws-dynamodb.md`.
2. **Architecture Document** (`docs/authentication-architecture.md`) — A comprehensive deep-dive with diagrams, lifecycle flows, all configuration values, file locations, and pitfalls.
3. **Cleanup** — Remove obsolete spec directories (`passkey-cognito-fix/`, `cognito-authentication/`) and the outdated `docs/authentication/` directory.

The documents consolidate information currently scattered across multiple obsolete specs and docs into a single authoritative source per audience (quick-reference vs. deep-dive).

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Documentation Structure                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  .kiro/steering/authentication.md    ← Quick-reference (≤80 lines)│
│       │                                                           │
│       └── References ──→ docs/authentication-architecture.md      │
│                          ← Comprehensive deep-dive                │
│                                                                   │
├─────────────────────────────────────────────────────────────────┤
│  PRESERVED:                                                       │
│    .kiro/specs/unified-auth-flow/  (design.md, requirements.md)  │
│                                                                   │
│  REMOVED:                                                         │
│    .kiro/specs/passkey-cognito-fix/                               │
│    .kiro/specs/cognito-authentication/                            │
│    docs/authentication/  (6 files)                                │
└─────────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### Component 1: Steering Document

**Path:** `.kiro/steering/authentication.md`

**Purpose:** Provide developers with a scannable quick-reference for auth rules, constraints, and common pitfalls during development.

**Format constraints:**

- Maximum 80 lines
- English language
- Bullet points, headers, and code blocks only — no prose paragraphs
- Matches style of existing `tech.md` and `aws-dynamodb.md` steering docs

**Content sections:**

1. Title and one-line purpose
2. Login paths summary (Passkey/Email OTP + Google SSO → Amplify v6)
3. Cognito config values (Pool ID, Client ID, WebAuthn RP ID, auth flows)
4. Backend auth pattern (`extract_user_credentials` → `validate_permissions_with_regions` → business logic)
5. Critical rules / pitfalls (compact list)
6. Reference link to architecture document

### Component 2: Architecture Document

**Path:** `docs/authentication-architecture.md`

**Purpose:** Provide comprehensive architectural documentation for the entire auth system.

**Content sections:**

1. Overview and system summary
2. ASCII architecture diagram (login → session → API call flow)
3. Cognito Pool configuration (all values)
4. Frontend file locations and component descriptions
5. Backend file locations (auth layer + all triggers)
6. Cognito trigger documentation (trigger source, purpose, behavior)
7. User lifecycle (signup → verzoek_lid → approval → hdcnLeden → roles)
8. AuthProvider, useAuth hook, and GroupAccessGuard documentation
9. Auth Utils Layer functions and role-to-permission mapping
10. Regional access control model
11. Cognito groups and their meanings
12. Known pitfalls with explanations and solutions

### Component 3: Cleanup Process

**Operations:**

- Delete `.kiro/specs/passkey-cognito-fix/` directory and all contents
- Delete `.kiro/specs/cognito-authentication/` directory and all contents
- Delete `docs/authentication/` directory and all contents (6 files)
- Verify each directory no longer exists after deletion
- Verify `.kiro/specs/unified-auth-flow/` is untouched (contains `design.md`, `requirements.md`)

## Data Models

No data models are required. This feature produces static markdown documentation files and performs file system cleanup. No runtime data structures, database schemas, or API contracts are involved.

## Error Handling

| Scenario                                            | Handling                                                         |
| --------------------------------------------------- | ---------------------------------------------------------------- |
| Target directory for steering doc doesn't exist     | Create `.kiro/steering/` if needed (it already exists)           |
| Target directory for architecture doc doesn't exist | Create `docs/` if needed (it already exists)                     |
| Obsolete spec directory doesn't exist               | Skip deletion, log that it was already removed                   |
| File write fails                                    | Report error, do not proceed with cleanup until docs are written |
| Cleanup accidentally targets wrong directory        | Verify exact paths before deletion; never use wildcards          |
| unified-auth-flow accidentally modified             | Verify its contents remain unchanged after cleanup               |

## Testing Strategy

**Property-based testing is NOT applicable** for this feature because:

- The deliverables are static markdown files (documentation), not code with inputs/outputs
- The cleanup operations are file system deletions with no transformation logic
- There are no pure functions, parsers, serializers, or algorithms to test

**Appropriate testing approach:**

1. **Content validation (manual review):**
   - Steering document ≤ 80 lines
   - Steering document contains required sections (login paths, config values, backend pattern, pitfalls, reference link)
   - Architecture document contains all 12 required sections
   - All Cognito config values are accurate and current
   - All file paths referenced in documents actually exist in the codebase

2. **Cleanup verification (automated checks):**
   - `.kiro/specs/passkey-cognito-fix/` does not exist after cleanup
   - `.kiro/specs/cognito-authentication/` does not exist after cleanup
   - `docs/authentication/` does not exist after cleanup
   - `.kiro/specs/unified-auth-flow/design.md` still exists
   - `.kiro/specs/unified-auth-flow/requirements.md` still exists
   - `docs/authentication-architecture.md` exists (new file, not in deleted subdirectory)

3. **Style validation:**
   - Steering document uses no prose paragraphs
   - Steering document uses bullet points, headers, and code blocks only
   - Both documents are written in English
