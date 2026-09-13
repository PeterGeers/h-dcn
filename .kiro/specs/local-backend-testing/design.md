# Local Backend Testing — Design

## Overview

This design delivers two connected capabilities for the H-DCN backend on WSL
Ubuntu:

1. **A repaired, reproducible local Python test environment** (`backend/.venv`)
   so `pytest` runs unit tests with zero workarounds — the reliable, Docker-free
   everyday path (Tier 1).
2. **`sam local` as a first-class local AWS test path** — running the real Lambda
   handlers in a Docker Lambda runtime against a local DynamoDB, closer to real
   AWS than moto (Tier 2, Docker-dependent).

Plus developer documentation/steering so the workflow is reproducible without
tribal knowledge, and (added during review) **static-analysis / dead-code
tooling** — ruff + vulture (backend) and ts-prune (frontend) — installed in
report/non-blocking mode (Component 4).

The design is deliberately **two-tiered** (per Requirement 12): Tier 1 never
depends on Docker, so unit testing always works even if Docker is unavailable;
Tier 2 layers on the Docker-based realism and uses the **native WSL Docker
engine only** (proven stable on this machine by a sibling project). Everything
runs on native Linux; Docker Desktop is not a supported path.

This design maps to the approved `requirements.md`. It introduces **no
product/handler behavior changes**, adds **no resources to the SAM template**,
and **edits no CI workflow**.

> **GitHub workflows — no edits (deliberate).** `full-test-suite.yml` already
> runs `pip install -r tests/requirements.txt` on a clean runner, so pinning that
> file (Requirement 2) improves CI reproducibility **without** any workflow
> change. This spec adds no `sam local` / DynamoDB Local step and no
> ruff/vulture/ts-prune gate to CI (OQ3 = CI out; tooling = report mode). The
> only CI interaction is a **one-time verification run** to confirm the pinned
> deps don't break the Full Test Suite (Requirement 2.6). The pinned-deps change
> is the one thing that *reaches* CI (via the file CI already installs), which is
> why that verification run exists.

---

## Root-Cause Analysis (why the venv is broken)

Two independent faults were verified this session:

**Fault A — venv site-packages not on `sys.path`.** `backend/.venv` exists and
its interpreter runs, but its own `site-packages` is not on `sys.path`. Imports
fall through to user-site (`~/.local/lib/python3.11/site-packages`). The most
common causes on a Windows→WSL migration are:

- A `.venv` copied/relocated across filesystems so the hardcoded absolute paths
  in `pyvenv.cfg` / the interpreter symlink no longer resolve, and/or
- `include-system-site-packages = true` in `pyvenv.cfg` combined with an active
  user-site, so user-site shadows a (possibly empty) venv `site-packages`.

**Fault B — broken user-site OpenSSL/cryptography.** The user-site stack that
imports get resolved against has an incompatible OpenSSL/`cryptography`
combination:

- `OpenSSL.crypto` → `AttributeError: module 'lib' has no attribute 'GEN_EMAIL'`
- `cryptography.hazmat.bindings._rust` cannot import `x509`

This is a classic `pyOpenSSL` ↔ `cryptography` version mismatch (a `pyOpenSSL`
built against a newer/older `cryptography` than the one actually importable).
Because of Fault A, this broken stack is what every venv import lands on, so
`boto3`/`moto` fail and `pytest` cannot run.

**Design consequence:** repairing the venv is necessary but not sufficient — the
user-site stack must also be prevented from leaking back in (Requirement 3),
otherwise a future `include-system-site-packages` or an un-set
`PYTHONNOUSERSITE` reintroduces the breakage. The design therefore combines
*recreate the venv* + *pin a coherent toolchain* + *durable user-site
isolation*.

---

## Architecture

### The two tiers

```
┌─────────────────────────────────────────────────────────────────────┐
│ TIER 1 — Docker-free (everyday, reliable)                            │
│                                                                       │
│   backend/.venv  ──►  pytest tests/unit/…  ──►  moto (in-process)     │
│   (python3.11)        (PYTHONNOUSERSITE=1)      mock_aws              │
│                                                                       │
│   Primary acceptance gate: test_product_soft_delete.py passes here    │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                │  (same repaired venv drives the tooling)
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│ TIER 2 — Docker-dependent (closer to real AWS)                       │
│                                                                       │
│   sam local invoke <Fn> -e events/<x>.json  ──┐                       │
│   sam local start-api                          │  Docker Lambda       │
│                                                │  runtime (native     │
│                                                │  WSL engine)         │
│                                                ▼                       │
│                            AWS_ENDPOINT_URL_DYNAMODB ──► DynamoDB      │
│                                                          Local (Docker)│
│                                                          seeded w/     │
│                                                          fixtures      │
│                                                                       │
│   Docker-free fallback for data: read-only real `test` stage          │
└─────────────────────────────────────────────────────────────────────┘
```

### Key enabling fact: endpoint override needs no handler changes

Handlers construct their DynamoDB resource at import time, e.g.
(`backend/handler/get_products/app.py`):

```python
dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table_name = os.environ.get('PRODUCTEN_TABLE_NAME', 'Producten')
```

There is **no `endpoint_url`** and the region is hardcoded. However, the project
pins `boto3==1.34.0` / `botocore==1.34.0`, which is **newer** than the release
(boto3 1.28.58 / botocore 1.31.58, late 2023) that added support for the global
endpoint environment variables `AWS_ENDPOINT_URL` and the service-specific
`AWS_ENDPOINT_URL_DYNAMODB`. botocore reads these at client/resource construction
time regardless of whether `endpoint_url` is passed in code.

**Therefore:** setting `AWS_ENDPOINT_URL_DYNAMODB=http://dynamodb-local:8000` in
the Lambda container's environment redirects the handlers' DynamoDB calls to
DynamoDB Local with **zero handler code changes**. This is the linchpin of the
Tier 2 design and must be verified early (see Tasks). The hardcoded
`region_name='eu-west-1'` is harmless — DynamoDB Local ignores the region but
still requires one to be present.

> If this endpoint-env behavior were ever unavailable, the fallback is the
> read-only real `test` stage (no local data container). We do **not** modify
> handler code to add `endpoint_url` — that would touch product code for a
> test-only concern.

---

## Component 1 — Repaired virtualenv (Tier 1)

### 1.1 Recreate the venv cleanly

- Remove the existing broken `backend/.venv` and recreate with the system
  Python 3.11: `python3.11 -m venv backend/.venv`.
- Verify `backend/.venv/pyvenv.cfg` has `include-system-site-packages = false`.
- Verify the interpreter's own `site-packages` is first on `sys.path` and that
  user-site does not appear when `PYTHONNOUSERSITE=1`.

### 1.2 Durable user-site isolation (Requirement 3)

Two complementary, non-destructive mechanisms (prefer isolation over deletion):

- **`include-system-site-packages = false`** in `pyvenv.cfg` (blocks system
  `dist-packages`).
- **`PYTHONNOUSERSITE=1`** baked into the documented workflow. Options, in order
  of preference:
  1. Document exporting `PYTHONNOUSERSITE=1` in the venv's `activate` script (a
     small, reversible edit local to `backend/.venv`), and/or
  2. Document it in the "local backend test setup" doc + a `pytest` invocation
     wrapper.

Deletion of the broken user-site `pyOpenSSL`/`cryptography` is **offered as an
optional, explicitly-confirmed cleanup** (Requirement 3.4) — not required, since
isolation already prevents the leak. If chosen, it is limited to the specific
offending packages, and the developer confirms first.

### 1.3 Pin a coherent test toolchain (Requirement 2)

Update `backend/tests/requirements.txt` to pin working, mutually-compatible
versions. Target set (exact patch versions to be locked during implementation by
installing into the clean venv and freezing):

| Package        | Constraint intent                                            |
| -------------- | ------------------------------------------------------------ |
| `pytest`       | pin the verified version                                     |
| `pytest-mock`  | pin                                                          |
| `boto3`        | align with runtime `boto3==1.34.0` (Req 2.4)                 |
| `botocore`     | matching `1.34.x`                                            |
| `moto`         | pin a version compatible with `boto3 1.34`                   |
| `hypothesis`   | pin                                                          |
| `cryptography` | pin a version whose wheel imports cleanly (fixes Fault B)    |
| `pyOpenSSL`    | pin to match the chosen `cryptography` (prevents `GEN_EMAIL`)|
| `Pillow`       | keep existing                                                |
| `PyJWT`        | keep `==2.9.0`                                                |
| `bcrypt`       | keep `==4.2.1`                                                |

- The exact working versions are determined empirically during implementation
  (install into the clean venv, confirm `import OpenSSL.crypto` and
  `from cryptography import x509` succeed, then freeze).
- A verified freeze snapshot (and the Python patch version) is recorded in the
  docs so the set is reproducible (Requirement 2.5).

### 1.4 Verification (Requirement 4)

- Primary gate: `pytest tests/unit/test_product_soft_delete.py` passes from
  `backend/.venv` with `PYTHONNOUSERSITE=1`, no `/tmp` venv.
- Secondary: one representative moto test (e.g. a `scan_product` /
  `get_members`-style test that exercises `boto3` + `mock_aws`) passes.
- Conventions in `.kiro/steering/testing-backend.md` remain authoritative for
  test structure; no test files are restructured by this spec beyond what is
  needed to run them.

---

## Component 2 — `sam local` local AWS path (Tier 2)

### 2.1 DynamoDB Local container + shared network (Requirement 7, OQ1)

- A helper script (bash, e.g. `scripts/local/dynamodb-local-up.sh`) starts a
  **DynamoDB Local** container (`amazon/dynamodb-local`) on a named Docker
  network (e.g. `hdcn-local`), publishing port `8000`.
- `sam local invoke` / `start-api` run with `--docker-network hdcn-local` so the
  Lambda container can resolve `http://dynamodb-local:8000`.
- A **seed script** (`scripts/local/seed-dynamodb-local.py`) creates the tables
  (`Producten`, `Members`, `Payments`, `Events`, `Memberships`, `Orders`,
  `Counters`) in DynamoDB Local and inserts **small, synthetic fixtures** — no
  copy from prod, no PII. Keys/attribute types mirror the Field Registry so
  handler reads behave realistically (financial fields as Number, etc.).
- Teardown script stops/removes the container. DynamoDB Local data is ephemeral
  (in-memory or a local file under `backend/.local/`), never a real table.

**Why DynamoDB Local over moto here:** moto's mocks are process-scoped and live
inside the pytest process; `sam local` runs handlers in a **separate Docker
process**, so moto cannot intercept them. DynamoDB Local is a real network
endpoint both processes can share. (Tradeoffs table below.)

### 2.2 Environment injection via `--env-vars` (Requirement 5.3)

- A checked-in template `backend/events/env/local.json.example` (developer copies
  to `local.json`, which is gitignored) supplies per-function env vars:
  - `AWS_ENDPOINT_URL_DYNAMODB=http://dynamodb-local:8000`
  - `*_TABLE_NAME` values matching the seeded table names
  - `REGION_NAME` / region = `eu-west-1`
  - Placeholder non-secret values for anything else a handler reads.
- Supplied via `sam local invoke --env-vars backend/events/env/local.json`.
- The SAM template is **not edited** to achieve any of this (Requirement 5.2,
  10.2).

> **Dummy AWS credentials:** the Lambda container is given
> `AWS_ACCESS_KEY_ID=local` / `AWS_SECRET_ACCESS_KEY=local` (any non-empty value)
> so botocore signs requests; DynamoDB Local ignores the signature.

### 2.3 Sample events (Requirement 6)

Expand `backend/events/` beyond the single generic `event.json`. Chosen set
(justified: one read, one mutating/financial, one auth-triggered — Req 6.4),
each an API Gateway proxy event shaped like what handlers read:

| File                                | Handler / purpose                     | Category      |
| ----------------------------------- | ------------------------------------- | ------------- |
| `events/get_products.json`          | `GetProducts` — read path             | read          |
| `events/submit_order.json`          | order submission — mutating/financial | mutating      |
| `events/get_members_filtered.json`  | member read w/ regional filtering     | read + auth   |
| `events/cognito_post_authentication.json` | Cognito trigger event shape      | auth-triggered|

- Auth-carrying events include the shape handlers read for
  `extract_user_credentials` — access-token-based `cognito:groups` claims (per
  the auth steering) — using **fake** groups/emails/IDs only (Req 6.2, 6.3).
- No real JWTs, secrets, or member PII. Values are obviously synthetic
  (`user@example.test`, `local-fake-...`).

### 2.4 `sam local invoke` / `start-api` flow (Requirement 5)

- Documented commands:
  - `sam build` (once, or when handler deps change)
  - `sam local invoke <FunctionName> -e events/<x>.json --env-vars
    backend/events/env/local.json --docker-network hdcn-local`
  - `sam local start-api --env-vars … --docker-network hdcn-local` for an HTTP
    server exercising API Gateway routing.
- Region references are `eu-west-1` throughout (Req 5.4).

### 2.5 Data-source tradeoffs (Requirement 7.1)

| Option              | Realism        | Risk to real data | Offline | Works with `sam local`?          | Decision      |
| ------------------- | -------------- | ----------------- | ------- | -------------------------------- | ------------- |
| moto                | medium (mock)  | none              | yes     | **no** (process-scoped, can't cross into Docker) | unit tests only |
| **DynamoDB Local**  | high (real DDB API) | none         | yes     | **yes** (shared network endpoint) | **default**   |
| real `test` stage   | highest        | low (read-only)   | no      | yes (needs AWS creds)            | opt-in fallback |

- **Default: DynamoDB Local.** Least-risky option that actually works with
  `sam local`.
- **Fallback: real `test` stage, read-only**, using the `nonprofit-deploy`
  profile for automated ops (MFA profiles `nonprofit-dev`/`nonprofit-admin` for
  interactive work), region `eu-west-1` (Req 7.3). Documented as explicitly
  opt-in and Docker-free. Never runs destructive ops (Req 7.2, 10.1).

### 2.6 Local AWS service coverage — DynamoDB only, others mocked (Requirement 18)

`sam local` in this design emulates **DynamoDB only** (via DynamoDB Local). The
handlers also call other AWS services that are **not** emulated:

| Service            | Under `sam local`                     | For real fidelity                     |
| ------------------ | ------------------------------------- | ------------------------------------- |
| DynamoDB           | **emulated** (DynamoDB Local)         | —                                     |
| Cognito            | **mock/stub** locally                 | integration on real `test` stage      |
| SES (email)        | **mock/stub** locally                 | integration on real `test` stage      |
| S3                 | **mock/stub** locally                 | integration on real `test` stage      |

Decisions (per review):

- **Default = mock.** A handler under `sam local` that depends on Cognito/SES/S3
  gets those dependencies mocked/stubbed, or the needed value supplied via the
  event / `--env-vars`. It does **not** reach real AWS by default. This keeps
  `sam local` fully offline and avoids the region-availability trap — a handler
  can never silently reach a region where a service/feature (e.g. WebAuthn PLUS
  tier, or any region-gated capability) isn't available.
- **Real fidelity = integration on the `test` stage in `eu-west-1`.** When a
  handler's behavior genuinely depends on a real non-DynamoDB service, that is
  **integration testing against the deployed `test` stage** (explicit opt-in),
  `nonprofit-deploy` profile, region `eu-west-1`, read-only. Not a `sam local`
  concern.
- **Candidate selection.** The documented `sam local` handler/event set prefers
  **DynamoDB-backed** handlers (reads/writes). Cognito/SES/S3-dependent handlers
  are flagged in the docs as "mock locally, or integration-test on the `test`
  stage" rather than presented as full-fidelity local targets.
- **Region documentation, not enforcement (yet).** Any real-AWS reach is
  documented as `eu-west-1`; a hard fail-if-region-unset rule is **deferred**
  (possible future tightening) to avoid scope creep now.

> This is why the sample-event set in §2.3 is DynamoDB-leaning, and why the
> `cognito_post_authentication.json` event is included only to exercise the
> handler's **event-shape parsing / group-decision logic** locally (mocked
> Cognito calls), not to perform real Cognito group assignment.

### 2.7 Integration tests wiring (Requirement 8)

- Survey the existing `backend/tests/integration/` suite and classify each file:
  - **Offline-capable** (pure logic / moto-style) → run in Tier 1 with the
    repaired venv; documented under the unit/integration local flow.
  - **Needs a live-ish AWS surface** → documented against DynamoDB Local (Tier 2)
    or the read-only `test` stage, whichever the test's assertions require.
- Where an integration test cannot run purely locally, that is stated explicitly
  in the docs (Req 8.2) rather than silently mixed in.
- No integration test is rewritten to change behavior; the design only documents
  *how to run them locally* and, where trivial (e.g. adding an env-var/marker),
  makes them runnable.

---

## Component 3 — Developer documentation / steering (Requirement 9)

- **New doc:** `docs/development/local-backend-testing.md` — the primary guide.
  Sections:
  1. Prerequisites (python3.11, native WSL Docker engine, SAM CLI — all already
     installed; how to confirm).
  2. Tier 1: create venv → install `tests/requirements.txt` → run unit tests
     (moto) with `PYTHONNOUSERSITE=1`.
  3. Tier 2: start DynamoDB Local → seed → `sam build` → `sam local invoke` /
     `start-api` with `--env-vars` + `--docker-network`.
  4. Data-source options + the read-only `test`-stage fallback.
  5. AWS profile guidance (`nonprofit-deploy` for automated ops; MFA profiles
     for interactive).
  6. Docker troubleshooting (confirming the native WSL engine with `docker
     version`; starting the daemon) — Req 12.5. Docker Desktop is out of scope.
- **Steering pointer:** extend/point from `.kiro/steering/tech.md` (Common
  Commands) and `.kiro/steering/testing-backend.md` to the new doc, rather than
  duplicating (Req 9.4). A short steering note may be added if the team wants it
  always-in-context; default is a doc + a one-line steering reference.
- All commands target WSL/bash, not PowerShell (Req 9.2).

### Reconcile the existing WSL setup doc + ADR (Requirements 9.5–9.6, 17)

Two existing documents conflict with this spec and are reconciled **without
rewriting the Accepted migration ADR**:

- **`docs/development/wsl-ubuntu-setup.md` (edit):**
  - Fix the venv step — it currently prescribes
    `python3.11 -m venv backend/.venv` + `pip install -r … tests/requirements.txt`
    with **no user-site isolation**, i.e. the exact recipe that produced the
    broken venv. Add `PYTHONNOUSERSITE=1` / `include-system-site-packages = false`
    guidance.
  - Correct the Docker note — it currently says Docker is "only needed for
    `sam build --use-container`" and mentions Docker Desktop WSL integration.
    State that Docker is also the runtime for the `sam local` Tier-2 path, using
    the **native WSL Docker engine only**, and **remove** the Docker Desktop
    WSL-integration suggestion (everything runs on native Linux; Docker Desktop is
    not a supported path).
  - Cross-link to `docs/development/local-backend-testing.md` instead of
    duplicating.
- **`docs/decisions/local-backend-testing.md` (new ADR):** records the decisions
  from this spec (repaired venv + isolation, pinned toolchain, `sam local` +
  DynamoDB Local, native-engine-over-Docker-Desktop, report-mode tooling). It
  **references** `docs/decisions/wsl-ubuntu-migration.md` and explicitly
  supersedes that ADR's two stale points (Docker scope; venv recipe). Follows the
  existing ADR format (Context / Decision / Alternatives / Consequences). The
  Accepted migration ADR itself is left intact (Req 17.3).

> The migration ADR's "Open flags" (frontend deploy bucket/CloudFront mismatch;
> `scripts/config.sh`/`config.py` old-account pool) are **unrelated** to this
> spec and left untouched.

---

---

## Component 4 — Static-analysis / dead-code tooling (Requirements 13–16)

Added during review: this spec also stands up dead-code / lint tooling in
**report / non-blocking mode**. None of it is wired into CI, and no broad
auto-fix/deletion sweep is performed — findings are triaged, safe items fixed,
the rest whitelisted with a reason (consistent with "fix only what is asked").

### 4.1 Backend: ruff + vulture

- **Home for the deps:** create **`backend/requirements-dev.txt`** as the backend
  dev-tooling file (keeps runtime `requirements.txt` and test `tests/requirements.txt`
  clean). Pin `ruff` and `vulture` there. Rationale: linters are neither runtime
  deps nor strictly test deps; a dedicated dev file is the cleanest home and gives
  the future "blocking mode" follow-up an obvious place to build on.
- **ruff config:** `ruff.toml` at `backend/` (or `[tool.ruff]` in a backend
  `pyproject.toml` if one is introduced). Start with rule sets `E, F, I, B, UP`;
  line length matching current style. Per-file ignores for:
  - handler `try/except ImportError` shared-layer fallback blocks (`F401`/`E402`),
  - `tests/**`,
  - intentionally-retained public API (e.g.
    `hdcn_cognito_admin/permission_utils.py` trio) via `# noqa` with a reason.
- **vulture config:** documented invocation (e.g. `vulture backend/handler
  backend/layers --min-confidence 80`) plus a `backend/.vulture_whitelist.py`
  for proven-but-dynamically-referenced symbols and test-proven public API.
- **Triage, not sweep:** first run classifies findings → fix only the safe,
  genuinely-dead ones; whitelist/`# noqa` the rest with a reason.
- **Report mode:** both run on demand (documented commands); NOT added to CI or
  any pre-commit/pre-push gate in this spec. Dev-time only, no Lambda cold-start
  impact.
- **Complementarity note** goes in the docs: ruff = within-file, vulture =
  cross-module.

### 4.2 Frontend: ts-prune

- Add `ts-prune` to `frontend/package.json` `devDependencies` (pinned) with an
  npm script, e.g. `"find:unused-exports": "ts-prune"`.
- First run captures a findings report. Genuinely-unused exports removed only
  where safe per `.kiro/steering/specs.md` dead-code rules; otherwise logged for
  follow-up.
- Known false positives (barrel files, framework entry points) documented or
  suppressed via ts-prune's ignore mechanism.
- Report mode only; not wired into CI. Never touches presmeet, legacy field
  names, or product behavior.

### 4.3 Documentation & supersede (Requirement 16)

- The `docs/development/local-backend-testing.md` guide gains a "Static analysis
  / dead-code tooling" section (ruff, vulture, ts-prune — commands, config
  locations, report-mode expectation, complementarity note).
- `.kiro/specs/code-quality-fixes-2026-09/tasks.md` is updated with pointer notes
  marking the Ruff follow-up section, P2.4 (ts-prune), and the vulture mentions
  as **folded into `local-backend-testing`** — pointer only, no behavior change
  to that spec's other tasks.
- **`.kiro/specs/Common/code-quality-maintenance/prompt.md` (edit)** — this
  reusable monthly-scan prompt already invokes `vulture` (pre-paste warning,
  step 3 "Dead code", execution hints) but **assumes it is already installed**.
  Reconcile it to the tooling this spec standardizes:
  - Step 3 (Dead code): use `ruff` + `vulture` (backend) and `ts-prune` via the
    new npm script (frontend), replacing the vague "check frontend for unused
    exports".
  - Pre-paste command warning + execution hints: add `ruff` and `ts-prune`
    alongside `vulture`, and note the tools come from the `local-backend-testing`
    setup (pinned dev deps; see `docs/development/local-backend-testing.md`),
    rather than assuming presence.
  - Note the report/non-blocking expectation. No other change to the scan's
    structure, output-spec location, or workflow.

---

## File / Change Inventory

New (all test/dev-only; no product code, no SAM template, no CI):

```
backend/tests/requirements.txt            (edit: pin toolchain)
backend/.venv/                            (recreate — not committed; gitignored)
backend/events/get_products.json          (new sample event)
backend/events/submit_order.json          (new sample event)
backend/events/get_members_filtered.json  (new sample event)
backend/events/cognito_post_authentication.json (new sample event)
backend/events/env/local.json.example     (new env-vars template; local.json gitignored)
scripts/local/dynamodb-local-up.sh        (new: start DynamoDB Local on hdcn-local net)
scripts/local/dynamodb-local-down.sh      (new: teardown)
scripts/local/seed-dynamodb-local.py      (new: create tables + synthetic fixtures)
docs/development/local-backend-testing.md (new: the guide)
docs/decisions/local-backend-testing.md   (new: ADR; references + supersedes stale points of wsl-ubuntu-migration.md)
docs/development/wsl-ubuntu-setup.md       (edit: fix venv step + Docker note, cross-link new guide)
.gitignore                                (edit: ignore backend/.local/, env/local.json)
.kiro/steering/tech.md                    (edit: pointer to the new doc)
.kiro/steering/testing-backend.md         (edit: pointer to the new doc)

# Tooling (Component 4 — report mode only, no CI wiring)
backend/requirements-dev.txt              (new: pin ruff + vulture)
backend/ruff.toml                         (new: curated ruff config)
backend/.vulture_whitelist.py             (new: vulture false-positive whitelist)
frontend/package.json                     (edit: add ts-prune devDep + npm script)
.kiro/specs/code-quality-fixes-2026-09/tasks.md (edit: pointer notes — folded-in)
.kiro/specs/Common/code-quality-maintenance/prompt.md (edit: dead-code step → ruff+vulture+ts-prune; note setup source)
```

Explicitly **not** changed: `backend/template.yaml`, any `backend/handler/**`
product code, any `.github/workflows/**`, Cognito config, DynamoDB field
names/types, `frontend/src/modules/presmeet/**`.

---

## Guardrail Compliance (Requirement 10)

- **No SAM template resource additions** — externally-managed DynamoDB/Cognito/S3
  stay out; env injection is via `--env-vars`, not template edits.
- **No destructive S3 ops** against `h-dcn-data-506221081911`; the design never
  targets the data bucket at all.
- **Cognito untouched** — sample Cognito events use fake payloads; no pool/client
  config change.
- **`nonprofit-deploy` + eu-west-1** for any automated AWS op; `test` stage
  access is read-only and opt-in.
- **Financial fields, legacy names, presmeet** — untouched.
- **Secrets** — no real secrets/JWTs/PII in events or env files; `local.json`
  (which may hold local values) is gitignored; the pre-push ggshield scan still
  applies.

---

## Risks & Mitigations

| Risk                                                       | Mitigation                                                                 |
| ---------------------------------------------------------- | -------------------------------------------------------------------------- |
| `AWS_ENDPOINT_URL_DYNAMODB` not honored by pinned boto3    | Verified boto3 1.34 ≥ 1.28.58 (support added). Confirm empirically in an early task; fallback = read-only `test` stage (no handler edits). |
| Chosen `cryptography`/`pyOpenSSL` pins still conflict      | Lock versions empirically in the clean venv; assert `import OpenSSL.crypto` + `from cryptography import x509` before freezing.             |
| user-site leaks back after repair                          | `include-system-site-packages=false` + `PYTHONNOUSERSITE=1` baked into workflow; optional confirmed deletion of offending user-site pkgs.  |
| Docker instability recurs                                  | Tier 1 is fully Docker-free; Tier 2 targets native WSL engine (proven stable) + documented `test`-stage fallback + troubleshooting note.   |
| DynamoDB Local schema drifts from real tables              | Seed script mirrors Field Registry keys/types; kept minimal and synthetic.                                                                 |
| Handler under `sam local` silently reaches real AWS (Cognito/SES/S3), possibly in a region where a feature is unavailable | Only DynamoDB emulated; Cognito/SES/S3 mocked/stubbed locally by default (Req 18). Real-service fidelity is opt-in integration on the `test` stage, `eu-west-1`. |
| Full backend suite accidentally run (~40 min)              | Docs and tasks specify single-file runs only, per steering.                                                                                |

---

## Testing Strategy for this spec

Because this spec is environment/tooling (not product code), "tests" means
**verification steps**, not new unit tests:

1. **Venv health:** `python -c "import site; print(site.ENABLE_USER_SITE)"`,
   `import OpenSSL.crypto`, `from cryptography import x509`, `import moto, boto3`
   — all succeed in `backend/.venv` with `PYTHONNOUSERSITE=1`.
2. **Primary gate:** `pytest tests/unit/test_product_soft_delete.py` passes from
   `backend/.venv` (no `/tmp` venv).
3. **Endpoint override proof:** a small check that a handler invoked under
   `sam local` with `AWS_ENDPOINT_URL_DYNAMODB` reads/writes DynamoDB Local.
4. **`sam local invoke`** returns a valid response for at least the read sample
   event against seeded DynamoDB Local.
5. **Docs walkthrough:** follow `docs/development/local-backend-testing.md` on a
   clean shell and reach step 2 without prior context (Req 9.3).
6. **Tooling smoke:** `ruff check` and `vulture` run from `backend/` and
   `npm run find:unused-exports` runs from `frontend/`, each producing a report
   without erroring on config (report mode; no CI, no gate).
7. **Docs reconciliation:** the new ADR exists and references the migration ADR;
   `wsl-ubuntu-setup.md`'s venv step includes isolation and its Docker note is
   corrected — verified by reading the edited sections.

No full-suite runs; single-file verification only.
