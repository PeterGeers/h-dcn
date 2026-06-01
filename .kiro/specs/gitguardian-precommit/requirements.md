# Requirements Document

## Introduction

This feature fixes the GitGuardian (ggshield) pre-commit hook deployment for the H-DCN project. The current hook uses a `#!/bin/sh` shebang that invokes WSL/bash on Windows, causing failures on developer machines running Git for Windows. Additionally, the `.gitguardian.yaml` configuration lacks file size exclusions, causing `frontend/package-lock.json` (>1MB) to be scanned unnecessarily, triggering rate limits and timeouts during `ggshield secret scan commit-range`.

## Glossary

- **Pre_Commit_Hook**: The Git hook script located at `.git/hooks/pre-commit` that runs automatically before each commit
- **GGShield**: The GitGuardian CLI tool (`ggshield`) used for secret scanning in commits
- **GitGuardian_Config**: The `.gitguardian.yaml` configuration file at the project root that controls scanning behavior
- **Auth_Layer_Sync**: The process of copying `backend/shared/auth_utils.py` to `backend/layers/auth-layer/python/shared/auth_utils.py` to keep the Lambda Layer in sync
- **Git_For_Windows**: The Windows-native Git distribution that includes `sh.exe` (POSIX shell emulator) but does not use WSL

## Requirements

### Requirement 1: Windows-Compatible Pre-Commit Hook

**User Story:** As a developer on Windows, I want the pre-commit hook to execute correctly using Git for Windows shell, so that secret scanning runs without WSL-related failures.

#### Acceptance Criteria

1. THE Pre_Commit_Hook SHALL use a shebang compatible with Git for Windows sh.exe (`#!/bin/sh`)
2. THE Pre_Commit_Hook SHALL use only POSIX shell commands supported by Git for Windows sh.exe
3. THE Pre_Commit_Hook SHALL avoid bash-specific syntax, Windows-specific commands, and WSL-dependent paths
4. WHEN Git for Windows executes the Pre_Commit_Hook, THE Pre_Commit_Hook SHALL complete without shell interpreter errors

### Requirement 2: Large File Exclusion from Secret Scanning

**User Story:** As a developer, I want large generated files excluded from GitGuardian scanning, so that commits complete without rate limit errors or timeouts.

#### Acceptance Criteria

1. THE GitGuardian_Config SHALL exclude `frontend/package-lock.json` from secret scanning
2. THE GitGuardian_Config SHALL exclude all files larger than 1MB from secret scanning using the `ignored_paths` or equivalent configuration
3. WHEN GGShield performs a pre-commit scan, THE GGShield SHALL skip files matching the exclusion patterns in GitGuardian_Config
4. WHEN GGShield performs a `commit-range` scan, THE GGShield SHALL skip files matching the exclusion patterns in GitGuardian_Config

### Requirement 3: Auth Layer Synchronization in Pre-Commit

**User Story:** As a developer, I want the auth layer file to be automatically synchronized before secret scanning, so that the Lambda Layer always contains the latest auth utilities.

#### Acceptance Criteria

1. WHEN `backend/shared/auth_utils.py` differs from `backend/layers/auth-layer/python/shared/auth_utils.py`, THE Pre_Commit_Hook SHALL copy the main file to the layer location
2. WHEN the Auth_Layer_Sync copies a file, THE Pre_Commit_Hook SHALL stage the updated layer file using `git add`
3. WHEN `backend/shared/auth_utils.py` matches `backend/layers/auth-layer/python/shared/auth_utils.py`, THE Pre_Commit_Hook SHALL skip the sync step without error

### Requirement 4: Secret Scan Execution and Commit Blocking

**User Story:** As a developer, I want the pre-commit hook to block commits containing secrets, so that sensitive data is never pushed to the repository.

#### Acceptance Criteria

1. WHEN GGShield is installed and available on PATH, THE Pre_Commit_Hook SHALL execute `ggshield secret scan pre-commit`
2. WHEN GGShield detects secrets in staged files, THE Pre_Commit_Hook SHALL exit with a non-zero exit code to block the commit
3. WHEN GGShield detects secrets in staged files, THE Pre_Commit_Hook SHALL display a message indicating secrets were found
4. WHEN GGShield scan completes without finding secrets, THE Pre_Commit_Hook SHALL allow the commit to proceed
5. IF GGShield is not installed or not found on PATH, THEN THE Pre_Commit_Hook SHALL print a warning message and allow the commit to proceed

### Requirement 5: GitGuardian Configuration Completeness

**User Story:** As a developer, I want the GitGuardian configuration to include all necessary exclusions, so that scanning is efficient and avoids false positives on generated or test files.

#### Acceptance Criteria

1. THE GitGuardian_Config SHALL exclude lock files (`**/package-lock.json`, `**/yarn.lock`, `**/pnpm-lock.yaml`) from scanning
2. THE GitGuardian_Config SHALL exclude the `.venv` directory from scanning
3. THE GitGuardian_Config SHALL exclude the `node_modules` directory from scanning
4. THE GitGuardian*Config SHALL retain existing exclusions for test files (`test*\*.py`, `**/tests/**`, `**/**tests**/**`)
5. THE GitGuardian_Config SHALL set `ignored_matches` or `ignored_paths` patterns that apply to both `pre-commit` and `commit-range` scan modes
