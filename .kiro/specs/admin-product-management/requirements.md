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

## Requirements

### Requirement 1: Admin Navigation Integration

**User Story:** As a webshop administrator, I want to access the webshop management section directly from the main H-DCN dashboard, so that I do not need to navigate through the PresMeet booking flow to perform administrative tasks.

#### Acceptance Criteria

1. THE Admin_Portal SHALL display a "Webshop Beheer" Dashboard_Card on the main `/dashboard` page for users with the `Webshop_Management` role
2. WHEN a user with the `Webshop_Management` role clicks the "Webshop Beheer" Dashboard_Card, THE Admin_Portal SHALL navigate to the `/webshop_management` route
3. THE Admin_Portal SHALL render the webshop management section at the `/webshop_management` route with tab or sub-navigation for Products, Orders, Payments, and Reports
4. THE Admin_Portal SHALL integrate the existing `/products` page (ProductManagementPage) as the Products sub-section within `/webshop_management`, making `/webshop_management` the parent navigation hub
5. WHEN a user without the `Webshop_Management` role navigates to `/webshop_management`, THE Admin_Portal SHALL deny access and display a 403 forbidden message
6. THE Admin_Portal SHALL use the existing FunctionGuard component with `requiredRoles={['Webshop_Management']}` to control visibility of the Dashboard_Card
7. THE Admin_Portal SHALL render the webshop management section independently of the PresMeet onboarding flow, requiring no club selection or club_id assignment for admin users

### Requirement 2: Product Configuration Management

**User Story:** As a webshop administrator, I want to manage all products from a single interface with tenant-based filtering, where each product is a single record containing both its catalog data (name, price) and its configuration rules (constraints, attribute schemas), so that all product behavior is data-driven and manageable without code changes.

#### Acceptance Criteria

1. THE Product_Manager SHALL store each product as a single record in the Producten table containing both catalog fields (name, price, description, active status) and configuration fields (max_per_club, min_per_club, required_attributes schema, product_type) in one unified record
2. THE Product_Manager SHALL display a list of all products from the Producten table, showing product name, tenant, product_type (if applicable), price, and active status
3. THE Product_Manager SHALL provide a tenant filter dropdown that allows filtering the product list by tenant value (e.g., "presmeet", "h-dcn", or "all")
4. WHEN a Webshop_Admin selects a product, THE Product_Manager SHALL display a detail/edit view showing all fields: catalog data (name, price, description, active) and configuration rules (max_per_club, min_per_club, required_attributes) in a single form
5. WHEN a Webshop_Admin creates a new product, THE Product_Manager SHALL create a single record with both catalog and configuration fields, assigning a tenant and optionally a product_type
6. WHEN a Webshop_Admin updates any field on a product (price, limits, attribute schema), THE Product_Manager SHALL persist the change to the single product record and the system SHALL use the updated values immediately without code deployment
7. IF a product has a `required_attributes` schema defined, THEN THE Product_Manager SHALL validate that `min_per_club` does not exceed `max_per_club` before saving
8. IF a Webshop_Admin attempts to save a product with an invalid `required_attributes` schema (malformed JSON, conflicting constraints), THEN THE Product_Manager SHALL display validation errors identifying the issue
9. THE backend SHALL read all product data (price, limits, attribute schemas) from the single product record at runtime, and SHALL NOT use hardcoded values in any handler code
10. THE Product_Manager SHALL display the tenant value as a label/badge on each product row to distinguish the source
11. THE system SHALL eliminate the current separation between "config records" (source: presmeet_config) and "product records" — each product SHALL be one self-contained record with all its rules and catalog data together

### Requirement 3: Product Variants (Parent/Child Model)

**User Story:** As a webshop administrator, I want products to support variants (e.g., t-shirt sizes and genders), so that each variant is independently trackable for stock and sales while sharing the parent product's configuration and pricing rules.

#### Acceptance Criteria

1. THE Product_Manager SHALL support a parent/child relationship where a parent product defines shared configuration (product_type, tenant, required_attributes, max_per_club, min_per_club, base price) and child variant records represent specific combinations (e.g., Male-S, Male-M, Female-L)
2. THE Product_Manager SHALL store variant records in the Producten table with a `parent_id` field referencing the parent product's `product_id`
3. EACH variant record SHALL contain: variant-specific attribute values (e.g., gender: "male", size: "XL"), stock quantity, sales count, and optionally an overriding price (falling back to the parent's price if not set)
4. WHEN a Webshop_Admin views a parent product, THE Product_Manager SHALL display all its variants in a sub-table showing the variant attribute values, current stock, total sold, and price
5. WHEN a Webshop_Admin creates a new variant for a product, THE Product_Manager SHALL validate that the variant's attribute values conform to the parent's `required_attributes` enum definitions (e.g., size must be one of S, M, L, XL, XXL, 3XL, 4XL)
6. WHEN a cart item is created, THE system SHALL link it to the specific variant record (not the parent), decrementing stock on that variant
7. THE Product_Manager SHALL allow a Webshop_Admin to update stock levels on individual variants
8. THE Product_Manager SHALL display aggregated totals per parent product (total stock across all variants, total sold across all variants) alongside the per-variant breakdown
9. WHEN a Webshop_Admin bulk-creates variants, THE Product_Manager SHALL generate variant records for all valid attribute combinations defined in the parent's `required_attributes` enums (e.g., all gender × size combinations for t-shirts)
10. IF a variant's stock reaches zero, THE Product_Manager SHALL mark the variant as out-of-stock but SHALL NOT prevent admin from viewing or editing it

### Requirement 4: Order Management

**User Story:** As a webshop administrator, I want to view and manage all orders from a central location with tenant-based filtering, so that I can track order status across all sources (webshop, presmeet, future tenants) from one interface.

#### Acceptance Criteria

1. THE Order_Manager SHALL display a table of all orders from the Orders table, showing order ID, tenant, customer/club name, order status, payment status, total amount, amount paid, outstanding balance, creation date, and submission date
2. THE Order_Manager SHALL provide a tenant filter dropdown that allows filtering the order list by tenant value (e.g., "presmeet", "h-dcn", or "all")
3. THE Order_Manager SHALL default the tenant filter to "all" showing orders from all tenants
4. WHEN a Webshop_Admin selects an order row, THE Order_Manager SHALL display full order details including all line items with their product_type, attributes, quantity, and unit price, plus the complete payment history
5. WHEN a Webshop_Admin clicks "Lock" on an order with status "submitted", THE Order_Manager SHALL transition the order status to "locked" and refresh the order list
6. WHEN a Webshop_Admin clicks "Unlock" on an order with status "locked", THE Order_Manager SHALL transition the order status back to "submitted" and refresh the order list
7. WHEN a Webshop_Admin clicks "Lock ALL", THE Order_Manager SHALL transition all orders matching the current tenant filter that are in "submitted" status to "locked" status
8. THE Order_Manager SHALL display a status badge for each order using distinct colors: gray for draft, blue for submitted, green for locked
9. THE Order_Manager SHALL display the tenant value as a label/badge on each order row to distinguish the source
10. IF a lock or unlock operation fails, THEN THE Order_Manager SHALL display an error toast notification with the failure reason and leave the order status unchanged

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

**User Story:** As a webshop administrator, I want financial and non-financial reports on order data across all tenants, so that I can monitor business progress with the ability to drill down by tenant.

#### Acceptance Criteria

1. THE Report_Generator SHALL display a summary overview showing total orders, total revenue, total paid, and total outstanding, filterable by tenant
2. WHEN tenant filter is set to "presmeet", THE Report_Generator SHALL display PresMeet-specific metrics: total counts per product_type split by order status (draft, submitted, locked)
3. WHEN tenant filter is set to "h-dcn", THE Report_Generator SHALL display regular webshop metrics: total orders, items sold, and revenue by product
4. WHEN a Webshop_Admin clicks "Refresh Data", THE Report_Generator SHALL regenerate report data and reload the display
5. THE Report_Generator SHALL provide a downloadable CSV export of orders matching the current tenant filter, containing customer/club name, order status, and for each item: product_type, quantity, unit price, and all attribute values
6. THE Report_Generator SHALL display the report generation timestamp
7. WHEN a CSV download fails, THE Report_Generator SHALL display an error toast notification with the failure reason

### Requirement 7: Role-Based Access Control

**User Story:** As a system administrator, I want the webshop management section protected by the existing Cognito role system, so that only authorized users can access administrative functionality.

#### Acceptance Criteria

1. THE Admin_Portal SHALL require the `Webshop_Management` Cognito group membership to access any functionality within the `/webshop_management` route
2. WHEN an authenticated user without the `Webshop_Management` role requests any admin API endpoint (`/presmeet/admin/*`), THE Admin_Portal SHALL return a 403 error response
3. THE Admin_Portal SHALL NOT require any region-specific role (Regio_Pressmeet or Regio_All) for accessing the webshop management section, unlike the current PresMeet admin tab which requires both management and region roles
4. THE Admin_Portal SHALL validate the user's access token on each API request to the admin endpoints using the existing `validate_permissions_with_regions` function from the auth layer
5. IF the user's session expires while using the webshop management section, THEN THE Admin_Portal SHALL redirect the user to the login page

### Requirement 8: Separation from PresMeet Booking Flow

**User Story:** As a webshop administrator, I want the admin section to function as a generic management tool where PresMeet is just one tenant, so that future order sources can be managed through the same interface.

#### Acceptance Criteria

1. THE Admin_Portal SHALL render the webshop management section without requiring a `club_id` assignment or club onboarding completion for the logged-in user
2. THE Admin_Portal SHALL NOT display the OnboardingFlow component when accessing the `/webshop_management` route
3. THE Admin_Portal SHALL use generic API endpoints for order management (e.g., `/admin/orders`, `/admin/payments`) that accept a `tenant` query parameter for filtering, rather than presmeet-specific endpoints
4. IF no tenant filter is specified, THE Admin_Portal SHALL return data from all tenants
5. THE Admin_Portal SHALL treat the existing PresMeet admin endpoints (`/presmeet/admin/*`) as the PresMeet-tenant-specific implementation that the generic endpoints delegate to when `tenant=presmeet`
6. WHEN a new tenant is introduced in the future, THE Admin_Portal SHALL support it by adding the tenant value to the filter options without requiring changes to the order management, payment, or reporting UI logic
