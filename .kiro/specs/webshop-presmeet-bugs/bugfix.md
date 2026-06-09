# Bugfix Requirements Document

## Introduction

Three related bugs in the H-DCN portal affect the Webshop and PresMeet modules. The webshop product filter is non-functional because the `scan_product` endpoint omits `groep` and `subgroep` fields. Product images are not displayed because the same endpoint omits the `images` field. The PresMeet page shows a "Fout bij laden PresMeet Network Error" when no order exists for a club because the backend returns a 404 that the frontend does not handle gracefully.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN the webshop page loads products via the `GET /scan-product/` endpoint THEN the system returns product objects without `groep` and `subgroep` fields, causing the ProductFilter component to render an empty filter tree

1.2 WHEN the webshop page loads products via the `GET /scan-product/` endpoint THEN the system returns product objects without the `images` field, causing the ProductCard component to display "Geen afbeelding" instead of actual product images

1.3 WHEN a club has no existing PresMeet order and the user opens the PresMeet page THEN the `GET /presmeet/orders` endpoint returns HTTP 404 ("Booking not found"), which is not handled by the Axios interceptor or the PresMeetPage error handling, resulting in the error message "Fout bij laden PresMeet Network Error"

### Expected Behavior (Correct)

2.1 WHEN the webshop page loads products via the `GET /scan-product/` endpoint THEN the system SHALL return product objects including `groep` and `subgroep` fields so the ProductFilter can build its group/subgroup filter tree

2.2 WHEN the webshop page loads products via the `GET /scan-product/` endpoint THEN the system SHALL return product objects including the `images` field so the ProductCard can display product images

2.3 WHEN a club has no existing PresMeet order and the user opens the PresMeet page THEN the system SHALL handle the absence of an order gracefully by either returning an empty/draft order structure (backend) or catching the 404 response and showing an empty booking state (frontend), without displaying an error message to the user

### Unchanged Behavior (Regression Prevention)

3.1 WHEN the `scan_product` endpoint returns products with existing fields (product_id, name, price, variant_schema, is_parent, event_id, active) THEN the system SHALL CONTINUE TO return these fields correctly with proper Decimal-to-number conversion

3.2 WHEN the `get_products` endpoint (`GET /products`) is called THEN the system SHALL CONTINUE TO return all fields (including groep, subgroep, images) as it currently does

3.3 WHEN a club HAS an existing PresMeet order THEN the `GET /presmeet/orders` endpoint SHALL CONTINUE TO return the order data successfully with HTTP 200

3.4 WHEN a user lacks PresMeet access (no Regio_Pressmeet or Regio_All role) THEN the system SHALL CONTINUE TO return HTTP 403 with "PresMeet access required"

3.5 WHEN a user has no club assignment THEN the system SHALL CONTINUE TO return HTTP 403 with "Missing club assignment" and the frontend SHALL CONTINUE TO show the onboarding flow

3.6 WHEN the ProductFilter component receives products with groep/subgroep data THEN the system SHALL CONTINUE TO build the filter tree, apply group/subgroup filtering, and highlight selected filters correctly

3.7 WHEN product images are available and the URLs are valid S3 paths THEN the ProductCard SHALL CONTINUE TO render the image carousel with navigation controls

---

## Bug Condition Derivation

### Bug 1 & 2: Missing fields in scan_product response

```pascal
FUNCTION isBugCondition_ScanProduct(X)
  INPUT: X of type ScanProductRequest
  OUTPUT: boolean

  // The bug always triggers: scan_product never returns groep/subgroep/images
  RETURN TRUE
END FUNCTION
```

```pascal
// Property: Fix Checking - scan_product includes groep, subgroep, images
FOR ALL X WHERE isBugCondition_ScanProduct(X) DO
  response ← scan_product'(X)
  FOR ALL product IN response.items DO
    ASSERT product HAS FIELD "groep"
    ASSERT product HAS FIELD "subgroep"
    ASSERT product HAS FIELD "images"
  END FOR
END FOR
```

```pascal
// Property: Preservation Checking - existing fields unchanged
FOR ALL X WHERE NOT isBugCondition_ScanProduct(X) DO
  ASSERT scan_product(X) = scan_product'(X)
END FOR
```

### Bug 3: PresMeet 404 when no order exists

```pascal
FUNCTION isBugCondition_PresMeet(X)
  INPUT: X of type PresMeetOrderRequest
  OUTPUT: boolean

  // Bug triggers when the club has no existing order in the Orders table
  RETURN X.club_has_order = FALSE AND X.has_presmeet_access = TRUE AND X.has_club_assignment = TRUE
END FUNCTION
```

```pascal
// Property: Fix Checking - No order returns empty state, not error
FOR ALL X WHERE isBugCondition_PresMeet(X) DO
  result ← getPresMeetBooking'(X)
  ASSERT result.status_code ≠ 404
  ASSERT no_error_shown_to_user(result)
  ASSERT (result.status_code = 200 AND result.body IS empty_order_structure)
    OR (frontend_handles_404_gracefully(result))
END FOR
```

```pascal
// Property: Preservation Checking - Existing orders still returned correctly
FOR ALL X WHERE NOT isBugCondition_PresMeet(X) DO
  ASSERT getPresMeetBooking(X) = getPresMeetBooking'(X)
END FOR
```
