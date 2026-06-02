# Requirements Document

## Introduction

PresMeet is an event registration and booking module for the FH-DCE Presidents' Meeting, integrated into the existing H-DCN member portal. It allows ~65 FH-DCE clubs to register delegates, order party tickets, t-shirts, and airport transfers through a booking-form UX that maps to the existing webshop cart/order/payment pipeline. All orderable items are modeled as products with product-type-driven JSON attributes.

## Glossary

- **Booking_System**: The PresMeet module within the H-DCN portal that handles event registration and ordering
- **Club_User**: An authenticated user representing one of the ~65 FH-DCE member clubs
- **Admin**: An event organizer with elevated permissions to manage all bookings and payments
- **Product**: An item in the Producten table with a `product_type` field and type-specific JSON `attributes`
- **Cart**: A collection of product items being assembled by a Club_User before submission
- **Order**: A submitted collection of product items with a lifecycle status (draft → submitted → locked)
- **Product_Type**: A classification that determines the required JSON attributes and business rules for a product (meeting_ticket, party_ticket, tshirt, airport_transfer)
- **Product_Type_Config**: A configuration record defining rules per product type (max_per_club, min_per_club, required_attributes schema)
- **Delegate**: A club representative attending the Presidents' Meeting (max 3 per club)
- **Guest**: An additional person attending the party (not a delegate)
- **Mollie**: The payment service provider used for online payments

## Requirements

### Requirement 1: Product Type Extension

**User Story:** As a system administrator, I want products to carry a product_type and type-specific attributes, so that the webshop can handle diverse event items with validated metadata.

#### Acceptance Criteria

1. THE Booking_System SHALL store a `product_type` field on each product record in the Producten table, constrained to one of: `meeting_ticket`, `party_ticket`, `tshirt`, `airport_transfer`
2. THE Booking_System SHALL store an `attributes` JSON field on each product record containing type-specific metadata
3. WHEN a product has product_type `meeting_ticket`, THE Booking_System SHALL require attributes containing `name` (string, 1–100 characters) and `role` (string, 1–100 characters)
4. WHEN a product has product_type `party_ticket`, THE Booking_System SHALL require attributes containing `name` (string, 1–100 characters) and `person_type` (one of: delegate, guest)
5. WHEN a product has product_type `tshirt`, THE Booking_System SHALL require attributes containing `name` (string, 1–100 characters), `gender` (one of: male, female), and `size` (one of: S, M, L, XL, XXL, 3XL, 4XL)
6. WHEN a product has product_type `airport_transfer`, THE Booking_System SHALL require attributes containing `direction` (one of: pickup, dropoff), `airport` (one of: AMS, RTM, EIN), `flight` (string, 2–10 characters), `date` (ISO 8601 date string, format YYYY-MM-DD), `time` (string in HH:MM 24-hour format), and `persons` (integer, minimum 1, maximum 50)
7. IF a cart item is added with invalid or missing required attributes for its product_type, THEN THE Booking_System SHALL reject the item and return a validation error indicating which fields failed and the reason for each failure
8. IF a product is created or updated with a `product_type` value not in the allowed set, THEN THE Booking_System SHALL reject the operation and return a validation error indicating the invalid product_type

### Requirement 2: Product Type Configuration

**User Story:** As an admin, I want to configure per-product-type rules (maximum and minimum quantities per club), so that booking constraints are enforced consistently and can be adjusted without code changes.

#### Acceptance Criteria

1. THE Booking_System SHALL store a Product_Type_Config record for each product_type containing `max_per_club` (integer, 1 or greater) and `min_per_club` (integer, 0 or greater) fields, where `min_per_club` does not exceed `max_per_club`
2. THE Booking_System SHALL enforce that a Club_User cannot add more items of a given product_type to their active order than the configured `max_per_club` value for that product_type
3. WHEN a Club_User attempts to add a cart item that would cause the total count of that product_type in their order to exceed `max_per_club`, THE Booking_System SHALL reject the addition and return an error indicating the configured limit and the current count
4. THE Booking_System SHALL enforce the following default Product_Type_Config values: meeting_ticket `max_per_club` of 3 and `min_per_club` of 1, party_ticket `max_per_club` of 13 and `min_per_club` of 0, tshirt `max_per_club` of 13 and `min_per_club` of 0, airport_transfer `max_per_club` of 20 and `min_per_club` of 0
5. WHEN a Club_User submits a booking and the order contains fewer items of a product_type than its configured `min_per_club`, THE Booking_System SHALL reject the submission and return a validation error indicating the minimum required quantity
6. WHEN an Admin updates a Product_Type_Config, THE Booking_System SHALL apply the new limits to all subsequent cart additions and submission validations without affecting items already present in existing orders

### Requirement 3: Club-Based Authentication and Authorization

**User Story:** As a club representative, I want to log in with my club account and access only my club's booking, so that each club manages its own registration independently.

#### Acceptance Criteria

1. THE Booking_System SHALL authenticate Club_Users via the existing AWS Cognito user pool
2. THE Booking_System SHALL map each authenticated user to exactly one FH-DCE club using a `club_id` claim derived from the user's Cognito group membership
3. THE Booking_System SHALL store a `club_id` field on each Cart and Order record, assigned from the authenticated Club_User's mapped club at creation time
4. WHEN a Club_User is authenticated, THE Booking_System SHALL restrict cart and order access to records whose `club_id` matches the user's mapped club
5. WHEN an unauthenticated request is received, THE Booking_System SHALL return a 401 error response
6. WHEN a Club_User attempts to access another club's order or cart, THE Booking_System SHALL return a 403 error response
7. IF an authenticated user cannot be mapped to any club (no club group membership found), THEN THE Booking_System SHALL return a 403 error response indicating missing club assignment
8. THE Booking_System SHALL grant Admin users read and write access to all clubs' orders and carts regardless of club_id

### Requirement 4: Booking Form Cart Management

**User Story:** As a club representative, I want to fill in a booking form with delegates, guests, t-shirts, and transfers, so that the system creates the correct cart items behind the scenes.

#### Acceptance Criteria

1. WHEN a Club_User adds a delegate via the booking form, THE Booking_System SHALL create a meeting_ticket cart item with the delegate's name and role as attributes, and IF party attendance is selected for that delegate, THE Booking_System SHALL also create a party_ticket cart item with person_type "delegate" and the delegate's name as attributes
2. WHEN a Club_User adds a guest via the booking form, THE Booking_System SHALL create a party_ticket cart item with person_type "guest" and the guest's name as attributes
3. WHEN a Club_User selects a t-shirt for a delegate or guest, THE Booking_System SHALL create a tshirt cart item with the associated person's name, selected gender (male or female), and selected size (S, M, L, XL, XXL, 3XL, or 4XL) as attributes
4. WHEN a Club_User adds an airport transfer, THE Booking_System SHALL create an airport_transfer cart item with direction (pickup or dropoff), airport (AMS, RTM, or EIN), flight number (string, maximum 10 characters), date (ISO date within the event date range), time (HH:MM format), and number of persons (integer, 1 to 13) as attributes
5. THE Booking_System SHALL calculate the cart total as the sum of: (count of meeting_ticket items × €50) + (count of party_ticket items × €99.50) + (count of tshirt items × €25) + (sum of each airport_transfer item's persons field × €5)
6. WHEN a Club_User saves the booking form, THE Booking_System SHALL persist all cart items with status "draft"
7. WHILE the order status is "draft", THE Booking_System SHALL allow a Club_User to add, edit, or remove cart items
8. WHEN a Club_User removes a delegate via the booking form, THE Booking_System SHALL delete the associated meeting_ticket, party_ticket (if present), and tshirt (if present) cart items for that delegate
9. IF a Club_User attempts to add a cart item that would exceed the configured max_per_club limit for that product_type, THEN THE Booking_System SHALL reject the addition and display an error indicating the maximum allowed quantity

### Requirement 5: Order Lifecycle

**User Story:** As a club representative, I want to submit my booking when complete, so that the organizers can process it and I can proceed to payment.

#### Acceptance Criteria

1. THE Booking_System SHALL support three order statuses: draft, submitted, and locked
2. WHEN a Club_User submits a booking, THE Booking_System SHALL transition the order status from "draft" to "submitted"
3. IF a Club_User attempts to submit a booking that is not in "draft" status, THEN THE Booking_System SHALL reject the submission and return an error indicating the current status does not allow submission
4. WHILE an order status is "submitted", THE Booking_System SHALL allow the Club_User to add, remove, or update cart items, and SHALL transition the order status back to "draft" upon any such modification
5. WHEN an Admin locks an order, THE Booking_System SHALL transition the order status to "locked"
6. WHILE an order status is "locked", THE Booking_System SHALL reject any modification attempt by the Club_User and return an error indicating the order is locked
7. WHILE an order status is "locked", THE Booking_System SHALL allow an Admin to unlock or view the order but SHALL prevent Admin item modifications
8. WHEN an Admin unlocks an order, THE Booking_System SHALL transition the order status back to "submitted"
9. WHEN an Admin triggers "Lock ALL", THE Booking_System SHALL transition all orders currently in "submitted" status to "locked" status, leaving "draft" orders unchanged

### Requirement 6: Payment Processing

**User Story:** As a club representative, I want to pay for my booking online or have the admin record a manual payment, so that the financial status of my booking is tracked.

#### Acceptance Criteria

1. WHEN a Club_User initiates payment for an order with status "submitted" or "locked", THE Booking_System SHALL create a Mollie payment session for the order total amount
2. WHEN Mollie reports a successful payment via webhook, THE Booking_System SHALL record the payment against the order and set the order payment status to "paid"
3. IF Mollie reports a failed, cancelled, or expired payment via webhook, THEN THE Booking_System SHALL update the payment record status to the corresponding Mollie status and leave the order payment status unchanged
4. WHEN an Admin records a manual payment, THE Booking_System SHALL create a payment record with the specified amount (between €0.01 and €999,999.99), date, and description (maximum 255 characters)
5. THE Booking_System SHALL calculate the outstanding balance as the order total minus the sum of all recorded payments for that order, with a minimum balance of €0.00
6. WHEN the outstanding balance reaches zero, THE Booking_System SHALL mark the order as fully paid
7. IF a Club_User attempts to initiate payment for an order with status "draft", THEN THE Booking_System SHALL reject the request and return an error indicating the order must be submitted before payment

### Requirement 7: Admin Dashboard and Reporting

**User Story:** As an admin, I want an overview of all bookings with aggregated statistics, so that I can monitor registration progress and manage the event logistics.

#### Acceptance Criteria

1. THE Booking_System SHALL display an overview showing total counts per product_type across all orders, split by order status (draft, submitted, and locked)
2. THE Booking_System SHALL display a list of all orders sorted by club name ascending, showing club name, order status, creation date, modification date, and submission date (blank if not yet submitted)
3. WHEN an Admin selects an order, THE Booking_System SHALL display the full order details including all items with their product_type and attributes, and the payment history showing each payment amount, date, and description
4. THE Booking_System SHALL provide a downloadable CSV export of all submitted orders containing club name, order status, and for each item: product_type, quantity, unit price, and all attribute values
5. THE Booking_System SHALL provide a downloadable CSV export of all saved orders (including drafts and locked) containing club name, order status, and for each item: product_type, quantity, unit price, and all attribute values
6. THE Booking_System SHALL display aggregate payment statistics showing total charged, total paid, and total outstanding across all submitted and locked orders
7. WHEN a non-Admin user attempts to access the admin dashboard, THE Booking_System SHALL return a 403 error response

### Requirement 8: Attribute Validation

**User Story:** As a club representative, I want the system to validate my booking data before submission, so that I can correct errors early.

#### Acceptance Criteria

1. WHEN a Club_User submits a booking, THE Booking_System SHALL validate that all cart items have attributes matching the `required_attributes` schema defined in the Product_Type_Config for their product_type
2. IF validation fails, THEN THE Booking_System SHALL reject the submission, keep the order in "draft" status, and return a list of all validation errors where each error references the specific cart item and the field that failed validation
3. IF the order contains fewer than 1 meeting_ticket item, THEN THE Booking_System SHALL reject the submission and return a validation error indicating that at least one meeting_ticket is required
4. IF an airport_transfer item has a `date` value that falls outside the event start and end dates as configured on the associated Event record, THEN THE Booking_System SHALL reject the submission and return a validation error referencing the item and the invalid date
5. IF an airport_transfer item has a `persons` value that is not an integer between 1 and 50 inclusive, THEN THE Booking_System SHALL reject the submission and return a validation error referencing the item and the invalid persons value
6. WHEN a Club_User saves the booking form as draft, THE Booking_System SHALL NOT enforce submission validation rules, allowing incomplete attributes to be persisted

### Requirement 9: Booking Overview

**User Story:** As a club representative, I want to see a summary of my booking with itemized costs, so that I can verify everything before submitting.

#### Acceptance Criteria

1. THE Booking_System SHALL display a booking overview showing all items grouped by product_type, where each group displays the product_type label, the number of items, the unit price, and the line total (quantity × unit price)
2. THE Booking_System SHALL display within each product_type group the individual items with their identifying attributes (name for meeting_ticket and party_ticket, name and size for tshirt, direction and airport for airport_transfer)
3. THE Booking_System SHALL display the grand total of the booking as the sum of all line totals, formatted in euros with two decimal places
4. THE Booking_System SHALL display a payment summary showing the total amount paid and the remaining balance (grand total minus total paid)
5. WHEN the order status changes, THE Booking_System SHALL display the current order status label (draft, submitted, or locked) in the booking overview
6. IF the booking contains no items, THEN THE Booking_System SHALL display the overview with a zero grand total and an indication that no items have been added

### Requirement 10: Product Type Attribute Schema Validation

**User Story:** As a developer, I want a schema-driven validation system for product attributes, so that new product types can be added without modifying validation logic.

#### Acceptance Criteria

1. THE Booking_System SHALL store a `required_attributes` JSON schema definition on each Product_Type_Config record, supporting field-level constraints for type (string, integer), enum (list of allowed values), required (boolean), and minimum (numeric lower bound)
2. WHEN a cart item is created or updated, THE Booking_System SHALL validate the item's attributes against the `required_attributes` schema of its product_type and reject the item with a validation error identifying each failing field and constraint violation if validation fails
3. THE Booking_System SHALL ensure that all attribute values stored as JSON can be deserialized back to produce a structurally identical attribute object (all keys and values preserved with original types)
4. IF an attribute value is not contained in the enum list defined by the schema for that field, THEN THE Booking_System SHALL reject the cart item and return a validation error identifying the field and the allowed values
5. IF an attribute value does not match the type constraint defined by the schema for that field, THEN THE Booking_System SHALL reject the cart item and return a validation error identifying the field and the expected type
6. IF a cart item is missing one or more fields marked as required in the schema for its product_type, THEN THE Booking_System SHALL reject the cart item and return a validation error identifying each missing field
