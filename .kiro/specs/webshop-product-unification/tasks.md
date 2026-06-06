# Implementation Plan: Webshop Product Unification

## Overview

This plan implements the unification of the H-DCN webshop and PresMeet booking systems into a single product/order/payment pipeline. The implementation evolves the existing admin-product-management foundation: extending shared modules, modifying handlers to support the three-field split (variant_schema, order_item_fields, purchase_rules), adding customer-facing checkout with Mollie, tenant-based visibility, and per-item data collection.

The approach is: backend shared modules → backend handlers → migration scripts → frontend services/types → frontend components → property tests → integration tests.

## Tasks

- [x] 1. Extend shared layer with new modules
  - [x] 1.1 Create `backend/layers/auth-layer/python/shared/purchase_rules_engine.py`
    - Implement `enforce_max_per_order(quantity, max_per_order)` returning violation or None
    - Implement `enforce_max_per_member(member_id, product_id, new_quantity, max_per_member, orders_table)` querying existing paid/pending orders
    - Implement `enforce_max_per_club(club_id, product_id, new_quantity, max_per_club, orders_table)` querying existing paid/pending orders
    - Implement `enforce_requires_membership(member_id, memberships_table)` checking active membership
    - Implement `validate_purchase_rules(rules, context)` orchestrator calling all applicable rules
    - _Requirements: 5.1–5.12, 16.1–16.7_

  - [x] 1.2 Create `backend/layers/auth-layer/python/shared/item_fields_validator.py`
    - Implement `validate_item_fields_data(item_fields_data, order_item_fields_definition, quantity)` checking count matches quantity
    - Implement `validate_field_value(value, field_def)` checking required, min_length, max_length, minimum, maximum, pattern, options, email format
    - Return structured error with item_index, field_id, and constraint description
    - _Requirements: 4.1–4.6, 17.1–17.5_

  - [x] 1.3 Create `backend/layers/auth-layer/python/shared/tenant_resolver.py`
    - Implement `resolve_tenants(cognito_groups)` deriving accessible tenants from group claims (hdcnLeden→h-dcn, Regio_Pressmeet/Regio_All→presmeet)
    - Implement `validate_tenant_access(requested_tenants, user_tenants)` returning 403 error if mismatch
    - _Requirements: 7.1–7.7_

  - [x] 1.4 Create `backend/layers/auth-layer/python/shared/mollie_client.py`
    - Implement `create_payment(amount, description, redirect_url, webhook_url, method)` calling Mollie Payments API
    - Implement `get_payment(payment_id)` fetching payment status from Mollie
    - Implement `verify_webhook_signature(request_body, signature)` for webhook security
    - Handle Mollie API errors with structured error responses
    - _Requirements: 9.1, 9.2, 9.5_

  - [x] 1.5 Create `backend/layers/auth-layer/python/shared/stock_reservation.py`
    - Implement `reserve_stock_for_order(order_items, producten_table, order_id)` using DynamoDB conditional expressions
    - Use conditional update: `SET stock = stock - :qty, sold_count = sold_count + :qty IF stock >= :qty AND stock_reserved_for_order <> :order_id`
    - Implement idempotency guard to prevent double-deduction on retry
    - _Requirements: 6.6, 6.7, 6.8_

  - [x] 1.6 Update `backend/layers/auth-layer/python/shared/variant_helpers.py`
    - Refactor `generate_variant_combinations()` to accept `variant_schema` dict (replacing `required_attributes` logic)
    - Generate variant records with `variant_attributes` mapping each axis to its selected value
    - Preserve existing `create_default_variant()` and `should_remove_default_variant()` functions
    - _Requirements: 3.1–3.8_

  - [x] 1.7 Update `backend/layers/auth-layer/python/shared/product_validation.py`
    - Add `validate_variant_schema(schema)` checking: axis names non-empty/unique, values non-empty/unique per axis, total combos ≤ 100, max 5 axes, max 20 values per axis
    - Add `validate_order_item_fields(fields)` checking: max 20 definitions, unique ids, valid types, select has options, validation constraints
    - Add `validate_purchase_rules(rules)` checking: numeric ranges, min_per_club ≤ max_per_club, valid order_mode
    - Preserve existing validation functions for backward compatibility
    - _Requirements: 1.1–1.8, 3.1, 3.6, 3.8, 4.1, 4.6, 5.4_

- [x] 2. Checkpoint - Ensure shared module tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. Modify backend handlers for unified pipeline
  - [x] 3.1 Modify `backend/handler/get_products/app.py`
    - Add tenant query parameter support
    - Integrate `tenant_resolver.resolve_tenants()` to derive accessible tenants from Cognito claims
    - Validate requested tenant against user access using `validate_tenant_access()`
    - Filter products by tenant and `is_parent: true`, `active: true`
    - _Requirements: 7.1–7.7, 2.1–2.3_

  - [x] 3.2 Create `backend/handler/get_variants/app.py`
    - GET `/products/{id}/variants` — fetch all variant records for a parent product
    - Query Producten table GSI `parent_id-index` with the given product_id
    - Return variant records with stock, variant_attributes, allow_oversell, price
    - Validate tenant access before returning results
    - _Requirements: 6.2, 15.3_

  - [x] 3.3 Modify `backend/handler/create_cart/app.py`
    - Add `club_id` field support (derived from Cognito group membership for PresMeet users)
    - Add `tenant` field on cart record
    - Ensure cart items use `variant_id` reference (not `selectedOption`)
    - _Requirements: 6.1, 6.3, 6.5, 12.5_

  - [x] 3.4 Modify `backend/handler/update_cart_items/app.py`
    - Store `variant_id` and `variant_attributes` on each cart item (remove `selectedOption` support)
    - Support `item_fields_data` array on each cart item (partial data allowed during cart phase)
    - Validate variant exists and belongs to referenced product
    - Check stock availability for variants with `allow_oversell: false`
    - Implement quantity decrease logic: remove highest-numbered item_fields_data entries
    - Handle schema evolution: discard orphaned field values on cart load
    - _Requirements: 6.1–6.5, 6.7, 8.3, 8.7, 8.8, 8.9_

  - [x] 3.5 Modify `backend/handler/create_order/app.py`
    - Integrate purchase_rules_engine: validate all rules for each line item
    - Integrate item_fields_validator: validate all required fields and constraints
    - Validate stock availability for each variant (reject if insufficient and allow_oversell false)
    - Support `payment_method` field: "ideal", "creditcard", "bank_transfer"
    - For Mollie methods: create Mollie payment, return checkout_url with payment_status "pending"
    - For bank_transfer: create order with payment_status "unpaid", return transfer instructions
    - Support persistent order mode: find existing club order, update instead of create new
    - Implement optimistic locking with version attribute for persistent orders
    - Store Item_Fields_Data on order record with field_id, field_label, value, item_index
    - _Requirements: 5.7–5.12, 6.6–6.8, 8.4–8.6, 9.1–9.5, 10.1, 10.5–10.7, 12.5–12.13, 16.1–16.7, 17.1–17.5_

  - [x] 3.6 Create `backend/handler/mollie_webhook/app.py`
    - POST `/mollie-webhook` — process Mollie payment status callbacks
    - Fetch payment status from Mollie API using mollie_client
    - If "paid": update order payment_status to "paid", trigger stock_reservation
    - If "failed"/"expired"/"cancelled": update payment_status to "payment_failed"
    - Implement idempotency: use mollie_payment_id as key, guard stock reservation with conditional update
    - Return 200 for all valid webhook calls (Mollie requirement)
    - _Requirements: 9.6, 9.7, 9.11_

  - [x] 3.7 Modify `backend/handler/admin_record_payment/app.py`
    - Recalculate payment_status based on total_paid vs order total after recording payment
    - Trigger stock_reservation when payment_status transitions to "paid"
    - Support partial payments (payment_status "partial" when 0 < paid < total)
    - _Requirements: 9.10_

  - [x] 3.8 Modify `backend/handler/admin_create_product/app.py`
    - Accept `variant_schema`, `order_item_fields`, `purchase_rules` fields
    - Validate new fields using updated product_validation module
    - Generate variants from variant_schema (instead of required_attributes)
    - Preserve existing Default_Variant logic for products without variant_schema
    - Store groep, subgroep, images fields
    - _Requirements: 1.1–1.8, 2.7, 3.2, 3.3, 3.5_

  - [x] 3.9 Modify `backend/handler/admin_update_product/app.py`
    - Support updating variant_schema with variant regeneration (remove old variants, create new)
    - Support updating order_item_fields and purchase_rules
    - Validate all three fields on update
    - Handle variant_schema change: regenerate variants, reset stock to 0
    - Preserve groep, subgroep, images update capability
    - _Requirements: 1.1–1.8, 2.7, 3.7, 13.1–13.7_

- [x] 4. Checkpoint - Ensure all backend handler tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Create migration scripts
  - [x] 5.1 Create `backend/scripts/migrate_opties_to_variants.py`
    - Parse `opties` comma-separated string into variant_schema with single axis "opties"
    - Generate variant records for each parsed value (stock=0, allow_oversell=true)
    - Move original `opties` value to `legacy_opties` field, remove `opties` field
    - Skip already-migrated products (check for `legacy_opties` or existing variants with matching parent_id)
    - Log each migration: product_id, original opties, variant count, timestamp
    - Output summary: total processed, successful, skipped with reasons
    - _Requirements: 11.1–11.5, 14.1, 14.2_

  - [x] 5.2 Create `backend/scripts/migrate_presmeet_config.py`
    - Convert `config_presmeet_*` records into regular Parent_Product records with tenant "presmeet"
    - Map enum-type required_attributes to `variant_schema` axes
    - Map text/date/integer required_attributes to `order_item_fields` entries
    - Map max_per_club, min_per_club to `purchase_rules`
    - Preserve legacy required_attributes as read-only field
    - Skip unconvertible products, log failures, continue processing
    - Output summary report
    - _Requirements: 12.1–12.4, 14.3–14.6_

  - [x] 5.3 Create `backend/scripts/migrate_cart_selectedoption.py`
    - Find cart items with `selectedOption` field
    - Match selectedOption value to generated variant's variant_attributes
    - Replace `selectedOption` with `variant_id` of matching variant
    - Log unmatched cart items for manual resolution
    - _Requirements: 11.6, 11.7_

- [x] 6. Update SAM template
  - [x] 6.1 Add new Lambda function resources to `backend/template.yaml`
    - Add `GetVariantsFunction` (GET /products/{id}/variants)
    - Add `MollieWebhookFunction` (POST /mollie-webhook, no auth — Mollie calls this)
    - Add environment variables for Mollie API key (from Parameter Store)
    - Update existing handler resources with new environment variables as needed
    - _Requirements: 9.1, 15.3_

- [x] 7. Create frontend types and services
  - [x] 7.1 Create `frontend/src/modules/webshop/types/unifiedProduct.types.ts`
    - Define `VariantSchema` type (Record<string, string[]>)
    - Define `OrderItemField` interface with id, label, type, required, validation, options
    - Define `PurchaseRules` interface with max_per_order, max_per_member, max_per_club, min_per_club, requires_membership, order_mode
    - Define `UnifiedProduct` interface extending existing product type with new fields
    - Define `VariantRecord` interface with variant_attributes, stock, sold_count, allow_oversell
    - Define `CartItem` interface with variant_id, variant_attributes, item_fields_data
    - Define `ItemFieldsEntry` interface with field_values per item
    - Define `MolliePaymentResponse` interface with checkout_url
    - Define `TransferInstructions` interface
    - _Requirements: 1.1–1.3, 6.1, 6.4_

  - [x] 7.2 Create `frontend/src/modules/webshop/services/mollie.ts`
    - Implement `createMolliePayment(orderId, method)` calling backend create_order
    - Implement `handleMollieRedirect(checkoutUrl)` for browser redirect
    - Implement `handlePaymentReturn(status)` for post-payment return page logic
    - Replace Stripe integration references
    - _Requirements: 9.2, 9.5, 9.8, 9.9_

  - [x] 7.3 Update `frontend/src/modules/webshop/services/api.ts`
    - Add `getVariants(productId)` calling GET /products/{id}/variants
    - Add tenant parameter to `getProducts(tenant)` call
    - Update cart API calls to send variant_id instead of selectedOption
    - Add item_fields_data support in cart update calls
    - Add payment_method to order creation call
    - _Requirements: 6.1, 7.5, 15.3_

- [x] 8. Create frontend webshop components
  - [x] 8.1 Create `frontend/src/modules/webshop/components/VariantSelector.tsx`
    - Render a dropdown/select for each axis in variant_schema
    - Disable add-to-cart until all axes have a selection
    - Resolve matching variant from selections, display stock count
    - Show out-of-stock message when variant has stock=0 and allow_oversell=false
    - Show "combination unavailable" when no matching variant exists
    - Re-resolve on axis change
    - _Requirements: 15.1–15.8_

  - [x] 8.2 Create `frontend/src/modules/webshop/components/ItemFieldsForm.tsx`
    - Render configured fields for each item quantity (Q items = Q sets of fields)
    - Support field types: text, select, date, number, email
    - Display sequential item labels ("Item 1 of 3", "Item 2 of 3")
    - Validate required fields and constraints on form submission
    - Allow saving with incomplete data (validation only at order submission)
    - Display field-level error messages identifying item number, field, violation
    - _Requirements: 4.1–4.6, 8.1–8.5_

  - [x] 8.3 Create `frontend/src/modules/webshop/components/PurchaseRulesFeedback.tsx`
    - Display max_per_order violation message with allowed quantity
    - Display max_per_member remaining quantity based on user's order history
    - Display max_per_club remaining quantity based on club's order history
    - Display requires_membership message when user lacks active membership
    - Disable add-to-cart when any rule is violated
    - _Requirements: 5.7–5.10_

  - [x] 8.4 Create `frontend/src/modules/webshop/components/PaymentMethodSelector.tsx`
    - Render payment method options: iDEAL, credit card, bank transfer
    - Display bank transfer instructions after selection (reference, IBAN, amount)
    - Handle Mollie redirect flow for online payment methods
    - Display post-payment return messaging (success, failed, retry option)
    - _Requirements: 9.1–9.9_

  - [x] 8.5 Modify `frontend/src/modules/webshop/components/ProductCard.tsx`
    - Replace legacy opties dropdown with VariantSelector component
    - Integrate PurchaseRulesFeedback component
    - Use variant_id for add-to-cart action instead of selectedOption
    - Preserve existing image carousel and product details display
    - _Requirements: 2.5, 2.6, 15.1, 15.2_

  - [x] 8.6 Modify `frontend/src/modules/webshop/components/CartModal.tsx`
    - Display variant_attributes as axis:value pairs per item
    - Embed ItemFieldsForm for items with order_item_fields
    - Support quantity decrease with highest-numbered field data removal
    - Save partial item_fields_data on cart update
    - _Requirements: 6.4, 8.1–8.3, 8.7, 8.8, 15.8, 15.9_

  - [x] 8.7 Modify `frontend/src/modules/webshop/components/CheckoutModal.tsx`
    - Integrate PaymentMethodSelector component
    - Validate all required item fields before allowing submission
    - Call create_order with payment_method and item_fields_data
    - Handle Mollie redirect for online payments
    - Display bank transfer instructions for manual payment
    - Handle payment return (success/failure messaging)
    - _Requirements: 8.4, 8.5, 9.1–9.9_

  - [x] 8.8 Modify `frontend/src/modules/webshop/components/ProductFilter.tsx`
    - Add tenant-awareness: derive visible tenants from user's Cognito roles
    - Build groep/subgroep filter options dynamically from active products matching user's tenants
    - Display "no product access" message when user has no tenant roles
    - _Requirements: 2.1–2.3, 7.1–7.4_

- [x] 9. Checkpoint - Ensure frontend components compile and render
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Create admin UI components for new product fields
  - [x] 10.1 Create `frontend/src/modules/products/components/VariantSchemaEditor.tsx`
    - Visual editor for adding up to 5 axes with names and values
    - Controls to add, reorder, remove axes and values
    - Validate axis names non-empty/unique, values non-empty/unique per axis
    - Display error when total combinations exceed 100
    - _Requirements: 13.1, 13.2, 13.5, 13.7_

  - [x] 10.2 Create `frontend/src/modules/products/components/OrderItemFieldsEditor.tsx`
    - Form builder for up to 20 field definitions
    - Each field: id (auto-generated or manual), label, type selector, required toggle
    - Validation constraint inputs per type (min_length, max_length, minimum, maximum, pattern)
    - Options editor for select-type fields
    - Validate unique ids, select has at least one option
    - _Requirements: 13.1, 13.3, 13.5, 13.7_

  - [x] 10.3 Create `frontend/src/modules/products/components/PurchaseRulesEditor.tsx`
    - Form inputs for max_per_order, max_per_member, max_per_club, min_per_club
    - Requires_membership toggle and order_mode select ("single" / "persistent")
    - Validate numeric ranges and min_per_club ≤ max_per_club
    - _Requirements: 13.1, 13.4, 13.5_

  - [x] 10.4 Integrate new editors into admin product create/edit forms
    - Add collapsible sections for Variant Schema, Order Item Fields, Purchase Rules
    - Display legacy `required_attributes` as read-only with migration pending label
    - Wire save/validation to backend admin_create_product and admin_update_product
    - _Requirements: 13.1, 13.5, 13.6_

- [x] 11. Checkpoint - Ensure all frontend tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. Write backend property-based tests
  - [x] 12.1 Write property test for variant generation count (Property 1)
    - **Property 1: Variant generation count equals cartesian product**
    - Test: for any valid variant_schema, generated variant count equals C₁ × C₂ × ... × Cₙ
    - Use Hypothesis `variant_schema_strategy()` generator
    - File: `backend/tests/unit/test_product_unification_properties.py`
    - **Validates: Requirements 3.2, 3.3**

  - [x] 12.2 Write property test for variant schema validation (Property 2)
    - **Property 2: Variant schema validation rejects invalid schemas**
    - Test: schemas with duplicate values, empty arrays, or combos > 100 are rejected
    - File: `backend/tests/unit/test_product_unification_properties.py`
    - **Validates: Requirements 3.6, 3.8**

  - [x] 12.3 Write property test for max_per_order enforcement (Property 3)
    - **Property 3: Purchase rules enforcement — max_per_order**
    - Test: quantity > max_per_order rejected, quantity ≤ max_per_order allowed
    - File: `backend/tests/unit/test_product_unification_properties.py`
    - **Validates: Requirements 5.1, 5.7, 16.2**

  - [x] 12.4 Write property test for max_per_member enforcement (Property 4)
    - **Property 4: Purchase rules enforcement — max_per_member**
    - Test: (existing_total + new_quantity) > max_per_member rejected
    - Use `order_history_strategy()` generator
    - File: `backend/tests/unit/test_product_unification_properties.py`
    - **Validates: Requirements 5.2, 5.8, 16.3**

  - [x] 12.5 Write property test for max_per_club enforcement (Property 5)
    - **Property 5: Purchase rules enforcement — max_per_club**
    - Test: (club_total + new_quantity) > max_per_club rejected
    - File: `backend/tests/unit/test_product_unification_properties.py`
    - **Validates: Requirements 5.3, 5.9, 16.4**

  - [x] 12.6 Write property test for absent rules (Property 6)
    - **Property 6: Absent purchase rules impose no constraints**
    - Test: when a rule is absent/null, any valid quantity is allowed
    - File: `backend/tests/unit/test_product_unification_properties.py`
    - **Validates: Requirements 5.6, 16.7**

  - [x] 12.7 Write property test for min/max club constraint (Property 7)
    - **Property 7: min_per_club cannot exceed max_per_club**
    - Test: validation rejects configs where min_per_club > max_per_club
    - File: `backend/tests/unit/test_product_unification_properties.py`
    - **Validates: Requirements 5.4**

  - [x] 12.8 Write property test for stock reservation (Property 8)
    - **Property 8: Stock reservation correctness**
    - Test: initial_stock - stock_after = sold_count_after - initial_sold_count = ordered_quantity
    - File: `backend/tests/unit/test_product_unification_properties.py`
    - **Validates: Requirements 6.6**

  - [x] 12.9 Write property test for stock enforcement (Property 9)
    - **Property 9: Stock enforcement prevents overselling**
    - Test: allow_oversell=false AND stock < qty → reject; otherwise → allow
    - File: `backend/tests/unit/test_product_unification_properties.py`
    - **Validates: Requirements 6.7, 6.8**

  - [x] 12.10 Write property test for cart item structure (Property 10)
    - **Property 10: Cart items never contain selectedOption**
    - Test: all cart items have product_id, variant_id, quantity; never selectedOption
    - File: `backend/tests/unit/test_product_unification_properties.py`
    - **Validates: Requirements 6.1, 6.5**

  - [x] 12.11 Write property test for tenant role derivation (Property 11)
    - **Property 11: Tenant role derivation**
    - Test: hdcnLeden→h-dcn, Regio_Pressmeet/Regio_All→presmeet, union of grants
    - File: `backend/tests/unit/test_product_unification_properties.py`
    - **Validates: Requirements 7.1–7.4, 7.7**

  - [x] 12.12 Write property test for tenant access enforcement (Property 12)
    - **Property 12: Tenant access enforcement**
    - Test: requesting inaccessible tenant returns 403
    - File: `backend/tests/unit/test_product_unification_properties.py`
    - **Validates: Requirements 7.6**

  - [x] 12.13 Write property test for item fields count (Property 13)
    - **Property 13: Item fields data count matches quantity**
    - Test: exactly Q entries required for Q items; fewer or more rejected
    - File: `backend/tests/unit/test_product_unification_properties.py`
    - **Validates: Requirements 4.4, 17.5**

  - [x] 12.14 Write property test for required field validation (Property 14)
    - **Property 14: Required field validation**
    - Test: empty values for required fields rejected per type-specific rules
    - File: `backend/tests/unit/test_product_unification_properties.py`
    - **Validates: Requirements 4.3, 17.1**

  - [x] 12.15 Write property test for field constraint validation (Property 15)
    - **Property 15: Field constraint validation**
    - Test: values violating min_length, max_length, minimum, maximum, pattern, options rejected
    - File: `backend/tests/unit/test_product_unification_properties.py`
    - **Validates: Requirements 4.5, 17.2**

  - [x] 12.16 Write property test for opties migration (Property 16)
    - **Property 16: Opties migration round-trip**
    - Test: migrated variant_schema has axis "opties" with values = split(opties, ",").trim()
    - File: `backend/tests/unit/test_product_unification_properties.py`
    - **Validates: Requirements 11.1, 11.2, 11.3**

  - [x] 12.17 Write property test for migration idempotence (Property 17)
    - **Property 17: Migration idempotence**
    - Test: second run produces no changes to already-migrated products
    - File: `backend/tests/unit/test_product_unification_properties.py`
    - **Validates: Requirements 11.4**

  - [x] 12.18 Write property test for Mollie webhook idempotence (Property 18)
    - **Property 18: Mollie webhook idempotence**
    - Test: processing same payment_id multiple times produces same state, no duplicate stock reservations
    - File: `backend/tests/unit/test_product_unification_properties.py`
    - **Validates: Requirements 9.11**

  - [x] 12.19 Write property test for payment status calculation (Property 19)
    - **Property 19: Payment status calculation for manual payments**
    - Test: P >= T → "paid", 0 < P < T → "partial"; stock reservation only on "paid" transition
    - File: `backend/tests/unit/test_product_unification_properties.py`
    - **Validates: Requirements 9.10**

  - [x] 12.20 Write property test for item fields persistence (Property 20)
    - **Property 20: Item fields data persistence on order**
    - Test: stored data preserves field_id, field_label, value, 1-based item_index
    - File: `backend/tests/unit/test_product_unification_properties.py`
    - **Validates: Requirements 10.1, 10.5**

  - [x] 12.21 Write property test for CSV export row count (Property 21)
    - **Property 21: CSV export row count**
    - Test: CSV rows = Σ(Qᵢ × Fᵢ) + 1 header row
    - File: `backend/tests/unit/test_product_unification_properties.py`
    - **Validates: Requirements 10.4**

  - [x] 12.22 Write property test for quantity decrease (Property 22)
    - **Property 22: Quantity decrease removes highest-numbered item data**
    - Test: decrease to Q-N retains items 1..Q-N, discards Q-N+1..Q
    - File: `backend/tests/unit/test_product_unification_properties.py`
    - **Validates: Requirements 8.8**

  - [x] 12.23 Write property test for schema evolution (Property 23)
    - **Property 23: Schema evolution discards orphaned field data**
    - Test: field_ids not in current definition are discarded; existing ones retained
    - File: `backend/tests/unit/test_product_unification_properties.py`
    - **Validates: Requirements 8.9**

  - [x] 12.24 Write property test for persistent order uniqueness (Property 24)
    - **Property 24: Persistent order — one per club**
    - Test: order_mode "persistent" maintains at most one active order per club
    - File: `backend/tests/unit/test_product_unification_properties.py`
    - **Validates: Requirements 12.9**

  - [x] 12.25 Write property test for optimistic locking (Property 25)
    - **Property 25: Optimistic locking rejects stale writes**
    - Test: concurrent writes with same version → exactly one succeeds, other rejected
    - File: `backend/tests/unit/test_product_unification_properties.py`
    - **Validates: Requirements 12.13**

  - [x] 12.26 Write property test for legacy field precedence (Property 26)
    - **Property 26: Legacy field precedence**
    - Test: when both required_attributes and new fields exist, required_attributes is ignored
    - File: `backend/tests/unit/test_product_unification_properties.py`
    - **Validates: Requirements 1.8**

  - [x] 12.27 Write property test for variant resolution (Property 27)
    - **Property 27: Variant resolution**
    - Test: complete axis selections resolve to exactly one variant or indicate no match
    - File: `backend/tests/unit/test_product_unification_properties.py`
    - **Validates: Requirements 15.3, 15.5**

- [x] 13. Write backend integration tests
  - [x] 13.1 Create `backend/tests/integration/test_unified_pipeline.py` with moto-mocked DynamoDB fixtures
    - Set up Producten, Carts, Orders, Members, Memberships tables
    - Create test products with variant_schema, order_item_fields, purchase_rules
    - _Requirements: all_

  - [x] 13.2 Write integration test for full order lifecycle with Mollie
    - Cart creation → add items with variant_id → order creation with iDEAL → Mollie webhook "paid" → stock reservation → completion
    - _Requirements: 6.6, 9.5, 9.6_

  - [x] 13.3 Write integration test for purchase rules enforcement end-to-end
    - Create orders exceeding max_per_member and max_per_club → verify 400 rejections
    - _Requirements: 16.1–16.7_

  - [x] 13.4 Write integration test for item fields validation end-to-end
    - Submit order with missing required fields, wrong count, constraint violations → verify 400
    - _Requirements: 17.1–17.5_

  - [x] 13.5 Write integration test for tenant filtering
    - Users with different role combinations → verify correct product visibility and 403 on cross-tenant access
    - _Requirements: 7.1–7.7_

  - [x] 13.6 Write integration test for migration scripts
    - Run migrate_opties_to_variants on fixture data → verify variant generation and idempotence
    - Run migrate_presmeet_config → verify field mapping
    - Run migrate_cart_selectedoption → verify variant_id replacement
    - _Requirements: 11.1–11.7, 14.1–14.6_

- [x] 14. Write frontend unit tests
  - [x] 14.1 Write tests for VariantSelector component
    - Axis rendering, selection interaction, variant resolution, stock display, out-of-stock state
    - File: `frontend/src/modules/webshop/__tests__/VariantSelector.test.tsx`
    - _Requirements: 15.1–15.8_

  - [x] 14.2 Write tests for ItemFieldsForm component
    - Field rendering per type, required validation, constraint validation, multi-item sets
    - File: `frontend/src/modules/webshop/__tests__/ItemFieldsForm.test.tsx`
    - _Requirements: 8.1–8.5_

  - [x] 14.3 Write tests for PurchaseRulesFeedback component
    - Rule violation messages, disabled state, remaining quantity display
    - File: `frontend/src/modules/webshop/__tests__/PurchaseRulesFeedback.test.tsx`
    - _Requirements: 5.7–5.10_

  - [x] 14.4 Write tests for PaymentMethodSelector component
    - Method selection, bank transfer instructions display, Mollie redirect handling
    - File: `frontend/src/modules/webshop/__tests__/PaymentMethodSelector.test.tsx`
    - _Requirements: 9.1–9.9_

  - [x] 14.5 Write tests for admin editors (VariantSchemaEditor, OrderItemFieldsEditor, PurchaseRulesEditor)
    - Axis/field CRUD operations, validation errors, limit enforcement
    - File: `frontend/src/modules/products/__tests__/AdminEditors.test.tsx`
    - _Requirements: 13.1–13.7_

- [x] 15. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- The existing admin-product-management infrastructure (order state machine, stock_helpers, payment_helpers, variant_helpers) is extended rather than rewritten
- Backend shared modules (Task 1) must be implemented before handlers (Task 3) since handlers import from them
- Migration scripts (Task 5) depend on the updated variant_helpers for variant generation logic
- Frontend types/services (Task 7) must exist before components (Tasks 8, 10) can be implemented
- Mollie webhook handler has no Cognito authorizer (Mollie calls it directly) — secure via signature verification
- The `selectedOption` field is fully deprecated after migration; no new code should reference it

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3", "1.4", "1.5", "1.6", "1.7"] },
    { "id": 1, "tasks": ["3.1", "3.2", "3.3", "3.4", "3.6", "3.8", "3.9"] },
    { "id": 2, "tasks": ["3.5", "3.7", "5.1", "5.2", "5.3", "6.1"] },
    { "id": 3, "tasks": ["7.1", "7.2", "7.3"] },
    { "id": 4, "tasks": ["8.1", "8.2", "8.3", "8.4", "8.5", "8.8"] },
    { "id": 5, "tasks": ["8.6", "8.7", "10.1", "10.2", "10.3"] },
    { "id": 6, "tasks": ["10.4"] },
    {
      "id": 7,
      "tasks": [
        "12.1",
        "12.2",
        "12.3",
        "12.4",
        "12.5",
        "12.6",
        "12.7",
        "12.8",
        "12.9",
        "12.10",
        "12.11",
        "12.12",
        "12.13",
        "12.14",
        "12.15",
        "12.16",
        "12.17",
        "12.18",
        "12.19",
        "12.20",
        "12.21",
        "12.22",
        "12.23",
        "12.24",
        "12.25",
        "12.26",
        "12.27"
      ]
    },
    { "id": 8, "tasks": ["13.1", "13.2", "13.3", "13.4", "13.5", "13.6"] },
    { "id": 9, "tasks": ["14.1", "14.2", "14.3", "14.4", "14.5"] }
  ]
}
```
