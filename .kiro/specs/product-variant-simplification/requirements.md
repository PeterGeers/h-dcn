# Requirements Document

## Introduction

Simplification of the product variant management UI in the admin portal. The current VariantSchemaEditor is confusing and broken — it will be removed entirely along with the `variant_schema` field on parent products. Variant management moves to a direct table-based approach where admins add/edit variants inline. The webshop derives available axes/values directly from variant records at display time — no sync logic needed.

## Glossary

- **ProductCard**: The modal component (`ProductCard.tsx`) for creating and editing products in the admin interface.
- **VariantSubTable**: The table component displaying all variant records for a parent product.
- **VariantEditModal**: The modal for creating and editing a single variant. Opens in create mode (empty, with axis name/value inputs) when adding a new variant, or in edit mode (pre-filled with variant data) when clicking an existing variant row.
- **Variant_Record**: A DynamoDB item in the Producten table with `is_parent=false` and a `parent_id` referencing the parent product.
- **Parent_Product**: A DynamoDB item in the Producten table with `is_parent=true`, representing the base product.
- **Variant_Schema**: A field on the Parent_Product (`variant_schema`) that maps axis names to lists of values, e.g. `{"Maat": ["S","M","L"], "Kleur": ["Rood","Blauw"]}`.
- **Axis**: A dimension of variation (e.g., "Maat", "Kleur"). Maximum 2 axes per product.
- **MAX_AXES**: A configurable constant defining the maximum number of variant axes allowed per product. Currently set to 2.
- **Event_Selector**: A searchable dropdown with checkboxes for selecting events to associate with a product.
- **CollapsibleSection**: A reusable wrapper component that shows a header with a title (and optional summary content) in collapsed state, and reveals its full content when expanded. Used for Bestelvelden, Aankoopregels, Afbeeldingen, and Evenementen.
- **OrderItemFieldsEditor**: The editor for bestelvelden (order item fields) configuration per product.
- **PurchaseRulesEditor**: The editor for aankoopregels (purchase rules) configuration per product.
- **Variant_Sync**: The backend module (`variant_sync.py`) that rebuilds the parent's `variant_schema` from all active variant records.

## Requirements

### Requirement 1: Remove Old Variant Management System (Cleanup)

**User Story:** As a developer, I want all code, data fields, and UI related to the old VariantSchemaEditor and variant_schema approach removed, so that there is one clean approach to variant management.

#### Acceptance Criteria

**Frontend removal:**

1. THE ProductCard SHALL NOT render the VariantSchemaEditor component or display a "Sync varianten" button.
2. THE file `VariantSchemaEditor.tsx` and any associated test files SHALL be deleted.
3. THE productApi.ts file SHALL NOT export `updateVariantSchema`, `addVariantToProduct`, or `removeVariantFromProduct` functions.
4. THE ProductCard SHALL NOT import or reference any of the above.

**Backend removal:** 5. THE `variant_sync.py` module's `sync_schema_to_variants` and `sync_variant_to_schema` functions SHALL be removed. 6. THE `admin_update_product` handler SHALL NOT accept `variant_schema` in the request body. 7. THE `admin_create_variant` handler SHALL NOT validate variant_attributes against a `variant_schema` field — only check for duplicates. 8. THE Backend SHALL NOT store, update, or return a `variant_schema` field on Parent_Product records. 9. THE Backend `scan_product` endpoint SHALL NOT include `variant_schema` in its response.

**Schema/types removal:** 10. THE `variant_schema` field SHALL be removed from the Producten field registry (TypeScript types, productFields config, and any schema definitions). 11. WHEN the feature is complete, THE Codebase SHALL contain zero references to `variant_schema` except in migration/cleanup scripts.

### Requirement 2: Variant Sub-Table as Primary Variant UI

**User Story:** As an admin, I want to see and manage all variants for a product in a single table, so that I have a clear overview of all variant records.

#### Acceptance Criteria

1. THE ProductCard SHALL display the VariantSubTable within its variant management section, showing all existing Variant_Records for the current Parent_Product.
2. WHEN a Variant_Record exists, THE VariantSubTable SHALL display the axis names and values from `variant_attributes` for each row.
3. WHEN a user clicks a variant row in the VariantSubTable, THE ProductCard SHALL open the VariantEditModal for that specific Variant_Record.
4. THE VariantSubTable SHALL display variant stock, sold_count, prijs, allow_oversell, and active status for each Variant_Record.

### Requirement 3: VariantEditModal Create Mode — Zero Axes State

**User Story:** As an admin, I want to create the first variant for a product by specifying both axis name and value, so that I establish the initial variant dimension.

#### Acceptance Criteria

1. WHEN no Variant_Records exist for the Parent_Product AND the user clicks "Add variant", THE VariantEditModal SHALL open in create mode and display a free-text input for the axis name AND a free-text input for the value.
2. WHEN the user submits the VariantEditModal in create mode with a new axis name and value, THE System SHALL create a Variant_Record with `variant_attributes` containing that axis-value pair.
3. WHEN the user submits the VariantEditModal in create mode, THE VariantEditModal SHALL validate that both the axis name and value are non-empty strings.

### Requirement 4: VariantEditModal Create Mode — Existing Axes

**User Story:** As an admin, I want to add variants using existing axes or create new axes (up to the maximum), so that I can expand the product's variant dimensions in a controlled way.

#### Acceptance Criteria

1. WHEN the user clicks "Add variant" AND fewer than MAX_AXES axes exist across all Variant_Records, THE VariantEditModal SHALL open in create mode and allow the user to either select an existing axis name OR type a new axis name (free text).
2. WHEN the user clicks "Add variant" AND MAX_AXES axes already exist across all Variant_Records, THE VariantEditModal SHALL open in create mode and only allow the user to select from the existing axis names (no free text for new axis).
3. THE VariantEditModal in create mode SHALL display a free-text input for the variant value under the selected or newly typed axis.
4. THE System SHALL define MAX_AXES as a configurable constant with a default value of 2.
5. WHEN the user submits the form in create mode, THE System SHALL create a Variant_Record with `variant_attributes` containing the chosen axis-value pair.

### Requirement 5: Webshop Derives Variant Axes from Records

**User Story:** As a customer browsing the webshop, I want to see the available variant options (e.g., size, colour) derived directly from active variant records, so that the options always reflect the current state without relying on a cached schema.

#### Acceptance Criteria

1. THE Webshop VariantSelector SHALL derive available axis names and values by aggregating `variant_attributes` from all active Variant_Records for the product.
2. THE Webshop VariantSelector SHALL NOT read or depend on a `variant_schema` field on the Parent_Product.
3. WHEN a Variant_Record is deactivated or deleted by an admin, THE Webshop SHALL no longer display that variant's attribute values in the axis selectors (on next page load).
4. THE Backend `scan_product` endpoint SHALL NOT include `variant_schema` in its response (field removed from parent products).

### Requirement 6: Event Selection via Searchable Dropdown in Collapsible Section

**User Story:** As an admin, I want to associate a product with events using a searchable dropdown wrapped in a collapsible section, so that the ProductCard stays uncluttered and I can quickly see which events are selected without opening the editor.

#### Acceptance Criteria

1. THE ProductCard SHALL wrap the Event_Selector component inside a CollapsibleSection with the title "Evenementen".
2. WHILE the CollapsibleSection is collapsed, THE CollapsibleSection SHALL display the currently selected events as tags or badges in the collapsed header area.
3. WHILE the CollapsibleSection is collapsed AND no events are selected, THE CollapsibleSection SHALL display a placeholder text indicating no events are selected.
4. THE CollapsibleSection for events SHALL behave identically to the OrderItemFieldsEditor and PurchaseRulesEditor collapsible sections (same expand/collapse animation and styling).
5. WHEN the user expands the CollapsibleSection, THE Event_Selector SHALL display a searchable dropdown with checkboxes for selecting events.
6. WHEN the user types in the Event_Selector search input, THE Event_Selector SHALL filter the displayed event list to show only events whose name contains the typed text (case-insensitive).
7. THE Event_Selector SHALL display a checkbox next to each event, allowing the user to select or deselect multiple events.
8. WHEN the user selects or deselects an event checkbox, THE Event_Selector SHALL update the product's event association immediately in the form state.

### Requirement 7: Product Generic Fields Preserved

**User Story:** As an admin, I want the core product fields (naam, artikelcode, prijs, groep, subgroep) to remain unchanged, so that existing product management workflows continue to work.

#### Acceptance Criteria

1. THE ProductCard SHALL display editable fields for naam, artikelcode, prijs, groep, and subgroep in its generic product section.
2. THE ProductCard SHALL validate required fields using the productFields registry configuration.
3. THE ProductCard SHALL use the field names exactly as defined in the Producten schema (naam, artikelcode, prijs, groep, subgroep).

### Requirement 8: OrderItemFieldsEditor and PurchaseRulesEditor Preserved

**User Story:** As an admin, I want the bestelvelden and aankoopregels editors to continue working as before, so that I can still configure order item fields and purchase rules.

#### Acceptance Criteria

1. THE ProductCard SHALL continue to render the OrderItemFieldsEditor component in its current position and behavior.
2. THE ProductCard SHALL continue to render the PurchaseRulesEditor component in its current position and behavior.

### Requirement 9: Dark Theme UI Compliance

**User Story:** As a user, I want the simplified variant management UI to follow the existing dark theme conventions, so that the interface looks consistent.

#### Acceptance Criteria

1. THE VariantEditModal SHALL use Chakra UI v2 components with the project's dark theme tokens (gray.800 background, orange.400 borders for focus/accent).
2. THE Event_Selector SHALL use Chakra UI v2 components with the project's dark theme tokens.
3. THE ProductCard SHALL NOT introduce custom CSS or external UI libraries beyond Chakra UI v2.

### Requirement 10: Product Images in Collapsible Section

**User Story:** As an admin, I want the product images section in a collapsible panel like Bestelvelden and Aankoopregels, so that the ProductCard modal is less cluttered and consistent.

#### Acceptance Criteria

1. THE ProductCard SHALL wrap the product images UI (upload, preview, delete) inside a CollapsibleSection component with the title "Afbeeldingen".
2. THE CollapsibleSection for images SHALL default to collapsed when no images are present, and expanded when images exist.
3. THE images CollapsibleSection SHALL behave identically to the OrderItemFieldsEditor and PurchaseRulesEditor collapsible sections (same expand/collapse animation and styling).

### Requirement 11: ProductCard Layout Fixes

**User Story:** As an admin, I want the ProductCard modal to use its full width and remove broken navigation arrows, so that the UI is clean and usable.

#### Acceptance Criteria

1. THE ProductCard generic fields section (Groep/Subgroep selector) SHALL use the full width of the modal, not half-width.
2. THE ProductCard SHALL NOT render left/right navigation arrows (the previous/next product arrows that no longer function).
3. THE code for the navigation arrows (onNavigate prop, ChevronLeftIcon, ChevronRightIcon handlers) SHALL be removed from ProductCard.

### Requirement 12: Duplicate Variant Prevention

**User Story:** As an admin, I want to be prevented from creating a variant with the same attribute combination that already exists, so that data integrity is maintained.

#### Acceptance Criteria

1. WHEN the user attempts to create a Variant_Record with `variant_attributes` identical to an existing Variant_Record for the same Parent_Product, THE Backend SHALL reject the request with a 409 status code and a descriptive error message.
2. IF the backend returns a duplicate variant error, THEN THE VariantEditModal SHALL display the error message to the user.
