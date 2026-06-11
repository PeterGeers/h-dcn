# Requirements Document

## Introduction

The goal of this specification is to establish a single unified backend system that handles both the sale of webshop products and the booking of event registrations (PresMeet, rallies, member days). Today, parallel code paths, duplicate handlers, and inconsistent data models have created instability where changes to one part break another. This migration eliminates that by moving to one product model, one order flow, and one admin interface — with only the customer-facing booking wizard remaining as event-specific frontend.

Specifically, the migration eliminates the legacy `opties`-based product model, replaces the `channel` concept with event linkage (`event_id`), removes the Cart table in favor of draft orders, consolidates all product/order/payment handlers into a single set, and ensures all product data (prices, variants, attributes) comes from the Producten table — never hardcoded.

## Glossary

- **Producten_Table**: The DynamoDB table storing all product and variant records, keyed by `product_id (S)`
- **Legacy_Product**: A product record using the old model with `id`, `opties` (comma-separated string), `prijs`, and `naam` fields
- **Unified_Product**: A product record using the unified model with `product_id`, `variant_schema` (Record<string, string[]>), `price`, `name`, `event_id` (null for generic webshop, set for event-linked products), `is_parent`, and `active` fields
- **Variant_Schema**: A Record<string, string[]> mapping axis names to their possible values (e.g., `{"Maat": ["S","M","L","XL"]}`)
- **Variant_Record**: A child record in the Producten_Table with `is_parent: false`, `parent_id`, `variant_attributes`, `stock`, and `allow_oversell` fields representing a single purchasable SKU
- **Parent_Product**: A product record with `is_parent: true` that defines the variant_schema and groups variant children
- **Default_Variant**: A single variant record created for products that have no meaningful variant axes (single-option products)
- **Migration_Script**: An idempotent Python script that converts Legacy_Products to Unified_Products and generates Variant_Records
- **ProductCard_Editor**: The admin-facing product editing component (`ProductCard.tsx`) used to create and modify products
- **VariantSchemaEditor**: The React component that provides UI for editing variant_schema as Record<string, string[]>
- **VariantSelector**: The customer-facing React component that renders dropdowns for each variant axis and resolves the selected variant
- **ProductCardModal**: The legacy customer-facing modal component that splits `opties` by comma to present product options
- **Legacy_Handler**: The backend handlers (`update_product`, `get_product_byid`, `delete_product`) that use `Key: {'id': ...}` instead of `Key: {'product_id': ...}`
- **Admin_Handler**: The backend handlers (`admin_update_product`, `admin_get_products`, `admin_create_product`) that use `Key: {'product_id': ...}` correctly

## Requirements

### Requirement 1: Product Data Migration

**User Story:** As a system administrator, I want all legacy H-DCN products converted to the unified model with UUID identifiers and variant records, so that the entire product catalog uses a single consistent data structure and all table references are updated.

#### Acceptance Criteria

1. WHEN the Migration_Script is executed, THE Migration_Script SHALL scan all records in the Producten_Table and identify Legacy_Products as records that contain an `opties` field but do not contain a `legacy_opties` field and do not have existing Variant_Records (records where `parent_id` equals the product's `product_id`)
2. FOR each Legacy_Product, THE Migration_Script SHALL perform the following as a single atomic operation per product: (a) generate a new UUID v4 as the product's `product_id`, (b) store the original `id` value in a `legacy_id` field, (c) create a human-readable `slug` field by concatenating the old id with the product name (e.g., `"G5-t-shirt"`), (d) convert `opties` to `variant_schema`, (e) generate variant records, (f) create the new UUID-keyed record, (g) delete the old record keyed by the legacy `id`
3. WHEN a Legacy_Product has an `opties` value containing comma-separated values (e.g., "S,M,L,XL"), THE Migration_Script SHALL parse the value by splitting on commas, trimming whitespace from each item, filtering out empty strings, and converting the result to a Variant_Schema with key "Maat" and values as the parsed list (e.g., `{"Maat": ["S","M","L","XL"]}`)
4. WHEN a Legacy_Product has an `opties` value of "One Size" or an `opties` value that is empty or null after trimming, THE Migration_Script SHALL create a single Default_Variant with a UUID v4 as `product_id`, `is_parent: false`, `parent_id` set to the parent's new UUID, `variant_attributes: {}`, `stock: 0`, and `allow_oversell: true`, without setting a `variant_schema` on the parent record
5. WHEN a Legacy_Product has a Variant_Schema with one or more values, THE Migration_Script SHALL generate one Variant_Record for each value, where each Variant_Record has: `product_id` set to a new UUID v4, `is_parent: false`, `parent_id` set to the parent's new UUID, `variant_attributes` mapping the schema axis key to the specific value, `stock: 0`, and `allow_oversell: true`
6. WHEN a Legacy_Product is migrated, THE Migration_Script SHALL set `is_parent: true`, `event_id: null` (generic webshop product), and `active: true` on the parent product record, copy the original `opties` value into a `legacy_opties` field for audit, and remove the `opties` field
7. THE Migration_Script SHALL delete ALL records from the Orders table (test data)
8. THE Migration_Script SHALL delete ALL records from the Carts table (test data)
9. THE Migration_Script SHALL delete ALL records from the Payments table (test data)
10. PresMeet products that already have UUID-based `product_id` values SHALL be skipped by the UUID assignment (but SHALL still have their `channel` field replaced with `event_id` per AC15)
11. WHEN the Migration_Script encounters a product that already has a `legacy_opties` field or a `legacy_id` field, THE Migration_Script SHALL skip that product without modification
12. THE Migration_Script SHALL be idempotent such that running the script multiple times produces the same end state without creating duplicate records
13. IF the Migration_Script fails to process a specific product, THEN THE Migration_Script SHALL log the product id and error detail, skip that product, and continue processing remaining products
14. WHEN the Migration_Script completes, THE Migration_Script SHALL output a summary indicating: total records scanned, products migrated (with new UUIDs and variants), orders/carts/payments deleted, products skipped, and errors
15. THE Legacy_Handlers (update_product, get_product_byid, delete_product) SHALL use `Key: {'product_id': product_id}` instead of `Key: {'id': product_id}` for all DynamoDB operations
16. THE Migration_Script SHALL remove the `channel` and `tenant` fields from ALL product records and replace them with an `event_id` field: products with `channel: "presmeet"` SHALL have `event_id` set to their linked event's `event_id`, products with `channel: "h-dcn"` (or no channel) SHALL have `event_id` set to `null`
17. ~~REMOVED~~ — This criterion is superseded by AC 1.7 (all order records are deleted as test data, making channel→event_id transformation on orders unnecessary)
18. THE Migration_Script SHALL remove the `channel` field from ALL cart records in the Carts table

### Requirement 2: Frontend Product Type Unification

**User Story:** As a developer, I want the Product TypeScript type to reflect only the unified model, so that compile-time type checking prevents legacy field usage.

#### Acceptance Criteria

1. THE Product interface in `types/index.ts` SHALL remove the `opties` field entirely and SHALL NOT export any type that includes an `opties` property
2. THE Product interface in `types/index.ts` SHALL include `product_id: string`, `variant_schema?: VariantSchema` (imported or re-exported from `modules/webshop/types/unifiedProduct.types`), `is_parent?: boolean`, `event_id?: string | null`, and `active?: boolean` fields
3. THE Product interface in `types/index.ts` SHALL retain backward-compatible fields (`naam`, `prijs`, `groep`, `subgroep`) as optional, and SHALL retain the existing base fields (`id`, `name`, `price`, `category`) as optional to allow partial compliance where some components may not provide all fields
4. WHEN the TypeScript compiler is run via `npm run type-check`, THE compilation SHALL produce zero type errors across all frontend source files — this requires the `opties` field to be completely removed from the interface before compilation can succeed
5. IF any frontend source file references the removed `opties` field on a Product-typed variable, THEN the TypeScript compiler SHALL report a type error for that reference, confirming the field is no longer accessible at compile time

### Requirement 3: Admin Product Editor Migration

**User Story:** As an admin user, I want the product editor to use VariantSchemaEditor exclusively, so that I can manage product variants consistently for all products.

#### Acceptance Criteria

1. THE ProductCard_Editor SHALL remove the `opties` text field and its Yup validation schema entry from the product editing form
2. THE ProductCard_Editor SHALL render the VariantSchemaEditor component for editing variant axes on all products regardless of channel, outside of any `readOnly` conditional (visible in both edit and read-only modes)
3. WHEN an admin saves a product via the ProductCard_Editor, THE ProductCard_Editor SHALL submit the `variant_schema` field in the API payload and SHALL NOT include the `opties` field in the payload
4. THE ProductCard_Editor SHALL call the `admin_update_product` API endpoint (PUT `/admin-update-product/{id}`, which uses `Key: {'product_id': ...}`) for all product updates instead of the generic `/update-product/{id}` endpoint
5. IF a product has no variant axes defined (variant_schema is undefined or an empty object), THEN THE ProductCard_Editor SHALL display the VariantSchemaEditor in its empty state showing the "As toevoegen" button, allowing the admin to add up to 5 axes
6. IF the VariantSchemaEditor reports validation errors (duplicate axis names, duplicate values, empty names, or total combinations exceeding 100), THEN THE ProductCard_Editor SHALL prevent form submission until all validation errors are resolved
7. THE ProductCard_Editor SHALL include an `event_id` selector field that allows the admin to link the product to an event or leave it unlinked (null for webshop products), displaying a searchable dropdown of available events loaded from the Events table

### Requirement 4: Legacy Customer Modal Removal

**User Story:** As a customer, I want to select product variants using the VariantSelector component, so that I have a consistent shopping experience with stock visibility for all products.

#### Acceptance Criteria

1. THE WebshopPage SHALL use the VariantSelector component for ALL products that have a `variant_schema` defined, passing the variant_schema (axes and their possible values) and the associated Variant_Records to the component
2. IF a product has no `variant_schema` (single-option product with Default_Variant), THEN THE WebshopPage SHALL allow adding to cart without variant selection by auto-selecting the Default_Variant
3. THE ProductCardModal component file and all references to it SHALL be removed from the codebase, with no remaining imports or usages of the `opties.split(',')` pattern for variant selection
4. THE VariantSelector SHALL receive the array of Variant_Records for the given parent product from the Producten_Table, each record containing variant_attributes, stock count, and allow_oversell flag
5. WHEN a customer selects all variant axes, THE VariantSelector SHALL resolve the matching Variant_Record and display the numeric stock count as an "in stock" indicator
6. IF all variant axes are selected and no matching Variant_Record exists for the combination, THEN THE VariantSelector SHALL display a "combination unavailable" message and disable the add-to-cart action — this message SHALL only appear after all axes have been selected, not while the user is still selecting
7. IF the resolved Variant_Record has stock equal to 0 and allow_oversell is false, THEN THE VariantSelector SHALL display an "out of stock" indicator and disable the add-to-cart action
8. IF the variant fetch request for a product fails, THEN THE WebshopPage SHALL display an error message indicating variants could not be loaded and disable the add-to-cart action

### Requirement 5: Backend Handler Consolidation

**User Story:** As a developer, I want product CRUD operations to use a consistent key pattern, so that there is a single reliable code path for all product operations.

#### Acceptance Criteria

1. THE update_product handler SHALL use `Key: {'product_id': product_id}` for DynamoDB operations instead of `Key: {'id': product_id}`
2. THE get_product_byid handler SHALL use `Key: {'product_id': product_id}` for DynamoDB operations instead of `Key: {'id': id}`
3. THE delete_product handler SHALL use `Key: {'product_id': product_id}` for DynamoDB operations instead of `Key: {'id': product_id}`
4. WHEN scan_product returns results, THE scan_product handler SHALL return each product record containing at minimum the fields `product_id`, `name`, `price`, `variant_schema`, `is_parent`, `event_id`, and `active`, where missing fields are included with their stored value or omitted if not present in the DynamoDB item
5. WHEN scan_product returns results, THE scan_product handler SHALL exclude records where `is_parent` is explicitly set to `false` and records where `source` equals `migration`, while retaining records where `is_parent` is `true` or where the `is_parent` attribute does not exist
6. IF a get or delete operation targets a `product_id` that does not exist in the Producten table, THEN the handler SHALL return a 404 error response indicating the product was not found — IF an update operation targets a non-existent `product_id`, THE handler MAY create the product instead of returning 404

### Requirement 6: Product API Client Alignment

**User Story:** As a developer, I want the frontend API client to use the correct endpoints and payload format, so that all product operations work with the unified model.

#### Acceptance Criteria

1. THE productApi `updateProduct` function SHALL call the `/admin/products/{id}` endpoint with the product's `product_id` value as the `{id}` path parameter using the HTTP PUT method
2. THE productApi `deleteProduct` function SHALL call the `/delete-product/{id}` endpoint with the product's `product_id` value as the `{id}` path parameter using the HTTP DELETE method
3. THE productApi `getProductById` function SHALL call the `/get-product-byid/{id}` endpoint with the product's `product_id` value as the `{id}` path parameter using the HTTP GET method
4. WHEN `scanProducts` returns data, THE productApi SHALL type the response as an array of objects using the unified Product interface that contains `product_id`, `name`, `event_id`, `price`, `variant_schema`, and `purchase_rules`, without the deprecated `opties` field
5. IF the `updateProduct` function receives an HTTP error response (status code 400 or higher) or a network-level failure (timeout, connection refused), THEN THE productApi SHALL propagate the error to the caller without swallowing the response

### Requirement 7: Unified Order-Based Flow (Cart Elimination)

**User Story:** As a developer, I want all purchases to use a single order-based flow (draft → update → submit → pay), eliminating the separate Cart table and handlers, so that both the webshop and booking wizard use the same backend.

#### Acceptance Criteria

1. THE system SHALL use ONE set of order handlers for all purchase flows: create draft order, update order items, submit order, and initiate payment — used by both the webshop and the booking wizard
2. THE Carts DynamoDB table SHALL be eliminated — the Migration_Script SHALL delete all records from the Carts table
3. THE cart handlers (`create_cart`, `update_cart_items`, `get_cart`, `clear_cart`) SHALL be retired and removed from the SAM template
4. THE webshop purchase flow SHALL create a draft order directly (status: "draft", event_id: null) instead of using a cart, then update it as the user adds/removes items, then submit+pay in one action at checkout
5. THE booking wizard purchase flow SHALL continue to create a draft order (status: "draft", event_id: set) and update it over multiple sessions, then submit when ready, then pay separately
6. ALL order item prices SHALL be read from the Producten table at order creation/update time (from the parent product's `price` field or the variant's `price` override) — there SHALL be NO hardcoded prices in any handler
7. ALL product attributes used in orders (order_item_fields, variant_schema, purchase_rules, price) SHALL be fetched from the Producten table at runtime — there SHALL be NO hardcoded product configuration in handler code
8. IF a product record in the Producten table has an empty or null `price` field, THEN the system SHALL reject adding that product to an order with an error indicating the product has no configured price
9. THE draft order SHALL support optimistic locking via a `version` field — updates must include the current version, and the backend rejects updates with a stale version (409 conflict)
10. THE draft order SHALL accept incomplete item data (missing required fields, partial item_fields_data) during saves without validation — validation is only enforced at submit time
11. THE presmeet-specific order handlers (`presmeet_get_order`, `presmeet_upsert_order`, `presmeet_submit_order`) SHALL be consolidated into the universal order handlers, with event-specific behavior (auto-create draft per club+event, event constraint validation) driven by the presence of `event_id` on the order
12. THE frontend webshop SHALL be refactored to work with draft orders: the current `CartModal` becomes a draft order items editor, and `CheckoutModal` triggers submit+pay on the draft order — both components SHALL use `product_id` (UUID) and `variant_id` (UUID) when building order payloads, and the legacy `selectedOption` field SHALL NOT be used
13. Orders SHALL use `event_id` (null for webshop orders, set for event orders) to distinguish between quick-purchase and event-booking flows
14. THE system SHALL provide an endpoint for authenticated users to retrieve their own previous orders in read-only mode, showing order status, items, totals, and payment status
15. FOR webshop orders (event_id: null), THE system SHALL allow the user to create new orders at any time — completed orders remain read-only
16. FOR event orders (event_id: set), THE system SHALL maintain one order per club per event that can be updated even after partial payment — the outstanding balance recalculates when items change

### Requirement 8: CSV Export Migration

**User Story:** As an admin user, I want the CSV export to reflect the unified model, so that exported data accurately represents current product configuration.

#### Acceptance Criteria

1. THE AdvancedExportsPage SHALL remove the `opties` column from the CSV export
2. THE AdvancedExportsPage SHALL include variant information derived from `variant_schema` in the CSV export (e.g., axis names and values formatted as "Maat: S, M, L, XL")
3. WHEN a product has no `variant_schema`, THE AdvancedExportsPage SHALL export "Standaard" in the variant column for that product

### Requirement 9: Scan Product Response Normalization

**User Story:** As a frontend developer, I want the scan_product endpoint to return a consistent response shape, so that the product management page can render all products uniformly.

#### Acceptance Criteria

1. THE scan_product handler SHALL include the fields `product_id`, `name`, `price`, `variant_schema`, `is_parent`, `event_id`, and `active` in every returned product record
2. THE scan_product handler SHALL use `naam` as fallback for `name` and `prijs` as fallback for `price` if the canonical field names are not present on a record

### Requirement 10: Unified Backend — Single Set of Handlers

**User Story:** As a developer, I want one single backend for all product/order/payment operations regardless of event linkage, so that future enhancements are applied in one place and all products benefit equally.

#### Acceptance Criteria

1. THE system SHALL have ONE set of product CRUD handlers (`admin_create_product`, `admin_update_product`, `admin_get_products`, `delete_product`, `get_product_byid`) that work for all products, differentiated only by the `event_id` field (null for webshop, set for event-linked)
2. THE legacy `update_product` handler SHALL be retired (removed from SAM template) after the migration, with all product updates routed through `admin_update_product`
3. THE legacy `save_presmeet_booking` handler SHALL be retired if the v3 `create_order`/`presmeet_upsert_order` flow has fully replaced it — there SHALL NOT be parallel order-creation paths
4. THE legacy `validate_presmeet_cart` handler SHALL be retired if the unified `create_order` validation pipeline (purchase_rules + item_fields + stock check) covers its functionality
5. THE webshop-management admin panel SHALL display and manage ALL products in a single interface, with a filter for "Webshop" (event_id is null) vs specific events — not separate admin pages
6. THE `presmeet_generate_report` handler SHALL identify products using a `product_type` field stored on order items (e.g., "meeting_ticket", "party_ticket") instead of string-matching on the `product_id` value, since all product_ids are now UUIDs
7. THE `generate_order_pdf` handler SHALL use unified field names (`name`, `unit_price`, `variant_attributes`) when rendering order items — not legacy fields like `naam`, `price`, or `selectedOption`
8. THE `create_order` handler SHALL work for both webshop orders and event-linked orders using the same validation pipeline (purchase_rules, item_fields, stock)
9. THE universal order handlers SHALL validate items by fetching variants with `Key: {'product_id': variant_id}` and verifying `variant.parent_id == product_id` — this works for all products
10. THE `admin_record_payment` and `mollie_webhook` handlers SHALL trigger stock reservation using `variant_id` from stored order items — same flow regardless of product type
11. ONLY the PresMeet booking wizard (BookingWizard, ProductConfigurator, BookingOverview) SHALL remain as event-specific frontend — everything else (admin, orders, payments, reports) is shared
12. THE Migration_Script SHALL replace the `channel` field with `event_id` on all existing product records: products with `channel: "presmeet"` SHALL have `event_id` set to their linked event's `event_id`, products with `channel: "h-dcn"` SHALL have `event_id` set to `null`, and the `channel` field SHALL be removed

### Requirement 11: Unified Reporting in Webshop Management

**User Story:** As an admin, I want structured reports in the Webshop Management Reports tab covering financials, product sales details, order overview, and stock movements, so that I have one place to view all operational data.

#### Acceptance Criteria

1. THE Reports tab in Webshop Management SHALL support the following report types: Financial, Products, Orders, and Stock Movements
2. THE Reports tab SHALL provide a primary filter selector with options: "All" (all orders), "Webshop" (orders without event_id), and each available event by name (e.g., "PresMeet 2027") — this filter SHALL apply to ALL report types
3. THE Reports tab SHALL allow additional filtering by order status (draft, submitted, locked, paid, all) and payment_status (unpaid, partial, paid, all)
4. THE Financial report SHALL display: a list of all orders matching the active filters with payment status per order, a totals overview (total orders, total charged, total paid, total outstanding), and a cost breakdown from StockMovements when stock movement records exist for the filtered products
5. THE Products report SHALL allow the admin to select a parent product from a list of all products matching the active primary filter
6. WHEN a parent product is selected in the Products report, THE report SHALL display the product definition (name, price, variant_schema axes and values, order_item_fields definitions, purchase_rules), all variant records with their variant_attributes, stock, sold_count, allow_oversell, and price override, and below that all order items sold for that product showing each item's variant_attributes, item_fields_data values as columns, the order's club, order status, and payment status
7. THE Products report SHALL display a totals overview row showing total items sold, total quantity, and total revenue for the selected product
8. THE Orders report SHALL display a list of all orders matching the active filters showing: order_id, customer/club name, order status, payment status, item count, total amount, amount paid, outstanding amount, and created date
9. WHEN an admin selects a single order in the Orders report, THE report SHALL display a detailed invoice-style view showing: all order line items with product name, variant_attributes, item_fields_data values, quantity, unit price, and line total, plus any additional costs, payment history (payments recorded against the order), and a summary with subtotal, total amount, total paid, and outstanding balance
10. THE Orders report SHALL display a totals overview row showing total order count, total revenue, total paid, and total outstanding
11. THE Stock Movements report SHALL display all inbound and sale stock movements for products matching the active filters, showing: variant name, movement type (inbound/sale), quantity, purchase price per unit, total cost, supplier name, reference, and date
12. THE Stock Movements report SHALL display a totals overview row showing total inbound quantity, total inbound cost, total sold quantity, and weighted average cost per variant
13. ALL report types SHALL support JSON and CSV export formats
14. THE Reports tab SHALL include event context (event name, location, dates) in report output when an event is selected as the primary filter

### Requirement 12: Channel-to-Event Codebase Cleanup

**User Story:** As a developer, I want all code references to `channel` and `tenant` replaced with `event_id` logic, so that product visibility and access control is determined solely by event linkage.

#### Acceptance Criteria

1. ALL backend handlers SHALL remove any filtering, routing, or logic based on `channel` or `tenant` fields — this includes: `get_products`, `get_variants`, `admin_create_variant`, `admin_export_report`, `manual_presmeet_payment`, `lock_presmeet_orders`, `get_presmeet_booking`, `presmeet_get_order`, `create_order`, and any other handler referencing these fields
2. THE `get_products` handler SHALL filter products by `event_id` (null for webshop products, or a specific event_id) instead of by `channel` — the `?channel=` query parameter SHALL be replaced with `?event_id=`
3. THE `get_variants` handler SHALL remove channel access validation (`resolve_channels`, `validate_channel_access`) since product access is now determined by event membership or general webshop access
4. THE `admin_create_variant` handler SHALL NOT store a `tenant` or `channel` field on variant records
5. THE `shared/channel_resolver.py` module SHALL be removed from the codebase — channel resolution is no longer needed
6. ALL frontend components and types SHALL remove any references to `channel` or `tenant` on product and order objects — this includes: `WebshopManagementPage.tsx`, `TenantFilter.tsx` (rename to EventFilter), `OrdersTab.tsx`, `OrderDetailDrawer.tsx`, `PaymentsTab.tsx`, `ProductManagementPage.tsx`, `presmeet.types.ts`, `admin.types.ts`, `unifiedProduct.types.ts`, `webshop/services/api.ts`, `presmeetApi.ts`
7. THE `UnifiedProduct` TypeScript interface SHALL replace the `channel: Channel` field with `event_id?: string | null`
8. THE `VariantRecord` TypeScript interface SHALL remove the `channel: Channel` field
9. THE `Channel` and `Tenant` type exports in `unifiedProduct.types.ts` SHALL be removed
10. THE `useChannelFilter` hook SHALL be replaced with an event-based filter (selecting "Webshop" or a specific event)
11. THE customer-facing webshop (WebshopPage) SHALL display only products where `event_id` is null — these are the generic H-DCN products available for purchase
12. THE customer-facing webshop SHALL NOT display event-linked products — those are only available through the event's booking wizard
13. THE `presmeetApi.getProducts(channel)` call SHALL be replaced with a call that fetches products by event_id from the event's `product_ids` list
14. THE `create_order` handler SHALL use `event_id` (null for webshop orders, set for event orders) instead of `channel` on order records
15. THE SAM template environment variables and configurations referencing channel/tenant SHALL be removed from Lambda function configurations
16. ALL test files referencing `channel: 'presmeet'` or `channel: 'h-dcn'` SHALL be updated to use `event_id` instead
17. THE cart handlers (`create_cart`, `update_cart_items`, `get_cart`, `clear_cart`) SHALL be removed from the SAM template and their handler directories deleted from the codebase
18. ALL frontend code referencing the Carts API endpoints (`/create-cart`, `/update-cart-items`, `/get-cart`, `/clear-cart`) SHALL be removed or refactored to use the order endpoints
19. THE `CartModal` component SHALL be refactored from a cart-based component into a draft order items editor — any logic that reads from or writes to the Carts table SHALL be replaced with order read/update calls
20. THE frontend `webshop/services/api.ts` cart-related methods (createCart, updateCartItems, getCart, clearCart) SHALL be removed and replaced with order-based methods
21. Any shared validation logic currently in cart handlers (e.g., variant validation, stock checks in `update_cart_items`) SHALL be preserved in the unified order update handler
