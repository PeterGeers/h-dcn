# Implementation Plan: Order Pipeline Improvements

## Overview

This plan implements the order pipeline improvements in six phases: shared modules (state machine, number generator, item fields validator, variant sync), handler updates, frontend changes, and testing. Each task builds incrementally — shared modules first, then handlers that consume them, then frontend that displays their output.

## Tasks

- [x] 1. Create shared modules in Lambda Layer
  - [x] 1.1 Implement order state machine module (`backend/layers/auth-layer/python/shared/order_state_machine.py`)
    - Define `ORDER_TRANSITIONS` and `PAYMENT_TRANSITIONS` dicts
    - Implement `validate_order_transition`, `validate_payment_transition`, `transition_order`, `transition_payment`
    - Define `InvalidTransitionError` exception class
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 1.2 Write property tests for order state machine (Properties 1–5)
    - **Property 1: Order state machine accepts all valid transitions**
    - **Property 2: Order state machine rejects all invalid transitions**
    - **Property 3: Payment state machine accepts all valid transitions**
    - **Property 4: Payment state machine rejects all invalid transitions**
    - **Property 5: Payment confirmation triggers order confirmation**
    - **Validates: Requirements 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 2.1, 2.2, 2.3, 2.4, 2.5**
    - File: `backend/tests/unit/test_order_state_machine.py`
    - Use Hypothesis `@given` with `st.sampled_from` for status enums

  - [x] 1.3 Implement number generator module (`backend/layers/auth-layer/python/shared/number_generator.py`)
    - Implement `generate_order_number(counters_table, today)` → `H-YYMMDD-NNN`
    - Implement `generate_invoice_number(counters_table, year)` → `F-YYYY-NNNN`
    - Use DynamoDB `UpdateItem` with `ADD current_value :inc` pattern
    - Define `CounterWriteError` for transient DynamoDB failures with retry logic
    - _Requirements: 3.1, 3.2, 7.1, 7.2_

  - [x] 1.4 Write property tests for number generator (Properties 6–7)
    - **Property 6: Order number format validity**
    - **Property 7: Invoice number format validity**
    - **Validates: Requirements 3.1, 7.1**
    - File: `backend/tests/unit/test_number_generator.py`
    - Use Hypothesis `@given` with date strategies and integer strategies for sequences

  - [x] 1.5 Implement item fields validator module (`backend/layers/auth-layer/python/shared/item_fields_validator.py`)
    - Implement `validate_item_fields(order_item_fields, item_fields_data, quantity)` returning list of errors
    - Validate count match (item_fields_data length == quantity)
    - Validate required fields have non-empty values
    - Validate type-specific rules (email pattern, number min/max)
    - Return structured error list with `item_index`, `field_id`, `message`
    - _Requirements: 6.3, 6.4, 6.5_

  - [x] 1.6 Write property test for item fields validation (Property 13)
    - **Property 13: Required item fields validation**
    - **Validates: Requirements 6.3, 6.4**
    - File: `backend/tests/unit/test_item_fields_validation.py`
    - Use Hypothesis to generate field definitions and submission data

  - [x] 1.7 Implement purchase rules validator module (`backend/layers/auth-layer/python/shared/purchase_rules_validator.py`)
    - Implement `validate_purchase_rules(purchase_rules, existing_count, new_quantity, is_member)` returning error or None
    - Check `max_per_order`, `max_per_member`, `max_per_club`
    - Check `requires_membership` flag
    - Return structured `PurchaseRuleViolation` error with rule name, limit, and current count
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [x] 1.8 Write property test for purchase rules (Property 12)
    - **Property 12: Purchase rules enforcement**
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.5**
    - File: `backend/tests/unit/test_purchase_rules_validation.py`
    - Use Hypothesis with integer strategies for limits and quantities

  - [x] 1.9 Implement variant sync module (`backend/layers/auth-layer/python/shared/variant_sync.py`)
    - Implement `sync_schema_to_variants(producten_table, parent_id, new_schema, parent_price)` → `SyncResult`
    - Implement `sync_variant_to_schema(producten_table, parent_id, variant_attributes)` → updated schema
    - Compute cartesian product of schema axes for top-down sync
    - Preserve stock/price on unchanged variants, deactivate removed combinations
    - Define `SyncResult` dataclass with created/preserved/deactivated counts
    - Define `MaxCombinationsExceeded` error (limit: 100)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.7_

  - [x] 1.10 Write property tests for variant sync (Properties 9–11)
    - **Property 9: Variant generation produces correct count and structure**
    - **Property 10: Top-down schema sync preserves unchanged variant data**
    - **Property 11: Bottom-up schema derivation reflects active variants**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.6, 4.7**
    - File: `backend/tests/unit/test_variant_sync.py`
    - Use Hypothesis to generate variant schemas (dict of axis→values)

- [x] 2. Checkpoint - Verify shared modules
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. Update backend handlers — order submission and payment
  - [x] 3.1 Update `submit_order` handler (`backend/handler/submit_order/app.py`)
    - Import and use `order_state_machine.transition_order` to validate `draft→submitted`
    - Call `number_generator.generate_order_number` and store on order record
    - Import and use `item_fields_validator.validate_item_fields` for strict validation
    - Import and use `purchase_rules_validator.validate_purchase_rules` for server-side check
    - Add `submitted_at` timestamp
    - Add `COUNTERS_TABLE_NAME` environment variable reference
    - _Requirements: 1.2, 3.1, 3.2, 3.3, 5.5, 6.3, 6.4, 6.5_

  - [x] 3.2 Update `pay_order` handler (`backend/handler/pay_order/app.py`)
    - Use `order_state_machine.transition_payment` for `unpaid→pending` (online) or `unpaid→awaiting_payment` (bank transfer)
    - Include `order_number` as `reference` in `transfer_instructions` response for bank transfers
    - Do NOT mark bank transfer as `paid` in mock payment mode
    - _Requirements: 2.1, 2.2, 2.6, 3.7_

  - [x] 3.3 Write property test for bank transfer reference (Property 8)
    - **Property 8: Bank transfer reference equals order number**
    - **Validates: Requirements 3.7**
    - File: `backend/tests/unit/test_number_generator.py` (append to existing)

  - [x] 3.4 Update `mollie_webhook` handler (`backend/handler/mollie_webhook/app.py`)
    - On `paid` status: call `transition_payment("pending", "paid")`, call `transition_order("submitted", "confirmed")`
    - On `paid` status: call `generate_invoice_number` and store `invoice_number` on order
    - On `paid` status: set `paid_at` timestamp
    - On `failed` status: call `transition_payment` to set `unpaid`, keep order `submitted`
    - Return HTTP 200 always (Mollie requirement)
    - Ignore duplicate webhooks (if already `paid`, silently skip)
    - _Requirements: 1.3, 1.8, 2.3, 7.1, 7.2, 7.3, 7.4_

  - [x] 3.5 Write property test for invoice number on unpaid orders (Property 14)
    - **Property 14: No invoice number on unpaid orders**
    - **Validates: Requirements 7.4**
    - File: `backend/tests/unit/test_number_generator.py` (append to existing)

  - [x] 3.6 Create `admin_confirm_payment` handler (`backend/handler/admin_confirm_payment/app.py`)
    - Admin endpoint to confirm bank transfer receipt
    - Call `transition_payment("awaiting_payment", "paid")` and `transition_order("submitted", "confirmed")`
    - Call `generate_invoice_number` and store on order
    - Set `paid_at` timestamp
    - Require admin permission via `validate_permissions_with_regions`
    - _Requirements: 1.4, 2.4, 7.1, 7.3_

- [x] 4. Update backend handlers — product management
  - [x] 4.1 Update `admin_create_product` handler (`backend/handler/admin_create_product/app.py`)
    - Store `variant_schema` in Record format
    - Call `variant_sync.sync_schema_to_variants` after product creation
    - Set `active: true`, `is_parent: true`, numeric `price`
    - _Requirements: 4.1, 4.6, 4.7_

  - [x] 4.2 Update `admin_update_product` handler (`backend/handler/admin_update_product/app.py`)
    - Detect `variant_schema` changes → call `sync_schema_to_variants` (top-down)
    - Detect variant add/remove → call `sync_variant_to_schema` (bottom-up)
    - _Requirements: 4.2, 4.3, 4.4, 4.5_

  - [x] 4.3 Update or create `admin_delete_product` handler (`backend/handler/admin_delete_product/app.py`)
    - Implement soft-delete: set `active: false` on product and all child variants
    - Implement hard-delete guard: query Orders table for non-cancelled orders referencing product
    - Reject hard-delete if any references found, return `ProductHasOrderHistory` error
    - Allow hard-delete only when zero non-cancelled orders reference the product
    - _Requirements: 8.1, 8.2, 8.6_

  - [x] 4.4 Write property tests for product soft delete (Properties 15–16)
    - **Property 15: Customer-facing listing excludes inactive products**
    - **Property 16: Hard-delete guard prevents deletion of sold products**
    - **Validates: Requirements 8.1, 8.2, 8.6**
    - File: `backend/tests/unit/test_product_soft_delete.py`

  - [x] 4.5 Update customer-facing product listing handler to filter `active=true` only
    - Modify the existing product listing query to exclude `active: false` products
    - Ensure admin endpoints still return inactive products when filter is applied
    - _Requirements: 8.1, 8.5_

- [x] 5. Checkpoint - Verify backend handlers
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Update SAM template and configuration
  - [x] 6.1 Add `admin_confirm_payment` Lambda function to `backend/template.yaml`
    - Define API Gateway route `POST /admin/orders/{id}/confirm-payment`
    - Add environment variables: `ORDERS_TABLE_NAME`, `COUNTERS_TABLE_NAME`
    - Add IAM policy for DynamoDB access to Orders and Counters tables
    - _Requirements: 2.4_

  - [x] 6.2 Add `COUNTERS_TABLE_NAME` environment variable to existing handlers
    - Update `submit_order`, `mollie_webhook`, and `admin_confirm_payment` function definitions
    - Add IAM policy for Counters table UpdateItem permission
    - Note: Counters table must be created manually in DynamoDB (not in SAM template)
    - _Requirements: 3.2, 7.2_

- [x] 7. Frontend changes — order display and checkout
  - [x] 7.1 Update `CheckoutModal` to display `order_number` after submission
    - Show `order_number` on order confirmation screen
    - Display `order_number` as bank transfer reference when payment method is bank transfer
    - _Requirements: 3.4, 3.7_

  - [x] 7.2 Update `OrdersAdmin` component to show order and invoice numbers
    - Add `order_number` column to admin order list
    - Add `invoice_number` badge/column (show when present)
    - Add payment status filter (unpaid, pending, awaiting_payment, paid)
    - Indicate which orders have an invoice generated
    - _Requirements: 3.6, 7.6, 7.8_

  - [x] 7.3 Create Invoice PDF generation utility
    - Create `frontend/src/modules/webshop/utils/invoicePdf.ts`
    - Generate PDF with `invoice_number`, H-DCN BTW-nummer, itemized amounts with VAT, customer details
    - Only available when `invoice_number` is present (payment_status = paid)
    - Distinct from order confirmation PDF
    - _Requirements: 7.5, 7.7_

  - [x] 7.4 Update order confirmation PDF to include `order_number`
    - Modify existing PDF generation to prominently display `order_number`
    - _Requirements: 3.5_

- [x] 8. Frontend changes — product management
  - [x] 8.1 Update `WebshopManagementPage` with active/inactive filter and soft-delete
    - Add filter toggle to show/hide inactive products (default: show active only)
    - Add soft-delete button (sets `active: false`)
    - Add hard-delete option with guard (API rejects if orders exist)
    - Show warning when deactivating product with pending orders
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [x] 8.2 Update variant schema editor for bidirectional sync
    - Support top-down flow: editing schema triggers `sync_schema_to_variants` via API
    - Support bottom-up flow: adding/removing individual variants triggers `sync_variant_to_schema` via API
    - _Requirements: 4.5_

- [x] 9. Checkpoint - Verify frontend changes
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Integration tests
  - [x] 10.1 Write integration test for submit order flow
    - Test full pipeline: create order → add items with item_fields → submit → verify order_number, validation, status transitions
    - Use moto for DynamoDB mocking
    - File: `backend/tests/integration/test_submit_order_flow.py`
    - _Requirements: 1.2, 3.1, 5.5, 6.3_

  - [x] 10.2 Write integration test for payment confirmation flow
    - Test webhook → confirmed → invoice_number assignment
    - Test admin confirm payment → confirmed → invoice_number assignment
    - Verify coupled transition (payment_status=paid triggers status=confirmed)
    - File: `backend/tests/integration/test_payment_confirmation_flow.py`
    - _Requirements: 1.3, 1.4, 2.3, 2.4, 7.1, 7.3_

- [x] 11. Final checkpoint
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional property-based test tasks and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties using Hypothesis
- Unit tests validate specific examples and edge cases using pytest + moto
- The Counters DynamoDB table must be created manually (not in SAM template) before deploying
- Frontend tests use Jest + React Testing Library (`npx react-scripts test --watchAll=false`)
- Backend tests use `pytest tests/` from the backend directory
- All shared modules go in `backend/layers/auth-layer/python/shared/` to be available in the Lambda Layer

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.3", "1.5", "1.7"] },
    { "id": 1, "tasks": ["1.2", "1.4", "1.6", "1.8", "1.9"] },
    { "id": 2, "tasks": ["1.10"] },
    { "id": 3, "tasks": ["3.1", "3.2", "3.4", "3.6", "4.1", "4.3", "4.5"] },
    { "id": 4, "tasks": ["3.3", "3.5", "4.2", "4.4", "6.1", "6.2"] },
    { "id": 5, "tasks": ["7.1", "7.2", "7.3", "7.4", "8.1", "8.2"] },
    { "id": 6, "tasks": ["10.1", "10.2"] }
  ]
}
```
