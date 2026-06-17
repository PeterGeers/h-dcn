# Bugfix Requirements Document

## Introduction

The `product-variant-stock-management` spec built a full `VariantSubTable` component with inline price editing, oversell toggles, deactivation/deletion, size sorting, stock management, and an AddVariantForm — but none of it was wired into the actual product management UI (`ProductCard`). Additionally, the `VariantActionPanel` Select dropdowns in `VariantSchemaEditor` display size values in raw/unsorted order, and the `removeVariantFromProduct` function in `productApi.ts` uses an incorrect API call pattern (PUT with `variant_action` payload) instead of the deployed `admin_delete_variant` DELETE endpoint. The result is that admins cannot manage individual variants from the product editing interface, size dropdowns are confusing, and variant removal may silently fail.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN the admin opens a ProductCard modal and views the Variant Schema section THEN the system does NOT render the VariantSubTable component, making all variant management features (inline price editing, oversell toggle, deactivation, deletion, stock management) invisible and inaccessible to the admin.

1.2 WHEN the VariantActionPanel renders Select dropdowns for axes containing clothing sizes (e.g., "XS", "S", "M", "L", "XL") THEN the system displays values in their raw array order from `variant_schema` rather than logical clothing size order.

1.3 WHEN the admin uses the "Variant verwijderen" button in the VariantActionPanel THEN the system calls `removeVariantFromProduct` which sends a PUT request to `/admin/products/{id}` with `{ variant_action: 'remove_variant', variant_attributes: {...} }` instead of calling the deployed `admin_delete_variant` handler at `DELETE /admin/products/{id}/variants/{vid}`.

1.4 WHEN the admin wants to see variant stock levels, edit variant prices inline, or toggle oversell for individual variants THEN the system provides no UI to do so from the ProductCard, despite the VariantSubTable component existing with all these capabilities fully implemented.

1.5 WHEN the admin saves a product that has existing `order_item_fields` with validation rules (e.g., min_length=1, max_length=100) or `purchase_rules` (e.g., max_per_member=5) THEN the backend returns a validation error claiming values are invalid (e.g., "min_length must be between 1 and 1000", "max_per_member must be an integer") even though the values in the record are valid integers. The error response is not displayed in a user-friendly way — the admin cannot copy the text and there is no console message, only a raw JSON-like error referencing field indices (e.g., "order_item_fields[0].validation.min_length", "fields[9]", "purchase_rules.max_per_member").

### Expected Behavior (Correct)

2.1 WHEN the admin opens a ProductCard modal for a product that has a `variant_schema` with at least one axis containing values THEN the system SHALL render the VariantSubTable component (below the Variant Schema section) showing all active variants with inline editing capabilities, fetching variants from the admin API.

2.2 WHEN the VariantActionPanel renders Select dropdowns for any axis THEN the system SHALL sort the dropdown values using the `sortSizeValues` utility, displaying clothing sizes in logical order (XXS, XS, S, M, L, XL, XXL, 3XL, 4XL, 5XL) and numeric values in ascending numeric order.

2.3 WHEN the admin uses the "Variant verwijderen" button in the VariantActionPanel THEN the system SHALL call `deleteVariant(productId, variantId)` from `adminApi.ts` which sends a DELETE request to `/admin/products/{id}/variants/{vid}`, using the deployed `admin_delete_variant` backend handler.

2.4 WHEN the VariantSubTable is rendered inside ProductCard THEN the system SHALL provide inline price editing, oversell toggle, deactivate/delete actions, add stock, and add variant functionality — all already implemented in the VariantSubTable component — directly within the product editing modal.

2.5 WHEN the admin saves a product that has `order_item_fields` with validation rules or `purchase_rules` with numeric constraints THEN the system SHALL send these values as proper integers (not strings) to the backend, and the backend SHALL accept valid integer values without returning spurious validation errors. IF validation fails, the error SHALL be displayed in a readable toast or alert with clear field names — not raw JSON with array indices.

### Unchanged Behavior (Regression Prevention)

3.1 WHEN the admin edits the variant_schema axes and values in the VariantSchemaEditor (adding/removing axes, adding/removing values, renaming axes) THEN the system SHALL CONTINUE TO update the variant_schema form field and validate combinations as it does today.

3.2 WHEN the admin clicks "Sync varianten" in the VariantSchemaEditor THEN the system SHALL CONTINUE TO call `updateVariantSchema` to regenerate variants from the schema via the existing top-down sync flow.

3.3 WHEN the admin uses the "Variant toevoegen" button in the VariantActionPanel THEN the system SHALL CONTINUE TO call `addVariantToProduct` to create a single variant via bottom-up sync (this function's behavior is correct).

3.4 WHEN the VariantSubTable is used in the existing webshop-management module (WebshopManagementPage → ProductsTab) THEN the system SHALL CONTINUE TO function identically — the integration into ProductCard must not alter VariantSubTable's own behavior or API.

3.5 WHEN a product has no `variant_schema` or an empty variant_schema THEN the system SHALL CONTINUE TO show only the VariantSchemaEditor without rendering VariantSubTable (no variants to display).

3.6 WHEN the ProductCard form is submitted (save product) THEN the system SHALL CONTINUE TO validate and save product-level fields exactly as today — the addition of VariantSubTable SHALL NOT interfere with the Formik form submission flow.

3.7 WHEN the admin saves a product with `order_item_fields` that have no validation rules, or `purchase_rules` that have no numeric constraints THEN the system SHALL CONTINUE TO save successfully without introducing new validation requirements that weren't there before.
