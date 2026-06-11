# Implementation Plan: Product Model Unification

## Overview

This plan migrates the H-DCN product model from legacy (`opties`, `channel`, `id`-keyed records) to a unified model with UUID primary keys, `variant_schema` + variant records, `event_id` linkage, and a single order pipeline replacing the separate Cart table. Implementation proceeds in waves: migration script → backend handler consolidation → frontend type/component updates → reporting → cleanup verification.

## Tasks

- [x] 1. Migration script and data transformation
  - [x] 1.1 Create migration script (`scripts/migrate_products.py`)
    - Implement `migrate_products(dry_run: bool) -> MigrationSummary` function
    - Scan Producten table, identify legacy products (has `opties`, no `legacy_opties`, no existing variants)
    - For each legacy product: generate UUID v4, store original `id` in `legacy_id`, create `slug` from id+name
    - Parse `opties` → `variant_schema` (comma-separated → `{"Maat": [...]}`) or create Default_Variant for "One Size"/empty
    - Generate Variant_Records (one per value) with UUID, `is_parent: false`, `parent_id`, `variant_attributes`, `stock: 0`, `allow_oversell: true`
    - Set `is_parent: true`, `active: true`, `event_id: null`, copy `opties` to `legacy_opties`, remove `opties` field
    - Delete old `id`-keyed record after creating new `product_id`-keyed record
    - Skip already-migrated products (idempotency check: has `legacy_opties` or `legacy_id`)
    - Log per-product errors and continue processing
    - Output MigrationSummary at completion
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.10, 1.11, 1.12, 1.13, 1.14_

  - [x] 1.2 Implement channel-to-event_id transformation in migration script
    - Replace `channel`/`tenant` fields with `event_id` on all product records
    - `channel: "presmeet"` → `event_id` set to linked event's event_id (lookup in Events table)
    - `channel: "h-dcn"` or absent → `event_id: null`
    - Remove `channel` field from all cart records
    - Handle missing linked event gracefully (log warning, set `event_id: null`)
    - _Requirements: 1.16, 1.18, 10.12, 12.1_

  - [x] 1.3 Implement test data deletion in migration script
    - Delete ALL records from Orders table
    - Delete ALL records from Carts table
    - Delete ALL records from Payments table
    - Include deletion counts in MigrationSummary
    - _Requirements: 1.7, 1.8, 1.9_

  - [x] 1.4 Write property tests for migration transformation (Property 1)
    - **Property 1: Migration transformation produces correct unified records**
    - Generate random legacy products with various `opties` values using Hypothesis
    - Verify: UUID v4 generation, `legacy_id` preservation, `slug` format, `variant_schema` correctness, variant record generation
    - **Validates: Requirements 1.2, 1.3, 1.4, 1.5, 1.6**

  - [x] 1.5 Write property tests for migration identification (Property 2)
    - **Property 2: Migration identification correctly selects legacy products**
    - Generate mixed table states (legacy, already-migrated, pre-existing UUID products)
    - Verify only correct records are selected for migration
    - **Validates: Requirements 1.1, 1.10, 1.11**

  - [x] 1.6 Write property test for migration idempotency (Property 3)
    - **Property 3: ion is idempotent**
    - Run migration twice on generated data, verify same end state
    - **Validates: Requirements 1.12**

  - [x] 1.7 Write property test for channel-to-event_id transformation (Property 4)
    - **Property 4: Channel-to-event_id transformation is correct**
    - Generate records with various `channel` values, verify correct `event_id` assignment and `channel` removal
    - **Validates: Requirements 1.16, 1.17, 10.12**

- [x] 2. Checkpoint - Ensure all migration tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. Backend handler consolidation — product handlers
  - [x] 3.1 Update `get_product_byid` handler to use `product_id` key
    - Change DynamoDB `Key` from `{'id': ...}` to `{'product_id': ...}`
    - Return 404 if product not found
    - _Requirements: 5.2, 5.6_

  - [x] 3.2 Update `delete_product` handler to use `product_id` key
    - Change DynamoDB `Key` from `{'id': ...}` to `{'product_id': ...}`
    - Return 404 if product not found
    - _Requirements: 5.3, 5.6_

  - [x] 3.3 Update `scan_product` handler for unified response
    - Return fields: `product_id`, `name`, `price`, `variant_schema`, `is_parent`, `event_id`, `active`
    - Use `naam` as fallback for `name`, `prijs` as fallback for `price`
    - Exclude records where `is_parent` is `false`
    - Exclude records where `source` equals `"migration"`
    - _Requirements: 5.4, 5.5, 9.1, 9.2_

  - [x] 3.4 Create `get_variants` handler (`backend/handler/get_variants/app.py`)
    - GET `/products/{id}/variants` endpoint
    - Scan Producten table for records with `parent_id` matching the given product_id
    - Return array of VariantRecord objects
    - Add to SAM template with API Gateway event
    - _Requirements: 4.4, 12.3_

  - [x] 3.5 Remove channel_resolver.py and channel logic from shared layer
    - Delete `backend/layers/auth-layer/python/shared/channel_resolver.py`
    - Remove `resolve_channels()` and `validate_channel_access()` calls from all handlers that import them
    - _Requirements: 12.5, 12.3_

  - [x] 3.6 Write property tests for scan_product (Properties 6 & 7)
    - **Property 6: scan_product response normalization**
    - **Property 7: scan_product excludes variant and migration records**
    - Generate products with mixed field names, verify normalization
    - Generate table with parents + variants, verify correct filtering
    - **Validates: Requirements 5.4, 5.5, 9.1, 9.2**

- [x] 4. Backend handler consolidation — unified order handlers
  - [x] 4.1 Create `create_order` handler (`backend/handler/create_order/app.py`)
    - POST `/orders` endpoint
    - Accept `event_id` (null for webshop, set for event order)
    - For event orders: check existing order for same `club_id` + `event_id`, return existing if found
    - For webshop orders: always create new draft
    - Set initial `version: 1`, `status: "draft"`, `payment_status: "unpaid"`
    - Fetch product prices from Producten table — reject if price is null/empty/zero
    - _Requirements: 7.1, 7.4, 7.5, 7.6, 7.7, 7.8, 7.13, 7.16, 10.8_

  - [x] 4.2 Create `update_order_items` handler (`backend/handler/update_order_items/app.py`)
    - PUT `/orders/{id}/items` endpoint
    - Implement optimistic locking: reject if provided version ≠ stored version (409 Conflict)
    - Accept incomplete item data without validation (validation at submit only)
    - Fetch prices from Producten table for each item
    - Validate variant `parent_id` matches `product_id`
    - Increment version on success
    - _Requirements: 7.6, 7.7, 7.8, 7.9, 7.10, 7.21, 10.9_

  - [x] 4.3 Create `submit_order` handler (`backend/handler/submit_order/app.py`)
    - POST `/orders/{id}/submit` endpoint
    - Validate all required fields, `item_fields_data`, variant selections
    - Verify each item's `variant_id` resolves to variant with matching `parent_id`
    - Set status to `"submitted"`
    - _Requirements: 7.1, 7.10, 10.8, 10.9_

  - [x] 4.4 Create `get_customer_orders` handler (`backend/handler/get_customer_orders/app.py`)
    - GET `/orders/my` endpoint
    - Return authenticated user's orders (read-only)
    - Show status, items, totals, payment status
    - _Requirements: 7.14, 7.15_

  - [x] 4.5 Update `pay_order` handler for unified model
    - Use `variant_id` from order items for stock reservation
    - Works for both webshop and event orders
    - _Requirements: 10.10_

  - [x] 4.6 Write property tests for order handlers (Properties 8, 9, 10, 11, 12, 13)
    - **Property 8: Order prices fetched from Producten table**
    - **Property 9: Null or empty price rejects order item**
    - **Property 10: Optimistic locking rejects stale versions**
    - **Property 11: Draft orders accept incomplete item data**
    - **Property 12: One order per club per event**
    - **Property 13: Order validation pipeline works for all product types**
    - **Validates: Requirements 7.6, 7.7, 7.8, 7.9, 7.10, 7.16, 10.8, 10.9**

- [x] 5. Checkpoint - Ensure all backend tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. SAM template updates — retire legacy handlers
  - [x] 6.1 Remove retired handlers from SAM template
    - Remove `create_cart`, `update_cart_items`, `get_cart`, `clear_cart` functions
    - Remove `save_presmeet_booking`, `validate_presmeet_cart` functions
    - Remove `presmeet_get_order`, `presmeet_upsert_order`, `presmeet_submit_order` functions
    - Remove legacy `update_product` function (replaced by `admin_update_product`)
    - _Requirements: 7.3, 10.2, 10.3, 10.4, 12.17_

  - [x] 6.2 Add new unified handlers to SAM template
    - Add `create_order` (POST `/orders`)
    - Add `update_order_items` (PUT `/orders/{id}/items`)
    - Add `submit_order` (POST `/orders/{id}/submit`)
    - Add `get_customer_orders` (GET `/orders/my`)
    - Add `get_variants` (GET `/products/{id}/variants`)
    - Remove `CHANNEL`/`TENANT` environment variables from all Lambda configurations
    - _Requirements: 7.1, 12.15_

  - [x] 6.3 Delete retired handler directories
    - Delete `backend/handler/create_cart/`
    - Delete `backend/handler/update_cart_items/` (if exists)
    - Delete `backend/handler/get_cart/`
    - Delete `backend/handler/clear_cart/`
    - Delete `backend/handler/save_presmeet_booking/` (if exists)
    - Delete `backend/handler/validate_presmeet_cart/` (if exists)
    - Delete `backend/handler/presmeet_get_order/` (if exists)
    - Delete `backend/handler/presmeet_upsert_order/` (if exists)
    - Delete `backend/handler/presmeet_submit_order/` (if exists)
    - _Requirements: 7.3, 12.17_

- [x] 7. Frontend type system updates
  - [x] 7.1 Update Product interface in `frontend/src/types/index.ts`
    - Remove `opties` field entirely
    - Add `product_id: string`, `variant_schema?: VariantSchema`, `is_parent?: boolean`, `event_id?: string | null`, `active?: boolean`
    - Retain backward-compat fields (`naam`, `prijs`, `groep`, `subgroep`, `id`, `name`, `price`, `category`) as optional
    - _Requirements: 2.1, 2.2, 2.3_

  - [x] 7.2 Update `modules/webshop/types/unifiedProduct.types.ts`
    - Replace `channel: Channel` with `event_id?: string | null` on UnifiedProduct
    - Remove `channel` from VariantRecord interface
    - Remove `Channel` and `Tenant` type exports
    - _Requirements: 12.7, 12.8, 12.9_

  - [x] 7.3 Update frontend API client (`modules/webshop/services/api.ts`)
    - Remove `cartService` (createCart, getCart, updateCartItems, clearCart)
    - Add `orderService` (createDraft, updateItems, submitOrder, payOrder, getMyOrders)
    - Update `productService.getVariants` to call `/products/{id}/variants`
    - Replace `?channel=` parameters with `?event_id=`
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 7.20, 12.13_

  - [x] 7.4 Verify TypeScript compilation passes with zero errors
    - Run `npm run type-check` and fix any remaining type errors from removed fields
    - _Requirements: 2.4, 2.5_

- [x] 8. Frontend component migration — webshop
  - [x] 8.1 Delete `ProductCardModal` component and all references
    - Remove the component file
    - Remove all imports and usages of `ProductCardModal`
    - Remove any `opties.split(',')` patterns
    - _Requirements: 4.3_

  - [x] 8.2 Update `WebshopPage` to use VariantSelector
    - Integrate VariantSelector for all products with `variant_schema`
    - Auto-select Default_Variant for products without `variant_schema`
    - Fetch variants via `productService.getVariants(productId)`
    - Display stock indicator and handle "combination unavailable"
    - Handle variant fetch failure (disable add-to-cart, show error message)
    - Filter to show only products where `event_id` is null
    - _Requirements: 4.1, 4.2, 4.5, 4.6, 4.7, 4.8, 12.11, 12.12_

  - [x] 8.3 Refactor `CartModal` → DraftOrderModal
    - Replace cart API calls with order API calls (createDraft, updateItems)
    - Use `product_id` (UUID) and `variant_id` (UUID) in order payloads
    - Remove `selectedOption` field usage
    - _Requirements: 7.12, 7.19, 12.18_

  - [x] 8.4 Refactor `CheckoutModal` to submit+pay draft order
    - Call `submitOrder` then `payOrder` on draft order
    - Handle 409 conflict (prompt refresh and retry)
    - _Requirements: 7.4, 7.12_

  - [x] 8.5 Write property test for VariantSelector resolution (Property 5)
    - **Property 5: VariantSelector resolves correct variant**
    - Generate variant schemas with N axes and variant records using fast-check
    - Verify correct variant resolution when all axes selected
    - **Validates: Requirements 4.5, 4.6**

- [x] 9. Frontend component migration — admin
  - [x] 9.1 Update ProductCard editor (admin)
    - Remove `opties` text field and Yup validation for it
    - Render VariantSchemaEditor for all products
    - Submit `variant_schema` in API payload (not `opties`)
    - Call `admin_update_product` endpoint for all updates
    - Add `event_id` selector (searchable dropdown of events)
    - Prevent form submission on VariantSchemaEditor validation errors
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

  - [x] 9.2 Refactor `TenantFilter` → `EventFilter`
    - Rename component file
    - Show options: "Alle", "Webshop" (event_id null), and event names from Events table
    - Replace channel-based filtering with event_id-based filtering
    - Update all usages across admin pages
    - _Requirements: 10.5, 12.6, 12.10_

  - [x] 9.3 Update `WebshopManagementPage` for unified product management
    - Display ALL products in single interface
    - Use EventFilter for "Webshop" vs specific events
    - Remove any separate presmeet admin pages/tabs
    - _Requirements: 10.5, 12.6_

  - [x] 9.4 Update `OrdersTab` and `OrderDetailDrawer`
    - Remove `channel`/`tenant` references
    - Use `event_id` for filtering
    - Display unified order fields (`name`, `unit_price`, `variant_attributes`)
    - _Requirements: 12.6_

- [x] 10. Checkpoint - Ensure frontend compiles and tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Reporting updates
  - [x] 11.1 Update `presmeet_generate_report` handler
    - Use `product_type` field on order items instead of string-matching on `product_id`
    - _Requirements: 10.6_

  - [x] 11.2 Update `generate_order_pdf` handler
    - Use unified field names: `name`, `unit_price`, `variant_attributes`
    - Remove legacy fields: `naam`, `price`, `selectedOption`
    - _Requirements: 10.7_

  - [x] 11.3 Update `AdvancedExportsPage` CSV export
    - Remove `opties` column
    - Add variant information from `variant_schema` (format: "Maat: S, M, L, XL")
    - Show "Standaard" for products without `variant_schema`
    - _Requirements: 8.1, 8.2, 8.3_

  - [x] 11.4 Write property test for CSV variant formatting (Property 14)
    - **Property 14: CSV export formats variant_schema correctly**
    - Generate products with various variant_schema structures using fast-check
    - Verify correct string formatting
    - **Validates: Requirements 8.2, 8.3**

  - [x] 11.5 Implement Reports tab in Webshop Management
    - Support report types: Financial, Products, Orders, Stock Movements
    - Primary filter: "All", "Webshop" (no event_id), and each event by name
    - Additional filters: order status, payment_status
    - Financial report: order list with payments, totals overview, cost breakdown from StockMovements
    - Products report: select product → show definition, variants, sold items, totals
    - Orders report: order list with details, invoice-style single-order view, totals
    - Stock Movements report: inbound/sale movements, totals with weighted average cost
    - All reports support JSON and CSV export
    - Include event context (name, location, dates) when event filter active
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8, 11.9, 11.10, 11.11, 11.12, 11.13, 11.14_

- [x] 12. Channel/tenant codebase cleanup
  - [x] 12.1 Remove channel/tenant from all remaining backend handlers
    - Sweep all handlers in `backend/handler/` for `channel` or `tenant` references
    - Replace `?channel=` query parameter handling with `?event_id=` in `get_products`
    - Remove channel logic from `admin_create_variant`, `admin_export_report`, `manual_presmeet_payment`, `lock_presmeet_orders`, `get_presmeet_booking`
    - _Requirements: 12.1, 12.2, 12.4, 12.14_

  - [x] 12.2 Remove channel/tenant from all frontend code
    - Remove from `WebshopManagementPage.tsx`, `OrdersTab.tsx`, `OrderDetailDrawer.tsx`, `PaymentsTab.tsx`, `ProductManagementPage.tsx`
    - Remove from `presmeet.types.ts`, `admin.types.ts`
    - Remove `useChannelFilter` hook, replace with event-based filter
    - Update `presmeetApi.getProducts(channel)` → fetch by `event_id`
    - _Requirements: 12.6, 12.10, 12.13_

  - [x] 12.3 Update all test files
    - Replace `channel: 'presmeet'` / `channel: 'h-dcn'` with `event_id` in test fixtures
    - Remove test files for retired handlers (cart, legacy update_product, presmeet-specific)
    - Update fixtures using `opties`, cart APIs, or legacy key patterns
    - _Requirements: 12.16_

- [x] 13. Checkpoint - Full test suite pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 14. Verification and final cleanup
  - [x] 14.1 Run post-migration grep verification checks
    - `grep -r "channel\|tenant" backend/handler/` → zero hits
    - `grep -r "channel\|tenant" frontend/src/` → zero hits (excluding unrelated uses)
    - `grep -r "opties" backend/ frontend/` → zero hits
    - `grep -r "create_cart\|update_cart\|get_cart\|clear_cart" backend/ frontend/` → zero hits
    - `grep -r "'id'" backend/handler/` for Producten table access → zero hits (all use `product_id`)
    - `grep -r "ProductCardModal" frontend/src/` → zero hits
    - `grep -r "selectedOption" frontend/src/` → zero hits
    - Fix any remaining references found
    - _Requirements: Design verification checklist_

  - [x] 14.2 Verify SAM template cleanliness
    - Confirm no retired handlers in template
    - Confirm no `CHANNEL`/`TENANT` environment variables
    - Confirm `channel_resolver.py` does not exist
    - Does not work: Run `sam build --use-container` to verify template validity Replace by push to main
    - _Requirements: 12.15, 12.17_

  - [x] 14.3 Verify TypeScript compilation
    - Run `npm run type-check` — zero errors
    - Run `npm test -- --watchAll=false` — all tests pass
    - _Requirements: 2.4_

- [x] 15. Final checkpoint - All verification passes
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties (Hypothesis for Python, fast-check for TypeScript)
- Unit tests validate specific examples and edge cases
- The PresMeet booking wizard frontend (BookingWizard, ProductConfigurator, BookingOverview) is kept as-is — only its backend calls change to universal order handlers
- Migration script should be run with `dry_run=True` first to verify transformation before actual execution
- All handlers follow the existing pattern: import from `shared.auth_utils`, use `extract_user_credentials()`, return via `create_success_response()`/`create_error_response()`

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3"] },
    { "id": 1, "tasks": ["1.4", "1.5", "1.6", "1.7", "3.5"] },
    { "id": 2, "tasks": ["3.1", "3.2", "3.3", "3.4"] },
    { "id": 3, "tasks": ["3.6", "4.1", "4.2", "4.3", "4.4", "4.5"] },
    { "id": 4, "tasks": ["4.6", "6.1", "6.2", "6.3"] },
    { "id": 5, "tasks": ["7.1", "7.2", "7.3"] },
    { "id": 6, "tasks": ["7.4", "8.1", "9.1", "9.2"] },
    { "id": 7, "tasks": ["8.2", "8.3", "8.4", "9.3", "9.4"] },
    { "id": 8, "tasks": ["8.5", "11.1", "11.2", "11.3"] },
    { "id": 9, "tasks": ["11.4", "11.5", "12.1", "12.2"] },
    { "id": 10, "tasks": ["12.3"] },
    { "id": 11, "tasks": ["14.1", "14.2", "14.3"] }
  ]
}
```
Open questions 
- Is the daat migrated. Did the migration script run (Dry and Full) 
- Can we push to main