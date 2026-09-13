# Local Backend Testing — Requirements

## Introduction

This project was migrated from Windows to WSL Ubuntu. The migration left the
local backend Python test environment half-wired, and it also exposed a gap in
how the backend is tested locally: unit tests only run against **moto**
(in-memory mocked AWS), and there is no documented, standard way to run the real
Lambda handlers locally against a Lambda-like runtime.

This spec covers two connected concerns:

1. **Repair** the broken local Python test environment so `pytest` runs backend
   unit tests from `backend/.venv` with zero workarounds.
2. **Establish** `sam local` as a first-class local backend test path, so
   handler behavior can be exercised in a Lambda-like Docker runtime and is less
   likely to drift from real AWS.
3. **Document** the resulting workflow for developers (docs and/or a steering
   file).
4. **Establish static-analysis / dead-code tooling** for the backend (**ruff**,
   **vulture**) and frontend (**ts-prune**), pinned in the dev toolchain, so
   dead-code and lint hunting is automated rather than manual.

> **Scope note (added during review):** ruff, vulture, and ts-prune were pulled
> into this spec at the reviewer's request. This spec therefore becomes the owner
> of that tooling and **supersedes** the related pointers in
> [`.kiro/specs/code-quality-fixes-2026-09/tasks.md`](../code-quality-fixes-2026-09/tasks.md):
> the "FOLLOW-UP: Introduce Ruff for backend Python (NEW SPEC)" section, task
> **P2.4** (add ts-prune to the frontend), and the vulture mentions. Those are
> folded in here (Requirements 13–15).

### Verified environment facts (established this session — treat as ground truth)

**Broken virtualenv (problem layer 1):**

- `backend/.venv` exists and its interpreter runs, but its own `site-packages`
  is **not** on `sys.path`. Every import falls through to
  `~/.local/lib/python3.11/site-packages`.
- That user-site stack has an incompatible OpenSSL/`cryptography` combination:
  - `OpenSSL.crypto` raises `AttributeError: module 'lib' has no attribute
    'GEN_EMAIL'`
  - `cryptography.hazmat.bindings._rust` cannot import `x509`
- Result: `boto3`/`moto` are unusable from `backend/.venv`, so `pytest` cannot
  run backend tests locally. A recent fix (`test_product_soft_delete`) had to be
  verified in a throwaway `/tmp` venv. That workaround must be eliminated.

**Weak local AWS testing story (problem layer 2):**

- Backend unit tests use moto — good for unit tests, but only simulates AWS.
- No documented/standard path to run the real handlers locally against a
  Lambda-like runtime, so behavior can drift from real AWS.

**Tooling already present (do NOT propose installing what already exists):**

- SAM CLI 1.165.0 installed; Docker 29.6.1 installed.
  - **Docker stability context:** On the old Windows setup, **Docker Desktop was
    unstable** and was a major pain point. Post-migration, a sibling project
    (migrated ~2 months ago) runs a **stable Docker MySQL + Python backend** on
    this same WSL Ubuntu machine — evidence that the **native WSL Docker engine**
    is reliable here and that the instability was specific to Docker Desktop on
    Windows. Everything now runs on native Linux; the Docker-dependent parts of
    this spec use the **native WSL Docker engine only** — Docker Desktop is not a
    supported path.
- `backend/template.yaml` (~97 KB) is the SAM template.
- `backend/events/event.json` exists — one generic sample event for
  `sam local invoke -e`.
- `backend/tests/integration/` already has integration tests
  (`test_admin_endpoints.py`, `test_api_gateway.py`, `test_auth_system_failures.py`,
  `test_payment_confirmation_flow.py`, `test_member_reporting_integration.py`,
  `test_member_reporting_e2e.py`, `test_submit_order_flow.py`,
  `test_unified_pipeline.py`, `test_auth_performance.py`) but they are not part
  of any documented local flow.
- `backend/tests/requirements.txt` already lists:
  `pytest, pytest-mock, boto3, moto, requests, hypothesis, Pillow, PyJWT==2.9.0,
  bcrypt==4.2.1` (no versions pinned for the core test toolchain).
- ggshield (pipx) + the pre-push hook were fixed this session and are **out of
  scope** — do not re-touch.

### Out of scope

- LocalStack (tracked as a possible future follow-up — see Requirement 8).
- Wiring any of this into CI (local-dev capability first — see Requirement 8).
- **Modifying the GitHub Actions workflows** (`.github/workflows/deploy-backend.yml`,
  `deploy-frontend.yml`, `full-test-suite.yml`). This spec adds no `sam local` /
  DynamoDB Local step and no ruff/vulture/ts-prune gate to CI. Note: CI already
  runs `pip install -r tests/requirements.txt`, so pinning that file (Requirement
  2) benefits CI automatically **without** editing any workflow — the only CI
  interaction is a one-time verification run (see Requirement 2.6) to confirm the
  pinned set does not break the Full Test Suite.
- ggshield / secret-scanning hooks (already fixed this session).
- Any change to product/handler behavior, DynamoDB field names, financial field
  types, or the presmeet module.
- Adding DynamoDB tables, the Cognito user pool, or S3 data buckets to the SAM
  template.

### Decisions

- **OQ1 — `sam local` data source — DECIDED.** Local **DynamoDB Local** container
  (Docker) on a shared Docker network, seeded from a small fixture script. Chosen
  because it is least risky (never touches real AWS data), works fully offline,
  and moto's process-scoped mocks don't span a separate `sam local` process. The
  real `test` stage remains an explicit, opt-in **read-only** path (Docker-free
  fallback), but is not the default. See Requirement 7 (data source) and
  Requirement 12 (Docker-stability tiering).
- **OQ2 — LocalStack — DECIDED: OUT.** This spec uses moto (unit tests) +
  DynamoDB Local (`sam local`) only. LocalStack is not installed or depended on;
  it is recorded as a possible future follow-up if multi-service local emulation
  (e.g. S3 + SQS + Cognito together) is ever needed. See Requirement 8.3.
- **OQ3 — CI wiring — DECIDED: local-dev first, CI OUT.** This spec delivers a
  local-developer capability only and does NOT modify any CI workflow
  (`.github/workflows/*`). Wiring `sam local` / DynamoDB Local into CI is a
  deliberate future follow-up. See Requirement 8.4.

- **Tooling adoption posture — DECIDED (review addition).** ruff, vulture, and
  ts-prune are introduced in **non-blocking / report mode first** (they surface
  findings but do not fail any build or gate). Flipping any of them to blocking —
  and any large auto-fix sweep — is a deliberate follow-up decision, NOT part of
  this spec. This keeps the just-stabilized CI and the "fix only what is asked"
  guardrail intact.

All open questions are resolved; the decisions above are firm for this spec.

---

## Glossary

- **moto** — Python library that mocks AWS APIs in-process. Used by unit tests.
- **`sam local invoke`** — runs a single Lambda handler inside a Lambda-like
  Docker container using an event JSON file.
- **`sam local start-api`** — runs API Gateway + the handlers locally as an HTTP
  server.
- **DynamoDB Local** — AWS's downloadable DynamoDB emulator, runnable as a
  Docker container.
- **user-site** — `~/.local/lib/python3.11/site-packages`, Python's per-user
  package location that leaks into any interpreter unless `PYTHONNOUSERSITE=1`.
- **`test` stage** — the deployed non-production CloudFormation stage in the
  nonprofit account (506221081911, eu-west-1).
- **ruff** — fast Python linter (and optional formatter); covers unused imports
  (`F401`), unused vars (`F841`), redefinitions (`F811`), unreachable code,
  import sorting (`I`), and more.
- **vulture** — static analyzer that finds dead Python code (functions, classes,
  attributes never referenced) across modules — complementary to ruff's
  within-file findings.
- **ts-prune** — tool that finds unused TypeScript `export`s across a frontend
  codebase.
- **report / non-blocking mode** — a tool runs and prints findings but does not
  fail a build, commit, or CI gate.

---

## Requirements

### Requirement 1 — Repaired virtualenv resolves all deps without `~/.local`

**User Story:** As a backend developer, I want `backend/.venv` to resolve every
test dependency from its own `site-packages`, so that imports never fall through
to the broken `~/.local` stack.

#### Acceptance Criteria

1. WHEN `backend/.venv` is recreated with `python3.11 -m venv` THEN the
   interpreter SHALL place its own `site-packages` on `sys.path` ahead of any
   user-site path.
2. WHEN the venv interpreter runs with `PYTHONNOUSERSITE=1` THEN every test
   dependency (`boto3`, `moto`, `hypothesis`, `pytest`, `cryptography`,
   `Pillow`, `PyJWT`, `bcrypt`) SHALL import successfully with no reliance on
   `~/.local/lib/python3.11/site-packages`.
3. WHEN `python -c "import OpenSSL.crypto"` runs in the repaired venv THEN it
   SHALL NOT raise `AttributeError: module 'lib' has no attribute 'GEN_EMAIL'`.
4. WHEN `python -c "from cryptography import x509"` runs in the repaired venv
   THEN it SHALL import without the `cryptography.hazmat.bindings._rust` error.
5. WHEN `python -c "import site; print(site.ENABLE_USER_SITE)"` runs under the
   documented setup THEN user-site SHALL be disabled (or otherwise proven not to
   shadow the venv).

### Requirement 2 — Pinned, reproducible test toolchain

**User Story:** As a backend developer, I want the test toolchain pinned in
`backend/tests/requirements.txt`, so that a clean install produces a known-good,
reproducible environment.

#### Acceptance Criteria

1. WHEN `backend/tests/requirements.txt` is updated THEN it SHALL pin working
   versions for at least `boto3`, `moto`, `hypothesis`, `pytest`, and a working
   `cryptography` (in addition to the existing `Pillow`, `PyJWT`, `bcrypt`).
2. WHEN the pinned `cryptography` version is chosen THEN it SHALL be compatible
   with the pinned `pyOpenSSL`/`boto3` such that Requirement 1.3 and 1.4 hold.
3. WHEN `pip install -r backend/tests/requirements.txt` runs into a freshly
   created `backend/.venv` THEN it SHALL complete without dependency-resolution
   errors.
4. WHERE the runtime deps in `backend/requirements.txt` (`boto3==1.34.0`,
   `botocore==1.34.0`) constrain the test toolchain THEN the test requirements
   SHALL be chosen to remain compatible, OR the divergence SHALL be documented.
5. WHEN the test requirements are pinned THEN the pins SHALL be recorded in a way
   that a future developer can reproduce the exact set (e.g. a comment noting the
   verified Python patch version, or a lock/freeze snapshot in the spec/docs).
6. WHEN `backend/tests/requirements.txt` is repinned THEN the Full Test Suite
   (`full-test-suite.yml`, which already runs `pip install -r
   tests/requirements.txt` on a clean runner) SHALL be run once against the
   feature branch to confirm the pinned set does not break CI — **without editing
   the workflow itself**. This is a verification step, not a workflow change.

### Requirement 3 — Conflicting user-site / system packages no longer leak in

**User Story:** As a backend developer, I want the broken `~/.local` and system
`dist-packages` OpenSSL/`cryptography` to stop shadowing the venv, so that they
cannot silently break tests again after the venv is repaired.

#### Acceptance Criteria

1. WHEN the repair is complete THEN the conflicting `~/.local`
   OpenSSL/`cryptography` packages SHALL be removed, relocated, OR isolated via a
   documented, durable mechanism (e.g. `PYTHONNOUSERSITE=1` baked into the
   documented workflow and/or a venv activation setting).
2. IF the system `dist-packages` OpenSSL/`cryptography` are the source of the
   conflict THEN the chosen isolation SHALL prevent them from appearing on the
   venv's `sys.path`.
3. WHEN a developer follows the documented setup on a clean checkout THEN the
   conflict SHALL NOT recur (the fix SHALL be durable, not a one-off manual
   patch).
4. WHERE removing user-site packages could affect other tooling on the machine
   THEN the spec SHALL prefer isolation (non-destructive) over deletion, and any
   deletion SHALL be called out explicitly for the developer to confirm.

### Requirement 4 — Unit tests run from the repaired venv (no `/tmp` workaround)

**User Story:** As a backend developer, I want to run backend unit tests directly
from `backend/.venv`, so that I never need a throwaway `/tmp` venv again.

#### Acceptance Criteria

1. WHEN `pytest backend/tests/unit/test_product_soft_delete.py` runs from the
   repaired `backend/.venv` THEN it SHALL pass with no `/tmp` venv and no
   `~/.local` reliance. *(Primary acceptance gate — matches Goal A.)*
2. WHEN a representative moto-based unit test that exercises `boto3`/`moto` runs
   from the repaired venv THEN it SHALL pass.
3. WHEN unit tests run THEN they SHALL continue to honor
   `.kiro/steering/testing-backend.md` conventions (importlib `_load_handler`,
   `mock_aws`, `AWS_DEFAULT_REGION` + dummy creds set before handler import, no
   bare `sys.path` + `import app`).
4. WHEN verifying THEN only the specific relevant test file(s) SHALL be run — the
   full ~40-minute backend suite SHALL NOT be run in automation.

### Requirement 5 — `sam local invoke` is a documented, working local path

**User Story:** As a backend developer, I want a standard way to run a single
real handler locally in the Lambda-like Docker runtime, so that I can validate
behavior closer to real AWS than moto allows.

#### Acceptance Criteria

1. WHEN a developer runs `sam local invoke <FunctionName> -e <event-file>` per the
   documented steps THEN the handler SHALL execute in the Docker Lambda runtime
   and return a response.
2. WHEN the SAM template is used for local invoke THEN NO new DynamoDB table,
   Cognito pool, or S3 data bucket SHALL be added to it (guardrail: externally
   managed resources stay out of CloudFormation).
3. WHEN local invoke needs environment variables (table names, region, pool IDs)
   THEN the documented flow SHALL supply them via an env-var JSON file
   (`--env-vars`) rather than editing the template.
4. WHEN the region is referenced THEN it SHALL be `eu-west-1`.

### Requirement 6 — Representative sample events for key endpoints

**User Story:** As a backend developer, I want realistic sample events for the
key endpoints, so that I can invoke handlers locally without hand-crafting event
JSON each time.

#### Acceptance Criteria

1. WHEN `backend/events/` is expanded THEN it SHALL contain representative event
   JSON files for a selected set of key endpoints (beyond the single generic
   `event.json`).
2. WHERE endpoints require auth THEN sample events SHALL include a
   `requestContext.authorizer` / headers shape consistent with what handlers
   read (access-token-based `cognito:groups`, per the auth steering), using
   **placeholder** non-secret values.
3. WHEN sample events are added THEN they SHALL NOT contain real secrets, real
   member PII, or real JWTs — only clearly-fake placeholders.
4. WHEN the set of "key endpoints" is chosen THEN it SHALL be justified in the
   design (e.g. one read, one mutating/financial, one auth-triggered) rather than
   attempting to cover all handlers.

### Requirement 7 — Documented, low-risk data source for `sam local`

**User Story:** As a backend developer, I want a documented way for locally
invoked handlers to reach data, so that I can run realistic local scenarios
without risking real AWS data.

#### Acceptance Criteria

1. WHEN the data-source approach is documented THEN it SHALL present the DECIDED
   default — **DynamoDB Local** (Docker) seeded from small fixtures — WITH
   tradeoffs versus the alternatives (moto vs local DynamoDB vs real `test`
   stage).
2. WHEN the default is documented THEN it SHALL NEVER perform destructive
   operations against `h-dcn-data-506221081911` or any production table.
3. IF the real `test` stage is offered as an opt-in path THEN the docs SHALL
   specify read-only intent, the `nonprofit-deploy` profile for automated ops
   (noting MFA profiles `nonprofit-dev`/`nonprofit-admin` for interactive work),
   and eu-west-1.
4. WHERE a local DynamoDB container is used THEN the design SHALL document how it
   is started, seeded (small fixtures, no prod copy), and connected to the
   `sam local` network.
5. WHEN any data-source option is documented THEN it SHALL NOT require adding
   externally-managed resources to the SAM template.

### Requirement 8 — Integration tests wired into the local story; scope boundaries

**User Story:** As a backend developer, I want the existing
`backend/tests/integration/` tests connected to the documented local flow where
it makes sense, and clear boundaries on what is deferred.

#### Acceptance Criteria

1. WHEN the design covers integration tests THEN it SHALL state which existing
   `backend/tests/integration/` tests fit the `sam local` / local-data flow and
   how they are run locally.
2. WHERE an integration test cannot run purely locally (e.g. needs the real
   `test` stage) THEN that SHALL be documented explicitly, not silently mixed
   with the offline path.
3. WHEN LocalStack is considered THEN it SHALL be recorded as OUT of scope for
   this spec (per OQ2 default) with a one-line note as a possible follow-up.
4. WHEN CI is considered THEN it SHALL be recorded as a local-dev-first
   capability with CI wiring as an optional follow-up (per OQ3 default), and this
   spec SHALL NOT modify CI workflows.

### Requirement 9 — Developer documentation / steering

**User Story:** As a developer new to the repo, I want a concise "local backend
test setup" guide, so that I can set up and run everything without tribal
knowledge or the `/tmp` workaround.

#### Acceptance Criteria

1. WHEN the documentation is added THEN it SHALL live in `docs/` and/or a
   steering file under `.kiro/steering/`, and cover: creating the venv,
   installing deps, running unit tests (moto), running a handler via `sam local`,
   and the AWS profile guidance (`nonprofit-deploy` for automated ops; MFA
   profiles for interactive work).
2. WHEN the docs describe commands THEN they SHALL target the WSL Ubuntu / bash
   environment (not PowerShell), consistent with the migrated setup.
3. WHEN the docs are complete THEN a developer following them on a clean checkout
   SHALL be able to reach the Requirement 4.1 acceptance gate without prior
   context.
4. WHERE existing steering (`testing-backend.md`, `tech.md`, `aws-dynamodb.md`,
   `guardrails.md`) already covers a point THEN the new docs SHALL reference it
   rather than duplicating or contradicting it.
5. WHEN the existing setup doc `docs/development/wsl-ubuntu-setup.md` is
   reconciled THEN its venv step SHALL be updated to include the user-site
   isolation guidance (`PYTHONNOUSERSITE=1` / `include-system-site-packages =
   false`) so it no longer reproduces the broken-venv recipe, AND its Docker note
   SHALL be corrected to reflect that Docker is also required for the `sam local`
   Tier-2 path (not only `sam build --use-container`), using the **native WSL
   Docker engine**. The Docker Desktop WSL-integration suggestion SHALL be
   **removed** — everything runs on native Linux and Docker Desktop is not a
   supported path.
6. WHERE `docs/development/wsl-ubuntu-setup.md` overlaps the new guide THEN it
   SHALL cross-link to `docs/development/local-backend-testing.md` rather than
   duplicating it.

### Requirement 17 — Architecture Decision Record + reconcile the migration ADR

**User Story:** As the project owner, I want the decisions in this spec recorded
as an ADR and reconciled with the existing WSL-migration ADR, so that
`docs/decisions/` stays the accurate source of truth.

#### Acceptance Criteria

1. WHEN this spec is implemented THEN a new ADR `docs/decisions/local-backend-testing.md`
   SHALL be created recording: the repaired-venv + user-site-isolation approach,
   the pinned test toolchain, `sam local` + DynamoDB Local as the Tier-2 path,
   the native-WSL-Docker-engine-only stance (no Docker Desktop), and the
   report-mode dead-code tooling (ruff/vulture/ts-prune).
2. WHEN the new ADR is written THEN it SHALL **reference** the existing
   `docs/decisions/wsl-ubuntu-migration.md` and explicitly note that it
   supersedes that ADR's two now-stale points: (a) Docker being "only needed for
   `sam build --use-container`", and (b) the venv setup recipe that omitted
   user-site isolation.
3. WHEN reconciling THEN the existing Accepted `wsl-ubuntu-migration.md` ADR
   SHALL NOT be rewritten; the correction SHALL live in the new ADR (and the
   setup doc per Requirement 9.5), preserving the migration ADR's provenance.
4. WHEN the new ADR is written THEN it SHALL follow the format of the existing
   ADRs in `docs/decisions/` (Context, Decision, Alternatives, Consequences).

### Requirement 18 — Local AWS service coverage: DynamoDB-only emulation, others mocked

**User Story:** As a backend developer, I want it made explicit that `sam local`
only emulates DynamoDB and that other AWS services (Cognito, SES, S3) are
mocked/stubbed locally, so that I am not misled into thinking a locally-invoked
handler exercises its full real-AWS dependency graph — and so a handler never
silently reaches a region where a service or feature is unavailable.

#### Acceptance Criteria

1. WHEN Tier 2 (`sam local`) is documented THEN it SHALL state that only
   **DynamoDB** is emulated locally (via DynamoDB Local), and that **Cognito,
   SES, and S3** calls are NOT emulated.
2. WHEN a handler under `sam local` depends on a non-DynamoDB AWS service THEN
   the documented default SHALL be to **mock/stub** that dependency locally (or
   supply the value via the event / `--env-vars`), NOT to reach real AWS.
3. WHERE a handler's behavior genuinely depends on a real non-DynamoDB service
   (e.g. Cognito group logic, SES send, S3 object) THEN it SHALL be treated as
   **integration testing against the real `test` stage in `eu-west-1`** (explicit
   opt-in), rather than expecting `sam local` to cover it.
4. WHEN any local path reaches real AWS (the opt-in `test`-stage integration
   path) THEN the region SHALL be `eu-west-1` and the `nonprofit-deploy` profile
   SHALL be used for automated ops (MFA profiles for interactive), consistent
   with Requirement 7.3.
5. WHEN the documentation lists sample events / candidate handlers for `sam
   local` THEN it SHALL prefer DynamoDB-backed handlers and SHALL flag
   Cognito/SES/S3-dependent handlers as "mock locally, or integration-test on the
   `test` stage".
6. WHERE real-AWS region enforcement is concerned THEN this spec SHALL only
   **document** `eu-west-1` as the expected region for real-AWS reach; a hard
   fail-if-unset rule is explicitly deferred (possible future tightening), so as
   not to expand scope now.

### Requirement 10 — Guardrail compliance throughout

**User Story:** As the project owner, I want this work to respect all project
guardrails, so that local testing never endangers production data or config.

#### Acceptance Criteria

1. WHEN any step touches AWS THEN it SHALL NOT run destructive S3 operations
   (`--delete`, `rm --recursive`) against `h-dcn-data-506221081911`.
2. WHEN the SAM template is involved THEN DynamoDB tables, the Cognito user pool,
   and S3 data buckets SHALL NOT be added without `DeletionPolicy: Retain` — and
   this spec adds none of them at all.
3. WHEN Cognito is referenced THEN its configuration SHALL NOT be modified.
4. WHEN AWS operations are automated THEN they SHALL use the `nonprofit-deploy`
   profile in eu-west-1.
5. WHEN financial fields, legacy field names, or the presmeet module are
   encountered THEN they SHALL be left unchanged.

### Requirement 12 — Tiered testing: Docker-free unit tests, Docker-dependent local AWS

**User Story:** As a backend developer who was burned by unstable Docker Desktop
on Windows, I want the everyday unit-test path to have zero Docker dependency and
the Docker-dependent capabilities clearly separated, so that I can always run
unit tests even if Docker is unavailable, and so the Docker parts target the
proven native WSL engine.

#### Acceptance Criteria

1. WHEN the unit-test path (repaired `backend/.venv` + moto) is used THEN it
   SHALL run to completion with **no dependency on Docker** (the primary
   acceptance gate in Requirement 4.1 SHALL NOT require Docker).
2. WHEN the design presents the local testing capabilities THEN it SHALL define
   two explicit tiers:
   - **Tier 1 (Docker-free):** venv + moto unit tests — the reliable everyday
     path.
   - **Tier 2 (Docker-dependent):** `sam local invoke` / `sam local start-api`
     and DynamoDB Local — closer to real AWS.
3. WHEN Tier 2 (Docker) is documented THEN it SHALL specify the **native WSL
   Docker engine** as the only supported path and SHALL NOT suggest Docker
   Desktop (everything runs on native Linux; Docker Desktop is not used),
   referencing the sibling project's stable native-Docker setup as the proven
   pattern.
4. WHEN Tier 2 data is needed but Docker is unavailable or undesirable THEN the
   docs SHALL offer the **read-only real `test` stage** as a Docker-free fallback
   (consistent with Requirement 7.3), so a developer is never fully blocked.
5. WHEN the docs describe Tier 2 THEN they SHALL include a short Docker
   troubleshooting note (e.g. verifying the engine with `docker version`,
   confirming it is the WSL-native engine, and how to start the daemon) so Docker
   issues are self-serviceable.

### Requirement 13 — Backend linting with ruff (report mode)

**User Story:** As a backend developer, I want ruff available and configured for
the backend Python code, so that lint issues and simple dead-code (unused
imports/vars, unreachable code, import order) are surfaced automatically instead
of hunted by hand.

#### Acceptance Criteria

1. WHEN the backend dev toolchain is set up THEN `ruff` SHALL be added as a
   pinned backend dev dependency (in `backend/tests/requirements.txt` or a
   dedicated `backend/requirements-dev.txt` — the design decides which).
2. WHEN ruff is configured THEN a curated config (`ruff.toml` or
   `[tool.ruff]` in `pyproject.toml`) SHALL start conservative with rule sets
   `E, F, I, B, UP` and a line length matching current style.
3. WHERE known-intentional patterns exist THEN per-file ignores / `# noqa`
   (with a reason) SHALL be configured for at least: the handler
   `try/except ImportError` shared-layer fallback blocks, test files
   (`tests/**`), and intentionally-retained public API (e.g. the
   `hdcn_cognito_admin/permission_utils.py` trio).
4. WHEN ruff is first run THEN findings SHALL be triaged into "safe to fix now"
   vs "ignore/`# noqa`", and only the safe ones fixed — consistent with the
   "fix only what is asked" guardrail (no broad auto-fix sweep).
5. WHEN ruff is adopted THEN it SHALL run in **report / non-blocking mode** and
   SHALL NOT be wired into any CI gate in this spec (blocking mode is a
   deliberate follow-up).
6. WHEN ruff runs THEN it SHALL be a dev-time-only tool with no runtime/Lambda
   cold-start impact (consistent with the lean-tooling stance in
   `.kiro/steering/type-safety.md`).

### Requirement 14 — Backend cross-module dead-code detection with vulture

**User Story:** As a backend developer, I want vulture available for the backend,
so that "defined but never referenced anywhere" dead code (which ruff's
within-file analysis misses) is surfaced.

#### Acceptance Criteria

1. WHEN the backend dev toolchain is set up THEN `vulture` SHALL be added as a
   pinned backend dev dependency alongside ruff.
2. WHEN vulture is configured THEN it SHALL have a documented invocation and,
   where needed, a whitelist / minimum-confidence setting to suppress known false
   positives (e.g. dynamically-referenced symbols, public API contracts proven by
   tests).
3. WHEN vulture is first run THEN its findings SHALL be triaged the same way as
   ruff (fix only the genuinely-dead, safe items; whitelist the rest with a
   reason) — no broad deletion sweep.
4. WHEN vulture is adopted THEN it SHALL run in **report / non-blocking mode**
   and SHALL NOT be wired into CI in this spec.
5. WHERE vulture and ruff overlap THEN the docs SHALL note they are
   complementary (ruff = within-file, vulture = cross-module), not a replacement
   for each other.

### Requirement 15 — Frontend unused-export detection with ts-prune (report mode)

**User Story:** As a frontend developer, I want ts-prune available for the
frontend, so that unused TypeScript exports are surfaced automatically (folding
in code-quality task P2.4).

#### Acceptance Criteria

1. WHEN the frontend tooling is set up THEN `ts-prune` SHALL be added as a pinned
   frontend dev dependency in `frontend/package.json` (devDependencies) with an
   npm script to run it (e.g. `npm run find:unused-exports`).
2. WHEN ts-prune is first run THEN its results SHALL be captured/logged as a
   findings report; genuinely-unused exports MAY be removed only where safe and
   in line with the dead-code rules in `.kiro/steering/specs.md`, otherwise left
   for a follow-up.
3. WHERE intentional public exports exist (e.g. barrel files, framework entry
   points) THEN ts-prune's known false positives SHALL be documented or
   suppressed via its ignore mechanisms.
4. WHEN ts-prune is adopted THEN it SHALL run in **report / non-blocking mode**
   and SHALL NOT be wired into CI in this spec.
5. WHEN ts-prune runs THEN it SHALL NOT modify the presmeet module, legacy field
   names, or any product behavior — it is a reporting tool.

### Requirement 16 — Tooling documented and superseding prior pointers

**User Story:** As a developer, I want the new tooling documented in one place
and the older code-quality pointers reconciled, so there is a single source of
truth.

#### Acceptance Criteria

1. WHEN the tooling is added THEN the "local backend test setup" documentation
   (Requirement 9) SHALL include how to run ruff, vulture, and ts-prune (commands,
   config location, report-mode expectation).
2. WHEN this spec is delivered THEN the code-quality tasks file SHALL be updated
   to mark the Ruff follow-up section, P2.4 (ts-prune), and the vulture mentions
   as folded into `local-backend-testing` (a pointer note, not a behavior change
   to that spec's other tasks).
3. WHEN the tooling is adopted THEN it SHALL be dev-time only and consistent with
   existing steering (`type-safety.md` lean-tooling stance; `specs.md` dead-code
   rules); it SHALL NOT contradict them.
4. WHEN the reusable monthly-scan prompt
   `.kiro/specs/Common/code-quality-maintenance/prompt.md` is reconciled THEN it
   SHALL be updated so its dead-code step uses the tooling this spec standardizes:
   `ruff` + `vulture` for the backend and `ts-prune` (via the new npm script) for
   the frontend, replacing the vague "check frontend for unused exports".
5. WHEN that prompt is updated THEN its pre-paste command warning and
   "execution hints" SHALL reflect the added tools (`ruff`, `ts-prune` alongside
   `vulture`) and SHALL note that these tools are installed/pinned by the
   `local-backend-testing` setup (referencing `docs/development/local-backend-testing.md`),
   rather than assuming they are already present.
6. WHEN that prompt is updated THEN it SHALL note the report/non-blocking
   expectation and SHALL NOT otherwise change the scan's structure, output-spec
   location, or workflow.
