# Code Quality Fixes — June 2026 Tasks

## Group 1: Dead Code Removal (Quick Wins)

### Task 1.1: Delete unused frontend util files

- [ ] Delete `frontend/src/utils/blockPasswordManagers.ts`
- [ ] Delete `frontend/src/utils/dynamoService.ts`
- [ ] Delete `frontend/src/utils/membershipTypeMapper.ts`
- [ ] Delete `frontend/src/utils/permissionHelpers.ts`
- [ ] Delete `frontend/src/utils/statusTranslation.ts`
- [ ] Delete `frontend/src/utils/webauthnConfig.ts`
- [ ] Verify no barrel export (`index.ts`) references them
- [ ] Run `npx tsc --noEmit` to confirm no breakage

### Task 1.2: Remove unused backend imports

- [ ] In `backend/handler/hdcn_cognito_admin/app.py` line 60, remove unused imports: `check_role_permission`, `get_role_summary`, `get_user_field_permissions`
- [ ] Run `pytest tests/unit/test_hdcn_cognito_admin.py -q` to verify

### Task 1.3: Delete stale migration template files

- [ ] Delete all 9 `*_migration_template.py` files:
  - `backend/handler/delete_payment/delete_payment_migration_template.py`
  - `backend/handler/get_customer_orders/get_customer_orders_migration_template.py`
  - `backend/handler/get_orders/get_orders_migration_template.py`
  - `backend/handler/get_order_byid/get_order_byid_migration_template.py`
  - `backend/handler/hdcn_cognito_admin/hdcn_cognito_admin_migration_template.py`
  - `backend/handler/update_member/update_member_migration_template.py`
  - `backend/handler/update_order_status/update_order_status_migration_template.py`
  - `backend/handler/update_payment/update_payment_migration_template.py`
  - `backend/handler/update_product/update_product_migration_template.py`

### Task 1.4: Fix corrupt `__init__.py` files

- [ ] Replace all 9 null-byte `__init__.py` files with empty files (or delete if not needed):
  - `backend/handler/delete_member/__init__.py`
  - `backend/handler/get_events/__init__.py`
  - `backend/handler/get_members/__init__.py`
  - `backend/handler/get_memberships/__init__.py`
  - `backend/handler/get_member_byid/__init__.py`
  - `backend/handler/get_member_payments/__init__.py`
  - `backend/handler/get_orders/__init__.py`
  - `backend/handler/get_order_byid/__init__.py`
  - `backend/handler/update_order_status/__init__.py`

---

## Group 2: File Length — Backend Refactoring (High Priority)

### Task 2.1: Refactor `update_member/app.py` (913 lines)

- [ ] Extract validation logic into `update_member/validators.py`
- [ ] Extract field-update helpers into `update_member/field_updates.py`
- [ ] Keep `app.py` under 500 lines with only `lambda_handler` + orchestration
- [ ] Run `pytest tests/unit/test_update_member.py -q`

### Task 2.2: Refactor `hdcn_cognito_admin/role_operations.py` (909 lines)

- [ ] Split into logical units (role CRUD, permission mapping, group management)
- [ ] Target: each file ≤500 lines
- [ ] Run `pytest tests/unit/test_hdcn_cognito_admin.py -q`

### Task 2.3: Refactor `role_permissions.py` (940 lines)

- [ ] Split permission definitions from permission logic
- [ ] Consider moving large permission maps to a config/data file
- [ ] Run `pytest tests/unit/test_role_permissions_consolidation.py -q`

### Task 2.4: Refactor `cognito_role_assignment/app.py` (626 lines)

- [ ] Extract role assignment logic from the handler entry point
- [ ] Target: ≤500 lines
- [ ] Run `pytest tests/unit/test_cognito_role_assignment.py -q`

### Task 2.5: Refactor `generate_order_pdf/app.py` (629 lines)

- [ ] Extract PDF template/formatting logic into helper modules
- [ ] Target: ≤500 lines
- [ ] Run `pytest tests/unit/test_generate_order_pdf.py -q`

---

## Group 3: File Length — Frontend Refactoring (High Priority)

### Task 3.1: Refactor `ProductCard.tsx` (751 lines)

- [ ] Extract variant display logic into sub-components
- [ ] Extract price/stock display into separate component
- [ ] Target: ≤500 lines

### Task 3.2: Refactor `WebshopPage.tsx` (746 lines)

- [ ] Extract filter logic into custom hook
- [ ] Extract product grid into separate component
- [ ] Target: ≤500 lines

### Task 3.3: Refactor `MembershipManagement.tsx` (721 lines)

- [ ] Extract table/list view into sub-component
- [ ] Extract form/modal logic into separate component
- [ ] Target: ≤500 lines

### Task 3.4: Refactor `NewMemberApplicationForm.tsx` (706 lines)

- [ ] Extract form sections into sub-components
- [ ] Move validation schema to separate file
- [ ] Target: ≤500 lines

### Task 3.5: Refactor `MemberEditView.tsx` (704 lines)

- [ ] Extract tab content into sub-components
- [ ] Target: ≤500 lines

### Task 3.6: Refactor `MemberAdminTable.tsx` (699 lines)

- [ ] Extract column definitions into config
- [ ] Extract row actions into sub-component
- [ ] Target: ≤500 lines

### Task 3.7: Refactor `MemberEditModal.tsx` (696 lines)

- [ ] Extract form sections into sub-components
- [ ] Share logic with MemberEditView where possible
- [ ] Target: ≤500 lines

### Task 3.8: Refactor `DataProcessingService.ts` (663 lines)

- [ ] Split into domain-specific processing modules
- [ ] Target: ≤500 lines

### Task 3.9: Refactor `GoogleMailService.ts` (622 lines)

- [ ] Extract template rendering from API integration
- [ ] Target: ≤500 lines

---

## Group 4: Broken/Stale Tests — Backend (All scan_product)

### Task 4.1: Diagnose `scan_product` handler 500 errors

- [ ] Read `backend/handler/scan_product/app.py` (modified 2026-06-16)
- [ ] Identify what changed vs what the tests expect
- [ ] Determine: is the handler broken (real bug) or did the API intentionally change (stale tests)?

### Task 4.2: Fix `test_scan_product.py` (6 failures)

- [ ] Fix `test_returns_canonical_dutch_fields` — `assert 500 == 200`
- [ ] Fix `test_naam_fallback_from_legacy_name` — `KeyError: 0`
- [ ] Fix `test_prijs_fallback_from_legacy_price` — `KeyError: 0`
- [ ] Fix `test_naam_preferred_over_legacy_name` — `KeyError: 0`
- [ ] Fix `test_prijs_preferred_over_legacy_price` — `KeyError: 0`
- [ ] Fix `test_event_ids_returned_as_list` — `KeyError: 0`
- [ ] Fix `test_excludes_variant_records` / `test_excludes_migration_source_records` / `test_includes_records_without_is_parent`

### Task 4.3: Fix `test_property_scan_product.py` (7 failures)

- [ ] Update property tests to match new handler response format
- [ ] Fix `TestProperty6ScanProductNormalization` (4 tests)
- [ ] Fix `TestProperty7ScanProductFiltering` (3 tests)

### Task 4.4: Fix `test_scan_product_bug_condition.py` (4 failures)

- [ ] Fix or remove if bug conditions are resolved: `test_response_includes_groep_field`, `test_response_includes_subgroep_field`, `test_response_includes_images_field`, `test_all_three_fields_present_together`

### Task 4.5: Fix `test_scan_product_preservation.py` (5 failures)

- [ ] Update to match current handler API
- [ ] Fix: `test_existing_seven_fields_are_returned`, `test_product_id_preserved_exactly`, `test_decimal_to_number_conversion`, `test_name_fallback_logic_preserved`, `test_is_parent_and_active_preserved`

---

## Group 5: Broken/Stale Tests — Frontend (6 suites, 22 tests)

### Task 5.1: Fix `memberReportingIntegration.test.tsx` (15 failures)

- [ ] Root cause: `MemberDataService.ts:116` — `Cannot read properties of undefined (reading 'length')`
- [ ] The mock likely returns wrong structure; update mock to match current `fetchMembers` response shape
- [ ] Fix all 15 tests (Regional flow, Cache tests, Performance, Error handling, Calculated fields)
- [ ] Also fix duplicate `integration/memberReportingIntegration.test.ts` (1 failure, same issue)

### Task 5.2: Fix `AnalyticsService.test.ts` (4 failures)

- [ ] Fix `generateOverview`, `generateRegionalStats`, `generateAgeViolinData`, `generateMembershipViolinData`
- [ ] Likely the AnalyticsService interface changed — update test mocks/assertions

### Task 5.3: Fix `WebWorkerManager.test.ts` (1 failure)

- [ ] Fix `should execute regional filter task successfully`
- [ ] Likely environment/mock issue with Web Workers in test environment

### Task 5.4: Fix `PresMeetPage.preservation.test.tsx` (1 failure)

- [ ] Fix `shows onboarding flow when 403 indicates missing club assignment`
- [ ] Component behavior or error handling likely changed

### Task 5.5: Fix `clubSearch.property.test.ts` (suite failed to run)

- [ ] Fix broken import or parse error preventing suite from running

---

## Group 6: Missing Tests — High Priority Handlers

### Task 6.1: Add test for `pay_order` handler

- [ ] Create `backend/tests/unit/test_pay_order.py`
- [ ] Test successful payment flow
- [ ] Test validation failures (missing fields, invalid order state)
- [ ] Test permission checks

### Task 6.2: Add test for `admin_bulk_create_variants` handler

- [ ] Create `backend/tests/unit/test_admin_bulk_create_variants.py`
- [ ] Test bulk creation with valid data
- [ ] Test validation of variant schema
- [ ] Test permission checks

### Task 6.3: Add test for `admin_confirm_payment` handler

- [ ] Create `backend/tests/unit/test_admin_confirm_payment.py`
- [ ] Test manual payment confirmation
- [ ] Test already-confirmed order

### Task 6.4: Add test for `admin_update_order_status` handler

- [ ] Create `backend/tests/unit/test_admin_update_order_status.py`
- [ ] Test valid status transitions
- [ ] Test invalid transitions (state machine)
- [ ] Test permission checks

### Task 6.5: Add test for `cognito_pre_signup` handler

- [ ] Create `backend/tests/unit/test_cognito_pre_signup.py`
- [ ] Test Google SSO linking logic
- [ ] Test duplicate email detection
- [ ] Test race condition handling

### Task 6.6: Add test for `s3_file_manager` handler

- [ ] Create `backend/tests/unit/test_s3_file_manager.py`
- [ ] Test upload presigned URL generation
- [ ] Test file listing
- [ ] Test permission checks

---

## Group 7: Missing Tests — Medium Priority Handlers

### Task 7.1: Add tests for remaining admin handlers

- [ ] `admin_delete_product` — test soft-delete behavior
- [ ] `admin_export_report` — test report generation
- [ ] `admin_generate_report` — test data aggregation
- [ ] `admin_get_stock_movements` — test filtering/pagination

### Task 7.2: Add tests for Cognito triggers

- [ ] `cognito_post_authentication` — test post-auth actions
- [ ] `cognito_user_migration` — test user migration flow
- [ ] `assign_club` — test club assignment logic

---

## Group 8: Stale Documentation

### Task 8.1: Archive completed documentation

- [ ] Move `docs/FOLDER_REORGANIZATION_2026-01-18.md` to `docs/archive/`
- [ ] Move `docs/fixes/membership-dropdown-parameter-table-fix.md` to `docs/archive/`
- [ ] Move `docs/fixes/parameter-system-fix.md` to `docs/archive/`
- [ ] If `docs/fixes/` is now empty, remove the directory

### Task 8.2: Review `bucket-separation-strategy.md`

- [ ] Check if the bucket separation described is still the current architecture
- [ ] Update or archive if outdated

---

## Group 9: Frontend Dead Code (Services)

### Task 9.1: Review `DataProcessingService.example.ts`

- [ ] If this is truly an example/template, delete it
- [ ] If it contains useful patterns, move to docs or convert to actual implementation

---

## Priority Order

1. **Group 1** (Dead code removal) — Quick wins, zero risk, immediate cleanup
2. **Group 4** (Fix broken backend tests) — All scan_product, single root cause
3. **Group 5** (Fix broken frontend tests) — 6 suites, mostly stale mocks
4. **Group 2, Tasks 2.1–2.3** (Backend >900 lines) — Highest complexity debt
5. **Group 3, Tasks 3.1–3.3** (Frontend >700 lines) — Most impactful UI debt
6. **Group 6** (Missing tests for critical handlers) — Safety net
7. **Group 8** (Stale docs) — Quick housekeeping
8. **Groups 7, 9** (Lower priority tests, dead services) — Incremental improvement
