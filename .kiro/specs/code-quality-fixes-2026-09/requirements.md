# Code Quality Fixes — 2026-09

Findings from the monthly code quality scan (per
`.kiro/specs/Common/code-quality-maintenance/prompt.md`), run on branch
`feature/wsl-ubuntu-migration`.

Scope excludes: test files, `.venv/`, `node_modules/`, `build/`, generated files.

---

## 1. File length (target 500, error > 1000)

### Backend — ERROR (> 1000 lines)

| Lines | File |
| ----- | ---- |
| 1298  | `backend/handler/generate_order_pdf/app.py` |

> `backend/handler/generate_order_pdf/tests/test_properties.py` (1205) is a test
> file and is exempt per the file-size guideline.

### Backend — over 500 (non-test)

| Lines | File |
| ----- | ---- |
| 973 | `backend/layers/auth-layer/python/shared/role_permissions.py` |
| 784 | `backend/layers/auth-layer/python/shared/product_validation.py` |
| 741 | `backend/handler/generate_preparation_pdf/app.py` |
| 693 | `backend/handler/submit_order/app.py` |
| 684 | `backend/handler/pay_order/app.py` |
| 675 | `backend/handler/mollie_webhook/app.py` |
| 662 | `backend/handler/hdcn_cognito_admin/user_operations.py` |
| 649 | `backend/handler/admin_event_claims/app.py` |
| 646 | `backend/handler/cognito_role_assignment/app.py` |
| 645 | `backend/layers/auth-layer/python/shared/auth_utils.py` |
| 626 | `backend/handler/event_onboard/app.py` |
| 571 | `backend/handler/sync_google_calendar/app.py` |
| 556 | `backend/handler/update_order_items/app.py` |
| 554 | `backend/handler/manage_delegates/app.py` |
| 551 | `backend/handler/update_event/app.py` |
| 527 | `backend/handler/cognito_custom_message/app.py` |

### Frontend — over 500 (non-test source)

None exceed 1000. Files over 500:

| Lines | File |
| ----- | ---- |
| 809 | `frontend/src/components/MemberEditView.tsx` |
| 792 | `frontend/src/components/MemberAdminTable.tsx` |
| 763 | `frontend/src/utils/functionPermissions.ts` |
| 749 | `frontend/src/components/NewMemberApplicationForm.tsx` |
| 737 | `frontend/src/modules/members/components/MemberEditModal.tsx` |
| 727 | `frontend/src/services/DataProcessingService.ts` |
| 699 | `frontend/src/modules/eventBooking/admin/AdminClaimsManagement.tsx` |
| 698 | `frontend/src/services/GoogleMailService.ts` |
| 678 | `frontend/src/config/memberFields/modalConfig.ts` |
| 660 | `frontend/src/modules/webshop-management/components/OrderDetailDrawer.tsx` |
| 655 | `frontend/src/components/auth/CustomAuthenticator.tsx` |
| 654 | `frontend/src/modules/eventBooking/components/BookingWizard.tsx` |
| 650 | `frontend/src/modules/webshop/components/CheckoutModal.tsx` |
| 644 | `frontend/src/modules/products/ProductManagementPage.tsx` |
| 624 | `frontend/src/modules/products/components/OrderItemFieldsEditor.tsx` |
| 617 | `frontend/src/modules/products/components/VariantEditModal.tsx` |
| 609 | `frontend/src/modules/eventBooking/pages/EventRegisterPage.tsx` |
| 605 | `frontend/src/components/reporting/GoogleMailIntegration.tsx` |
| 599 | `frontend/src/services/MemberExportService.ts` |
| 568 | `frontend/src/modules/eventBooking/admin/AdminOrderLockUnlock.tsx` |
| 562 | `frontend/src/utils/fieldRenderers.ts` |
| 549 | `frontend/src/components/reporting/AddressLabelGenerator.tsx` |
| 544 | `frontend/src/modules/eventBooking/admin/EventDashboard.tsx` |
| 539 | `frontend/src/components/reporting/AnalyticsSection.tsx` |
| 538 | `frontend/src/modules/events/components/EventForm.tsx` |
| 532 | `frontend/src/services/AddressLabelService.ts` |
| 522 | `frontend/src/modules/webshop-management/components/OrdersTab.tsx` |
| 521 | `frontend/src/modules/events/EventLandingPage.tsx` |
| 514 | `frontend/src/components/auth/BrowserCompatibilityTest.tsx` |
| 512 | `frontend/src/modules/eventBooking/components/BookingSummaryPdf.tsx` |

---

## 2. Missing tests

95 backend handlers total; **35 have no corresponding test** (heuristic: no
`test_<handler>*.py` and no reference to the handler dir in any test file).
Verify each before writing tests — a few may be covered indirectly.

Handlers without an obvious test:

```
admin_batch_pdf            admin_batch_update_status   admin_confirm_payment
admin_export_report        admin_generate_report       admin_get_payments
admin_get_products         admin_get_report            admin_get_stock_movements
admin_lock_orders          admin_unlock_order          admin_update_order_status
assign_club                cognito_user_migration      create_membership
delete_event               delete_membership           delete_payment
delete_product             get_club_registry           get_event_byid
get_member_byid            get_member_payments         get_membership_byid
get_memberships            get_order_byid              get_orders
get_payment_byid           get_payments                s3_file_manager
update_membership          update_payment              update_product
upload_club_logo           upload_registry_logo
```

Priority subset (financial / data-mutating, higher risk): `admin_confirm_payment`,
`update_payment`, `delete_payment`, `update_product`, `delete_product`,
`admin_update_order_status`, `admin_lock_orders`, `admin_unlock_order`,
`create_membership`, `update_membership`, `delete_membership`.

> Frontend missing-test analysis was not exhaustively computed this run; the
> file-length list above shows many components/services lack adjacent `.test`
> files. Recommend a dedicated frontend coverage pass (see tasks).

---

## 3. Dead code (vulture)

### Confirmed (100% confidence)

| File:Line | Issue |
| --------- | ----- |
| `backend/handler/sync_google_calendar/app.py:271` | unreachable code after `return` |

### Likely orphaned file

- `backend/handler/get_events/app_fixed.py` — appears to be a stale duplicate of
  `get_events/app.py` (name suggests a one-off fix copy). Verify it is not wired
  into `template.yaml`, then remove.

### Unused symbols (60% confidence — MANUAL VERIFICATION REQUIRED)

`lambda_handler` and Cognito trigger entrypoints were excluded as false positives
(invoked by the AWS runtime, not from code). Remaining candidates worth checking:

- Handlers: `admin_event_claims` (`claimed_at`), `admin_event_dashboard`
  (`sold_count`, class `DashboardResponse`), `cognito_role_assignment`
  (`unapproved_statuses`), `event_onboard` (`get_row_allowed_emails`),
  `export_members` (`apply_regional_filtering`), `get_event_registry`
  (`SESSION_TOKEN_MAX_AGE`, `claimed_contact`), `hdcn_cognito_admin/permission_utils.py`
  (`get_user_field_permissions`, `check_role_permission`, `get_role_summary`),
  `manage_delegates` (classes `InviteRequest`, `RevokeRequest`), `pay_order`
  (`confirm_payment_and_reserve_stock`), `send_delegate_invitation`
  (`InviteEmailRequest`), `submit_order` (`item_idx` ×3),
  `sync_google_calendar` (`google_calendar_event_id` ×2), `update_member`
  (`validate_permissions_fallback` ×2, `status_details`),
  `verify_event_password` (`VerifyPasswordRequest`).
- Auth layer / shared: `auth_utils.py` (`check_regional_data_access`,
  `get_user_accessible_regions`, `log_role_structure_validation`),
  `order_state_machine.py` (`validate_fulfilment_transition`,
  `get_valid_transitions_for_actor`, `get_next_valid_states`),
  `product_validation.py` (`validate_variant_attributes`,
  `validate_variant_schema`), `role_permissions.py` (6 `*_organizational_role*`
  / regional helpers), `mollie_client.py` (`verify_webhook_signature`,
  `to_error_response`, `MOLLIE_API_KEY`), `workflows/*` (`register`,
  `get_allowed_events`, `has_valid_payment`, etc.), `stock_reservation.py`
  (`AlreadyReservedError`), `item_fields_validator.py`
  (`validate_item_fields_data`).

> Caution: several auth-layer functions and `workflows/*` methods may be public
> API, dynamically dispatched, or used only from tests. Do NOT delete without
> grepping the codebase (and `.kiro/specs/`) for each symbol first.

> Frontend unused-export analysis was not run this cycle (no ts-prune configured).
> Recommend adding a `ts-prune` pass in a follow-up.

---

## 4. Stale documentation

Code last changed `2026-09-12`. Docs sorted oldest-first; pre-June-2026
non-archive docs are review candidates:

- `docs/deployment/powershell-tips.md` (2026-01-18) — **HIGH**: PowerShell-centric,
  likely outdated after the Windows→Linux dev migration. Review/retire or add a
  bash equivalent.
- `docs/security/secrets-management.md` (2026-01-18) — verify against current
  SSM/Secrets Manager layout (`/h-dcn/{env}/...`) and `.secrets` usage.
- `docs/infrastructure/custom-domain-setup.md` (2026-01-18) — verify.
- `docs/archive/*` (2026-01-18 / 2026-06-30) — archive folder, expected stale;
  no action unless promoting content.
- Mid-2026 docs (`authentication-architecture.md`, `guardrails.md`, decisions)
  are recent enough; spot-check only if related handlers changed.

> Staleness here is date-based heuristic, not content diff. Each flagged doc needs
> a human read against current code before edits.

---

## 5. Broken / stale tests (Full Test Suite)

- Triggered "Full Test Suite" (`full-test-suite.yml`) on branch
  `feature/wsl-ubuntu-migration`. Run ID: **34702448400**, completed
  `2026-09-12`.

### CRITICAL: the summary is misleading — collection errors are hidden

The workflow's per-file runner reports `Total: 139 | Passed: 139 | Failed: 0`,
and the uploaded `test-output.txt` artifact contains ONLY that one summary line.
But the live GitHub Actions console log shows **pytest collection errors** that
the summary does not count as failures, e.g.:

```
[67/139] Running: tests/unit/test_get_member_self.py
ERROR tests/unit/test_get_member_self.py - botocore.exceptions.NoRegionError: You must specify a region.
!!!!! Interrupted: 1 error during collection !!!!!
[68/139] Running: tests/unit/test_get_members_filtered.py
ERROR tests/unit/test_get_members_filtered.py - botocore.exceptions.NoRegionError: You must specify a region.
```

**Root cause (a Test bug, per the categorization):** these test files import the
handler's `app.py` at module load (`from handler.<name>.app import lambda_handler`),
which instantiates a boto3 DynamoDB resource at import time. The test files do
NOT set `AWS_DEFAULT_REGION`/`AWS_REGION` before that import and do NOT wrap it
in `moto`, so in CI (no region configured) boto3 raises `NoRegionError` and the
file is interrupted during collection — its tests never run and are counted as
neither passed nor failed. This violates `.kiro/steering/testing-backend.md`
(set region + dummy creds before import; prefer the `_load_handler` importlib
pattern; avoid bare `sys.path` + `import app`).

### Confirmed collection errors (from console log) — FIXED

- `backend/tests/unit/test_get_member_self.py` — `NoRegionError` (no region env
  set, `sys.path.insert` + `from handler...app import`). **Fixed**: set
  `AWS_DEFAULT_REGION` + dummy creds before import.
- `backend/tests/unit/test_get_members_filtered.py` — `NoRegionError`. **Fixed**
  the same way.

Verified under CI-like conditions (region unset): both collect and pass
(21 tests). A full `--co` sweep of `tests/unit` (region unset) then confirmed
**0 remaining `NoRegionError`** across 1755 collected tests.

### Additional collection error found during the sweep (TEST-ISOLATION BUG) — FIXED

- `backend/tests/unit/test_event_dedup.py` — `ModuleNotFoundError: No module
  named 'shared.event_dedup'`. **Not stale** (an earlier note misclassified it):
  the module exists at `scripts/shared/event_dedup.py`. The failure is a package
  name collision — the auth layer also ships a `shared` package, and whichever is
  imported first shadows the other in `sys.modules`. The test passed in isolation
  (38 tests) but failed in the full suite. **Fixed** by loading the module
  directly by file path via `importlib` (unique name `scripts_event_dedup`).
  Verified: 0 collection errors across the full unit sweep (1793 tests).

### At-risk (import handler, no region env, no moto) — VERIFY EACH

Static scan found **16** test files matching the risky pattern (some may still
collect via a `conftest.py`/autouse fixture — confirm by running each locally):

```
test_admin_get_orders.py          test_admin_properties.py
test_admin_record_payment.py      test_cognito_custom_message_locale.py
test_cognito_role_assignment.py   test_create_member.py
test_create_order.py              test_export_members.py
test_generate_order_pdf.py        test_get_customer_orders.py
test_get_member_self.py           test_hdcn_cognito_admin.py
test_i18n_email.py                test_registry_properties.py
test_stub_validity.py             test_update_member.py
```

### Two problems to fix

1. **Test bug (code-quality)**: add the region/credential env setup before
   handler import (or refactor to the `_load_handler` + moto pattern) in the
   affected files so they collect and run.
2. **CI-reporting bug (infrastructure)**: `full-test-suite.yml` counts a
   collection error (pytest exit 2) as "passed" and only uploads a one-line
   summary. It should (a) treat non-zero pytest exit as a failure/error, and
   (b) capture full per-file output into the artifact, so future scans can
   actually see errors. The prompt's Step-5 analysis assumes a populated
   `failed_tests` array + full output that this workflow does not produce.

> Correction: an earlier draft of this section reported "0 failures / nothing to
> fix" based on the misleading one-line summary. That was wrong — there are real
> collection errors the summary concealed. Frontend (145/145) appears genuinely
> clean, but the backend result cannot be trusted until the CI reporting is fixed
> and the suite re-run.

### Trustworthy re-run results (run 34709680003, after CI-reporting fix)

Once the reporting bug (P1.2) and the `set -e` early-abort bug (P1.6) were fixed
and the stale test (P1.7) rewritten, a full re-run gave the FIRST honest numbers:

| Suite    | Total | Passed | Failed | Errors |
| -------- | ----- | ------ | ------ | ------ |
| Backend  | 139   | 121    | 9      | 9      |
| Frontend | 145   | 133    | 12     | 0      |

So ~30 problem files were being completely hidden by the old reporting.

**Backend collection errors (7) — same `NoRegionError` root cause as P1.1**
(handler builds boto3 resource at import; test imports it without setting a
region). 234 `NoRegionError` occurrences in the output. Files:
```
tests/unit/test_admin_get_orders.py
tests/unit/test_admin_record_payment.py
tests/unit/test_cognito_role_assignment.py
tests/unit/test_create_member.py
tests/unit/test_export_members.py
tests/unit/test_hdcn_cognito_admin.py
tests/unit/test_update_member.py
tests/integration/test_member_reporting_integration.py   (also collection error)
```

**Backend test failures / timeout (need triage — real bug vs test bug vs stale):**
```
tests/test_runner_utils.py (exit 5 — no tests collected?)
tests/unit/test_bulk_transition_members.py
tests/unit/test_cognito_post_authentication.py
tests/unit/test_create_order.py
tests/unit/test_get_customer_orders.py
tests/unit/test_hdcn_cognito_admin_split.py
tests/unit/test_stub_validity.py
tests/unit/test_sync_google_calendar.py
tests/unit/test_update_order_items.py
tests/unit/test_product_soft_delete.py (TIMEOUT >120s)
```

**Frontend failures (12) — need triage:**
```
src/__tests__/i18n/localeSync.property.test.ts
src/__tests__/i18n/translationFileConventions.test.ts
src/components/__tests__/MemberAdminTable.test.tsx
src/components/__tests__/MemberEditView.test.tsx
src/components/auth/__tests__/AuthenticationIntegration.test.tsx
src/components/auth/__tests__/PasswordlessAuthenticationFlow.test.tsx
src/config/memberFields/__tests__/memberFields.integrity.test.ts
src/modules/eventBooking/__tests__/BookingWizard.test.tsx
src/modules/products/__tests__/ProductCard.test.tsx
src/modules/webshop/__tests__/VariantSelector.test.tsx
src/modules/webshop/__tests__/WebshopPage.test.tsx (TIMEOUT >60s)
src/pages/__tests__/Dashboard.events-calendar.test.tsx
```

> These were pre-existing failures masked by the broken reporting, NOT regressions
> introduced by this work. The CI-reporting + collection fixes simply made them
> visible. Triage tracked as tasks P1.9 / P1.10.
