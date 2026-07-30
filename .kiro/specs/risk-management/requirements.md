# Requirements Document

## Introduction

This feature addresses credential security risks on the developer laptop for the H-DCN project. While repository-level scanning (GitGuardian pre-commit/pre-push hooks) protects against secrets entering git, local credentials — static AWS keys, Google service account keys, shell history entries, and non-tracked files — remain vulnerable to theft if the laptop is compromised. This spec formalizes the migration to short-lived credentials, automated scanning of local files, and a credential rotation policy.

## Glossary

- **SSO_Profile**: An AWS CLI profile configured to authenticate via AWS IAM Identity Center, producing session tokens that expire automatically (1–12 hours)
- **Static_Credentials**: Long-lived AWS access key pairs stored in `~/.aws/credentials` that remain valid until manually revoked
- **WIF**: Google Workload Identity Federation — a mechanism that allows workloads to impersonate a Google service account using short-lived tokens without requiring a key file on disk
- **Shell_History**: The PowerShell command history file located at the path returned by `(Get-PSReadLineOption).HistorySavePath`
- **Permission_Set**: An AWS IAM Identity Center construct that defines the IAM policies attached to an SSO session
- **Rotation_Policy**: A documented schedule specifying when each credential type must be replaced or regenerated
- **Credential_Store**: Any local file or location on the developer machine that contains authentication material (keys, tokens, passwords)

## Requirements

### Requirement 1: AWS SSO Migration

**User Story:** As a developer, I want to authenticate to AWS using short-lived SSO session tokens, so that stolen laptop credentials expire automatically and cannot be reused indefinitely.

#### Acceptance Criteria

1. WHEN the developer runs `aws sso login --profile nonprofit-deploy`, THE SSO_Profile SHALL authenticate via AWS IAM Identity Center and produce a session token with a configurable expiry between 1 and 12 hours
2. WHEN the SSO session token expires, THE SSO_Profile SHALL require re-authentication before any AWS CLI or SDK operation succeeds
3. WHEN the SSO_Profile is configured, THE SSO_Profile SHALL provide the same IAM permissions as the current `NonprofitDeployRole` (account 506221081911, region eu-west-1), verified by successfully executing `sam deploy`, `aws s3 ls`, and `aws dynamodb list-tables` with the SSO profile
4. WHEN the SSO_Profile is verified functional by completing a SAM deploy and at least one CLI operation using `--profile nonprofit-deploy`, THE Static_Credentials SHALL be removed from `~/.aws/credentials` for the `nonprofit-deploy` profile
5. WHEN a SAM deploy command uses `--profile nonprofit-deploy`, THE SSO_Profile SHALL provide valid credentials without requiring changes to the deploy command syntax
6. IF the SSO session token has expired during a deployment, THEN THE SSO_Profile SHALL return an authentication error that contains an indication of session expiry and the `aws sso login` command needed to re-authenticate
7. WHEN the SSO migration is complete, THE SSO_Profile SHALL not affect GitHub Actions CI/CD workflows, which use IAM role assumption independent of the developer's local SSO configuration

### Requirement 2: Google Credential Security — Lambda (WIF)

**User Story:** As a developer, I want the `sync_google_calendar` Lambda to authenticate to Google APIs using Workload Identity Federation, so that no static service account key is stored in SSM Parameter Store.

#### Acceptance Criteria

1. WHEN the `sync_google_calendar` Lambda executes, THE WIF SHALL use the Lambda's AWS IAM execution role to obtain a short-lived Google OAuth 2.0 access token via Workload Identity Federation (AWS → Google token exchange)
2. WHEN WIF is configured, THE WIF SHALL provide the `calendar` scope required by the Calendar sync and the `photoslibrary.appendonly` scope required by the Google Photos museum upload
3. WHEN WIF is operational for the Lambda, THE Static_Credentials stored in SSM parameter `/h-dcn/google-credentials` SHALL be deleted
4. WHEN WIF is operational for the Lambda, THE OAuth refresh token stored in SSM parameter `/h-dcn/google-photos-oauth` SHALL be evaluated for replacement — IF WIF can provide `photoslibrary.appendonly` access, THEN the OAuth parameter SHALL be deleted
5. IF WIF token acquisition fails at runtime, THEN THE Lambda SHALL return an error indicating the authentication failure without falling back to a static key or OAuth token
6. WHEN WIF is configured, THE WIF SHALL require a workload identity pool, a pool provider mapped to the Lambda's AWS account (506221081911), and an attribute condition restricting access to the `sync_google_calendar` execution role ARN

### Requirement 2b: Google Credential Security — Local Dev (Rotation & Cleanup)

**User Story:** As a developer, I want enforced key expiration and a single well-managed service account for all local Google API integrations, so that keys cannot become stale and the current mess of ad-hoc service accounts is consolidated.

#### Acceptance Criteria

1. WHEN the cleanup is complete, THE Google Cloud project SHALL have a single service account dedicated to local developer use, with only the required scopes: `spreadsheets.readonly`, `drive.readonly`, `drive.file`, `calendar`, and `calendar.readonly`
2. WHEN the cleanup is complete, all unused or duplicate service accounts and their keys SHALL be deleted from the Google Cloud project
3. THE Google Cloud project SHALL have the organization policy constraint `constraints/iam.serviceAccountKeyExpiryHours` set to `2160` (90 days), enforcing automatic expiration of all newly created service account keys
4. WHEN a new `.googleCredentials.json` key is generated, THE key SHALL automatically expire after 90 days due to the org policy constraint — no manual tracking required
5. WHEN the key approaches expiration (within 7 days), THE developer SHALL receive a reminder (calendar event or automated notification) to generate a replacement key
6. WHEN a new key is generated during rotation, THE Rotation_Policy SHALL require verifying connectivity for each local integration — gspread (read one row from target sheet), Calendar API (list upcoming events), Drive API (list files), and Drive upload (create a test file in the poster folder) — before deleting the expired key from the Google Cloud console
7. THE cleanup SHALL produce a documented inventory of the single active service account: its email, project, granted roles, and authorized scopes

### Requirement 3: Shell History Secret Prevention

**User Story:** As a developer, I want to prevent secrets from being saved to PowerShell history, so that credential material never persists in readable history files regardless of which project or directory I'm working in.

#### Acceptance Criteria

1. WHEN a command containing a secret pattern is entered in any PowerShell session on the laptop, THE AddToHistoryHandler SHALL prevent that command from being written to the history file by returning `SkipAdding`
2. THE AddToHistoryHandler SHALL detect at minimum the following patterns: AWS access keys (`AKIA...`), private keys (`BEGIN...PRIVATE KEY`), Stripe keys (`sk_live_`, `pk_live_`), Mollie keys (`live_`, `test_` followed by alphanumeric characters), GitHub/GitLab tokens (`ghp_`, `glpat-`), Google API keys (`AIza...`), Slack tokens (`xox[bpors]-`), and Bearer tokens with hardcoded values
3. THE AddToHistoryHandler SHALL be registered in the user's PowerShell `$PROFILE` file, ensuring it applies to all PowerShell sessions system-wide (not per-project)
4. THE AddToHistoryHandler SHALL still allow the command to execute and remain in the in-memory session history (only file persistence is blocked)
5. WHEN the AddToHistoryHandler is installed, a one-time cleanup script SHALL scan the existing history file at `(Get-PSReadLineOption).HistorySavePath` and remove lines matching secret patterns
6. THE one-time cleanup script SHALL create a backup of the original history file before modifying it
7. THE AddToHistoryHandler SHALL add negligible latency to command entry (regex matching on a single line, no file I/O or network calls)
