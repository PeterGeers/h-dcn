# Requirements Document

## Introduction

This feature completes and fixes variant management in the webshop management module. Currently, inline editing of variant properties (price, stock, allow_oversell) is broken, variant deletion shows a success toast but doesn't actually remove the variant, there is no UI for adding individual variants (bottom-up direction), and clothing sizes are not logically sorted. These issues block products from being orderable in the webshop.

The system already has backend support (`variant_sync.py`) for bidirectional sync and handlers for creating/updating variants. This spec addresses the frontend bugs, the missing delete handler/flow, the missing bottom-up variant creation UI, and size sorting logic.

## Glossary

- **Variant_Manager**: The frontend UI subsystem (VariantSubTable, AddVariantForm, BulkVariantCreator) responsible for displaying and managing product variants in the webshop management module.
- **Variant_API**: The backend Lambda handlers (`admin_update_variant`, `admin_create_variant`, `admin_bulk_create_variants`) that process variant CRUD operations.
- **Variant_Sync**: The shared backend module (`variant_sync.py`) that maintains bidirectional consistency between `variant_schema` on the parent product and individual variant records.
- **Parent_Product**: A product record with `is_parent = true` that defines the `variant_schema` (axes and values).
- **Variant_Record**: A product record with `is_parent = false` and a `parent_id` linking it to a Parent_Product. Contains `variant_attributes`, `stock`, `sold_count`, `allow_oversell`, and `prijs`.
- **variant_schema**: A map on the Parent_Product defining axes and their possible values, e.g. `{"Maat": ["S","M","L"]}`.
- **variant_attributes**: A map on a Variant_Record specifying which value the variant has for each axis, e.g. `{"Maat": "M"}`.
- **Size_Sorter**: A utility function that sorts standard clothing size values in logical order (XXS → XS → S → M → L → XL → XXL → 3XL → 4XL) rather than alphabetically.
- **Oversell**: The ability to sell a variant even when `stock` is 0, controlled by the `allow_oversell` boolean field.
- **Bottom_Up_Creation**: Adding an individual variant with specific `variant_attributes`, which triggers `sync_variant_to_schema` to update the parent's `variant_schema`.
- **Top_Down_Creation**: Generating all attribute combinations from `variant_schema` via bulk creation.

## Requirements

### Requirement 1: Inline Price Editing

**User Story:** As a webshop admin, I want to edit the price of individual variants inline in the variant table, so that I can set variant-specific pricing without navigating away.

#### Acceptance Criteria

1. WHEN the admin clicks on a variant price cell, THE Variant_Manager SHALL display an inline number input pre-filled with the current variant price value, accepting values between 0.00 and 999999.99 with a maximum of 2 decimal places.
2. WHEN the admin confirms the inline price edit (via Enter key or input blur) with a valid non-negative number, THE Variant_Manager SHALL call the Variant_API to persist the new price and display a success notification that auto-dismisses within 5 seconds.
3. WHEN the admin submits an empty price value, THE Variant_Manager SHALL set the variant price to null, causing the variant to inherit the Parent_Product price.
4. IF the admin submits a negative number, a value exceeding 999999.99, or a non-numeric value, THEN THE Variant_Manager SHALL display a validation warning and prevent the API call.
5. WHEN the admin presses Escape or clicks a cancel action during inline editing, THE Variant_Manager SHALL discard the edit and revert the cell to its previous display value without calling the API.
6. IF the Variant_API returns an error during price update, THEN THE Variant_Manager SHALL display an error notification and retain the previous price value in the UI.
7. WHEN the price is successfully updated, THE Variant_Manager SHALL refresh the variant list to reflect the persisted value.

### Requirement 2: Oversell Toggle

**User Story:** As a webshop admin, I want to toggle the allow_oversell setting per variant inline, so that I can control which variants can be sold when out of stock.

#### Acceptance Criteria

1. WHEN the admin toggles the oversell switch on a variant row, THE Variant_Manager SHALL send the updated `allow_oversell` boolean value to the Variant_API without requiring a confirmation step, and SHALL disable the toggle until the API responds.
2. WHEN the Variant_API confirms the update, THE Variant_Manager SHALL display a success notification indicating whether oversell was enabled or disabled, auto-dismiss the notification within 5 seconds, and refresh the variant data to reflect the persisted state.
3. IF the Variant_API returns an error during the oversell update, THEN THE Variant_Manager SHALL revert the switch to its previous state, re-enable the toggle, and display an error notification containing the failure reason that auto-dismisses within 5 seconds.
4. WHILE the admin lacks the `Products_CRUD` permission, THE Variant_Manager SHALL disable the oversell toggle and display a tooltip stating the specific permission name required.

### Requirement 3: Variant Deactivation and Deletion

**User Story:** As a webshop admin, I want to deactivate or delete a variant, so that I can remove variants from sale or permanently remove unused ones.

#### Acceptance Criteria

1. THE Variant_Manager SHALL display a deactivate action and a delete action on each variant row when the current admin has `Products_CRUD` permission.
2. WHEN the admin clicks the deactivate action, THE Variant_API SHALL set the variant's `active` field to `false`, making it unavailable for sale in the webshop but preserving the record for order history.
3. WHEN the admin clicks the delete action, THE Variant_API SHALL check if any Orders reference the variant's `product_id`.
4. IF orders referencing the variant exist, THEN THE Variant_API SHALL reject the deletion and return an error indicating the variant cannot be deleted because it has related orders — the admin should deactivate instead.
5. IF no orders reference the variant, THEN THE Variant_API SHALL permanently remove the variant record from the Producten table and trigger `sync_variant_to_schema` to update the parent's `variant_schema`.
6. WHEN deactivation or deletion succeeds, THE Variant_Manager SHALL update the displayed list and show a success notification.
7. IF the Variant_API returns an error, THEN THE Variant_Manager SHALL display an error notification indicating the failure reason and keep the variant visible.
8. THE Variant_Manager SHALL only display active variants (`active = true`) in the variant sub-table by default, with an option to show inactive variants.

### Requirement 4: Add Individual Variant

**User Story:** As a webshop admin, I want to add an individual variant to a product, so that I can extend the available sizes or options without regenerating all combinations.

#### Acceptance Criteria

1. THE Variant_Manager SHALL display an "Add Variant" button below the variant sub-table for admins with `Products_CRUD` permission.
2. WHEN the admin clicks "Add Variant", THE Variant_Manager SHALL display a simple form with a dropdown per axis showing existing values from `variant_schema`, plus the ability to type a new value (e.g. typing "XS" for the Maat axis).
3. WHEN the admin submits a new variant, THE Variant_API SHALL create the variant record and automatically call `sync_variant_to_schema` to update the parent's `variant_schema` with any new values.
4. IF a variant with identical `variant_attributes` already exists (active or inactive), THEN THE Variant_API SHALL return an error indicating the combination already exists.
5. WHEN variant creation succeeds, THE Variant_Manager SHALL refresh the variant list and show a success notification.
6. IF the Variant_API returns an error, THEN THE Variant_Manager SHALL display the error message and keep the form open with entered values preserved.

### Requirement 5: Clothing Size Sorting

**User Story:** As a webshop admin, I want clothing sizes to be displayed in logical order (XS, S, M, L, XL, etc.), so that the variant list is easy to read and matches industry conventions.

#### Acceptance Criteria

1. THE Size_Sorter SHALL sort values matching standard clothing size patterns (case-insensitive) in this fixed order: XXS, XS, S, M, L, XL, XXL, 3XL, 4XL, 5XL.
2. WHEN the variant list contains variants with a "Maat" (size) axis, THE Variant_Manager SHALL sort variants using the Size_Sorter for the size axis.
3. WHEN a size axis contains a mix of recognized clothing sizes and unrecognized values, THE Size_Sorter SHALL place all recognized sizes first (in standard order), followed by unrecognized values sorted case-insensitively in alphabetical order.
4. WHEN sorting variants with multiple axes, THE Variant_Manager SHALL sort by the first axis defined in the variant_schema using Size_Sorter logic, then by subsequent axes in case-insensitive alphabetical order.
5. THE Size_Sorter SHALL handle numeric size values (e.g., "38", "40", "42") by sorting them in ascending numeric order.
6. IF variant values do not match a recognized clothing size pattern and are not numeric, THEN THE Size_Sorter SHALL sort those values in case-insensitive alphabetical order.

### Requirement 6: Stock Management via Add Stock Form

**User Story:** As a webshop admin, I want to add stock to a variant, so that the variant becomes orderable in the webshop.

#### Acceptance Criteria

1. THE Variant_Manager SHALL display an "Add Stock" action per variant row that opens the AddStockForm containing a required quantity field (positive integer between 1 and 10,000).
2. WHILE the admin lacks the `Products_CRUD` permission, THE Variant_Manager SHALL disable the "Add Stock" action.
3. IF the admin submits a quantity that is zero, negative, non-integer, or exceeds 10,000, THEN THE Variant_Manager SHALL display a validation error indicating the quantity must be a whole number between 1 and 10,000, and prevent the API call.
4. WHEN the admin submits a valid stock quantity, THE Variant_API SHALL increment the variant's `stock` field by the given amount and record a stock movement.
5. WHEN stock is successfully added, THE Variant_Manager SHALL close the AddStockForm, refresh the variant list to display the updated stock count, and display a success notification including the quantity added.
6. IF the Variant_API returns an error, THEN THE Variant_Manager SHALL display an error notification with the failure reason and keep the AddStockForm open with entered values preserved.

### Requirement 7: Variant Data Refresh After Mutations

**User Story:** As a webshop admin, I want the variant list to always reflect the latest state after any mutation, so that I never see stale data.

#### Acceptance Criteria

1. WHEN any variant mutation (create, update, delete, add stock) succeeds, THE Variant_Manager SHALL re-fetch the variant list from the Variant_API.
2. WHILE the variant list is being refreshed, THE Variant_Manager SHALL display a non-blocking loading indicator that does not prevent the admin from interacting with other parts of the page.
3. WHEN the re-fetch completes, THE Variant_Manager SHALL replace the displayed variant list with the fresh data, preserving scroll position when the list container remains mounted.
4. IF the re-fetch fails, THEN THE Variant_Manager SHALL display an error notification and retain the previously displayed variant list.
