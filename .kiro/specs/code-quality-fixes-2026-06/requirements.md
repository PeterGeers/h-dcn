# Code Quality Scan — June 2026

**Run date:** 2026-06-25  
**Backend tests:** 28 failed / 1229 passed / 21 skipped (33 min)  
**Frontend tests:** 35 failed / 1478 passed (26s)

---

## 1. File Length Violations

### Backend (>500 lines, target 500, max 1000)

| Lines | File                                                            | Status                          |
| ----- | --------------------------------------------------------------- | ------------------------------- |
| 970   | `backend/handler/generate_order_pdf/tests/test_properties.py`   | ⚠️ Warning (test file — exempt) |
| 940   | `backend/layers/auth-layer/python/shared/role_permissions.py`   | ⚠️ Warning                      |
| 913   | `backend/handler/update_member/app.py`                          | ⚠️ Warning                      |
| 909   | `backend/handler/hdcn_cognito_admin/role_operations.py`         | ⚠️ Warning                      |
| 680   | `backend/layers/auth-layer/python/shared/product_validation.py` | ⚠️ Warning                      |
| 630   | `backend/handler/generate_preparation_pdf/app.py`               | ⚠️ Warning                      |
| 629   | `backend/handler/generate_order_pdf/app.py`                     | ⚠️ Warning                      |
| 626   | `backend/handler/cognito_role_assignment/app.py`                | ⚠️ Warning                      |
| 617   | `backend/layers/auth-layer/python/shared/auth_utils.py`         | ⚠️ Warning                      |
| 581   | `backend/handler/pay_order/app.py`                              | ⚠️ Warning                      |
| 573   | `backend/handler/mollie_webhook/app.py`                         | ⚠️ Warning                      |
| 561   | `backend/handler/hdcn_cognito_admin/user_operations.py`         | ⚠️ Warning                      |
| 542   | `backend/handler/admin_event_claims/app.py`                     | ⚠️ Warning                      |
| 515   | `backend/handler/submit_order/app.py`                           | ⚠️ Warning                      |
| 513   | `backend/handler/event_onboard/app.py`                          | ⚠️ Warning                      |

### Frontend (>500 lines)

| Lines | File                                                                 | Status                       |
| ----- | -------------------------------------------------------------------- | ---------------------------- |
| 763   | `frontend/src/modules/events/components/EventForm.tsx`               | ⚠️ Warning                   |
| 761   | `frontend/src/modules/webshop/WebshopPage.tsx`                       | ⚠️ Warning                   |
| 724   | `frontend/src/modules/products/components/ProductCard.tsx`           | ⚠️ Warning                   |
| 721   | `frontend/src/pages/MembershipManagement.tsx`                        | ⚠️ Warning                   |
| 706   | `frontend/src/components/NewMemberApplicationForm.tsx`               | ⚠️ Warning                   |
| 704   | `frontend/src/components/MemberEditView.tsx`                         | ⚠️ Warning                   |
| 701   | `frontend/src/utils/functionPermissions.ts`                          | ⚠️ Warning                   |
| 696   | `frontend/src/modules/members/components/MemberEditModal.tsx`        | ⚠️ Warning                   |
| 663   | `frontend/src/services/DataProcessingService.ts`                     | ⚠️ Warning                   |
| 656   | `frontend/src/config/memberFields/modalConfig.ts`                    | ⚠️ Warning (config — exempt) |
| 622   | `frontend/src/services/GoogleMailService.ts`                         | ⚠️ Warning                   |
| 591   | `frontend/src/modules/eventBooking/admin/AdminClaimsManagement.tsx`  | ⚠️ Warning                   |
| 591   | `frontend/src/components/MemberAdminTable.tsx`                       | ⚠️ Warning                   |
| 576   | `frontend/src/modules/eventBooking/components/BookingWizard.tsx`     | ⚠️ Warning                   |
| 562   | `frontend/src/modules/products/ProductManagementPage.tsx`            | ⚠️ Warning                   |
| 560   | `frontend/src/modules/products/components/OrderItemFieldsEditor.tsx` | ⚠️ Warning                   |
| 559   | `frontend/src/components/reporting/GoogleMailIntegration.tsx`        | ⚠️ Warning                   |
| 548   | `frontend/src/modules/eventBooking/pages/EventRegisterPage.tsx`      | ⚠️ Warning                   |
| 540   | `frontend/src/services/MemberExportService.ts`                       | ⚠️ Warning                   |
| 519   | `frontend/src/components/reporting/AddressLabelGenerator.tsx`        | ⚠️ Warning                   |
| 508   | `frontend/src/components/auth/CustomAuthenticator.tsx`               | ⚠️ Warning                   |
| 507   | `frontend/src/modules/webshop/components/CheckoutModal.tsx`          | ⚠️ Warning                   |
| 503   | `frontend/src/modules/eventBooking/admin/EventDashboard.tsx`         | ⚠️ Warning                   |
| 502   | `frontend/src/components/reporting/AnalyticsSection.tsx`             | ⚠️ Warning                   |

**No files exceed 1000 lines** — no critical errors.

---

## 2. Missing Tests

### Backend — 40 handlers without test files (out of 91 total = 44% uncovered)

Key gaps (non-trivial handlers without tests):

- `admin_bulk_create_variants`, `admin_confirm_payment`, `admin_delete_product`
- `admin_export_report`, `admin_generate_report`, `admin_get_payments`
- `admin_get_products`, `admin_get_stock_movements`, `admin_lock_orders`
- `admin_unlock_order`, `admin_update_order_status`
- `cognito_post_authentication`, `cognito_pre_signup`, `cognito_user_migration`
- `create_membership`, `delete_event`, `delete_member`, `delete_membership`, `delete_payment`, `delete_product`
- `get_club_registry`, `get_event_byid`, `get_events`, `get_member_byid`
- `get_member_payments`, `get_membership_byid`, `get_memberships`
- `get_order_byid`, `get_payment_byid`, `get_payments`
- `insert_product`, `s3_file_manager`
- `update_membership`, `update_order_status`, `update_parameters`, `update_payment`
- `upload_image`, `upload_registry_logo`

### Frontend — Not scanned (too many components to enumerate; focus on test failures instead)

---

## 3. Dead Code

### Vulture findings (≥80% confidence)

| File                                                          | Line | Issue                                      |
| ------------------------------------------------------------- | ---- | ------------------------------------------ |
| `backend/handler/generate_order_pdf/tests/test_logo_fetch.py` | 3    | unused import `pytest`                     |
| `backend/handler/generate_order_pdf/tests/test_logo_fetch.py` | 5    | unused import `ReadTimeoutError`           |
| `backend/handler/generate_order_pdf/tests/test_properties.py` | 8    | unused import `pytest`                     |
| `backend/handler/generate_order_pdf/tests/test_properties.py` | 772  | unused variable `mock_cors`                |
| `backend/handler/generate_order_pdf/tests/test_properties.py` | 772  | unused variable `mock_log`                 |
| `backend/handler/hdcn_cognito_admin/app.py`                   | 60   | unused import `check_role_permission`      |
| `backend/handler/hdcn_cognito_admin/app.py`                   | 60   | unused import `get_role_summary`           |
| `backend/handler/hdcn_cognito_admin/app.py`                   | 60   | unused import `get_user_field_permissions` |

### Stale migration templates (parse errors — broken/incomplete code)

These files have syntax errors and are likely leftover scaffolding:

- `backend/handler/delete_payment/delete_payment_migration_template.py`
- `backend/handler/get_customer_orders/get_customer_orders_migration_template.py`
- `backend/handler/get_orders/get_orders_migration_template.py`
- `backend/handler/get_order_byid/get_order_byid_migration_template.py`
- `backend/handler/hdcn_cognito_admin/hdcn_cognito_admin_migration_template.py`
- `backend/handler/update_member/update_member_migration_template.py`
- `backend/handler/update_order_status/update_order_status_migration_template.py`
- `backend/handler/update_payment/update_payment_migration_template.py`
- `backend/handler/update_product/update_product_migration_template.py`

### Null-byte `__init__.py` files (corrupted)

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

## 4. Stale Documentation

### Likely stale (last updated Dec 2025 – Jan 2026, 6+ months old)

| Last Modified | File                                                    | Risk                                 |
| ------------- | ------------------------------------------------------- | ------------------------------------ |
| 2025-12-30    | `docs/architecture/bucket-separation-strategy.md`       | May not reflect current S3 layout    |
| 2025-12-30    | `docs/data-management/image-recovery-plan.md`           | Completed action — archive candidate |
| 2025-12-30    | `docs/data-management/image-restoration-completed.md`   | Archive candidate                    |
| 2025-12-30    | `docs/deployment/powershell-tips.md`                    | Low risk                             |
| 2025-12-30    | `docs/fixes/membership-dropdown-parameter-table-fix.md` | Archive candidate                    |
| 2025-12-30    | `docs/fixes/parameter-system-fix.md`                    | Archive candidate                    |
| 2025-12-30    | `docs/infrastructure/custom-domain-setup.md`            | Low risk (infra rarely changes)      |
| 2026-01-18    | `docs/FOLDER_REORGANIZATION_2026-01-18.md`              | Archive candidate                    |

### Archive folder (all Jan 2026 or older)

The entire `docs/archive/` folder (8 files) is explicitly archival — no action needed.

---

## 5. Broken/Stale Tests

### Backend — 28 failures

**Root cause cluster A: `scan_product` handler — ResourceNotFoundException (25 failures)**

Tests: `test_scan_product.py`, `test_property_scan_product.py`, `test_scan_product_bug_condition.py`, `test_scan_product_preservation.py`

Error: `DynamoDB error in scan_product: ResourceNotFoundException - Requested resource not found`  
→ The moto mock table is not created/found. Tests access `body[0]` which fails as `KeyError: 0` because the response body is empty (handler returned 500).

**Diagnosis: Test bug** — The handler's DynamoDB table name likely changed (possibly from `Producten` to env-var based), and these tests don't set up the mock table correctly or load the handler outside `mock_aws()` context.

**Root cause cluster B: `test_create_default_variant_creates_correct_record` (1 failure)**

Error: `KeyError: 'price'`  
Test asserts `variant['price'] is None` but the field was renamed to `prijs` (Dutch canonical name per field registry).

**Diagnosis: Stale test** — Test references old field name `price` that was renamed to `prijs`.

**Root cause cluster C: `test_normalized_response_includes_all_required_fields` (2 failures from property tests)**

Error: `assert 500 == 200` — Same underlying ResourceNotFoundException.

**Diagnosis: Same as cluster A** — test infrastructure issue.

---

### Frontend — 35 failures across 8 test suites

**Cluster 1: memberReportingIntegration (2 files, ~15 tests)**

Error: `TypeError: Cannot read properties of undefined (reading 'length')` at `MemberDataService.ts:116`  
→ The mock doesn't return the expected response shape. Service tries to access `.length` on undefined.

**Diagnosis: Test bug** — Mock response shape doesn't match current `MemberDataService.fetchMembers()` implementation (likely the response wrapper changed).

**Cluster 2: VariantEditModal (6 tests)**

Error: `Unable to find an element with the placeholder text of: Bijv. Maat, Kleur...`  
→ Component uses i18n translation keys for placeholders. The test doesn't set up i18n, so translated placeholders don't render.

**Diagnosis: Test bug** — Missing i18n provider in test setup, or placeholder text changed to use translation keys instead of hardcoded Dutch strings.

**Cluster 3: EventSelector (6 tests)**

Errors:

- `Unable to find an element with the text: Webshop (algemeen)` — Text changed or uses i18n
- Checkbox checked state mismatches — Event ordering/selection logic changed
- `onChange` called with wrong event IDs — Component implementation changed

**Diagnosis: Stale test** — The EventSelector component was refactored (likely the `event_id` removal spec). Tests assert old behavior.

**Cluster 4: ProductCard (1 test)**

Error: `Unable to find an element with the text: Varianten`  
→ The "Varianten" section header text may now use a translation key or the rendering condition changed.

**Diagnosis: Test bug** — Missing i18n setup or component conditionally renders differently now.

**Cluster 5: WebWorkerManager (1 test)**

Error: `Worker initialization failed`  
→ Web Workers aren't available in jsdom test environment.

**Diagnosis: Test bug** — Missing Worker mock in test setup.

**Cluster 6: AnalyticsService (4 tests)**

Error: Same `MemberDataService` TypeError propagating through analytics calculations.

**Diagnosis: Test bug** — Same root cause as Cluster 1 (mock response shape).

**Cluster 7: PresMeetPage.preservation (1 test)**

Error: `Unable to find an element by: [data-testid="onboarding-flow"]` — shows spinner instead.  
→ The async 403 handling isn't completing before assertion.

**Diagnosis: Test bug** — Missing `waitFor` or `act()` wrapper; async state update not awaited.
