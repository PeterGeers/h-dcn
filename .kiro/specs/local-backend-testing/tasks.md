# Local Backend Testing — Tasks

Implementation plan for the approved `requirements.md` (R1–R18) and `design.md`
(Components 1–4 + docs/ADR/prompt reconciliation).

## Ground rules

- Work on a **feature branch**, deliver via a **PR** — never commit directly to
  `main` (per steering). Current branch at spec creation was `main`, so the first
  task is creating the branch.
- **No product/handler behavior changes**, **no SAM template resource additions**,
  **no CI workflow edits**, no Cognito/field-name/presmeet changes.
- Verify with **single test files only** — never the full ~40-min backend suite.
- Tooling (ruff/vulture/ts-prune) runs in **report / non-blocking mode**; triage,
  don't sweep.
- All commands target **WSL/bash**; Docker means the **native WSL engine only**.

## Phase order & rationale

```
Phase 0  Branch setup                         ← must precede any change
Phase 1  Repair venv + toolchain (Tier 1)     ← unblocks everything; Docker-free
Phase 2  sam local + DynamoDB Local (Tier 2)  ← depends on a working venv/tooling
Phase 3  Static-analysis tooling (report)     ← independent of Tier 2; needs venv
Phase 4  Docs, ADR, prompt & supersede notes  ← after the behavior it documents exists
Phase 5  Verify + PR                          ← last
```

---

## Phase 0 — Branch setup

- [x] **T0.1** Create and check out a feature branch from `main` (e.g.
  `feature/local-backend-testing`) and push it to origin with `-u`. Confirm with
  `git branch --show-current`. (Steering: never work on `main`.)

---

## Phase 1 — Repair the venv + pinned toolchain (Tier 1, Docker-free)

_Requirements: 1, 2, 3, 4, 12.1_

- [x] **T1.1** Diagnose the current `backend/.venv` before deleting it: capture
  `pyvenv.cfg` contents, `sys.path`, and `site.ENABLE_USER_SITE` so the root
  cause (Fault A/B) is recorded. (R1.1, R1.5)
- [x] **T1.2** Recreate the venv cleanly: remove the broken `backend/.venv` and
  run `python3.11 -m venv backend/.venv`. Confirm `pyvenv.cfg` has
  `include-system-site-packages = false` and the venv `site-packages` is first on
  `sys.path`. (R1.1)
- [x] **T1.3** Determine a coherent, working set of pinned versions by installing
  into the clean venv and asserting the imports succeed:
  - `python -c "import OpenSSL.crypto"` (no `GEN_EMAIL` error) (R1.3)
  - `python -c "from cryptography import x509"` (no `_rust` error) (R1.4)
  - `python -c "import moto, boto3, hypothesis, pytest"` (R1.2)
  Lock the exact `cryptography` + `pyOpenSSL` (and `boto3`/`botocore`/`moto`)
  versions that pass. (R2.1, R2.2)
- [x] **T1.4** Update `backend/tests/requirements.txt` with the pinned set
  (`pytest`, `pytest-mock`, `boto3`, `botocore`, `moto`, `hypothesis`,
  `cryptography`, `pyOpenSSL`, keep `Pillow`/`PyJWT==2.9.0`/`bcrypt==4.2.1`).
  Keep alignment with runtime `boto3==1.34.0` or document the divergence.
  (R2.1, R2.3, R2.4)
- [x] **T1.5** Record the reproducible freeze: add a comment/snapshot noting the
  verified Python patch version and a `pip freeze` capture (in the doc or spec).
  (R2.5)
- [x] **T1.6** Establish durable user-site isolation (prefer non-destructive):
  - Bake `PYTHONNOUSERSITE=1` into the documented workflow (and optionally the
    venv `activate` script). (R3.1)
  - Confirm system `dist-packages` cannot appear on the venv `sys.path`
    (`include-system-site-packages = false`). (R3.2)
  - Confirm a clean-checkout setup does not reproduce the breakage. (R3.3)
  - IF deletion of the broken `~/.local` `pyOpenSSL`/`cryptography` is chosen,
    flag it explicitly and confirm before deleting (isolation preferred). (R3.4)
- [x] **T1.7** **Primary acceptance gate:** from the repaired `backend/.venv`
  with `PYTHONNOUSERSITE=1`, run
  `pytest tests/unit/test_product_soft_delete.py` — passes, no `/tmp` venv, no
  `~/.local` reliance. (R4.1, R12.1)
- [x] **T1.8** Run one representative moto-based unit test (e.g. a
  `scan_product`/`get_members`-style test exercising `boto3` + `mock_aws`) from
  the repaired venv — passes; confirms `testing-backend.md` conventions still
  hold. (R4.2, R4.3)

---

## Phase 2 — `sam local` + DynamoDB Local (Tier 2, native WSL Docker)

_Requirements: 5, 6, 7, 8, 12.2–12.5, 18; guardrails R10_

- [x] **T2.1** Confirm the Docker prerequisite: `docker version` shows the
  **native WSL engine** (not Docker Desktop). Record the check for the docs.
  (R12.3)
- [x] **T2.2** **Verify the endpoint-override enabler (do early — it gates the
  approach):** prove that a handler run under the pinned `boto3` honors
  `AWS_ENDPOINT_URL_DYNAMODB` and reaches DynamoDB Local, with **no handler code
  change**. If it does not, fall back to the read-only `test` stage and record
  that in the design/docs. (design §"Key enabling fact"; R5)
- [x] **T2.3** Add `scripts/local/dynamodb-local-up.sh` — start
  `amazon/dynamodb-local` on a named network (`hdcn-local`), publish port 8000.
  Add `scripts/local/dynamodb-local-down.sh` for teardown. (R7.4)
- [x] **T2.4** Add `scripts/local/seed-dynamodb-local.py` — create the tables
  (`Producten`, `Members`, `Payments`, `Events`, `Memberships`, `Orders`,
  `Counters`) in DynamoDB Local and insert **small synthetic fixtures** mirroring
  Field Registry keys/types (financial fields as Number). No prod copy, no PII.
  (R7.4, R7.5; guardrails: financial Number type)
- [x] **T2.5** Add `backend/events/env/local.json.example` — per-function env
  vars: `AWS_ENDPOINT_URL_DYNAMODB=http://dynamodb-local:8000`, `*_TABLE_NAME`,
  region `eu-west-1`, dummy AWS creds, placeholder non-secrets. Gitignore the
  real `local.json`. (R5.3, R5.4; R10.6)
- [x] **T2.6** Add representative sample events under `backend/events/`
  (justified set: one read, one mutating/financial, one auth, one Cognito
  trigger), with fake auth payloads (access-token `cognito:groups` shape), no
  real secrets/PII/JWTs:
  - `get_products.json` (read)
  - `submit_order.json` (mutating/financial)
  - `get_members_filtered.json` (read + regional auth)
  - `cognito_post_authentication.json` (auth-triggered; event-shape/group logic
    only, Cognito mocked)
  (R6.1–R6.4, R18.5)
- [x] **T2.7** Validate the flow end to end: `sam build`, then
  `sam local invoke GetProducts -e events/get_products.json --env-vars
  backend/events/env/local.json --docker-network hdcn-local` returns a valid
  response against seeded DynamoDB Local. (R5.1, R5.2)
- [x] **T2.8** Document the DynamoDB-only service coverage: Cognito/SES/S3 are
  **mocked/stubbed locally**; real fidelity for those = integration on the real
  `test` stage in `eu-west-1` (read-only, `nonprofit-deploy`, opt-in). Flag
  Cognito/SES/S3-dependent handlers accordingly. (R18.1–R18.5, R7.2, R7.3)
- [x] **T2.9** Survey `backend/tests/integration/` and classify each file:
  offline-capable (Tier 1 / DynamoDB Local) vs needs-real-`test`-stage; document
  how each is run locally and flag any that cannot run purely locally. No
  behavior rewrites. (R8.1, R8.2)
- [x] **T2.10** Record scope boundaries in the docs: LocalStack OUT (one-line
  follow-up note); CI wiring OUT (local-dev first). (R8.3, R8.4)

---

## Phase 3 — Static-analysis / dead-code tooling (report mode)

_Requirements: 13, 14, 15; report-mode, no CI gate_

- [x] **T3.1** Create `backend/requirements-dev.txt` and pin `ruff` + `vulture`.
  (R13.1, R14.1)
- [x] **T3.2** Add `backend/ruff.toml` (or `[tool.ruff]`): rule sets `E, F, I, B,
  UP`; line length matching current style; per-file ignores for the handler
  `try/except ImportError` fallback blocks, `tests/**`, and intentionally-kept
  public API (e.g. `hdcn_cognito_admin/permission_utils.py` trio via `# noqa` +
  reason). (R13.2, R13.3)
- [x] **T3.3** First ruff run: triage findings into "safe to fix now" vs
  "ignore/`# noqa`"; fix only the safe ones (no broad auto-fix). Keep it
  report-mode; do NOT wire into CI. (R13.4, R13.5, R13.6)
- [x] **T3.4** Configure vulture: documented invocation (e.g.
  `vulture backend/handler backend/layers --min-confidence 80`) + a
  `backend/.vulture_whitelist.py` for dynamically-referenced/public-API symbols.
  (R14.2)
- [x] **T3.5** First vulture run: triage the same way (fix genuinely-dead safe
  items, whitelist the rest with a reason). Report-mode, no CI. (R14.3, R14.4)
- [x] **T3.6** Add `ts-prune` to `frontend/package.json` devDependencies (pinned)
  + npm script `find:unused-exports`. Run once, capture the report; suppress/
  document known false positives (barrel files, entry points); remove
  genuinely-unused exports only where safe per `specs.md`. Do not touch presmeet.
  Report-mode, no CI. (R15.1–R15.5)

---

## Phase 4 — Documentation, ADR, prompt & supersede reconciliation

_Requirements: 9, 16, 17_

- [x] **T4.1** Write `docs/development/local-backend-testing.md` — the guide:
  prerequisites (python3.11, native WSL Docker, SAM CLI), Tier 1 (venv + deps +
  unit tests with `PYTHONNOUSERSITE=1`), Tier 2 (DynamoDB Local → seed →
  `sam build` → `sam local invoke`/`start-api` with `--env-vars` +
  `--docker-network`), data-source options + read-only `test`-stage fallback, AWS
  profile guidance, Docker troubleshooting (native engine; `docker version`),
  and the static-analysis tooling section (ruff/vulture/ts-prune, report-mode,
  complementarity note). Bash-only. (R9.1–R9.3, R16.1, R14.5)
- [x] **T4.2** Update `.gitignore` to ignore `backend/.local/` and
  `backend/events/env/local.json`. (design file inventory; R10.6)
- [x] **T4.3** Add steering pointers (not duplication): reference the new guide
  from `.kiro/steering/tech.md` (Common Commands) and
  `.kiro/steering/testing-backend.md`. (R9.4)
- [x] **T4.4** Reconcile `docs/development/wsl-ubuntu-setup.md`: fix the venv step
  to include user-site isolation; correct the Docker note (Docker also runs the
  `sam local` Tier-2 path, native WSL engine only) and **remove** the Docker
  Desktop WSL-integration suggestion; cross-link the new guide. (R9.5, R9.6)
- [x] **T4.5** Write the ADR `docs/decisions/local-backend-testing.md` in the
  existing ADR format (Context / Decision / Alternatives / Consequences),
  recording the repaired-venv + isolation approach, pinned toolchain, `sam local`
  + DynamoDB Local, native-WSL-engine-only stance, and report-mode tooling. It
  **references** `docs/decisions/wsl-ubuntu-migration.md` and supersedes its two
  stale points (Docker scope; venv recipe) **without rewriting** that ADR.
  (R17.1–R17.4)
- [x] **T4.6** Update `.kiro/specs/Common/code-quality-maintenance/prompt.md`:
  dead-code step → `ruff` + `vulture` (backend) and `ts-prune` via the new npm
  script (frontend); update pre-paste warning + execution hints to add `ruff`/
  `ts-prune` and note the tools come from the `local-backend-testing` setup;
  note report-mode. No other structural change. (R16.4–R16.6)
- [x] **T4.7** Add supersede pointer notes to
  `.kiro/specs/code-quality-fixes-2026-09/tasks.md`: mark the Ruff follow-up
  section, P2.4 (ts-prune), and the vulture mentions as **folded into
  `local-backend-testing`** (pointer only; no behavior change to that spec).
  (R16.2)

---

## Phase 5 — Verification & delivery

_Requirements: 2.6, 4, 9.3, 10, 12; design "Testing Strategy"_

- [x] **T5.1** Venv health check (record outputs):
  `import site; print(site.ENABLE_USER_SITE)`, `import OpenSSL.crypto`,
  `from cryptography import x509`, `import moto, boto3` — all succeed in the
  repaired venv with `PYTHONNOUSERSITE=1`. (R1, R3)
- [x] **T5.2** Re-confirm the primary gate (T1.7) and the representative moto
  test (T1.8) still pass. (R4.1, R4.2)
- [x] **T5.3** Tooling smoke: `ruff check` + `vulture` from `backend/` and
  `npm run find:unused-exports` from `frontend/` each produce a report without
  config errors (report-mode; no gate). (R13.5, R14.4, R15.4)
- [x] **T5.4** Docs walkthrough: follow `docs/development/local-backend-testing.md`
  on a clean shell and reach the primary gate (T1.7) without prior context.
  (R9.3)
- [x] **T5.5** Docs reconciliation check: the new ADR exists and references the
  migration ADR; `wsl-ubuntu-setup.md`'s venv step includes isolation and its
  Docker note is corrected (Docker Desktop suggestion removed). (R17, R9.5)
- [ ] **T5.6** **CI verification (no workflow edit):** push the branch and run the
  Full Test Suite once against it to confirm the repinned `tests/requirements.txt`
  does not break CI. Inspect the artifacts (CI reports "success" via
  continue-on-error). Do NOT modify any workflow. (R2.6)
- [x] **T5.7** Guardrail self-check before PR: no SAM template resource additions;
  no destructive S3 ops against `h-dcn-data-506221081911`; Cognito untouched;
  `nonprofit-deploy` + eu-west-1 for any real-AWS reach; financial fields / legacy
  names / presmeet untouched; no secrets/PII in events or env files. (R10.1–R10.6)
- [ ] **T5.8** Clean up any temporary artifacts (throwaway venvs, `.tmp-*`,
  DynamoDB Local data dirs). Open the PR (never merge to `main` directly);
  summarize changes, what was verified, and any deferred follow-ups (LocalStack,
  CI wiring, blocking-mode tooling, region-enforcement). (delivery)

---

## Deferred follow-ups (out of scope — noted, not done here)

- LocalStack (multi-service local emulation).
- Wiring `sam local` / DynamoDB Local into CI.
- Flipping ruff/vulture/ts-prune to **blocking** mode + any large auto-fix sweep.
- Hard fail-if-region-unset enforcement for real-AWS reach (currently documented,
  not enforced).
