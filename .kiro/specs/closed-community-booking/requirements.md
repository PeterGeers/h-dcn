# Requirements Document

## Introduction

A generic booking module for invitation-only (closed community) events within the H-DCN club portal. Access is controlled by a shared event password and a configurable invitee registry (S3 JSON). Each row in the registry represents one booking slot. Event rules define how the registry works — what a "slot" means, who can claim it, and how many delegates per slot.

The module reuses existing Products, Orders, and Payments infrastructure. One order per registry row per event. This feature is intended to replace the existing PresMeet module with a generic, registry-driven booking system.

## Glossary

- **Portal**: The H-DCN web application at portal.h-dcn.nl
- **Invitee_Registry**: A per-event S3 JSON file listing all allowed booking slots (rows), uploaded by an admin and read-only at runtime
- **Registry_Row**: A single entry in the Invitee_Registry representing one booking slot (e.g., a club, team, or individual)
- **Claim**: The act of reserving a Registry_Row by an authenticated user, stored as runtime state in DynamoDB
- **Delegate**: A user who manages an order for a claimed Registry_Row (primary or secondary)
- **Primary_Delegate**: The member who originally claimed the Registry_Row and owns the order
- **Secondary_Delegate**: An additional member invited by the Primary_Delegate to co-manage the order
- **Person**: An attendee (guest) added to an order who will receive products/tickets at the event
- **Event_Password**: A shared secret (bcrypt-hashed) used as a gate to the registration flow
- **Landing_Page_Flow**: The multi-step registration process: password gate → registry selector → account creation/linking → row claim → redirect to booking
- **Password_Gate**: The UI step where users enter the shared event password
- **Registry_Selector**: The UI step where users choose an available Registry_Row to claim
- **Booking_Form**: The per-person product selection form where delegates build their order
- **Order_Lifecycle**: The status progression of an order: draft → submitted → locked
- **Claim_Mode**: The access control mode for row claims: first_come_first_served or email_restricted
- **Row_Label**: A configurable display term for registry rows (e.g., "club", "team", "deelnemer")
- **Preparation_PDF**: An admin-downloadable PDF for preparing event handover packages
- **Onboard_Endpoint**: The backend API that atomically claims a row, creates/links a Cognito account, and creates/updates the Member record
- **Registry_Claims_Map**: A DynamoDB map attribute on the Event record storing all row claims at runtime
- **Effective_Limit**: The minimum of the per-order remaining capacity and the per-event remaining capacity for a product
- **Sold_Count**: The aggregate number of a specific product sold across all orders for an event

## Requirements

### Requirement 1: Event Password Verification

**User Story:** As an invited guest, I want to verify the event password on the landing page, so that only authorized invitees can access the registration flow.

#### Acceptance Criteria

1. WHEN a user submits a password on the landing page, THE Portal SHALL truncate the input to a maximum of 72 bytes before verification, verify it against the bcrypt-hashed Event_Password stored on the Event record, and return a validity result within 2 seconds
2. IF the submitted password is incorrect or the event_id does not match any existing Event record, THEN THE Portal SHALL display the same localized error message in both cases without revealing whether the event exists
3. WHEN the submitted password is correct, THE Portal SHALL present the Registry_Selector step with event metadata and registry configuration
4. THE Portal SHALL rate-limit the password verification endpoint to a maximum of 10 requests per IP address per minute via API Gateway throttling; IF the rate limit is exceeded, THEN THE Portal SHALL reject the request and display a localized message indicating the user must wait before retrying
5. IF the Event record has no Event_Password or landing_page_enabled is false, THEN THE Portal SHALL skip the Password_Gate step entirely

### Requirement 2: Invitee Registry Display

**User Story:** As an invited guest, I want to see all available booking slots after password verification, so that I can select my club or team.

#### Acceptance Criteria

1. WHEN a user passes the Password_Gate, THE Portal SHALL display all Registry_Rows merged from the S3 Invitee_Registry and DynamoDB Registry_Claims_Map, sorted alphabetically by row label
2. THE Portal SHALL show each Registry_Row with its label, availability status (available or taken), and logo image; IF a Registry_Row has no logo_url, THEN THE Portal SHALL display a generic placeholder icon in place of the logo
3. WHEN a Registry_Row is already claimed, THE Portal SHALL display a masked version of the claimant email (first two characters + asterisks + domain) and disable selection
4. THE Portal SHALL use the Row_Label from registry_config to label the UI elements (e.g., "Selecteer je club" or "Selecteer je team")
5. WHILE the Claim_Mode is email_restricted, THE Portal SHALL visually distinguish rows matching the current user's email address by rendering them as enabled and marking non-matching rows as disabled with a tooltip explaining the restriction
6. IF the S3 Invitee_Registry fails to load or returns a non-200 response, THEN THE Portal SHALL display a localized error message indicating the registry is temporarily unavailable and offer a retry action

### Requirement 3: Row Claim (Atomic Registration)

**User Story:** As an invited guest, I want to claim a booking slot for my club, so that I become the primary delegate and can start booking.

#### Acceptance Criteria

1. WHEN a user selects an available Registry_Row, THE Onboard_Endpoint SHALL atomically claim it using a DynamoDB conditional write on the Registry_Claims_Map
2. IF the conditional write fails (row already claimed by another user), THEN THE Onboard_Endpoint SHALL return HTTP 409 with a masked contact email of the existing claimant
3. WHILE the Claim_Mode is email_restricted, THE Onboard_Endpoint SHALL verify the user's email matches the allowed_emails list on the Registry_Row using case-insensitive comparison before accepting the claim
4. IF the user's email does not match the allowed_emails for an email_restricted row, THEN THE Onboard_Endpoint SHALL return HTTP 403 with an error message indicating the user's email is not authorized for the selected row
5. WHEN a claim succeeds, THE Onboard_Endpoint SHALL store the member_id, email, name, and claimed_at timestamp in the Registry_Claims_Map
6. IF a user already holds a claim on another Registry_Row for the same event, THEN THE Onboard_Endpoint SHALL return HTTP 409 with an error message indicating only one row may be claimed per user per event

### Requirement 4: Account Creation and Linking

**User Story:** As a new user, I want to create an account during the registration flow, so that I can access the booking form with my personal credentials.

#### Acceptance Criteria

1. WHEN a new user completes the onboarding flow, THE Onboard_Endpoint SHALL create a Cognito user via AdminCreateUser with email_verified set to true and a permanent password (MessageAction SUPPRESS) so the user is in CONFIRMED state without requiring a forced password change
2. WHEN a new user is onboarded, THE Onboard_Endpoint SHALL create a Member record with member_type set to the event_id, club_id set to the row_id, allowed_events containing the event_id, email set to the user's email, and name set to the user's provided name
3. WHEN a new user is onboarded, THE Onboard_Endpoint SHALL add the Cognito user to the event_participant group
4. WHEN an existing H-DCN member claims a row, THE Onboard_Endpoint SHALL append the event_id to the member's allowed_events list only if not already present, without modifying member_type, club_id, or other existing fields
5. IF a Cognito user with the same email already exists during onboarding, THEN THE Onboard_Endpoint SHALL link the existing account by adding event access (allowed_events, event_participant group) without creating a duplicate Cognito user
6. WHEN a returning user (already onboarded for this event) logs in, THE Portal SHALL detect that the event_id is present in the user's allowed_events and grant direct access to the Booking_Form without requiring the Landing_Page_Flow
7. IF Cognito user creation succeeds but Member record creation fails, THEN THE Onboard_Endpoint SHALL delete the created Cognito user and return an error indicating the operation failed

### Requirement 5: Delegate Management

**User Story:** As a primary delegate, I want to invite a secondary delegate to co-manage my booking, so that another person from my club can help manage the order.

#### Acceptance Criteria

1. THE Portal SHALL allow the Primary_Delegate to invite a Secondary_Delegate by entering a valid email address, up to the max_delegates_per_row limit from registry_config
2. IF the Primary_Delegate enters their own email address as the invitation target, THEN THE Portal SHALL reject the invitation and display an error message indicating self-invitation is not allowed
3. WHEN a secondary delegate invitation is sent, THE Portal SHALL store the email (lowercased) as pending_secondary_email on the order until the invitee creates or links an account
4. WHEN a pending secondary delegate completes onboarding with a case-insensitive matching email, THE Portal SHALL automatically link them as Secondary_Delegate on the order
5. WHILE the order status is draft, THE Portal SHALL allow both Primary_Delegate and Secondary_Delegate to edit the order with optimistic locking (version field) to prevent conflicts
6. WHEN a delegate attempts to save and the order version has changed, THE Portal SHALL reject the save and display a notification indicating the order was modified by another delegate, with a reload action
7. THE Portal SHALL allow the Primary_Delegate to revoke a pending invitation or remove a linked Secondary_Delegate at any time while the order status is draft

### Requirement 6: Person (Guest) Management

**User Story:** As a delegate, I want to add and manage persons (attendees) on my order, so that I can book products for all guests in my group.

#### Acceptance Criteria

1. THE Booking_Form SHALL allow delegates to add persons up to the highest max_per_club value across all event-linked products, with a minimum of 1 person (the delegate themselves)
2. THE Booking_Form SHALL require a trimmed name of 1 to 100 characters for every person added to the order, rejecting whitespace-only input
3. THE Booking_Form SHALL pre-fill the first person card with the delegate's name from the Member record, and SHALL prevent removal of this first person
4. WHEN a person is added or their name is updated, THE Booking_Form SHALL sync item_fields_data.name on every product line for that person with the current person name
5. WHEN a person is removed, THE Booking_Form SHALL remove all product lines associated with that person from the order

### Requirement 7: Product Selection with Dual Quantity Limits

**User Story:** As a delegate, I want to select products for each person with clear visibility of remaining capacity, so that I can build a valid order within the event limits.

#### Acceptance Criteria

1. THE Booking_Form SHALL display all active parent products linked to the event for each person, fetched via the products endpoint filtered by event_id
2. THE Booking_Form SHALL enforce the per-order limit (max_per_club) for each product across all persons in the order by disabling the product selection control when the limit is reached
3. THE Booking_Form SHALL enforce the per-event limit (max_per_event) for each product using the Sold_Count from the backend by disabling the product selection control when the remaining event capacity is zero
4. IF a product has no max_per_event configured, THEN THE Booking_Form SHALL treat the per-event capacity as unlimited and apply only the per-order limit (max_per_club)
5. THE Booking_Form SHALL display the Effective_Limit for each product as "X of Y remaining", where Y is the minimum of max_per_club and max_per_event (or max_per_club alone when max_per_event is absent), and X is Y minus the quantity already selected in this order or sold globally
6. WHEN a product has variant_schema defined, THE Booking_Form SHALL render variant selection dropdowns that map to a valid variant_id before the product line can be added
7. WHEN a product has order_item_fields defined, THE Booking_Form SHALL render the dynamic fields via the ProductConfigurator component
8. WHEN the Booking_Form is opened or a product selection is changed, THE Booking_Form SHALL fetch the current Sold_Count from the backend to reflect up-to-date per-event capacity

### Requirement 8: Order Auto-Save (Draft State)

**User Story:** As a delegate, I want my booking progress to be auto-saved, so that I do not lose work if I navigate away or close the browser.

#### Acceptance Criteria

1. WHILE the order status is draft, THE Booking_Form SHALL auto-save the order to the backend 3 seconds after the last modification to order data (adding/removing persons, changing product quantities, selecting variants, or editing field values)
2. WHILE the order status is draft, THE Booking_Form SHALL accept data that does not pass submission validation (missing person names, incomplete fields, zero quantities) without displaying validation errors
3. THE Booking_Form SHALL use optimistic locking via a version field to prevent concurrent overwrites between delegates
4. WHILE auto-saving, THE Booking_Form SHALL display a visual save-status indicator showing one of three states: saving, saved, or save failed
5. IF an auto-save request fails due to a network error or server error, THEN THE Booking_Form SHALL retain the unsaved changes locally, display the save-failed indicator, and retry the save on the next user modification or after 30 seconds (whichever comes first)

### Requirement 9: Order Submission with Validation

**User Story:** As a delegate, I want to submit my booking after validation, so that the event organizers can confirm my registration.

#### Acceptance Criteria

1. WHEN a delegate submits the order, THE Portal SHALL validate on the backend that every person has a non-empty name (at least 1 non-whitespace character)
2. WHEN a delegate submits the order, THE Portal SHALL validate on the backend that every order line has item_fields_data.name populated with a non-empty string
3. WHEN a delegate submits the order, THE Portal SHALL validate on the backend that all required order_item_fields (as defined in the product configuration) are filled for each product line
4. WHEN a delegate submits the order, THE Portal SHALL validate on the backend that per-order quantity limits (max_per_club) are not exceeded for any product across all persons in the order
5. WHEN a delegate submits the order, THE Portal SHALL validate on the backend that per-event capacity limits (max_per_event) are not exceeded by reading the current Sold_Count from DynamoDB at submission time
6. WHEN a delegate submits the order, THE Portal SHALL validate on the backend that every variant selection references a variant_id that exists in the product's variant list
7. WHEN all validations pass, THE Portal SHALL transition the order status from draft to submitted and display a confirmation page with a payment option
8. IF any validation fails, THEN THE Portal SHALL return error messages identifying the failing person, product, and field for each violation, and display them grouped per person in the Booking_Form
9. IF a per-event capacity limit (max_per_event) is exceeded at submission time due to concurrent orders, THEN THE Portal SHALL reject the submission and display the current remaining capacity for the affected products

### Requirement 10: Order Locking

**User Story:** As an admin, I want to lock orders after the registration deadline, so that delegates cannot modify confirmed bookings.

#### Acceptance Criteria

1. WHEN an admin locks a submitted order, THE Portal SHALL transition the order status from submitted to locked and prevent delegates from adding, removing, or editing persons, product selections, and quantities
2. WHILE the order status is submitted or locked, THE Portal SHALL render the order in a read-only view for delegates where all form fields are disabled, add/remove person actions are hidden, and no save or submit actions are available
3. WHEN an admin unlocks a submitted or locked order, THE Portal SHALL transition the order status back to draft and re-enable delegate editing with auto-save behaviour
4. IF an admin attempts to lock an order that is not in submitted status, THEN THE Portal SHALL reject the action and display an error message indicating only submitted orders can be locked
5. THE Portal SHALL allow admins to lock or unlock multiple orders in a single batch action from the order list view, applying the same status transition rules per order

### Requirement 11: Payment Integration

**User Story:** As a delegate, I want to pay for my booking via Mollie, so that I can complete my registration.

#### Acceptance Criteria

1. WHEN a delegate initiates payment on a submitted or locked order with an outstanding balance greater than zero, THE Portal SHALL redirect to the Mollie checkout page using the existing pay_order handler and return the checkout URL within 5 seconds
2. WHEN the Mollie webhook confirms payment, THE Portal SHALL update the order's payment_status to paid (if total_paid equals or exceeds total_amount) or partial (if total_paid is greater than zero but less than total_amount), and update total_paid accordingly
3. WHEN an admin records a manual payment via the admin_record_payment endpoint specifying order_id and amount, THE Portal SHALL add the amount to total_paid and recalculate payment_status using the same paid/partial/unpaid rules
4. THE Portal SHALL treat submission and payment as separate steps — a submitted order is visible in admin dashboards, lockable by admins, and downloadable as PDF regardless of payment_status
5. IF the Mollie payment provider returns an error during payment initiation, THEN THE Portal SHALL display an error message indicating the payment could not be started and preserve the order in its current status

### Requirement 12: PDF Booking Confirmation

**User Story:** As a delegate, I want to download a PDF summary of my booking, so that I have a portable confirmation document.

#### Acceptance Criteria

1. THE Portal SHALL allow delegates to download a PDF booking confirmation at any order status (draft, submitted, or locked)
2. THE Portal SHALL include in the PDF: event name, row label, name and email of all assigned delegates (primary and secondary), all persons with their products, fields, variants, order status, total amount, and payment status
3. WHEN the PDF is generated, THE Portal SHALL run the same validation checks as order submission (person names non-empty, item_fields_data.name populated, required order_item_fields filled, per-order quantity limits, per-event capacity limits, variant validity) and indicate whether the order is "valid at this moment" or list issues grouped per person and per product
4. THE Portal SHALL append a disclaimer to every PDF: "Generated on {date-time}. Products and availability subject to change." where {date-time} is a locale-formatted date and time including hours and minutes
5. IF the order is in draft status with no persons added, THEN THE Portal SHALL generate a PDF containing the order metadata (event name, row label, delegate information, order status, and disclaimer) with an indication that no persons have been added yet

### Requirement 13: Admin Claims Management

**User Story:** As an admin, I want to view and manage all registry claims, so that I can resolve claim issues and manually assign rows.

#### Acceptance Criteria

1. THE Portal SHALL display an admin table listing all Registry_Rows with: row label, claim status (available, claimed, or pending), delegate name, delegate email, and claimed_at timestamp, with pagination at 50 rows per page
2. WHEN an admin releases a claim, THE Portal SHALL remove the entry from the Registry_Claims_Map and retain the associated order in its current status without deletion
3. WHEN an admin releases a claim, THE Portal SHALL require a confirmation dialog before executing the release
4. WHEN an admin manually assigns a row to a member (identified by email address search), THE Portal SHALL write the claim to Registry_Claims_Map and create a draft order for that row, bypassing the Landing_Page_Flow
5. IF an admin attempts to manually assign a row that is already claimed, THEN THE Portal SHALL display the current claimant and require the admin to release the existing claim before re-assigning
6. THE Portal SHALL allow admins to reassign the Primary_Delegate on an order to a different member, remove a Secondary_Delegate from an order, and cancel a pending secondary delegate invitation

### Requirement 14: Registration Progress Dashboard

**User Story:** As an admin, I want a real-time overview of booking progress, so that I can monitor registration status and take action on incomplete bookings.

#### Acceptance Criteria

1. WHEN an admin navigates to the event dashboard, THE Portal SHALL display summary cards showing: total rows, claimed rows, unclaimed rows, and registration percentage (integer, 0-100) calculated from the Invitee_Registry and Registry_Claims_Map for the selected event
2. THE Portal SHALL display order status breakdown: draft, submitted, and locked counts with percentages (integer, of total orders for the event)
3. THE Portal SHALL display payment status breakdown: unpaid, partial, and paid counts with total revenue collected versus expected, where expected revenue is the sum of total_amount across all submitted and locked orders for the event, displayed in EUR with 2 decimal places
4. THE Portal SHALL display per-product capacity usage with progress bars showing Sold_Count versus max_per_event for each event-linked product
5. THE Portal SHALL display a filterable list of orders (by status, payment_status, and row/club) linking to order detail, refreshed each time the admin navigates to the dashboard
6. THE Portal SHALL allow admins to export all orders for the event to CSV including: order items (product name, variant, quantity, unit price), delegate name and email, person names, order status, payment status, and order total

### Requirement 15: Preparation PDF (Admin)

**User Story:** As an event organizer, I want to generate preparation PDFs grouped by order or by guest, so that I can prepare handover packages and goodie bags.

#### Acceptance Criteria

1. THE Portal SHALL allow admins to download a Preparation_PDF in two modes: "by order" (grouped by club) and "by guest" (one page per person)
2. WHEN the mode is "by order", THE Portal SHALL render one page per order containing: club logo (if available in the registry, otherwise omitted), club name, event name, primary and secondary delegate names, a table of all guests with columns for guest name, product name, variant, field values, unit price, and line total, order total, and payment status
3. WHEN the mode is "by guest", THE Portal SHALL render one page per person containing: club logo (if available in the registry, otherwise omitted), club name, guest name, and all items ordered for that guest with product name, variant, field values, and unit price
4. THE Portal SHALL include only submitted and locked orders in the Preparation_PDF (draft orders are excluded)
5. THE Portal SHALL sort pages alphabetically case-insensitive (by club name in order-view, by guest last word in name in guest-view), with secondary sort by first name when primary keys are equal
6. THE Portal SHALL include a footer on each page with: event name, generation date in ISO 8601 format (YYYY-MM-DD), and page number in "Page X of Y" format
7. WHERE a product filter is specified, THE Portal SHALL include only pages that contain at least one order line matching the filtered product, and within those pages display only the matching product lines
8. IF no orders with status submitted or locked exist for the event, THEN THE Portal SHALL display an informational message indicating no data is available for PDF generation instead of producing an empty document

### Requirement 16: Access Control and Security

**User Story:** As a system operator, I want robust access control on the booking module, so that only authorized users can access their own bookings and event data.

#### Acceptance Criteria

1. THE Portal SHALL store the Event_Password as a bcrypt hash and never return it in plaintext via any API response
2. THE Portal SHALL mask claimant email addresses in the registry response (show first two characters + asterisks + domain)
3. THE Onboard_Endpoint SHALL use DynamoDB conditional writes to guarantee atomic row claims with no race conditions
4. WHEN a new user is created via onboarding, THE Portal SHALL assign only the event_participant Cognito group — no hdcnLeden, admin, or webshop roles
5. THE Portal SHALL verify event access on every booking API call (order read, order update, order submit, payment initiation) using the allowed_events list on the Member record combined with order ownership (delegate must be listed as Primary_Delegate or Secondary_Delegate on the order)
6. THE Portal SHALL re-verify the event password (or validate a session token with a maximum lifetime of 15 minutes) on the onboard endpoint to prevent direct API abuse
7. IF a booking API call fails the access check (event not in allowed_events or user is not a delegate on the order), THEN THE Portal SHALL return HTTP 403 with an error message indicating insufficient event access without revealing whether the order exists

### Requirement 17: Internationalization

**User Story:** As a user of any supported language, I want the booking module to be fully translated, so that I can complete the registration and booking flow in my preferred language.

#### Acceptance Criteria

1. THE Portal SHALL provide translations for all user-facing strings in the Landing_Page_Flow under the eventBooking namespace (landing section) in all 8 supported languages (nl, en, de, fr, es, it, da, sv), such that no component in the Landing_Page_Flow renders hardcoded text visible to the user
2. THE Portal SHALL provide translations for all user-facing strings in the Booking_Form under the eventBooking namespace in all 8 supported languages, such that no component in the Booking_Form renders hardcoded text visible to the user
3. THE Portal SHALL use the Row_Label value from registry_config as an interpolation parameter (e.g., {{rowLabel}}) in translated UI strings, so that labels like "Select your {{rowLabel}}" adapt dynamically to the event configuration
4. IF a translation key is missing for the user's selected language, THEN THE Portal SHALL fall back to the Dutch (nl) translation for that key
5. WHEN translation files are added or updated, THE Portal SHALL include the keys in both the src/locales/{lang}/eventBooking.json and public/locales/{lang}/eventBooking.json files for all 8 supported languages

### Requirement 18: Order Deduplication

**User Story:** As a system operator, I want to guarantee one order per registry row per event, so that duplicate bookings cannot be created.

#### Acceptance Criteria

1. THE Portal SHALL enforce one order per combination of club_id (row_id) and event_id by querying for existing non-cancelled orders before creating a new one in the create_order handler
2. IF a delegate navigates to the Booking_Form and a non-cancelled order already exists for their club_id and event_id, THEN THE Portal SHALL load the existing order and display it in the Booking_Form without creating a new order
3. IF the create_order handler receives a request with a null or empty club_id for an event order, THEN THE Portal SHALL return an error response indicating that club_id is required for event orders
4. WHEN the create_order handler returns an existing order (deduplication match), THE Portal SHALL return HTTP 200, distinguishable from HTTP 201 returned when a new order is created

### Requirement 19: Access Denied Handling

**User Story:** As a user without event access, I want to see a clear message directing me to register, so that I understand how to gain access to the booking form.

#### Acceptance Criteria

1. WHEN an authenticated user navigates to the Booking_Form without event access (event_id not in allowed_events), THE Portal SHALL display an AccessDeniedScreen containing a message that explains registration is required and a link to the event landing page (/events/:slug/info)
2. IF the event has no landing page configured (landing_page_enabled is false or slug is absent), THEN THE Portal SHALL display the AccessDeniedScreen without a registration link and instruct the user to contact the event organizer
3. THE Portal SHALL display all AccessDeniedScreen text in the user's selected language using translation keys from the eventBooking namespace, across all 8 supported languages (nl, en, de, fr, es, it, da, sv)
