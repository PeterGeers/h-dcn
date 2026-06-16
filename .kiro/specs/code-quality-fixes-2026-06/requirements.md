# Code Quality Scan — June 2026

Scan date: 2026-06-16

## Summary

| Category                          | Findings                                                                 |
| --------------------------------- | ------------------------------------------------------------------------ |
| Files over 1000 lines (ERROR)     | 0 backend, 0 frontend                                                    |
| Files over 500 lines (WARNING)    | 11 backend, 22 frontend                                                  |
| Backend handlers without tests    | 41 handlers                                                              |
| Frontend dead code (unused files) | 6 utils files                                                            |
| Backend dead code                 | 3 unused imports + 9 stale migration templates + 9 corrupt `__init__.py` |
| Stale documentation               | 10 docs older than 3 months referencing code                             |
| Broken/stale tests                | 25 backend (all scan_product) + 22 frontend (6 suites)                   |

## 1. File Length Violations

### Backend (>500 lines)

| File                                                            | Lines | Severity                       |
| --------------------------------------------------------------- | ----- | ------------------------------ |
| `backend/handler/generate_order_pdf/tests/test_properties.py`   | 970   | ⚠️ WARNING (test file, exempt) |
| `backend/layers/auth-layer/python/shared/role_permissions.py`   | 940   | ⚠️ WARNING                     |
| `backend/handler/update_member/app.py`                          | 913   | ⚠️ WARNING                     |
| `backend/handler/hdcn_cognito_admin/role_operations.py`         | 909   | ⚠️ WARNING                     |
| `backend/layers/auth-layer/python/shared/product_validation.py` | 680   | ⚠️ WARNING                     |
| `backend/handler/generate_order_pdf/app.py`                     | 629   | ⚠️ WARNING                     |
| `backend/handler/cognito_role_assignment/app.py`                | 626   | ⚠️ WARNING                     |
| `backend/layers/auth-layer/python/shared/auth_utils.py`         | 617   | ⚠️ WARNING                     |
| `backend/handler/mollie_webhook/app.py`                         | 573   | ⚠️ WARNING                     |
| `backend/handler/hdcn_cognito_admin/user_operations.py`         | 561   | ⚠️ WARNING                     |
| `backend/handler/pay_order/app.py`                              | 556   | ⚠️ WARNING                     |

### Frontend (>500 lines)

| File                                                                 | Lines | Severity                         |
| -------------------------------------------------------------------- | ----- | -------------------------------- |
| `frontend/src/modules/products/components/ProductCard.tsx`           | 751   | ⚠️ WARNING                       |
| `frontend/src/modules/webshop/WebshopPage.tsx`                       | 746   | ⚠️ WARNING                       |
| `frontend/src/pages/MembershipManagement.tsx`                        | 721   | ⚠️ WARNING                       |
| `frontend/src/components/NewMemberApplicationForm.tsx`               | 706   | ⚠️ WARNING                       |
| `frontend/src/components/MemberEditView.tsx`                         | 704   | ⚠️ WARNING                       |
| `frontend/src/utils/functionPermissions.ts`                          | 701   | ⚠️ WARNING                       |
| `frontend/src/components/MemberAdminTable.tsx`                       | 699   | ⚠️ WARNING                       |
| `frontend/src/modules/members/components/MemberEditModal.tsx`        | 696   | ⚠️ WARNING                       |
| `frontend/src/services/DataProcessingService.ts`                     | 663   | ⚠️ WARNING                       |
| `frontend/src/config/memberFields/modalConfig.ts`                    | 656   | ⚠️ WARNING (config file, exempt) |
| `frontend/src/services/GoogleMailService.ts`                         | 622   | ⚠️ WARNING                       |
| `frontend/src/modules/presmeet/components/AdminDashboard.tsx`        | 588   | ⚠️ WARNING                       |
| `frontend/src/modules/products/components/OrderItemFieldsEditor.tsx` | 560   | ⚠️ WARNING                       |
| `frontend/src/components/reporting/GoogleMailIntegration.tsx`        | 559   | ⚠️ WARNING                       |
| `frontend/src/modules/presmeet/components/BookingWizard.tsx`         | 556   | ⚠️ WARNING                       |
| `frontend/src/services/MemberExportService.ts`                       | 540   | ⚠️ WARNING                       |
| `frontend/src/modules/products/ProductManagementPage.tsx`            | 521   | ⚠️ WARNING                       |
| `frontend/src/components/reporting/AddressLabelGenerator.tsx`        | 519   | ⚠️ WARNING                       |
| `frontend/src/components/auth/CustomAuthenticator.tsx`               | 508   | ⚠️ WARNING                       |
| `frontend/src/modules/webshop/components/CheckoutModal.tsx`          | 506   | ⚠️ WARNING                       |
| `frontend/src/modules/products/components/VariantSchemaEditor.tsx`   | 503   | ⚠️ WARNING                       |
| `frontend/src/components/reporting/AnalyticsSection.tsx`             | 502   | ⚠️ WARNING                       |

## 2. Missing Tests

### Backend handlers without test coverage (41)

| Handler                       | Priority                                        |
| ----------------------------- | ----------------------------------------------- |
| `admin_bulk_create_variants`  | HIGH (recently changed)                         |
| `admin_confirm_payment`       | MEDIUM                                          |
| `admin_delete_product`        | MEDIUM                                          |
| `admin_export_report`         | MEDIUM                                          |
| `admin_generate_report`       | MEDIUM                                          |
| `admin_get_payments`          | LOW                                             |
| `admin_get_products`          | LOW                                             |
| `admin_get_report`            | LOW                                             |
| `admin_get_stock_movements`   | MEDIUM                                          |
| `admin_lock_orders`           | LOW (tested in `test_admin_lock_unlock_orders`) |
| `admin_unlock_order`          | LOW (tested in `test_admin_lock_unlock_orders`) |
| `admin_update_order_status`   | MEDIUM                                          |
| `assign_club`                 | MEDIUM                                          |
| `cognito_post_authentication` | MEDIUM                                          |
| `cognito_pre_signup`          | MEDIUM                                          |
| `cognito_user_migration`      | LOW                                             |
| `create_membership`           | LOW                                             |
| `delete_event`                | LOW                                             |
| `delete_member`               | LOW                                             |
| `delete_membership`           | LOW                                             |
| `delete_payment`              | LOW                                             |
| `delete_product`              | LOW                                             |
| `get_club_registry`           | LOW                                             |
| `get_event_byid`              | LOW                                             |
| `get_events`                  | LOW                                             |
| `get_member_byid`             | LOW                                             |
| `get_member_payments`         | LOW                                             |
| `get_membership_byid`         | LOW                                             |
| `get_memberships`             | LOW                                             |
| `get_order_byid`              | LOW                                             |
| `get_payment_byid`            | LOW                                             |
| `get_payments`                | LOW                                             |
| `insert_product`              | LOW                                             |
| `pay_order`                   | HIGH (recently changed, 556 lines)              |
| `s3_file_manager`             | MEDIUM                                          |
| `shared`                      | N/A (helper module)                             |
| `update_membership`           | LOW                                             |
| `update_order_status`         | LOW                                             |
| `update_parameters`           | LOW                                             |
| `update_payment`              | LOW                                             |
| `upload_image`                | LOW                                             |

### Frontend untested services (4)

- `apiService.ts` — general API service
- `DataProcessingService.example.ts` — example file (low priority)
- `googleAuthService.ts` — Google auth helper
- `MemberService.ts` — member CRUD service

### Frontend untested utils (9, 6 confirmed dead)

- `blockPasswordManagers.ts` — **DEAD CODE** (0 imports)
- `dynamoService.ts` — **DEAD CODE** (0 imports)
- `membershipTypeMapper.ts` — **DEAD CODE** (0 imports)
- `permissionHelpers.ts` — **DEAD CODE** (0 imports)
- `statusTranslation.ts` — **DEAD CODE** (0 imports)
- `webauthnConfig.ts` — **DEAD CODE** (0 imports)
- `api.ts` — untested (but used)
- `apiService.ts` — untested
- `emailService.ts` — untested (14 references)

### Frontend untested hooks (6)

- `useAdminLocale.ts`
- `useAuth.ts`
- `useGoogleMailIntegration.ts`
- `useMemberExport.ts`
- `useMembers.ts`
- `useWebWorkers.ts`

## 3. Dead Code

### Backend

**Unused imports** (vulture, 90% confidence):

- `backend/handler/hdcn_cognito_admin/app.py:60` — `check_role_permission`, `get_role_summary`, `get_user_field_permissions`

**Stale migration template files** (9 files — leftover from auth layer migration):

- `backend/handler/delete_payment/delete_payment_migration_template.py`
- `backend/handler/get_customer_orders/get_customer_orders_migration_template.py`
- `backend/handler/get_orders/get_orders_migration_template.py`
- `backend/handler/get_order_byid/get_order_byid_migration_template.py`
- `backend/handler/hdcn_cognito_admin/hdcn_cognito_admin_migration_template.py`
- `backend/handler/update_member/update_member_migration_template.py`
- `backend/handler/update_order_status/update_order_status_migration_template.py`
- `backend/handler/update_payment/update_payment_migration_template.py`
- `backend/handler/update_product/update_product_migration_template.py`

**Corrupt `__init__.py` files** (contain null bytes, 9 files):

- `backend/handler/delete_member/__init__.py`
- `backend/handler/get_events/__init__.py`
- `backend/handler/get_members/__init__.py`
- `backend/handler/get_memberships/__init__.py`
- `backend/handler/get_member_byid/__init__.py`
- `backend/handler/get_member_payments/__init__.py`
- `backend/handler/get_orders/__init__.py`
- `backend/handler/get_order_byid/__init__.py`
- `backend/handler/update_order_status/__init__.py`

### Frontend

**Completely unused util files** (0 imports anywhere in codebase):

- `frontend/src/utils/blockPasswordManagers.ts`
- `frontend/src/utils/dynamoService.ts`
- `frontend/src/utils/membershipTypeMapper.ts`
- `frontend/src/utils/permissionHelpers.ts`
- `frontend/src/utils/statusTranslation.ts`
- `frontend/src/utils/webauthnConfig.ts`

## 4. Stale Documentation

Docs older than 3 months that reference backend/frontend code:

| File                                                           | Last Modified | Action                   |
| -------------------------------------------------------------- | ------------- | ------------------------ |
| `docs/FOLDER_REORGANIZATION_2026-01-18.md`                     | 2026-01-18    | Archive (completed task) |
| `docs/architecture/bucket-separation-strategy.md`              | 2025-12-30    | Review if still relevant |
| `docs/archive/auth_layer_alignment_check.md`                   | 2026-01-08    | Already archived ✓       |
| `docs/archive/member_self_service_field_alignment.md`          | 2026-01-14    | Already archived ✓       |
| `docs/archive/members_me_self_service_enhancement_proposal.md` | 2026-01-12    | Already archived ✓       |
| `docs/archive/role_migration_plan.md`                          | 2026-01-08    | Already archived ✓       |
| `docs/archive/SMART_FALLBACK_PATTERN.md`                       | 2026-01-13    | Already archived ✓       |
| `docs/archive/test-task-buttons.md`                            | 2026-01-08    | Already archived ✓       |
| `docs/fixes/membership-dropdown-parameter-table-fix.md`        | 2025-12-30    | Archive (completed fix)  |
| `docs/fixes/parameter-system-fix.md`                           | 2025-12-30    | Archive (completed fix)  |

## 5. Broken/Stale Tests

**CI reports "success" but tests are failing** — workflow uses `continue-on-error` or custom exit handling.

### Backend: 25 failed, 1190 passed, 21 skipped, 7 xfailed (33 min)

All 25 failures are in `scan_product`-related tests. Root cause: the `scan_product` handler was recently refactored (2026-06-16) and tests haven't been updated to match.

| Test File                                          | Failures                            | Error Pattern                                             | Category                             |
| -------------------------------------------------- | ----------------------------------- | --------------------------------------------------------- | ------------------------------------ |
| `test_scan_product.py` (6 tests)                   | `KeyError: 0`                       | Tests access `response['body']` as JSON but get 500 error | **Stale test** — handler API changed |
| `test_property_scan_product.py` (7 tests)          | `assert 500 == 200` / `KeyError: 0` | Same pattern with property-based tests                    | **Stale test** — handler API changed |
| `test_scan_product_bug_condition.py` (4 tests)     | `assert 500 == 200`                 | Handler returns 500 instead of 200                        | **Real bug** or **stale test**       |
| `test_scan_product_preservation.py` (5 tests)      | `assert 500 == 200` / `KeyError: 0` | Same pattern                                              | **Stale test** — handler API changed |
| `test_product_unification_properties.py` (3 tests) | Unknown (in full output)            | Likely same scan_product issue                            | **Stale test**                       |

**Diagnosis**: `scan_product/app.py` was modified on 2026-06-16 18:28. The tests expect the old response format. Either:

- The handler now returns 500 due to a bug introduced in the refactor
- The tests assume an old response shape that changed

### Frontend: 6 suites failed, 22 tests failed, 103 passed, 1394 total

| Test File                                                 | Failures                                                                               | Error Pattern                            | Category                         |
| --------------------------------------------------------- | -------------------------------------------------------------------------------------- | ---------------------------------------- | -------------------------------- |
| `memberReportingIntegration.test.tsx` (15 tests)          | `Cannot read properties of undefined (reading 'length')` at `MemberDataService.ts:116` | Mock doesn't match new service interface | **Stale test** — service changed |
| `integration/memberReportingIntegration.test.ts` (1 test) | Same as above                                                                          | Duplicate test file, same issue          | **Stale test**                   |
| `WebWorkerManager.test.ts` (1 test)                       | Task execution test failing                                                            | Likely mock/environment issue            | **Test bug**                     |
| `AnalyticsService.test.ts` (4 tests)                      | Statistics generation failing                                                          | Service API changed                      | **Stale test**                   |
| `PresMeetPage.preservation.test.tsx` (1 test)             | 403 authorization error handling                                                       | Component behavior changed               | **Stale test**                   |
| `clubSearch.property.test.ts` (suite failed to run)       | Import/parse error                                                                     | **Test bug** — broken import             |
