# Code Quality Fixes — 2026-09 — Tasks

Execution sequence (revised after the Full Test Suite scan revealed hidden
collection errors). Each task references findings in `requirements.md`.

Definition of done per project rules: code + tests pass, `npx eslint` clean,
`npx tsc --noEmit` clean (frontend), translations in all 8 locales for any
user-facing strings, migration script if DynamoDB data changes, commit on the
current feature branch, push + trigger workflows.

## Why this order

1. **Fix the tests & CI reporting first** — the suite currently hides collection
   errors, so there is no trustworthy baseline. Nothing else can be validated
   until the suite is honest and green.
2. **Dead code next** — low risk, and removing it shrinks files, so some may drop
   under the 500-line threshold and need no refactor.
3. **File length after dead code** — refactor only what is still oversized.
4. **Missing tests** — add coverage once the code being tested is stable.
5. **Stale docs last** — independent, lowest urgency.

## Dependency graph

```
Phase 1  (tests + CI reporting)   ← FIRST: establish a trustworthy green baseline
   P1.2 (fix CI reporting) ─── must land before ── P1.4 (re-run suite)
   P1.1 (fix test files)  ─────────────────────────┘
Phase 2  (dead code)  ── shrinks files, do before length refactors
Phase 3  (file length) ── depends on Phase 2
Phase 4  (missing tests) ── depends on a stable/green baseline (Phase 1)
Phase 5  (stale docs)  ── independent, last
```

---

## Phase 1 — Broken tests + CI reporting (DO FIRST)

The Full Test Suite summary reported "139 passed / 0 failed", but the console log
showed **pytest collection errors** (`NoRegionError`) that the summary miscounts
as passing. See requirements §5. Establish a trustworthy baseline before any
other change.

- [x] **P1.0** Retrieved run **34702448400** results (branch
  `feature/wsl-ubuntu-migration`) and inspected console log + artifacts.
- [x] **P1.1** Fixed confirmed `NoRegionError` collection errors by setting
  `AWS_DEFAULT_REGION` + dummy creds BEFORE the handler import (per
  `.kiro/steering/testing-backend.md`):
  - [x] `backend/tests/unit/test_get_member_self.py`
  - [x] `backend/tests/unit/test_get_members_filtered.py`
  - [x] Verified under CI-like env (region unset): both collect + pass (21 passed).
- [x] **P1.3** Swept ALL unit tests with `--co` under CI-like env (region unset,
  `--continue-on-collection-errors`). Result: **0 `NoRegionError` remain**; 1755
  tests collect. One unrelated collection error surfaced (see P1.5). The other
  "at-risk" files collect fine (they set region via env/conftest).
- [x] **P1.5** (test-isolation bug — NOT stale) `backend/tests/unit/test_event_dedup.py`
  failed collection with `ModuleNotFoundError: No module named 'shared.event_dedup'`.
  Root cause: the module DOES exist at `scripts/shared/event_dedup.py`, but the
  auth layer also ships a `shared` package; whichever loads first wins in
  `sys.modules` and shadows the other. In isolation the test passed (38 tests);
  only the full-suite run collided. **Fixed** by loading the module directly by
  file path via `importlib` (unique module name `scripts_event_dedup`), avoiding
  the `shared` name collision. Verified: passes with the auth-layer `shared`
  loaded first, and full `--co` sweep now shows 0 collection errors (1793 tests).
- [x] **P1.2** (CI-reporting bug) Fixed `full-test-suite.yml`. Root cause: the
  runner used `pytest "$f" ... | tail -3` inside an `if`, so the pipeline's exit
  status was `tail`'s (always 0) — every file counted as PASSED, hiding
  collection errors (exit 2) AND real failures. Changes (backend + frontend):
  - Capture pytest/jest's REAL exit code (no pipe masking); classify exit 2 as a
    collection error, 124 as timeout, other non-zero as failure.
  - Append FULL per-file output to `test-output.txt` (was a one-line summary
    only), so downstream analysis can see errors.
  - Count errors separately; write correct `failures`/`errors` into the JUnit XML.
  - `exit 1` from the run step when any file failed/errored so the run status is
    meaningful (later steps still run via `continue-on-error`).
  - Verified YAML parses; verified the exit-code logic fix locally.
- [~] **P1.4** Re-ran the Full Test Suite (run **34709004161**) after pushing the
  Phase-1 fixes. The run correctly **failed** (proving P1.2's reporting fix works —
  the old run would have falsely reported success). Analysis of the artifacts
  revealed:
  - [x] **P1.2 validated** — errors now surface instead of being hidden.
  - [x] **P1.6** (workflow follow-up bug, MINE) The rewritten run steps aborted at
    the first failing file because GitHub runs `run:` bash with `set -e`; a
    failing `pytest`/`jest` tripped errexit before the loop could continue.
    **Fixed** by adding `set +e` to both run steps (backend + frontend). YAML
    re-validated.
  - [x] **P1.7** (STALE test — rewritten) `test_admin_endpoints.py::TestOrderLifecycle::
    test_payment_failed_is_terminal` asserted `payment_failed` is terminal, but
    `order_state_machine.py` **intentionally** allows `payment_failed → submitted`
    (retry). Rewrote as `test_payment_failed_allows_retry_to_submitted`: asserts
    the retry IS allowed, cannot skip to `paid`, and `get_next_valid_states` ==
    `['submitted']`. Verified locally (TestOrderLifecycle: 4 passed).
  - [ ] **P1.8** Frontend failure at `src/__tests__/i18n/localeSync.property.test.ts`
    (file 14/145) — the run aborted there under `set -e`, so files 15-145 never
    ran. After P1.6, re-run to surface the full frontend failure set, then triage.
  - [ ] **P1.4-redo** After P1.6 + P1.7 (+ P1.8 triage), re-run and confirm a
    trustworthy result across ALL files.

> The re-run did its job: it exposed a real stale test (P1.7), a frontend failure
> (P1.8), and a bug in my own workflow edit (P1.6). Backend is NOT green — at
> least one stale test fails, and the suite hadn't run all files. Do P1.6 first
> (so the suite runs completely), then P1.7/P1.8.

## Phase 2 — Dead code (low risk, shrinks files)

- [ ] **P2.1** Remove unreachable code after `return` at
  `backend/handler/sync_google_calendar/app.py:271` (100% confidence). Verify the
  block below the return is truly dead, delete it, run
  `pytest tests/ -k sync_google_calendar`.
- [ ] **P2.2** Investigate and remove orphaned
  `backend/handler/get_events/app_fixed.py`. Confirm it is not referenced in
  `backend/template.yaml` or any import, then delete.
- [ ] **P2.3** Triage the 60%-confidence unused-symbol list (requirements §3).
  For EACH symbol, `grep` across `backend/`, `frontend/`, and `.kiro/specs/`
  before removing. Split into:
  - [ ] P2.3a Handler-local unused vars (`item_idx`, `claimed_at`, `sold_count`,
    `status_details`, `google_calendar_event_id`, `admin_error_response`,
    `line_idx`, `unapproved_statuses`, `SESSION_TOKEN_MAX_AGE`, `claimed_contact`)
    — safe to remove if genuinely unused.
  - [ ] P2.3b Unused local functions/classes (`get_row_allowed_emails`,
    `apply_regional_filtering`, `confirm_payment_and_reserve_stock`,
    `validate_permissions_fallback`, `InviteRequest`, `RevokeRequest`,
    `InviteEmailRequest`, `VerifyPasswordRequest`, `DashboardResponse`,
    permission_utils helpers) — verify not part of an interface/import.
  - [ ] P2.3c Auth-layer / shared / workflows candidates — **HIGH CAUTION**.
    `role_permissions.py`, `order_state_machine.py`, `product_validation.py`,
    `mollie_client.py` (esp. `verify_webhook_signature`), `workflows/*`,
    `stock_reservation.py`. These may be public API or dynamically dispatched.
    Keep unless proven dead; add `# vulture: ignore` or a whitelist entry if kept
    intentionally.
- [ ] **P2.4** (Optional) Add `ts-prune` to the frontend and run it to find
  unused TS exports; log results as a follow-up finding.

## Phase 3 — File length (refactor > 500; > 1000 is an error) — after Phase 2

- [ ] **P3.1** (ERROR) `backend/handler/generate_order_pdf/app.py` (1298) — split
  PDF-building helpers into a module (e.g. `pdf_builder.py`) under the handler;
  keep `lambda_handler` thin. Do first (only file over the hard limit).
- [ ] **P3.2** Refactor backend shared modules over 500:
  `role_permissions.py` (973), `product_validation.py` (784),
  `auth_utils.py` (645). Extract cohesive helper groups; these are
  high-blast-radius (imported everywhere) so change carefully with tests.
- [ ] **P3.3** Refactor backend handlers over 500 (recheck sizes after Phase 2
  dead-code removal, which may drop some under the threshold): `generate_preparation_pdf`,
  `submit_order`, `pay_order`, `mollie_webhook`, `hdcn_cognito_admin/user_operations.py`,
  `admin_event_claims`, `cognito_role_assignment`, `event_onboard`,
  `sync_google_calendar`, `update_order_items`, `manage_delegates`, `update_event`,
  `cognito_custom_message`.
- [ ] **P3.4** Refactor frontend files over 500 (extract hooks/subcomponents/utils).
  Prioritize the largest: `MemberEditView.tsx` (809), `MemberAdminTable.tsx` (792),
  `functionPermissions.ts` (763), `NewMemberApplicationForm.tsx` (749),
  `MemberEditModal.tsx` (737), `DataProcessingService.ts` (727). Others per §1.

## Phase 4 — Missing tests (35 backend handlers) — after Phase 1 baseline

- [ ] **P4.1** Add tests for financial / mutating handlers first (higher risk):
  `admin_confirm_payment`, `update_payment`, `delete_payment`, `update_product`,
  `delete_product`, `admin_update_order_status`, `admin_lock_orders`,
  `admin_unlock_order`, `create_membership`, `update_membership`,
  `delete_membership`. Follow `.kiro/steering/testing-backend.md` (importlib
  loader, moto, auth patches).
- [ ] **P4.2** Add tests for read handlers: `get_orders`, `get_payments`,
  `get_member_byid`, `get_membership_byid`, `get_memberships`, `get_order_byid`,
  `get_event_byid`, `get_member_payments`, `get_payment_byid`, `get_club_registry`,
  `admin_get_products`, `admin_get_payments`, `admin_get_report`,
  `admin_get_stock_movements`.
- [ ] **P4.3** Add tests for remaining: `admin_batch_pdf`,
  `admin_batch_update_status`, `admin_export_report`, `admin_generate_report`,
  `assign_club`, `cognito_user_migration`, `delete_event`, `s3_file_manager`,
  `upload_club_logo`, `upload_registry_logo`.
- [ ] **P4.4** (Frontend) Dedicated coverage pass for components/services lacking
  adjacent `.test` files (cross-reference §1 list).

## Phase 5 — Stale documentation (last)

- [ ] **P5.1** (HIGH) Review `docs/deployment/powershell-tips.md` — update for the
  Linux dev environment or retire it / add a bash equivalent.
- [ ] **P5.2** Verify `docs/security/secrets-management.md` against current SSM /
  Secrets Manager layout and `.secrets` usage.
- [ ] **P5.3** Verify `docs/infrastructure/custom-domain-setup.md`.
- [ ] **P5.4** Leave `docs/archive/*` as-is unless promoting content.

---

## Notes

- Work on branch `feature/wsl-ubuntu-migration` (do not create a new branch).
- Phase 3 after Phase 2: removing dead code may push some files back under 500
  lines, avoiding unnecessary refactors.
- The auth layer is high-blast-radius — refactor with full test coverage.
- Do not touch `frontend/src/modules/presmeet/`, legacy DynamoDB field names, or
  Cognito config (per steering "out of scope").
