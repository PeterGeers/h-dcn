# Implementation Plan

- [x] 1. Add line-ending normalization
  - Create root `.gitattributes` with `* text=auto eol=lf`, force LF for `*.sh`, `.githooks/*`, and mark binary assets (`*.png`, `*.jpg`, `*.jpeg`, `*.gif`, `*.pdf`, `*.woff`, `*.woff2`, `*.ttf`, `*.ico`) as `binary`.
  - Commit `.gitattributes` first, then run `git add --renormalize .` as a separate isolated commit.
  - Verify with `git ls-files --eol` that `.githooks/pre-push` and `*.sh` show `lf`, and confirm no binary assets appear in the renormalize diff.
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 2. Port the secret scanner to bash
  - Create `scripts/scan-secrets-local.sh` (`#!/usr/bin/env bash`, `chmod +x`, LF) reproducing `scan-secrets-local.ps1`: 13 patterns as POSIX ERE (`grep -E`/`grep -iE`), staged files via `git diff --cached`, content via `git show ":$file"`, skip binary extensions + comment/`example|placeholder|dummy|fake|mock` lines + env-var references, parse `ignored_paths` from `.gitguardian.yaml`, exit 1 on findings else 0.
  - Parity test: run the `.ps1` (Windows) and `.sh` against the same staged fixtures (a clean file, an AKIA key, a private-key header, an ignored-path file) and confirm identical findings.
  - _Requirements: 2.2, 10.2_

- [x] 3. Rewrite the pre-push git hook in bash (no PowerShell)
  - In `.githooks/pre-push`, replace both `powershell.exe -File .../scan-secrets-local.ps1` invocations with `sh "$REPO_ROOT/scripts/scan-secrets-local.sh"`.
  - Keep `#!/bin/sh`; ensure LF.
  - Test: on a scratch branch, a benign push passes; a staged fake secret blocks the push.
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 4. Rewrite the Kiro pre-commit hook in bash (no PowerShell)
  - Create `scripts/precommit-guard.sh`: read stdin JSON, extract `toolInput.command` via `python3`, exit 0 if it lacks `git commit`; else Auth_Layer_Sync (`cmp -s` + `cp` + `git add` when `backend/shared/auth_utils.py` differs from the layer copy), then `exec sh scripts/scan-secrets-local.sh`.
  - Update `.kiro/hooks/ggshield-pre-commit.json` `command` to `sh scripts/precommit-guard.sh`, preserving `matcher: execute_pwsh` and `timeout`.
  - Test: commit with out-of-sync auth layer → verify it syncs + `git add`s; commit with a fake secret → verify it blocks; non-commit tool call → verify no-op.
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 5. Delete the now-unused PowerShell secret scanner
  - After tasks 2–4 verify green, delete `scripts/scan-secrets-local.ps1`.
  - Grep to confirm nothing else references it.
  - _Requirements: 10.2, 10.6_

- [x] 6. Fix cross-platform npm build script
  - Add `"cross-env": "7.0.3"` to `frontend/package.json` devDependencies.
  - Change `build:prod` to `cross-env GENERATE_SOURCEMAP=false react-scripts build`.
  - Run `npm install` in `frontend/` and confirm `npm run build:prod` starts without the `set` error.
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 7. Rewrite VS Code auth-layer tasks in bash
  - In `.vscode/tasks.json`, change "Check AuthLayer Sync" and "Sync AuthLayer Files" from `powershell` to `bash -c` using `cmp -s`/`cp` with forward-slash paths (`backend/shared/auth_utils.py` → `backend/layers/auth-layer/python/shared/auth_utils.py`).
  - Leave the git-based tasks unchanged.
  - _Requirements: 5.4_

- [x] 8. Remove hardcoded Windows paths from VS Code settings
  - Remove `terminal.integrated.cwd` from `backend/.vscode/settings.json`.
  - Remove `terminal.integrated.cwd` from `frontend/.vscode/settings.json`, keep the copilot setting.
  - Add `"terminal.integrated.defaultProfile.linux": "bash"` to root `.vscode/settings.json`.
  - _Requirements: 5.1, 5.2, 5.3_

- [x] 9. Parameterize the import script path
  - In `backend/scripts/import_members.py`, accept the CSV path as `sys.argv[1]`, keep the existing string as a documented default, and print usage + exit non-zero when the resolved file is absent.
  - Add type hints on the touched function(s) per the type-safety steering.
  - _Requirements: 5.5_

- [x] 10. Delete DEAD PowerShell scripts
  - Delete the 32 DEAD scripts (migration ×5, decommission ×3, `backend/Migratie/cognito_bulk_cli.ps1`, `validate-role-migration.ps1`, empty `pre-deployment-snapshot.ps1`, one-time fixes, image one-offs, retired-endpoint tests, git one-offs, space-named junk, `temp/old-scripts/*`).
  - Commit as its own isolated commit.
  - Grep the repo (exclude `.git`, `node_modules`, `.venv`, `sam-env`) for each deleted filename to confirm no live hook/workflow/npm/script reference remains.
  - _Requirements: 10.1, 10.5, 10.6_

- [x] 11. Retain UNSURE scripts and runbook docs as reference
  - Keep the 5 UNSURE scripts (`cleanup-s3-bucket.ps1`, `test_members_api_endpoint.ps1`, `check-ssl-validation.ps1`, `verify-access.ps1`, `install-gh-cli.ps1`) and the runbook docs (`cutover-dns.md`, `rollback-dns.md`).
  - Optionally add a one-line note in each runbook doc that the referenced migration scripts have been removed (historical record).
  - _Requirements: 10.4_

- [x] 12. Write the WSL/Ubuntu setup documentation
  - Create `docs/development/wsl-ubuntu-setup.md`: toolchain (Python 3.11, Node 18, AWS CLI v2, SAM CLI, Docker, ggshield, git — **no pwsh**); clone to `/home/peter/projects/h-dcn` on the WSL native filesystem (not `/mnt/c`); `git config core.hooksPath .githooks`.
  - Recreate-don't-copy Machine_Local_Artifacts: backend `.venv` (Linux `bin/`), never reuse `backend/sam-env/` or Windows `.venv/`, `samconfig.toml`, `frontend/.env` + `.env.local`, credential files by key name only.
  - Deploy path: push to `main` triggers CI; list equivalent manual commands. Note MANUAL-KEEP `.ps1` are Windows-only, unsupported on Linux.
  - Reference `aws-dynamodb` steering for `--profile nonprofit-deploy`. Include the Requirement 8 verification checklist.
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 10.3_

- [x] 13. Record an ADR for the migration decision
  - Create `docs/decisions/wsl-ubuntu-migration.md`: the "no PowerShell on Linux — bash hooks + CI deploys" decision, the 55-script inventory outcome (1 LIVE / 22 keep / 32 deleted), and the flagged discrepancies.
  - _Requirements: 3.1, 3.3, 3.5_

- [ ] 14. Commit and push the changes on a feature branch
  - Stage specific files per change (not `git add .`), conventional commit messages (`chore:`, `fix:`, `docs:`); keep cleanup and `.gitattributes` renormalization as their own commits.
  - Let the (now bash) pre-commit hook run; do not use `--no-verify`. Never push to `main`.
  - Push the feature branch to `origin` so the fresh Ubuntu clone will contain the bash hooks and `.gitattributes`.
  - _Requirements: 9.1, 9.2, 9.3, 9.4_

- [ ] 15. Clone and bootstrap the Ubuntu environment (documented manual steps)
  - `git clone https://github.com/PeterGeers/h-dcn.git /home/peter/projects/h-dcn` on the WSL native filesystem (not `/mnt/c`); `git checkout <migration-feature-branch>`.
  - `git config core.hooksPath .githooks`; `chmod +x .githooks/pre-push scripts/scan-secrets-local.sh scripts/precommit-guard.sh`.
  - Create the Python 3.11 venv (`python3.11 -m venv backend/.venv`, activate `bin/activate`); `pip install -r backend/requirements.txt -r backend/tests/requirements.txt`; `npm install` in `frontend/`.
  - Recreate `backend/samconfig.toml`, `frontend/.env`, `frontend/.env.local`, and credential files (`.awsCredentials.json`, `.googleCredentials.json`, `.secrets`) natively — by key name, never copied from Windows.
  - Confirm `backend/sam-env/` and any Windows `.venv/` are absent.
  - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7_

- [ ] 16. Verify the migrated environment on Ubuntu
  - Backend: run targeted `pytest tests/unit/test_<name>.py` in the Linux venv; confirm pass.
  - Frontend: `npx tsc --noEmit`; one targeted `react-scripts test --watchAll=false --testPathPattern="<file>"`.
  - Deploy validation only: `sam validate` + `python scripts/validate_all.py` (no pwsh, no prod deploy).
  - Hooks: pre-commit runs Auth_Layer_Sync + bash scanner (incl. blocked-secret negative test); pre-push runs the bash scanner on a test branch.
  - Confirm Machine_Local_Artifacts are not committed and remain gitignored; document any Docker-dependent `sam build --use-container` limitation.
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 9.1, 9.2, 9.4_
