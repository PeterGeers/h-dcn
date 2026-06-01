# Implementation Plan: GitGuardian Pre-Commit Hook

## Overview

This implementation creates a Windows-compatible pre-commit hook for GitGuardian secret scanning and updates the `.gitguardian.yaml` configuration to exclude large/generated files. The hook also synchronizes the auth layer file before scanning. All shell scripting uses POSIX-compliant syntax for Git for Windows `sh.exe` compatibility.

## Tasks

- [ ] 1. Update GitGuardian configuration
  - [ ] 1.1 Update `.gitguardian.yaml` with complete exclusion patterns
    - Add lock file exclusions: `**/package-lock.json`, `**/yarn.lock`, `**/pnpm-lock.yaml`
    - Add `.venv/**` and `**/.venv/**` directory exclusions
    - Add `**/node_modules/**` directory exclusion
    - Retain existing test file exclusions: `test_*.py`, `test_*.html`, `**/tests/**`, `**/__tests__/**`
    - Retain existing utility script exclusions: `decode_*.py`, `trigger_*.py`
    - Ensure `exit_zero: false` is preserved
    - _Requirements: 2.1, 2.2, 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 2. Create POSIX-compliant pre-commit hook script
  - [ ] 2.1 Create the pre-commit hook script at project root as `pre-commit-hook.sh`
    - Use `#!/bin/sh` shebang (no bash)
    - Use only POSIX shell constructs: `[ ... ]` tests, `$(...)` command substitution, `command -v` for tool detection
    - Avoid bash-isms: no `[[ ]]`, no arrays, no `local` keyword, no `which`
    - Include clear comments explaining each section
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [ ] 2.2 Implement auth layer synchronization logic
    - Compare `backend/shared/auth_utils.py` with `backend/layers/auth-layer/python/shared/auth_utils.py` using `cmp -s`
    - If files differ, copy source to layer location with `cp`
    - Stage the updated layer file with `git add`
    - Skip silently if either file does not exist (check with `[ -f ... ]`)
    - Suppress `cmp` stderr with `2>/dev/null`
    - _Requirements: 3.1, 3.2, 3.3_

  - [ ] 2.3 Implement ggshield secret scan execution and exit code handling
    - Check ggshield availability with `command -v ggshield`
    - If available, run `ggshield secret scan pre-commit`
    - Capture and propagate ggshield exit code
    - If secrets found (non-zero exit), print error message and exit with ggshield's exit code
    - If scan passes, exit 0
    - If ggshield not installed, print warning and exit 0
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ] 3. Checkpoint - Verify POSIX compliance
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Create installation and validation artifacts
  - [ ] 4.1 Create a hook installation script `install-hooks.sh`
    - Copy `pre-commit-hook.sh` to `.git/hooks/pre-commit`
    - Set executable permissions (`chmod +x`)
    - Print confirmation message
    - Use POSIX-compliant shell syntax
    - _Requirements: 1.1, 1.4_

  - [ ]\* 4.2 Write a ShellCheck validation script
    - Create a script or CI step that runs `shellcheck --shell=sh pre-commit-hook.sh`
    - Verify zero errors and zero warnings
    - _Requirements: 1.2, 1.3_

- [ ] 5. Final checkpoint - Ensure all artifacts are complete
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- The pre-commit hook is stored as `pre-commit-hook.sh` in the project root for version control; developers install it to `.git/hooks/pre-commit` via the install script
- Property-based testing does not apply to this feature (shell script + YAML config are not pure functions with meaningful input variation)
- ShellCheck (`shellcheck --shell=sh`) serves as the automated POSIX compliance validator
- The `.gitguardian.yaml` exclusions apply to both local `pre-commit` and CI `commit-range` scan modes without any workflow file changes
- Each task references specific requirements for traceability

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "2.1"] },
    { "id": 1, "tasks": ["2.2"] },
    { "id": 2, "tasks": ["2.3"] },
    { "id": 3, "tasks": ["4.1", "4.2"] }
  ]
}
```
