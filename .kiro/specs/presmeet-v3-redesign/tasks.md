# Tasks

## Task 1: Shared Layer - Channel Resolver Rename

- [ ] Rename `backend/layers/auth-layer/python/shared/tenant_resolver.py` to `channel_resolver.py`
- [ ] Rename `resolve_tenants` to `resolve_channels` and `validate_tenant_access` to `validate_channel_access`
- [ ] Rename `GROUP_TENANT_MAP` to `GROUP_CHANNEL_MAP` (same mappings: hdcnLeden → h-dcn, Regio_Pressmeet → presmeet, Regio_All → presmeet)
- [ ] Update all handler imports referencing the old module and function names
- [ ] Add backward-compatible alias imports in `__init__.py` if one exists
  > Requirements: 16
  > Dependencies: none

## Task 2: Shared Layer - Event Constraints Module

- [ ] Create `backend/layers/auth-layer/python/shared/event_constraints.py`
- [ ] Implement `validate_event_constraints(order_items, event_constraints, all_event_orders)` function
- [ ] Support counting_rule `count_items_by_product`: count items matching a product_id across submitted/locked orders
- [ ] Support counting_rule `count_distinct_clubs`: count distinct club_ids across submitted/locked orders
- [ ] Support counting_rule `sum_field`: sum a numeric field across items in submitted/locked orders
- [ ] Return structured validation errors with constraint key, current count, and max
- [ ] Write unit tests in `backend/tests/unit/test_event_constraints.py`
  > Requirements: 4.2, 6.3
  > Dependencies: none

## Task 3: Shared Layer - Validation Module

- [ ] Create `backend/layers/auth-layer/python/shared/presmeet_validation.py`
- [ ] Implement `validate_item_fields(items, products)`: validate required fields, types, options per product's `order_item_fields`
- [ ] Implement `validate_purchase_rules(items, products)`: check min_per_club, max_per_club per product
- [ ] Implement `validate_submission(order, event, products, all_event_orders)`: orchestrate field + rules + constraints
- [ ] Return all errors (not just first) with item index and field references
- [ ] Write unit tests in `backend/tests/unit/test_presmeet_validation.py`
  > Requirements: 3, 5, 6
  > Dependencies: Task 2

## Task 4: DynamoDB GSI - Event-Club Index

- [ ] Add GSI `event-club-index` (PK: `event_id`, SK: `club_id`) to Orders table definition
- [ ] Since DynamoDB tables are managed outside CloudFormation, create a script to add the GSI via AWS CLI/boto3
- [ ] Document the GSI in the project README or infrastructure notes
- [ ] Verify the GSI is active and queryable
  > Requirements: 1.6, 3.3
  > Dependencies: none

## Task 5: Backend Handler - presmeet_get_order

- [ ] Create `backend/handler/presmeet_get_order/app.py`
- [ ] Implement GET /presmeet/orders?event_id=X: query by club_id (from user) + event_id using GSI
- [ ] If no order exists and event is `open`, auto-create a draft order (version=1, empty items, delegates.primary=user_email)
- [ ] If no order exists and event is not `open`, return error (registration not active)
- [ ] If order exists, return it with all fields including version
- [ ] Use conditional PutItem to prevent duplicate creation (race condition, Req 1.6)
- [ ] Validate user has club_id (reject with 403 if missing)
- [ ] Validate user is in order's delegates (primary or secondary) or is admin
- [ ] Write unit tests
  > Requirements: 1, 15
  > Dependencies: Task 1, Task 4

## Task 6: Backend Handler - presmeet_upsert_order

- [ ] Create `backend/handler/presmeet_upsert_order/app.py`
- [ ] Implement PUT /presmeet/orders/{id}: update items array with optimistic locking (ConditionExpression version=N)
- [ ] Increment version on success, update updated_at
- [ ] No field validation on draft save (accept incomplete data)
- [ ] Reject if order status is `locked` (unless requester is admin, then allow direct edit per Req 9.2)
- [ ] If order was `submitted`, revert to `draft` on delegate edit (Req 2.6)
- [ ] Record admin edits in status_history (Req 9.2)
- [ ] Handle ConditionalCheckFailedException → return 409 with current version
- [ ] Recalculate total_amount from items × unit_price
- [ ] Write unit tests
  > Requirements: 2, 9.2
  > Dependencies: Task 1, Task 4

## Task 7: Backend Handler - presmeet_submit_order

- [ ] Create `backend/handler/presmeet_submit_order/app.py`
- [ ] Implement POST /presmeet/orders/{id}/submit
- [ ] Reject if status is `locked` or event is not `open`
- [ ] Fetch all products for the event from Producten table
- [ ] Fetch all submitted/locked orders for the event via GSI
- [ ] Call validation module: field validation + purchase_rules + event constraints
- [ ] On success: set status=submitted, record submitted_at
- [ ] On failure: return all errors, keep status as draft
- [ ] Write unit tests
  > Requirements: 3, 6
  > Dependencies: Task 3, Task 4, Task 5

## Task 8: Backend Handler - presmeet_create_payment

- [ ] Create `backend/handler/presmeet_create_payment/app.py`
- [ ] Implement POST /presmeet/orders/{id}/pay
- [ ] Calculate outstanding = total_amount - total_paid
- [ ] Create Mollie payment (amount in EUR, 2 decimal string format)
- [ ] Support iDEAL (primary) and bank transfer (secondary)
- [ ] Store payment record in Payments table (status: pending, provider: mollie)
- [ ] Return Mollie checkout_url to frontend
- [ ] Handle Mollie API errors → 502 response without creating payment record
- [ ] Reject if order not found or no outstanding balance
- [ ] Write unit tests (mock Mollie client)
  > Requirements: 7
  > Dependencies: Task 5

## Task 9: Backend Handler - Mollie Webhook Extension

- [ ] Extend or create `backend/handler/mollie_webhook/app.py` to handle PresMeet payment callbacks
- [ ] On status "paid": update order total_paid, recalculate payment_status
- [ ] Set payment_status: "paid" if total_paid >= total_amount, "partial" if 0 < total_paid < total_amount
- [ ] Update payment record status in Payments table
- [ ] Write unit tests
  > Requirements: 7.3, 7.4
  > Dependencies: Task 8

## Task 10: Backend Handler - presmeet_generate_report

- [ ] Create `backend/handler/presmeet_generate_report/app.py`
- [ ] Implement GET /presmeet/reports/{type}?event_id=X&status=all&payment_status=all&format=json
- [ ] Support 7 report types: attendees, party, tshirts, pickups, dropoffs, financial, overview
- [ ] Query Orders table filtered by event_type + event_id (via GSI)
- [ ] Apply optional status and payment_status filters
- [ ] Include event metadata (name, location, dates) in response
- [ ] Financial report: calculate total_charged, total_paid, total_outstanding
- [ ] Support JSON and CSV export formats
- [ ] Validate report type and event_id (return errors for invalid)
- [ ] Write unit tests
  > Requirements: 10
  > Dependencies: Task 4

## Task 11: Backend - Event Management (create/update_event extension)

- [ ] Extend existing `create_event` handler to support event_type, constraints array, and product_ids
- [ ] Extend existing `update_event` handler with same fields
- [ ] Add date validation: registration_open < registration_close <= start_date <= end_date
- [ ] Add required field validation: name, event_type, start_date, end_date, registration_open, registration_close
- [ ] Add constraint validation: unique keys, max > 0, valid counting_rule
- [ ] Implement manual status override transitions (draft→open, open→closed, closed→open)
- [ ] Implement event clone (copy event_type, product_ids, constraints, location; clear dates)
- [ ] Write unit tests
  > Requirements: 4
  > Dependencies: Task 1

## Task 12: Backend - Event Status Scheduler (auto-open, auto-close + auto-lock)

- [ ] Create a scheduled Lambda (EventBridge rule, daily or hourly) that checks event dates
- [ ] Transition events from `draft` → `open` when registration_open <= today
- [ ] Transition events from `open` → `closed` when registration_close <= today
- [ ] On close transition: set all submitted orders for that event to `locked` with status_history entry "auto-locked on registration close"
- [ ] Add to SAM template with schedule expression
- [ ] Write unit tests
  > Requirements: 4.4, 4.5, 4.6
  > Dependencies: Task 11

## Task 13: Backend - Admin Lock/Unlock Extension

- [ ] Extend existing `admin_lock_orders` handler to support single-order lock with status_history (timestamp, admin email, source: "manual")
- [ ] Extend existing `admin_unlock_order` handler: set status back to `submitted`, reject if event is closed (return error: "edit directly instead")
- [ ] Add concurrency check (ConditionExpression on status) for conflict detection
- [ ] Require Webshop_Management + Regio_Pressmeet or Regio_All
- [ ] Write unit tests
  > Requirements: 9
  > Dependencies: Task 5

## Task 14: Backend - Delegate Management

- [ ] Add secondary delegate management to presmeet_upsert_order or create dedicated endpoint
- [ ] Implement add secondary delegate: validate email is existing portal user with Regio_Pressmeet/Regio_All
- [ ] Implement remove secondary delegate: primary can remove at any time
- [ ] Store delegates object on order record: { primary: email, secondary: email|null }
- [ ] Update authorization checks in all PresMeet handlers to check delegates.primary OR delegates.secondary
- [ ] Write unit tests
  > Requirements: 12.6-12.10
  > Dependencies: Task 5, Task 6

## Task 15: Backend - Seed Script (PM2027 Setup)

- [ ] Create `backend/scripts/seed_presmeet_2027.py`
- [ ] Delete existing presmeet test data (orders, products with channel=presmeet)
- [ ] Create 4 product records (meeting, party, tshirt, transfer) with correct schemas
- [ ] Create Event_Record for PM2027 with constraints and linked product_ids
- [ ] Make script idempotent (safe to run multiple times)
- [ ] Add CLI flag --dry-run for preview
  > Requirements: 14
  > Dependencies: Task 11

## Task 16: SAM Template Updates

- [ ] Add new Lambda function definitions for: presmeet_get_order, presmeet_upsert_order, presmeet_submit_order, presmeet_create_payment, presmeet_generate_report
- [ ] Add API Gateway routes for all new endpoints
- [ ] Add EventBridge scheduled rule for event status scheduler
- [ ] Add environment variables (ORDERS_TABLE_NAME, EVENTS_TABLE_NAME, PRODUCTEN_TABLE_NAME, PAYMENTS_TABLE_NAME, MOLLIE_API_KEY)
- [ ] Remove legacy PresMeet handler definitions (save_presmeet_booking, submit_presmeet_booking, validate_presmeet_cart, create_presmeet_payment, get_presmeet_booking, get_presmeet_config, manual_presmeet_payment)
- [ ] Ensure auth layer is attached to all new functions
  > Requirements: 14.4
  > Dependencies: Task 5, Task 6, Task 7, Task 8, Task 10, Task 11, Task 12, Task 13

## Task 17: Frontend - Types and API Client

- [ ] Create `frontend/src/modules/presmeet/types/presmeet.types.ts` with interfaces for Order, Event, Product, Constraint, PaymentRecord, Delegate
- [ ] Create `frontend/src/modules/presmeet/services/presmeetApi.ts` with Axios methods for all endpoints (getOrder, saveOrder, submitOrder, pay, getEvent, getReport)
- [ ] Handle 409 (version conflict) responses with structured error
- [ ] Handle authorization errors (403)
  > Requirements: 11.2, 11.8
  > Dependencies: none

## Task 18: Frontend - Order Transformer and Price Calculator Utils

- [ ] Create `frontend/src/modules/presmeet/utils/orderTransformer.ts`
- [ ] Implement person-centric form state → order items array transformation
- [ ] Implement order items array → person-centric form state (for loading existing orders)
- [ ] Create `frontend/src/modules/presmeet/utils/priceCalculator.ts`
- [ ] Implement client-side total calculation from items × unit_price
- [ ] Write tests for both utils
  > Requirements: 11.5, 11.6, 11.7
  > Dependencies: Task 17

## Task 19: Frontend - Onboarding Flow

- [ ] Create `frontend/src/modules/presmeet/components/OnboardingFlow.tsx`
- [ ] Load clubs from Club_Registry API
- [ ] Show club selection dropdown
- [ ] On selection: check if club already has a delegate for the event → block if yes
- [ ] On success: update member record with club_id, navigate to booking form
- [ ] Skip if user already has club_id
- [ ] Handle loading errors with retry
  > Requirements: 12.1-12.5
  > Dependencies: Task 17

## Task 20: Frontend - Booking Wizard (Core)

- [ ] Create `frontend/src/modules/presmeet/components/BookingWizard.tsx`
- [ ] Load event data and products on mount
- [ ] Call presmeet_get_order to load/create order
- [ ] Display event info: name, location, dates, days until close
- [ ] If event not open: show ReadOnlyView
- [ ] Implement person cards (add/remove delegates and guests based on product max_per_club)
- [ ] Implement product configurator per person (dynamically render fields from order_item_fields)
- [ ] Show effective limits per product: min(max_per_club, event_remaining)
- [ ] Recalculate and display total within 500ms
  > Requirements: 11.1, 11.3, 11.4, 6.4
  > Dependencies: Task 17, Task 18, Task 19

## Task 21: Frontend - Save, Submit, and Error Handling

- [ ] Implement save action: transform form → items, PUT to API with version
- [ ] Handle 409 conflict: show message with option to reload
- [ ] Implement submit action: client-side required field validation → inline errors
- [ ] On submit success: update UI state
- [ ] On submit failure: display server validation errors per field/item
- [ ] Preserve form state on any failure (no data loss)
- [ ] Implement debounced auto-save (optional UX enhancement)
  > Requirements: 11.6, 11.8, 11.9
  > Dependencies: Task 20

## Task 22: Frontend - Payment Panel

- [ ] Create `frontend/src/modules/presmeet/components/PaymentPanel.tsx`
- [ ] Show outstanding amount (total_amount - total_paid)
- [ ] "Pay" button → POST /presmeet/orders/{id}/pay
- [ ] Redirect to Mollie checkout_url on success
- [ ] Show payment_status badge (unpaid, partial, paid)
- [ ] Handle payment errors gracefully
  > Requirements: 7, 11
  > Dependencies: Task 20

## Task 23: Frontend - Booking Summary PDF

- [ ] Create `frontend/src/modules/presmeet/components/BookingSummaryPdf.tsx`
- [ ] Use jsPDF + jspdf-autotable to generate PDF
- [ ] Include: club name, event name, all persons with products, field values, variants, prices, total, payment status, order status
- [ ] Make download button available at all order statuses
  > Requirements: 11.10, 11.11
  > Dependencies: Task 20

## Task 24: Frontend - Delegate Manager

- [ ] Create `frontend/src/modules/presmeet/components/DelegateManager.tsx`
- [ ] Show current delegates (primary = current user label, secondary = email or empty)
- [ ] Primary can add secondary by email (validate via API)
- [ ] Primary can remove secondary
- [ ] Non-primary users see read-only delegate info
  > Requirements: 12.6-12.8
  > Dependencies: Task 20

## Task 25: Frontend - Admin Event Dashboard

- [ ] Create `frontend/src/modules/presmeet/admin/EventDashboard.tsx`
- [ ] Event selector dropdown (load all events with event_type=presmeet)
- [ ] Display constraint progress bars (current/max per constraint from API)
- [ ] Display payment summary (total charged, paid, outstanding, fully paid clubs count)
- [ ] Navigation to report views with status/payment_status filters
- [ ] Handle empty event state (zero values)
  > Requirements: 13
  > Dependencies: Task 17

## Task 26: Frontend - Admin Report Views

- [ ] Create report components for 7 report types within admin module
- [ ] Implement filter controls (order status, payment_status)
- [ ] Display report data in tables
- [ ] Implement CSV download option
- [ ] Link from EventDashboard to each report type
  > Requirements: 10, 13.3
  > Dependencies: Task 25

## Task 27: Channel Rename - DynamoDB Data Migration

- [ ] Create `backend/scripts/rename_tenant_to_channel.py`
- [ ] Scan Orders, Producten, Carts, StockMovements tables for records with `tenant` field
- [ ] For each record: copy `tenant` value to `channel`, remove `tenant` field
- [ ] Default missing values to `h-dcn`
- [ ] Make script idempotent (skip records already having `channel`)
- [ ] Add --dry-run flag for preview
- [ ] Run as part of deployment (after code deploy, before traffic)
  > Requirements: 16.1, 16.7, 16.8
  > Dependencies: Task 1

## Task 28: Channel Rename - Handler Updates

- [ ] Update all handler files that reference `tenant` as a data field to use `channel`
- [ ] Update handlers: create_cart, get_products, admin_get_products, admin_lock_orders, admin_generate_report, shared/stock_helpers.py, shared/variant_helpers.py
- [ ] Update API query parameter from `tenant` to `channel` in all affected endpoints
- [ ] Update frontend service calls and TypeScript types referencing `tenant` → `channel`
- [ ] Verify all tests pass after rename
  > Requirements: 16.2-16.6
  > Dependencies: Task 1, Task 27

## Task 29: Integration Testing

- [ ] Write integration tests for full order lifecycle: create → edit → submit → pay → lock
- [ ] Test event constraint validation with multiple clubs
- [ ] Test optimistic locking conflict resolution
- [ ] Test auto-lock on event close (scheduler)
- [ ] Test authorization: delegate access, admin access, cross-club rejection
- [ ] Test channel rename compatibility (old records without `channel` field)
  > Requirements: All
  > Dependencies: Task 5, Task 6, Task 7, Task 8, Task 12, Task 13, Task 27
