# Requirements Document

## Introduction

The Admin Product Management feature restructures the existing PresMeet admin functionality from its current location (hidden behind the club onboarding flow in `/presmeet`) into a proper admin management section accessible from the main H-DCN dashboard. This new section — accessible at `/webshop_management` — serves as the administrative hub for the webshop, consolidating the existing `/products` page and adding order management, payment tracking, and reporting capabilities. The section is accessible to users with the `Webshop_Management` role and operates independently of the PresMeet club onboarding flow.

## Glossary

- **Admin_Portal**: The administrative section of the H-DCN member portal accessible from the main dashboard, housing management tools for Members, Events, Products, and the new Webshop Management
- **Webshop_Admin**: An authenticated user with the `Webshop_Management` Cognito group role, authorized to manage products, orders, payments, and reports
- **Tenant**: A logical grouping/source of orders within the system. Current tenants are `"presmeet"` (Presidents' Meeting bookings) and `"h-dcn"` (regular webshop orders). The tenant field on each order determines which filter group it belongs to
- **Product_Manager**: The component responsible for defining and configuring products, including product types and their attributes
- **Order_Manager**: The generic component responsible for viewing and managing all orders across all tenants, with tenant-based filtering
- **Payment_Tracker**: The component responsible for viewing payment status, recording manual payments, and tracking outstanding balances across all tenants
- **Report_Generator**: The component responsible for producing financial and non-financial reports and analytics, filterable by tenant
- **Dashboard_Card**: A navigation tile on the main `/dashboard` page that routes to a specific admin function, guarded by role-based access control
- **FunctionGuard**: The existing React component that conditionally renders UI elements based on Cognito group membership
- **Product_Type_Config**: A configuration record defining rules per product type (max_per_club, min_per_club, pricing, required_attributes schema)
- **Allow_Oversell**: A boolean flag on each variant record (defaults to `false`) that controls whether sales may proceed when the variant's stock reaches zero or would go negative. Each variant can have its own `allow_oversell` setting independently
- **Default_Variant**: A single variant record with empty `variant_attributes` (`{}`) that is automatically created for simple products (products without attribute combinations). This ensures all stock is tracked at the variant level uniformly
- **Stock_Movement**: A record tracking a change in variant stock — either inbound (purchase/receipt of goods) or outbound (sale fulfillment). Each movement records the quantity, cost, supplier (for inbound), and the user who recorded it.

## Requirements

### Requirement 1: Admin Navigation Integration

**User Story:** As a webshop administrator, I want to access the webshop management section directly from the main H-DCN dashboard, so that I do not need to navigate through the PresMeet booking flow to perform administrative tasks.

#### Acceptance Criteria

1. THE Admin*Portal SHALL display a "Webshop Beheer" Dashboard_Card on the main `/dashboard` page for users with any Products*\* role (`Products_CRUD`, `Products_Read`, or `Products_Export`)
2. WHEN a user with a qualifying Products\_\* role clicks the "Webshop Beheer" Dashboard_Card, THE Admin_Portal SHALL navigate to the `/webshop_management` route
3. THE Admin_Portal SHALL render the webshop management section at the `/webshop_management` route with tab or sub-navigation for Products, Orders, Payments, and Reports
4. THE Admin_Portal SHALL integrate the existing `/products` page (ProductManagementPage) as the Products sub-section within `/webshop_management`, making `/webshop_management` the parent navigation hub
5. WHEN a user without any Products\_\* role navigates to `/webshop_management`, THE Admin_Portal SHALL deny access and display a 403 forbidden message
6. THE Admin_Portal SHALL use the existing FunctionGuard component with `requiredRoles={['Products_CRUD', 'Products_Read', 'Products_Export']}` to control visibility of the Dashboard_Card
7. THE Admin_Portal SHALL render the webshop management section independently of the PresMeet onboarding flow, requiring no club selection or club_id assignment for admin users

### Requirement 2: Product Configuration Management

**User Story:** As a webshop administrator, I want to manage all products from a single interface with tenant-based filtering, where each product is a single record containing both its catalog data (name, price) and its configuration rules (constraints, attribute schemas), so that all product behavior is data-driven and manageable without code changes.

#### Acceptance Criteria

1. THE Product_Manager SHALL store each product as a single record in the Producten table containing catalog fields (name, price, description, active status) and configuration fields (max_per_club, min_per_club, required_attributes schema, product_type) in one unified record. Stock management fields (stock, sold_count, allow_oversell) SHALL reside exclusively on variant records, never on the parent product record
2. THE Product_Manager SHALL display a list of all products from the Producten table, showing product name, tenant, product_type (if applicable), price, and active status
3. THE Product_Manager SHALL provide a tenant filter dropdown that allows filtering the product list by tenant value (e.g., "presmeet", "h-dcn", or "all")
4. WHEN a Webshop_Admin selects a product, THE Product_Manager SHALL display a detail/edit view showing all fields: catalog data (name, price, description, active), configuration rules (max_per_club, min_per_club, required_attributes), and a variants sub-section listing all variants with their stock, sold_count, allow_oversell flag, and variant attributes in a single form
5. WHEN a Webshop_Admin creates a new product, THE Product_Manager SHALL create a product record with catalog fields and configuration fields, assigning a tenant and optionally a product_type. THE Product_Manager SHALL also create a Default_Variant record (with empty `variant_attributes`, stock defaulting to 0, sold_count defaulting to 0, and allow_oversell defaulting to false) automatically, ensuring stock is always tracked at the variant level
6. WHEN a Webshop_Admin updates any field on a product (price, limits, attribute schema), THE Product_Manager SHALL persist the change to the single product record and the system SHALL use the updated values immediately without code deployment
7. IF a product has a `required_attributes` schema defined, THEN THE Product_Manager SHALL validate that `min_per_club` does not exceed `max_per_club` before saving
8. IF a Webshop_Admin attempts to save a product with an invalid `required_attributes` schema (malformed JSON, conflicting constraints), THEN THE Product_Manager SHALL display validation errors identifying the issue
9. THE backend SHALL read all product data (price, limits, attribute schemas) from the single product record at runtime, and SHALL NOT use hardcoded values in any handler code
10. THE Product_Manager SHALL display the tenant value as a label/badge on each product row to distinguish the source
11. THE system SHALL eliminate the current separation between "config records" (source: presmeet_config) and "product records" — each product SHALL be one self-contained record with all its rules and catalog data together

### Requirement 3: Stock Management and Product Variants

**User Story:** As a webshop administrator, I want all products to track stock exclusively at the variant level — every product has at least one variant — so that inventory management is uniform. I also want products to support multiple variants (e.g., t-shirt sizes and genders) where each variant is independently trackable for stock and sales while sharing the parent product's configuration and pricing rules. Additionally, I want an `allow_oversell` flag per variant to control whether sales can proceed when that variant's stock reaches zero or would go negative.

#### Acceptance Criteria

1. THE Product_Manager SHALL enforce that every product has at least one variant record. Simple products (without attribute combinations such as badges or pins) SHALL have a single Default_Variant with empty `variant_attributes` (`{}`). Stock SHALL always be tracked at the variant level; the parent product record SHALL NOT store stock or sold_count fields
2. THE Product_Manager SHALL support a parent/child relationship where a parent product defines shared configuration (product_type, tenant, required_attributes, max_per_club, min_per_club, base price) and child variant records represent specific combinations (e.g., Male-S, Male-M, Female-L) or a single Default_Variant for simple products
3. THE Product_Manager SHALL store variant records in the Producten table with a `parent_id` field referencing the parent product's `product_id`
4. EACH variant record SHALL contain: variant-specific attribute values (e.g., gender: "male", size: "XL", or `{}` for Default_Variant), stock quantity, sold_count, the `allow_oversell` boolean flag (defaulting to false), and optionally an overriding price (falling back to the parent's price if not set)
5. WHEN a Webshop_Admin views a parent product, THE Product_Manager SHALL display all its variants in a sub-table showing the variant attribute values, current stock, total sold, allow_oversell flag, and price
6. WHEN a Webshop_Admin creates a new variant for a product, THE Product_Manager SHALL validate that the variant's attribute values conform to the parent's `required_attributes` enum definitions (e.g., size must be one of S, M, L, XL, XXL, 3XL, 4XL)
7. WHEN a Webshop_Admin adds attribute-based variants to a product that currently has only a Default_Variant, THE Product_Manager SHALL remove the Default_Variant after the new variants are created, preserving the principle that a product either has one Default_Variant or one-or-more attribute-based variants
8. WHEN a cart item is created for any product, THE system SHALL link it to the specific variant record and decrement stock on that variant. The parent product record is never directly referenced for stock operations
9. THE Product_Manager SHALL allow a Webshop_Admin to update stock levels and the `allow_oversell` flag on individual variants
10. THE Product_Manager SHALL display aggregated totals per parent product (total stock across all variants, total sold across all variants) alongside the per-variant breakdown
11. WHEN a Webshop_Admin bulk-creates variants, THE Product_Manager SHALL generate variant records for all valid attribute combinations defined in the parent's `required_attributes` enums (e.g., all gender × size combinations for t-shirts), removing any existing Default_Variant in the process
12. IF a variant's stock reaches zero AND that variant's `allow_oversell` is false, THE system SHALL prevent adding that variant to the cart and display an out-of-stock indication
13. EACH variant record SHALL have its own `allow_oversell` boolean flag, defaulting to `false`. This flag is set independently per variant, not inherited from the parent product
14. WHEN a variant's `allow_oversell` is set to `true`, THE system SHALL allow cart additions and order placement to proceed for that variant even when its calculated stock would go negative
15. WHEN a variant's `allow_oversell` is set to `false` (default), THE system SHALL prevent adding that variant to the cart when its stock is zero or when the requested quantity would cause its stock to go negative
16. THE Product_Manager SHALL allow a Webshop_Admin to view and edit the `allow_oversell` flag on each variant independently in the product detail/edit form
17. IF a variant's stock reaches zero AND its `allow_oversell` is false, THE Product_Manager SHALL mark the variant as out-of-stock but SHALL NOT prevent admin from viewing or editing it
18. WHEN a product has a single Default_Variant, THE Product_Manager SHALL display stock management fields (stock, sold_count, allow_oversell) inline on the product detail view without requiring the admin to navigate into a separate variants sub-table

### Requirement 4: Order Management

**User Story:** As a webshop administrator, I want to view and manage all orders from a central location with tenant-based filtering, including a full order lifecycle with defined states, so that I can track order progress across all sources from one interface.

#### Acceptance Criteria

1. THE Order_Manager SHALL support the following order states: `draft`, `submitted`, `locked`, `order_received`, `payment_pending`, `payment_failed`, `paid`, `picked`, `packed`, `shipped`, `delivered`, `return_requested`, `return_received`, `completed`
2. THE Order_Manager SHALL enforce valid state transitions: draft → submitted → locked → order_received → payment_pending or paid → picked → packed → shipped → delivered → return_requested → return_received → completed. Payment_failed is a terminal state. Payment_pending can transition to paid or payment_failed. An admin SHALL be able to skip intermediate states by jumping forward multiple steps in one action (e.g., directly from order_received to paid, or from paid to shipped), provided the target state is reachable from the current state in the defined sequence.
3. THE Order_Manager SHALL display a table of all orders from the Orders table, showing order ID, tenant, customer/club name, order status, payment status, total amount, amount paid, outstanding balance, creation date, and submission date
4. THE Order_Manager SHALL provide a tenant filter dropdown that allows filtering the order list by tenant value (e.g., "presmeet", "h-dcn", or "all")
5. THE Order_Manager SHALL default the tenant filter to "all" showing orders from all tenants
6. WHEN a user with Products_CRUD selects an order row, THE Order_Manager SHALL display full order details including all line items with their product_type, attributes, quantity, and unit price, plus the complete payment history and state transition history
7. THE Order_Manager SHALL allow a user with Products_CRUD to manually advance an order to the next valid state via a status transition button
8. WHEN a user with Products_CRUD clicks "Lock" on an order with status "submitted", THE Order_Manager SHALL transition the order status to "locked" and refresh the order list
9. WHEN a user with Products_CRUD clicks "Unlock" on an order with status "locked", THE Order_Manager SHALL transition the order status back to "submitted" and refresh the order list
10. WHEN a user with Products_CRUD clicks "Lock ALL", THE Order_Manager SHALL transition all orders matching the current tenant filter that are in "submitted" status to "locked" status
11. THE Order_Manager SHALL display a status badge for each order using distinct colors per state (e.g., gray=draft, blue=submitted, green=locked/paid, orange=shipped, red=payment_failed)
12. THE Order_Manager SHALL display the tenant value as a label/badge on each order row to distinguish the source
13. THE Order_Manager SHALL record each state transition with a timestamp and the user who triggered it, stored on the order record as a `status_history` array
14. IF a state transition fails or is invalid, THEN THE Order_Manager SHALL display an error toast notification with the failure reason and leave the order status unchanged
15. WHEN an order transitions to "paid", THE Order_Manager SHALL reserve stock on the associated variant records — decrementing `stock` and incrementing `sold_count` on each line item's variant by exactly the line item's quantity. Stock is always reserved at the variant level, including for products with a single Default_Variant
16. THE Order_Manager SHALL display the tenant value as a label/badge on each order row to distinguish the source
17. IF a lock or unlock operation fails, THEN THE Order_Manager SHALL display an error toast notification with the failure reason and leave the order status unchanged

### Requirement 5: Payment Tracking

**User Story:** As a webshop administrator, I want to view payment status and record manual payments across all tenants, so that I can track financial obligations and reconcile offline payments regardless of order source.

#### Acceptance Criteria

1. THE Payment_Tracker SHALL display aggregate payment statistics showing total charged, total paid, and total outstanding, filterable by tenant (all, presmeet, h-dcn)
2. WHEN a Webshop_Admin opens the payment recording form, THE Payment_Tracker SHALL require input of order ID, amount (between €0.01 and €999,999.99), date (ISO format), and optional description (maximum 255 characters)
3. WHEN a Webshop_Admin submits a valid manual payment, THE Payment_Tracker SHALL record the payment against the specified order and update the display upon success
4. IF a manual payment submission fails, THEN THE Payment_Tracker SHALL display an error message with the failure reason and preserve the form inputs
5. THE Payment_Tracker SHALL display each order's payment status using distinct badge colors: green for "paid", yellow for "partial", red for "unpaid"
6. WHEN a Webshop_Admin views an order's payment history, THE Payment_Tracker SHALL display all payment records for that order showing amount, date, description, and payment method (mollie or manual)
7. THE Payment_Tracker SHALL respect the active tenant filter, showing only payment statistics for orders matching the selected tenant

### Requirement 6: Reporting and Analytics

**User Story:** As a webshop administrator, I want financial and non-financial reports on order data across all tenants, stored in S3 for both online display and local download, so that I can monitor business progress and process data offline.

#### Acceptance Criteria

1. WHEN a user with Products_CRUD clicks "Refresh Data", THE Report_Generator SHALL generate a report snapshot, store it as a JSON file in S3, and reload the display from the stored snapshot
2. THE Report_Generator SHALL read report data from the S3-stored snapshot for online display, rather than querying DynamoDB on every page load
3. THE Report_Generator SHALL display a summary overview from the stored snapshot showing total orders, total revenue, total paid, and total outstanding, filterable by tenant
4. WHEN tenant filter is set to "presmeet", THE Report_Generator SHALL display PresMeet-specific metrics: total counts per product_type split by order status (draft, submitted, locked)
5. WHEN tenant filter is set to "h-dcn", THE Report_Generator SHALL display regular webshop metrics: total orders, items sold, and revenue by product
6. WHEN a user downloads the report, THE Report_Generator SHALL offer the choice of CSV or JSON format, generating the file on-the-fly from the stored JSON snapshot, respecting the active tenant filter. The CSV SHALL contain a flat structure (customer/club name, order status, product_type, quantity, unit price, attribute values). The JSON SHALL preserve the full nested structure (orders with items and payment history).
7. THE Report_Generator SHALL display the report generation timestamp on the stored snapshot so the user knows how current the data is
8. WHEN a report generation or download fails, THE Report_Generator SHALL display an error toast notification with the failure reason

### Requirement 7: Role-Based Access Control

**User Story:** As a system administrator, I want the webshop management section protected by the existing Cognito role system using the Products\_\* role family, so that access is consistent with the read/CRUD/export model used across the portal.

#### Acceptance Criteria

1. THE Admin_Portal SHALL require at least one of `Products_CRUD`, `Products_Read`, or `Products_Export` Cognito group membership to access the `/webshop_management` route
2. WHEN a user has `Products_Read` only, THE Admin_Portal SHALL allow viewing all sections (products, orders, payments, reports) but SHALL disable all create, update, delete, lock/unlock, and manual payment actions
3. WHEN a user has `Products_CRUD`, THE Admin_Portal SHALL grant full access to all functionality: product management, variant management, order lock/unlock, manual payment recording, and reporting
4. WHEN a user has `Products_Export`, THE Admin_Portal SHALL allow downloading CSV exports from the Reports tab (can be combined with Read or CRUD)
5. THE Admin_Portal SHALL treat the existing `Webshop_Management` role as equivalent to `Products_CRUD` for backward compatibility until it is fully deprecated
6. THE Admin_Portal SHALL NOT require any region-specific role (Regio_Pressmeet or Regio_All) for accessing the webshop management section
7. THE Admin_Portal SHALL validate the user's access token on each API request using the existing `validate_permissions_with_regions` function from the auth layer
8. IF the user's session expires while using the webshop management section, THEN THE Admin_Portal SHALL redirect the user to the login page
9. WHEN an authenticated user without any qualifying Products\_\* role navigates to `/webshop_management`, THE Admin_Portal SHALL deny access and display a 403 forbidden message

### Requirement 8: Separation from PresMeet Booking Flow

**User Story:** As a webshop administrator, I want the admin section to function as a generic management tool where PresMeet is just one tenant, so that future order sources can be managed through the same interface.

#### Acceptance Criteria

1. THE Admin_Portal SHALL render the webshop management section without requiring a `club_id` assignment or club onboarding completion for the logged-in user
2. THE Admin_Portal SHALL NOT display the OnboardingFlow component when accessing the `/webshop_management` route
3. THE Admin_Portal SHALL use generic API endpoints for order management (e.g., `/admin/orders`, `/admin/payments`) that accept a `tenant` query parameter for filtering, rather than presmeet-specific endpoints
4. IF no tenant filter is specified, THE Admin_Portal SHALL return data from all tenants
5. THE Admin_Portal SHALL treat the existing PresMeet admin endpoints (`/presmeet/admin/*`) as the PresMeet-tenant-specific implementation that the generic endpoints delegate to when `tenant=presmeet`
6. WHEN a new tenant is introduced in the future, THE Admin_Portal SHALL support it by adding the tenant value to the filter options without requiring changes to the order management, payment, or reporting UI logic

### Requirement 9: Stock Movements

**User Story:** As a webshop administrator, I want to record inbound stock movements (purchase orders) per variant with purchase price and supplier information, so that I can track inventory additions, calculate actual stock from movement history, and analyze purchase costs.

#### Acceptance Criteria

1. THE Product_Manager SHALL provide a "Voeg voorraad toe" (Add stock) action on each variant, accessible to users with Products_CRUD role
2. WHEN a Webshop_Admin adds stock to a variant, THE system SHALL require input of: quantity (positive integer), purchase price per unit (€0.01 - €999,999.99), supplier name (required, max 100 characters), and optional reference/note (max 255 characters)
3. WHEN a valid inbound stock movement is submitted, THE system SHALL create a stock movement record with type "inbound", the variant_id, the tenant (matching the variant's tenant), the quantity, purchase_price_per_unit, total_cost (quantity × purchase_price_per_unit), supplier_name, recorded_by (email of the logged-in user), reference, and timestamp
4. WHEN a valid inbound stock movement is recorded, THE system SHALL increment the variant's `stock` field by the submitted quantity
5. WHEN an order transitions to "paid", THE system SHALL automatically create stock movement records with type "sale" for each line item, recording the variant_id, tenant, quantity (as negative or a separate field), and a reference to the order_id
6. THE Product_Manager SHALL display stock movement history per variant, showing date, type (inbound/sale), quantity, purchase price (for inbound), supplier (for inbound), reference, and recorded_by
7. THE Report_Generator SHALL include purchase cost data in reports: total purchase cost by tenant, weighted average cost per variant (total inbound cost ÷ total inbound quantity), and gross margin (selling price − weighted average cost)
8. THE system SHALL store stock movement records with a `tenant` field, and the stock movements SHALL be filterable by tenant in both the admin UI and reports
9. IF an inbound stock movement submission fails, THEN THE system SHALL display an error toast with the failure reason and preserve the form inputs
