# Code Quality Fixes — 2026-09 — Tasks

Execution sequence (revised after the Full Test Suite scan revealed hidden
collection errors). Each task references findings in `requirements.md`.

Definition of done per project rules: code + tests pass, `npx eslint` clean,
`npx tsc --noEmit` clean (frontend), translations in all 8 locales for any
user-facing strings, migration script if DynamoDB data changes, commit on the
current feature branch, push + trigger workflows.

## START HERE (session hand-off, updated 2026-09-12)

Branch: `feature/wsl-ubuntu-migration`. All work below is committed + pushed.

**Done:** Phase 1 is effectively complete. Backend collection errors + failures
fixed; CI reporting fixed (`full-test-suite.yml` honest); i18n conventions
conformed; and the **9 remaining frontend failures are ALL fixed** (P1.10b,
commit `adcb751`). Full Test Suite run **34717731194** confirms: frontend
145/145 green, backend 138 passed / 0 failed / 1 error.

**One open Phase-1 item (P1.11):** `tests/unit/test_product_soft_delete.py`
times out (>120s) in CI — the sole remaining "error". Pre-existing, unrelated to
the frontend work; needs optimization or a higher per-file timeout.

**Immediate next work:** P1.11 (the timeout), then Phase 2 (dead code) → Phase 3
(file length) → Phase 4 (missing tests) → Phase 5 (stale docs). None of 2–5
started yet.

**Commits this effort:** f5f304a, 06c1ffa, b951313, fb5d341, a60f620, d4cd610,
58bf88c (Phase 1 backend); ac8cdf9, 8c08693 (ADR), e1cb8a5, 33f41ef (i18n);
adcb751 (P1.10b — 9 frontend suites).

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
  - [x] **P1.8 / P1.4-redo** Re-ran with all fixes (run **34709680003**). Suite
    now runs to completion and reports honestly. FIRST trustworthy numbers:
    backend 121 passed / 9 failed / 9 errors; frontend 133 passed / 12 failed.
    Full failure inventory captured in requirements §5. These are pre-existing
    failures the old reporting hid — not regressions from this work.

### Newly surfaced work (pre-existing failures, now visible)

- [x] **P1.9** Fixed the 8 remaining backend collection errors — same
  `NoRegionError` fix as P1.1 (set `AWS_DEFAULT_REGION` + dummy creds before the
  handler import): `test_admin_get_orders`, `test_admin_record_payment`,
  `test_cognito_role_assignment`, `test_create_member`, `test_export_members`,
  `test_hdcn_cognito_admin`, `test_update_member`,
  `test_member_reporting_integration`. Verified under CI-like env (region unset):
  0 collection errors, all collect; and all 31 tests pass when run.
- [~] **P1.10** Triage the backend failures + 12 frontend failures. NOTE: CI runs
  each file as an INDEPENDENT pytest process (no cross-file ordering effects), so
  every failure is intrinsic to its file + the CI environment (fresh deps, no AWS
  region). Split into:
  - [x] **P1.10a** (region-only test bugs — mechanical fix, same as P1.1/P1.9)
    Fixed + verified under region-unset env (73 passed):
    `test_create_order`, `test_get_customer_orders`, `test_update_order_items`,
    `test_hdcn_cognito_admin_split`, `test_stub_validity`.
  - [ ] **P1.10b** (genuine failures — need per-case triage):
    - [x] `test_bulk_transition_members` — was `ModuleNotFoundError: No module
      named 'actions'`. Handler does `from actions import register_actions`; the
      importlib `_load_handler` didn't put the handler dir on `sys.path`. Fixed
      the loader to add the handler dir. Verified: 8 passed.
    - [x] `test_runner_utils.py` — was exit 5 (no tests collected): a util module
      named `test_*` with no tests. Added parametrized tests for
      `compute_combined_exit_code`. Verified: 6 passed.
    - [x] `test_sync_google_calendar` — STALE test (4 failures). Asserted
      `calendarId='test-calendar-id'` from a `GOOGLE_CALENDAR_ID` env var the
      handler no longer reads (it now selects per event_type via
      `_get_calendar_id`, defaulting to the Nationaal calendar). Updated the 4
      assertions to the real Nationaal calendar ID. Verified: 16 passed.
    - [x] **`test_cognito_post_authentication` — FIXED (was stale, handler
      correct).** Investigated both sources of truth:
      - Field registry `status` enum: `['Actief','Opgezegd','wachtRegio',...]` —
        no `'active'`/`'approved'`/`'pending'`.
      - Production Members table (1229 records): `Actief` 1097, `HdcnAccount` 62,
        `Sponsor` 52, `Club` 18 — ZERO `'active'`/`'approved'`.
      So the handler (`member_status == 'Actief'` → `hdcnLeden`; else/unknown →
      `verzoek_lid`) is correct and matches the auth steering. The 10 failures
      are all stale-test issues, in two groups:
      1. Seed non-existent statuses (`'active'`, `'approved'`) but assert
         `hdcnLeden` → change seed to `'Actief'`.
      2. `test_pending_member_gets_no_group` / `test_unknown_user_gets_no_group`
         assert `add_user_to_group` is NOT called, but the handler now
         intentionally assigns `verzoek_lid` to pending/unknown users → update to
         assert the `verzoek_lid` assignment.
      **FIXED**: seeds now use canonical statuses (`Actief` for approved cases;
      `Aangemeld`/`Geschorst` for non-active), and the "no group" tests were
      rewritten to assert the `verzoek_lid` assignment (renamed accordingly).
      Verified: 24 passed. Confirmed against field registry + 1229 prod records —
      handler was correct, tests were stale.
    - [~] 12 frontend failures (requirements §5) — 3 FIXED, 9 remaining:
      - [x] `localeSync.property.test.ts` — REAL data issue: `webshop.json` out of
        sync between `src/locales` and `public/locales` in all 8 languages. Synced
        `src → public`. (commit ac8cdf9)
      - [x] `translationFileConventions.test.ts` — FIXED. Decision was Option A
        (conform files) per multi-language-support Requirement 10.2/10.3. All 4
        offending namespaces conformed to depth<=2 + snake_case: `workflows`
        (ac8cdf9), `common` + `events` (e1cb8a5), `eventBooking` (33f41ef). Used
        migration scripts `scripts/migrate_workflows_i18n_keys.py` and
        `scripts/migrate_eventbooking_i18n_keys.py`. Added steering
        `.kiro/steering/i18n.md`. Verified: 93 tests / 7 suites pass, tsc clean.
      - [x] `CalendarLocationPreservation.property.test.tsx` — FIXED as a side
        effect of the `events` conformance (calendar.card.noLocation ->
        calendar_card.no_location). Verified passing.
      - [x] **9 remaining frontend failures — ALL FIXED** (commit `adcb751`).
        All were pre-existing test-side issues (stale tests or test-mock gaps),
        not product regressions:
        - `MemberAdminTable` / `MemberEditView` — test mock omitted
          `initReactI18next`; the transitive `src/i18n/index.ts` import called
          `i18next.use(undefined)` and threw. Added
          `initReactI18next: { type: '3rdParty', init: jest.fn() }`.
        - `memberFields.integrity` — STALE: registry now has 40 fields
          (administrative 8, not 5). Updated expected counts. Also fixed a real
          registry inconsistency: the three `welcome_pack_*` fields were defined
          in `membershipFields.ts` but tagged `group: 'administrative'`; moved
          them to `administrativeFields.ts` so the partial matches the declared
          group (the invariant the test checks). `MEMBER_FIELDS` total unchanged.
        - `AuthenticationIntegration` / `PasswordlessAuthenticationFlow` — STALE:
          `CustomAuthenticator` now makes ONE `signIn` (`USER_AUTH` /
          `EMAIL_OTP`, `clientMetadata.locale`) and uses an INLINE OTP form
          (placeholder `00000000`, submit `data-testid="otp-submit"`), not the
          old WEB_AUTHN-first fallback + `window.prompt`. Rewrote 5 assertions.
        - `BookingWizard` — STALE: event status vocab is `draft|published|
          archived` (per `eventFields` registry); `open`/`closed` are
          participation modes. Fixtures `open`→`published`, `closed`→`archived`.
          Also: compact `EventInfoHeader` (no name; capacity `"{rem} / {total}"`)
          and person-level role field removed (role is per-product now).
        - `ProductCard` — TEST MOCK GAP: `ProductCardActions` uses `Tooltip`
          (@chakra-ui/react) and `NotAllowedIcon` (@chakra-ui/icons), absent from
          the hand-rolled mocks → "Element type is invalid". Added both.
        - `VariantSelector` — STALE: component intentionally shows NO stock badge
          when `allow_oversell` is true. Assert neither badge appears.
        - `Dashboard.events-calendar` — STALE: authenticated card navigates to
          `/calendar` (the authenticated route); `/events/calendar` is public.
        - `WebshopPage` (TIMEOUT) — INFINITE EFFECT LOOP from the test mock: an
          unstable `t` (new function each render) broke `useCallback([toast,t])`,
          re-firing the load effect forever. Made the `useTranslation` mock
          return a stable singleton. Now passes in ~5s.
        Verified: `tsc --noEmit` clean; each suite passes locally.
- [x] **P1.4-final** Re-ran the Full Test Suite on `feature/wsl-ubuntu-migration`
  after pushing `adcb751`. Run **34717731194** — conclusion **success**. Honest
  artifact numbers:
  - **Frontend: 145 / 145 passed, 0 failed, 0 errors** — fully green (all 9
    P1.10b fixes confirmed).
  - **Backend: 138 passed, 0 failed, 1 error** — the single "error" is
    `TIMEOUT: tests/unit/test_product_soft_delete.py`, i.e. the pre-existing
    timeout already flagged in requirements §5 ("NOT yet investigated — was a
    timeout, may pass with more time or need optimization"). It is not a genuine
    failure and is unrelated to the frontend work; it remains the one open
    Phase-1 item. No assertion failures anywhere (`failed_tests: []` in both).

> Phase 1 is otherwise green. The only remaining Phase-1 item is the
> `test_product_soft_delete` CI timeout (needs optimization or a longer per-file
> timeout) — tracked as follow-up P1.11 below.

- [ ] **P1.11** Investigate `tests/unit/test_product_soft_delete.py` CI timeout
  (>120s per-file). Determine whether it is genuinely slow (optimize/split) or
  needs a higher timeout budget in `full-test-suite.yml`. Pre-existing; deferred
  from P1.10.

> Phase-1 status: backend is fully green (all collection errors + failures fixed,
> verified). Frontend: 3 of 12 failures fixed; 9 remain (listed above) — that is
> the immediate next work. CI reporting is fixed and trustworthy.

## Phase 2 — Dead code (low risk, shrinks files)

- [x] **P2.1** Removed the duplicate, unreachable `return SyncResult(...)` (and its
  duplicated comment) in the `except` block of
  `backend/handler/sync_google_calendar/app.py`. Verified: `pytest -k
  sync_google_calendar` = 22 passed.
- [x] **P2.2** Removed orphaned `backend/handler/get_events/app_fixed.py` AND the
  stale `app.py.backup_corrupted` in the same dir. Neither is referenced; the SAM
  template uses `Handler: app.lambda_handler` (only `app.py`).
- [x] **P2.3** Triaged the 60%-confidence unused-symbol list (each grepped across
  `backend/`, `frontend/`, `.kiro/specs/` first):
  - [x] P2.3a Removed genuinely-dead handler-local symbols:
    - `cognito_role_assignment`: unused `unapproved_statuses` list.
    - `get_event_registry`: unused `SESSION_TOKEN_MAX_AGE` constant (token expiry
      is enforced by the PyJWT `exp` claim set in `verify_event_password` — not a
      security regression).
    - `submit_order`: 3× `for item_idx, item in enumerate(items)` → `for item in
      items` (index never used; loops use `person_index`).
    - `update_member`: `status_details` unpack → `_`.
    - `update_payment` + `update_order_status`: `admin_error_response,
      regional_info` unpack → `_, _` (only `is_admin_authorized` is used).
    - FALSE POSITIVES kept (confirmed used): `sold_count`, `claimed_at`,
      `claimed_contact`, `google_calendar_event_id` (`line_idx` did not exist).
  - [x] P2.3b Removed dead documentation-only TypedDicts and uncalled functions:
    `InviteRequest`/`RevokeRequest` (manage_delegates), `InviteEmailRequest`
    (send_delegate_invitation), `VerifyPasswordRequest` (verify_event_password),
    `DashboardResponse`+`ProductCapacity` (admin_event_dashboard),
    `apply_regional_filtering` (export_members — the handler deliberately does no
    backend regional filtering; see note), `get_row_allowed_emails`
    (event_onboard), and the shadowed module-level `validate_permissions_fallback`
    (update_member). Cleaned up now-unused `typing` imports.
    - KEPT (proven NOT dead): the `hdcn_cognito_admin/permission_utils.py` trio
      (`get_user_field_permissions`, `check_role_permission`, `get_role_summary`) —
      verified as a public-API contract by `test_hdcn_cognito_admin_split.py`.
    - LEFT for a follow-up decision: `confirm_payment_and_reserve_stock`
      (`pay_order`, ~120 lines) is uncalled (live Mollie flow uses
      `shared.stock_reservation.reserve_stock_for_order`), but it is payment code —
      not removed in this cleanup sweep. Tracked as **P2.5**.
  - [x] P2.3c Auth-layer / shared / workflows candidates — **KEPT** (per HIGH
    CAUTION). Spot-checked `mollie_client.verify_webhook_signature`,
    `mollie_client.to_error_response`, `stock_reservation.AlreadyReservedError` —
    all covered by dedicated unit tests (`test_mollie_client.py`,
    `test_stock_reservation.py`), i.e. public API. Not dead.
- [ ] **P2.4** (Optional) Add `ts-prune` to the frontend and run it to find
  unused TS exports; log results as a follow-up finding. NOT done this cycle.
- [ ] **P2.5** (follow-up) Decide whether to remove the uncalled
  `confirm_payment_and_reserve_stock` in `backend/handler/pay_order/app.py`. It is
  superseded by `reserve_stock_for_order`; its docstring ("Called by the Mollie
  webhook") is stale. Payment code — remove only with explicit sign-off.

> Phase-2 verification: each edited handler's tests pass in isolation
> (`test_admin_event_dashboard` + `test_event_onboard` = 39 passed;
> `sync_google_calendar` = 22 passed). A broad multi-file `-k` run showed 18
> `NoSuchBucket` failures in `test_admin_event_dashboard`/`test_event_onboard`,
> but those are a PRE-EXISTING test-isolation issue (moto S3 bucket not set up
> when many suites share a process) — the same files are green in isolation, so
> the failures are not caused by the dead-code removal.

> Note (out of scope, security observation): `export_members` intentionally
> returns all members and relies on frontend-side regional filtering
> (`filtering: 'frontend_only'`, `regional: False`). Worth a future review, but
> not changed here.

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
