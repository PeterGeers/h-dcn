# Requirements Document

## Introduction

This document specifies the requirements for the PresMeet v3 Redesign — a complete architectural overhaul of the Presidents' Meeting (PresMeet) booking system for the H-DCN portal. The redesign eliminates the dedicated PresMeet pipeline in favour of an order-only flow (no cart), event-linked architecture, unified product modeling, and Mollie payment integration. The goal is to reduce complexity, eliminate 6+ dedicated Lambda handlers, and leverage the existing webshop infrastructure while preserving the person-centric booking wizard UX.

## Glossary

- **Booking_System**: The PresMeet order management system that handles the full lifecycle from draft creation through submission, payment, and locking
- **Order_Service**: The backend service responsible for creating, updating, validating, and managing PresMeet orders in the Orders DynamoDB table
- **Event_Service**: The backend service responsible for managing PresMeet event records (create, open, close, archive) in the Events DynamoDB table
- **Payment_Service**: The backend service responsible for Mollie payment initiation, webhook processing, and manual payment recording
- **Report_Service**: The backend service responsible for generating reports by querying the Orders table filtered by event_type and event_id
- **Validation_Module**: The PresMeet-specific module that enforces cross-item validation rules at order submission time
- **Booking_Form**: The frontend person-centric wizard component that allows clubs to manage delegates, guests, and associated products
- **Onboarding_Flow**: The frontend flow that handles first-time club selection for PresMeet users
- **Admin_Dashboard**: The frontend admin interface for event management, reporting, and order administration
- **Club_Delegate**: A member authorized to manage their club's PresMeet booking (typically the club president)
- **Event_Record**: A record in the Events DynamoDB table representing a specific event edition (e.g., PresMeet 2027, Rally 2027) with an event_type field for categorization
- **UnifiedProduct**: The existing product schema in the Producten table with `order_item_fields` and `purchase_rules`
- **Optimistic_Locking**: Concurrency control via a `version` field — updates fail if the version has changed since last read
- **Mollie**: The payment service provider used for PresMeet payments (iDEAL, bank transfer)
- **Club_Registry**: The source of club data used for the onboarding flow club selection

## Requirements

### Requirement 1: Order Creation

**User Story:** As a Club_Delegate, I want to create a PresMeet order for my club when I first visit the booking page, so that I have a persistent working document to manage my club's registration.

#### Acceptance Criteria

1. WHEN a Club_Delegate accesses the Booking_Form for an open event and no order exists for the club and event combination, THE Order_Service SHALL create a new order with status `draft`, payment_status `unpaid`, total_amount `0.00`, an empty items array, the club_id, event_type `presmeet`, the event_id, and version `1`
2. WHEN a Club_Delegate accesses the Booking_Form and an existing order for the club and event combination already exists, THE Order_Service SHALL return the existing order including its current status, items, and version without creating a duplicate
3. WHEN the Order_Service creates an order, THE Order_Service SHALL assign a unique order_id formatted as a UUID and record a created_at timestamp
4. IF a Club_Delegate attempts to create an order for an event that is not in `open` status, THEN THE Order_Service SHALL reject the request with an error indicating registration is not active
5. IF the Club_Delegate's account has no associated club_id, THEN THE Order_Service SHALL reject the request with an error indicating that club assignment is required before booking
6. IF two Club_Delegates from the same club access the Booking_Form simultaneously and no order exists, THEN THE Order_Service SHALL ensure only one order is created for the club and event combination and return that order to both delegates

### Requirement 2: Order Updates (Draft Editing)

**User Story:** As a Club_Delegate, I want to save my booking progress at any point without validation, so that I can work on it over multiple sessions across days or weeks.

#### Acceptance Criteria

1. WHEN a Club_Delegate saves changes to a draft or submitted order, THE Order_Service SHALL update the order items in-place using Optimistic_Locking and return the new version number in the response
2. IF the version in the update request does not match the current version in the database, THEN THE Order_Service SHALL reject the update with a conflict error indicating the current version
3. WHEN the Order_Service successfully updates an order, THE Order_Service SHALL increment the version field by 1 and update the updated_at timestamp
4. THE Order_Service SHALL accept item data with missing or empty field values during draft saves without enforcing required-field validation, type constraints, or purchase_rules
5. IF a Club_Delegate attempts to update an order with status `locked`, THEN THE Order_Service SHALL reject the update with an error indicating the order is locked
6. WHEN a submitted order is edited by the Club_Delegate, THE Order_Service SHALL revert the status to `draft`
7. IF a Club_Delegate attempts to update an order that does not exist, THEN THE Order_Service SHALL reject the request with an error indicating the order was not found

### Requirement 3: Order Submission

**User Story:** As a Club_Delegate, I want to submit my completed booking, so that the organizers know my club's registration is final and ready for processing.

#### Acceptance Criteria

1. WHEN a Club_Delegate submits an order, THE Validation_Module SHALL validate all items against their product field definitions (required fields, type constraints, value ranges) as defined in each product's `order_item_fields` schema
2. WHEN a Club_Delegate submits an order, THE Validation_Module SHALL enforce purchase_rules for each product (min_per_club, max_per_club) by comparing the item count per product in the order against the product's configured limits
3. WHEN a Club_Delegate submits an order, THE Validation_Module SHALL validate event-level constraints by iterating over the event's constraints array, applying each constraint's counting_rule to sum relevant items from all submitted and locked orders for the same event, and rejecting the submission if adding the club's items would exceed any constraint's max
4. IF the order status is `locked` or the linked event status is not `open`, THEN THE Order_Service SHALL reject the submission with an error message indicating the order is not editable
5. WHEN all validations pass, THE Order_Service SHALL set the order status to `submitted` and record a `submitted_at` timestamp
6. IF any validation fails, THEN THE Order_Service SHALL return all validation errors with references to the specific item index and field name that caused each failure, preserve the order status as `draft`, and reject the submission

### Requirement 4: Event Management

**User Story:** As an admin, I want to create and manage events with registration periods and configurable constraints, so that any event type (PresMeet, rally, members day) can be properly configured and enforced without code changes.

#### Acceptance Criteria

1. THE Event_Service SHALL support creating Event_Records with name (maximum 200 characters), location (maximum 300 characters), event_type (e.g., `presmeet`, `rally`, `ledendag`), start_date, end_date, registration_open, registration_close, payment_deadline, a configurable constraints array, and linked product_ids
2. THE Event_Service SHALL store each constraint as an object with key (unique identifier, e.g., `max_meeting_attendees`), label (human-readable display name), max (numeric cap), and counting_rule (how to count items toward this cap: `count_items_by_product`, `count_distinct_clubs`, or `sum_field`)
3. THE Event_Service SHALL support four event statuses: `draft`, `open`, `closed`, and `archived`
4. WHEN the current date reaches registration_open, THE Event_Service SHALL transition the event status from `draft` to `open`
5. WHEN the current date reaches registration_close, THE Event_Service SHALL transition the event status from `open` to `closed`
6. WHEN an event transitions to `closed`, THE Order_Service SHALL automatically set the status to `locked` for all orders with status `submitted` linked to that event, record the transition in each order's status_history as "auto-locked on registration close", and reject any subsequent update attempts by Club_Delegates with an error indicating registration is closed
7. WHEN an admin triggers a manual status override, THE Event_Service SHALL allow transitions from `draft` to `open`, from `open` to `closed`, and from `closed` to `open`, independent of scheduled dates
8. WHEN an admin clones a previous event, THE Event_Service SHALL create a new Event_Record in `draft` status, copying event_type, product_ids, constraints, and location from the source event, while leaving date fields empty for admin configuration
9. IF an admin attempts to create or update an Event_Record where registration_open is not before registration_close, or registration_close is not before or equal to start_date, or start_date is not before or equal to end_date, THEN THE Event_Service SHALL reject the request with an error indicating the invalid date ordering
10. IF an admin attempts to create an Event_Record without providing name, event_type, start_date, end_date, registration_open, or registration_close, THEN THE Event_Service SHALL reject the request with an error indicating the missing required fields
11. THE Event_Service SHALL validate that each constraint in the constraints array has a unique key within the event, a max value greater than zero, and a valid counting_rule

### Requirement 5: Product Modeling

**User Story:** As an admin, I want event products defined using the existing UnifiedProduct schema with configurable fields and limits, so that the system uses consistent product infrastructure and limits can be adjusted per event without code changes.

#### Acceptance Criteria

1. THE Booking_System SHALL model each event product as a UnifiedProduct with: event_type (e.g., `presmeet`), order_item_fields (array of field definitions each with name, type, required flag, and optional options/min/max), an optional variant_schema (array of axes each with name and values), and purchase_rules (with optional min_per_club, max_per_club, and order_mode)
2. THE Booking_System SHALL support the following field types in order_item_fields: `text`, `select` (with configurable options array), `number` (with optional minimum and maximum), and `date`
3. THE Booking_System SHALL enforce purchase_rules at submission time by comparing the item count per product in the order against the product's configured min_per_club and max_per_club values
4. IF a product has a variant_schema, THEN THE Booking_System SHALL require a valid variant_id when adding that product to an order; IF a product has no variant_schema, THEN THE Booking_System SHALL NOT require a variant_id
5. THE Booking_System SHALL store all event product records in the existing Producten DynamoDB table, using the same product_id key and record structure as standard webshop products
6. THE Booking_System SHALL support order_mode `persistent` in purchase_rules, meaning items persist across saves and are not cleared on each session

### Requirement 6: Capacity Validation

**User Story:** As an organizer, I want the system to enforce both per-club product limits and event-wide capacity limits at submission time, so that overbooking is prevented automatically.

#### Acceptance Criteria

1. WHEN a Club_Delegate submits an order, THE Validation_Module SHALL check each product's `max_per_club` from its purchase_rules and reject the submission if the club's item count for any product exceeds that limit
2. WHEN a Club_Delegate submits an order, THE Validation_Module SHALL check each product's `min_per_club` from its purchase_rules (if defined) and reject the submission if the club's item count for that product is below the minimum
3. WHEN a Club_Delegate submits an order, THE Validation_Module SHALL calculate the remaining event capacity for each product by summing item counts from all submitted and locked orders for the same event, and reject the submission if adding the club's items would exceed the event constraint's max value
4. WHEN event capacity is partially consumed, THE Booking_Form SHALL display the effective available quantity per product as `min(product.max_per_club, event_remaining)` so the delegate sees realistic limits before submitting
5. IF any capacity validation fails, THEN THE Validation_Module SHALL return all validation errors identifying the product, the limit type (per-club or event-wide), the current count, and the maximum allowed, and preserve the order in its current draft state
6. THE Validation_Module SHALL enforce capacity validation only at submission time, not during draft saves

### Requirement 7: Payment Integration

**User Story:** As a Club_Delegate, I want to pay for my club's booking via iDEAL or bank transfer, so that we can settle our registration costs conveniently.

#### Acceptance Criteria

1. WHEN a Club_Delegate initiates payment, THE Payment_Service SHALL create a Mollie payment for the outstanding amount (total_amount minus total_paid) formatted as a string with 2 decimal places in EUR currency
2. THE Payment_Service SHALL support iDEAL as the primary payment method and bank transfer as the secondary method
3. WHEN a Mollie payment succeeds (webhook receives status "paid"), THE Payment_Service SHALL update the order's total_paid and set payment_status to "paid" if total_paid >= total_amount, "partial" if 0 < total_paid < total_amount
4. THE Payment_Service SHALL track payment_status as `unpaid` (no payments), `partial` (some paid, balance remaining), or `paid` (total_paid >= total_amount)
5. THE Payment_Service SHALL allow payment at any order status (draft or submitted) except when the order does not exist or has no outstanding balance
6. WHEN order items change after a payment has been recorded, THE Order_Service SHALL recalculate the outstanding amount based on the new total_amount minus total_paid
7. WHEN the Payment_Service creates a Mollie payment, THE Payment_Service SHALL store a payment record in the Payments table with payment_id, order_id, club_id, amount, status "pending", provider "mollie", mollie_payment_id, and created_at timestamp
8. IF the Mollie API is unreachable or returns an error, THEN THE Payment_Service SHALL return a 502 error indicating a payment provider error without creating a payment record

### Requirement 8: Admin Payment Management

**User Story:** As an admin, I want to record manual payments against any order (webshop, PresMeet, contribution) and view payment status, so that I can track payment settlement regardless of order channel.

#### Acceptance Criteria

1. WHEN an admin records a manual payment, THE Payment_Service SHALL accept any valid order_id regardless of the order's channel (h-dcn, presmeet, or future channels), recalculate total_paid as the sum of all recorded payments for that order, and set payment_status to "paid" if total_paid >= total_amount, "partial" if 0 < total_paid < total_amount, or "unpaid" if total_paid = 0
2. THE Payment_Service SHALL store each manual payment with an amount (between 0.01 and 999,999.99), a date in ISO 8601 format, method (bank_transfer), and an admin reference note of at most 255 characters
3. IF a payment would cause total_paid to exceed total_amount (overpayment), THEN THE Payment_Service SHALL accept the payment, set payment_status to "paid", and set an overpayment flag on the order indicating the surplus amount for manual refund review
4. IF the specified order does not exist, THEN THE Payment_Service SHALL reject the payment request with an error indicating the order was not found
5. WHEN a payment transitions an order to payment_status "paid" and the order contains items with variant_ids, THE Payment_Service SHALL trigger stock reservation for those items regardless of order channel
6. THE Payment_Service SHALL use the existing `admin_record_payment` Lambda handler for all manual payment recording, extending it if needed rather than creating a separate PresMeet-specific payment handler

### Requirement 9: Order Locking

**User Story:** As an admin, I want to manually lock orders before registration closes, and edit or update locked orders on behalf of end-users after close, so that I have full control over registration finalization while accommodating late corrections.

#### Acceptance Criteria

1. WHEN an admin manually locks an order, THE Order_Service SHALL set the order status to `locked`, record the transition in the order's status_history (including timestamp, triggering admin email, and source "manual"), and reject any subsequent update attempts by the Club_Delegate with an error response indicating the order is locked
2. THE Order_Service SHALL allow admin users to update locked orders directly (editing items, correcting fields) without changing the order status, recording the admin edit in the order's status_history with timestamp and admin email
3. WHEN an admin unlocks an order, THE Order_Service SHALL set the status back to `submitted`, record the transition in the order's status_history, and allow the Club_Delegate to make further edits only if the linked event is still in `open` status
4. IF an admin unlocks an order for an event that is in `closed` status, THEN THE Order_Service SHALL reject the unlock with an error indicating the event is closed and the admin should edit the order directly instead
5. IF a concurrent modification changes the order status between read and update during a lock or unlock operation, THEN THE Order_Service SHALL reject the operation with an error response indicating a concurrent modification conflict
6. THE Order_Service SHALL only allow users with admin permissions (Webshop_Management + Regio_Pressmeet or Regio_All) to lock, unlock, or directly edit locked orders

### Requirement 10: Reporting

**User Story:** As an admin, I want to generate reports for PresMeet events showing attendees, party guests, t-shirt orders, transfers, and financial status, so that I can coordinate logistics and track payments.

#### Acceptance Criteria

1. THE Report_Service SHALL support seven report types: attendees, party, tshirts, pickups, dropoffs, financial, and overview
2. THE Report_Service SHALL generate reports by querying the Orders table filtered by event_type and a required event_id parameter
3. THE Report_Service SHALL support filtering by order status (draft, submitted, locked, or all) with a default of `all` when no status filter is specified
4. THE Report_Service SHALL support filtering by payment_status (unpaid, partial, paid, or all) with a default of `all` when no payment_status filter is specified
5. THE Report_Service SHALL support JSON and CSV export formats for all report types, defaulting to JSON when no format is specified
6. THE Report_Service SHALL include event context (event name, location, dates) in report metadata
7. WHEN generating the financial report, THE Report_Service SHALL calculate totals for total_charged, total_paid, and total_outstanding across all orders matching the applied status and payment_status filters for the event
8. IF the request specifies an invalid report type, a missing event_id, or a non-existent event_id, THEN THE Report_Service SHALL return an error response indicating the specific validation failure without generating a report

### Requirement 11: Booking Form (Frontend)

**User Story:** As a Club_Delegate, I want a person-centric booking wizard that lets me add delegates and guests with their associated products, so that managing complex multi-person registrations is intuitive.

#### Acceptance Criteria

1. THE Booking_Form SHALL present a person-centric wizard where the Club_Delegate adds persons, with the maximum number of persons per category (delegates, guests) derived from the linked products' `max_per_club` values in their purchase_rules, then configures the available products per person as defined by the event's linked product_ids
2. THE Booking_Form SHALL target the Order_Service API directly (POST /orders/{event_type} for creation, PUT /orders/{id} for updates, POST /orders/{id}/submit for submission)
3. THE Booking_Form SHALL display the event name, location, dates, and days until registration close
4. WHEN the event is not in `open` status, THE Booking_Form SHALL display a read-only view of the existing order with a message indicating registration is closed or not yet open
5. THE Booking_Form SHALL recalculate and display the total order amount within 500ms as items are added or removed
6. WHEN save is triggered, THE Booking_Form SHALL transform the person-centric form state into order items with product_id, variant_id (where applicable), and item_fields_data, then send to the Order_Service
7. WHEN the Booking_Form loads and an existing order for the club and event exists, THE Booking_Form SHALL retrieve the order from the Order_Service and populate the wizard with the previously saved persons and their configured products
8. IF a save or submit request to the Order_Service fails, THEN THE Booking_Form SHALL display an error message indicating the failure reason and preserve the current form state so that no user input is lost
9. WHEN submit is triggered, THE Booking_Form SHALL validate that all fields marked as `required` in each product's `order_item_fields` definition are populated, and display inline validation errors for any missing fields before sending to the Order_Service
10. THE Booking_Form SHALL provide a "Download Booking Summary" action that generates a PDF containing the club name, event name, all booked persons with their configured products and field values, variant selections, per-item prices, total amount, payment status, and order status at the time of download
11. THE Booking_Form SHALL make the download action available at any order status (draft, submitted, locked) so the Club_Delegate can always produce a current snapshot of their booking

### Requirement 12: Onboarding Flow

**User Story:** As a first-time PresMeet user, I want to select my club before accessing the booking form, so that the system knows which club I represent.

#### Acceptance Criteria

1. WHEN a user accesses the booking system and has no club_id associated with their member record, THE Onboarding_Flow SHALL present a club selection interface displaying all clubs from the Club_Registry
2. WHEN a user selects a club and the club has no assigned delegate for the current event, THE Onboarding_Flow SHALL designate the user as the primary delegate, update the member record with the selected club_id, and navigate the user to the Booking_Form
3. WHEN a user already has a club_id on their member record, THE Onboarding_Flow SHALL skip the selection step and proceed directly to the Booking_Form
4. IF a user attempts to select a club that already has a primary delegate registered for the current event, THEN THE Onboarding_Flow SHALL block the selection and display an error message indicating the club is already assigned to another delegate
5. IF the Club_Registry fails to load, THEN THE Onboarding_Flow SHALL display an error message indicating the club list is unavailable and provide a retry option
6. THE Booking_Form SHALL allow the primary delegate to add a secondary delegate by entering their email address, provided the email belongs to an existing portal user with Regio_Pressmeet or Regio_All access
7. THE secondary delegate SHALL have equal editing rights to the primary delegate (save, submit, pay), with concurrent edits handled by Optimistic_Locking (version conflict on simultaneous saves)
8. THE primary delegate SHALL be able to remove the secondary delegate at any time, immediately revoking their access to the club's booking
9. THE Order_Service SHALL store a maximum of 2 authorized delegates per club per event (one primary, one optional secondary) on the order record
10. IF a conflict arises about delegate authorization (e.g., disputed primary status), THEN THE Order_Service SHALL require admin intervention to reassign or remove delegates — neither delegate can override the other's primary/secondary status

### Requirement 13: Admin Event Dashboard

**User Story:** As an admin, I want an event dashboard showing registration progress, constraint utilization, and payment status at a glance, so that I can monitor the event preparation status.

#### Acceptance Criteria

1. THE Admin_Dashboard SHALL display registration progress by iterating the selected event's constraints array and showing each constraint as a current/maximum pair (using the constraint's label for display and its counting_rule to compute the current value)
2. THE Admin_Dashboard SHALL display a payment summary showing: total charged amount, total paid amount, total outstanding amount (each formatted as currency with 2 decimal places), and the count of fully paid clubs versus total registered clubs
3. THE Admin_Dashboard SHALL provide navigation to all seven report types (attendees, party, t-shirts, pickups, dropoffs, financial, overview) with filtering controls for order status (draft, submitted, locked) and payment status (unpaid, partial, paid)
4. WHEN an admin selects a different event from the event selector, THE Admin_Dashboard SHALL update all displayed registration progress, payment summary, and report access to reflect the selected event within 3 seconds
5. IF the selected event has no orders, THEN THE Admin_Dashboard SHALL display zero values for all registration progress counts and payment summary amounts

### Requirement 14: Migration

**User Story:** As a developer, I want a clean deployment of the new PresMeet system that replaces the existing test implementation, so that we start fresh with the redesigned architecture.

#### Acceptance Criteria

1. WHEN deploying the new system, THE Booking_System SHALL delete all existing PresMeet test records from the Orders table (records with event_type/tenant `presmeet`) and any legacy PresMeet-specific records from the Producten table
2. THE Booking_System SHALL create UnifiedProduct records for the four PresMeet 2027 product types with the following initial configuration: (a) meeting tickets — order_item_fields: name (text, required), role (text, required), attend_party (select, required, options: yes/no); purchase_rules: min_per_club 1, max_per_club 3, order_mode persistent; (b) party tickets — order_item_fields: name (text, required), person_type (select, required, options: delegate/guest); purchase_rules: max_per_club 13, order_mode persistent; (c) t-shirts — variant_schema: Size (S, M, L, XL, XXL, 3XL, 4XL) × Gender (Male, Female); order_item_fields: person name (text, required); purchase_rules: max_per_club 13, order_mode persistent; (d) airport transfers — variant_schema: Direction (Pickup, Dropoff) × Airport (AMS, RTM, EIN); order_item_fields: flight number (text, required), date (date, required), time (text, required), persons (number, required, min 1, max 20); purchase_rules: max_per_club 20, order_mode persistent
3. THE Booking_System SHALL create an Event_Record for PresMeet 2027 with name, location, start_date, end_date, registration_open, registration_close, payment_deadline, constraints, and linked product_ids
4. THE Booking_System SHALL remove the 6 dedicated legacy PresMeet Lambda handlers (save, submit, validate, payment, lock, unlock) from the SAM template and deploy the new Order_Service handlers as replacements
5. THE Booking_System SHALL provide a seed script that can recreate the PM2027 product and event configuration from scratch, usable for both initial deployment and test environment setup

### Requirement 15: Authorization

**User Story:** As a system operator, I want proper authorization checks on all PresMeet endpoints, so that only authorized club delegates can manage their own bookings and only admins can perform administrative actions.

#### Acceptance Criteria

1. THE Order_Service SHALL verify that the authenticated user belongs to the club_id on the order before allowing read or write operations on PresMeet bookings
2. THE Order_Service SHALL use the existing auth pattern: extract_user_credentials() followed by validate_permissions_with_regions()
3. THE Order_Service SHALL require Regio_Pressmeet or Regio_All in the user's Cognito groups before granting access to any PresMeet endpoint
4. THE Order_Service SHALL scope all club-level operations to the user's resolved club_id via get_club_id(user_email)
5. IF a user attempts to access an order belonging to a different club, THEN THE Order_Service SHALL return a 403 Forbidden response
6. IF get_club_id(user_email) returns no club assignment, THEN THE Order_Service SHALL return a 403 Forbidden response indicating missing club assignment
7. THE Admin_Dashboard endpoints SHALL require Webshop_Management permission combined with Regio_Pressmeet or Regio_All before allowing administrative actions such as viewing any club's booking, locking orders, or recording payments
8. IF a user has PresMeet admin access (Webshop_Management combined with Regio_Pressmeet or Regio_All), THEN THE Order_Service SHALL allow that user to query bookings for any club_id via query parameter

### Requirement 16: Tenant Terminology Cleanup

**User Story:** As a developer, I want the field currently named `tenant` renamed to `channel` across the codebase and data layer, so that the term `tenant` remains available for future multi-tenancy and the field name accurately reflects its purpose (product catalog/shop channel segmentation).

#### Acceptance Criteria

1. WHEN the migration runs, THE Booking_System SHALL rename the `tenant` field to `channel` in all existing records in the Orders, Producten, Carts, and StockMovements DynamoDB tables
2. THE Booking_System SHALL update the shared auth layer module `tenant_resolver.py` to be renamed to `channel_resolver.py`, with functions renamed from `resolve_tenants` to `resolve_channels` and `validate_tenant_access` to `validate_channel_access`, while preserving identical logic
3. THE Booking_System SHALL update all Lambda handler source files that reference `tenant` as a data field or query parameter to use `channel` instead, including but not limited to: create_cart, get_products, admin_get_products, admin_lock_orders, admin_generate_report, save_presmeet_booking, and the shared helpers (stock_helpers, variant_helpers)
4. THE Booking_System SHALL update the GROUP_TENANT_MAP constant to GROUP_CHANNEL_MAP, maintaining the same Cognito group to channel value mappings: hdcnLeden → `h-dcn`, Regio_Pressmeet → `presmeet`, Regio_All → `presmeet`
5. THE Booking_System SHALL update all API query parameters and request/response body fields from `tenant` to `channel` across both backend endpoints and frontend API calls
6. THE Booking_System SHALL update all frontend service modules, TypeScript types, and component props that reference `tenant` to use `channel`
7. IF any DynamoDB record is missing the new `channel` field after migration (e.g., due to a partial migration), THEN THE Booking_System SHALL treat the record as having channel value `h-dcn` (the default) to maintain backward compatibility
8. THE Booking_System SHALL execute this rename as part of the same migration window as the PresMeet v3 data migration (Requirement 14), ensuring both changes are applied atomically per table scan batch
