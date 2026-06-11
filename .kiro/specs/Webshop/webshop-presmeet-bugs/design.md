# Webshop & PresMeet Bugfix Design

## Overview

Three related bugs degrade the Webshop and PresMeet user experience. The `scan_product` Lambda handler omits `groep`, `subgroep`, and `images` fields from its normalized response, rendering the product filter empty and product images invisible. Separately, the PresMeet booking flow returns HTTP 404 when no order exists for a club, which the frontend does not handle gracefully—resulting in a confusing "Network Error" message. The fix adds the missing fields to `scan_product` and introduces a frontend-side 404 handler in PresMeetPage that treats "no booking" as a valid empty state.

## Glossary

- **Bug_Condition (C)**: The condition that triggers the bug—either a `scan_product` response missing fields, or a `get_presmeet_booking` 404 when no order exists
- **Property (P)**: The desired behavior—products include `groep`/`subgroep`/`images`; absence of an order shows empty booking state (no error)
- **Preservation**: Existing behaviors that must remain unchanged—current field handling in `scan_product`, existing order retrieval in `get_presmeet_booking`, 403 handling in PresMeetPage
- **scan_product**: Lambda handler in `backend/handler/scan_product/app.py` that returns all active products for the webshop
- **get_presmeet_booking**: Lambda handler in `backend/handler/get_presmeet_booking/app.py` that returns a club's PresMeet order
- **PresMeetPage**: React page component at `frontend/src/modules/presmeet/PresMeetPage.tsx` that orchestrates PresMeet data loading
- **presmeetApi**: Axios client at `frontend/src/modules/presmeet/services/presmeetApi.ts` with interceptors for 401/403/409

## Bug Details

### Bug Condition

The bugs manifest in two independent scenarios:

1. **scan_product missing fields**: Every call to `GET /scan-product/` returns products without `groep`, `subgroep`, and `images`. This is unconditional—the bug triggers on every request because these fields are simply not included in the normalized response dict.

2. **PresMeet 404 unhandled**: When a club has no existing order in the Orders table and a user with valid PresMeet access opens the PresMeet page, the backend returns 404 ("Booking not found"). The Axios interceptor only transforms 409 and 403; the 404 passes through as a raw AxiosError. The PresMeetPage catch block only checks `isAuthorizationError` (type === 'AUTHORIZATION_ERROR'), so the 404 falls to the outer catch and displays a generic error.

**Formal Specification:**

```
FUNCTION isBugCondition_ScanProduct(request)
  INPUT: request of type ScanProductRequest
  OUTPUT: boolean

  // The bug is unconditional — scan_product never includes these fields
  RETURN TRUE
END FUNCTION

FUNCTION isBugCondition_PresMeet(request)
  INPUT: request of type PresMeetOrderRequest
  OUTPUT: boolean

  RETURN request.user_has_presmeet_access = TRUE
         AND request.user_has_club_assignment = TRUE
         AND request.club_has_existing_order = FALSE
END FUNCTION
```

### Examples

- **Bug 1**: User opens webshop → `scan_product` returns `[{product_id: "p1", name: "Polo", price: 35, ...}]` without `groep`/`subgroep` → ProductFilter renders empty tree → user cannot filter by category
- **Bug 2**: Same response lacks `images` field → ProductCard's `product.images || product.image` evaluates to `undefined` → placeholder "Geen afbeelding" shown even though images exist in DynamoDB
- **Bug 3**: New club opens PresMeet → backend returns `{statusCode: 404, body: {message: "Booking not found"}}` → Axios interceptor does not transform it → PresMeetPage outer catch displays "Fout bij laden PresMeet Network Error"
- **Non-bug**: Club WITH existing order → backend returns 200 with order data → page loads correctly (this must be preserved)

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**

- Existing fields in `scan_product` response (`product_id`, `name`, `price`, `variant_schema`, `is_parent`, `event_id`, `active`) must continue to return correctly with Decimal-to-number conversion
- `get_products` endpoint must continue to return all fields including `groep`, `subgroep`, `images` as it currently does
- When a club HAS an existing PresMeet order, `get_presmeet_booking` must continue to return 200 with order data
- HTTP 403 responses ("PresMeet access required", "Missing club assignment") must continue to be handled correctly by the frontend—showing appropriate error or onboarding flow
- ProductFilter component must continue to build filter tree correctly when `groep`/`subgroep` data is present
- ProductCard image carousel must continue to work when `images` contains valid S3 URLs
- The Axios interceptor must continue to transform 409 (VersionConflictError) and 403 (AuthorizationError)

**Scope:**
All inputs that do NOT involve the bug conditions should be completely unaffected:

- Authenticated requests that already have orders
- Non-scan-product endpoints (`get_products`, admin endpoints)
- 403 and 409 error paths in PresMeet
- Mouse/keyboard interactions unrelated to data loading

## Hypothesized Root Cause

Based on code analysis, the root causes are confirmed:

1. **scan_product incomplete normalization** (`backend/handler/scan_product/app.py`, lines 84-93): The normalized dict was written with only 7 fields. The `get_products` handler (which works correctly) includes `groep`, `subgroep`, and `images` in its response. The `scan_product` handler simply never added them—likely an oversight when the normalization logic was written or when these fields were introduced later.

2. **PresMeet 404 falls through error handling** (`backend/handler/get_presmeet_booking/app.py`, line 107): When `items` is empty after scanning, the handler returns `create_error_response(404, 'Booking not found')`. On the frontend:
   - `presmeetApi.ts` interceptor only transforms 409 and 403 into structured errors; 404 passes as raw AxiosError
   - `PresMeetPage.tsx` inner catch checks `isAuthorizationError(orderErr)` (checks for `type === 'AUTHORIZATION_ERROR'`) and `orderErr?.response?.status === 403`
   - A 404 matches neither condition → `throw orderErr` → outer catch → `setError(message)` where message resolves to "Fout bij laden PresMeet Network Error"

3. **Missing 404 semantic**: The API uses 404 to mean "no order yet" which is a valid user state, not an error. The frontend must distinguish this from actual errors.

## Correctness Properties

Property 1: Bug Condition - scan_product includes groep, subgroep, images

_For any_ request to the scan_product endpoint, the fixed handler SHALL return product objects that include `groep`, `subgroep`, and `images` fields (with values from DynamoDB, defaulting to `None`/`[]` when absent in the database record).

**Validates: Requirements 2.1, 2.2**

Property 2: Bug Condition - PresMeet 404 handled as empty state

_For any_ PresMeet order request where the user has valid access and club assignment but no existing order, the frontend SHALL treat the 404 response as a "no order yet" state and display an empty booking view without showing an error message to the user.

**Validates: Requirements 2.3**

Property 3: Preservation - scan_product existing fields unchanged

_For any_ request to the scan_product endpoint, the fixed handler SHALL continue to return `product_id`, `name`, `price`, `variant_schema`, `is_parent`, `event_id`, and `active` fields with identical values and Decimal-to-number conversion as before the fix.

**Validates: Requirements 3.1, 3.2**

Property 4: Preservation - PresMeet existing order retrieval unchanged

_For any_ PresMeet order request where the club HAS an existing order, the fixed system SHALL return the same 200 response with order data as before the fix. HTTP 403 responses for missing access or club assignment SHALL continue to trigger appropriate error/onboarding flows.

**Validates: Requirements 3.3, 3.4, 3.5**

## Fix Implementation

### Changes Required

**File**: `backend/handler/scan_product/app.py`

**Function**: `lambda_handler` — normalized response construction (lines 84-93)

**Specific Changes**:

1. **Add `groep` field**: Add `'groep': item.get('groep')` to the normalized dict
2. **Add `subgroep` field**: Add `'subgroep': item.get('subgroep')` to the normalized dict
3. **Add `images` field**: Add `'images': item.get('images', [])` to the normalized dict (default to empty list, matching `get_products` behavior)

---

**File**: `frontend/src/modules/presmeet/PresMeetPage.tsx`

**Function**: `loadPageData` — inner try/catch for order loading (around line 140)

**Specific Changes**: 4. **Add 404 detection**: After the `isAuthorizationError` check and the raw 403 check, add a condition for 404 responses:

```typescript
} else if (orderErr?.response?.status === 404) {
  // No order exists yet — valid state, show empty booking
  // Order remains null, which triggers the "create booking" flow
}
```

5. **Prevent throw for 404**: The 404 case should NOT throw—it should simply leave `order` as null and allow the component to render the empty/new-booking state

### Implementation Notes

- The frontend fix is preferred over changing the backend API contract (returning 200 with empty structure) because:
  - 404 is semantically correct ("resource not found")
  - Other API consumers may depend on the 404 behavior
  - Frontend-only change is less invasive and independently deployable
- The `images` default of `[]` matches the pattern used in `get_products/app.py`
- No changes to `get_products` handler are needed—it already works correctly

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bugs on unfixed code, then verify the fixes work correctly and preserve existing behavior.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bugs BEFORE implementing the fix. Confirm the root cause analysis.

**Test Plan**: Write unit tests for `scan_product` that assert `groep`/`subgroep`/`images` are present in the response. Write a test for the PresMeet flow that simulates a 404 response and asserts no error state is set. Run on UNFIXED code to observe failures.

**Test Cases**:

1. **scan_product missing groep**: Call handler with DynamoDB items containing `groep` → assert response includes `groep` (will fail on unfixed code)
2. **scan_product missing subgroep**: Call handler with DynamoDB items containing `subgroep` → assert response includes `subgroep` (will fail on unfixed code)
3. **scan_product missing images**: Call handler with DynamoDB items containing `images` → assert response includes `images` (will fail on unfixed code)
4. **PresMeet 404 handling**: Mock presmeetApi.getOrder to reject with 404 → assert component does NOT show error message (will fail on unfixed code)

**Expected Counterexamples**:

- `scan_product` response body will contain products WITHOUT `groep`, `subgroep`, `images` keys
- PresMeet page will set error state with "Booking not found" or network error message

### Fix Checking

**Goal**: Verify that for all inputs where the bug conditions hold, the fixed functions produce the expected behavior.

**Pseudocode:**

```
// Bug 1 & 2: scan_product fields
FOR ALL request WHERE isBugCondition_ScanProduct(request) DO
  response := scan_product_fixed(request)
  FOR ALL product IN response.items DO
    ASSERT "groep" IN product.keys()
    ASSERT "subgroep" IN product.keys()
    ASSERT "images" IN product.keys()
    ASSERT type(product["images"]) = list
  END FOR
END FOR

// Bug 3: PresMeet 404
FOR ALL request WHERE isBugCondition_PresMeet(request) DO
  result := loadPageData_fixed(request)
  ASSERT result.error = null
  ASSERT result.order = null  // empty state, no error shown
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug conditions do NOT hold, the fixed functions produce the same result as the original functions.

**Pseudocode:**

```
// scan_product: existing fields preserved
FOR ALL request DO
  original_response := scan_product_original(request)
  fixed_response := scan_product_fixed(request)
  FOR ALL (orig, fixed) IN zip(original_response.items, fixed_response.items) DO
    ASSERT orig["product_id"] = fixed["product_id"]
    ASSERT orig["name"] = fixed["name"]
    ASSERT orig["price"] = fixed["price"]
    ASSERT orig["variant_schema"] = fixed["variant_schema"]
    ASSERT orig["is_parent"] = fixed["is_parent"]
    ASSERT orig["event_id"] = fixed["event_id"]
    ASSERT orig["active"] = fixed["active"]
  END FOR
END FOR

// PresMeet: existing order still works
FOR ALL request WHERE NOT isBugCondition_PresMeet(request) DO
  ASSERT get_presmeet_booking_original(request) = get_presmeet_booking_fixed(request)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking of `scan_product` because:

- It generates many product configurations (varying Decimal values, missing fields, None values)
- It catches edge cases in Decimal-to-number conversion that manual tests might miss
- It provides strong guarantees that existing field handling is unchanged across all product shapes

**Test Plan**: Observe behavior of UNFIXED `scan_product` for existing fields, then write property-based tests that confirm those fields are unchanged after adding `groep`/`subgroep`/`images`.

**Test Cases**:

1. **Existing field preservation**: Generate random DynamoDB product items → verify `product_id`, `name`, `price`, `variant_schema`, `is_parent`, `event_id`, `active` are returned identically before and after fix
2. **Decimal conversion preservation**: Generate products with various Decimal price values → verify int/float conversion logic is unchanged
3. **PresMeet 200 preservation**: Mock existing order → verify same response returned after frontend fix
4. **PresMeet 403 preservation**: Mock 403 responses → verify onboarding and error flows unchanged

### Unit Tests

- `test_scan_product_includes_groep_subgroep`: Assert fixed handler includes `groep` and `subgroep` in each product
- `test_scan_product_includes_images`: Assert fixed handler includes `images` (defaulting to `[]`)
- `test_scan_product_images_default_empty_list`: Assert products without `images` in DynamoDB get `[]` not `None`
- `test_scan_product_existing_fields_unchanged`: Assert 7 original fields remain in response
- `test_presmeet_404_shows_empty_state`: Assert PresMeetPage renders empty booking on 404
- `test_presmeet_403_still_shows_error`: Assert 403 handling unchanged
- `test_presmeet_existing_order_loads`: Assert 200 with order data still works

### Property-Based Tests

- Generate random product dicts with varying field presence (groep present/absent, images present/absent/empty) → verify normalized output always includes all expected keys
- Generate random Decimal values for price → verify conversion to int/float is consistent
- Generate random product lists of varying length → verify all items in response include new fields

### Integration Tests

- End-to-end test: scan_product with mocked DynamoDB containing full product records → verify ProductFilter receives filterable data
- End-to-end test: scan_product with mocked DynamoDB containing products with S3 image URLs → verify ProductCard receives image data
- End-to-end test: PresMeet page load with no existing order → verify empty booking state rendered without error
- End-to-end test: PresMeet page load with existing order → verify order displayed correctly
