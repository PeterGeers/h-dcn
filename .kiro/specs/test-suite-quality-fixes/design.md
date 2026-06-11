# Test Suite Quality Fixes — Bugfix Design

## Overview

The backend test suite has 82 failing tests across 4 categories that make it unreliable as a quality gate. This design formalizes the bug condition (tests that fail), the fix strategy for each category, and the preservation requirements ensuring the 1300+ passing tests remain unaffected. The fix approach is category-specific: delete obsolete tests, update stale imports/mocks, fix test assertions, and add missing input validation to handlers.

## Glossary

- **Bug_Condition (C)**: A test that fails when the full suite is run — due to stale references, incomplete mocks, wrong assertions, missing handler validation, or obsolete migration code
- **Property (P)**: All tests pass (0 failures), providing a reliable quality gate
- **Preservation**: The 1300+ currently-passing tests continue to pass without modification; handlers with valid input continue to return correct responses
- **Stale Test**: A test importing from a module path that no longer exists or referencing a function signature that has changed
- **Test Bug**: A test with incorrect mocks, missing mock setup, or wrong assertions relative to current handler behavior
- **Handler Bug**: A real defect in production handler code (e.g., missing input validation returning 500 instead of 400)
- **Obsolete Migration Test**: A test for a one-time migration script that has already been executed and whose code is no longer maintained

## Bug Details

### Bug Condition

The bug manifests when `pytest backend/tests/` is executed and 82 tests fail. The failures are categorized into four root causes, each requiring a different fix strategy.

**Formal Specification:**

```
FUNCTION isBugCondition(test)
  INPUT: test of type TestCase
  OUTPUT: boolean

  RETURN test.result == FAIL
         AND (
           test.failureCategory IN ['stale_import', 'wrong_module_path', 'missing_argument']
           OR test.failureCategory IN ['incomplete_mock', 'wrong_assertion', 'wrong_response_format']
           OR test.failureCategory IN ['handler_missing_validation']
           OR test.failureCategory IN ['obsolete_migration']
         )
END FUNCTION
```

### Examples

- **Stale import**: `test_presmeet_generate_report.py` imports `apply_filters` from `handler/presmeet_generate_report/app.py` but that function was moved during refactoring → ImportError
- **Wrong module path**: `test_update_order_items.py` patches `handler/update_event/app.py` instead of the correct handler module → AttributeError
- **Missing argument**: `test_admin_properties.py` calls `create_inbound_movement()` without the new `channel` argument → TypeError
- **Incomplete mock**: `test_scan_product.py` mocks are incomplete for the current handler implementation → HTTP 500 instead of 200
- **Wrong assertion**: `test_admin_properties.py` asserts old filter behavior (None filter excludes event_id records) but behavior changed → AssertionError
- **Handler bug**: `admin_record_payment` receives invalid input and returns HTTP 500 instead of HTTP 400 with validation error
- **Obsolete migration**: `test_migrate_channel_to_event_id.py` tests a script that has already run and been removed → ImportError

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**

- All 1300+ currently-passing tests continue to pass without modification
- `admin_record_payment` handler continues to process valid payments and return HTTP 200
- `scan_product` handler continues to return normalized product data for valid requests
- `submit_order` handler continues to generate order numbers and return HTTP 200 for valid orders
- `create_order` handler continues to use event_id correctly when the field is present
- All handler CORS headers, auth checks, and error response formats remain unchanged
- Property-based tests with correct mocks continue to validate all properties

**Scope:**
All inputs that do NOT trigger the bug condition should be completely unaffected by this fix. This includes:

- Tests that currently pass (they should not be modified)
- Handler behavior for valid input (HTTP 200 paths remain unchanged)
- Shared auth layer behavior (`auth_utils.py`, `maintenance_fallback.py`)
- SAM template and infrastructure configuration
- Frontend code (not in scope)

## Hypothesized Root Cause

Based on the bug description and code analysis, the root causes are:

1. **Stale imports after refactoring (40 tests)**: Functions like `apply_filters`, `build_metadata`, `generate_*_report`, and `format_as_csv` were moved to new modules during a presmeet/reporting refactoring. Test files still import from the old locations. Similarly, `test_update_order_items.py` references `handler/update_event/app.py` instead of the correct path.

2. **Test bugs with incomplete mocks or wrong assertions (25 tests)**: Handler implementations evolved (new required arguments like `channel` and `parent_product_id`, changed response formats, changed filter behavior) but tests were not updated. Mock setups are incomplete for `scan_product` (missing DynamoDB table mocks or environment variables). `test_submit_order.py` has routing issues and missing counter table mock.

3. **Real handler bugs with missing input validation (12 tests)**: The `admin_record_payment` handler lacked early validation for missing/invalid fields, causing unhandled exceptions that returned HTTP 500. The `create_order` handler accesses `event_id` with bracket notation (`body['event_id']`) in a helper function instead of using `.get('event_id')`, causing KeyError when the field is absent.

4. **Obsolete migration tests (10 tests)**: `test_migrate_channel_to_event_id.py` and `test_migrate_products.py` test one-time migration scripts that have already been executed. The migration code has been removed or altered, causing import failures.

## Correctness Properties

Property 1: Bug Condition — All Failing Tests Resolve

_For any_ test in the test suite that currently fails (isBugCondition returns true), the fix SHALL result in that test either passing with correct assertions against current behavior, or being deliberately removed (for obsolete migration tests and irreparably stale tests).

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10, 2.11, 2.12, 2.13**

Property 2: Preservation — Passing Tests Remain Passing

_For any_ test that currently passes (isBugCondition returns false), the fix SHALL NOT modify that test or its dependencies in a way that causes it to fail, preserving the existing 1300+ passing test baseline.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**Category 1: Stale Tests (40 tests) — Delete or Re-target Imports**

**Files**: `backend/tests/unit/test_presmeet_generate_report.py`, `backend/tests/unit/test_update_order_items.py`, and other files with stale imports

**Specific Changes**:

1. **Locate moved functions**: Find where `apply_filters`, `build_metadata`, `generate_*_report`, `format_as_csv` currently reside
2. **Update import paths**: Change `sys.path` additions and import statements to reference current module locations
3. **Delete irreparable tests**: If functions were removed entirely (not just moved), delete the corresponding test file
4. **Fix module patches**: Update `@patch` decorators to reference correct module paths (e.g., fix `handler/update_event/app.py` → correct handler path)

**Category 2: Test Bugs (25 tests) — Update Mocks and Assertions**

**Files**: `backend/tests/unit/test_admin_properties.py`, `backend/tests/unit/test_scan_product.py`, `backend/tests/unit/test_submit_order.py`

**Specific Changes**:

1. **Add missing arguments**: Update calls to `create_inbound_movement(channel=...)` and `generate_variant_combinations(parent_product_id=...)`
2. **Fix event_id filter assertions**: Update assertions to match current behavior (None filter returns all records including those with event_id)
3. **Complete scan_product mocks**: Add missing DynamoDB table mocks, environment variables, and update response parsing (no longer integer-indexed)
4. **Fix submit_order test setup**: Correct routing configuration so auth checks return 401/403, and mock the counter table for order number generation

**Category 3: Real Handler Bugs (12 tests) — Add Input Validation**

**Files**: `backend/handler/admin_record_payment/app.py`, `backend/handler/create_order/app.py` (or helper module)

**Specific Changes**:

1. **admin_record_payment validation**: Verify that validation guards exist for missing order_id, non-numeric amount, out-of-range amount, missing date, and invalid date format — all returning HTTP 400 (these appear to already be present based on code review; tests may need updating to match the validation format)
2. **create_order KeyError fix**: Replace `body['event_id']` with `body.get('event_id')` in any helper function that accesses event_id unsafely

**Category 4: Obsolete Migration Tests (10 tests) — Delete**

**Files**: `backend/tests/unit/test_migrate_channel_to_event_id.py`, `backend/tests/unit/test_migrate_products.py`

**Specific Changes**:

1. **Delete test files**: Remove both migration test files entirely
2. **Verify no cross-references**: Ensure no other test files import from or depend on these migration test modules

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code, then verify the fix works correctly and preserves existing behavior.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm or refute the root cause analysis. If we refute, we will need to re-hypothesize.

**Test Plan**: Run the full test suite and categorize each failure by root cause. For each category, verify the hypothesized cause by examining the error trace.

**Test Cases**:

1. **Stale Import Test**: Run `pytest backend/tests/unit/test_presmeet_generate_report.py` — expect ImportError for moved functions (will fail on unfixed code)
2. **Wrong Module Path Test**: Run `pytest backend/tests/unit/test_update_order_items.py` — expect AttributeError for wrong handler reference (will fail on unfixed code)
3. **Missing Argument Test**: Run `pytest backend/tests/unit/test_admin_properties.py` — expect TypeError for missing `channel` arg (will fail on unfixed code)
4. **Incomplete Mock Test**: Run `pytest backend/tests/unit/test_scan_product.py` — expect HTTP 500 instead of 200 (will fail on unfixed code)
5. **Handler Validation Test**: Run `pytest backend/tests/unit/test_admin_record_payment.py` — expect 500 vs 400 mismatch (will fail on unfixed code)
6. **Obsolete Migration Test**: Run `pytest backend/tests/unit/test_migrate_channel_to_event_id.py` — expect ImportError (will fail on unfixed code)

**Expected Counterexamples**:

- ImportError traces pointing to moved/deleted modules
- TypeError traces showing missing required positional arguments
- AssertionError traces showing expected 400 but got 500
- Possible causes: code refactoring without test updates, missing validation, removed migration scripts

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed function produces the expected behavior.

**Pseudocode:**

```
FOR ALL test WHERE isBugCondition(test) DO
  result := runTest_afterFix(test)
  ASSERT result == PASS OR test WAS deliberately_deleted
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed function produces the same result as the original function.

**Pseudocode:**

```
FOR ALL test WHERE NOT isBugCondition(test) DO
  ASSERT runTest_afterFix(test) == PASS
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:

- It generates many test cases automatically across the input domain
- It catches edge cases that manual unit tests might miss
- It provides strong guarantees that handler behavior is unchanged for valid inputs

**Test Plan**: Run the full passing test baseline before and after the fix to verify no regressions.

**Test Cases**:

1. **Full Suite Regression**: Run `pytest backend/tests/` after all fixes — verify 0 failures
2. **Handler Valid Input Preservation**: Verify `admin_record_payment` with valid input still returns HTTP 200
3. **Create Order with event_id Preservation**: Verify `create_order` with event_id present still creates event-scoped orders correctly
4. **Auth Flow Preservation**: Verify all auth-related tests continue to pass (CORS, permissions, credential extraction)

### Unit Tests

- Test each stale import fix individually by running the updated test file
- Test each mock/assertion fix by running the specific test case
- Test handler validation by sending invalid input and verifying HTTP 400 responses
- Test create_order with missing event_id to verify no KeyError

### Property-Based Tests

- Generate random invalid inputs for `admin_record_payment` and verify all return HTTP 400 (not 500)
- Generate random order payloads with/without event_id for `create_order` and verify no crashes
- Generate random valid inputs for handlers and verify preservation of correct behavior

### Integration Tests

- Run the full test suite end-to-end to verify 0 failures
- Verify the test suite continues to run in CI (GitHub Actions nightly-tests workflow)
- Verify no import cycles or dependency issues introduced by path changes
