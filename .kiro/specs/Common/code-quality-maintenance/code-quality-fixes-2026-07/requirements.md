# Code Quality Scan — July 2026

## Summary

| Category               | Count                          | Status       |
| ---------------------- | ------------------------------ | ------------ |
| Backend test failures  | 189 tests in 32 files          | ❌ Needs fix |
| Frontend test failures | 0                              | ✅ Clean     |
| Files over 500 lines   | 22 frontend files              | ⚠️ Monitor   |
| Files over 1000 lines  | 0                              | ✅ Clean     |
| Backend dead code      | 1 finding                      | ⚠️ Minor     |
| Handlers without tests | 33 (excl. **pycache**, shared) | ⚠️ Backlog   |

## 1. Broken/Stale Tests (Backend — 189 failures)

### Category A: Stale tests (test references removed code/renamed functions)

| Test File                                | Failures | Root Cause                                                                     |
| ---------------------------------------- | -------- | ------------------------------------------------------------------------------ |
| test_create_order.py                     | 13       | Tests mock `get_club_id` which was removed in registry_row refactor            |
| test_upload_club_logo.py                 | 17       | Handler likely renamed/removed in registry_row refactor (club → registry_row)  |
| test_upload_club_logo_properties.py      | 3        | Same as above                                                                  |
| test_generate_preparation_pdf.py         | 4        | Tests reference `_sort_key_club_name` (removed), `Club Zebra` assertions stale |
| test_manage_delegates.py                 | 2        | Asserts 'club' in error message, now says 'row-scoped'                         |
| test_event_onboard_properties.py         | 3        | Tests reference `club_id` field and old function signature                     |
| test_registry_row_refactor_properties.py | 2        | Likely testing interim migration code that's complete                          |
| test_scan_product_preservation.py        | 5        | Tests old field preservation logic                                             |
| test_scan_product_bug_condition.py       | 4        | Meta-test confirming known bugs still exist                                    |
| test_bug_condition_exploration.py        | 2        | Meta-test confirming known bugs                                                |

### Category B: Real bugs (handler changed behavior, test expectations valid)

| Test File                       | Failures | Root Cause                                                              |
| ------------------------------- | -------- | ----------------------------------------------------------------------- |
| test_event_onboard.py           | 15       | Handler returns 500 instead of expected 200/400/403/409 — runtime error |
| test_get_event_registry.py      | 8        | Returns 401 instead of 200/404 — session token validation broken        |
| test_get_product_sold_counts.py | 10       | All return 500 — handler has runtime error                              |
| test_insert_product.py          | 8        | Returns 500 instead of 201 — handler crash                              |
| test_admin_event_claims.py      | 4        | Returns 500 instead of 200 — handler crash                              |
| test_admin_event_dashboard.py   | 3        | Returns 0 instead of expected counts                                    |

### Category C: Test bugs (wrong assertions, outdated expectations)

| Test File                                   | Failures | Root Cause                                                                            |
| ------------------------------------------- | -------- | ------------------------------------------------------------------------------------- |
| test_create_event.py                        | 17       | Tests don't send `linked_regio` (now required), registration dates no longer required |
| test_admin_lock_unlock_orders.py            | 5        | Unlock now transitions to `draft` not `submitted`                                     |
| test_admin_properties.py                    | 2        | `payment_failed → submitted` is now valid transition                                  |
| test_booking_validation_properties.py       | 2        | Event access check now happens before validation                                      |
| test_event_constraints.py                   | 2        | Counting logic changed (club exclusion on resubmit)                                   |
| test_scan_product.py                        | 11       | Field name expectations outdated                                                      |
| test_property_scan_product.py               | 7        | Same as above                                                                         |
| test_price_validation_handlers.py           | 7        | Handler API changed                                                                   |
| test_get_order.py                           | 1        | Error message text changed                                                            |
| test_order_deduplication_properties.py      | 4        | Order dedup logic changed                                                             |
| test_property_order_handlers.py             | 3        | Order handler API changed                                                             |
| test_pay_order.py                           | 2        | Payment flow changed                                                                  |
| test_submit_order_event_persons.py          | 1        | Event access check added                                                              |
| test_migration.py                           | 2        | Migration script references changed                                                   |
| test_admin_create_product.py (+ properties) | 14       | Handler uses argparse for CLI mode, causes SystemExit in test                         |
| test_unified_pipeline.py                    | 2        | get_products API changed (batch-get instead of scan)                                  |

## 2. File Length (Frontend — 22 files over 500 lines)

No files exceed 1000 lines. All are under 732 lines. Top candidates for refactoring:

| File                         | Lines | Priority      |
| ---------------------------- | ----- | ------------- |
| NewMemberApplicationForm.tsx | 732   | Medium        |
| MemberEditView.tsx           | 707   | Medium        |
| functionPermissions.ts       | 701   | Low (config)  |
| MemberEditModal.tsx          | 696   | Medium        |
| DataProcessingService.ts     | 663   | Low (service) |
| modalConfig.ts               | 656   | Low (config)  |
| OrderDetailDrawer.tsx        | 625   | Medium        |
| GoogleMailService.ts         | 622   | Low (service) |
| ProductManagementPage.tsx    | 604   | Medium        |
| CheckoutModal.tsx            | 601   | Medium        |

## 3. Dead Code (Backend)

| File                                 | Finding                                   | Confidence |
| ------------------------------------ | ----------------------------------------- | ---------- |
| backend/handler/update_member/app.py | unused import `log_status_change_success` | 90%        |

## 4. Handlers Without Tests (33)

Low priority backlog — these are mostly simple CRUD handlers or admin utilities:

admin_batch_pdf, admin_batch_update_status, admin_confirm_payment, admin_export_report, admin_generate_report, admin_get_payments, admin_get_products, admin_get_report, admin_get_stock_movements, admin_lock_orders, admin_unlock_order, admin_update_order_status, assign_club, cognito_user_migration, create_membership, delete_event, delete_membership, delete_payment, get_club_registry, get_event_byid, get_events, get_member_byid, get_member_payments, get_membership_byid, get_memberships, get_order_byid, get_payment_byid, get_payments, s3_file_manager, update_membership, update_parameters, update_payment, upload_image, upload_registry_logo

## 5. Stale Documentation

Not scanned in this round — docs/ changes are tracked via ADRs.
