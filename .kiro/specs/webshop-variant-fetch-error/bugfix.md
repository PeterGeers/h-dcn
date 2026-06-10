# Bugfix Requirements Document

## Introduction

Product cards in the H-DCN webshop display a "variant_fetch_error" message where variant options should appear, even when the backend successfully returns variant data. The root cause is incorrect response unpacking in `ProductCard.tsx`: the code treats `response.data` (an object with shape `{ product_id, variants, total_count }`) as if it were a direct array of variants, causing the VariantSelector to receive the wrong data shape and the error state to trigger.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN the backend returns a successful variant response with shape `{ success: true, data: { product_id, variants: [...], total_count } }` AND the product has a `variant_schema` THEN the system passes the entire `data` object (not the `variants` array) to the VariantSelector component, resulting in no variant options rendered and the "variant_fetch_error" message displayed

1.2 WHEN the backend returns a successful variant response AND the product does NOT have a `variant_schema` THEN the system cannot find a default variant in the malformed data, leaving the card in a broken state with "variant_fetch_error" displayed

1.3 WHEN the API call fails entirely (auth error, network error) THEN the system sets `variantFetchError=true` and displays the error message (this behavior is correct but included for completeness)

### Expected Behavior (Correct)

2.1 WHEN the backend returns a successful variant response with shape `{ success: true, data: { product_id, variants: [...], total_count } }` AND the product has a `variant_schema` THEN the system SHALL extract `response.data.variants` as the variants array and pass it to the VariantSelector component, rendering variant options correctly

2.2 WHEN the backend returns a successful variant response AND the product does NOT have a `variant_schema` THEN the system SHALL extract `response.data.variants` as the variants array and auto-select the default variant (the one with empty `variant_attributes`)

2.3 WHEN the API call fails entirely (auth error, network error) THEN the system SHALL continue to set `variantFetchError=true` and display the error message

### Unchanged Behavior (Regression Prevention)

3.1 WHEN the backend returns a successful response with an empty variants array `{ success: true, data: { product_id, variants: [], total_count: 0 } }` THEN the system SHALL CONTINUE TO set variants to an empty array and handle the empty state gracefully

3.2 WHEN the product card is closed (`isOpen=false`) or no product is selected THEN the system SHALL CONTINUE TO skip variant fetching entirely

3.3 WHEN a variant is successfully loaded and selected THEN the system SHALL CONTINUE TO enable the add-to-cart functionality as before

3.4 WHEN the backend returns an error HTTP status (4xx, 5xx) THEN the system SHALL CONTINUE TO display the variant_fetch_error message

---

## Bug Condition (Formal)

```pascal
FUNCTION isBugCondition(X)
  INPUT: X of type VariantFetchResponse
  OUTPUT: boolean

  // The bug triggers when the API returns successfully but the code
  // unpacks response.data (an object) instead of response.data.variants (an array)
  RETURN X.success = true
     AND X.data IS object
     AND X.data.variants IS array
END FUNCTION
```

```pascal
// Property: Fix Checking - Correct variant extraction
FOR ALL X WHERE isBugCondition(X) DO
  variantData ← extractVariants'(X)
  ASSERT variantData = X.data.variants
  ASSERT Array.isArray(variantData)
END FOR
```

```pascal
// Property: Preservation Checking - Failed requests still show error
FOR ALL X WHERE NOT isBugCondition(X) DO
  ASSERT extractVariants(X) = extractVariants'(X)
END FOR
```
