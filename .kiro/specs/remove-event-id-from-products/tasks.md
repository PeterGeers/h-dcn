# Implementation Plan: Remove event_id from Products

## Overview

Remove `event_id` and `event_ids` fields from the Product domain. The implementation starts with the migration script (clean break), then updates backend handlers in parallel, followed by frontend changes. Each task includes its own tests.

## Tasks

- [x] 1. Write and test migration script
  - [x] 1.1 Create migration script `scripts/migrate_remove_event_id_from_products.py`
    - Follow pattern from `migrate_remove_variant_schema.py`
    - Support `--dry-run` and `--profile` (default: `nonprofit-deploy`)
    - Scan for records with `attribute_exists(event_id) OR attribute_exists(event_ids)`
    - Remove both attributes with `REMOVE event_id, event_ids`
    - Handle DynamoDB pagination
    - Log counts: total scanned, matching, modified
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [x] 1.2 Write property tests for migration script
    - **Property 4: Migration dry-run preserves all data**
    - **Property 5: Migration removes event_id and event_ids from all records**
    - **Validates: Requirements 8.1, 8.2, 8.4**
    - Test file: `backend/tests/unit/test_migrate_remove_event_id_properties.py`
    - Use hypothesis + moto to generate random product records (some with event_id, some with event_ids, some with both, some with neither)
    - Verify dry-run leaves all records unchanged
    - Verify non-dry-run removes both attributes from all records

  - [x] 1.3 Write unit tests for migration script
    - Test file: `backend/tests/unit/test_migrate_remove_event_id.py`
    - Test --dry-run logs but doesn't modify
    - Test pagination handling (multiple scan pages)
    - Test records without event_id/event_ids are untouched
    - _Requirements: 8.1, 8.2, 8.4, 8.5_

- [x] 2. Rewrite get_products handler to batch-get-by-IDs
  - [x] 2.1 Rewrite `backend/handler/get_products/app.py`
    - Replace scan-by-event_id with batch-get-by-IDs pattern
    - Accept `product_ids` query parameter (comma-separated)
    - Return 400 if `product_ids` param missing entirely
    - Return 200 with empty list for empty `product_ids`
    - Chunk into batches of 100 for DynamoDB BatchGetItem limit
    - Handle unprocessed keys (DynamoDB throttling)
    - Retain existing auth check (hdcnLeden or event-related roles)
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [x] 2.2 Write property test for get_products batch-get
    - **Property 3: Batch-get returns exactly the existing subset**
    - **Validates: Requirements 6.1, 6.4**
    - Test file: `backend/tests/unit/test_get_products_properties.py`
    - Use hypothesis to generate random product ID lists (some existing, some not)
    - Verify response contains exactly the intersection of requested IDs and existing records

  - [x] 2.3 Write unit tests for get_products handler
    - Test file: `backend/tests/unit/test_get_products.py`
    - Test empty product_ids returns empty list (200)
    - Test missing product_ids param returns 400
    - Test non-existent IDs are silently omitted
    - Test >100 IDs are chunked correctly
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 3. Update admin_create_product handler
  - [x] 3.1 Strip event_id and event_ids from request body in `backend/handler/admin_create_product/app.py`
    - Add `body.pop('event_id', None)` and `body.pop('event_ids', None)` before building product dict
    - Remove `'event_id': event_id,` from product dict construction if present
    - Verify all other fields still persist correctly
    - _Requirements: 3.1, 3.2, 3.3_

  - [x] 3.2 Write property test for create product handler
    - **Property 1: Create handler never persists event_id or event_ids**
    - **Validates: Requirements 3.1, 3.2**
    - Test file: `backend/tests/unit/test_admin_create_product_properties.py`
    - Use hypothesis to generate payloads with random event_id/event_ids values
    - Verify resulting DynamoDB record never contains either attribute

  - [x] 3.3 Write unit tests for admin_create_product
    - Test file: `backend/tests/unit/test_admin_create_product.py`
    - Test that event_id in payload is stripped
    - Test that event_ids in payload is stripped
    - Test that valid fields are still stored
    - _Requirements: 3.1, 3.2, 3.3_

- [x] 4. Update admin_update_product handler
  - [x] 4.1 Remove `event_ids` from UPDATABLE_FIELDS in `backend/handler/admin_update_product/app.py`
    - Remove `'event_ids'` from the UPDATABLE_FIELDS list
    - No other changes needed (handler already ignores fields not in the list)
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 4.2 Write property test for update product handler
    - **Property 2: Update handler ignores event_id and event_ids**
    - **Validates: Requirements 4.3**
    - Test file: `backend/tests/unit/test_admin_update_product_properties.py`
    - Use hypothesis to generate update payloads with random event_id/event_ids values
    - Verify DynamoDB record is not modified for those attributes

  - [x] 4.3 Write unit tests for admin_update_product
    - Test file: `backend/tests/unit/test_admin_update_product.py`
    - Test that event_ids in payload is ignored
    - Test that event_id in payload is ignored
    - Test that valid updatable fields still work
    - _Requirements: 4.1, 4.2, 4.3_

- [x] 5. Update scan_product and generate_preparation_pdf handlers
  - [x] 5.1 Remove event_ids from scan_product response normalization in `backend/handler/scan_product/app.py`
    - Remove `'event_ids': item.get('event_ids', [])` from the normalized response dict
    - _Requirements: 9.1, 9.2_

  - [x] 5.2 Write property test for scan_product response
    - **Property 6: Scan response excludes event_id and event_ids**
    - **Validates: Requirements 9.1, 9.2**
    - Test file: `backend/tests/unit/test_scan_product_properties.py`
    - Use hypothesis to generate product records with/without legacy event_id/event_ids
    - Verify API response never contains either field

  - [x] 5.3 Rewrite `_fetch_products_map` in `backend/handler/generate_preparation_pdf/app.py`
    - Replace scan-by-event_id with batch-get using event's `product_ids` array
    - Update caller in lambda_handler to pass `event_record.get('product_ids', [])` instead of `event_id`
    - Add `_chunk_list` helper for 100-item BatchGetItem limit
    - Handle unprocessed keys
    - _Requirements: 7.1, 7.2, 7.3_

  - [x] 5.4 Write property test for PDF generator product fetch
    - **Property 7: PDF generator fetches products via event.product_ids**
    - **Validates: Requirements 7.1, 7.2**
    - Test file: `backend/tests/unit/test_generate_preparation_pdf_properties.py`
    - Use hypothesis to generate event records with random product_ids arrays
    - Verify exactly those products are fetched via batch-get, no scan by event_id

- [x] 6. Checkpoint - Backend complete
  - Ensure all backend tests pass, ask the user if questions arise.

- [x] 7. Frontend: TypeScript interfaces and Field Registry
  - [x] 7.1 Remove event_ids from Field Registry and TypeScript interfaces
    - Remove `event_ids` entry from `parentFields` in `frontend/src/config/productFields/fields.ts`
    - Remove `event_ids?: string[]` from Product type in `frontend/src/types/index.ts`
    - Remove `event_id?: string | null` from Product type in `frontend/src/modules/eventBooking/types/eventBooking.types.ts`
    - Run `npx tsc --noEmit` to verify zero type errors
    - _Requirements: 1.1, 1.2, 2.1, 2.2_

- [x] 8. Frontend: Remove event filter and product form event selector
  - [x] 8.1 Remove event filter components and hook
    - Delete `frontend/src/modules/webshop-management/hooks/useEventFilter.ts`
    - Delete `frontend/src/modules/webshop-management/components/EventFilter.tsx`
    - Remove `useEventFilter` import and usage from `WebshopManagementPage.tsx`
    - Remove `useEventFilter` import and usage from `ReportsTab.tsx`
    - Verify no other files import from deleted modules
    - Run `npx tsc --noEmit` and `npx eslint` on modified files
    - _Requirements: 10.1, 10.2, 10.3_

  - [x] 8.2 Verify admin product form no longer shows event selector
    - Confirm that removing `event_ids` from the Field Registry automatically hides the selector
    - If any hardcoded event selector exists outside the registry-driven form, remove it
    - _Requirements: 5.1, 5.2, 5.3_

  - [x] 8.3 Write frontend unit tests
    - Test that Field Registry does not export event_id/event_ids fields
    - Test that Product type compiles without event_id/event_ids
    - Run `npx react-scripts test --watchAll=false --testPathPattern="productFields"`
    - _Requirements: 1.1, 2.1_

- [x] 9. Final checkpoint - Ensure all tests pass
  - Ensure all backend and frontend tests pass, ask the user if questions arise.
  - Run `npx tsc --noEmit` for full type check
  - Run ESLint on all modified frontend files

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- Migration script (task 1) should be written first but run against prod AFTER backend handlers are deployed
- Backend handler changes (tasks 2-5) are largely independent and can proceed in parallel
- Frontend changes (tasks 7-8) depend on each other: interfaces first, then component removal
- Use `importlib.util` pattern for handler imports in all backend tests
- Use `moto` with `mock_aws()` for DynamoDB mocking in tests

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "4.1"] },
    { "id": 1, "tasks": ["1.2", "1.3", "2.1", "3.1", "4.2", "4.3", "5.1"] },
    { "id": 2, "tasks": ["2.2", "2.3", "3.2", "3.3", "5.2", "5.3"] },
    { "id": 3, "tasks": ["5.4", "7.1"] },
    { "id": 4, "tasks": ["8.1", "8.2"] },
    { "id": 5, "tasks": ["8.3"] }
  ]
}
```
