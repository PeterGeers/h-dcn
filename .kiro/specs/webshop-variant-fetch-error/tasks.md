# Implementation Plan

## Overview

Fix the variant_fetch_error bug in `ProductCard.tsx` where incorrect response unpacking causes "variant_fetch_error" to display instead of variant options. The response has shape `{ success: true, data: { product_id, variants: [...], total_count } }` but the code assigns `response.data` (entire object) instead of `response.data.variants` (the array).

## Tasks

- [x] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - Incorrect Variant Data Extraction
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bug exists in `ProductCard.tsx` variant unpacking
  - **Scoped PBT Approach**: Scope the property to the concrete failing case — any successful API response with shape `{ success: true, data: { product_id, variants: [...], total_count } }` where `response.data` is an object containing a `variants` array
  - Extract the variant unpacking logic into a testable pure function for isolation
  - Generate random `ApiResponse` objects where `isBugCondition(input)` is true: `input.success = true AND input.data IS object AND input.data.variants IS array`
  - Assert that `extractVariants(response)` returns `response.data.variants` (the actual `VariantRecord[]` array)
  - Assert that `Array.isArray(extractVariants(response))` is true
  - Assert that `extractVariants(response).length === response.data.total_count`
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS (this is correct - it proves the bug exists because unfixed code returns the entire `data` object instead of `data.variants`)
  - Document counterexamples found (e.g., `extractVariants({ success: true, data: { product_id: "p1", variants: [{...}], total_count: 1 } })` returns `{ product_id, variants, total_count }` object instead of `[{...}]` array)
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.1, 1.2_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Error and Skip Behavior Unchanged
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for non-buggy inputs (cases where `isBugCondition` returns false)
  - Observe: when response is `null` or `undefined`, `extractVariants(response)` returns `[]` on unfixed code
  - Observe: when response is a direct array (e.g., `[{variant_id: "v1", ...}]`), `extractVariants(response)` returns that array on unfixed code
  - Observe: when `response.data` is `null`/`undefined`, `extractVariants(response)` returns `[]` on unfixed code
  - Observe: when `productService.getVariants()` throws (network/auth error), the catch block sets `variantFetchError=true`
  - Write property-based tests: for all non-bug-condition inputs (null, undefined, error responses, direct arrays, responses without `data.variants`), the fixed extraction logic SHALL produce exactly the same result as the original
  - Generate random inputs where `isBugCondition` is false: null responses, undefined responses, direct arrays, objects where `data` is not an object with a `variants` array
  - Assert `extractVariants_original(input) === extractVariants_fixed(input)` for all generated non-bug-condition inputs
  - Verify tests pass on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 3. Fix for variant_fetch_error caused by incorrect response unpacking
  - [x] 3.1 Implement the fix in ProductCard.tsx
    - In the first `.then()` block (products with `variant_schema`), change `response?.data || []` to `response?.data?.variants || []`
    - In the second `.then()` block (products without `variant_schema`), change `response?.data || []` to `response?.data?.variants || []`
    - Optionally add type annotation to `.then()` callback replacing `(response: any)` with proper `ApiResponse<{ product_id: string; variants: VariantRecord[]; total_count: number }>` typing
    - Optionally add defensive guard: `Array.isArray(response?.data?.variants) ? response.data.variants : []`
    - _Bug_Condition: isBugCondition(input) where input.success = true AND input.data IS object AND input.data.variants IS array_
    - _Expected_Behavior: extractVariants(response) returns response.data.variants (VariantRecord[] array) when isBugCondition is true_
    - _Preservation: Non-bug-condition paths (API failures, null responses, direct arrays, skipped fetches) must produce identical behavior to unfixed code_
    - _Requirements: 1.1, 1.2, 2.1, 2.2, 3.1, 3.2, 3.3, 3.4_

  - [x] 3.2 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Correct Variant Array Extraction
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior (extractVariants returns response.data.variants)
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 1
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.1, 2.2_

  - [x] 3.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Error and Skip Behavior Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation property tests from step 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all tests still pass after fix (no regressions in error handling, null fallbacks, or direct array paths)

- [x] 4. Checkpoint - Ensure all tests pass
  - Run full test suite: `npm test -- --watchAll=false` from frontend directory
  - Ensure all property-based tests pass (both bug condition and preservation)
  - Ensure no TypeScript compilation errors (`npm run type-check`)
  - Ensure VariantSelector receives proper `VariantRecord[]` array for products with and without `variant_schema`
  - Ask the user if questions arise

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1", "2"] },
    { "id": 1, "tasks": ["3.1"] },
    { "id": 2, "tasks": ["3.2", "3.3"] },
    { "id": 3, "tasks": ["4"] }
  ]
}
```

## Notes

- The bug is a one-line fix per `.then()` block but requires property-based tests to verify correctness and prevent regression
- The exploration test (task 1) intentionally FAILS on unfixed code — this is expected and confirms the bug exists
- The preservation test (task 2) must PASS on unfixed code — this captures existing correct behavior before the fix
- Test framework: Jest + React Testing Library (per project conventions, use `npx react-scripts test`)
- Property-based testing library: Use `fast-check` for generating random API response shapes
- File under test: `frontend/src/modules/webshop/components/ProductCard.tsx`
