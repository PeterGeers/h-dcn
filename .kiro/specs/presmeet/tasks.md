# Implementation Plan: PresMeet

## Overview

PresMeet is implemented as a set of 12 Lambda handlers (Python 3.11), a shared validation module in the auth layer, and a React/TypeScript frontend module. The implementation follows the existing project conventions: one Lambda per endpoint, shared auth layer for cross-cutting concerns, DynamoDB for persistence, and S3 for report storage. The frontend uses Chakra UI v2 with a module-based structure under `frontend/src/modules/presmeet/`.

## Tasks

- [x] 1. Shared validation module and Product_Type_Config
  - [x] 1.1 Create `presmeet_validation.py` in the auth layer
    - Create `backend/layers/auth-layer/python/shared/presmeet_validation.py`
    - Implement `validate_product_type(product_type: str) -> tuple[bool, str | None]`
    - Implement `validate_attributes(product_type: str, attributes: dict, config: dict) -> list[dict]` with schema-driven validation (type, enum, required, min_length, max_length, minimum, maximum)
    - Implement `calculate_cart_total(items: list[dict]) -> Decimal` using pricing rules: meeting_ticket ×€50, party_ticket ×€99.50, tshirt ×€25, airport_transfer persons ×€5
    - Implement `calculate_outstanding_balance(order_total: Decimal, payments: list[dict]) -> Decimal` returning max(0, total - sum(payments))
    - Implement `validate_order_submission(order: dict, config: dict, event: dict) -> list[dict]` for full submission validation (schema, min/max counts, date ranges)
    - Implement `extract_club_id(user_roles: list[str]) -> str | None` extracting club*id from Cognito group matching `club*\*`
    - _Requirements: 1.1, 1.3–1.8, 2.1–2.5, 3.2, 4.5, 6.5, 6.6, 8.1–8.5, 10.1–10.6_

  - [x] 1.2 Write property test: Schema validation accepts all valid attributes
    - **Property 1: Schema validation accepts all valid attributes**
    - **Validates: Requirements 1.3, 1.4, 1.5, 1.6, 10.2**

  - [x] 1.3 Write property test: Schema validation rejects invalid attributes
    - **Property 2: Schema validation rejects invalid attributes with field-level errors**
    - **Validates: Requirements 1.7, 10.4, 10.5, 10.6**

  - [x] 1.4 Write property test: Product type validation
    - **Property 3: Product type validation**
    - **Validates: Requirements 1.1, 1.8**

  - [x] 1.5 Write property test: Cart total calculation
    - **Property 4: Cart total calculation**
    - **Validates: Requirements 4.5, 9.1, 9.3**

  - [x] 1.6 Write property test: Outstanding balance calculation
    - **Property 5: Outstanding balance calculation**
    - **Validates: Requirements 6.5, 6.6, 9.4**

  - [x] 1.7 Write property test: Club ID extraction from Cognito groups
    - **Property 11: Club ID extraction from Cognito groups**
    - **Validates: Requirements 3.2**

  - [x] 1.8 Write property test: JSON attribute round-trip preservation
    - **Property 15: JSON attribute round-trip preservation**
    - **Validates: Requirements 10.3**

  - [x] 1.9 Write property test: Draft save allows incomplete attributes
    - **Property 16: Draft save allows incomplete attributes**
    - **Validates: Requirements 8.6, 4.6**

- [x] 2. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. Config and booking retrieval handlers
  - [x] 3.1 Create `get_presmeet_config` Lambda handler
    - Create `backend/handler/get_presmeet_config/app.py`
    - Authenticate Club_User via `extract_user_credentials` and `validate_permissions_with_regions`
    - Query Producten table for all records with `source: "presmeet_config"` (prefix `config_presmeet_*`)
    - Query Events table for the active PresMeet event (`source: "presmeet"`)
    - Return product type configs and event info as JSON
    - _Requirements: 2.1, 2.4, 3.1_

  - [x] 3.2 Create `get_presmeet_booking` Lambda handler
    - Create `backend/handler/get_presmeet_booking/app.py`
    - Authenticate user, extract `club_id` via `extract_club_id`
    - Query Orders table for record with `source: "presmeet"` and matching `club_id`
    - If admin, accept optional `club_id` query parameter to view any club's booking
    - Return 404 if no booking exists, otherwise return full order with items
    - Enforce club-based access control (403 on mismatch)
    - _Requirements: 3.1–3.8, 9.1–9.6_

- [x] 4. Save and validate booking handlers
  - [x] 4.1 Create `save_presmeet_booking` Lambda handler
    - Create `backend/handler/save_presmeet_booking/app.py`
    - Authenticate user, extract `club_id`
    - Accept PUT body with booking form data (delegates, guests, transfers, tshirts)
    - Map form data to typed cart items (meeting_ticket, party_ticket, tshirt, airport_transfer)
    - Validate max_per_club limits per product_type (reject if exceeded)
    - Upsert order record in Orders table with `source: "presmeet"`, `status: "draft"`, `club_id`
    - If order was "submitted", transition back to "draft" on modification
    - Reject if order is "locked" (return 409)
    - Do NOT enforce attribute schema validation on draft save (allow incomplete)
    - Calculate and store `total_amount` using `calculate_cart_total`
    - _Requirements: 4.1–4.9, 5.4, 5.6, 8.6_

  - [x] 4.2 Create `validate_presmeet_cart` Lambda handler
    - Create `backend/handler/validate_presmeet_cart/app.py`
    - Authenticate user, extract `club_id`
    - Accept POST body with cart items array
    - Run `validate_attributes` against each item's product_type schema
    - Return validation result (list of errors or success)
    - _Requirements: 1.7, 8.1, 8.2, 10.2–10.6_

  - [x] 4.3 Write property test: Max-per-club enforcement
    - **Property 6: Max-per-club enforcement**
    - **Validates: Requirements 2.2, 2.3, 4.9**

  - [x] 4.4 Write property test: Booking form to cart item mapping
    - **Property 12: Booking form to cart item mapping**
    - **Validates: Requirements 4.1, 4.2**

  - [x] 4.5 Write property test: Cascade delete on delegate removal
    - **Property 13: Cascade delete on delegate removal**
    - **Validates: Requirements 4.8**

- [x] 5. Submit booking and order lifecycle handlers
  - [x] 5.1 Create `submit_presmeet_booking` Lambda handler
    - Create `backend/handler/submit_presmeet_booking/app.py`
    - Authenticate user, extract `club_id`
    - Load order from Orders table, verify `club_id` match and status is "draft"
    - Run full submission validation via `validate_order_submission` (schema, min/max counts, date ranges)
    - If validation fails, return 400 with error list, keep order in "draft"
    - If validation passes, transition order status to "submitted", set `submitted_at` timestamp
    - _Requirements: 5.1–5.3, 8.1–8.5, 2.5_

  - [x] 5.2 Create `lock_presmeet_orders` Lambda handler
    - Create `backend/handler/lock_presmeet_orders/app.py`
    - Authenticate admin user
    - Accept optional `order_ids` array in POST body
    - If `order_ids` provided, lock those specific orders (must be in "submitted" status)
    - If no `order_ids`, perform "Lock ALL": scan all PresMeet orders, transition all "submitted" to "locked", leave "draft" unchanged
    - Return count of locked orders
    - _Requirements: 5.5, 5.9_

  - [x] 5.3 Create `unlock_presmeet_order` Lambda handler
    - Create `backend/handler/unlock_presmeet_order/app.py`
    - Authenticate admin user
    - Accept `order_id` from path parameter
    - Verify order is in "locked" status, transition to "submitted"
    - _Requirements: 5.7, 5.8_

  - [x] 5.4 Write property test: Order state machine transitions
    - **Property 8: Order state machine transitions**
    - **Validates: Requirements 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8**

  - [x] 5.5 Write property test: Min-per-club enforcement on submission
    - **Property 7: Min-per-club enforcement on submission**
    - **Validates: Requirements 2.5, 8.3**

  - [x] 5.6 Write property test: Lock ALL batch operation
    - **Property 9: Lock ALL batch operation**
    - **Validates: Requirements 5.9**

  - [x] 5.7 Write property test: Airport transfer date validation
    - **Property 14: Airport transfer date validation**
    - **Validates: Requirements 8.4**

- [x] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Payment handlers
  - [x] 7.1 Create `create_presmeet_payment` Lambda handler
    - Create `backend/handler/create_presmeet_payment/app.py`
    - Authenticate Club_User, extract `club_id`
    - Load order, verify `club_id` match
    - Reject if order status is "draft" (return 400: "Order must be submitted before payment")
    - Calculate outstanding balance via `calculate_outstanding_balance`
    - Create Mollie payment session for the outstanding amount using Mollie API
    - Store payment record in Payments table with `source: "presmeet"`, `provider: "mollie"`, `status: "pending"`
    - Return Mollie checkout URL to frontend
    - _Requirements: 6.1, 6.5, 6.7_

  - [x] 7.2 Create `mollie_webhook` Lambda handler
    - Create `backend/handler/mollie_webhook/app.py`
    - No Cognito auth (Mollie signature verification instead)
    - Receive Mollie payment ID, fetch payment status from Mollie API
    - Update payment record status in Payments table
    - If status is "paid": update order `payment_status` (calculate if "paid" or "partial" based on outstanding balance)
    - If status is "failed"/"cancelled"/"expired": update payment record only, leave order payment_status unchanged
    - Idempotent: re-processing same payment ID is safe
    - Always return 200 to Mollie
    - _Requirements: 6.2, 6.3, 6.5, 6.6_

  - [x] 7.3 Create `manual_presmeet_payment` Lambda handler
    - Create `backend/handler/manual_presmeet_payment/app.py`
    - Authenticate admin user
    - Accept POST body with `order_id`, `amount` (€0.01–€999,999.99), `date`, `description` (max 255 chars)
    - Create payment record in Payments table with `provider: "manual"`
    - Recalculate order `payment_status` based on new outstanding balance
    - _Requirements: 6.4, 6.5, 6.6_

  - [x] 7.4 Write property test: Payment guard on draft orders
    - **Property 20: Payment guard on draft orders**
    - **Validates: Requirements 6.7**

  - [x] 7.5 Write property test: Payment status webhook handling
    - **Property 19: Payment status webhook handling**
    - **Validates: Requirements 6.2, 6.3**

  - [x] 7.6 Write property test: Club-based access control
    - **Property 10: Club-based access control**
    - **Validates: Requirements 3.4, 3.6, 3.8**

- [x] 8. Admin reporting handlers
  - [x] 8.1 Create `generate_presmeet_report` Lambda handler
    - Create `backend/handler/generate_presmeet_report/app.py`
    - Authenticate admin user
    - Scan Orders table for all records with `source: "presmeet"`
    - Scan Payments table for all records with `source: "presmeet"`
    - Compute aggregates: counts per product_type per status, payment totals (charged, paid, outstanding)
    - Build order list with payment summaries per order
    - Generate CSV exports (submitted-only and all orders) with columns: club name, order status, product_type, quantity, unit price, attribute values
    - Write `overview.json`, `orders.json`, `export_submitted.csv`, `export_all.csv`, `metadata.json` to S3 bucket `h-dcn-reports/presmeet/`
    - Return success with generation timestamp and metadata
    - _Requirements: 7.1, 7.4, 7.5, 7.6_

  - [x] 8.2 Create `get_presmeet_report` Lambda handler
    - Create `backend/handler/get_presmeet_report/app.py`
    - Authenticate admin user
    - Accept query parameter `?type=overview|orders|export_submitted|export_all|metadata`
    - Read requested file from S3 bucket
    - Return JSON or CSV content with appropriate Content-Type header
    - Return 404 if no report has been generated yet
    - _Requirements: 7.1–7.6_

  - [x] 8.3 Write property test: CSV export completeness
    - **Property 17: CSV export completeness**
    - **Validates: Requirements 7.4, 7.5**

  - [x] 8.4 Write property test: Admin aggregation correctness
    - **Property 18: Admin aggregation correctness**
    - **Validates: Requirements 7.1, 7.6**

- [x] 9. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. SAM template and infrastructure wiring
  - [x] 10.1 Add all PresMeet Lambda functions to `backend/template.yaml`
    - Define 12 Lambda function resources following existing handler pattern
    - Configure API Gateway REST endpoints with correct methods and paths
    - Set environment variables: table names, S3 bucket, Mollie API key, Cognito pool ID
    - Attach auth layer to all handlers
    - Configure IAM policies: DynamoDB read/write for Orders/Carts/Payments/Producten/Events, S3 read/write for report bucket
    - Configure `mollie_webhook` without Cognito authorizer (public endpoint)
    - _Requirements: 3.1, 3.8, 7.7_

  - [x] 10.2 Seed Product_Type_Config records in Producten table
    - Create a seed script `backend/scripts/seed_presmeet_config.py`
    - Insert 4 config records with `product_id` prefix `config_presmeet_*` and `source: "presmeet_config"`
    - meeting_ticket: max_per_club=3, min_per_club=1, unit_price=50.00, required_attributes schema
    - party_ticket: max_per_club=13, min_per_club=0, unit_price=99.50, required_attributes schema
    - tshirt: max_per_club=13, min_per_club=0, unit_price=25.00, required_attributes schema
    - airport_transfer: max_per_club=20, min_per_club=0, unit_price=5.00, required_attributes schema
    - _Requirements: 2.1, 2.4, 10.1_

- [x] 11. Frontend module implementation
  - [x] 11.1 Create TypeScript types and API service
    - Create `frontend/src/modules/presmeet/types/presmeet.ts` with all type definitions (ProductType, OrderStatus, CartItem, PresMeetBooking, PresMeetConfig, etc.)
    - Create `frontend/src/modules/presmeet/services/presmeetApi.ts` with API service methods for all endpoints
    - _Requirements: 3.1, 4.1–4.9, 9.1–9.6_

  - [x] 11.2 Create booking form components
    - Create `frontend/src/modules/presmeet/components/DelegateSection.tsx` — delegate input (name, role, party attendance toggle, tshirt options)
    - Create `frontend/src/modules/presmeet/components/GuestSection.tsx` — guest input (name, tshirt options)
    - Create `frontend/src/modules/presmeet/components/TransferSection.tsx` — airport transfer input (direction, airport, flight, date, time, persons)
    - Create `frontend/src/modules/presmeet/components/BookingForm.tsx` — multi-step form composing delegate/guest/transfer sections, save draft, submit
    - Implement client-side validation in `frontend/src/modules/presmeet/utils/validation.ts`
    - Display inline validation errors next to form fields
    - Enforce max_per_club limits in UI (disable add buttons when limit reached)
    - _Requirements: 4.1–4.9, 8.1, 8.2, 8.6_

  - [x] 11.3 Create booking overview and payment components
    - Create `frontend/src/modules/presmeet/components/BookingOverview.tsx` — summary grouped by product_type with item counts, unit prices, line totals, grand total
    - Create `frontend/src/modules/presmeet/components/PaymentSection.tsx` — payment status display, initiate Mollie payment button, payment history
    - Display current order status label (draft/submitted/locked)
    - Show remaining balance and total paid
    - Handle empty booking state (zero total, "no items" message)
    - _Requirements: 9.1–9.6, 6.1, 6.7_

  - [x] 11.4 Create admin dashboard component
    - Create `frontend/src/modules/presmeet/components/AdminDashboard.tsx`
    - Display aggregated stats from report data (counts per product_type per status)
    - Display order list sorted by club name with status, dates, payment info
    - Implement "Refresh Data" button triggering report generation
    - Implement lock/unlock controls per order and "Lock ALL" button
    - Implement manual payment recording form (amount, date, description)
    - Implement CSV export download buttons (submitted-only and all)
    - Display aggregate payment statistics (total charged, paid, outstanding)
    - Return 403 for non-admin users
    - _Requirements: 7.1–7.7_

  - [x] 11.5 Create main page and hook, wire routing
    - Create `frontend/src/modules/presmeet/hooks/usePresMeetBooking.ts` — state management hook (load config, load booking, save, submit, payment flow)
    - Create `frontend/src/modules/presmeet/PresMeetPage.tsx` — main page with tab navigation (Booking Form, Overview, Admin)
    - Add route for PresMeet module in app router
    - Conditionally show Admin tab based on user role
    - _Requirements: 3.1, 3.4, 3.8, 7.7_

  - [x] 11.6 Write frontend tests
    - Create `frontend/src/modules/presmeet/__tests__/BookingForm.test.tsx` — renders sections, validates inputs
    - Create `frontend/src/modules/presmeet/__tests__/BookingOverview.test.tsx` — displays totals, grouped items
    - Create `frontend/src/modules/presmeet/__tests__/AdminDashboard.test.tsx` — renders report data, lock/unlock actions
    - Create `frontend/src/modules/presmeet/__tests__/validation.test.ts` — client-side validation logic
    - _Requirements: 4.1–4.5, 7.1, 9.1–9.4_

- [x] 12. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The shared validation module (task 1.1) is the foundation — most handlers depend on it
- SAM template wiring (task 10.1) must be done before handlers can be deployed/tested end-to-end
- Frontend tasks (11.x) can proceed in parallel with backend once API contracts are defined
- DynamoDB tables already exist — no table creation needed, only config seeding

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    {
      "id": 1,
      "tasks": ["1.2", "1.3", "1.4", "1.5", "1.6", "1.7", "1.8", "1.9"]
    },
    { "id": 2, "tasks": ["3.1", "3.2", "11.1"] },
    { "id": 3, "tasks": ["4.1", "4.2", "10.1", "10.2"] },
    { "id": 4, "tasks": ["4.3", "4.4", "4.5", "5.1"] },
    { "id": 5, "tasks": ["5.2", "5.3", "5.4", "5.5", "5.6", "5.7"] },
    { "id": 6, "tasks": ["7.1", "7.2", "7.3"] },
    { "id": 7, "tasks": ["7.4", "7.5", "7.6", "8.1"] },
    { "id": 8, "tasks": ["8.2", "8.3", "8.4"] },
    { "id": 9, "tasks": ["11.2", "11.3", "11.4"] },
    { "id": 10, "tasks": ["11.5", "11.6"] }
  ]
}
```
