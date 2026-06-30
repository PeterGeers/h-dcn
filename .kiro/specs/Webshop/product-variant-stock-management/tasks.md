# Implementation Plan: Product Variant Stock Management

## Overview

Fix broken inline editing (field name mismatch price→prijs), add variant lifecycle actions (deactivation, deletion, individual creation), implement size sorting, and wire up stock management UI. The backend already has most infrastructure — work focuses on fixing field names, adding a delete handler, building an AddVariantForm, and implementing a sizeSorter utility.

## Tasks

- [x] 1. Fix field name mismatch (price → prijs) across backend and frontend
  - [x] 1.1 Update `admin_update_variant` handler UPDATABLE_VARIANT_FIELDS from `'price'` to `'prijs'`
    - In `backend/handler/admin_update_variant/app.py`, change `UPDATABLE_VARIANT_FIELDS` list entry from `'price'` to `'prijs'`
    - Verify the handler reads the field from request body and passes it to DynamoDB update expression correctly
    - _Requirements: 1.1, 1.2, 1.3_

  - [x] 1.2 Update `variant_sync.py` to create variants with `prijs` instead of `price`
    - In the shared variant_sync module, find where new variant records are built and change `price` key to `prijs`
    - Ensure `sync_variant_to_schema` and any variant creation logic uses `prijs`
    - _Requirements: 1.1, 1.2, 1.3_

  - [x] 1.3 Update frontend `AdminVariant` type and `updateVariant()` API call to use `prijs`
    - Update the TypeScript type definition for `AdminVariant` (rename `price` field to `prijs`)
    - Update `updateVariant()` in `adminApi.ts` to send `{ prijs: value }` instead of `{ price: value }`
    - Verify the HTTP method (PUT) matches the SAM template route configuration
    - Fix any other references in the frontend that use the old `price` field name on variants
    - _Requirements: 1.1, 1.2, 1.3, 1.6, 1.7_

  - [x] 1.4 Write data migration script to rename `price` → `prijs` on existing variant records
    - Create `scripts/migrate_variant_price_field.py`
    - Scan Producten table for items where `is_parent = false` and `price` attribute exists
    - For each record: copy `price` value to `prijs`, then remove `price` attribute
    - Include dry-run mode (default) and --apply flag for actual execution
    - Log all changes for audit trail
    - _Requirements: 1.1, 1.2_

- [x] 2. Checkpoint - Verify field name fix
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. Implement size sorting utility
  - [x] 3.1 Create `sizeSorter.ts` utility with `sortSizeValues` and `sortVariants` functions
    - Create file at `frontend/src/modules/webshop-management/utils/sizeSorter.ts`
    - Implement `SIZE_ORDER` priority map (xxs=1 through 5xl=10)
    - Implement `sortSizeValues(values: string[]): string[]` — sorts recognized clothing sizes first in standard order, then unrecognized non-numeric alphabetically, then numeric values in ascending numeric order
    - Implement `sortVariants(variants: AdminVariant[], variantSchema: Record<string, string[]>): AdminVariant[]` — sorts by first axis using sizeSorter logic, then subsequent axes alphabetically
    - Handle case-insensitive matching for size recognition
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

  - [x] 3.2 Write property test: Size sort preserves set membership (Property 1)
    - **Property 1: Size sort preserves set membership**
    - **Validates: Requirements 5.1, 5.3, 5.5, 5.6**
    - Create `frontend/src/modules/webshop-management/utils/sizeSorter.test.ts`
    - Use fast-check to generate arbitrary string arrays
    - Assert sorted output has same length and same multiset of values as input

  - [x] 3.3 Write property test: Recognized sizes precede unrecognized and are in standard order (Property 2)
    - **Property 2: Recognized sizes are in standard order and precede unrecognized values**
    - **Validates: Requirements 5.1, 5.3, 5.6**
    - Generate mixed arrays of recognized sizes and random strings
    - Assert: all recognized sizes appear before unrecognized, recognized are in XXS→5XL order, unrecognized non-numeric are in case-insensitive alphabetical order

  - [x] 3.4 Write property test: Numeric values sort numerically (Property 3)
    - **Property 3: Numeric values sort numerically**
    - **Validates: Requirements 5.5**
    - Generate arrays of numeric strings (e.g. "38", "40", "9", "100")
    - Assert sorted output is in ascending numeric order (not lexicographic)

  - [x] 3.5 Write property test: Sort is idempotent (Property 4)
    - **Property 4: Sort is idempotent**
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.5, 5.6**
    - Generate arbitrary string arrays
    - Assert `sortSizeValues(sortSizeValues(xs))` equals `sortSizeValues(xs)`

- [x] 4. Implement admin_delete_variant backend handler
  - [x] 4.1 Create `admin_delete_variant` handler with order reference check
    - Create `backend/handler/admin_delete_variant/app.py`
    - Implement auth check requiring `Products_CRUD` permission
    - Parse `product_id` and `variant_id` from path parameters
    - Verify variant exists in Producten table and `parent_id` matches product
    - Scan Orders table for any `line_items[].variant_id` matching the variant
    - If orders found: return 409 Conflict with message indicating order count
    - If no orders: delete variant record, call `sync_variant_to_schema` to rebuild parent schema
    - Return 200 on success
    - Use `os.environ.get('PRODUCTEN_TABLE_NAME', 'Producten')` and `os.environ.get('ORDERS_TABLE_NAME', 'Orders')` for table names
    - _Requirements: 3.3, 3.4, 3.5_

  - [x] 4.2 Add SAM template resource and API Gateway route for admin_delete_variant
    - Add Lambda function resource to `backend/template.yaml`
    - Configure DELETE method at `/admin/products/{id}/variants/{vid}`
    - Add environment variables for PRODUCTEN_TABLE_NAME and ORDERS_TABLE_NAME
    - Grant DynamoDB read/write on Producten and read on Orders
    - _Requirements: 3.3, 3.4, 3.5_

  - [x] 4.3 Write property test: Delete correctness depends on order references (Property 6)
    - **Property 6: Delete correctness depends on order references**
    - **Validates: Requirements 3.3, 3.4, 3.5**
    - Create `backend/tests/unit/test_admin_delete_variant_properties.py`
    - Use hypothesis + moto to generate variant records and optional order references
    - Assert: delete succeeds iff no orders reference the variant; returns 409 otherwise; record unchanged on rejection

- [x] 5. Checkpoint - Verify backend changes
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement deactivate/delete actions in VariantSubTable
  - [x] 6.1 Add deactivate and delete action buttons to VariantSubTable rows
    - Add a deactivate button (sets `active: false` via existing `updateVariant` API)
    - Add a delete button that calls new `deleteVariant` API function — use DeleteIcon (red, size xs) with Tooltip and aria-label per look-and-feel steering
    - Both actions require `Products_CRUD` permission — hide/disable if user lacks it
    - Show confirmation dialog before delete action
    - Handle 409 response from delete (show toast suggesting deactivation instead)
    - Call `onUpdate()` callback after successful deactivation or deletion
    - Follow `.kiro/steering/look-and-feel.md` for icon colors, dark theme, and component patterns
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

  - [x] 6.2 Add `deleteVariant` function to `adminApi.ts`
    - Add `deleteVariant(productId: string, variantId: string): Promise<void>` using DELETE method
    - URL-encode path parameters
    - _Requirements: 3.3, 3.5_

  - [x] 6.3 Add "show inactive" toggle to VariantSubTable
    - Default: only show variants where `active !== false`
    - Add toggle switch above the table to include inactive variants
    - Style inactive variants with reduced opacity or strikethrough
    - _Requirements: 3.8_

- [x] 7. Implement AddVariantForm component
  - [x] 7.1 Create AddVariantForm modal component
    - Create component at appropriate path in `frontend/src/modules/webshop-management/`
    - Props: `productId`, `variantSchema`, `onSuccess`, `isDisabled`
    - Render one CreatableSelect (or Input with datalist) per axis from variant_schema
    - Show existing values as dropdown options, allow typing new values
    - Submit calls `createVariant(productId, { variant_attributes: {...} })`
    - On success: call `onSuccess()`, close modal, show success toast
    - On error: show error toast, keep form open with values preserved
    - Handle duplicate attribute error (409) gracefully
    - Follow `.kiro/steering/look-and-feel.md`: modal positioning, dark theme (gray.800 bg, orange.400 borders), VStack spacing={4}, AddIcon=green for submit button
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

  - [x] 7.2 Wire AddVariantForm into VariantSubTable with "Add Variant" button
    - Add "Add Variant" button below the variant sub-table
    - Only show for admins with `Products_CRUD` permission
    - Opens AddVariantForm as a modal
    - Pass `onUpdate` as `onSuccess` to trigger data refresh after creation
    - _Requirements: 4.1, 4.5_

- [x] 8. Fix inline editing and integrate size sorting
  - [x] 8.1 Fix inline price editing to use `prijs` field and add validation
    - Ensure inline number input reads from and writes to `prijs` field
    - Accept values 0.00–999999.99, max 2 decimal places
    - Empty value sends `prijs: null` (inherit parent price)
    - Reject negative, >999999.99, or non-numeric input with validation warning
    - Escape key / cancel reverts without API call
    - On API error: show error toast, revert to previous value
    - On success: show success toast (auto-dismiss 5s), refresh variant list
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7_

  - [x] 8.2 Fix oversell toggle to use correct field and add optimistic revert
    - Ensure toggle sends `{ allow_oversell: boolean }` to updateVariant
    - Disable toggle while API call is in flight
    - On error: revert switch to previous state, show error toast
    - On success: show success toast, refresh variant list
    - Disable toggle + show tooltip when user lacks `Products_CRUD` permission
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 8.3 Integrate sizeSorter into VariantSubTable rendering
    - Import `sortVariants` from sizeSorter utility
    - Sort variant list before rendering using parent's `variant_schema` for axis order
    - _Requirements: 5.2, 5.4_

- [x] 9. Implement AddStockForm and stock management UI
  - [x] 9.1 Add "Add Stock" action to variant rows and wire AddStockForm
    - Add "Add Stock" button/action per variant row in VariantSubTable
    - Disable for users without `Products_CRUD` permission
    - Opens AddStockForm (existing or create simple form component)
    - Quantity field: positive integer, 1–10,000, validated client-side
    - Reject zero, negative, non-integer, or >10,000 with validation error
    - On submit: call add-stock API endpoint
    - On success: close form, refresh variant list, show success toast with quantity added
    - On error: show error toast, keep form open with values preserved
    - Follow `.kiro/steering/look-and-feel.md`: AddIcon=green for action, modal/form patterns, dark theme styling
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

- [x] 10. Implement variant data refresh after mutations
  - [x] 10.1 Ensure all mutation flows trigger variant list re-fetch
    - Verify `onUpdate()` is called after: price edit, oversell toggle, deactivate, delete, create variant, add stock
    - Show non-blocking loading indicator during re-fetch
    - Preserve scroll position when list container remains mounted
    - On re-fetch failure: show error toast, retain previously displayed data
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [x] 11. Checkpoint - Backend property tests
  - [x] 11.1 Write property test: Variant deactivation preserves record integrity (Property 5)
    - **Property 5: Variant deactivation preserves record integrity**
    - **Validates: Requirements 3.2**
    - Create `backend/tests/unit/test_admin_update_variant_properties.py`
    - Use hypothesis + moto to generate variant records with various field values
    - Assert: setting `active=false` preserves all other fields unchanged

  - [x] 11.2 Write property test: Stock addition is additive (Property 7)
    - **Property 7: Stock addition is additive**
    - **Validates: Requirements 6.4**
    - Create `backend/tests/unit/test_admin_add_stock_properties.py`
    - Use hypothesis to generate starting stock S and quantity Q (1–10000)
    - Assert: new stock = S + Q after add-stock operation

  - [x] 11.3 Write property test: Duplicate variant creation is rejected (Property 8)
    - **Property 8: Duplicate variant creation is rejected**
    - **Validates: Requirements 4.4**
    - Create `backend/tests/unit/test_admin_create_variant_properties.py`
    - Use hypothesis + moto to generate variant records, then attempt creation with same attributes
    - Assert: error returned, existing record unchanged

- [x] 12. Final checkpoint - Full integration verification
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The data migration script (1.4) should be run once after deploying the backend field name fixes
- Frontend uses Chakra UI v2 components, React 18 + TypeScript
- Backend uses Python 3.11, AWS SAM, pytest + hypothesis for testing
- Frontend tests use jest + fast-check for property-based testing
- All DynamoDB table names must come from environment variables (never hardcoded)
- **All frontend UI tasks MUST follow `.kiro/steering/look-and-feel.md`** — dark theme default, orange brand color (#f56500), Chakra UI only (no custom CSS), WCAG AA compliance, icon colors per action type (DeleteIcon=red, AddIcon=green, EditIcon=orange), cards with `bg="gray.800"` + `borderColor="orange.400"`, tables with `bg="gray.700"` headers
- **Field names MUST follow `.kiro/steering/schema-driven.md`** — never invent new field names, use `prijs` not `price`, use `naam` not `name`, check field registry before using any field
- **Backend handler tests MUST follow `.kiro/steering/testing.md`** — use importlib pattern (never `import app` via sys.path), load handler inside `mock_aws()` context, patch auth via `patch.multiple('app', ...)`
- **Backend handlers MUST follow `.kiro/steering/structure.md`** — one handler per folder under `backend/handler/`, import from `shared.auth_utils`, use `create_success_response()`/`create_error_response()`
- **DynamoDB access MUST follow `.kiro/steering/aws-dynamodb.md`** — table names from env vars, `boto3.resource('dynamodb')` pattern, tables are NOT in CloudFormation

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "3.1", "4.1"] },
    { "id": 1, "tasks": ["1.3", "1.4", "3.2", "3.3", "3.4", "3.5", "4.2"] },
    { "id": 2, "tasks": ["4.3", "6.2"] },
    { "id": 3, "tasks": ["6.1", "6.3", "7.1"] },
    { "id": 4, "tasks": ["7.2", "8.1", "8.2", "8.3"] },
    { "id": 5, "tasks": ["9.1", "10.1"] },
    { "id": 6, "tasks": ["11.1", "11.2", "11.3"] }
  ]
}
```
