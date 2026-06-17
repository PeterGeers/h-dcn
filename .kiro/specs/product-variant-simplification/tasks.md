# Implementation Plan: Product Variant Simplification

## Overview

This plan removes the old VariantSchemaEditor and `variant_schema` approach, makes VariantSubTable + VariantEditModal the primary variant UI with create/edit modes, adds a searchable EventSelector in a CollapsibleSection, wraps images in a CollapsibleSection, fixes ProductCard layout, and derives webshop variant axes directly from variant records. Tasks are ordered to remove old code first (unblocking), then build new UI components, then wire everything together.

## Tasks

- [x] 1. Remove old variant management code (frontend cleanup)
  - [x] 1.1 Delete VariantSchemaEditor and related files
    - Delete `VariantSchemaEditor.tsx` and its test file `__tests__/VariantSchemaEditor.test.tsx`
    - Delete `AddVariantForm.tsx` (functionality merged into VariantEditModal)
    - Remove `variant_schema` from the productFields field registry (`frontend/src/config/productFields/fields.ts`)
    - Remove `updateVariantSchema`, `addVariantToProduct`, `removeVariantFromProduct` from `productApi.ts`
    - Remove all imports/references to the above in ProductCard and other components
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.10_

  - [x] 1.2 Remove navigation arrows from ProductCard
    - Remove `onNavigate` prop handling, `ChevronLeftIcon`, `ChevronRightIcon` imports and rendering
    - Remove any arrow button JSX and associated click handlers
    - _Requirements: 11.2, 11.3_

  - [x] 1.3 Fix ProductCard layout — full-width category selector
    - Remove `width="50%"` constraint on the Groep/Subgroep selector section
    - Ensure generic fields section uses full modal width
    - _Requirements: 11.1_

- [x] 2. Remove old variant management code (backend cleanup)
  - [x] 2.1 Remove variant_schema from backend handlers
    - Remove `variant_schema` from `scan_product/app.py` response mapping
    - Remove acceptance of `variant_schema` in `admin_update_product` request body
    - Remove `variant_attributes` vs `variant_schema` validation in `admin_create_variant/app.py` (keep duplicate check)
    - Delete or strip `variant_sync.py` functions (`sync_schema_to_variants`, `sync_variant_to_schema`)
    - _Requirements: 1.5, 1.6, 1.7, 1.8, 1.9_

  - [x] 2.2 Write unit tests verifying variant_schema removal
    - Test that `scan_product` response does not include `variant_schema`
    - Test that `admin_create_variant` does not validate against `variant_schema`
    - _Requirements: 1.7, 1.9_

- [x] 3. Checkpoint — Ensure old code is fully removed
  - Ensure all tests pass, ask the user if questions arise.
  - Verify zero references to `variant_schema` remain in codebase (excluding migration scripts and spec docs)

- [x] 4. Create utility functions and constants
  - [x] 4.1 Add MAX_AXES constant and deriveAxesFromVariants utility
    - Add `MAX_AXES = 2` constant to frontend (`frontend/src/config/constants.ts` or inline)
    - Create `deriveAxesFromVariants(variants: VariantRecord[]): VariantSchema` utility function (pure function, extracts axes from active variants only)
    - Add `MAX_AXES = 2` to backend (`admin_create_variant` handler or shared constants)
    - _Requirements: 4.4, 5.1_

  - [x] 4.2 Write property test for deriveAxesFromVariants
    - **Property 4: Axis derivation from active variant records**
    - Test that returned map keys match axis names from active variants only, values contain no duplicates, inactive variants excluded
    - Place in `frontend/src/__tests__/deriveAxesFromVariants.property.test.ts`
    - **Validates: Requirements 5.1, 5.3**

  - [x] 4.3 Create determineFormMode and validateAxisInput helpers
    - `determineFormMode(existingVariants)`: returns zero-axes / under-max / at-max state
    - `validateAxisInput(axisName, value)`: returns boolean, rejects empty/whitespace-only
    - Place in a shared utility file near VariantEditModal
    - _Requirements: 3.3, 4.1, 4.2_

  - [x] 4.4 Write property tests for form mode and validation helpers
    - **Property 3: Form mode determined by axis count** — verify free-text allowed when distinct axes < MAX_AXES, restricted when = MAX_AXES
    - **Property 2: Empty axis name or value is rejected** — verify whitespace-only and empty strings rejected
    - Place in `frontend/src/__tests__/VariantEditModal.property.test.ts`
    - **Validates: Requirements 3.3, 4.1, 4.2**

- [x] 5. Implement VariantEditModal create mode
  - [x] 5.1 Add create mode to VariantEditModal
    - Accept `variant: AdminVariant | null` prop (null = create mode)
    - Accept `existingVariants: AdminVariant[]` prop
    - In create mode: derive existing axes from `existingVariants` using `useMemo`
    - Implement three-state axis input logic (zero-axes: free text, under MAX_AXES: dropdown + free text option, at MAX_AXES: dropdown only)
    - Free-text input for value in all states
    - Validate non-empty axis name and value before submission
    - Submit calls `POST /products/:id/variants` with `variant_attributes`
    - Use Chakra UI v2 components with dark theme tokens (gray.800 background, orange.400 accent)
    - _Requirements: 3.1, 3.2, 3.3, 4.1, 4.2, 4.3, 4.5, 9.1_

  - [x] 5.2 Handle duplicate variant error (409) in VariantEditModal
    - On 409 response, display toast "Variant bestaat al" with backend error message
    - Keep form open with values preserved on any network error
    - _Requirements: 12.2_

  - [x] 5.3 Write unit tests for VariantEditModal create mode
    - Test zero-axes state renders free text inputs
    - Test at-MAX_AXES state restricts axis to dropdown only
    - Test 409 error displays toast message
    - _Requirements: 3.1, 4.2, 12.2_

- [x] 6. Implement EventSelector with CollapsibleSection
  - [x] 6.1 Create EventSelector component
    - Implement searchable dropdown with Chakra UI `Input` for search filter
    - Render checkbox list filtered by search text (case-insensitive substring match)
    - Always include "Webshop (algemeen)" as first option with id `evt-webshop`
    - Support `events`, `selectedIds`, `onChange`, `isLoading`, `isDisabled` props
    - Use dark theme tokens (gray.800 background, orange.400 accent)
    - _Requirements: 6.5, 6.6, 6.7, 6.8, 9.2_

  - [x] 6.2 Wrap EventSelector in CollapsibleSection ("Evenementen")
    - Create or reuse `CollapsibleSection` wrapper component
    - Collapsed state: show selected events as tags/badges in header; placeholder text when none selected
    - Expanded state: reveal full EventSelector
    - Same expand/collapse animation and styling as OrderItemFieldsEditor/PurchaseRulesEditor sections
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [x] 6.3 Write property tests for EventSelector filter and collapsed display
    - **Property 5: Event search filter correctness** — filter returns exactly events whose name contains search string (case-insensitive)
    - **Property 6: Collapsed event display matches selection** — one tag per selected event, label matches event name
    - Place in `frontend/src/__tests__/EventSelector.property.test.ts`
    - **Validates: Requirements 6.2, 6.3, 6.6**

  - [x] 6.4 Write unit tests for EventSelector
    - Test checkboxes render for each event
    - Test collapsed state shows tags for selected events
    - Test collapsed state shows placeholder when no events selected
    - _Requirements: 6.2, 6.3, 6.5, 6.7_

- [x] 7. Implement images CollapsibleSection
  - [x] 7.1 Wrap product images in CollapsibleSection ("Afbeeldingen")
    - Wrap existing image upload/preview/delete UI in a CollapsibleSection titled "Afbeeldingen"
    - Default to collapsed when no images present, expanded when images exist
    - Same styling/animation as other collapsible sections
    - _Requirements: 10.1, 10.2, 10.3_

  - [x] 7.2 Write property test for CollapsibleSection default state
    - **Property 7: CollapsibleSection default state follows data** — expanded iff images array non-empty, collapsed if empty/absent
    - Place in `frontend/src/__tests__/CollapsibleSection.property.test.ts`
    - **Validates: Requirements 10.2**

- [x] 8. Checkpoint — Ensure new components work in isolation
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Wire components into ProductCard
  - [x] 9.1 Integrate VariantSubTable and VariantEditModal in ProductCard
    - Fetch variants unconditionally for parent products
    - Display VariantSubTable always visible (not collapsible)
    - On row click: open VariantEditModal in edit mode (pass variant)
    - On "Add variant" click: open VariantEditModal in create mode (pass null, pass existingVariants)
    - On modal success: refresh variant list
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 9.2 Integrate EventSelector CollapsibleSection in ProductCard
    - Add CollapsibleSection "Evenementen" with EventSelector
    - Wire `selectedIds` to Formik `event_ids` field
    - Wire `onChange` to update Formik state
    - Fetch events list for dropdown population
    - _Requirements: 6.1, 6.8_

  - [x] 9.3 Integrate images CollapsibleSection in ProductCard
    - Move existing image UI into CollapsibleSection "Afbeeldingen"
    - Ensure upload, preview, delete functionality preserved
    - _Requirements: 10.1_

  - [x] 9.4 Verify preserved fields and editors remain
    - Confirm naam, artikelcode, prijs, groep, subgroep fields render and validate
    - Confirm OrderItemFieldsEditor and PurchaseRulesEditor continue rendering in their positions
    - _Requirements: 7.1, 7.2, 7.3, 8.1, 8.2_

  - [x] 9.5 Write unit tests for ProductCard integration
    - Test ProductCard renders VariantSubTable
    - Test ProductCard does NOT render VariantSchemaEditor
    - Test ProductCard has no navigation arrows
    - Test images wrapped in CollapsibleSection
    - _Requirements: 1.1, 2.1, 10.1, 11.2_

- [x] 10. Implement backend duplicate variant prevention
  - [x] 10.1 Add duplicate check to admin_create_variant handler
    - Scan existing variants for parent product
    - Compare `variant_attributes` of new request against existing variants
    - Return 409 with descriptive error message if duplicate found
    - Keep existing 400 (missing fields) and 404 (parent not found) responses
    - _Requirements: 12.1_

  - [x] 10.2 Write property test for duplicate variant rejection
    - **Property 8: Duplicate variant attributes rejected** — identical `variant_attributes` for same parent returns 409
    - Place in `backend/tests/unit/test_admin_create_variant_properties.py`
    - **Validates: Requirements 12.1**

  - [x] 10.3 Write property test for attribute preservation
    - **Property 1: Variant creation preserves submitted attributes** — created Variant_Record contains exactly the submitted axis-value pairs
    - Place in `backend/tests/unit/test_admin_create_variant_properties.py`
    - **Validates: Requirements 3.2, 4.5**

- [x] 11. Modify webshop VariantSelector to derive axes from records
  - [x] 11.1 Update VariantSelector to use deriveAxesFromVariants
    - Remove `variantSchema` prop dependency
    - Use `deriveAxesFromVariants(variants)` to compute axis→values map from active variant records
    - Update VariantSelector props interface to accept `variants: VariantRecord[]` instead of schema
    - _Requirements: 5.1, 5.2, 5.3_

  - [x] 11.2 Write unit test for VariantSelector derivation
    - Test that deactivated variants are excluded from axis display
    - Test that axis values correctly aggregate from active records
    - _Requirements: 5.1, 5.3_

- [x] 12. Final checkpoint — Full integration verification
  - Ensure all tests pass, ask the user if questions arise.
  - Verify no `variant_schema` references remain (grep codebase excluding specs/migrations)
  - Verify dark theme compliance (no custom CSS, Chakra UI v2 only)

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases

### Steering Documents (follow during implementation)

| Steering file                        | Applies to                      | Key points                                                                                            |
| ------------------------------------ | ------------------------------- | ----------------------------------------------------------------------------------------------------- |
| `.kiro/steering/look-and-feel.md`    | All frontend UI tasks           | Dark theme tokens, card/modal/table patterns, icon colors, responsive rules                           |
| `.kiro/steering/testing-frontend.md` | All frontend test tasks         | Always `--watchAll=false` + `--testPathPattern`, never full suite, `npx tsc --noEmit` for type checks |
| `.kiro/steering/testing-backend.md`  | All backend test tasks          | `importlib.util` handler imports, `mock_aws` context, patch auth as `'app'` module                    |
| `.kiro/steering/tech.md`             | All tasks                       | Tech stack, common commands, file size guidelines                                                     |
| `.kiro/steering/structure.md`        | All tasks                       | Project structure, handler pattern, naming conventions                                                |
| `.kiro/steering/schema-driven.md`    | Field registry tasks (1.1, 4.1) | Never invent field names, registry is source of truth                                                 |
| `.kiro/steering/aws-dynamodb.md`     | Backend tasks (2.1, 10.1)       | Table conventions, SAM template rules, `--profile nonprofit-deploy`                                   |
| `.kiro/steering/authentication.md`   | Backend handler tasks           | `extract_user_credentials` → `validate_permissions_with_regions` pattern                              |
| `.kiro/steering/guardrails.md`       | All tasks                       | Only fix what's asked, no dangerous fallbacks, deploy via scripts only                                |
| `.kiro/steering/product.md`          | Context                         | Domain overview, key concepts                                                                         |

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3", "2.1"] },
    { "id": 1, "tasks": ["2.2", "4.1"] },
    { "id": 2, "tasks": ["4.2", "4.3"] },
    { "id": 3, "tasks": ["4.4", "5.1", "6.1", "7.1"] },
    { "id": 4, "tasks": ["5.2", "5.3", "6.2", "6.3", "6.4", "7.2", "10.1"] },
    { "id": 5, "tasks": ["9.1", "9.2", "9.3", "9.4", "10.2", "10.3", "11.1"] },
    { "id": 6, "tasks": ["9.5", "11.2"] }
  ]
}
```
