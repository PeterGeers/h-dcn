# Requirements Document

## Introduction

This feature unifies the H-DCN webshop and PresMeet booking systems into a single product/order pipeline. The current architecture has two problems: (1) the webshop cart references products by `product_id` + a flat `selectedOption` text string instead of an actual variant record, making stock management unreliable, and (2) PresMeet runs a completely separate cart/order/payment flow despite sharing the same DynamoDB tables and admin tooling.

The solution splits the overloaded `required_attributes` field into three explicit concerns — variant dimensions (`variant_schema`), per-item data collection (`order_item_fields`), and business rule constraints (`purchase_rules`) — and updates the customer-facing webshop to reference variant records directly, collect per-item registration data at checkout, and enforce purchase rules.

## Glossary

- **Webshop**: The customer-facing product catalog and shopping experience at the H-DCN portal
- **Cart**: A shopping cart stored in the Carts DynamoDB table, owned by a single authenticated user
- **Cart_Item**: A single line item in a cart referencing a product and its variant
- **Variant**: A child record in the Producten table representing a specific purchasable SKU with its own stock level
- **Default_Variant**: A variant with empty `variant_attributes` auto-created for simple products without variant axes
- **Parent_Product**: A parent record in the Producten table containing catalog data, configuration, and pricing
- **Variant_Schema**: A product field defining the axes (dimensions) that generate separate SKUs with independent stock
- **Order_Item_Fields**: A product field defining per-item data collection fields the buyer fills in at checkout
- **Purchase_Rules**: A product field defining business constraints on purchasing (quantity limits, membership requirements)
- **Item_Fields_Data**: The actual data collected per order item at checkout, stored on the order record
- **PresMeet**: The FH-DCE Presidents' Meeting booking system, currently a separate flow
- **Opties**: The legacy comma-separated string field on old products (e.g., "S,M,L,XL") used before the variant model
- **Producten_Table**: The DynamoDB table storing both parent products and variant records
- **Stock_Reservation**: The process of decrementing variant stock and incrementing sold_count when an order is paid
- **Tenant**: A field distinguishing product/order ownership (values: "h-dcn", "presmeet")
- **Groep**: A product categorization field for top-level filtering in the webshop (e.g., "Kleding", "Accessoires")
- **Subgroep**: A product sub-categorization field for second-level filtering (e.g., "T-shirts", "Hoodies")
- **Mollie**: The payment service provider used for processing online payments (iDEAL, credit card)

## Requirements

### Requirement 1: Split Product Configuration Into Three Concerns

**User Story:** As an admin, I want product configuration separated into variant dimensions, per-item data collection, and purchase rules, so that each concern is independently configurable without ambiguity.

#### Acceptance Criteria

1. THE Parent_Product SHALL store a `variant_schema` field defining axes that generate separate SKUs with independent stock tracking
2. THE Parent_Product SHALL store an `order_item_fields` field defining per-item data the buyer fills in at checkout
3. THE Parent_Product SHALL store a `purchase_rules` field defining business constraints on purchasing
4. WHEN a Parent_Product has a `variant_schema` field that is present and non-empty (contains at least one axis), THE Webshop SHALL use the schema exclusively for variant generation and stock tracking
5. WHEN a Parent_Product has an `order_item_fields` field that is present and non-empty (contains at least one field definition), THE Webshop SHALL use the fields exclusively for per-item data collection at checkout
6. WHEN a Parent_Product has a `purchase_rules` field that is present and non-empty (contains at least one constraint), THE Webshop SHALL use the rules exclusively for enforcing purchase constraints
7. THE Parent_Product SHALL support having any combination of the three fields (all, some, or none), yielding up to 8 valid configurations
8. IF a Parent_Product has a legacy `required_attributes` field present alongside any of the three new fields, THEN THE Webshop SHALL ignore `required_attributes` and use only `variant_schema`, `order_item_fields`, and `purchase_rules` for their respective concerns

### Requirement 2: Preserve Product Categorization and Media Fields

**User Story:** As a buyer, I want to filter products by group and subgroup and see product images so that I can find and evaluate products in the webshop catalog.

#### Acceptance Criteria

1. THE Parent_Product SHALL retain the existing `groep` and `subgroep` fields as optional string fields (maximum 50 characters each) for catalog categorization and filtering
2. THE Webshop product filter SHALL continue to use `groep` and `subgroep` for hierarchical filtering (group → subgroup), dynamically building the filter options from the set of distinct values present on active products
3. WHEN a product has no `groep` value, THE Webshop SHALL include it in the unfiltered product list but exclude it from group-based filter results
4. THE Parent_Product SHALL retain the existing `images` field (array of up to 10 S3 URLs) for product media at the parent level
5. THE Webshop ProductCard SHALL display product images from the parent product record with carousel navigation allowing the buyer to cycle through all images
6. IF a product has no images or all image URLs fail to load, THEN THE Webshop ProductCard SHALL display a placeholder image instead of broken content
7. WHEN an admin creates or edits a product, THE Admin_UI SHALL include optional fields for `groep` and `subgroep` (selectable from existing values or free-text entry) and an image upload control alongside the new configuration fields
8. THE `groep`, `subgroep`, and `images` fields SHALL be independent of `variant_schema`, `order_item_fields`, and `purchase_rules` — they serve catalog presentation, not product configuration

### Requirement 3: Variant Schema Definition

**User Story:** As an admin, I want to define variant axes on a product so that separate SKUs are generated with independent stock per combination.

#### Acceptance Criteria

1. THE Variant_Schema field SHALL accept an object where each key is an axis name (a non-empty string of 1 to 50 characters) and each value is a non-empty array of allowed string values (each 1 to 100 characters) for that axis, supporting a maximum of 5 axes with a maximum of 20 values per axis
2. WHEN an admin saves a Parent_Product with a Variant_Schema, THE Admin_System SHALL generate exactly C₁ × C₂ × ... × Cₙ variant records (one per combination), up to a maximum of 100 variant records per parent product
3. WHEN a variant is generated from a Variant_Schema, THE Variant record SHALL contain a `variant_attributes` object mapping each axis name to its selected value, with stock initialized to 0
4. THE Variant_Schema SHALL accept any admin-defined axis name as a key (e.g., size, gender, color, or any custom label), provided it meets the character length constraint and is unique within the schema
5. WHEN a Parent_Product has no Variant_Schema defined, THE Admin_System SHALL create a single Default_Variant with empty `variant_attributes` at product creation time
6. IF a Variant_Schema contains duplicate values within a single axis or an axis with an empty values array, THEN THE Admin_System SHALL reject the schema with a validation error indicating the specific axis that failed
7. IF an admin updates a Variant_Schema on a product that already has generated variants, THEN THE Admin_System SHALL remove existing variants and regenerate all variants from the updated schema, resetting stock to 0 for new combinations
8. IF the total number of combinations (C₁ × C₂ × ... × Cₙ) exceeds 100, THEN THE Admin_System SHALL reject the schema with an error indicating the maximum allowed variant count

### Requirement 4: Order Item Fields Definition

**User Story:** As an admin, I want to define per-item registration fields on a product so that buyers provide required data for each item at checkout.

#### Acceptance Criteria

1. THE Order_Item_Fields field SHALL accept an array of up to 20 field definitions, where each definition contains an id (unique within the array, alphanumeric with underscores, max 50 characters), a label (max 200 characters), a type, and a required boolean flag
2. THE Order_Item_Fields field SHALL support exactly these field types: text, select (with an options array of 1 to 50 string values), date, number, and email
3. IF a field definition has `required` set to true, THEN THE Checkout_System SHALL prevent order submission until the field value is non-empty for every item quantity, where non-empty means: for text and email, a trimmed string of at least 1 character; for select, a value matching one of the defined options; for number, a numeric value is present; for date, a valid date value is present
4. WHEN a Parent_Product has Order_Item_Fields defined with Q items of that product in the cart, THE Checkout_System SHALL collect field data for each of the Q items independently
5. THE Order_Item_Fields field SHALL support a `validation` property on each field for the following constraints: min_length and max_length (for text and email types, integers from 1 to 1000), minimum and maximum (for number type), and pattern (a regex string of max 500 characters, for text and email types)
6. IF a field definition contains a duplicate id within the same Order_Item_Fields array or a select type field has an empty options array, THEN THE Admin_System SHALL reject the product save and display a validation error indicating the specific field definition issue

### Requirement 5: Purchase Rules Definition

**User Story:** As an admin, I want to define purchase constraints on a product so that business rules are enforced during checkout.

#### Acceptance Criteria

1. THE Purchase_Rules field SHALL support a `max_per_order` constraint as a positive integer (1 to 9999) limiting the quantity of a product per single order
2. THE Purchase_Rules field SHALL support a `max_per_member` constraint as a positive integer (1 to 9999) limiting the total quantity a member can purchase across all orders with status "paid" or "pending"
3. THE Purchase_Rules field SHALL support a `max_per_club` constraint as a positive integer (1 to 9999) limiting the total quantity a club can purchase across all orders with status "paid" or "pending" (used for PresMeet-style per-club ordering)
4. THE Purchase_Rules field SHALL support a `min_per_club` constraint as a positive integer (1 to 9999) defining the minimum quantity a club must order (used for PresMeet-style per-club ordering), and the value SHALL NOT exceed the `max_per_club` value when both are defined
5. THE Purchase_Rules field SHALL support a `requires_membership` boolean constraint restricting purchase to members with a membership record that has status "active" in the Members table
6. WHEN a Purchase_Rules constraint is absent or null, THE Webshop SHALL treat that constraint as not applicable (no limit enforced for that rule)
7. WHEN a buyer attempts to add more items than `max_per_order` allows, THE Webshop SHALL reject the addition and display a message indicating the maximum allowed quantity per order
8. WHEN a buyer has previously purchased items and adding more would exceed `max_per_member`, THE Webshop SHALL reject the addition and display the remaining allowed quantity based on the buyer's existing orders with status "paid" or "pending"
9. WHEN a club's total purchased quantity for a product would exceed `max_per_club`, THE Webshop SHALL reject the addition and display the remaining allowed quantity for that club based on existing orders with status "paid" or "pending"
10. IF `requires_membership` is true and the buyer does not have a membership record with status "active", THEN THE Webshop SHALL prevent the product from being added to the cart and display a message indicating that an active membership is required
11. THE Purchase_Rules SHALL be enforced at the product level (across all variants of the same Parent_Product) and validated both in the frontend (for user experience) and in the backend create_order handler (for enforcement)
12. IF the backend create_order handler detects a Purchase_Rules violation that the frontend did not catch (due to concurrent orders or stale data), THEN THE Backend SHALL reject the order and return an error identifying the violated rule and the current allowed quantity

### Requirement 6: Cart References Variant Records

**User Story:** As a buyer, I want my cart items to reference actual variant records so that stock is accurately tracked and decremented when I complete a purchase.

#### Acceptance Criteria

1. WHEN a buyer adds a product to the cart, THE Cart_Item SHALL store `product_id` (parent reference), `variant_id` (variant reference), and `quantity` (number of units, minimum 1)
2. IF a product has a Variant_Schema, THEN THE Webshop SHALL require the buyer to select values for all axes before enabling the add-to-cart action
3. IF a product has no Variant_Schema, THEN THE Cart_Item SHALL reference the Default_Variant automatically without requiring buyer selection
4. THE Cart_Item SHALL store `variant_attributes` as a Record of axis name to selected value for display purposes
5. THE Cart_Item SHALL NOT store a flat `selectedOption` text string as the variant identifier
6. WHEN an order is paid, THE Stock_Reservation process SHALL decrement `stock` and increment `sold_count` on the variant record identified by `variant_id` by the ordered quantity
7. IF a variant has `allow_oversell` set to false and `stock` on the variant record is less than the requested quantity, THEN THE Webshop SHALL prevent the item from being added to the cart and display a message indicating the available stock quantity
8. WHEN the create_order handler processes an order, THE Backend SHALL re-validate stock availability for each line item against the variant's current `stock` value and reject the order if any variant with `allow_oversell` false has insufficient stock

### Requirement 7: Tenant-Based Product Visibility

**User Story:** As a buyer, I want to see only the products I have access to based on my roles so that the webshop shows relevant products for my membership.

#### Acceptance Criteria

1. WHEN a user with role `hdcnLeden` and without role `Regio_Pressmeet` or `Regio_All` enters the Webshop, THE Webshop SHALL display only products with tenant "h-dcn"
2. WHEN a user with role `Regio_Pressmeet` or `Regio_All` and without role `hdcnLeden` enters the Webshop, THE Webshop SHALL display only products with tenant "presmeet"
3. WHEN a user has both `hdcnLeden` and `Regio_Pressmeet` (or `Regio_All`), THE Webshop SHALL display products from both tenants ("h-dcn" and "presmeet")
4. IF a user has neither `hdcnLeden` nor `Regio_Pressmeet` nor `Regio_All`, THEN THE Webshop SHALL display no products and show a message indicating the user has no product access
5. THE product listing API SHALL accept a `tenant` query parameter containing one or more comma-separated tenant values and return only products matching those tenants
6. IF a user requests a tenant value that their roles do not grant access to, THEN THE Backend SHALL return a 403 response with an error indicating insufficient tenant access
7. THE Backend SHALL derive the user's accessible tenants from the Cognito group claims (`hdcnLeden` grants "h-dcn"; `Regio_Pressmeet` or `Regio_All` grants "presmeet") and validate the requested tenant parameter against them before returning products

### Requirement 8: Per-Item Data Collection at Checkout

**User Story:** As a buyer, I want to fill in registration data for each item I purchase (e.g., attendee name and role per ticket) so that the organizer has the information needed.

#### Acceptance Criteria

1. WHEN a cart contains items with Order_Item_Fields defined, THE Webshop SHALL display the configured fields for each item quantity in both the cart view and checkout flow, with each set of fields labelled by a sequential item number (e.g., "Item 1 of 3", "Item 2 of 3")
2. WHEN a buyer has 3 units of a product with Order_Item_Fields, THE Webshop SHALL display 3 independent sets of fields, each accepting input without affecting the other sets
3. WHEN a buyer saves the cart (before checkout submission), THE Cart SHALL persist any partially or fully filled Item_Fields_Data so that the buyer can return later and continue filling in the data
4. WHEN the buyer attempts to submit an order, THE Checkout_System SHALL validate all required fields and field-level constraints (min_length, max_length, minimum, maximum, pattern as defined in Order_Item_Fields) before allowing order submission
5. IF a required field is empty or a field value violates its validation constraints at submission time, THEN THE Checkout_System SHALL display an error message identifying the specific item number, field label, and nature of the violation, and prevent submission
6. WHEN an order is successfully submitted, THE Checkout_System SHALL store the collected Item_Fields_Data on the order record, associated with the specific Cart_Item and preserving the per-item-unit grouping
7. WHILE the buyer is filling in Item_Fields_Data in the cart view, THE Webshop SHALL allow saving with incomplete data (validation only enforced at order submission)
8. WHEN a buyer decreases the quantity of a cart item that has Item_Fields_Data filled, THE Webshop SHALL remove Item_Fields_Data sets from the highest-numbered items (last in, first removed) and retain the data for the remaining lower-numbered items
9. IF the Order_Item_Fields definition on a product changes while Item_Fields_Data already exists in a buyer's cart, THEN THE Webshop SHALL discard any saved field values whose field id no longer exists in the current definition and display the updated fields on next cart load

### Requirement 9: Unified Payment via Mollie

**User Story:** As a buyer, I want to pay for my order using Mollie or bank transfer so that I can choose the payment method that suits me.

#### Acceptance Criteria

1. THE Checkout_System SHALL use Mollie as the payment provider for online payments for both H-DCN and PresMeet orders (replacing the current Stripe integration for H-DCN)
2. THE Checkout_System SHALL support iDEAL and credit card as Mollie-processed payment methods
3. THE Checkout_System SHALL support bank transfer as a manual payment method where the order is created with payment_status "unpaid" and the buyer receives transfer instructions containing the order reference number and the club bank account IBAN
4. WHEN a buyer selects bank transfer, THE Backend SHALL create the order with payment_status "unpaid" without triggering Stock_Reservation (stock is reserved only when the admin records payment)
5. WHEN a buyer selects a Mollie-processed payment method, THE Backend SHALL create the order with payment_status "pending" and redirect the buyer to the Mollie-hosted payment page
6. WHEN a Mollie payment webhook confirms a successful payment, THE Backend SHALL update the order's payment_status to "paid" and trigger Stock_Reservation
7. WHEN a Mollie payment webhook reports a status of "failed", "expired", or "cancelled", THE Backend SHALL update the order's payment_status to "payment_failed" without reserving stock
8. WHEN the buyer returns from the Mollie payment page after a successful payment, THE Checkout_System SHALL display a confirmation message with the order reference
9. WHEN the buyer returns from the Mollie payment page after a failed, expired, or cancelled payment, THE Checkout_System SHALL display a message indicating payment was not completed and offer the option to retry payment or choose a different payment method
10. WHEN an admin records a manual payment for a bank transfer order, THE Admin_System SHALL recalculate the order's payment_status based on total paid versus order total ("paid" if fully covered, "partial" if not) and trigger Stock_Reservation when payment_status becomes "paid"
11. THE Mollie webhook handler SHALL be idempotent: processing the same Mollie payment ID multiple times SHALL produce the same result without duplicating stock reservations

### Requirement 10: Order Storage of Per-Item Registration Data

**User Story:** As an admin, I want per-item registration data stored on the order so that I can view attendee details and export them for event planning.

#### Acceptance Criteria

1. WHEN an order is created with Item_Fields_Data, THE Orders_Table SHALL store the data as an array of field-value objects nested under each order line item, with each entry indexed by item sequence number (1 through Q for Q items of that product)
2. THE Admin_System SHALL display Item_Fields_Data in the order detail view for each line item, showing the field label and submitted value grouped per item index
3. WHEN an admin exports orders in JSON format, THE Admin_System SHALL include the full Item_Fields_Data array nested under each line item in the exported order objects
4. WHEN an admin exports orders in CSV format, THE Admin_System SHALL output one row per item-field combination, with columns for order_id, line item product, item index, field label, and submitted value
5. THE Item_Fields_Data structure SHALL preserve the field id, label, submitted value, and item index (1-based sequence number) for each entry
6. IF an order line item has no Order_Item_Fields defined on its product, THEN THE Orders_Table SHALL store that line item without an Item_Fields_Data property
7. WHEN an order is created, THE Item_Fields_Data stored on that order SHALL be immutable and SHALL NOT be modified after order creation

### Requirement 11: Migration From Legacy Opties Format

**User Story:** As a system operator, I want existing products using the flat `opties` string field migrated to the variant model so that all products use a single consistent data structure.

#### Acceptance Criteria

1. WHEN a legacy product has an `opties` field with comma-separated values, THE Migration_Script SHALL create a `variant_schema` with a single axis named "opties" containing those values parsed by splitting on comma and trimming whitespace from each value
2. WHEN a legacy product is migrated, THE Migration_Script SHALL generate one variant record for each parsed option value with stock set to zero and `allow_oversell` set to true, pending admin review of stock allocation
3. WHEN a legacy product is migrated, THE Migration_Script SHALL move the `opties` field value into a `legacy_opties` field on the parent record and remove the original `opties` field
4. THE Migration_Script SHALL detect already-migrated products by checking for the presence of a `legacy_opties` field or existing variant records with a matching `parent_id`, and skip those products without modification
5. THE Migration_Script SHALL log each migrated product with the product_id, original `opties` value, number of variants created, and timestamp to a structured audit output
6. WHEN legacy Cart_Items exist with a `selectedOption` text value matching a parsed option value from the parent product's `opties` field, THE Migration_Script SHALL replace the `selectedOption` field with the `variant_id` of the corresponding generated variant
7. IF a legacy Cart_Item has a `selectedOption` value that does not match any generated variant for its referenced product, THEN THE Migration_Script SHALL log the unmatched cart item (cart_id, product_id, selectedOption value) and leave the item unchanged for manual resolution

### Requirement 12: Unification of PresMeet and H-DCN Webshop

**User Story:** As a platform maintainer, I want PresMeet products to use the same product/cart/order pipeline as the H-DCN webshop so that there is a single unified system to maintain.

#### Acceptance Criteria

1. WHEN a PresMeet product is created, THE Admin_System SHALL store it as a regular Parent_Product in the Producten_Table with tenant "presmeet"
2. THE PresMeet product's `required_attributes` registration fields SHALL be migrated to the `order_item_fields` field, mapping each legacy attribute (name, role, flight, dietary requirements, phone) to a field definition with id, label, type, and required flag
3. THE PresMeet product's `max_per_club` and `min_per_club` constraints SHALL be migrated to the `purchase_rules` field
4. THE PresMeet product's variant dimensions (gender, size for t-shirts) SHALL be stored in the `variant_schema` field
5. WHEN a PresMeet buyer adds items to their cart, THE Cart SHALL use the same Carts_Table and Cart_Item structure as the H-DCN webshop, with the buyer's `club_id` (derived from their Cognito group membership) stored on the cart
6. WHEN a PresMeet order is submitted, THE Order SHALL be stored in the same Orders_Table with tenant "presmeet", source "presmeet", and the buyer's `club_id`
7. THE unified pipeline SHALL preserve PresMeet per-club ordering, the draft → submitted → locked status flow (as defined in the order state machine), and payment processing via Mollie
8. THE Purchase_Rules field SHALL support an `order_mode` property with values "single" (default, H-DCN style one-shot order) or "persistent" (PresMeet style reopenable order per club)
9. WHEN a product has `order_mode` "persistent", THE Webshop SHALL maintain a single order per club (identified by `club_id`) that can be reopened and modified until the admin transitions it to "locked" status
10. WHEN a persistent order in "locked" or "paid" status is reopened by the admin, THE System SHALL transition the order back to "submitted" status, allow adding or removing items, and upon re-submission create a supplementary Mollie payment for any positive difference in the order total
11. IF a persistent order is reopened and items are removed resulting in a lower total than already paid, THEN THE System SHALL record the overpayment as a credit on the order and NOT trigger an automatic refund
12. WHEN a product has `order_mode` "single", THE Webshop SHALL follow standard cart → checkout → order → done flow where each purchase creates a new order
13. IF two members of the same club attempt to modify a persistent order concurrently, THEN THE System SHALL use optimistic locking (version attribute) on the order record and reject the second write with an error indicating the order was modified

### Requirement 13: Admin UI Updates for New Product Fields

**User Story:** As an admin, I want the product management UI to support editing variant_schema, order_item_fields, and purchase_rules so that I can configure products without direct database access.

#### Acceptance Criteria

1. WHEN an admin creates or edits a product, THE Admin_UI SHALL display separate collapsible sections for Variant Schema, Order Item Fields, and Purchase Rules below the existing product fields (name, price, category, images)
2. THE Admin_UI SHALL provide a visual editor for Variant_Schema allowing the admin to add up to 5 axes, name each axis (1–50 characters), and define up to 30 allowed values per axis (each value 1–50 characters), with controls to add, reorder, and remove axes and values
3. THE Admin_UI SHALL provide a form builder for Order_Item_Fields allowing the admin to add up to 20 field definitions, and for each field set an id (auto-generated or manual, 1–50 characters, unique within the product), a label (1–100 characters), a type (text, select, date, number, or email), a required flag, and optional validation constraints (min_length, max_length, minimum, maximum, pattern)
4. THE Admin_UI SHALL provide form inputs for Purchase_Rules including max_per_order (integer, 1–999), max_per_member (integer, 1–999), max_per_club (integer, 1–9999), min_per_club (integer, 0–9999), requires_membership (boolean), and order_mode (select: "single" or "persistent")
5. WHEN an admin saves a product with an invalid configuration, THE Admin_UI SHALL display field-level validation errors and prevent saving, validating at minimum: axis names are non-empty and unique within the product, each axis has at least one value, axis values are non-empty and unique within their axis, order_item_field ids are unique within the product, select-type fields have at least one option defined, and numeric purchase_rules values are within their allowed ranges
6. WHILE a product record contains a non-empty `required_attributes` field, THE Admin_UI SHALL display the `required_attributes` field as read-only with a label indicating it is a legacy field pending migration
7. IF an admin attempts to add a Variant_Schema axis or Order_Item_Field that would exceed the maximum allowed count, THEN THE Admin_UI SHALL display an error indicating the limit has been reached and prevent the addition

### Requirement 14: Complete Migration of Legacy Data

**User Story:** As a system operator, I want all legacy product data migrated in a single pass so that the new unified model is the only active format.

#### Acceptance Criteria

1. THE Migration_Script SHALL convert all products with an `opties` field to the new variant model in a single execution and SHALL report the total number of products processed and the number successfully converted
2. WHEN the migration is complete, THE Webshop SHALL exclusively use `variant_id` references in cart items and the `opties` field SHALL no longer be read by any component
3. THE Migration*Script SHALL convert PresMeet config records (`config_presmeet*\*`) into regular Parent_Product records by mapping `required_attributes`fields with enum constraints to`variant_schema`axes, mapping remaining`required_attributes`fields (text, date, integer) to`order_item_fields`entries, and mapping`max_per_club`and`min_per_club`values to`purchase_rules`
4. WHEN the migration is complete, THE Legacy `required_attributes` field SHALL be preserved on the Parent_Product record as a read-only field that is not used for variant generation or data collection by any backend handler or frontend component
5. IF the Migration_Script encounters a product that cannot be converted (e.g., missing required data or conflicting field structure), THEN THE Migration_Script SHALL skip that product, log the product_id and failure reason, and continue processing the remaining products
6. WHEN the Migration_Script completes, THE Migration_Script SHALL output a summary report listing: total records processed, successfully migrated count, skipped count with reasons, so the operator can verify completeness before switching to the new model

### Requirement 15: Frontend Variant Selection Component

**User Story:** As a buyer, I want to select product options (size, gender, etc.) from the variant schema so that the correct variant is added to my cart with accurate stock information.

#### Acceptance Criteria

1. WHEN a product with Variant_Schema is displayed in the ProductCard modal, THE ProductCard SHALL render a selector for each axis defined in the schema (replacing the legacy opties-based dropdown)
2. WHILE the buyer has not selected values for all axes, THE ProductCard SHALL disable the add-to-cart button and not display stock information
3. WHEN the buyer selects values for all axes, THE Webshop SHALL resolve the matching variant record and display its available stock as a numeric quantity (e.g., "3 op voorraad")
4. IF the resolved variant has zero stock and `allow_oversell` is false, THEN THE Webshop SHALL disable the add-to-cart button and display an out-of-stock message
5. IF no variant record exists for the selected axis combination, THEN THE Webshop SHALL disable the add-to-cart button and display a message indicating the combination is unavailable
6. WHEN the buyer changes an axis selection, THE Webshop SHALL re-resolve the variant and update the stock display
7. THE Variant selection component SHALL display axis labels and option values in the language configured for the portal
8. THE CartModal SHALL display `variant_attributes` per item as a formatted list of axis-value pairs (e.g., "Maat: XL, Gender: Male") instead of the flat `selectedOption` string
9. WHEN a cart item has Order_Item_Fields associated with its product, THE CartModal SHALL display expandable per-item field forms below that cart line item

### Requirement 16: Purchase Rules Backend Enforcement

**User Story:** As a system operator, I want purchase rules enforced in the backend so that constraints cannot be bypassed by manipulating the frontend.

#### Acceptance Criteria

1. WHEN the create_order handler processes an order, THE Backend SHALL validate all Purchase_Rules for each line item before persisting the order
2. IF a line item quantity exceeds the product's `max_per_order` value, THEN THE Backend SHALL reject the order with an error identifying the violated constraint, the product_id, and the maximum allowed quantity
3. IF a member's total purchased quantity for a product across existing orders with status "paid" or "pending" plus the current order quantity exceeds `max_per_member`, THEN THE Backend SHALL reject the order with an error showing the remaining allowed quantity
4. IF a club's total purchased quantity for a product across existing orders with status "paid" or "pending" plus the current order quantity exceeds `max_per_club`, THEN THE Backend SHALL reject the order with an error showing the remaining allowed quantity for that club
5. IF `requires_membership` is true and the buyer does not have a membership record in the Memberships table with a status of "active" and a non-expired end date, THEN THE Backend SHALL reject the order with an error indicating the membership requirement
6. IF any Purchase_Rule validation fails, THEN THE Backend SHALL return a 400 response with structured error details including the rule name, product_id, and violated limit
7. IF a line item references a product that has no `purchase_rules` defined, THEN THE Backend SHALL skip purchase rule validation for that line item and continue processing

### Requirement 17: Order Item Fields Backend Validation

**User Story:** As a system operator, I want per-item registration data validated in the backend so that incomplete or malformed submissions are rejected.

#### Acceptance Criteria

1. WHEN the create_order handler processes an order with Item_Fields_Data, THE Backend SHALL validate that all fields with `required` set to true in the product's Order_Item_Fields definition are present with a non-null, non-empty-string value for each item quantity
2. WHEN a field has type constraints, THE Backend SHALL validate the submitted value against those constraints: `min_length` and `max_length` for text fields, `minimum` and `maximum` for number fields, `pattern` as a regex match for text fields, allowed `options` list membership for select fields, and valid email format for email-type fields
3. IF Item_Fields_Data validation fails, THEN THE Backend SHALL return a 400 response with a structured error body identifying the specific item index (zero-based position in the line item's fields array), the field id that failed, and a description of the validation constraint that was violated
4. WHEN a product has Order_Item_Fields defined but the order submission contains no Item_Fields_Data for that line item, THE Backend SHALL reject the order with a 400 response identifying the line item index and indicating that Item_Fields_Data is missing
5. IF the number of Item_Fields_Data entries submitted for a line item does not equal the quantity ordered for that line item, THEN THE Backend SHALL reject the order with a 400 response identifying the line item index, the expected count (equal to the item quantity), and the actual count received
