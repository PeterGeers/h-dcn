# Requirements Document

## Introduction

This feature improves the H-DCN webshop order pipeline across five areas: (1) separating order status from payment status into proper state machines, (2) introducing human-readable order numbers alongside internal UUIDs, (3) generating sequential gapless invoice numbers upon payment confirmation for VAT compliance, (4) ensuring admin product creation writes correct data formats for the frontend, and (5) verifying that PresMeet purchase rules and order item fields work correctly end-to-end. These improvements fix the current mock payment behavior (which incorrectly marks bank transfer orders as "paid" immediately) and provide a better user experience with recognizable order references and legally compliant invoicing.

## Glossary

- **Order_Pipeline**: The backend system managing order lifecycle from draft creation through payment and completion, implemented as AWS Lambda handlers (`create_order`, `update_order_items`, `submit_order`, `pay_order`)
- **Order_Status**: The lifecycle state of an order record, independent of payment. Valid values: `draft`, `submitted`, `confirmed`, `completed`, `cancelled`
- **Payment_Status**: The payment state of an order record, independent of order lifecycle. Valid values: `unpaid`, `pending`, `paid`, `awaiting_payment`
- **Order_Number_Generator**: A service that produces human-readable order numbers in format `H-YYMMDD-NNN` using a DynamoDB atomic counter for daily sequencing
- **Invoice_Number_Generator**: A service that produces sequential invoice numbers in format `F-YYYY-NNNN` using a DynamoDB atomic counter per calendar year, assigned only on payment confirmation
- **Orders_Table**: The DynamoDB table storing order records (PK: `order_id`)
- **Producten_Table**: The DynamoDB table storing product and variant records (PK: `product_id`)
- **Counter_Table**: A DynamoDB table (or item within Orders_Table) storing the daily atomic counter for order number generation
- **Admin_Product_Creator**: The backend handler (`admin_create_product`) that persists new products to the Producten_Table
- **Variant_Record**: A child product record with `parent_id`, `variant_attributes`, `price`, `stock`, and `allow_oversell` fields
- **Purchase_Rules**: Business constraints on product purchasing defined per product (`max_per_order`, `max_per_member`, `max_per_club`, `requires_membership`)
- **Order_Item_Fields**: Per-item data collection fields defined on a product and filled by the buyer at checkout
- **PurchaseRulesFeedback_Component**: The existing React component that displays purchase rule validation messages to the buyer
- **ItemFieldsForm_Component**: The existing React component that collects per-item field data from the buyer
- **Mollie**: The payment service provider used for online (iDEAL, credit card) and bank transfer payments
- **Frontend_App**: The React 18 + TypeScript + Chakra UI single-page application at `portal.h-dcn.nl`

## Requirements

### Requirement 1: Order Status State Machine

**User Story:** As a webshop administrator, I want order status to track the order lifecycle independently from payment, so that I can see which orders are confirmed and which are still being processed regardless of payment method.

#### Acceptance Criteria

1. WHEN a new order is created, THE Order_Pipeline SHALL set `status` to `draft` and `payment_status` to `unpaid`
2. WHEN a draft order is submitted via the submit endpoint, THE Order_Pipeline SHALL transition `status` from `draft` to `submitted`
3. WHEN a submitted order receives a successful online payment confirmation (iDEAL or credit card), THE Order_Pipeline SHALL transition `status` from `submitted` to `confirmed` and `payment_status` from `pending` to `paid`
4. WHEN a submitted order with bank transfer method receives payment confirmation, THE Order_Pipeline SHALL transition `status` from `submitted` to `confirmed` and `payment_status` from `awaiting_payment` to `paid`
5. WHEN an admin marks a confirmed order as fulfilled, THE Order_Pipeline SHALL transition `status` from `confirmed` to `completed`
6. WHEN an admin cancels an order that is in `draft` or `submitted` status, THE Order_Pipeline SHALL transition `status` to `cancelled`
7. THE Order_Pipeline SHALL reject any status transition that does not follow the allowed paths: `draft` → `submitted` → `confirmed` → `completed`, or `draft`/`submitted` → `cancelled`
8. IF a webhook reports a failed payment for a submitted order, THEN THE Order_Pipeline SHALL keep `status` as `submitted` and set `payment_status` to `unpaid`

### Requirement 2: Payment Status State Machine

**User Story:** As a webshop administrator, I want payment status to accurately reflect whether money has been received, so that I can track outstanding bank transfers separately from confirmed online payments.

#### Acceptance Criteria

1. WHEN a submitted order initiates an online payment (Mollie (iDEAL or credit card) bank transfer), THE Order_Pipeline SHALL transition `payment_status` from `unpaid` to `pending`
2. WHEN a submitted order selects bank transfer as payment method, THE Order_Pipeline SHALL transition `payment_status` from `unpaid` to `awaiting_payment`
3. WHEN a Mollie webhook confirms an online payment is successful, THE Order_Pipeline SHALL transition `payment_status` from `pending` to `paid`
4. WHEN an admin confirms receipt of a bank transfer, THE Order_Pipeline SHALL transition `payment_status` from `awaiting_payment` to `paid`
5. THE Order_Pipeline SHALL reject any `payment_status` transition that does not follow the allowed paths: `unpaid` → `pending` → `paid` (online), or `unpaid` → `awaiting_payment` → `paid` (bank transfer)
6. THE Order_Pipeline SHALL NOT mark an order as `paid` in mock payment mode when the payment method is `bank_transfer`

### Requirement 3: Human-Readable Order Numbers

**User Story:** As a webshop customer, I want to see a short recognizable order number instead of a UUID, so that I can easily reference my order in communication and bank transfers.

#### Acceptance Criteria

1. WHEN a draft order transitions to `submitted`, THE Order_Number_Generator SHALL assign a unique `order_number` in format `H-YYMMDD-NNN` where `YY` is two-digit year, `MM` is two-digit month, `DD` is two-digit day, and `NNN` is a zero-padded daily sequence starting at 001
2. THE Order_Number_Generator SHALL use a DynamoDB atomic counter (UpdateItem with ADD operation) to guarantee unique sequential numbers per day without race conditions
3. THE Order_Pipeline SHALL store the generated `order_number` as a new attribute on the order record alongside the existing `order_id` (UUID) primary key
4. THE Frontend_App SHALL display the `order_number` on the order confirmation screen after successful submission
5. THE Frontend_App SHALL include the `order_number` in the generated order confirmation PDF
6. THE Frontend_App SHALL display the `order_number` in the admin order list (OrdersAdmin component)
7. WHEN a bank transfer payment is initiated, THE Order_Pipeline SHALL use the `order_number` as the `reference` field in `transfer_instructions` returned to the frontend
8. THE Order_Pipeline SHALL include the `order_number` in email notifications sent to the customer

### Requirement 4: Admin Product Data Consistency

**User Story:** As a webshop administrator, I want product creation and variant management to keep variant_schema and variant records in sync bidirectionally, so that I can edit either the schema or individual variants and the system stays consistent.

#### Acceptance Criteria

1. WHEN an admin creates a parent product with variant axes via the schema editor, THE Admin_Product_Creator SHALL store `variant_schema` in Record format (e.g., `{"Maat": ["S", "M", "L"]}`) and auto-generate one variant record per value combination
2. WHEN an admin updates the `variant_schema` on an existing product (top-down), THE system SHALL regenerate variant records to match the new schema, preserving stock and price on unchanged variants and creating new records for added values
3. WHEN an admin adds a variant record directly to a product (bottom-up), THE system SHALL update the parent's `variant_schema` to include the new variant's attribute values
4. WHEN an admin removes a variant record directly from a product (bottom-up), THE system SHALL update the parent's `variant_schema` to remove attribute values that no longer have corresponding variant records
5. THE admin product management UI SHALL support both editing flows: editing the schema (which regenerates variants) and editing individual variants (which updates the schema)
6. WHEN an admin creates a parent product, THE Admin_Product_Creator SHALL store a numeric `price` field, set `is_parent` to `true`, and set `active` to `true` on the product record
7. WHEN variant records are auto-generated, THE system SHALL store each variant with `parent_id` referencing the parent `product_id`, a `variant_attributes` map, a numeric `price` (inherited from parent unless overridden), `stock` defaulting to `0`, and `allow_oversell` defaulting to `true`
8. IF a product record in the Producten_Table has a `prijs` field but no `price` field, THEN THE Order_Pipeline SHALL read from `prijs` as a fallback when calculating order totals

### Requirement 5: Purchase Rules Enforcement

**User Story:** As a webshop customer, I want the system to enforce product purchase limits at the point of adding to cart and at checkout, so that I receive immediate feedback when a constraint would be violated.

#### Acceptance Criteria

1. WHEN a buyer attempts to add more than `purchase_rules.max_per_order` units of a product to a single order, THE Frontend_App SHALL prevent the addition and display a message via the PurchaseRulesFeedback_Component
2. WHEN a buyer attempts to purchase a product with `purchase_rules.max_per_member` set, THE Frontend_App SHALL check the member's existing paid and pending orders for that product and block the purchase if the total would exceed the limit
3. WHEN a buyer attempts to purchase a product with `purchase_rules.max_per_club` set, THE Frontend_App SHALL check the club's total orders for that product and block the purchase if the total would exceed the limit
4. WHEN a product has `purchase_rules.requires_membership` set to `true`, THE Frontend_App SHALL block non-members from adding the product to cart and display an appropriate message
5. WHEN the submit endpoint validates an order, THE Order_Pipeline SHALL re-check all `purchase_rules` constraints server-side and reject the submission with a descriptive error if any constraint is violated

### Requirement 6: Per-Item Data Collection

**User Story:** As a webshop customer purchasing event tickets, I want to fill in per-item data (such as participant names and roles) during checkout, so that the organizer receives the required information for each ticket.

#### Acceptance Criteria

1. WHEN a product has `order_item_fields` defined, THE Frontend_App SHALL render the ItemFieldsForm_Component for each quantity unit in the cart
2. WHEN the buyer submits an order containing items with `order_item_fields`, THE Frontend_App SHALL include the `item_fields_data` array in the submit request
3. WHEN the submit endpoint receives an order with `order_item_fields` products, THE Order_Pipeline SHALL validate that all required fields have non-empty values for each item unit
4. IF a required field in `order_item_fields` is missing or empty for any item unit, THEN THE Order_Pipeline SHALL reject the submission with an error identifying the item index, field ID, and validation message
5. THE Order_Pipeline SHALL persist validated `item_fields_data` on the order items in the Orders_Table
6. WHEN per-item data collection is used within the PresMeet booking flow (event-linked products), THE system SHALL use the same `order_item_fields` mechanism and ItemFieldsForm_Component as the general webshop, ensuring a single shared implementation for both flows
7. WHEN an admin defines `order_item_fields` on a product via the product management UI, THE admin UI SHALL support all field types (text, select, date, number, email) with validation configuration (min/max, required, options for select)

### Requirement 7: Invoice Number Generation

**User Story:** As a VAT-registered nonprofit, I want sequential invoice numbers assigned only when payment is confirmed, so that I maintain a legally compliant gapless invoice register for the Belastingdienst.

#### Acceptance Criteria

1. WHEN an order's `payment_status` transitions to `paid`, THE Invoice_Number_Generator SHALL assign a unique `invoice_number` in format `F-YYYY-NNNN` where `YYYY` is the four-digit calendar year and `NNNN` is a zero-padded yearly sequence starting at 0001
2. THE Invoice_Number_Generator SHALL use a DynamoDB atomic counter (UpdateItem with ADD operation) keyed by calendar year to guarantee sequential gapless numbering
3. THE Order_Pipeline SHALL store the generated `invoice_number` as a new attribute on the order record
4. THE Order_Pipeline SHALL NOT assign an `invoice_number` to orders that are cancelled, unpaid, or still awaiting payment
5. THE Frontend_App SHALL generate a separate invoice PDF (factuur) containing the `invoice_number`, BTW-nummer of H-DCN, itemized amounts including VAT, and customer details
6. THE Frontend_App SHALL display the `invoice_number` in the admin order detail view alongside the `order_number`
7. THE Invoice PDF SHALL be distinct from the order confirmation PDF — the order confirmation uses `order_number` and is shown at submission, the invoice uses `invoice_number` and is available only after payment
8. WHEN an admin views orders in the admin panel, THE Frontend_App SHALL indicate which orders have an invoice generated (have `invoice_number`) versus which are still awaiting payment

### Requirement 8: Product Lifecycle and Soft Delete

**User Story:** As a webshop administrator, I want to deactivate discontinued products using the existing `active` field, so that they disappear from the webshop without losing order history.

#### Acceptance Criteria

1. WHEN an admin sets `active` to `false` on a product, THE webshop SHALL hide it from the customer-facing product listing
2. WHEN an admin attempts to hard-delete a product that has existing paid or pending orders referencing it, THE system SHALL reject the deletion and display an error explaining that the product has order history
3. WHEN an admin sets `active` to `false` on a product that has pending (unpaid/submitted) orders, THE admin UI SHALL display a warning before allowing the change
4. THE admin product management UI SHALL provide a filter toggle to show/hide inactive products (`active: false`), defaulting to showing only active products
5. WHEN an order or invoice references a product that has since been set to `active: false`, THE system SHALL still display the product name and details correctly in order history and invoice PDFs
6. THE system SHALL allow hard-deletion only for products that have never been sold (no orders with `status` other than `cancelled` reference the product)
