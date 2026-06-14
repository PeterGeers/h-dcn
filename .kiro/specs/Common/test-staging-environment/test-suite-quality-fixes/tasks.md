# Implementation Plan

## Overview

- [x] 3. Fix Category 4: Delete obsolete migration tests (10 tests)
  - [x] 3.1 Delete obsolete migration test files
    - Delete `backend/tests/unit/test_migrate_channel_to_event_id.py`
    - Delete `backend/tests/unit/test_migrate_products.py`
    - Verify no other test files import from these modules
    - _Bug_Condition: isBugCondition(test) where test.failureCategory == 'obsolete_migration'_
    - _Expected_Behavior: Tests are deliberately removed since migration scripts no longer exist_
    - _Preservation: No other tests depend on these files_
    - _Requirements: 2.13_

- [x] 4. Fix Category 1: Stale tests referencing moved/deleted code (40 tests)
  - [x] 4.1 Fix `test_presmeet_generate_report.py` imports (26 tests)
    - Locate where `apply_filters`, `build_metadata`, `generate_*_report`, and `format_as_csv` currently reside
    - Update import paths in `backend/tests/unit/test_presmeet_generate_report.py` to reference the correct module
    - If functions were removed entirely (not just moved), delete the test file
    - Update any `sys.path` additions to point to correct locations
    - _Bug_Condition: isBugCondition(test) where test imports from moved/deleted handler path_
    - _Expected_Behavior: Tests import from correct current module path and pass_
    - _Preservation: No modification to currently-passing tests_
    - _Requirements: 2.2_

  - [x] 4.2 Fix `test_update_order_items.py` module path
    - Identify the correct handler module path (currently references `handler/update_event/app.py`)
    - Update `@patch` decorators and imports to reference the correct handler
    - Verify all tests in the file pass after the fix
    - _Bug_Condition: isBugCondition(test) where test.failureCategory == 'wrong_module_path'_
    - _Expected_Behavior: Tests reference correct handler module and pass_
    - _Preservation: No modification to other test files_
    - _Requirements: 2.3_

- [x] 5. Fix Category 2: Test bugs with incomplete mocks or wrong assertions (25 tests)
  - [x] 5.1 Fix `test_admin_properties.py` — missing arguments and wrong assertions
    - Add `channel` argument to all `create_inbound_movement()` calls
    - Add `parent_product_id` argument to all `generate_variant_combinations()` calls
    - Update event_id filter assertions to match current behavior (None filter returns all records including those with event_id)
    - _Bug_Condition: isBugCondition(test) where test.failureCategory IN ['missing_argument', 'wrong_assertion']_
    - _Expected_Behavior: Function calls match current signatures; assertions match current filter behavior_
    - _Preservation: Unrelated tests in the file (product creation, stock management) remain unchanged_
    - _Requirements: 2.4, 2.5, 2.6_

  - [x] 5.2 Fix `test_scan_product.py` — incomplete mocks and wrong response format
    - Add missing DynamoDB table mocks and environment variables needed by current handler
    - Update response parsing: response is no longer integer-indexed (remove `response[0]` patterns)
    - Use correct response structure matching current handler output
    - _Bug_Condition: isBugCondition(test) where test.failureCategory IN ['incomplete_mock', 'wrong_response_format']_
    - _Expected_Behavior: Complete mocks allow handler to return HTTP 200; response parsed correctly_
    - _Preservation: scan_product handler behavior for valid requests unchanged_
    - _Requirements: 2.8, 2.9_

  - [x] 5.3 Fix `test_submit_order.py` — routing issues and missing counter table mock
    - Fix test setup so routing correctly handles auth checks (missing auth → 401, insufficient permissions → 403)
    - Add mock for counter table used in order number generation
    - Verify handler returns HTTP 200 for valid order submissions
    - _Bug_Condition: isBugCondition(test) where test.failureCategory IN ['routing_issue', 'missing_mock']_
    - _Expected_Behavior: Auth checks return correct status codes; order number generation succeeds_
    - _Preservation: submit_order handler behavior for valid orders unchanged_
    - _Requirements: 2.10, 2.11_

- [x] 6. Fix Category 3: Real handler bugs with missing input validation (12 tests)
  - [x] 6.1 Add input validation to `admin_record_payment` handler
    - In `backend/handler/admin_record_payment/app.py`, add early validation guards:
      - Missing `order_id` → HTTP 400
      - Non-numeric `amount` → HTTP 400
      - Out-of-range `amount` → HTTP 400
      - Missing `date` → HTTP 400
      - Invalid date format → HTTP 400
    - All validation errors return HTTP 400 with descriptive error message
    - Valid inputs continue to follow the existing success path (HTTP 200)
    - _Bug_Condition: isBugCondition(test) where test.failureCategory == 'handler_missing_validation'_
    - _Expected_Behavior: Invalid input returns HTTP 400 with error message, no unhandled exceptions_
    - _Preservation: Valid payment processing continues to return HTTP 200_
    - _Requirements: 2.7, 3.2_

  - [x] 6.2 Fix `create_order` KeyError on missing `event_id`
    - In `backend/handler/create_order/app.py` (or helper module), replace `body['event_id']` with `body.get('event_id')`
    - Ensure handler gracefully handles missing event_id field without crashing
    - Verify orders WITH event_id still work correctly (event-scoped behavior preserved)
    - _Bug_Condition: isBugCondition(test) where body lacks 'event_id' key_
    - _Expected_Behavior: Handler uses .get() for safe access; no KeyError_
    - _Preservation: Orders with event_id present continue to use it correctly_
    - _Requirements: 2.12, 3.5_

  - [x] 6.3 Update `test_admin_record_payment.py` assertions if needed
    - Verify test assertions match the validation error response format from 6.1
    - Ensure tests assert HTTP 400 (not 500) for invalid input cases
    - Ensure tests assert HTTP 200 for valid input cases
    - _Requirements: 2.7_
