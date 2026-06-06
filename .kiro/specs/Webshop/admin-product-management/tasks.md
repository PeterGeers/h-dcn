# Implementation Plan

## Overview

This plan implements the Admin Product Management feature, restructuring the PresMeet admin into a unified webshop management section at `/webshop_management`. The implementation is organized backend-first (shared modules → handlers → SAM template) then frontend (types → components → pages → tests), ensuring each layer builds on the previous.

## Tasks

- [x] 1. Create order state machine module
  - [x] 1.1 Create `backend/handler/shared/order_state_machine.py` with `ORDERED_STATES`, `SPECIAL_TRANSITIONS`, and `is_valid_transition(current, target)` function per design doc
  - [x] 1.2 Implement `get_next_valid_states(current_status)` helper returning all valid target states from a given state
  - [x] 1.3 Write property-based test (Hypothesis) for state transition validity (Property 8) at `backend/tests/unit/test_admin_properties.py`
- [x] 2. Create product validation module
  - [x] 2.1 Create `backend/handler/shared/product_validation.py` with `validate_product(payload)` function checking min_per_club ≤ max_per_club, required_attributes schema validity
  - [x] 2.2 Implement `validate_variant_attributes(variant_attrs, parent_required_attributes)` to check variant values conform to parent enum definitions
  - [x] 2.3 Write property-based test (Hypothesis) for product validation constraints (Property 4) at `backend/tests/unit/test_admin_properties.py`
- [x] 3. Create stock and payment calculation helpers
  - [x] 3.1 Create `backend/handler/shared/stock_helpers.py` with `reserve_stock(order_items, producten_table, movements_table, order_id, tenant)` function per design doc
  - [x] 3.2 Implement `create_inbound_movement(variant_id, tenant, quantity, purchase_price_per_unit, supplier_name, recorded_by, reference, movements_table)` in `stock_helpers.py`
  - [x] 3.3 Create `backend/handler/shared/payment_helpers.py` with `compute_payment_aggregates(orders)` returning total_charged, total_paid, total_outstanding
  - [x] 3.4 Write property-based test (Hypothesis) for payment aggregate correctness (Property 12) at `backend/tests/unit/test_admin_properties.py`
  - [x] 3.5 Write property-based test (Hypothesis) for stock reservation always targets variant records (Property 10) at `backend/tests/unit/test_admin_properties.py`
  - [x] 3.6 Write property-based test (Hypothesis) for inbound stock movement consistency (Property 18) at `backend/tests/unit/test_admin_properties.py`
  - [x] 3.7 Write property-based test (Hypothesis) for sale movement auto-creation (Property 19) at `backend/tests/unit/test_admin_properties.py`
- [x] 4. Create variant generation module
  - [x] 4.1 Create `backend/handler/shared/variant_helpers.py` with `generate_variant_combinations(required_attributes)` producing all attribute combos
  - [x] 4.2 Implement `create_default_variant(parent_product_id, tenant)` and `should_remove_default_variant(existing_variants, new_variants)` helpers
  - [x] 4.3 Write property-based test (Hypothesis) for bulk variant generation (Property 7) at `backend/tests/unit/test_admin_properties.py`
  - [x] 4.4 Write property-based test (Hypothesis) for variant aggregation correctness (Property 6) at `backend/tests/unit/test_admin_properties.py`
  - [x] 4.5 Write property-based test (Hypothesis) for Default_Variant auto-creation and removal (Property 16) at `backend/tests/unit/test_admin_properties.py`
  - [x] 4.6 Write property-based test (Hypothesis) for oversell control per variant (Property 15) at `backend/tests/unit/test_admin_properties.py`
- [x] 5. Implement admin product CRUD handlers
  - [x] 5.1 Create `backend/handler/admin_get_products/app.py` — GET `/admin/products` with tenant query param filter, requires Products_Read
  - [x] 5.2 Create `backend/handler/admin_create_product/app.py` — POST `/admin/products` with auto-creation of Default_Variant, requires Products_CRUD
  - [x] 5.3 Create `backend/handler/admin_update_product/app.py` — PUT `/admin/products/{id}` for catalog and config field updates, requires Products_CRUD
  - [x] 5.4 Create `backend/handler/admin_create_variant/app.py` — POST `/admin/products/{id}/variants` with attribute validation, removes Default_Variant when applicable, requires Products_CRUD
  - [x] 5.5 Create `backend/handler/admin_update_variant/app.py` — PUT `/admin/products/{id}/variants/{vid}` for stock, allow_oversell, price, requires Products_CRUD
  - [x] 5.6 Create `backend/handler/admin_bulk_create_variants/app.py` — POST `/admin/products/{id}/variants/bulk` generating all combos from required_attributes, requires Products_CRUD
- [x] 6. Implement admin stock movement handlers
  - [x] 6.1 Create `backend/handler/admin_add_stock/app.py` — POST `/admin/products/{id}/variants/{vid}/stock` recording inbound movement and incrementing variant stock, requires Products_CRUD
  - [x] 6.2 Create `backend/handler/admin_get_stock_movements/app.py` — GET `/admin/products/{id}/variants/{vid}/movements` with tenant filter, requires Products_Read
- [x] 7. Implement admin order management handlers
  - [x] 7.1 Create `backend/handler/admin_get_orders/app.py` — GET `/admin/orders` with tenant and status query param filters, requires Products_Read
  - [x] 7.2 Create `backend/handler/admin_update_order_status/app.py` — PUT `/admin/orders/{id}/status` using state machine validation, optimistic locking, stock reservation on paid transition, status_history recording, requires Products_CRUD
  - [x] 7.3 Create `backend/handler/admin_lock_orders/app.py` — POST `/admin/orders/lock` bulk-locking all submitted orders matching tenant filter, requires Products_CRUD
  - [x] 7.4 Create `backend/handler/admin_unlock_order/app.py` — POST `/admin/orders/{id}/unlock` transitioning locked to submitted, requires Products_CRUD
- [x] 8. Implement admin payment handlers
  - [x] 8.1 Create `backend/handler/admin_get_payments/app.py` — GET `/admin/payments` returning aggregate stats and order payment details with tenant filter, requires Products_Read
  - [x] 8.2 Create `backend/handler/admin_record_payment/app.py` — POST `/admin/payments` recording manual payment, updating order amount_paid and payment_status, requires Products_CRUD
- [x] 9. Implement admin report handlers
  - [x] 9.1 Create `backend/handler/admin_generate_report/app.py` — POST `/admin/reports/generate` querying orders and stock movements, generating JSON snapshot to S3, requires Products_CRUD
  - [x] 9.2 Create `backend/handler/admin_get_report/app.py` — GET `/admin/reports` reading the latest S3 snapshot with tenant filter applied, requires Products_Read
  - [x] 9.3 Create `backend/handler/admin_export_report/app.py` — GET `/admin/reports/export` generating CSV or JSON download from snapshot with tenant filter, requires Products_Export
- [x] 10. Create DynamoDB StockMovements table, Producten GSI, and Reports S3 bucket via AWS CLI
  - [x] 10.1 Create StockMovements DynamoDB table via `aws dynamodb create-table --profile nonprofit-deploy --region eu-west-1` with partition key `movement_id` (S), billing PAY_PER_REQUEST
  - [x] 10.2 Create GSI `variant_id-index` on StockMovements with partition key `variant_id` (S) and sort key `created_at` (S)
  - [x] 10.3 Create GSI `tenant-index` on StockMovements with partition key `tenant` (S) and sort key `created_at` (S)
  - [x] 10.4 Add GSI `parent_id-index` on existing Producten table via `aws dynamodb update-table --profile nonprofit-deploy --region eu-west-1` with partition key `parent_id` (S) for querying variants by parent product
  - [x] 10.5 Create S3 bucket for report snapshots via `aws s3 mb --profile nonprofit-deploy --region eu-west-1` with appropriate naming (e.g., `h-dcn-webshop-reports`)
  - [x] 10.6 Configure CORS on the reports S3 bucket via `aws s3api put-bucket-cors --profile nonprofit-deploy` allowing GET/PUT from `https://portal.h-dcn.nl` origin, and set a bucket policy granting Lambda execution role access
  - [x] 10.7 Add a data migration script at `backend/scripts/migrate_products_to_unified.py` that converts existing presmeet_config records into unified product records with `is_parent: true`, `parent_id: null`, and creates Default_Variant records for each existing product
  - [x] 10.8 Run the data migration script against the Producten table in the nonprofit account to seed unified product records and Default_Variants for all existing products
- [x] 11. Update SAM template with new resources
  - [x] 11.1 Add parameters for StockMovements table name and Reports S3 bucket name to `backend/template.yaml`
  - [x] 11.2 Add all 17 new Lambda function resources with API Gateway events, environment variables, and IAM policies to `backend/template.yaml`
  - [x] 11.3 Add API Gateway resource paths under existing REST API for `/admin/*` routes with Cognito authorizer
- [x] 12. Create frontend TypeScript types and API client
  - [x] 12.1 Create `frontend/src/modules/webshop-management/types/admin.types.ts` with all interfaces (AdminProduct, AdminVariant, AdminOrder, OrderStatus, StatusHistoryEntry, StockMovement, RecordPaymentRequest, AddStockRequest, ReportResponse) per design doc
  - [x] 12.2 Create `frontend/src/modules/webshop-management/services/adminApi.ts` with Axios-based API client functions for all `/admin/*` endpoints accepting tenant query param
- [x] 13. Create shared frontend components
  - [x] 13.1 Create `frontend/src/modules/webshop-management/components/TenantFilter.tsx` — dropdown with all, presmeet, h-dcn options
  - [x] 13.2 Create `frontend/src/modules/webshop-management/components/StatusBadge.tsx` — badge with color mapping per order status
  - [x] 13.3 Create `frontend/src/modules/webshop-management/hooks/useTenantFilter.ts` — shared hook for tenant filter state management
- [x] 14. Create WebshopManagementPage with routing
  - [x] 14.1 Create `frontend/src/modules/webshop-management/WebshopManagementPage.tsx` with Chakra UI Tabs for Products, Orders, Payments, Reports
  - [x] 14.2 Add `/webshop_management` route to the app router protected by FunctionGuard with requiredRoles Products_CRUD, Products_Read, Products_Export
  - [x] 14.3 Add Webshop Beheer Dashboard*Card to the main dashboard page gated by FunctionGuard with Products*\* roles
  - [x] 14.4 Ensure route renders independently of PresMeet onboarding flow with no club_id or OnboardingFlow dependency
- [x] 15. Implement Products tab with variant management
  - [x] 15.1 Create `frontend/src/modules/webshop-management/components/ProductsTab.tsx` wrapping existing ProductManagementPage with TenantFilter
  - [x] 15.2 Create `frontend/src/modules/webshop-management/components/VariantSubTable.tsx` displaying variants with stock, sold_count, allow_oversell, price, and attribute values
  - [x] 15.3 Create `frontend/src/modules/webshop-management/components/BulkVariantCreator.tsx` — modal for generating all attribute combinations from required_attributes enums
  - [x] 15.4 Add inline stock management display for single Default_Variant products showing stock, sold_count, allow_oversell directly without sub-table
  - [x] 15.5 Add stock movement recording form (Voeg voorraad toe) with quantity, purchase price, supplier, reference fields on each variant
- [x] 16. Implement Orders tab
  - [x] 16.1 Create `frontend/src/modules/webshop-management/hooks/useAdminOrders.ts` — data fetching hook with tenant and status filtering
  - [x] 16.2 Create `frontend/src/modules/webshop-management/components/OrdersTab.tsx` — order table with order ID, tenant badge, customer/club name, status badge, payment badge, total, paid, outstanding, dates
  - [x] 16.3 Create `frontend/src/modules/webshop-management/components/OrderDetailDrawer.tsx` — drawer showing line items, payment history, status history
  - [x] 16.4 Implement state transition controls with next status button, Lock/Unlock buttons, and Lock ALL bulk action
  - [x] 16.5 Implement role-based action gating disabling mutation buttons for Products_Read-only users
- [x] 17. Implement Payments tab
  - [x] 17.1 Create `frontend/src/modules/webshop-management/hooks/useAdminPayments.ts` — data fetching hook for payment stats and recording
  - [x] 17.2 Create `frontend/src/modules/webshop-management/components/PaymentsTab.tsx` — aggregate stats display with tenant filter and payment status badges per order
  - [x] 17.3 Add manual payment recording form with Formik and Yup validation for order_id, amount 0.01-999999.99, ISO date, optional description max 255 chars, preserving inputs on failure
- [x] 18. Implement Reports tab
  - [x] 18.1 Create `frontend/src/modules/webshop-management/hooks/useAdminReports.ts` — hook for loading S3 snapshot and triggering refresh and export
  - [x] 18.2 Create `frontend/src/modules/webshop-management/components/ReportsTab.tsx` — summary display with total orders, revenue, paid, outstanding, generation timestamp, Refresh Data button
  - [x] 18.3 Implement export controls with format selection CSV or JSON and download trigger respecting active tenant filter
  - [x] 18.4 Display PresMeet-specific metrics (counts per product_type by order status) when tenant filter is presmeet
  - [x] 18.5 Display H-DCN webshop metrics (orders, items sold, revenue by product) when tenant filter is h-dcn
- [x] 19. Implement frontend role-based access control
  - [x] 19.1 Implement Products_Read restriction allowing viewing all tabs but disabling all create, update, delete, lock, unlock, and payment-record actions
  - [x] 19.2 Implement Products_CRUD full access enabling all mutation actions across all tabs
  - [x] 19.3 Implement Products_Export restriction enabling CSV and JSON download buttons in Reports tab only when user has this role
  - [x] 19.4 Handle session expiry 401 response with redirect to login page
  - [x] 19.5 Display 403 forbidden message when unauthorized user navigates to /webshop_management
- [x] 20. Write frontend property-based tests
  - [x] 20.1 Write property-based test (fast-check) for role to action permission mapping (Property 1) at `frontend/src/modules/webshop-management/__tests__/admin.properties.test.ts`
  - [x] 20.2 Write property-based test (fast-check) for status badge color mapping correctness at `frontend/src/modules/webshop-management/__tests__/admin.properties.test.ts`
  - [x] 20.3 Write property-based test (fast-check) for payment status computation paid/partial/unpaid from amounts at `frontend/src/modules/webshop-management/__tests__/admin.properties.test.ts`
- [x] 21. Write remaining backend property-based tests
  - [x] 21.1 Write property-based test (Hypothesis) for tenant filter correctness (Property 2) at `backend/tests/unit/test_admin_properties.py`
  - [x] 21.2 Write property-based test (Hypothesis) for cart always links to variant (Property 17) at `backend/tests/unit/test_admin_properties.py`
  - [x] 21.3 Write property-based test (Hypothesis) for stock movement tenant consistency (Property 20) at `backend/tests/unit/test_admin_properties.py`
- [x] 22. Write backend integration tests
  - [x] 22.1 Create `backend/tests/integration/test_admin_endpoints.py` with moto-mocked DynamoDB and S3 fixtures
  - [x] 22.2 Write integration test for full order lifecycle: create, submit, lock, paid with stock reservation, shipped, delivered, completed
  - [x] 22.3 Write integration test for product CRUD with auto Default_Variant creation and bulk variant generation
  - [x] 22.4 Write integration test for manual payment recording and aggregate computation
  - [x] 22.5 Write integration test for report generation to S3 and export in CSV and JSON formats

## Task Dependency Graph

```json
{
  "waves": [
    {
      "id": 0,
      "tasks": [
        "1.1",
        "1.2",
        "1.3",
        "2.1",
        "2.2",
        "2.3",
        "3.1",
        "3.2",
        "3.3",
        "3.4",
        "3.5",
        "3.6",
        "3.7",
        "4.1",
        "4.2",
        "4.3",
        "4.4",
        "4.5",
        "4.6"
      ]
    },
    {
      "id": 1,
      "tasks": [
        "5.1",
        "5.2",
        "5.3",
        "5.4",
        "5.5",
        "5.6",
        "6.1",
        "6.2",
        "7.1",
        "7.2",
        "7.3",
        "7.4",
        "8.1",
        "8.2",
        "9.1",
        "9.2",
        "9.3",
        "10.1",
        "10.2",
        "10.3",
        "10.4",
        "10.5",
        "10.6",
        "10.7",
        "10.8",
        "12.1",
        "12.2",
        "21.1",
        "21.2",
        "21.3"
      ]
    },
    { "id": 2, "tasks": ["11.1", "11.2", "11.3", "13.1", "13.2", "13.3"] },
    { "id": 3, "tasks": ["14.1", "14.2", "14.3", "14.4"] },
    {
      "id": 4,
      "tasks": [
        "15.1",
        "15.2",
        "15.3",
        "15.4",
        "15.5",
        "16.1",
        "16.2",
        "16.3",
        "16.4",
        "16.5",
        "17.1",
        "17.2",
        "17.3",
        "18.1",
        "18.2",
        "18.3",
        "18.4",
        "18.5"
      ]
    },
    { "id": 5, "tasks": ["19.1", "19.2", "19.3", "19.4", "19.5"] },
    {
      "id": 6,
      "tasks": ["20.1", "20.2", "20.3", "22.1", "22.2", "22.3", "22.4", "22.5"]
    }
  ]
}
```

## Notes

- Backend shared modules (Tasks 1-4) must be implemented before handlers (Tasks 5-9) since handlers import from them
- DynamoDB table and S3 bucket creation (Task 10) can run in parallel with handlers since it uses AWS CLI with `--profile nonprofit-deploy`
- SAM template updates (Task 11) should come after all handlers are written to declare them correctly
- Frontend types and API client (Task 12) must be created before any frontend components
- Property-based tests within tasks 1-4 can run immediately after the module they test is implemented
- All backend handlers follow the existing pattern: import from shared.auth_utils, validate permissions, business logic, return response with CORS headers
- Frontend uses Chakra UI v2 components, Formik for forms, and Axios for HTTP
