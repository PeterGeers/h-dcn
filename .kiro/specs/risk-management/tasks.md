# Implementation Plan: Risk Management — Credential Security

## Overview

This plan implements four independent credential security mitigations: AWS SSO migration (config-only), Google Workload Identity Federation for Lambda, Google service account consolidation with 90-day expiry enforcement, and PowerShell shell history secret prevention. Each component is self-contained — they can be implemented in any order without dependencies between them.

## Tasks

- [ ] 1. AWS SSO Profile Configuration
  - [ ] 1.1 Configure AWS SSO session and profile in `~/.aws/config`
    - Add `[sso-session h-dcn]` section with `sso_start_url`, `sso_region`, `sso_registration_scopes`
    - Update `[profile nonprofit-deploy]` to reference `sso_session = h-dcn` with `sso_account_id`, `sso_role_name = NonprofitDeployAccess`, `region`, `output`
    - Run `aws sso login --profile nonprofit-deploy` and verify with `aws sts get-caller-identity --profile nonprofit-deploy`
    - _Requirements: 1.1, 1.2, 1.5_

  - [ ] 1.2 Verify SSO profile permissions match current static credentials
    - Execute `sam deploy --profile nonprofit-deploy` (dry-run or small change)
    - Execute `aws s3 ls --profile nonprofit-deploy`
    - Execute `aws dynamodb list-tables --profile nonprofit-deploy`
    - Confirm GitHub Actions workflows are unaffected (they use OIDC role assumption)
    - _Requirements: 1.3, 1.5, 1.6, 1.7_

  - [ ] 1.3 Remove static credentials from `~/.aws/credentials`
    - Remove the `[nonprofit-deploy]` section from `~/.aws/credentials`
    - Verify `aws sts get-caller-identity --profile nonprofit-deploy` still works via SSO
    - _Requirements: 1.4_

- [ ] 2. Google Workload Identity Federation (Lambda)
  - [ ] 2.1 Create Google Cloud WIF resources (pool, provider, SA binding)
    - Create Workload Identity Pool `h-dcn-aws-pool`
    - Create AWS provider `aws-lambda-provider` with account ID `506221081911` and attribute condition restricting to `h-dcn-SyncGoogleCalendarRole`
    - Bind service account with `roles/iam.workloadIdentityUser` to the pool principal set
    - _Requirements: 2.6_

  - [ ] 2.2 Modify `sync_google_calendar/app.py` to use WIF authentication
    - Replace `_get_google_credentials_json()` with `_build_wif_credentials()` using `google.auth.identity_pool.Credentials`
    - Configure audience, subject_token_type, token_url, credential_source (AWS environment), scopes (`calendar`), and service_account_impersonation_url
    - Update `_build_calendar_service()` to use WIF credentials
    - Ensure Lambda returns HTTP 500 with clear error message on WIF failure — no fallback to SSM
    - _Requirements: 2.1, 2.2, 2.5_

  - [ ] 2.3 Update SAM template for WIF migration
    - Remove `SSMGetParameterPolicy` for `/h-dcn/google-credentials` from `SyncGoogleCalendarRole`
    - Remove `GOOGLE_CREDENTIALS_PARAMETER` environment variable from the function
    - Verify `sts:GetCallerIdentity` permission is available (Lambda basic execution role)
    - _Requirements: 2.1, 2.3_

  - [ ]\* 2.4 Write unit tests for WIF credential builder
    - Test `_build_wif_credentials()` returns correct audience and subject_token_type
    - Test Lambda returns 500 with error message when WIF fails (mock `identity_pool.Credentials`)
    - Test no fallback to SSM parameter read on WIF failure
    - _Requirements: 2.1, 2.5_

  - [ ] 2.5 Delete SSM parameter `/h-dcn/google-credentials` after WIF verification
    - Invoke Lambda with a test event and confirm Google Calendar sync succeeds via WIF
    - Delete SSM parameter `/h-dcn/google-credentials`
    - Verify `/h-dcn/google-photos-oauth` is retained (Photos requires OAuth user consent, not WIF)
    - _Requirements: 2.3, 2.4_

- [ ] 3. Checkpoint — Verify AWS SSO and Google WIF
  - Ensure SSO profile works for all CLI operations and SAM deploys
  - Ensure Lambda successfully authenticates via WIF
  - Ask the user if questions arise.

- [ ] 4. Google Service Account Consolidation (Local Dev)
  - [ ] 4.1 Audit and consolidate Google service accounts
    - List all service accounts in the Google Cloud project
    - Identify unused/duplicate service accounts and their keys
    - Keep single SA (`h-dcn-local-dev@{project}.iam.gserviceaccount.com`) with required scopes: `spreadsheets.readonly`, `drive.readonly`, `drive.file`, `calendar`, `calendar.readonly`
    - Delete all other service accounts and keys
    - _Requirements: 2b.1, 2b.2_

  - [ ] 4.2 Set org policy for 90-day key expiry
    - Set `constraints/iam.serviceAccountKeyExpiryHours` = `2160` on the Google Cloud project
    - Generate a fresh key for the consolidated service account → save as `.googleCredentials.json`
    - Verify key expiry via `gcloud iam service-accounts keys list` showing `valid_before` timestamp
    - _Requirements: 2b.3, 2b.4_

  - [ ] 4.3 Create verification script for service account connectivity
    - Write Python script `scripts/verify_google_sa.py` that tests: gspread (read one row), Calendar API (list events), Drive API (list files), Drive upload (create + delete test file)
    - Run verification to confirm consolidated SA works for all integrations
    - _Requirements: 2b.6_

  - [ ] 4.4 Create rotation reminder and document inventory
    - Create recurring Google Calendar event (every 83 days) titled "Rotate .googleCredentials.json key" with rotation steps in description
    - Document inventory of the single active service account: email, project, granted roles, authorized scopes
    - _Requirements: 2b.5, 2b.7_

- [ ] 5. PowerShell Shell History Secret Prevention
  - [ ] 5.1 Implement AddToHistoryHandler in PowerShell `$PROFILE`
    - Add `Set-PSReadLineOption -AddToHistoryHandler` block to `$PROFILE` (Microsoft.PowerShell_profile.ps1)
    - Implement regex patterns for: AWS keys (`AKIA...`), private keys (`BEGIN...PRIVATE KEY`), Stripe keys (`sk_live_`, `pk_live_`), Mollie keys (`live_`/`test_` + alphanumeric), GitHub/GitLab tokens (`ghp_`, `glpat-`), Google API keys (`AIza...`), Slack tokens (`xox[bpors]-`), Bearer tokens
    - Return `SkipAdding` for matches, `MemoryAndFile` for non-matches
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.7_

  - [ ] 5.2 Implement Python secret filter module for testing
    - Create `backend/handler/secret_filter/secret_patterns.py` with the same regex patterns as the PowerShell handler
    - Implement `contains_secret(line: str) -> bool` function mirroring the PowerShell logic
    - This enables property-based testing of the regex patterns in Python (Hypothesis)
    - _Requirements: 3.1, 3.2_

  - [ ]\* 5.3 Write property test: Secret pattern detection
    - **Property 1: Secret pattern detection**
    - **Validates: Requirements 3.1, 3.2, 3.5**
    - Create `backend/tests/unit/test_secret_filter_properties.py`
    - Use Hypothesis to generate command strings containing embedded secret patterns (random pattern type, random position, random surrounding text)
    - Assert `contains_secret()` returns `True` for all generated strings

  - [ ]\* 5.4 Write property test: Non-secret passthrough
    - **Property 2: Non-secret passthrough**
    - **Validates: Requirements 3.1, 3.4, 3.5**
    - Use Hypothesis to generate plausible PowerShell commands that don't match secret patterns (e.g., `Get-Process`, `ls -la`, `git status`, random alphanumeric strings)
    - Assert `contains_secret()` returns `False` for all generated strings

  - [ ]\* 5.5 Write unit tests for secret filter edge cases
    - Test each pattern family matches a known example (one per pattern)
    - Test edge cases: partial matches that should NOT trigger (e.g., `AKIA` alone without 16 chars, `test_` with fewer than 20 chars)
    - Test that normal commands with coincidental substrings pass through
    - _Requirements: 3.2_

  - [ ] 5.6 Implement one-time history cleanup script
    - Create `scripts/cleanup_powershell_history.ps1`
    - Backup existing history file to `$histPath.backup.<timestamp>`
    - Remove lines matching secret patterns from history file
    - Report number of lines removed
    - Handle edge cases: locked file (retry once after 1s), empty file (report 0 removed)
    - _Requirements: 3.5, 3.6_

- [ ] 6. Final checkpoint — Ensure all tests pass
  - Run `pytest backend/tests/unit/test_secret_filter_properties.py` to verify property tests
  - Verify PowerShell AddToHistoryHandler is registered in `$PROFILE`
  - Verify cleanup script creates backup before modifying history
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Components 1–4 are independent — implement in any order
- Property tests validate the regex logic (Requirement 3) using Hypothesis (already in use in this project)
- AWS SSO and Google WIF are infrastructure/config changes verified by smoke tests, not unit tests
- Google Photos OAuth token (`/h-dcn/google-photos-oauth`) is intentionally retained — WIF cannot replace user-consent OAuth scopes
- The Python `secret_patterns.py` module mirrors the PowerShell regex patterns to enable PBT — the PowerShell `$PROFILE` is the production artifact

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "2.1", "4.1", "5.1"] },
    { "id": 1, "tasks": ["1.2", "2.2", "4.2", "5.2"] },
    { "id": 2, "tasks": ["1.3", "2.3", "4.3", "5.3", "5.4"] },
    { "id": 3, "tasks": ["2.4", "4.4", "5.5", "5.6"] },
    { "id": 4, "tasks": ["2.5"] }
  ]
}
```
