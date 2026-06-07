# Requirements Document

## Introduction

Presmeet v3 addresses critical bugs, missing features, and UX improvements in the FH-DCE Presidents' Meeting booking system within the H-DCN member portal. The scope covers PDF generation for booking confirmations, correct order calculation including delegate party tickets and transport quantities, onboarding UX improvements, product data model migration, admin UI fixes, and permission corrections.

## Glossary

- **Presmeet_System**: The Presidents' Meeting booking module (frontend React components + backend Lambda handlers) that allows club presidents to book attendance, delegates, party tickets, t-shirts, and airport transfers for the annual FH-DCE Presidents' Meeting.
- **Booking_Overview**: The summary view displaying all booked items, quantities, unit prices, line totals, and the grand total for a club's Presidents' Meeting order.
- **PDF_Generator**: The frontend utility (jsPDF + jspdf-autotable) that produces a downloadable PDF document containing the booking overview and payment instructions.
- **Order_Calculator**: The backend logic (in `save_presmeet_booking` and `validate_presmeet_cart` handlers) that computes item quantities, line totals, and grand total for a presmeet order.
- **Onboarding_Page**: The start page of the Presmeet module shown to users who are not yet assigned to a club, allowing them to search for and select their club.
- **Product_Modal**: The admin modal in webshopbeheer used to create and edit products, including variant schemas and purchase rules.
- **Presmeet_Modal**: The booking modal/form where club presidents configure their meeting attendance, delegates, guests, and transfers.
- **Webshop_Checkout**: The general H-DCN webshop order placement flow that handles cart-to-order conversion and payment initiation.
- **Admin_Payment_Handler**: The backend Lambda (`admin_record_payment`) that registers manual payments against orders.
- **Event_Admin**: The event administration module that manages club events and requires specific permissions.
- **Cart_System**: The webshop cart (Carts DynamoDB table) that stores items before order placement.

## Requirements

### Requirement 1: PDF Download of Booking Overview

**User Story:** As a club president, I want to download a PDF of my booking overview with payment instructions, so that I can share it with my club treasurer or keep a record offline.

#### Acceptance Criteria

1. WHEN the user clicks the download PDF button on the Booking_Overview, THE PDF_Generator SHALL produce a PDF document containing the club name, all booked items grouped by product type, quantities, unit prices, line totals, and the grand total.
2. WHEN the order has payment_status "unpaid" or "partial", THE PDF_Generator SHALL include payment instructions with the outstanding amount and payment method details in the generated PDF.
3. THE PDF_Generator SHALL include delegate party tickets in the item listing of the generated PDF.
4. THE PDF_Generator SHALL include the club name as a header in the generated PDF.
5. WHEN the PDF is generated, THE PDF_Generator SHALL trigger a browser download with filename format `presmeet-booking-{club_id}.pdf`.

### Requirement 2: Correct Party Ticket Display for Delegates in Overview

**User Story:** As a club president, I want to see the cost of party tickets for my delegates in the booking overview, so that I have an accurate view of total costs.

#### Acceptance Criteria

1. WHEN a delegate has `attend_party` set to true, THE Booking_Overview SHALL display a party_ticket line item for that delegate with the delegate's name and the party_ticket unit price.
2. THE Booking_Overview SHALL include delegate party tickets in the line total calculation for the party_ticket product group.
3. THE Booking_Overview SHALL include delegate party tickets in the grand total calculation.

### Requirement 3: Order Details in Booking Overview

**User Story:** As a club president, I want to see complete order details in my booking overview, so that I can verify all booked items and costs before submitting.

#### Acceptance Criteria

1. THE Booking_Overview SHALL display for each item: the item label (name, size, direction as applicable), the product type group heading, the unit price, the quantity per group, and the line total per group.
2. THE Booking_Overview SHALL display a summary section with grand total, total paid, and remaining balance.
3. WHEN the order status is "submitted" or "locked", THE Booking_Overview SHALL display the submission date.

### Requirement 4: Onboarding Page Search Functionality

**User Story:** As a new user without a club assignment, I want to search for my club on the start page, so that I can quickly find and select my club from a potentially long list.

#### Acceptance Criteria

1. THE Onboarding_Page SHALL display a search input field that filters the club list by club name.
2. WHEN the user types in the search field, THE Onboarding_Page SHALL filter the displayed clubs to show only those whose name contains the search text (case-insensitive).
3. WHEN no clubs match the search text, THE Onboarding_Page SHALL display a "no results" message.

### Requirement 5: Onboarding Page Branding and Logo Animation

**User Story:** As a user arriving at the Presmeet start page, I want to see the Presmeet logo and FH-DCE logo presented prominently, so that I recognize the official booking system.

#### Acceptance Criteria

1. THE Onboarding_Page SHALL display the Presmeet logo and the FH-DCE logo centered on the page at initial load with a large size (minimum 120px height).
2. WHEN the user scrolls down or after initial load animation completes, THE Onboarding_Page SHALL transition the logos to small versions (maximum 40px height) positioned at the top of the page.
3. THE Onboarding_Page SHALL use a smooth CSS transition (minimum 300ms duration) for the logo size change.

### Requirement 6: Fix Payment Registration 500 Error

**User Story:** As an admin, I want to register manual payments without errors, so that I can track offline bank transfers.

#### Acceptance Criteria

1. WHEN an admin submits a manual payment registration, THE Admin_Payment_Handler SHALL validate the request payload (order_id, amount, date, description) and return a 400 error with a descriptive message for invalid input.
2. WHEN the request payload is valid, THE Admin_Payment_Handler SHALL create a payment record in the Payments table and update the order's payment_status accordingly.
3. IF the Admin_Payment_Handler encounters a DynamoDB error during payment registration, THEN THE Admin_Payment_Handler SHALL return a 500 error with a structured error message and log the exception details.

### Requirement 7: Correct Delegate Party Ticket Calculation in Presmeet Modal

**User Story:** As a club president, I want the booking modal to correctly include party tickets for my delegates, so that the order total reflects the actual cost.

#### Acceptance Criteria

1. WHEN a delegate has `attend_party` set to true, THE Presmeet_Modal SHALL generate a party_ticket cart item with the delegate's name in the attributes and the configured party_ticket unit price.
2. THE Order_Calculator SHALL include all delegate party_ticket items in the order total calculation.
3. THE Presmeet_Modal SHALL display the correct item count and total including delegate party tickets in the order summary within the modal.

### Requirement 8: Correct Airport Transfer Quantity Handling

**User Story:** As a club president, I want the system to correctly use the number of persons I specify for airport transfers, so that I am charged for the correct number of transfer seats.

#### Acceptance Criteria

1. WHEN the user specifies a number of persons for an airport transfer, THE Presmeet_System SHALL store the specified persons value in the cart item attributes.
2. THE Order_Calculator SHALL multiply the airport_transfer unit price by the persons attribute value for each transfer item to compute the line total.
3. WHEN a transfer has persons greater than 1, THE Booking_Overview SHALL display the persons count and the computed line total (persons × unit price).

### Requirement 9: Party Ticket Guest Name Validation

**User Story:** As a club president, I want the system to require a name for each party ticket, so that event organizers know who is attending.

#### Acceptance Criteria

1. WHEN a party_ticket cart item has an empty or missing name attribute, THE Presmeet_System SHALL display a validation error indicating that a name is required.
2. THE Order_Calculator SHALL reject order submission (return validation errors) for any party_ticket item without a name attribute.

### Requirement 10: Presmeet Order Visibility in Cart

**User Story:** As a club president, I want to see my presmeet order reflected in the webshop cart, so that I can proceed to checkout through the normal webshop flow.

#### Acceptance Criteria

1. WHEN a presmeet order is created or updated in the Presmeet_Modal, THE Cart_System SHALL create or update corresponding cart items in the Carts table with source "presmeet".
2. WHEN the user navigates to the webshop cart, THE Cart_System SHALL display presmeet items alongside regular webshop items with appropriate grouping.
3. THE Cart_System SHALL prevent editing of presmeet items from the webshop cart (read-only display with link back to presmeet modal).

### Requirement 11: Fix Webshop Checkout Order Placement for Presmeet Products

**User Story:** As a club president, I want to place an order for presmeet products through the webshop checkout without errors, so that my booking is confirmed and payment can proceed.

#### Acceptance Criteria

1. WHEN the user places an order containing presmeet products via Webshop_Checkout, THE Webshop_Checkout SHALL serialize the order payload correctly (items as array, not null) and submit it to the create_order endpoint.
2. WHEN the create_order endpoint receives presmeet items, THE Webshop_Checkout SHALL handle the response without TypeError by validating the response structure before accessing array methods.
3. IF the order placement request fails with a network error, THEN THE Webshop_Checkout SHALL display a user-friendly error message and retain the cart contents.

### Requirement 12: Migrate Presmeet Products to New Data Model

**User Story:** As a developer, I want presmeet products migrated to the new product data model, so that the presmeet modal works consistently with the updated webshop product schema.

#### Acceptance Criteria

1. THE Presmeet_System SHALL read product configurations from Producten table items that use the new product data model schema (with product_type, variants, and purchase_rules fields).
2. THE Presmeet_Modal SHALL continue to function correctly after the product data model migration, mapping new schema fields to the existing booking form interface.
3. WHEN legacy `source: "presmeet_config"` items exist alongside new model items, THE Presmeet_System SHALL prefer the new model items and ignore legacy items.

### Requirement 13: Admin Dashboard Data Visibility Fix

**User Story:** As an admin viewing booking details, I want the admin data section to be readable and follow the standard presentation, so that I can review booking information efficiently.

#### Acceptance Criteria

1. THE Admin_Dashboard SHALL render text in the admin data section with sufficient color contrast (minimum WCAG AA ratio of 4.5:1 against the background).
2. THE Admin_Dashboard SHALL apply the standard presentation definition (consistent spacing, font sizes, and layout) to the admin data section matching other admin views.

### Requirement 14: Product Modal UI Fixes in Webshopbeheer

**User Story:** As a webshop admin, I want the product modal variant schema and purchase rules to be readable and functional, so that I can configure products correctly.

#### Acceptance Criteria

1. THE Product_Modal SHALL render variant schema text with sufficient color contrast (minimum WCAG AA ratio of 4.5:1 against the background).
2. THE Product_Modal SHALL render purchase rules (aankoopregels) text with sufficient color contrast (minimum WCAG AA ratio of 4.5:1 against the background).
3. WHEN the purchase rules dropdown is displayed, THE Product_Modal SHALL populate the dropdown options from the product configuration data (not hardcoded empty content).

### Requirement 15: Event Administration Permissions for Webmaster

**User Story:** As the webmaster (webmaster@h-dcn.nl), I want to have event administration permissions, so that I can manage club events.

#### Acceptance Criteria

1. WHEN the webmaster user accesses the event administration module, THE Event_Admin SHALL grant access based on the Events_Read, Events_Export, and Events_CRUD permissions.
2. THE Presmeet_System SHALL assign Events_Read, Events_Export, and Events_CRUD permissions to the webmaster role in the Cognito user pool groups.
