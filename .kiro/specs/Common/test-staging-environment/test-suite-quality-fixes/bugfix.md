# Bugfix Requirements Document

## Introduction

The backend test suite (1400+ tests) has 82 failing tests that make it unreliable as a quality gate. Failures fall into four categories: stale tests referencing moved/deleted code (40 tests), test bugs with incomplete mocks or wrong assertions (25 tests), real handler bugs with missing input validation (12 tests), and obsolete migration tests (10 tests). This bugfix restores the test suite to a clean, trustworthy state where every test either passes or is intentionally removed.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN the full test suite is run THEN 82 tests fail, masking real issues and making the suite unusable as a quality gate

1.2 WHEN `test_presmeet_generate_report.py` tests execute THEN all 26 tests fail with ImportError because `apply_filters`, `build_metadata`, `generate_*_report`, and `format_as_csv` cannot be imported from the handler path `handler/get_products/app.py` (functions were moved during refactoring)

1.3 WHEN `test_update_order_items.py` tests execute THEN tests fail with AttributeError because they reference the wrong handler module path (`handler/update_event/app.py` instead of the correct handler)

1.4 WHEN `test_admin_properties.py` calls `create_inbound_movement()` THEN the test fails with TypeError because the function now requires a `channel` argument that was added during refactoring

1.5 WHEN `test_admin_properties.py` calls `generate_variant_combinations()` THEN the test fails with TypeError because the function now requires a `parent_product_id` argument

1.6 WHEN `test_admin_properties.py` tests event_id filter logic THEN assertions fail because the filter behavior changed (records with event_id are returned when filter is None)

1.7 WHEN the `admin_record_payment` handler receives invalid input (missing order_id, non-numeric amount, out-of-range amount, missing date, invalid date format) THEN the handler returns HTTP 500 instead of HTTP 400

1.8 WHEN `test_scan_product.py` tests parse the handler response THEN they fail with `KeyError: 0` because the response format changed (response is no longer indexable by integer key)

1.9 WHEN scan_product handler receives a valid product with complete mocks THEN it returns HTTP 500 instead of HTTP 200 (mock setup incomplete for current handler implementation)

1.10 WHEN `test_submit_order.py` tests check authentication THEN requests return HTTP 404 instead of the expected 401/403 (routing issue in test setup)

1.11 WHEN `test_submit_order.py` tests submit an order THEN the handler returns HTTP 500 with "Failed to generate order number" because the counter table is not mocked

1.12 WHEN `test_create_order.py` creates a webshop order THEN the handler crashes with `KeyError: 'event_id'` because it accesses event_id without checking if it exists

1.13 WHEN `test_migrate_channel_to_event_id.py` and `test_migrate_products.py` tests execute THEN they fail because they test one-time migration scripts whose code has been removed or altered after successful execution

### Expected Behavior (Correct)

2.1 WHEN the full test suite is run THEN all tests pass (0 failures), providing a reliable indicator of code health

2.2 WHEN report generation tests exist THEN they SHALL import from the correct current module path where `apply_filters`, `build_metadata`, `generate_*_report`, and `format_as_csv` now reside, OR the stale test file SHALL be deleted if the functions were removed entirely

2.3 WHEN `test_update_order_items.py` tests execute THEN they SHALL reference the correct handler module path for the update_order_items handler

2.4 WHEN `test_admin_properties.py` calls `create_inbound_movement()` THEN it SHALL pass the required `channel` argument matching the current function signature

2.5 WHEN `test_admin_properties.py` calls `generate_variant_combinations()` THEN it SHALL pass the required `parent_product_id` argument matching the current function signature

2.6 WHEN `test_admin_properties.py` tests event_id filter logic THEN assertions SHALL match the current filter behavior (None filter returns all records including those with event_id)

2.7 WHEN the `admin_record_payment` handler receives invalid input (missing order_id, non-numeric amount, out-of-range amount, missing date, invalid date format) THEN the handler SHALL return HTTP 400 with a descriptive validation error message without crashing

2.8 WHEN scan_product tests parse the handler response THEN they SHALL use the correct response format (matching the current handler's response structure)

2.9 WHEN scan_product tests call the handler with valid products THEN mock setup SHALL be complete so the handler returns HTTP 200 with the normalized product data

2.10 WHEN `test_submit_order.py` tests check authentication THEN the test setup SHALL correctly route requests so that missing auth returns 401 and insufficient permissions returns 403

2.11 WHEN `test_submit_order.py` tests submit an order THEN the counter table SHALL be properly mocked so order number generation succeeds and the handler returns HTTP 200

2.12 WHEN the `create_order` handler receives an order without an `event_id` field THEN the handler SHALL gracefully handle the missing key (use `.get('event_id')` or guard the access) instead of crashing with KeyError

2.13 WHEN one-time migration scripts have completed THEN their corresponding test files (`test_migrate_channel_to_event_id.py`, `test_migrate_products.py`) SHALL be deleted from the test suite

### Unchanged Behavior (Regression Prevention)

3.1 WHEN tests for handlers that currently pass (1300+ tests) are run THEN the system SHALL CONTINUE TO pass without modification

3.2 WHEN the `admin_record_payment` handler receives valid input (valid order_id, numeric amount in range, valid date) THEN the system SHALL CONTINUE TO process the payment and return HTTP 200

3.3 WHEN scan_product handler receives a valid product scan request with proper authentication THEN the system SHALL CONTINUE TO return normalized product data with all required fields

3.4 WHEN submit_order handler receives a properly authenticated, valid order submission THEN the system SHALL CONTINUE TO generate an order number, update status, and return HTTP 200

3.5 WHEN create_order handler receives an order WITH an event_id field THEN the system SHALL CONTINUE TO use the event_id correctly in order creation

3.6 WHEN admin_properties tests verify behaviors unrelated to the changed function signatures (e.g., product creation, stock management) THEN those tests SHALL CONTINUE TO pass unchanged

3.7 WHEN property-based tests for handlers with correct mocks run THEN the system SHALL CONTINUE TO validate all properties across generated inputs
