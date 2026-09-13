# Local Backend Testing

How to run the H-DCN backend locally on WSL Ubuntu, in two tiers:

- **Tier 1 — Docker-free (everyday):** the repaired `backend/.venv` runs `pytest`
  unit tests with `moto` (in-process AWS mocks). Always works, no Docker.
- **Tier 2 — Docker (closer to real AWS):** `sam local` runs the real Lambda
  handlers in a Docker Lambda runtime against **DynamoDB Local**.

All commands are **bash / WSL**. Docker means the **native WSL Docker engine
only** (not Docker Desktop).

> See also the ADR: [`docs/decisions/local-backend-testing.md`](../decisions/local-backend-testing.md).

---

## Prerequisites

| Tool | Check | Notes |
| ---- | ----- | ----- |
| Python 3.11 | `python3.11 --version` | Verified patch: 3.11.15 |
| Native WSL Docker | `docker version` | Must show the native engine (context `default`, endpoint `unix:///var/run/docker.sock`), NOT Docker Desktop |
| SAM CLI | `sam --version` | For Tier 2 only |

Confirm Docker is the native WSL engine (Tier 2):

```bash
docker version          # Server should be "Docker Engine - Community", context: default
docker context ls       # 'default *' with unix:///var/run/docker.sock (no desktop-linux)
```

If `docker` reports "Cannot connect to the daemon", start it inside WSL
(`sudo service docker start` or your distro's equivalent). Docker Desktop is not
a supported path.

---

## Tier 1 — venv + unit tests (Docker-free)

### 1. Create / repair the venv

The venv **must** be isolated from system and user-site packages. A prior break
was caused by a missing `pyvenv.cfg` + a broken `~/.local` pyOpenSSL/cryptography
leaking onto `sys.path`. Recreate cleanly:

```bash
rm -rf backend/.venv
python3.11 -m venv backend/.venv
# Confirm isolation:
grep include-system-site-packages backend/.venv/pyvenv.cfg   # must be = false
```

### 2. User-site isolation (required)

Always run with `PYTHONNOUSERSITE=1` so a broken `~/.local` cannot leak in. The
venv's `activate` script exports it automatically; when calling the interpreter
directly, set it explicitly:

```bash
PYTHONNOUSERSITE=1 backend/.venv/bin/python -c "import site; print(site.ENABLE_USER_SITE)"  # False
```

### 3. Install the pinned test toolchain

```bash
backend/.venv/bin/pip install -r backend/tests/requirements.txt
```

The set is pinned for reproducibility (see `backend/tests/requirements.txt` and
the full freeze in `backend/tests/requirements.freeze.txt`). Key pins:

- `cryptography==43.0.3` + `pyOpenSSL==24.2.1` — the coherent pair that fixes the
  `OpenSSL.crypto` `GEN_EMAIL` crash. **pyOpenSSL is pinned explicitly** because
  modern `moto` no longer pulls it in transitively; omitting it reintroduces the
  break.
- `boto3==1.34.0` / `botocore==1.34.0` — match the runtime pins in
  `backend/requirements.txt`.
- `moto==5.0.14`.

### 4. Verify (primary gate)

```bash
cd backend
PYTHONNOUSERSITE=1 .venv/bin/python -m pytest tests/unit/test_product_soft_delete.py
PYTHONNOUSERSITE=1 .venv/bin/python -m pytest tests/unit/test_scan_product.py   # representative moto test
```

Both should pass, using `backend/.venv` (no `/tmp` venv, no `~/.local`).

> Never run the full backend suite locally (~40 min; runs nightly in CI). Run
> single files only, per `.kiro/steering/testing-backend.md`.

---

## Tier 2 — sam local + DynamoDB Local (Docker)

Tier 2 runs the real handlers in Docker against DynamoDB Local. The linchpin:
handlers create their DynamoDB resource with no `endpoint_url`, but the pinned
`boto3 1.34` honors the env var **`AWS_ENDPOINT_URL_DYNAMODB`** at construction
time — so pointing it at DynamoDB Local redirects the handler with **zero code
changes**.

### 1. Start DynamoDB Local

```bash
scripts/local/dynamodb-local-up.sh      # starts amazon/dynamodb-local on network hdcn-local, port 8000
```

### 2. Seed synthetic fixtures

```bash
backend/.venv/bin/python scripts/local/seed-dynamodb-local.py --reset
```

Creates the tables (Producten, Members, Payments, Events, Memberships, Orders,
Counters) with small **synthetic, non-PII** fixtures mirroring the Field Registry
keys/types (financial fields as Number). Flags: `--endpoint-url`, `--region`,
`--reset`.

### 3. Env-vars file

Copy the example (the real file is gitignored):

```bash
cp backend/events/env/local.json.example backend/events/env/local.json
```

It supplies, per function, `AWS_ENDPOINT_URL_DYNAMODB=http://dynamodb-local:8000`,
the `*_TABLE_NAME` values, region `eu-west-1`, and **dummy** AWS creds. No real
secrets/PII.

### 4. Build and invoke

```bash
cd backend
sam build
sam local invoke GetProductsFunction \
  -e events/get_products.json \
  --env-vars events/env/local.json \
  --docker-network hdcn-local
```

A valid response is a `statusCode: 200` proxy response whose body contains the
seeded products. Other sample events: `submit_order.json` (mutating/financial),
`get_members_filtered.json` (read + regional auth), `cognito_post_authentication.json`
(trigger shape; Cognito mocked).

For an HTTP server exercising API Gateway routing:

```bash
sam local start-api --env-vars events/env/local.json --docker-network hdcn-local
```

### 5. Teardown

```bash
scripts/local/dynamodb-local-down.sh
```

### Troubleshooting

- **`ValidationException: The provided key element does not match the schema`** on
  invoke → a stale table from an earlier seed run. Re-seed to drop and recreate:
  `backend/.venv/bin/python scripts/local/seed-dynamodb-local.py --reset`.
- **Lambda container can't reach DynamoDB** → ensure `--docker-network hdcn-local`
  and that the env file uses the in-network host `http://dynamodb-local:8000`
  (not `localhost`).
- **Docker not found / daemon down** → confirm the native WSL engine
  (`docker version`) and start it inside WSL.

---

## Local AWS service coverage

`sam local` here emulates **DynamoDB only** (via DynamoDB Local). Handlers that
call other AWS services are **not** emulated locally:

| Service | Locally | Real fidelity |
| ------- | ------- | ------------- |
| DynamoDB | Emulated (DynamoDB Local / moto) | — |
| Cognito | Mock/stub only | Integration on the deployed `test` stage |
| SES (email) | Mock/stub only | Integration on the deployed `test` stage |
| S3 | Mock/stub only | Integration on the deployed `test` stage |

Handlers depending on **Cognito** (e.g. the `cognito_*` triggers, the whole
`hdcn_cognito_admin/*` module, `get_member_self`, `event_onboard`,
`transition_member`, `bulk_transition_members`), **SES** (`send_delegate_invitation`,
the `email_actions.py` modules), or **S3** (report/registry/logo handlers,
`s3_file_manager`, `analyze_poster`, etc.) must have those calls mocked when run
purely locally, or be integration-tested against the deployed `test` stage.

### Data-source options

| Option | Realism | Risk | Offline | Works with sam local | Use |
| ------ | ------- | ---- | ------- | -------------------- | --- |
| moto | medium | none | yes | no (process-scoped) | unit tests only |
| DynamoDB Local | high | none | yes | yes | Tier 2 default |
| real `test` stage | highest | low (read-only) | no | yes | opt-in fallback |

The read-only `test`-stage fallback uses the `nonprofit-deploy` profile
(automated ops) or an MFA profile (`nonprofit-dev` / `nonprofit-admin`, interactive),
region `eu-west-1`, and never runs destructive operations.

### Integration tests (`backend/tests/integration/`)

Offline-capable (Tier 1, moto — run with `PYTHONNOUSERSITE=1`):
`test_admin_endpoints`, `test_submit_order_flow`, `test_payment_confirmation_flow`,
`test_unified_pipeline`, `test_auth_system_failures`,
`test_member_reporting_integration` (and `test_auth_performance`, though its
wall-clock timing assertions can be flaky under load).

Need the real `test` stage (hit live API Gateway / Cognito):
`test_api_gateway` (skips locally via `AWS_SAM_STACK_NAME` guard) and
`test_member_reporting_e2e` (mostly `TEST_JWT_*`-guarded, but a few error-path
tests are **not** guarded and will attempt real network calls — do not run
locally without setting a safe `API_BASE_URL`).

---

## Static analysis / dead-code tooling (report mode)

Report/non-blocking only — **not** wired into CI, no broad auto-fix sweep.
Complementary tools: **ruff** = within-file lint, **vulture** = cross-module dead
code, **ts-prune** = unused TS exports.

Install backend tools into the venv:

```bash
backend/.venv/bin/pip install -r backend/requirements-dev.txt   # ruff, vulture
```

### ruff (backend)

```bash
backend/.venv/bin/ruff check --config backend/ruff.toml backend/handler backend/layers
```

Config: `backend/ruff.toml` (rules `E, F, I, B, UP`; line-length 100; per-file
ignores for the handler `try/except ImportError` shared-layer fallback, `tests/**`,
and retained public API). Findings are triaged, not swept — fix only safe items
(import sorting etc.), leave the rest for a future opt-in blocking-mode pass.

### vulture (backend)

```bash
backend/.venv/bin/vulture backend/handler backend/layers backend/.vulture_whitelist.py --min-confidence 80
```

`backend/.vulture_whitelist.py` suppresses known false positives (Lambda entry
points, shared-layer public API, dynamically-referenced symbols) with a reason
per entry. Whitelist low-confidence shared-layer API rather than deleting it.

### ts-prune (frontend)

```bash
cd frontend
npm run find:unused-exports
```

Reports unused TS exports. Most findings are false positives: `(used in module)`
entries (used internally), `default` exports (dynamic import / lazy / barrel
files), and `.example.ts` demo files. **Never touch `presmeet`.** Remove only
genuinely-unused exports where clearly safe; document/suppress the rest.

---

## Scope boundaries

- **LocalStack: out of scope.** DynamoDB Local + moto cover the DynamoDB needs;
  multi-service local emulation (Cognito/SES/S3) is a possible future follow-up.
- **CI wiring: out of scope.** This is local-dev first. `sam local` / DynamoDB
  Local are not added to CI, and the ruff/vulture/ts-prune tools stay report-mode
  (no CI gate). The only CI touch is a one-time verification that the pinned
  `tests/requirements.txt` still installs.
