# Decision: WSL/Ubuntu Migration — Bash Hooks, No PowerShell on Linux

**Date:** 2026-09-12
**Status:** Accepted
**Related:** `.kiro/specs/Common/wsl-ubuntu-migration/`

## Context

The h-dcn development environment moved from Windows (PowerShell tooling) to
WSL/Ubuntu. The application code (Python 3.11, React/TypeScript) was already
portable; the friction was in the automation and environment layer:

- The git pre-push hook and the Kiro pre-commit hook both invoked a PowerShell
  secret scanner (`scripts/scan-secrets-local.ps1`) via `powershell.exe` /
  `powershell` — which does not exist on a default Ubuntu install.
- `frontend/package.json` `build:prod` used the CMD-only `set VAR=value` syntax.
- VS Code settings hardcoded `C:\Users\...` paths; the auth-layer tasks used
  PowerShell and backslash paths.
- No `.gitattributes` existed, so shell scripts risked CRLF corruption on checkout.
- The repo carried 55 `.ps1` scripts, many of them obsolete.

The real CI/CD was checked: all three GitHub Actions workflows run on
`ubuntu-latest` and invoke **no** `.ps1` script. Backend deploys via
`sam build`/`sam deploy`; frontend via `npm run build` (with `GENERATE_SOURCEMAP`
as a workflow env var) + `aws s3 sync` + CloudFront invalidation, triggered by push
to `main`. The CI ggshield scan was removed (2026-06-23) to preserve API quota, so
the **local hooks are the only secret gate**.

## Decision

**No PowerShell on Linux.** Make the commit/push path pure bash and rely on CI
(plain `sam`/`npm`/`aws`) for deploys.

1. **Ported the secret scanner to bash** (`scripts/scan-secrets-local.sh`),
   preserving the 13 patterns, `.gitguardian.yaml` `ignored_paths`, skip rules, and
   exit codes. Parity-verified against the PowerShell original before deleting it.
2. **Rewrote both hooks in bash:**
   - `.githooks/pre-push` calls `sh scripts/scan-secrets-local.sh` (no
     `powershell.exe`).
   - The Kiro pre-commit hook calls `scripts/precommit-guard.sh` (reads the
     tool-call JSON via `python3`, syncs the auth layer with `cmp`/`cp`, runs the
     bash scanner). `matcher: execute_pwsh` and `timeout` preserved.
3. **`.gitattributes`** normalizes text to LF (force LF for `*.sh` and
   `.githooks/*`; binary assets marked `binary`); renormalized the tree.
4. **`cross-env`** replaces the `set VAR=` syntax in `build:prod`.
5. **De-Windowsed config:** removed hardcoded `C:\...` paths from VS Code settings,
   added a Linux terminal profile, rewrote the auth-layer tasks as bash, and
   parameterized `backend/scripts/import_members.py`.
6. **Deploys stay on CI**; the equivalent manual commands are documented. No `pwsh`
   is required on Linux for any purpose.

### PowerShell script inventory outcome (55 total)

| Category | Count | Action |
| --- | --- | --- |
| LIVE (`scan-secrets-local.ps1`) | 1 | Ported to bash, then deleted |
| MANUAL-KEEP (Windows-only convenience) | 22 | Kept; documented Windows-only, unsupported on Linux |
| DEAD (completed migration/decommission, one-time fixes, ad-hoc tests, junk) | 32 | Deleted |

Of the "unsure" scripts, 5 (`cleanup-s3-bucket.ps1`, `test_members_api_endpoint.ps1`,
`check-ssl-validation.ps1`, `verify-access.ps1`, `install-gh-cli.ps1`) were **kept as
reference** by user decision. The DNS migration runbooks
(`scripts/migration/cutover-dns.md`, `rollback-dns.md`) were **kept as historical
record** with a note that their referenced scripts were removed.

## Alternatives considered

| Option | Verdict | Why |
| --- | --- | --- |
| Install `pwsh` on Ubuntu, fix only the `powershell.exe` calls | Rejected | User requirement: no PowerShell on Linux. Adds a runtime dependency for the most-run path. |
| Reuse the `myAdmin` project's bash scanner | Rejected | Keeps the two projects independent; avoids a forked/duplicated script and drift. |
| Rewrite all 55 `.ps1` scripts to bash | Rejected | Large, risky diff for rarely-run, guardrail-sensitive scripts. CI is the deploy source of truth; MANUAL-KEEP scripts are Windows-only convenience. |
| Copy the Windows working tree to Linux | Rejected | Drags CRLF and Windows artifacts (`sam-env/`, Windows `.venv/`) over. Clone-fresh is clean. |

## Consequences

- The commit/push secret gate works on Linux with zero PowerShell.
- The 22 MANUAL-KEEP `.ps1` scripts do not run on Linux; the setup guide points to
  CI / manual commands instead.
- The Linux environment is created by cloning fresh into
  `/home/peter/projects/h-dcn` and recreating machine-local artifacts natively.
- Setup steps are documented in `docs/development/wsl-ubuntu-setup.md`.

## Open flags (out of scope; separate decisions)

- `scripts/deployment/frontend-build-and-deploy-fast.ps1` references
  `s3://testportal-h-dcn-frontend/` and CloudFront `E2QTMDOE6H0R87`, which differ
  from the `guardrails` bucket `h-dcn-frontend-506221081911`. Not changed here.
- `scripts/config.sh` / `config.py` reference the old account pool
  (`eu-west-1_OAT3oPCIm`) and a `/dev` API — flagged for a separate cleanup.
