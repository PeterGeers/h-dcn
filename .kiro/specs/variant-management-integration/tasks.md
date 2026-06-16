# Implementation Plan

## Overview

This task list implements the variant-management-integration bugfix using the exploratory bugfix workflow. It addresses five related issues: missing VariantSubTable in ProductCard, unsorted size dropdowns, incorrect DELETE endpoint for variant removal, inaccessible inline variant management, and numeric fields sent as strings. The approach follows: explore bugs → preserve existing behavior → implement fix → validate.

## Tasks

- [x] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - Variant Management Integration Defects
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bugs exist
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the five bug conditions exist
  - **Scoped PBT Approach**: Scope properties to concrete failing cases for each bug condition
  - Test cases from Bug Condition in design:
    - Render ProductCard with a product that has `variant_schema: { Maat: ["S", "M", "L"] }` — assert VariantSubTable is NOT rendered (confirms bug 1)
    - Render VariantActionPanel Select with values `["XL", "S", "M", "XS", "L"]` — assert dropdown options are in raw unsorted order (confirms bug 2)
    - Call `removeVariantFromProduct("prod-1", {Maat: "S"})` — assert it sends PUT request instead of DELETE (confirms bug 3)
    - Build payload with `order_item_fields[0].validation = { min_length: "1", max_length: "100" }` — assert string values are passed through without integer coercion (confirms bug 4)
  - Property-based: for random size arrays, verify VariantActionPanel does NOT apply sortSizeValues
  - Property-based: for random numeric-string constraint objects, verify onSubmit does NOT coerce to integers
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests FAIL (this is correct — it proves the bugs exist)
  - Document counterexamples found to understand root cause
  - Mark task complete when tests are written, run, and failure is documented
  - Use `npx react-scripts test --watchAll=false --testPathPattern="variantManagement.bugCondition"` to run
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Existing ProductCard and VariantSchemaEditor Behavior
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for non-buggy inputs:
    - Observe: VariantSchemaEditor axes/values editing (add axis, remove axis, add value, remove value) works correctly
    - Observe: "Sync varianten" button calls `updateVariantSchema` with correct params
    - Observe: "Variant toevoegen" in VariantActionPanel calls `addVariantToProduct` correctly
    - Observe: ProductCard for product WITHOUT variant_schema does NOT render VariantSubTable
    - Observe: Formik form submission for product-level fields (naam, prijs, beschrijving) saves correctly
    - Observe: Products with `order_item_fields` that have NO validation rules save successfully
    - Observe: Products with `purchase_rules` that have NO numeric constraints save successfully
  - Write property-based tests capturing observed behavior:
    - For all products without variant_schema → VariantSubTable never rendered
    - For all axis editing operations → schema form field updated correctly
    - For all product saves without numeric constraints → payload passes through unchanged
    - For random product payloads without variant interactions → non-variant fields unmodified
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - Use `npx react-scripts test --watchAll=false --testPathPattern="variantManagement.preservation"` to run
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

- [x] 3. Fix for variant management integration into ProductCard
  - [x] 3.1 Integrate VariantSubTable into ProductCard
    - Import `VariantSubTable` from `../../webshop-management/components/VariantSubTable.tsx`
    - Import `AdminVariant`, `AdminProduct` types
    - Import `getAdminProducts`, `deleteVariant` from `../../webshop-management/services/adminApi.ts`
    - Add `useState` for `variants: AdminVariant[]` and `isLoadingVariants: boolean`
    - Add `fetchVariants` callback using admin products API for current product
    - Conditionally render VariantSubTable below VariantSchemaEditor CollapsibleSection when `variant_schema` has at least one axis with values
    - Pass product, variants, and refetch callback as props
    - _Bug_Condition: isBugCondition(input) where input.action == 'open_product_card' AND product.variant_schema IS NOT EMPTY AND VariantSubTable IS NOT RENDERED_
    - _Expected_Behavior: VariantSubTable renders with inline editing capabilities for all products with non-empty variant_schema_
    - _Preservation: Products without variant_schema must NOT render VariantSubTable; Formik form submission unaffected_
    - _Requirements: 2.1, 2.4, 3.5, 3.6_

  - [x] 3.2 Sort size values in VariantActionPanel dropdowns
    - Import `sortSizeValues` from `../../webshop-management/utils/sizeSorter.ts` into VariantSchemaEditor
    - In VariantActionPanel component, replace `values.map(...)` in Select rendering with `sortSizeValues(values).map(...)`
    - Ensures clothing sizes display in logical order (XXS→5XL), non-numeric alphabetically, numeric ascending
    - _Bug_Condition: isBugCondition(input) where input.action == 'render_variant_action_panel' AND dropdown_order != sortSizeValues(input.axisValues)_
    - _Expected_Behavior: Select dropdown options sorted via sortSizeValues utility_
    - _Preservation: VariantSchemaEditor axes/values editing functionality unchanged_
    - _Requirements: 2.2, 3.1_

  - [x] 3.3 Fix variant removal to use correct DELETE endpoint
    - Update VariantActionPanel's "Variant verwijderen" button handler to use `deleteVariant(productId, variantId)` from `adminApi.ts`
    - Pass variant list to VariantActionPanel so it can resolve variant_attributes → variant_id
    - Deprecate or remove `removeVariantFromProduct` from `productApi.ts`
    - Ensure DELETE request goes to `/admin/products/{id}/variants/{vid}`
    - _Bug_Condition: isBugCondition(input) where input.action == 'remove_variant' AND request.method == 'PUT'_
    - _Expected_Behavior: DELETE request sent to /admin/products/{id}/variants/{vid} via deleteVariant function_
    - _Preservation: "Variant toevoegen" button continues to call addVariantToProduct (bottom-up sync unchanged)_
    - _Requirements: 2.3, 3.3_

  - [x] 3.4 Add integer coercion for numeric fields in product payload
    - In ProductCard `onSubmit` handler, before calling `onSave(cleanValues)`:
      - Iterate `order_item_fields` and coerce `validation.min_length`, `validation.max_length`, `validation.minimum`, `validation.maximum` to integers via `parseInt`/`Number`
      - Coerce `purchase_rules.max_per_order`, `purchase_rules.max_per_member`, `purchase_rules.max_per_club`, `purchase_rules.min_per_club` to integers
    - Handle edge cases: empty string → remove field, undefined → skip, NaN → skip
    - _Bug_Condition: isBugCondition(input) where order_item_fields[*].validation.* IS string OR purchase_rules.* IS string_
    - _Expected_Behavior: All numeric constraint fields sent as proper JSON integers in request body_
    - _Preservation: Products with no validation rules or no purchase_rules continue to save without new requirements_
    - _Requirements: 2.5, 3.7_

  - [x] 3.5 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Variant Management Integration Fixed
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior for all five bug conditions
    - When this test passes, it confirms:
      - VariantSubTable renders for products with non-empty variant_schema
      - Size dropdown values are sorted via sortSizeValues
      - Variant removal sends DELETE to correct endpoint
      - Numeric constraint fields are proper integers in payload
    - Run bug condition exploration test from step 1
    - **EXPECTED OUTCOME**: Test PASSES (confirms bugs are fixed)
    - Use `npx react-scripts test --watchAll=false --testPathPattern="variantManagement.bugCondition"` to run
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 3.6 Verify preservation tests still pass
    - **Property 2: Preservation** - Existing Behavior Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation property tests from step 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all preserved behaviors still work:
      - VariantSchemaEditor axes/values editing unchanged
      - "Sync varianten" still calls updateVariantSchema
      - "Variant toevoegen" still calls addVariantToProduct
      - Products without variant_schema don't show VariantSubTable
      - Formik form submission unaffected
      - Products without numeric constraints save as before
    - Use `npx react-scripts test --watchAll=false --testPathPattern="variantManagement.preservation"` to run
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

- [x] 4. Checkpoint - Ensure all tests pass
  - Run both test suites together: `npx react-scripts test --watchAll=false --testPathPattern="variantManagement"`
  - Verify TypeScript compilation: `npx tsc --noEmit` from frontend/
  - Confirm no regressions in VariantSubTable's existing usage in webshop-management module
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- All frontend tests use `npx react-scripts test --watchAll=false` with `--testPathPattern` to target specific files (never run the full test suite)
- Property-based tests use `fast-check` library (frontend convention)
- The VariantSubTable component already exists in `frontend/src/modules/webshop-management/components/VariantSubTable.tsx` — this fix wires it into ProductCard
- The `sortSizeValues` utility already exists in `frontend/src/modules/webshop-management/utils/sizeSorter.ts`
- The `deleteVariant` function already exists in `frontend/src/modules/webshop-management/services/adminApi.ts`
- Integer coercion must handle edge cases: empty string, undefined, NaN (skip or remove field)

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1", "2"] },
    { "id": 1, "tasks": ["3.1", "3.2", "3.3", "3.4"] },
    { "id": 2, "tasks": ["3.5", "3.6"] },
    { "id": 3, "tasks": ["4"] }
  ]
}
```
