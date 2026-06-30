# Variant Management Integration Bugfix Design

## Overview

This bugfix addresses five related issues that prevent admins from effectively managing product variants within the ProductCard modal:

1. The `VariantSubTable` component (fully implemented in webshop-management) is not rendered in ProductCard, making variant-level operations invisible.
2. The `VariantActionPanel` displays size dropdown values in raw array order instead of logical clothing size order.
3. The `removeVariantFromProduct` function uses an incorrect PUT endpoint instead of the deployed `admin_delete_variant` DELETE endpoint.
4. Inline variant management (price editing, oversell toggle, stock) is inaccessible from ProductCard.
5. Numeric fields in `order_item_fields.validation` and `purchase_rules` may arrive at the backend as strings (from JSON serialization of Formik form values), causing `isinstance(value, int)` checks to fail spuriously.

The fix integrates existing, working components and utilities, corrects API routing, and ensures proper integer coercion on the frontend before submission.

## Glossary

- **Bug_Condition (C)**: The set of conditions that produce incorrect behavior — missing VariantSubTable, unsorted sizes, wrong DELETE endpoint, and string-typed integers in product payload
- **Property (P)**: The correct behavior — VariantSubTable rendered, sizes sorted logically, DELETE endpoint used, and integers sent as proper JSON numbers
- **Preservation**: Existing VariantSchemaEditor behavior, Formik form submission, mouse-click behavior, and products without variant schemas must remain unchanged
- **VariantSubTable**: Component in `frontend/src/modules/webshop-management/components/VariantSubTable.tsx` providing inline variant management (price editing, oversell, deactivate/delete, stock)
- **VariantActionPanel**: Sub-component in `VariantSchemaEditor.tsx` (line 419) rendering Select dropdowns for axis values and add/remove variant buttons
- **sortSizeValues**: Utility in `frontend/src/modules/webshop-management/utils/sizeSorter.ts` that sorts clothing sizes in logical order (XXS→5XL), then alphabetical non-numeric, then numeric ascending
- **removeVariantFromProduct**: Function in `frontend/src/modules/products/api/productApi.ts` that currently sends PUT with `variant_action: 'remove_variant'` (incorrect)
- **deleteVariant**: Function in `frontend/src/modules/webshop-management/services/adminApi.ts` that sends DELETE to `/admin/products/{id}/variants/{vid}` (correct)
- **ProductCard**: Component in `frontend/src/modules/products/components/ProductCard.tsx` — the main product editing modal

## Bug Details

### Bug Condition

The bug manifests across five scenarios when an admin interacts with product variant management in the ProductCard modal. The core issue is incomplete integration: working components and utilities exist but are not wired into the main product management UI.

**Formal Specification:**

```
FUNCTION isBugCondition(input)
  INPUT: input of type AdminAction
  OUTPUT: boolean

  RETURN (
    (input.action == 'open_product_card'
     AND input.product.variant_schema IS NOT EMPTY
     AND VariantSubTable IS NOT RENDERED)
    OR
    (input.action == 'render_variant_action_panel'
     AND input.axisValues CONTAINS clothing_sizes
     AND dropdown_order != sortSizeValues(input.axisValues))
    OR
    (input.action == 'remove_variant'
     AND request.method == 'PUT'
     AND request.url MATCHES '/admin/products/{id}')
    OR
    (input.action == 'save_product'
     AND (input.payload.order_item_fields[*].validation.min_length IS string
          OR input.payload.order_item_fields[*].validation.max_length IS string
          OR input.payload.purchase_rules.max_per_member IS string
          OR input.payload.purchase_rules.max_per_order IS string
          OR input.payload.purchase_rules.max_per_club IS string
          OR input.payload.purchase_rules.min_per_club IS string))
  )
END FUNCTION
```

### Examples

- **Missing VariantSubTable**: Admin opens ProductCard for a product with `variant_schema: { "Maat": ["S", "M", "L"] }`. They see the schema editor with axes/values but cannot see the variant list, edit prices, or manage stock. Expected: VariantSubTable renders below the schema editor showing all active variants.

- **Unsorted sizes**: VariantActionPanel renders a Select dropdown for axis "Maat" with values `["L", "XS", "XL", "M", "S"]`. The dropdown shows values in this raw order. Expected: Dropdown shows `["XS", "S", "M", "L", "XL"]`.

- **Wrong DELETE endpoint**: Admin clicks "Variant verwijderen" with selected attributes `{Maat: "S", Kleur: "Rood"}`. System sends `PUT /admin/products/123 { variant_action: 'remove_variant', variant_attributes: {Maat: "S", Kleur: "Rood"} }`. Expected: System identifies the variant_id and sends `DELETE /admin/products/123/variants/456`.

- **Integer validation failure**: Admin saves a product with `order_item_fields[0].validation = { min_length: "1", max_length: "100" }` (string values from form state). Backend rejects with `"min_length must be an integer between 1 and 1000"`. Expected: Frontend coerces to proper integers before sending.

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**

- VariantSchemaEditor functionality (adding/removing axes, adding/removing values, renaming axes, validation) must continue to work exactly as today
- "Sync varianten" button must continue to call `updateVariantSchema` for top-down schema sync
- "Variant toevoegen" button in VariantActionPanel must continue to call `addVariantToProduct` for bottom-up sync
- VariantSubTable in the existing webshop-management module (`WebshopManagementPage → ProductsTab`) must function identically
- Products without `variant_schema` must continue to show only the VariantSchemaEditor without VariantSubTable
- ProductCard Formik form submission flow must continue to validate and save product-level fields
- Products with `order_item_fields` that have no validation rules, or `purchase_rules` that have no numeric constraints, must continue to save successfully

**Scope:**
All inputs that do NOT involve the five bug conditions should be completely unaffected by this fix. This includes:

- Editing product-level fields (naam, prijs, beschrijving, etc.)
- Category management
- Image upload
- Event ID selection
- VariantSchemaEditor axis/value editing
- Products without variants

## Hypothesized Root Cause

Based on the bug description and code analysis, the root causes are:

1. **Missing VariantSubTable Integration**: `ProductCard.tsx` imports and renders `VariantSchemaEditor` but never imports or renders `VariantSubTable`. The component exists in a different module (`webshop-management`) and was built as part of a separate spec without being wired into the products module's ProductCard. The ProductCard also lacks the state management (fetching variants, handling refetch) that VariantSubTable requires.

2. **Missing Size Sorting in VariantActionPanel**: The `VariantActionPanel` component at line 519 in `VariantSchemaEditor.tsx` iterates over `values.map((val) => <option>)` directly from the `schema` prop without sorting. The `sortSizeValues` utility exists in `webshop-management/utils/sizeSorter.ts` but is not imported or used in the products module.

3. **Incorrect removeVariantFromProduct Implementation**: The `removeVariantFromProduct` function in `productApi.ts` sends a PUT request with `variant_action: 'remove_variant'` payload — an approach that was designed before the `admin_delete_variant` handler was deployed. The correct approach is to use `deleteVariant(productId, variantId)` from `adminApi.ts` which sends `DELETE /admin/products/{id}/variants/{vid}`. However, this requires knowing the `variant_id` rather than just `variant_attributes`, which means the removal flow in VariantActionPanel needs access to the variant list.

4. **String-typed Numeric Values in Product Payload**: Chakra UI's `NumberInput` `onChange` callback provides the value as a string. While `PurchaseRulesEditor` correctly uses `parseInt(valueStr, 10)`, the issue arises when:
   - Values loaded from DynamoDB come back as `Decimal` types (serialized to JSON as numbers, but may be stored inconsistently)
   - Formik `initialValues` may contain string representations if the API response is not properly typed
   - The `onSubmit` handler in ProductCard passes `cleanValues` to `onSave` without explicit integer coercion for nested objects (`order_item_fields[].validation.*`, `purchase_rules.*`)
   - The `OrderItemFieldsEditor`'s `TextValidationInputs` uses `parseInt(rawValue, 10)` but the parsed value gets stored back into the object tree — if Formik re-serializes or if initial load had strings, the backend's strict `isinstance(value, int)` check fails

## Correctness Properties

Property 1: Bug Condition - VariantSubTable Renders for Products with Variants

_For any_ product where `variant_schema` is defined and has at least one axis with values, the ProductCard modal SHALL render the `VariantSubTable` component below the Variant Schema section, fetching and displaying all active variants with inline management capabilities.

**Validates: Requirements 2.1, 2.4**

Property 2: Bug Condition - Size Values Sorted in Dropdowns

_For any_ axis in the VariantActionPanel Select dropdowns, the values SHALL be sorted using `sortSizeValues` logic: recognized clothing sizes in standard order (XXS→5XL), then unrecognized non-numeric alphabetically, then numeric values in ascending order.

**Validates: Requirements 2.2**

Property 3: Bug Condition - Correct DELETE Endpoint for Variant Removal

_For any_ variant removal action triggered from the VariantActionPanel, the system SHALL call `deleteVariant(productId, variantId)` sending a DELETE request to `/admin/products/{id}/variants/{vid}` instead of the incorrect PUT with `variant_action` payload.

**Validates: Requirements 2.3**

Property 4: Bug Condition - Integer Coercion on Product Save

_For any_ product save where `order_item_fields` contain validation rules with numeric constraints (min_length, max_length, minimum, maximum) or `purchase_rules` contain numeric constraints (max_per_order, max_per_member, max_per_club, min_per_club), the submitted JSON payload SHALL contain these values as proper integers (not strings), ensuring backend validation passes.

**Validates: Requirements 2.5**

Property 5: Preservation - Existing ProductCard Behavior Unchanged

_For any_ product operation that does NOT involve the four bug conditions (opening a product without variants, editing product-level fields, using VariantSchemaEditor axes/values, sync varianten, variant toevoegen via VariantActionPanel), the system SHALL produce exactly the same behavior as the original code.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**File**: `frontend/src/modules/products/components/ProductCard.tsx`

**Changes**:

1. **Import VariantSubTable**: Import `VariantSubTable` from `../../webshop-management/components/VariantSubTable.tsx` and supporting types (`AdminVariant`, `AdminProduct`).
2. **Import adminApi functions**: Import `getAdminProducts`, `deleteVariant` from `../../webshop-management/services/adminApi.ts` for fetching variants.
3. **Add variant state management**: Add `useState` for `variants: AdminVariant[]`, `isLoadingVariants: boolean`, and a `fetchVariants` callback that calls the admin products API to get variant data for the current product.
4. **Render VariantSubTable**: Below the VariantSchemaEditor `CollapsibleSection`, conditionally render VariantSubTable when `variant_schema` has at least one axis with values. Pass the product, variants, and refetch callback.
5. **Add integer coercion in onSubmit**: Before calling `onSave(cleanValues)`, recursively coerce numeric fields in `order_item_fields[].validation` and `purchase_rules` to integers using `parseInt`/`Number`.

**File**: `frontend/src/modules/products/components/VariantSchemaEditor.tsx`

**Changes**:

1. **Import sortSizeValues**: Import from `../../webshop-management/utils/sizeSorter.ts`.
2. **Sort dropdown values**: In the `VariantActionPanel` component, replace `values.map(...)` in the Select rendering with `sortSizeValues(values).map(...)` to sort axis values before display.
3. **Update removeVariant flow**: The `onRemoveVariant` prop needs to change from attribute-based removal to ID-based deletion. This requires either:
   - Passing the variant list to VariantActionPanel so it can resolve attributes → variant_id, OR
   - Keeping the attribute-based approach but having the parent (ProductCard) resolve the variant_id and call `deleteVariant` instead

**File**: `frontend/src/modules/products/api/productApi.ts`

**Changes**:

1. **Deprecate removeVariantFromProduct**: Mark as deprecated or remove. The VariantActionPanel "Variant verwijderen" button should use `deleteVariant` from `adminApi.ts` instead.

**File**: `frontend/src/modules/products/components/ProductCard.tsx` (onSubmit)

**Changes**:

1. **Coerce order_item_fields validation values**: Before submission, iterate `order_item_fields` and ensure `validation.min_length`, `validation.max_length`, `validation.minimum`, `validation.maximum` are proper integers/numbers (not strings).
2. **Coerce purchase_rules numeric values**: Before submission, ensure `purchase_rules.max_per_order`, `purchase_rules.max_per_member`, `purchase_rules.max_per_club`, `purchase_rules.min_per_club` are proper integers (not strings).

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bugs on unfixed code, then verify the fixes work correctly and preserve existing behavior.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bugs BEFORE implementing the fix. Confirm or refute the root cause analysis.

**Test Plan**: Write tests that verify the current defective behavior of each bug condition. Run these on the UNFIXED code to confirm our root cause analysis.

**Test Cases**:

1. **VariantSubTable Missing Test**: Render ProductCard with a product that has `variant_schema: { Maat: ["S", "M", "L"] }`. Assert that no VariantSubTable is rendered (will confirm on unfixed code).
2. **Unsorted Sizes Test**: Render VariantActionPanel with values `["XL", "S", "M", "XS", "L"]`. Assert dropdown options are in raw order (will confirm on unfixed code).
3. **Wrong Endpoint Test**: Call `removeVariantFromProduct("prod-1", {Maat: "S"})` and assert it sends a PUT request (will confirm on unfixed code).
4. **String Integer Test**: Build a payload with `{ order_item_fields: [{ validation: { min_length: "1" } }] }` and assert the backend rejects it (will confirm on unfixed code).

**Expected Counterexamples**:

- VariantSubTable component is not in the ProductCard render tree
- Dropdown values match raw array order, not sorted
- HTTP method is PUT instead of DELETE
- Backend returns 400 with "min_length must be an integer between 1 and 1000"

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed function produces the expected behavior.

**Pseudocode:**

```
FOR ALL input WHERE isBugCondition(input) DO
  result := fixedComponent(input)
  ASSERT expectedBehavior(result)
END FOR
```

Specifically:

- For any product with non-empty variant_schema → VariantSubTable is rendered
- For any axis values array → Select options are in sortSizeValues order
- For any variant removal → DELETE request sent to correct endpoint
- For any product save with numeric constraints → values are proper integers in the request body

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed function produces the same result as the original function.

**Pseudocode:**

```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT originalComponent(input) = fixedComponent(input)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:

- It generates many test cases automatically across the input domain
- It catches edge cases that manual unit tests might miss
- It provides strong guarantees that behavior is unchanged for all non-buggy inputs

**Test Plan**: Observe behavior on UNFIXED code first for non-variant interactions, then write property-based tests capturing that behavior continues to work after the fix.

**Test Cases**:

1. **Schema Editor Preservation**: Verify that VariantSchemaEditor axes/values editing continues to work (add axis, remove axis, add value, remove value)
2. **Sync Varianten Preservation**: Verify that the "Sync varianten" button continues to call `updateVariantSchema`
3. **Add Variant Preservation**: Verify that "Variant toevoegen" in VariantActionPanel continues to call `addVariantToProduct`
4. **Form Submission Preservation**: Verify that saving a product without variants continues to work exactly as before
5. **No-Variant Product Preservation**: Verify that ProductCard for a product without `variant_schema` does not render VariantSubTable

### Unit Tests

- Test `sortSizeValues` integration in VariantActionPanel dropdown rendering
- Test integer coercion utility function with various edge cases (empty string, undefined, valid number string, already-integer)
- Test that VariantSubTable receives correct props when rendered in ProductCard
- Test that `deleteVariant` is called with correct productId and variantId on removal

### Property-Based Tests

- Generate random arrays of size strings and verify `sortSizeValues` produces correct ordering (existing tests in `sizeSorter.property.test.ts`)
- Generate random `order_item_fields` validation objects with mixed string/integer values and verify coercion produces all-integer output
- Generate random `purchase_rules` objects with mixed string/integer values and verify coercion produces all-integer output
- Generate random product payloads and verify non-variant fields pass through unchanged after coercion

### Integration Tests

- Test full ProductCard render with variant data, verifying VariantSubTable appears and functions
- Test variant removal flow end-to-end: select values in VariantActionPanel → click remove → verify correct API call
- Test product save with `order_item_fields` and `purchase_rules` → verify backend accepts the payload
- Test that WebshopManagementPage's VariantSubTable is unaffected by the ProductCard integration
