# Decision: Local Backend Testing — Repaired venv + sam local/DynamoDB Local

**Date:** 2026-09-13
**Status:** Accepted
**Related:** `.kiro/specs/local-backend-testing/`; `docs/development/local-backend-testing.md`
**Supersedes (in part):** two stale points of `docs/decisions/wsl-ubuntu-migration.md` — see "What this means"

## Context

After the WSL/Ubuntu migration, the backend `backend/.venv` was broken: `pytest`
could not run because imports resolved against a broken `~/.local` stack
(`OpenSSL.crypto` → `GEN_EMAIL` AttributeError) instead of the venv. Two
independent faults were confirmed:

- **Fault A (root cause):** `backend/.venv/pyvenv.cfg` was missing, so CPython did
  not treat the directory as a venv — its own `site-packages` never loaded and
  `~/.local` + system `dist-packages` leaked onto `sys.path`.
- **Fault B:** the leaked user-site had an incompatible `pyOpenSSL` (25.3.0) /
  `cryptography` pair, crashing on import.

Separately, there was no first-class way to run the real Lambda handlers locally
against a database, and the test toolchain in `backend/tests/requirements.txt` was
largely unpinned (CI reproducibility risk). Dead-code/lint tooling (ruff, vulture,
ts-prune) was referenced by other specs but not actually installed.

## Decision

1. **Repair the venv by recreation + durable isolation**, not by patching
   `~/.local`. Recreate with `python3.11 -m venv` (restores `pyvenv.cfg` with
   `include-system-site-packages = false`), and enforce `PYTHONNOUSERSITE=1`
   (baked into the venv `activate` script and the documented workflow). Deleting
   the broken `~/.local` packages is an optional, explicitly-confirmed cleanup —
   isolation is preferred and sufficient.

2. **Pin a coherent test toolchain** in `backend/tests/requirements.txt`, with a
   full freeze snapshot in `backend/tests/requirements.freeze.txt`. The critical
   pins: `cryptography==43.0.3` + **explicit** `pyOpenSSL==24.2.1` (modern moto no
   longer pulls pyOpenSSL transitively), `boto3==1.34.0`/`botocore==1.34.0`
   (matching runtime), `moto==5.0.14`.

3. **Two-tier local testing:**
   - **Tier 1 (Docker-free):** venv + `pytest` + `moto` for unit tests. Always
     available.
   - **Tier 2 (Docker):** `sam local` runs real handlers against **DynamoDB
     Local** on a named Docker network. The enabler is `AWS_ENDPOINT_URL_DYNAMODB`,
     which the pinned `boto3 1.34` honors at client construction — so handlers
     reach DynamoDB Local with **zero code changes**. Env is injected via
     `sam local --env-vars`, not by editing the SAM template.

4. **Native WSL Docker engine only.** Docker Desktop is not a supported path.

5. **Static-analysis tooling in report mode.** ruff + vulture (backend,
   `requirements-dev.txt`) and ts-prune (frontend) are installed and configured
   but **not** wired into CI and run no broad auto-fix/deletion sweep — findings
   are triaged, safe items fixed, the rest whitelisted with a reason.

## Alternatives considered

- **Patch `~/.local` in place** (reinstall pyOpenSSL/cryptography there): rejected
  — leaves the leak mechanism intact; a future `include-system-site-packages` or
  unset `PYTHONNOUSERSITE` reintroduces the break.
- **moto for `sam local`:** impossible — moto is process-scoped and cannot
  intercept the separate Docker Lambda process. DynamoDB Local is a real shared
  network endpoint both processes reach.
- **Add `endpoint_url` to handler code:** rejected — that changes product code for
  a test-only concern. The env-var override achieves it with no code change.
- **LocalStack** (multi-service local emulation) and **wiring the tools/sam-local
  into CI:** deferred, out of scope.

## What this means

- `backend/.venv` is a recreatable, isolated dev artifact (gitignored). The
  reproducible recipe lives in `docs/development/local-backend-testing.md`.
- `sam local` covers **DynamoDB only**; Cognito/SES/S3 are mocked/stubbed locally.
  Real fidelity for those = integration on the deployed `test` stage (eu-west-1,
  read-only, opt-in).
- This ADR **supersedes two stale points** of `docs/decisions/wsl-ubuntu-migration.md`
  without rewriting it:
  1. **Docker scope** — Docker is not only for `sam build --use-container`; it is
     also the Tier-2 runtime for `sam local` + DynamoDB Local (native WSL engine).
  2. **venv recipe** — the bare `python3.11 -m venv` + `pip install` recipe is
     replaced by the recreate-with-isolation recipe (`PYTHONNOUSERSITE=1`,
     `include-system-site-packages = false`, pinned toolchain).
  The migration ADR itself remains Accepted and intact.

## When to reconsider

- If a shared API layer/SDK or a FastAPI migration emerges, revisit pinning and
  validation strategy.
- If multi-service local fidelity becomes necessary, revisit LocalStack.
- If the tooling should gate CI, revisit flipping ruff/vulture/ts-prune to
  blocking mode (and doing a proper cleanup sweep).
