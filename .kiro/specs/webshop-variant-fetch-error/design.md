# Webshop Variant Fetch Error Bugfix Design

## Overview

Product cards in the H-DCN webshop display "variant_fetch_error" instead of variant options because `ProductCard.tsx` incorrectly unpacks the API response. The response from `ApiService.get()` has shape `{ success: true, data: { product_id, variants: [...], total_count } }`, but the code assigns `response.data` (the entire object) instead of `response.data.variants` (the array). The fix is a one-line change to correctly extract the nested `variants` array.

## Glossary

- **Bug_Condition (C)**: The condition that triggers the bug — when `ApiService.get()` returns a successful response containing a `data.variants` array, and `ProductCard.tsx` assigns the entire `data` object instead of `data.variants`
- **Property (P)**: The desired behavior — `variantData` must be the `VariantRecord[]` array from `response.data.variants`, not the wrapping object
- **Preservation**: Existing error handling behavior (failed requests showing error state), empty variant arrays, and skip-fetching logic must remain unchanged
- **ApiResponse\<T\>**: The generic wrapper type from `apiService.ts` with shape `{ success: boolean, data?: T, error?: string }`
- **VariantRecord**: A single variant entry containing `variant_id`, `variant_attributes`, `stock`, `price`, and `allow_oversell`
- **productService.getVariants()**: The service method in `frontend/src/modules/webshop/services/api.ts` that calls `ApiService.get<VariantRecord[]>()` for a given product ID
- **extractVariants**: The inline logic in `ProductCard.tsx` that unpacks the API response into a `VariantRecord[]`

## Bug Details

### Bug Condition

The bug manifests when `productService.getVariants()` returns a successful `ApiResponse` object. The response chain produces `{ success: true, data: { product_id, variants: [...], total_count } }`, but the unpacking logic `response?.data || []` assigns the entire `data` object (not the `variants` array) to `variantData`. Since an object is not iterable as `VariantRecord[]`, the VariantSelector receives invalid data and the error state triggers.

**Formal Specification:**

```
FUNCTION isBugCondition(input)
  INPUT: input of type ApiResponse<{ product_id: string, variants: VariantRecord[], total_count: number }>
  OUTPUT: boolean

  RETURN input.success = true
         AND input.data IS object
         AND input.data.variants IS array
         AND Array.isArray(input.data) = false
END FUNCTION
```

### Examples

- **Product with variants (e.g., T-shirt with size/color)**: Backend returns `{ success: true, data: { product_id: "p1", variants: [{variant_id: "v1", variant_attributes: {Maat: "L"}, stock: 5, ...}], total_count: 3 } }`. Code assigns `{ product_id, variants, total_count }` object as `variantData` → VariantSelector receives an object instead of an array → "variant_fetch_error" displayed.
- **Product without variant_schema (default variant)**: Same response structure, `variantData.find(...)` called on an object → TypeError or no match → error state triggered, no default variant selected.
- **Product with empty variants array**: Backend returns `{ success: true, data: { product_id: "p2", variants: [], total_count: 0 } }`. Code assigns `{ product_id, variants: [], total_count: 0 }` → same problem, but less visible since no variants to display anyway.
- **API failure (network/auth error)**: `productService.getVariants()` throws → catch block correctly sets `variantFetchError=true` → this path is unaffected by the bug.

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**

- When `productService.getVariants()` throws an error (network failure, auth failure), the catch block must continue to set `variantFetchError=true` and display the error message
- When `isOpen=false` or `product` is null, the variant fetch useEffect must continue to skip execution entirely
- When variants are loaded and a variant is selected, the add-to-cart flow must continue to work exactly as before
- When the backend returns an empty variants array, the empty state must be handled gracefully (empty `[]` assigned to `variants`)
- When a product without `variant_schema` loads, the default variant auto-selection logic must continue to work (finding variant with empty `variant_attributes`)

**Scope:**
All inputs that do NOT involve a successful API response with a nested `data.variants` array should be completely unaffected by this fix. This includes:

- API failures (catch path)
- Skipped fetches (no product or not open)
- Any direct array responses (the `Array.isArray(response)` guard, though this path is not currently exercised)

## Hypothesized Root Cause

Based on the code analysis, the root cause is confirmed (not just hypothesized):

1. **Incorrect property access depth**: The backend `get_variants` handler returns `create_success_response({ product_id, variants: [...], total_count })`. The `ApiService.get()` wraps this as `{ success: true, data: { product_id, variants: [...], total_count } }`. The unpacking line `response?.data || []` accesses one level too shallow — it gets the wrapper object instead of the nested `variants` array.

2. **Type mismatch assumption**: The code was likely written assuming `ApiService.get<VariantRecord[]>()` would place the array directly at `response.data`. In reality, the backend wraps its payload in an additional object layer containing `product_id`, `variants`, and `total_count`.

3. **Missing TypeScript enforcement**: The `response` is typed as `any` in the `.then()` callback, bypassing type checking that would have caught the structural mismatch at compile time.

## Correctness Properties

Property 1: Bug Condition - Correct variant array extraction

_For any_ successful API response where `response.data` is an object containing a `variants` array (isBugCondition returns true), the fixed extraction logic SHALL assign `response.data.variants` (the actual `VariantRecord[]` array) to `variantData`, ensuring `Array.isArray(variantData)` is true and each element has the `VariantRecord` shape.

**Validates: Requirements 2.1, 2.2**

Property 2: Preservation - Error and skip behavior unchanged

_For any_ input where the bug condition does NOT hold (API failure, missing product, closed modal), the fixed code SHALL produce exactly the same behavior as the original code, preserving error state handling, fetch skipping, and empty-array assignment.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

## Fix Implementation

### Changes Required

**File**: `frontend/src/modules/webshop/components/ProductCard.tsx`

**Function**: `useEffect` variant fetching hook (lines ~87-120)

**Specific Changes**:

1. **Fix response unpacking (line ~99, first `.then()` block)**: Change from:

   ```typescript
   const variantData = Array.isArray(response)
     ? response
     : response?.data || [];
   ```

   To:

   ```typescript
   const variantData = Array.isArray(response)
     ? response
     : response?.data?.variants || [];
   ```

2. **Fix response unpacking (line ~112, second `.then()` block)**: The same pattern appears in the else branch for products without `variant_schema`. Change from:

   ```typescript
   const variantData = Array.isArray(response)
     ? response
     : response?.data || [];
   ```

   To:

   ```typescript
   const variantData = Array.isArray(response)
     ? response
     : response?.data?.variants || [];
   ```

3. **Optional improvement - Add type safety**: Replace `(response: any)` with proper typing to prevent similar regressions:

   ```typescript
   .then((response: ApiResponse<{ product_id: string; variants: VariantRecord[]; total_count: number }>) => {
   ```

4. **Optional improvement - Defensive fallback**: Add a guard for cases where `response.data.variants` might not exist:
   ```typescript
   const variantData = Array.isArray(response)
     ? response
     : Array.isArray(response?.data?.variants)
       ? response.data.variants
       : [];
   ```

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code, then verify the fix works correctly and preserves existing behavior.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm the root cause analysis by observing that the unfixed code assigns an object instead of an array.

**Test Plan**: Write unit tests that mock `productService.getVariants()` to return the real API response shape, render `ProductCard`, and assert the variant state. Run on UNFIXED code to observe failures.

**Test Cases**:

1. **Product with variant_schema**: Mock response `{ success: true, data: { product_id: "p1", variants: [{...}], total_count: 1 } }` → assert VariantSelector receives an array (will fail on unfixed code — receives object)
2. **Product without variant_schema (default variant)**: Mock same response shape → assert default variant is auto-selected (will fail on unfixed code — `.find()` called on object)
3. **Multiple variants**: Mock response with 3 variants → assert all 3 are passed to VariantSelector (will fail on unfixed code)
4. **Empty variants array**: Mock response `{ success: true, data: { product_id: "p1", variants: [], total_count: 0 } }` → assert empty array assigned (will fail on unfixed code — object assigned)

**Expected Counterexamples**:

- `variantData` is `{ product_id, variants, total_count }` object instead of `VariantRecord[]` array
- `Array.isArray(variantData)` returns false
- `variantData.find(...)` throws or returns undefined because it's called on an object

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed extraction produces the correct `VariantRecord[]` array.

**Pseudocode:**

```
FOR ALL response WHERE isBugCondition(response) DO
  variantData := extractVariants_fixed(response)
  ASSERT Array.isArray(variantData) = true
  ASSERT variantData = response.data.variants
  ASSERT variantData.length = response.data.total_count
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed function produces the same result as the original function.

**Pseudocode:**

```
FOR ALL response WHERE NOT isBugCondition(response) DO
  ASSERT extractVariants_original(response) = extractVariants_fixed(response)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:

- It generates many response shapes automatically (null, undefined, error objects, direct arrays)
- It catches edge cases in the fallback logic (`|| []`)
- It provides strong guarantees that non-buggy paths remain unchanged

**Test Plan**: Extract the variant unpacking logic into a testable pure function, observe behavior on UNFIXED code for non-bug-condition inputs, then verify the fixed version produces identical results.

**Test Cases**:

1. **API failure preservation**: Verify that when `getVariants()` rejects, `variantFetchError` is still set to `true` after the fix
2. **Null/undefined response preservation**: Verify `response?.data?.variants || []` still falls back to `[]` when response is null/undefined
3. **Direct array response preservation**: Verify `Array.isArray(response)` guard still works for direct array inputs
4. **Modal closed preservation**: Verify that closing the modal still prevents variant fetching

### Unit Tests

- Test the extraction logic in isolation with various response shapes
- Test ProductCard rendering with mocked successful variant response
- Test ProductCard rendering with mocked failed response (error state)
- Test default variant auto-selection when product has no `variant_schema`
- Test that VariantSelector receives a proper `VariantRecord[]` array

### Property-Based Tests

- Generate random `ApiResponse` objects with valid `{ product_id, variants, total_count }` structure → verify extraction always produces the correct `variants` array
- Generate random non-bug-condition inputs (nulls, errors, direct arrays) → verify preservation of original behavior
- Generate random `VariantRecord[]` arrays of varying lengths → verify the extracted array length matches `total_count`

### Integration Tests

- Test full ProductCard → VariantSelector flow with real-shaped API mock data
- Test that selecting a variant after successful fetch enables add-to-cart
- Test that "variant_fetch_error" message no longer appears for valid responses
- Test the complete flow for products with and without `variant_schema`
