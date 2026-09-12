# Requirements Document

## Introduction

This document defines the requirements for migrating the h-dcn development environment from Windows (with PowerShell/pwsh tooling) to a WSL/Ubuntu (Linux) environment reachable at `\\wsl.localhost\Ubuntu`. The goal is a fully functional Linux dev environment where a developer can clone the repo, install toolchains, build and test both backend (Python 3.11 + AWS SAM) and frontend (Node + react-scripts), run the git hooks and Kiro hooks, and deploy — without relying on Windows-only constructs.

The migration is **development-environment only**. It does not touch AWS infrastructure, DynamoDB data, Cognito, or production buckets. All AWS account, region, and credential rules from the existing steering (`aws-dynamodb`, `guardrails`, `authentication`) remain authoritative and unchanged.

The Linux working copy is created by **cloning fresh from GitHub** (`https://github.com/PeterGeers/h-dcn.git`) into `/home/peter/projects/h-dcn`, not by copying the Windows working tree. The cross-platform code changes (bash hooks, `.gitattributes`, cross-env, path fixes, script cleanup) are made and committed from the current repo on a feature branch first, so the fresh Linux clone already contains them. The developer then recreates the machine-local artifacts (venv, `samconfig.toml`, `.env` files, credentials) natively on Linux.

## Scope

### In scope
- Making automation cross-platform: git hooks, Kiro hooks, VS Code tasks, deployment scripts, npm scripts.
- Removing hardcoded Windows paths from committed config.
- Line-ending normalization so shell scripts run on Linux.
- Documenting the Linux toolchain setup (Python 3.11, Node, pwsh, AWS SAM, Docker, ggshield).
- Recreating (not copying) machine-local artifacts: virtual environments, `samconfig.toml`, `.env` files, credential files.

### Out of scope
- Any AWS infrastructure change (Lambda, API Gateway, DynamoDB, Cognito, S3, CloudFront).
- Migrating or copying DynamoDB data.
- Changing the CI/CD workflows' runtime behavior (they already run on Linux runners).
- Rewriting deployment bucket/distribution values (flag discrepancies only; do not change without confirmation).

## Glossary

- **WSL**: Windows Subsystem for Linux — the Ubuntu Linux environment at `\\wsl.localhost\Ubuntu`.
- **Auth_Layer_Sync**: The requirement that `backend/shared/auth_utils.py` and `backend/layers/auth-layer/python/shared/auth_utils.py` remain byte-identical.
- **Local_Secret_Scanner**: The regex secret scanner used as the ggshield fallback and by the Kiro pre-commit hook. Currently `scripts/scan-secrets-local.ps1` (PowerShell); to be ported to a bash equivalent (`scripts/scan-secrets-local.sh`) so the commit/push path has no PowerShell dependency.
- **pwsh**: PowerShell Core, the cross-platform PowerShell that runs on Linux. Only relevant to the rarely-run deploy/utility `.ps1` scripts that are kept as-is, not to the commit/push path.
- **Machine_Local_Artifact**: A file or directory that is gitignored and must be recreated per-machine (venv, `samconfig.toml`, `.env`, credential files).
- **Cross_Platform**: Runs correctly on both Windows and Linux without modification, OR the Windows path is preserved alongside a Linux equivalent.

## Requirements

### Requirement 1: Cross-platform git hooks

**User Story:** As a developer on Ubuntu, I want the pre-push git hook to run the secret scan without invoking `powershell.exe`, so that pushes are not blocked by a missing Windows executable.

#### Acceptance Criteria

1. WHEN the pre-push hook runs on Linux AND ggshield quota is exhausted, THE hook SHALL invoke the bash Local_Secret_Scanner (no PowerShell).
2. WHEN the pre-push hook runs on Linux AND ggshield is not installed, THE hook SHALL invoke the bash Local_Secret_Scanner (no PowerShell).
3. THE pre-push hook SHALL not require PowerShell (`pwsh` or `powershell.exe`) on any platform for its secret-scan fallback.
4. THE pre-push hook file SHALL have LF line endings and a POSIX-compatible shebang.
5. WHEN the repository is cloned on Ubuntu, THE setup documentation SHALL instruct the developer to set `core.hooksPath` to `.githooks`.

### Requirement 2: Cross-platform Kiro pre-commit hook

**User Story:** As a developer on Ubuntu, I want the Kiro pre-commit hook (auth-layer sync + secret scan) to run on Linux, so that commits are protected the same way they are on Windows.

#### Acceptance Criteria

1. THE Kiro pre-commit hook SHALL perform Auth_Layer_Sync (copy `backend/shared/auth_utils.py` to the layer path and `git add` it when they differ) on Linux using bash/coreutils (no PowerShell).
2. THE Kiro pre-commit hook SHALL run the bash Local_Secret_Scanner on Linux and block the commit (non-zero exit) when secrets are found.
3. THE Kiro pre-commit hook SHALL invoke a bash script, not `powershell`/`pwsh`.
4. WHEN the intercepted command does not contain `git commit`, THE hook SHALL exit 0 without side effects.
5. THE hook `matcher` (`execute_pwsh`) and `timeout` SHALL be preserved; only the invoked command changes.

### Requirement 3: Deploy path on Linux uses CI, not PowerShell

**User Story:** As a developer on Ubuntu, I want deployment to work without any PowerShell, so that I never need pwsh on Linux.

#### Acceptance Criteria

1. THE canonical deploy path SHALL be the GitHub Actions workflows (`deploy-backend.yml`, `deploy-frontend.yml`) triggered by push to `main`, which run on `ubuntu-latest` and use no `.ps1` scripts.
2. THE setup documentation SHALL record the equivalent manual Linux commands (`sam build`/`sam deploy`; `npm run build` with `GENERATE_SOURCEMAP=false` + `aws s3 sync` + CloudFront invalidation) for local use, mirroring what CI does.
3. THE migration SHALL NOT require `pwsh` to be installed on Linux for any purpose; PowerShell SHALL be absent from every automatic path (commit, push, CI deploy).
4. THE retained MANUAL-KEEP `.ps1` scripts SHALL remain Windows-only convenience tools; the documentation SHALL state they are not supported on Linux and SHALL point to the equivalent CI/manual commands instead.
5. THE migration SHALL NOT change hardcoded S3 bucket names or CloudFront distribution IDs; any discrepancy with `guardrails` steering SHALL be flagged to the user for a separate decision.

### Requirement 4: Cross-platform npm scripts

**User Story:** As a developer on Ubuntu, I want `npm run build:prod` to work, so that production builds succeed on Linux.

#### Acceptance Criteria

1. THE `build:prod` script SHALL set `GENERATE_SOURCEMAP=false` in a way that works on both Linux and Windows.
2. THE solution SHALL NOT rely on CMD-only `set VAR=value` syntax.
3. WHEN a cross-platform env-var mechanism requires a dependency (e.g. `cross-env`), THE dependency SHALL be added to `frontend/package.json` devDependencies with a pinned version.
4. ALL other npm scripts SHALL continue to run unchanged on Linux.

### Requirement 5: Remove hardcoded Windows paths from committed config

**User Story:** As a developer on Ubuntu, I want no `C:\Users\...` paths in committed config, so that editor and tooling behavior is correct on Linux.

#### Acceptance Criteria

1. THE `backend/.vscode/settings.json` SHALL NOT contain a hardcoded Windows `terminal.integrated.cwd` path.
2. THE `frontend/.vscode/settings.json` SHALL NOT contain a hardcoded Windows `terminal.integrated.cwd` path.
3. THE root `.vscode/settings.json` SHALL provide a Linux terminal profile default alongside (or instead of) the Windows-only `terminal.integrated.defaultProfile.windows`.
4. THE `.vscode/tasks.json` auth-layer tasks SHALL use commands and paths that resolve on Linux.
5. THE `backend/scripts/import_members.py` hardcoded Windows CSV path SHALL be parameterized: the script SHALL accept the CSV path as a command-line argument, retain a documented default, and print usage when the file is absent.

### Requirement 6: Line-ending normalization

**User Story:** As a developer, I want a `.gitattributes` policy, so that shell scripts and hooks are not broken by CRLF when checked out on Linux.

#### Acceptance Criteria

1. THE repository SHALL contain a root `.gitattributes` that normalizes text files to LF on checkout (`* text=auto eol=lf` or equivalent).
2. THE `.gitattributes` SHALL force LF for shell scripts (`*.sh`) and the `.githooks/*` files.
3. WHEN the repo is re-normalized, THE change SHALL NOT corrupt binary files (images, PDFs, fonts SHALL be marked binary or excluded).
4. THE normalization SHALL be applied and committed so a fresh Ubuntu checkout gets LF line endings.

### Requirement 7: Toolchain setup documentation

**User Story:** As a developer setting up Ubuntu, I want a step-by-step setup guide, so that I can reach a working build/test/deploy state.

#### Acceptance Criteria

1. THE documentation SHALL list required Linux packages and versions: Python 3.11, Node 18 (matching CI), AWS CLI v2, AWS SAM CLI, Docker (for `sam build --use-container`), ggshield, git. Bash and coreutils are assumed present. THE documentation SHALL NOT list pwsh as a dependency (it is not required on Linux).
2. THE documentation SHALL specify the preferred clone location `/home/peter/projects/h-dcn` on the WSL native filesystem (not `/mnt/c`), and SHALL describe recreating Machine_Local_Artifacts on Linux: backend virtualenv (using `bin/` not `Scripts/`), `samconfig.toml`, `frontend/.env` and `.env.local`, and credential files (`.awsCredentials.json`, `.googleCredentials.json`, `.secrets`) — recreated, never copied from the Windows tree.
3. THE documentation SHALL state that `backend/sam-env/` and any `.venv/` from Windows MUST NOT be reused, and MUST be recreated natively.
4. THE documentation SHALL describe configuring `core.hooksPath=.githooks` and installing the pre-push hook.
5. THE documentation SHALL reference the existing AWS profile rules (`--profile nonprofit-deploy`) from steering without duplicating or contradicting them.
6. THE documentation SHALL include a verification checklist: backend tests run, frontend `tsc --noEmit` passes, a targeted frontend test runs, `sam build` succeeds, and both hooks fire correctly.

### Requirement 8: Verified working state on Ubuntu

**User Story:** As a developer, I want confirmation that core workflows work on Ubuntu, so that I can trust the migrated environment.

#### Acceptance Criteria

1. WHEN backend unit tests are run per the testing-backend steering conventions on Ubuntu, THE relevant test files SHALL pass.
2. WHEN `npx tsc --noEmit` is run in `frontend/` on Ubuntu, THE type check SHALL pass (or fail only with pre-existing, documented issues).
3. WHEN a targeted frontend test is run per the testing-frontend steering conventions on Ubuntu, THE test SHALL pass.
4. WHEN a git commit is attempted on Ubuntu, THE Kiro pre-commit hook SHALL run Auth_Layer_Sync and the secret scan.
5. WHEN a git push is attempted on Ubuntu, THE pre-push hook SHALL run the secret scan.
6. IF `sam build` requires Docker AND Docker is unavailable, THEN the limitation SHALL be documented rather than silently skipped.

### Requirement 9: No secret or data leakage during migration

**User Story:** As a security-conscious developer, I want the migration to avoid exposing secrets, so that credentials are not committed or leaked.

#### Acceptance Criteria

1. THE migration SHALL NOT commit `.awsCredentials.json`, `.googleCredentials.json`, `.secrets`, `.env`, `.env.local`, or `samconfig.toml`.
2. THE migration SHALL verify these files remain gitignored after any `.gitignore` edits.
3. WHEN documenting credential recreation, THE documentation SHALL reference secrets by key name, never by value.
4. THE migration SHALL NOT bypass the secret-scanning hooks (`--no-verify`) except where an existing script already does so for its documented purpose.

### Requirement 10: Dead PowerShell script cleanup

**User Story:** As a developer moving to Linux, I want obsolete PowerShell scripts removed, so that the repo is not cluttered with Windows-only, one-time scripts that will never run on the new environment.

#### Acceptance Criteria

1. THE migration SHALL delete the 32 scripts classified as DEAD/OBSOLETE (completed account-migration and decommission tooling, one-time fix scripts, ad-hoc tests against retired endpoints, empty files, and `temp/old-scripts/` junk).
2. THE migration SHALL preserve the single LIVE script's behavior by porting `scripts/scan-secrets-local.ps1` to bash (`scripts/scan-secrets-local.sh`) before or alongside removing PowerShell from the commit/push path; the `.ps1` original MAY then be deleted.
3. THE migration SHALL retain the MANUAL-KEEP `.ps1` scripts (Windows-only convenience) and document them as not supported on Linux.
4. THE migration SHALL retain the 5 UNSURE scripts (`scripts/maintenance/cleanup-s3-bucket.ps1`, `scripts/testing/test_members_api_endpoint.ps1`, `scripts/utilities/check-ssl-validation.ps1`, `infrastructure/verify-access.ps1`, `git/install-gh-cli.ps1`) as reference and the migration runbook docs (`scripts/migration/cutover-dns.md`, `rollback-dns.md`) as historical record; these SHALL NOT be deleted.
5. THE cleanup SHALL be committed separately from functional changes so it is independently reviewable and revertible.
6. AFTER deletion, THE migration SHALL verify no remaining live code, hook, workflow, or npm script references a deleted script (per the dead-code rules in `specs` steering).

### Requirement 11: Clone-based environment bootstrap on Ubuntu

**User Story:** As a developer, I want the Linux working copy created by cloning from GitHub (not copied from Windows), so that I start from a clean, LF-normalized tree without Windows-specific artifacts.

#### Acceptance Criteria

1. THE Linux working copy SHALL be created with `git clone https://github.com/PeterGeers/h-dcn.git` into `/home/peter/projects/h-dcn`, NOT by copying the Windows working tree.
2. THE migration SHALL NOT copy `backend/sam-env/`, any `.venv/`, `.aws-sam/`, `node_modules/`, or `__pycache__/` from Windows; these SHALL be regenerated natively on Linux.
3. AFTER cloning, THE developer SHALL set `git config core.hooksPath .githooks` and make the hook and `scripts/*.sh` files executable.
4. THE bootstrap SHALL create the backend virtualenv with Python 3.11 and install `backend/requirements.txt` and `backend/tests/requirements.txt`; and run `npm install` in `frontend/`.
5. THE bootstrap SHALL recreate the Machine_Local_Artifacts (`samconfig.toml`, `frontend/.env`, `frontend/.env.local`, `.awsCredentials.json`, `.googleCredentials.json`, `.secrets`) natively, referencing secrets by key name only.
6. WHEN the migration code changes are not yet on `main`, THE developer SHALL check out the migration feature branch after cloning so the clone contains the bash hooks and `.gitattributes`.
7. THE bootstrap SHALL be a documented manual procedure in the setup guide (no automated bootstrap script is required).
