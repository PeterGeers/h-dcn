# Implementation Plan: Webshop & PresMeet Bugfix

## Overview

This plan fixes three related bugs: (1) `scan_product` endpoint omits `groep`, `subgroep`, and `images` fields breaking webshop filtering and product images, and (2) PresMeet page shows "Network Error" when no order exists because the 404 response is not handled gracefully. The workflow follows the bug condition methodology: write exploration tests to confirm the bugs, write preservation tests to protect existing behavior, then implement the fix and verify.

## Tasks

- [x] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - scan_product omits groep/subgroep/images and PresMeet 404 unhandled
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bugs exist
  - **Scoped PBT Approach**: For scan_product, the bug is unconditional (isBugCondition returns TRUE for all requests). For PresMeet, scope to: user has presmeet access AND club assignment AND no existing order.
  - Backend test (`backend/tests/unit/test_scan_product_bug_condition.py`): mock DynamoDB scan returning items with `groep`, `subgroep`, and `images` fields → assert handler response includes all three fields in each product object
  - Frontend test (`frontend/src/modules/presmeet/__tests__/PresMeetPage.404.test.tsx`): mock presmeetApi.getOrder to reject with AxiosError status 404 → assert PresMeetPage does NOT set error state and does NOT display error message
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests FAIL (this is correct - it proves the bugs exist)
  - Document counterexamples: scan_product response missing `groep`/`subgroep`/`images` keys; PresMeet sets error message on 404
  - Mark task complete when tests are written, run, and failure is documented
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Existing scan_product fields and PresMeet 200/403 handling unchanged
  - **IMPORTANT**: Follow observation-first methodology
  - Observe: call scan_product on UNFIXED code → confirm existing fields (`product_id`, `name`, `price`, `variant_schema`, `is_parent`, `event_id`, `active`) are returned with Decimal-to-number conversion
  - Observe: call PresMeet with existing order on UNFIXED code → confirm 200 with order data
  - Observe: call PresMeet with 403 responses on UNFIXED code → confirm authorization error handling triggers correctly
  - Backend property test (`backend/tests/unit/test_scan_product_preservation.py`): use Hypothesis to generate random DynamoDB product items with varying Decimal values, missing optional fields, None values → verify existing 7 fields are returned identically with correct Decimal conversion
  - Frontend preservation test (`frontend/src/modules/presmeet/__tests__/PresMeetPage.preservation.test.tsx`): mock existing order → verify 200 response loads correctly; mock 403 → verify authorization error flow unchanged (isAuthorizationError path, onboarding flow)
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 3. Fix scan_product missing fields and PresMeet 404 handling
  - [x] 3.1 Add groep, subgroep, images to scan_product normalized response
    - In `backend/handler/scan_product/app.py`, add to the normalized dict (around lines 84-93):
      - `'groep': item.get('groep')`
      - `'subgroep': item.get('subgroep')`
      - `'images': item.get('images', [])`
    - Default `images` to empty list `[]` when absent in DynamoDB (matching `get_products` behavior)
    - `groep` and `subgroep` default to `None` when absent
    - _Bug_Condition: isBugCondition_ScanProduct(X) = TRUE (unconditional — all requests affected)_
    - _Expected_Behavior: response includes groep, subgroep, images for every product_
    - _Preservation: existing fields (product_id, name, price, variant_schema, is_parent, event_id, active) unchanged with Decimal conversion_
    - _Requirements: 2.1, 2.2, 3.1_

  - [x] 3.2 Handle 404 as empty state in PresMeetPage
    - In `frontend/src/modules/presmeet/PresMeetPage.tsx`, in the `loadPageData` inner try/catch (around line 140):
    - After the `isAuthorizationError` check and raw 403 check, add condition for 404:
      ```typescript
      } else if (orderErr?.response?.status === 404) {
        // No order exists yet — valid state, show empty booking
      }
      ```
    - The 404 case must NOT throw — leave `order` as null to trigger the create-booking flow
    - _Bug_Condition: isBugCondition_PresMeet(X) = club_has_order=FALSE AND has_presmeet_access=TRUE AND has_club_assignment=TRUE_
    - _Expected_Behavior: no error shown, order remains null, empty booking state rendered_
    - _Preservation: 403 handling unchanged, existing order retrieval unchanged, 409 interceptor unchanged_
    - _Requirements: 2.3, 3.3, 3.4, 3.5_

  - [x] 3.3 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - scan_product includes groep/subgroep/images and PresMeet 404 shows empty state
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 1
    - **EXPECTED OUTCOME**: Test PASSES (confirms bugs are fixed)
    - _Requirements: 2.1, 2.2, 2.3_

  - [x] 3.4 Verify preservation tests still pass
    - **Property 2: Preservation** - Existing scan_product fields and PresMeet 200/403 handling unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation property tests from step 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all preservation tests still pass after fix (no regressions introduced)

- [x] 4. Checkpoint - Ensure all tests pass
  - Run full backend test suite: `pytest tests/` from `backend/`
  - Run full frontend test suite: `npx react-scripts test --watchAll=false` from `frontend/`
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Backend tests use pytest + moto for DynamoDB mocking, Hypothesis for property-based testing
- Frontend tests use Jest + React Testing Library (run via `npx react-scripts test`)
- The scan_product bug is unconditional — every request is affected, no special trigger needed
- The PresMeet 404 fix is frontend-only — the backend correctly returns 404 for "resource not found"
- The `images` default of `[]` matches the existing pattern in `get_products/app.py`
- No changes to `get_products` handler are needed — it already works correctly
- The Axios interceptor in `presmeetApi.ts` is NOT modified — 404 handling is done in the component's catch block

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1"] },
    { "id": 1, "tasks": ["2"] },
    { "id": 2, "tasks": ["3.1", "3.2"] },
    { "id": 3, "tasks": ["3.3", "3.4"] },
    { "id": 4, "tasks": ["4"] }
  ]
}
```
