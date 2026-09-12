# Design Document

## Overview

The h-dcn codebase is portable at the application level (Python 3.11, boto3, React/TypeScript). The migration friction is entirely in the **automation and environment layer**: PowerShell-coupled hooks, Windows path literals, CMD-only npm syntax, missing line-ending policy, and machine-local artifacts baked for Windows.

This design chooses a **"bash for the commit/push path, leave deploy scripts alone"** strategy:

- The commit/push path (Kiro pre-commit hook + git pre-push hook + the secret scanner they call) runs on **every** commit and push, so it must have **zero PowerShell dependency**. We port the secret scanner from `scripts/scan-secrets-local.ps1` to a bash script `scripts/scan-secrets-local.sh`, and rewrite both hooks to call it via bash/coreutils. No `pwsh`, no `powershell.exe`.
- The `.ps1` deploy/utility scripts are run **rarely and deliberately**, and CI already deploys on Linux runners using plain `sam`/`npm`/`aws` commands. Rewriting hundreds of lines of guardrail-sensitive PowerShell to bash is high-risk and unnecessary, so those scripts are **left unchanged**. The primary documented local deploy path becomes the same plain commands CI uses; `pwsh` is only needed if a developer chooses to run the convenience `.ps1` scripts.
- For the small, high-churn breakages (npm `set VAR=`, VS Code tasks, hardcoded paths) we make minimal, surgical edits.
- Line endings get a proper `.gitattributes` so a fresh checkout is Linux-safe.
- A single setup doc captures the toolchain and the recreate-don't-copy artifact list.

### Decision rationale: no PowerShell on Linux

The user has explicitly chosen **zero PowerShell on Linux**. Investigation of the real CI/CD confirms this is clean to achieve:

- All three GitHub Actions workflows run on `ubuntu-latest` and invoke **no `.ps1` script**. `deploy-backend.yml` runs `sam build`/`sam deploy`; `deploy-frontend.yml` runs `npm run build` with `GENERATE_SOURCEMAP: 'false'` set as a workflow env var, then `aws s3 sync`/CloudFront invalidation. Deploys are triggered by push to `main`.
- The CI ggshield scan was removed (2026-06-23) to save API quota; the **only** secret gate now is the local hooks. That makes porting the scanner correctly essential.
- A full inventory found **55 `.ps1` scripts**: exactly **1 is LIVE** (`scripts/scan-secrets-local.ps1`, called by both hooks), **22 are MANUAL-KEEP** (Windows-only convenience), and **32 are DEAD** (completed account-migration/decommission tooling, one-time fixes, ad-hoc tests against retired endpoints, empty files, `temp/old-scripts/` junk).

| Concern | Approach | Rationale |
|---|---|---|
| Commit/push path (pre-commit hook, pre-push hook, secret scanner) | **Rewrite in bash** | Runs on every commit/push; the only secret gate; must not depend on PowerShell. |
| Local deploy | **Use CI + documented plain commands** | CI already deploys from Linux with no `.ps1`. No pwsh needed. |
| 22 MANUAL-KEEP `.ps1` | **Keep, mark Windows-only** | Rarely used convenience; not worth porting; harmless if left. |
| 32 DEAD `.ps1` | **Delete** | Obsolete/one-time; clutter; will never run on Linux. |
| Installing pwsh on Linux | **Rejected** | User requirement: no PowerShell on Linux. |

An ADR will be recorded in `docs/decisions/` per the specs steering.

### Secret scanner parity note

The bash scanner must preserve the behavior of the PowerShell original: the 13 regex patterns (AWS keys, private keys, Stripe, GitHub/GitLab, Google, Slack, generic assignments, connection strings, bearer tokens, JWT), reading staged content via `git show ":$file"`, skipping binary extensions and comment/`example|placeholder|dummy|fake|mock` lines and env-var references (`${`, `$(`, `process.env`, `os.environ`, `getenv`), honoring `ignored_paths` from `.gitguardian.yaml`, and exit code 1 on findings / 0 when clean. Regex is translated to POSIX ERE / `grep -E` semantics; case-insensitive matches use `grep -iE`.

## Architecture

```
Ubuntu (WSL) dev environment
├── Toolchain (installed, documented)
│   ├── Python 3.11 + venv (backend/.venv, bin/)
│   ├── Node + npm (frontend)
│   ├── AWS CLI v2 + SAM CLI + Docker
│   └── ggshield + git + bash/coreutils   (NO PowerShell anywhere)
│
├── Automation layer
│   ├── scripts/scan-secrets-local.sh  (NEW — bash port; replaces the .ps1)
│   ├── scripts/precommit-guard.sh     (NEW — bash auth-layer sync + scanner)
│   ├── .githooks/pre-push        → powershell.exe ⇒ bash scan-secrets-local.sh
│   ├── .kiro/hooks/ggshield-pre-commit.json → powershell ⇒ bash precommit-guard.sh
│   ├── .vscode/tasks.json        → powershell + copy\ ⇒ bash cp + forward slashes
│   ├── frontend/package.json     → set VAR= ⇒ cross-env
│   ├── DEAD .ps1 (×32)           → deleted
│   └── MANUAL-KEEP .ps1 (×22)    → kept, documented Windows-only
│
├── Config layer (de-Windowsed)
│   ├── backend/.vscode/settings.json  → drop hardcoded C:\ cwd
│   ├── frontend/.vscode/settings.json → drop hardcoded C:\ cwd
│   ├── .vscode/settings.json          → add linux terminal profile
│   └── .gitattributes (NEW)           → LF normalization
│
└── Machine-local (recreated, never copied)
    ├── backend/.venv (Linux bin/)
    ├── backend/sam-env  (do NOT reuse Windows copy)
    ├── samconfig.toml
    ├── frontend/.env, .env.local
    └── .awsCredentials.json, .googleCredentials.json, .secrets
```

## Components and Changes

### 0. Bash secret scanner (`scripts/scan-secrets-local.sh`, NEW)

Port of `scripts/scan-secrets-local.ps1`. Preserves behavior exactly (see Secret scanner parity note above):
- 13 regex patterns translated to POSIX ERE for `grep -E` (case-insensitive → `grep -iE`).
- Staged files via `git diff --cached --name-only --diff-filter=ACM`; content via `git show ":$file"`.
- Skip binary extensions, comment lines, `example|placeholder|dummy|fake|mock` lines, and env-var references (`${`, `$(`, `process.env`, `os.environ`, `getenv`).
- Parse `ignored_paths` from `.gitguardian.yaml` (simple line-based parse mirroring the original), glob→regex.
- Exit 1 on findings (with file:line and pattern name), exit 0 when clean.
- Shebang `#!/usr/bin/env bash`, LF endings, `chmod +x`.

Once this exists and both hooks call it, `scripts/scan-secrets-local.ps1` is deleted (it was the only LIVE `.ps1`).

### 1. Pre-push git hook (`.githooks/pre-push`)

Current: shebang `#!/bin/sh` (already POSIX). On quota exhaustion / missing ggshield it calls `powershell.exe -File .../scan-secrets-local.ps1`.

Change: replace both `powershell.exe` invocations with a direct call to the bash scanner:
```sh
sh "$REPO_ROOT/scripts/scan-secrets-local.sh"
```
No interpreter resolver, no PowerShell. File keeps `#!/bin/sh`, saved LF (enforced by `.gitattributes`).

### 2. Kiro pre-commit hook (`.kiro/hooks/ggshield-pre-commit.json`)

Current `command` invokes bare `powershell -NoProfile -Command "..."` that: parses stdin JSON → checks the command contains `git commit` → Auth_Layer_Sync via `Get-FileHash`/`Copy-Item` + `git add` → runs `./scripts/scan-secrets-local.ps1`.

Change: extract the logic into a bash guard script `scripts/precommit-guard.sh` and point the hook at it. The hook still matches `execute_pwsh` (the Kiro tool name is unchanged regardless of underlying shell) and keeps its `timeout`.

`scripts/precommit-guard.sh` (bash):
```bash
#!/usr/bin/env bash
set -euo pipefail
input=$(cat)                                   # stdin JSON from Kiro
cmd=$(printf '%s' "$input" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("toolInput",{}).get("command",""))')
case "$cmd" in
  *"git commit"*) : ;;                         # proceed
  *) exit 0 ;;                                 # not a commit → no-op
esac
src="backend/shared/auth_utils.py"
dst="backend/layers/auth-layer/python/shared/auth_utils.py"
if [ -f "$src" ] && [ -f "$dst" ] && ! cmp -s "$src" "$dst"; then
  cp "$src" "$dst"; git add "$dst"; echo "Auth layer synced"
fi
exec sh scripts/scan-secrets-local.sh          # propagate scanner exit code
```
Hook `command` becomes: `sh scripts/precommit-guard.sh`. JSON parsing uses `python3` (already a required dependency) rather than a fragile pure-bash JSON parse; `cmp -s` replaces `Get-FileHash` for the byte-identical check.

### 3. VS Code tasks (`.vscode/tasks.json`)

"Check AuthLayer Sync" and "Sync AuthLayer Files" use `"command": "powershell"` with `copy backend\shared\...`.

Change: rewrite as bash tasks. Set `"command": "bash"` with `-c` args using `cmp -s`/`cp` and forward-slash paths, e.g. Sync becomes `cp backend/shared/auth_utils.py backend/layers/auth-layer/python/shared/auth_utils.py`. The git-based tasks ("Git Status...", "Show Recent Changes...") are already portable and unchanged.

### 4. npm `build:prod` (`frontend/package.json`)

Current: `"build:prod": "set GENERATE_SOURCEMAP=false && react-scripts build"`.

Change: use `cross-env` (added to devDependencies, pinned) so it works on both platforms:
```json
"build:prod": "cross-env GENERATE_SOURCEMAP=false react-scripts build"
```
`cross-env` is the standard CRA-ecosystem solution and avoids shell-specific env syntax. Add `"cross-env": "7.0.3"` to devDependencies.

### 5. VS Code settings de-Windowsing

- `backend/.vscode/settings.json`: remove the `terminal.integrated.cwd` Windows path. VS Code defaults cwd to the workspace folder, which is correct.
- `frontend/.vscode/settings.json`: remove the `terminal.integrated.cwd` Windows path; keep the copilot setting.
- Root `.vscode/settings.json`: keep `terminal.integrated.defaultProfile.windows` (harmless on Linux) and add `"terminal.integrated.defaultProfile.linux": "bash"` so Linux gets a sensible default.

### 6. `.gitattributes` (new)

```
* text=auto eol=lf
*.sh text eol=lf
.githooks/* text eol=lf
*.ps1 text eol=lf

# Binary — never normalize
*.png binary
*.jpg binary
*.jpeg binary
*.gif binary
*.pdf binary
*.woff binary
*.woff2 binary
*.ttf binary
*.ico binary
```
After adding, run `git add --renormalize .` in a dedicated commit so tracked text files are stored LF. Binary markers protect assets.

### 7. Hardcoded path in `import_members.py`

`backend/scripts/import_members.py` hardcodes a Windows Downloads CSV path. Change (user-approved): accept the CSV path as `sys.argv[1]`, keep the existing string as a documented default, and print a usage message and exit non-zero when the resolved file does not exist. Add type hints on the touched function(s) per the type-safety steering. This makes the script runnable on Linux by passing a path (e.g. `python backend/scripts/import_members.py ~/data/ledenbestand.csv`).

### 8. Setup documentation

New `docs/development/wsl-ubuntu-setup.md` covering:
- Package install commands (apt / official installers) for Python 3.11, Node 18, AWS CLI v2, SAM CLI, Docker, ggshield. **No pwsh.**
- Clone location: **`/home/peter/projects/h-dcn`** on the WSL native filesystem — **not** `/mnt/c/…` — for performance and correct file permissions.
- `git config core.hooksPath .githooks`.
- Recreate-don't-copy list for Machine_Local_Artifacts, with a note that credential files are referenced by key name and recreated from a password manager / AWS, never carried from Windows.
- Reference to `aws-dynamodb` steering for profiles (`nonprofit-deploy`).
- Deploy: push to `main` triggers CI; documented equivalent manual commands for local use (no `.ps1`).
- A note that the retained `scripts/**/*.ps1` are Windows-only convenience tools, not supported on Linux.
- Verification checklist mapping to Requirement 8.

### 9. Dead PowerShell script cleanup

Delete the 32 DEAD scripts identified in the inventory. Grouped:
- `scripts/migration/*.ps1` (5) — completed account migration.
- `scripts/decommission/*.ps1` (3) — completed personal-account decommission.
- `backend/Migratie/cognito_bulk_cli.ps1` — targets legacy Cognito pool.
- `scripts/deployment/validate-role-migration.ps1`, `scripts/deployment/pre-deployment-snapshot.ps1` (empty).
- One-time fixes: `backend/cleanup-requirements.ps1`, `backend/fix-runtime-properties.ps1`, `frontend/fix-build.ps1`, `scripts/cleanup_powershell_history.ps1`.
- Image one-offs: `scripts/utilities/create-placeholder-images.ps1`, `create-simple-placeholders.ps1`, `restore-images-from-local.ps1`, `check-s3-recovery-options.ps1`, `setup-test-environment.ps1`.
- Ad-hoc tests against retired endpoints: `scripts/testing/{test-current-frontend,test-nonprofit-deployment,test-validation,test-api,test-s3-api,test-s3-list}.ps1`.
- Git/setup one-offs: `git/setup-git.ps1`, `git/README.ps1`.
- Space-named junk: `backend/scripts/Detect the Python runtime bundled with SAM CLI.ps1`, `backend/tests/integration/Integral API test with html report.ps1`.
- `temp/old-scripts/{fixed-powershell-profile,simple-profile}.ps1`.

Kept (MANUAL-KEEP, documented Windows-only): the deployment convenience scripts, `run-tests.ps1`, `load-secrets.ps1`, `setup-ssm-parameters.ps1`, security/ops/dev-convenience utilities (22 total).

**Kept as reference (user decision):** the 5 UNSURE scripts — `scripts/maintenance/cleanup-s3-bucket.ps1`, `scripts/testing/test_members_api_endpoint.ps1`, `scripts/utilities/check-ssl-validation.ps1`, `infrastructure/verify-access.ps1`, `git/install-gh-cli.ps1` — are retained for reference despite stale references. The migration runbook docs `scripts/migration/cutover-dns.md` and `rollback-dns.md` are kept as historical record even though the scripts they reference are deleted; a short note may be added that the referenced scripts have been removed.

Cleanup is its own commit; afterward, grep confirms no live hook/workflow/npm/script references a deleted file.

### 10. Clone-based Ubuntu bootstrap (documented manual procedure)

The Linux environment is created by cloning from GitHub, never by copying the Windows tree. This guarantees a clean, LF-normalized checkout free of Windows artifacts (`sam-env/` with `Scripts/`+`Lib/`, Windows `.venv/`, `.aws-sam/`, `node_modules/`, `__pycache__/`).

Sequencing (important): the code changes (tasks 1–10) are committed on a **feature branch** from the current repo and pushed **first**. Only then is the clone done on Ubuntu, so the fresh checkout already contains the bash hooks and `.gitattributes`. Per `specs`/`git_safety` steering, work is never pushed directly to `main`.

Documented manual steps (into the setup guide; no bootstrap script per user decision):
```bash
# 1. Clone into the native filesystem
git clone https://github.com/PeterGeers/h-dcn.git /home/peter/projects/h-dcn
cd /home/peter/projects/h-dcn
git checkout <migration-feature-branch>      # until merged to main

# 2. Hooks
git config core.hooksPath .githooks
chmod +x .githooks/pre-push scripts/scan-secrets-local.sh scripts/precommit-guard.sh

# 3. Backend venv (Python 3.11, Linux bin/)
python3.11 -m venv backend/.venv
source backend/.venv/bin/activate
pip install -r backend/requirements.txt -r backend/tests/requirements.txt

# 4. Frontend
( cd frontend && npm install )

# 5. Recreate machine-local artifacts (never copied from Windows):
#    backend/samconfig.toml, frontend/.env, frontend/.env.local,
#    .awsCredentials.json, .googleCredentials.json, .secrets
#    (populate from password manager / AWS — by key name)
```
`git`, `python3.11`, `node`/`npm`, AWS CLI v2, SAM CLI, Docker, and ggshield are installed per the toolchain section before this procedure.

## Data Models

No data models change. No DynamoDB, Cognito, or S3 changes. The Field Registry, auth layer contract, and API surface are untouched.

## Error Handling

- **Secret scanner**: exits 1 on any finding (fail-closed); the hooks propagate that exit code to block the commit/push. If `git`/`python3` are missing the guard fails loudly rather than passing silently.
- **`.gitattributes` renormalization**: performed as an isolated commit so any unexpected diff is reviewable and revertible before it mixes with functional changes.
- **Docker absent for `sam build --use-container`**: documented as a known limitation; plain `sam build` remains available (CI uses plain `sam build`).
- **CRLF residue**: the renormalization step plus binary markers guard against corrupting assets; verify with `git diff --stat` showing only expected files.
- **Script deletion**: performed in an isolated commit; a post-delete grep verifies no live reference remains, so an accidental over-delete is caught before merge and revertible.

## Testing Strategy

Per project steering (`testing-backend`, `testing-frontend`, `specs` Definition of Done):

1. **Backend**: run targeted unit test files with `pytest tests/unit/test_<name>.py` from `backend/` on Ubuntu (never the full suite in automation). Confirm moto-based tests pass with the Linux venv.
2. **Frontend type check**: `npx tsc --noEmit` in `frontend/`.
3. **Frontend targeted test**: `npx react-scripts test --watchAll=false --testPathPattern="<file>"` for one representative suite (never the full suite).
4. **Lint**: `npx eslint` on any modified `.ts/.tsx` (none expected here beyond package.json).
5. **Hook behavior** (bash, no PowerShell):
   - Stage a benign file and attempt a commit → verify Auth_Layer_Sync runs and the bash scanner passes.
   - Stage a file containing a fake AKIA-style key → verify the pre-commit guard blocks the commit → remove.
   - Attempt a push on a test branch → verify the pre-push hook runs the bash scanner.
   - Scanner parity: run both `scan-secrets-local.ps1` (on Windows) and `scan-secrets-local.sh` against the same staged fixtures and confirm identical findings before deleting the `.ps1`.
6. **Deploy validation only**: run `sam validate` and `python scripts/validate_all.py` directly (no pwsh). Do NOT run an actual production deploy as part of migration verification.
7. **Line endings**: after `.gitattributes`, verify `git ls-files --eol` shows `lf` for `*.sh` and `.githooks/*`.
8. **Cleanup safety**: after deleting DEAD scripts, `grep` the repo (excluding `.git`, `node_modules`, `.venv`) for each deleted filename to confirm no live reference remains.

## Rollback

Each change is a small, isolated commit on the feature branch. Because no infrastructure or data is touched, rollback is `git revert` of the relevant commits. Windows behavior is preserved for the kept scripts; the bash scanner is verified for parity against the PowerShell one before the `.ps1` is removed, so the secret gate is never weakened.

## Resolved Decisions

- **UNSURE scripts** → kept as reference (not deleted).
- **Migration runbook docs** (`cutover-dns.md`, `rollback-dns.md`) → kept as historical record.
- **`import_members.py`** → parameterized (CLI arg + documented default + usage message).
- **Clone location** → `/home/peter/projects/h-dcn` (WSL native filesystem).

## Open Flags (out of scope; separate decision)

1. **Frontend deploy target discrepancy**: `frontend-build-and-deploy-fast.ps1` references `s3://testportal-h-dcn-frontend/` and CloudFront `E2QTMDOE6H0R87`, which differ from the `guardrails` bucket `h-dcn-frontend-506221081911`. Kept as MANUAL-KEEP; not changed here.
2. **Stale IDs in `scripts/config.sh` / `config.py`**: point at the old account pool (`eu-west-1_OAT3oPCIm`) and a `/dev` API. Flag for a separate cleanup.
