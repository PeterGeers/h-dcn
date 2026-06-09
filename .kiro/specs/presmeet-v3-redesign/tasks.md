# Implementation Plan

## Overview

Implementation of the PresMeet v3 Redesign — replacing legacy PresMeet handlers with an event-driven, order-only architecture. Tasks cover shared layer modules, backend handlers, frontend components, channel rename migration, and integration testing.

## Tasks

- [x] 1. Shared Layer - Channel Resolver Rename
  - [x] 1.1. Rename `backend/layers/auth-layer/python/shared/tenant_resolver.py` to `channel_resolver.py`
  - [x] 1.2. Rename `resolve_tenants` to `resolve_channels` and `validate_tenant_access` to `validate_channel_access`
  - [x] 1.3. Rename `GROUP_TENANT_MAP` to `GROUP_CHANNEL_MAP` (same mappings: hdcnLeden → h-dcn, Regio_Pressmeet → presmeet, Regio_All → presmeet)
  - [x] 1.4. Update all handler imports referencing the old module and function names
  - [x] 1.5. Add backward-compatible alias imports in `__init__.py` if one exists
    > Requirements: 16

- [x] 2. Shared Layer - Event Constraints Module
  - [x] 2.1. Create `backend/layers/auth-layer/python/shared/event_constraints.py`
  - [x] 2.2. Implement `validate_event_constraints(order_items, event_constraints, all_event_orders)` function
  - [x] 2.3. Support counting_rule `count_items_by_product`: count items matching a product_id across submitted/locked orders
  - [x] 2.4. Support counting_rule `count_distinct_clubs`: count distinct club_ids across submitted/locked orders
  - [x] 2.5. Support counting_rule `sum_field`: sum a numeric field across items in submitted/locked orders
  - [x] 2.6. Return structured validation errors with constraint key, current count, and max
  - [x] 2.7. Write unit tests in `backend/tests/unit/test_event_constraints.py`
    > Requirements: 4.2, 6.3

- [x] 3. Shared Layer - Validation Module
  - [x] 3.1. Create `backend/layers/auth-layer/python/shared/presmeet_validation.py`
  - [x] 3.2. Implement `validate_item_fields(items, products)`: validate required fields, types, options per product's `order_item_fields`
  - [x] 3.3. Implement `validate_purchase_rules(items, products)`: check min_per_club, max_per_club per product
  - [x] 3.4. Implement `validate_submission(order, event, products, all_event_orders)`: orchestrate field + rules + constraints
  - [x] 3.5. Return all errors (not just first) with item index and field references
  - [x] 3.6. Write unit tests in `backend/tests/unit/test_presmeet_validation.py`
    > Requirements: 3, 5, 6

- [x] 4. DynamoDB GSI - Event-Club Index
  - [x] 4.1. Add GSI `event-club-index` (PK: `event_id`, SK: `club_id`) to Orders table definition
  - [x] 4.2. Since DynamoDB tables are managed outside CloudFormation, create a script to add the GSI via AWS CLI/boto3
  - [x] 4.3. Document the GSI in the project README or infrastructure notes
  - [x] 4.4. Verify the GSI is active and queryable > Requirements: 1.6, 3.3
- [x] 5. Backend Handler - presmeet_get_order
  - [x] 5.1. Create `backend/handler/presmeet_get_order/app.py`
  - [x] 5.2. Implement GET /presmeet/orders?event_id=X: query by club_id (from user) + event_id using GSI
  - [x] 5.3. If no order exists and event is `open`, auto-create a draft order (version=1, empty items, delegates.primary=user_email)
  - [x] 5.4. If no order exists and event is not `open`, return error (registration not active)
  - [x] 5.5. If order exists, return it with all fields including version
  - [x] 5.6. Use conditional PutItem to prevent duplicate creation (race condition, Req 1.6)
  - [x] 5.7. Validate user has club_id (reject with 403 if missing)
  - [x] 5.8. Validate user is in order's delegates (primary or secondary) or is admin
  - [x] 5.9. Write unit tests
    > Requirements: 1, 15

- [x] 6. Backend Handler - presmeet_upsert_order
  - [x] 6.1. Create `backend/handler/presmeet_upsert_order/app.py`
  - [x] 6.2. Implement PUT /presmeet/orders/{id}: update items array with optimistic locking (ConditionExpression version=N)
  - [x] 6.3. Increment version on success, update updated_at
  - [x] 6.4. No field validation on draft save (accept incomplete data)
  - [x] 6.5. Reject if order status is `locked` (unless requester is admin, then allow direct edit per Req 9.2)
  - [x] 6.6. If order was `submitted`, revert to `draft` on delegate edit (Req 2.6)
  - [x] 6.7. Record admin edits in status_history (Req 9.2)
  - [x] 6.8. Handle ConditionalCheckFailedException → return 409 with current version
  - [x] 6.9. Recalculate total_amount from items × unit_price
  - [x] 6.10. Write unit tests
    > Requirements: 2, 9.2

- [x] 7. Backend Handler - presmeet_submit_order
  - [x] 7.1. Create `backend/handler/presmeet_submit_order/app.py`
  - [x] 7.2. Implement POST /presmeet/orders/{id}/submit
  - [x] 7.3. Reject if status is `locked` or event is not `open`
  - [x] 7.4. Fetch all products for the event from Producten table
  - [x] 7.5. Fetch all submitted/locked orders for the event via GSI
  - [x] 7.6. Call validation module: field validation + purchase_rules + event constraints
  - [x] 7.7. On success: set status=submitted, record submitted_at
  - [x] 7.8. On failure: return all errors, keep status as draft
  - [x] 7.9. Write unit tests
    > Requirements: 3, 6

- [x] 8. Backend Handler - presmeet_create_payment
  - [x] 8.1. Create `backend/handler/presmeet_create_payment/app.py`
  - [x] 8.2. Implement POST /presmeet/orders/{id}/pay
  - [x] 8.3. Calculate outstanding = total_amount - total_paid
  - [x] 8.4. Create Mollie payment (amount in EUR, 2 decimal string format)
  - [x] 8.5. Support iDEAL (primary) and bank transfer (secondary)
  - [x] 8.6. Store payment record in Payments table (status: pending, provider: mollie)
  - [x] 8.7. Return Mollie checkout_url to frontend
  - [x] 8.8. Handle Mollie API errors → 502 response without creating payment record
  - [x] 8.9. Reject if order not found or no outstanding balance
  - [x] 8.10. Write unit tests (mock Mollie client)
    > Requirements: 7

- [x] 9. Backend Handler - Mollie Webhook Extension
  - [x] 9.1. Extend or create `backend/handler/mollie_webhook/app.py` to handle PresMeet payment callbacks
  - [x] 9.2. On status "paid": update order total_paid, recalculate payment_status
  - [x] 9.3. Set payment_status: "paid" if total_paid >= total_amount, "partial" if 0 < total_paid < total_amount
  - [x] 9.4. Update payment record status in Payments table
  - [x] 9.5. Write unit tests
    > Requirements: 7.3, 7.4

- [x] 10. Backend Handler - presmeet_generate_report
  - [x] 10.1. Create `backend/handler/presmeet_generate_report/app.py`
  - [x] 10.2. Implement GET /presmeet/reports/{type}?event_id=X&status=all&payment_status=all&format=json
  - [x] 10.3. Support 7 report types: attendees, party, tshirts, pickups, dropoffs, financial, overview
  - [x] 10.4. Query Orders table filtered by event_type + event_id (via GSI)
  - [x] 10.5. Apply optional status and payment_status filters
  - [x] 10.6. Include event metadata (name, location, dates) in response
  - [x] 10.7. Financial report: calculate total_charged, total_paid, total_outstanding
  - [x] 10.8. Support JSON and CSV export formats
  - [x] 10.9. Validate report type and event_id (return errors for invalid)
  - [x] 10.10. Write unit tests
    > Requirements: 10

- [x] 11. Backend - Event Management (create/update_event extension)
  - [x] 11.1. Extend existing `create_event` handler to support event_type, constraints array, and product_ids
  - [x] 11.2. Extend existing `update_event` handler with same fields
  - [x] 11.3. Add date validation: registration_open < registration_close <= start_date <= end_date
  - [x] 11.4. Add required field validation: name, event_type, start_date, end_date, registration_open, registration_close
  - [x] 11.5. Add constraint validation: unique keys, max > 0, valid counting_rule
  - [x] 11.6. Implement manual status override transitions (draft→open, open→closed, closed→open)
  - [x] 11.7. Implement event clone (copy event_type, product_ids, constraints, location; clear dates)
  - [x] 11.8. Write unit tests
    > Requirements: 4

- [x] 12. Backend - Event Status Scheduler (auto-open, auto-close + auto-lock)
  - [x] 12.1. Create a scheduled Lambda (EventBridge rule, daily or hourly) that checks event dates
  - [x] 12.2. Transition events from `draft` → `open` when registration_open <= today
  - [x] 12.3. Transition events from `open` → `closed` when registration_close <= today
  - [x] 12.4. On close transition: set all submitted orders for that event to `locked` with status_history entry "auto-locked on registration close"
  - [x] 12.5. Add to SAM template with schedule expression
  - [x] 12.6. Write unit tests
    > Requirements: 4.4, 4.5, 4.6

- [x] 13. Backend - Admin Lock/Unlock Extension
  - [x] 13.1. Extend existing `admin_lock_orders` handler to support single-order lock with status_history (timestamp, admin email, source: "manual")
  - [x] 13.2. Extend existing `admin_unlock_order` handler: set status back to `submitted`, reject if event is closed (return error: "edit directly instead")
  - [x] 13.3. Add concurrency check (ConditionExpression on status) for conflict detection
  - [x] 13.4. Require Webshop_Management + Regio_Pressmeet or Regio_All
  - [x] 13.5. Write unit tests
    > Requirements: 9

- [x] 14. Backend - Delegate Management
  - [x] 14.1. Add secondary delegate management to presmeet_upsert_order or create dedicated endpoint
  - [x] 14.2. Implement add secondary delegate: validate email is existing portal user with Regio_Pressmeet/Regio_All
  - [x] 14.3. Implement remove secondary delegate: primary can remove at any time
  - [x] 14.4. Store delegates object on order record: { primary: email, secondary: email|null }
  - [x] 14.5. Update authorization checks in all PresMeet handlers to check delegates.primary OR delegates.secondary
  - [x] 14.6. Write unit tests
    > Requirements: 12.6-12.10

- [x] 15. Backend - Seed Script (PM2027 Setup)
  - [x] 15.1. Create `backend/scripts/seed_presmeet_2027.py`
  - [x] 15.2. Delete existing presmeet test data (orders, products with channel=presmeet)
  - [x] 15.3. Create 4 product records (meeting, party, tshirt, transfer) with correct schemas
  - [x] 15.4. Create Event_Record for PM2027 with constraints and linked product_ids
  - [x] 15.5. Make script idempotent (safe to run multiple times)
  - [x] 15.6. Add CLI flag --dry-run for preview
    > Requirements: 14

- [x] 16. SAM Template Updates
  - [x] 16.1. Add new Lambda function definitions for: presmeet_get_order, presmeet_upsert_order, presmeet_submit_order, presmeet_create_payment, presmeet_generate_report
  - [x] 16.2. Add API Gateway routes for all new endpoints
  - [x] 16.3. Add EventBridge scheduled rule for event status scheduler
  - [x] 16.4. Add environment variables (ORDERS_TABLE_NAME, EVENTS_TABLE_NAME, PRODUCTEN_TABLE_NAME, PAYMENTS_TABLE_NAME, MOLLIE_API_KEY)
  - [x] 16.5. Remove legacy PresMeet handler definitions (save_presmeet_booking, submit_presmeet_booking, validate_presmeet_cart, create_presmeet_payment, get_presmeet_booking, get_presmeet_config, manual_presmeet_payment)
  - [x] 16.6. Ensure auth layer is attached to all new functions
    > Requirements: 14.4

- [x] 17. Frontend - Types and API Client
  - [x] 17.1. Create `frontend/src/modules/presmeet/types/presmeet.types.ts` with interfaces for Order, Event, Product, Constraint, PaymentRecord, Delegate
  - [x] 17.2. Create `frontend/src/modules/presmeet/services/presmeetApi.ts` with Axios methods for all endpoints (getOrder, saveOrder, submitOrder, pay, getEvent, getReport)
  - [x] 17.3. Handle 409 (version conflict) responses with structured error
  - [x] 17.4. Handle authorization errors (403)
    > Requirements: 11.2, 11.8

- [x] 18. Frontend - Order Transformer and Price Calculator Utils
  - [x] 18.1. Create `frontend/src/modules/presmeet/utils/orderTransformer.ts`
  - [x] 18.2. Implement person-centric form state → order items array transformation
  - [x] 18.3. Implement order items array → person-centric form state (for loading existing orders)
  - [x] 18.4. Create `frontend/src/modules/presmeet/utils/priceCalculator.ts`
  - [x] 18.5. Implement client-side total calculation from items × unit_price
  - [x] 18.6. Write tests for both utils
    > Requirements: 11.5, 11.6, 11.7

- [x] 19. Frontend - Onboarding Flow
  - [x] 19.1. Create `frontend/src/modules/presmeet/components/OnboardingFlow.tsx`
  - [x] 19.2. Load clubs from Club_Registry API
  - [x] 19.3. Show club selection dropdown
  - [x] 19.4. On selection: check if club already has a delegate for the event → block if yes
  - [x] 19.5. On success: update member record with club_id, navigate to booking form
  - [x] 19.6. Skip if user already has club_id
  - [x] 19.7. Handle loading errors with retry
    > Requirements: 12.1-12.5

- [ ] 20. Frontend - Booking Wizard (Core)
  - [~] 20.1. Create `frontend/src/modules/presmeet/components/BookingWizard.tsx`
  - [~] 20.2. Load event data and products on mount
  - [~] 20.3. Call presmeet_get_order to load/create order
  - [~] 20.4. Display event info: name, location, dates, days until close
  - [~] 20.5. If event not open: show ReadOnlyView
  - [~] 20.6. Implement person cards (add/remove delegates and guests based on product max_per_club)
  - [~] 20.7. Implement product configurator per person (dynamically render fields from order_item_fields)
  - [~] 20.8. Show effective limits per product: min(max_per_club, event_remaining)
  - [~] 20.9. Recalculate and display total within 500ms
    > Requirements: 11.1, 11.3, 11.4, 6.4

- [ ] 21. Frontend - Save, Submit, and Error Handling
  - [~] 21.1. Implement save action: transform form → items, PUT to API with version
  - [~] 21.2. Handle 409 conflict: show message with option to reload
  - [~] 21.3. Implement submit action: client-side required field validation → inline errors
  - [~] 21.4. On submit success: update UI state
  - [~] 21.5. On submit failure: display server validation errors per field/item
  - [~] 21.6. Preserve form state on any failure (no data loss)
  - [~] 21.7. Implement debounced auto-save (optional UX enhancement)
    > Requirements: 11.6, 11.8, 11.9

- [ ] 22. Frontend - Payment Panel
  - [~] 22.1. Create `frontend/src/modules/presmeet/components/PaymentPanel.tsx`
  - [~] 22.2. Show outstanding amount (total_amount - total_paid)
  - [~] 22.3. "Pay" button → POST /presmeet/orders/{id}/pay
  - [~] 22.4. Redirect to Mollie checkout_url on success
  - [~] 22.5. Show payment_status badge (unpaid, partial, paid)
  - [~] 22.6. Handle payment errors gracefully
    > Requirements: 7, 11

- [ ] 23. Frontend - Booking Summary PDF
  - [~] 23.1. Create `frontend/src/modules/presmeet/components/BookingSummaryPdf.tsx`
  - [~] 23.2. Use jsPDF + jspdf-autotable to generate PDF
  - [~] 23.3. Include: club name, event name, all persons with products, field values, variants, prices, total, payment status, order status
  - [~] 23.4. Make download button available at all order statuses
    > Requirements: 11.10, 11.11

- [ ] 24. Frontend - Delegate Manager
  - [~] 24.1. Create `frontend/src/modules/presmeet/components/DelegateManager.tsx`
  - [~] 24.2. Show current delegates (primary = current user label, secondary = email or empty)
  - [~] 24.3. Primary can add secondary by email (validate via API)
  - [~] 24.4. Primary can remove secondary
  - [~] 24.5. Non-primary users see read-only delegate info
    > Requirements: 12.6-12.8

- [x] 25. Frontend - Admin Event Dashboard
  - [x] 25.1. Create `frontend/src/modules/presmeet/admin/EventDashboard.tsx`
  - [x] 25.2. Event selector dropdown (load all events with event_type=presmeet)
  - [x] 25.3. Display constraint progress bars (current/max per constraint from API)
  - [x] 25.4. Display payment summary (total charged, paid, outstanding, fully paid clubs count)
  - [x] 25.5. Navigation to report views with status/payment_status filters
  - [x] 25.6. Handle empty event state (zero values)
    > Requirements: 13

- [ ] 26. Frontend - Admin Report Views
  - [ ] 26.1. Create report components for 7 report types within admin module
  - [ ] 26.2. Implement filter controls (order status, payment_status)
  - [ ] 26.3. Display report data in tables
  - [ ] 26.4. Implement CSV download option
  - [ ] 26.5. Link from EventDashboard to each report type
    > Requirements: 10, 13.3

- [x] 27. Channel Rename - DynamoDB Data Migration
  - [x] 27.1. Create `backend/scripts/rename_tenant_to_channel.py`
  - [x] 27.2. Scan Orders, Producten, Carts, StockMovements tables for records with `tenant` field
  - [x] 27.3. For each record: copy `tenant` value to `channel`, remove `tenant` field
  - [x] 27.4. Default missing values to `h-dcn`
  - [x] 27.5. Make script idempotent (skip records already having `channel`)
  - [x] 27.6. Add --dry-run flag for preview
  - [x] 27.7. Run as part of deployment (after code deploy, before traffic)
    > Requirements: 16.1, 16.7, 16.8

- [x] 28. Channel Rename - Handler Updates
  - [x] 28.1. Update all handler files that reference `tenant` as a data field to use `channel`
  - [x] 28.2. Update handlers: create_cart, get_products, admin_get_products, admin_lock_orders, admin_generate_report, shared/stock_helpers.py, shared/variant_helpers.py
  - [x] 28.3. Update API query parameter from `tenant` to `channel` in all affected endpoints
  - [x] 28.4. Update frontend service calls and TypeScript types referencing `tenant` → `channel`
  - [x] 28.5. Verify all tests pass after rename
    > Requirements: 16.2-16.6

- [x] 29. Integration Testing
  - [x] 29.1. Write integration tests for full order lifecycle: create → edit → submit → pay → lock
  - [x] 29.2. Test event constraint validation with multiple clubs
  - [x] 29.3. Test optimistic locking conflict resolution
  - [x] 29.4. Test auto-lock on event close (scheduler)
  - [x] 29.5. Test authorization: delegate access, admin access, cross-club rejection
  - [x] 29.6. Test channel rename compatibility (old records without `channel` field)
    > Requirements: All

## Task Dependency Graph

```json
{
  "waves": [
    {
      "wave": 1,
      "tasks": [1, 2, 4, 17]
    },
    {
      "wave": 2,
      "tasks": [3, 5, 6, 10, 11, 18, 19, 25, 27]
    },
    {
      "wave": 3,
      "tasks": [7, 8, 12, 13, 14, 15, 20, 26, 28]
    },
    {
      "wave": 4,
      "tasks": [9, 16, 21, 22, 23, 24]
    },
    {
      "wave": 5,
      "tasks": [29]
    }
  ],
  "dependencies": {
    "3": [2],
    "5": [1, 4],
    "6": [1, 4],
    "7": [3, 4, 5],
    "8": [5],
    "9": [8],
    "10": [4],
    "11": [1],
    "12": [11],
    "13": [5],
    "14": [5, 6],
    "15": [11],
    "16": [5, 6, 7, 8, 10, 11, 12, 13],
    "18": [17],
    "19": [17],
    "20": [17, 18, 19],
    "21": [20],
    "22": [20],
    "23": [20],
    "24": [20],
    "25": [17],
    "26": [25],
    "27": [1],
    "28": [1, 27],
    "29": [5, 6, 7, 8, 12, 13, 27]
  }
}
```

## Notes

- DynamoDB tables are managed outside CloudFormation — Task 4 must use a boto3 script, not SAM resources
- All backend handlers follow the established auth pattern: extract_user_credentials() → validate_permissions_with_regions()
- Frontend uses React 18 + TypeScript + Chakra UI v2 + Formik + Axios
- The `channel` rename (Tasks 1, 27, 28) must maintain backward compatibility during migration
- Task 16 (SAM Template) is a rollup task that should be done after all handler tasks complete
