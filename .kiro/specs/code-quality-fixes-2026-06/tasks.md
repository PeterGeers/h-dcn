# Code Quality Fixes — June 2026 Tasks

Priority order: broken tests → dead code → file length → missing tests → stale docs

---

## Priority 1: Broken Tests (fix test infrastructure)

### Backend

- [x] **Task 1.1** — Fix `scan_product` test table setup (25 tests)
  - Files: `backend/tests/unit/test_scan_product.py`, `test_property_scan_product.py`, `test_scan_product_bug_condition.py`, `test_scan_product_preservation.py`
  - Root cause: Moto mock table not found — handler likely uses `os.environ.get('PRODUCTS_TABLE_NAME', 'Producten')` but tests don't set the env var or create the table with the right name
  - Fix: Ensure `PRODUCTS_TABLE_NAME` is set and table is created inside `mock_aws()` context before handler load
  - Category: **Test bug**

- [x] **Task 1.2** — Fix `test_create_default_variant_creates_correct_record` (1 test)
  - File: `backend/tests/integration/test_admin_endpoints.py:303`
  - Root cause: Asserts `variant['price']` but field was renamed to `prijs`
  - Fix: Change assertion to use `prijs` (canonical Dutch field name per registry)
  - Category: **Stale test**

### Frontend

- [x] **Task 1.3** — Fix `memberReportingIntegration` tests (15 tests, 2 files)
  - Files: `frontend/src/__tests__/memberReportingIntegration.test.tsx`, `frontend/src/__tests__/integration/memberReportingIntegration.test.ts`
  - Root cause: Mock response shape doesn't match current `MemberDataService.fetchMembers()` — service accesses `.length` on undefined at line 116
  - Fix: Update mock to match current response structure (check what `fetchMembers` now returns)
  - Category: **Test bug**

- [x] **Task 1.4** — Fix `VariantEditModal` tests (6 tests)
  - File: `frontend/src/modules/products/__tests__/VariantEditModal.test.tsx`
  - Root cause: Placeholder texts `Bijv. Maat, Kleur...` and `Bijv. S, Rood, 42...` not found — component now uses i18n translation keys
  - Fix: Either add i18n mock that returns expected strings, or update test queries to match actual rendered text (check component's `useTranslation` keys)
  - Category: **Test bug**

- [x] **Task 1.5** — Fix `EventSelector` tests (6 tests) ✓ Already resolved (component + test deleted in event_id removal spec)
  - File: `frontend/src/modules/products/__tests__/EventSelector.test.tsx`
  - Root cause: Component refactored (likely event_id removal spec) — "Webshop (algemeen)" text gone, event ordering changed, onChange callback args changed
  - Fix: Rewrite tests to match current component behavior
  - Category: **Stale test** — delete and rewrite

- [x] **Task 1.6** — Fix `ProductCard` test (1 test)
  - File: `frontend/src/modules/products/__tests__/ProductCard.test.tsx`
  - Root cause: "Varianten" text not found — likely now uses translation key or conditional rendering changed
  - Fix: Check what the component renders for parent products and update assertion
  - Category: **Test bug**

- [x] **Task 1.7** — Fix `WebWorkerManager` test (1 test)
  - File: `frontend/src/services/__tests__/WebWorkerManager.test.ts`
  - Root cause: Worker initialization fails in jsdom environment — missing Worker/MessageChannel mock
  - Fix: Add proper Worker mock or mark as integration-only test
  - Category: **Test bug**

- [x] **Task 1.8** — Fix `AnalyticsService` tests (4 tests)
  - File: `frontend/src/services/__tests__/AnalyticsService.test.ts`
  - Root cause: Same `MemberDataService` mock issue as Task 1.3
  - Fix: Update mock response shape (will likely be resolved by Task 1.3 fix)
  - Category: **Test bug**

- [x] **Task 1.9** — Fix `PresMeetPage.preservation` test (1 test) ✓ Already resolved (module refactored/deleted)
  - File: `frontend/src/modules/presmeet/__tests__/PresMeetPage.preservation.test.tsx`
  - Root cause: Async 403 response handling shows spinner; test doesn't await state resolution
  - Fix: Add `waitFor` wrapper around `data-testid="onboarding-flow"` assertion
  - Category: **Test bug** (out of scope per steering — PresMeet module)

---

## Priority 2: Dead Code Cleanup

- [x] **Task 2.1** — Remove unused imports in `hdcn_cognito_admin/app.py`
  - Line 60: Remove `check_role_permission`, `get_role_summary`, `get_user_field_permissions` (moved to submodule but import left behind)

- [x] **Task 2.2** — Remove unused imports/variables in `generate_order_pdf/tests/`
  - `test_logo_fetch.py:3` — remove unused `pytest` import
  - `test_logo_fetch.py:5` — remove unused `ReadTimeoutError` import
  - `test_properties.py:8` — remove unused `pytest` import
  - `test_properties.py:772` — remove unused `mock_cors`, `mock_log` variables

- [x] **Task 2.3** — Delete stale migration template files (9 files)
  - All `*_migration_template.py` files have syntax errors and serve no purpose
  - Files: `delete_payment/`, `get_customer_orders/`, `get_orders/`, `get_order_byid/`, `hdcn_cognito_admin/`, `update_member/`, `update_order_status/`, `update_payment/`, `update_product/`

- [x] **Task 2.4** — Fix or delete null-byte `__init__.py` files (9 files)
  - These contain null bytes and can't be parsed — likely corrupted
  - Replace with empty files or delete if not needed (Lambda handlers don't need `__init__.py`)

---

## Priority 3: File Length (>700 lines — highest impact to refactor)

- [x] **Task 3.1** — Refactor `backend/handler/update_member/app.py` (913 lines) ✓ Already at 304 lines
  - Extract validation logic and field-specific update logic into helper modules

- [x] **Task 3.2** — Refactor `backend/handler/hdcn_cognito_admin/role_operations.py` (909 lines) ✓ Already split into sub-modules
  - Already split from main app.py — consider further splitting by operation type

- [x] **Task 3.3** — Refactor `frontend/src/modules/events/components/EventForm.tsx` (763 lines) ✓ Already at 462 lines
  - Extract form sections into sub-components

- [x] **Task 3.4** — Refactor `frontend/src/modules/webshop/WebshopPage.tsx` (761 lines) ✓ Already at 347 lines
  - Extract product list, filters, cart summary into sub-components

- [x] **Task 3.5** — Refactor `frontend/src/modules/products/components/ProductCard.tsx` (724 lines) ✓ Already at 456 lines
  - Extract variant sub-table, image section, action buttons into sub-components

- [x] **Task 3.6** — Refactor `frontend/src/pages/MembershipManagement.tsx` (721 lines)
  - Extract membership type list and form into separate components

---

## Priority 4: Missing Tests (high-priority handlers only)

- [x] **Task 4.1** — Add tests for `admin_bulk_create_variants`
- [x] **Task 4.2** — Add tests for `admin_delete_product`
- [x] **Task 4.3** — Add tests for `delete_member`
- [x] **Task 4.4** — Add tests for `insert_product`
- [x] **Task 4.5** — Add tests for `update_order_status`
- [x] **Task 4.6** — Add tests for `cognito_pre_signup` (security-critical)
- [x] **Task 4.7** — Add tests for `cognito_post_authentication` (security-critical)

---

## Priority 5: Stale Documentation

- [x] **Task 5.1** — Move completed fix docs to archive
  - `docs/fixes/membership-dropdown-parameter-table-fix.md` → `docs/archive/`
  - `docs/fixes/parameter-system-fix.md` → `docs/archive/`
  - `docs/data-management/image-recovery-plan.md` → `docs/archive/`
  - `docs/data-management/image-restoration-completed.md` → `docs/archive/`
  - `docs/FOLDER_REORGANIZATION_2026-01-18.md` → `docs/archive/`

- [x] **Task 5.2** — Review `docs/architecture/bucket-separation-strategy.md`
  - Last updated Dec 2025 — verify it reflects current S3 bucket setup

---

## Summary

| Category                | Items                                                         | Effort |
| ----------------------- | ------------------------------------------------------------- | ------ |
| Broken tests (backend)  | 26 failures, 2 root causes                                    | ~2h    |
| Broken tests (frontend) | 35 failures, 7 root causes                                    | ~4h    |
| Dead code               | 8 unused imports/vars + 9 stale templates + 9 corrupted files | ~1h    |
| File length             | 6 high-priority refactors                                     | ~8h    |
| Missing tests           | 7 priority handlers                                           | ~6h    |
| Stale docs              | 5 files to archive, 1 to review                               | ~30min |

**Total estimated effort: ~21h**
