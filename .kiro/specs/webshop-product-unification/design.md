# Design Document: Webshop Product Unification

## Overview

This design unifies the H-DCN webshop and PresMeet booking systems into a single product/order/payment pipeline. The core change splits the overloaded `required_attributes` JSON Schema field (which currently mixes variant dimensions, registration fields, and constraints) into three purpose-built fields:

- **`variant_schema`** — defines axes that generate SKUs with independent stock
- **`order_item_fields`** — defines per-item data collected from the buyer at checkout
- **`purchase_rules`** — defines business constraints on purchasing (quantity limits, membership, order mode)

The cart model shifts from referencing products via `product_id` + flat `selectedOption` string to referencing actual variant records via `variant_id`. This enables reliable stock tracking at the variant level.

PresMeet products join the same pipeline by storing them in `Producten` with `tenant: "presmeet"` and using the same cart/order/payment tables and handlers. Tenant-based visibility ensures buyers only see products they have access to.

Payment processing consolidates on Mollie (replacing the current Stripe integration for H-DCN), with bank transfer as an alternative manual method.

## Architecture

```mermaid
graph TB
    subgraph Frontend ["Frontend (React 18 + TypeScript)"]
        WP[WebshopPage]
        PC[ProductCard + VariantSelector]
        CM[CartModal + ItemFieldsForms]
        CO[CheckoutModal + PaymentSelector]
        AF[ProductFilter - groep/subgroep]
    end

    subgraph API ["API Gateway (REST)"]
        GP[GET /products?tenant=]
        GV[GET /products/{id}/variants]
        CC[POST /carts]
        UC[PUT /carts/{id}/items]
        CRO[POST /orders]
        MW[POST /mollie-webhook]
        AP[POST /admin/payments]
    end

    subgraph Lambda ["Lambda Handlers"]
        LGP[get_products]
        LGV[get_variants]
        LCC[create_cart]
        LUC[update_cart_items]
        LCRO[create_order]
        LMW[mollie_webhook]
        LAP[admin_record_payment]
    end

    subgraph DynamoDB ["DynamoDB Tables"]
        PT[(Producten<br/>parent + variant records)]
        CT[(Carts)]
        OT[(Orders)]
        MT[(Members)]
        MST[(Memberships)]
    end

    subgraph External ["External Services"]
        MOL[Mollie API]
        COG[Cognito<br/>role claims]
    end

    WP --> GP
    PC --> GV
    CM --> UC
    CO --> CRO
    GP --> LGP --> PT
    GV --> LGV --> PT
    CC --> LCC --> CT
    UC --> LUC --> CT
    CRO --> LCRO --> OT
    LCRO --> PT
    LCRO --> MOL
    MW --> LMW --> OT
    LMW --> PT
    AP --> LAP --> OT
    LAP --> PT
    LCRO --> MT
    LCRO --> MST
    COG -.->|role claims| LGP
    COG -.->|role claims| LCRO
```

### Key Architectural Decisions

1. **Single table for parent + variants** — Variant records live in the same `Producten` table with `is_parent: false` and a `parent_id` FK. This keeps queries simple (GSI on `parent_id`) and avoids a new table.

2. **Tenant filtering at API level** — The `get_products` handler derives accessible tenants from Cognito group claims and validates the requested `tenant` parameter. No cross-tenant data leakage.

3. **Optimistic locking for persistent orders** — A `version` attribute on Orders enables safe concurrent edits to PresMeet persistent orders.

4. **Mollie replaces Stripe** — A new `mollie_webhook` handler processes payment status callbacks. The existing Stripe integration is deprecated but left in code until migration completes.

5. **Validation in both frontend and backend** — Purchase rules and order item fields are validated client-side for UX, with authoritative enforcement in the `create_order` handler.

## Components and Interfaces

### Backend Components

#### Shared Layer Extensions (`backend/layers/auth-layer/python/shared/`)

| Module                     | Responsibility                                                                                       |
| -------------------------- | ---------------------------------------------------------------------------------------------------- |
| `variant_helpers.py`       | Updated: generate variants from `variant_schema` (replaces `required_attributes` logic)              |
| `product_validation.py`    | Updated: validate `variant_schema`, `order_item_fields`, `purchase_rules`                            |
| `purchase_rules_engine.py` | New: enforce purchase constraints (max_per_order, max_per_member, max_per_club, requires_membership) |
| `item_fields_validator.py` | New: validate Item_Fields_Data against Order_Item_Fields definitions                                 |
| `tenant_resolver.py`       | New: derive accessible tenants from Cognito group claims                                             |
| `mollie_client.py`         | New: Mollie API client (create payment, verify webhook signature)                                    |
| `stock_reservation.py`     | New: atomic stock decrement + sold_count increment on variant records                                |

#### New/Modified Lambda Handlers

| Handler                | Method | Path                      | Description                                                               |
| ---------------------- | ------ | ------------------------- | ------------------------------------------------------------------------- |
| `get_products`         | GET    | `/products`               | Tenant-filtered product listing (modified)                                |
| `get_variants`         | GET    | `/products/{id}/variants` | Get variants for a parent product (new)                                   |
| `create_cart`          | POST   | `/carts`                  | Create cart with `club_id` support (modified)                             |
| `update_cart_items`    | PUT    | `/carts/{id}/items`       | Update cart with variant_id references + Item_Fields_Data (modified)      |
| `create_order`         | POST   | `/orders`                 | Full validation pipeline: purchase rules + item fields + stock (modified) |
| `mollie_webhook`       | POST   | `/mollie-webhook`         | Idempotent Mollie payment status handler (new)                            |
| `admin_record_payment` | POST   | `/admin/payments`         | Record manual payment, recalculate status (modified)                      |
| `admin_create_product` | POST   | `/admin/products`         | Support new three-field schema (modified)                                 |
| `admin_update_product` | PUT    | `/admin/products/{id}`    | Support schema updates with variant regeneration (modified)               |

#### Migration Scripts (`scripts/`)

| Script                           | Description                                                                     |
| -------------------------------- | ------------------------------------------------------------------------------- |
| `migrate_opties_to_variants.py`  | Convert legacy `opties` comma-strings to `variant_schema` + variant records     |
| `migrate_presmeet_config.py`     | Convert PresMeet `config_presmeet_*` records to standard Parent_Product records |
| `migrate_cart_selectedoption.py` | Replace `selectedOption` in cart items with `variant_id` references             |

### Frontend Components

#### New/Modified Components (`frontend/src/modules/webshop/`)

| Component                   | Description                                                                      |
| --------------------------- | -------------------------------------------------------------------------------- |
| `VariantSelector.tsx`       | New: renders axis dropdowns from `variant_schema`, resolves variant              |
| `ItemFieldsForm.tsx`        | New: per-item registration fields based on `order_item_fields`                   |
| `PurchaseRulesFeedback.tsx` | New: displays rule violations (max qty reached, membership required)             |
| `PaymentMethodSelector.tsx` | New: Mollie (iDEAL / credit card) or bank transfer selection                     |
| `ProductCard.tsx`           | Modified: use VariantSelector instead of legacy opties dropdown                  |
| `CartModal.tsx`             | Modified: display `variant_attributes` as axis:value pairs, embed ItemFieldsForm |
| `CheckoutModal.tsx`         | Modified: validate item fields, call Mollie payment flow                         |
| `ProductFilter.tsx`         | Modified: tenant-aware, dynamic groep/subgroep from active products              |

#### New/Modified Components (`frontend/src/modules/products/`)

| Component                   | Description                              |
| --------------------------- | ---------------------------------------- |
| `VariantSchemaEditor.tsx`   | New: visual axis/values editor for admin |
| `OrderItemFieldsEditor.tsx` | New: form builder for order_item_fields  |
| `PurchaseRulesEditor.tsx`   | New: form inputs for purchase_rules      |

#### Services (`frontend/src/modules/webshop/services/`)

| Service     | Description                                                         |
| ----------- | ------------------------------------------------------------------- |
| `api.ts`    | Modified: add variant resolution, Mollie redirect, tenant parameter |
| `mollie.ts` | New: replaces `stripe.ts` — handles Mollie redirect flow            |

### API Contracts

#### POST /orders (create_order)

**Request body:**

```json
{
  "cart_id": "uuid",
  "payment_method": "ideal" | "creditcard" | "bank_transfer",
  "items": [
    {
      "product_id": "prod_xxx",
      "variant_id": "var_xxx",
      "quantity": 2,
      "item_fields_data": [
        { "field_values": { "name": "Jan", "role": "delegate" } },
        { "field_values": { "name": "Piet", "role": "guest" } }
      ]
    }
  ]
}
```

**Response (success — online payment):**

```json
{
  "order_id": "uuid",
  "payment_status": "pending",
  "checkout_url": "https://www.mollie.com/checkout/..."
}
```

**Response (success — bank transfer):**

```json
{
  "order_id": "uuid",
  "payment_status": "unpaid",
  "transfer_instructions": {
    "reference": "ORD-2024-001234",
    "iban": "NL00BANK0123456789",
    "amount": 45.0
  }
}
```

**Response (validation error — 400):**

```json
{
  "error": "purchase_rule_violation",
  "details": {
    "rule": "max_per_member",
    "product_id": "prod_xxx",
    "limit": 2,
    "current_total": 1,
    "requested": 2,
    "remaining_allowed": 1
  }
}
```

#### POST /mollie-webhook

**Request body (from Mollie):**

```json
{ "id": "tr_xxxxx" }
```

**Processing:** Fetch payment status from Mollie API, update order, trigger stock reservation if paid. Idempotent — re-processing the same `id` produces the same final state.

## Data Models

### Parent Product Record (Producten table)

```python
{
    "product_id": "prod_abc123",       # PK
    "is_parent": True,
    "parent_id": None,
    "tenant": "h-dcn" | "presmeet",
    "name": "Club T-shirt",
    "description": "...",
    "price": Decimal("25.00"),
    "active": True,
    "groep": "Kleding",                # Optional, max 50 chars
    "subgroep": "T-shirts",            # Optional, max 50 chars
    "images": ["https://s3.../img1.jpg"],  # Array of up to 10 S3 URLs

    # NEW: Three separated concerns
    "variant_schema": {                # Optional
        "Maat": ["S", "M", "L", "XL"],
        "Gender": ["Male", "Female"]
    },
    "order_item_fields": [             # Optional
        {
            "id": "attendee_name",
            "label": "Naam deelnemer",
            "type": "text",
            "required": True,
            "validation": { "min_length": 2, "max_length": 100 }
        },
        {
            "id": "dietary",
            "label": "Dieetwensen",
            "type": "select",
            "required": False,
            "options": ["Geen", "Vegetarisch", "Veganistisch", "Glutenvrij"]
        }
    ],
    "purchase_rules": {                # Optional
        "max_per_order": 5,
        "max_per_member": 2,
        "max_per_club": 20,
        "min_per_club": 5,
        "requires_membership": True,
        "order_mode": "single"         # "single" | "persistent"
    },

    # LEGACY (preserved read-only after migration)
    "required_attributes": {...},      # Ignored when new fields present
    "legacy_opties": "S,M,L,XL",      # Original opties value post-migration

    "created_by": "admin@h-dcn.nl",
    "created_at": "2024-01-15T10:00:00Z",
    "updated_at": "2024-01-15T10:00:00Z"
}
```

### Variant Record (Producten table)

```python
{
    "product_id": "var_prod_abc123_maat_s_gender_male",  # PK
    "is_parent": False,
    "parent_id": "prod_abc123",        # FK to parent
    "tenant": "h-dcn",
    "name": "Club T-shirt - S / Male",
    "variant_attributes": {
        "Maat": "S",
        "Gender": "Male"
    },
    "price": Decimal("25.00"),         # Inherited from parent or overridden
    "stock": 10,
    "sold_count": 3,
    "allow_oversell": False,
    "active": True,
    "created_at": "2024-01-15T10:00:00Z",
    "updated_at": "2024-01-15T10:00:00Z"
}
```

### Default Variant (for products without variant_schema)

```python
{
    "product_id": "var_prod_xyz_default",
    "is_parent": False,
    "parent_id": "prod_xyz",
    "tenant": "h-dcn",
    "name": "Default Variant",
    "variant_attributes": {},          # Empty = default variant
    "price": Decimal("15.00"),
    "stock": 50,
    "sold_count": 12,
    "allow_oversell": False,
    "active": True,
    "created_at": "2024-01-15T10:00:00Z",
    "updated_at": "2024-01-15T10:00:00Z"
}
```

### Cart Record (Carts table)

```python
{
    "cart_id": "uuid",                 # PK
    "customer_id": "member_123",
    "user_email": "user@example.com",
    "club_id": "NL001",               # NEW: for PresMeet per-club ordering
    "tenant": "h-dcn",                # NEW: tenant context
    "items": [
        {
            "product_id": "prod_abc123",
            "variant_id": "var_prod_abc123_maat_s_gender_male",  # NEW: replaces selectedOption
            "variant_attributes": {"Maat": "S", "Gender": "Male"},  # For display
            "quantity": 2,
            "unit_price": Decimal("25.00"),
            "item_fields_data": [      # NEW: per-item registration data (can be partial)
                {"attendee_name": "Jan Jansen", "dietary": "Geen"},
                {"attendee_name": "", "dietary": ""}  # Partially filled
            ]
        }
    ],
    "total_amount": Decimal("50.00"),
    "created_at": "2024-01-15T10:00:00Z",
    "updated_at": "2024-01-15T12:30:00Z"
}
```

### Order Record (Orders table)

```python
{
    "order_id": "uuid",                # PK
    "user_email": "user@example.com",
    "member_id": "member_123",
    "club_id": "NL001",               # For PresMeet per-club ordering
    "tenant": "h-dcn" | "presmeet",
    "source": "webshop" | "presmeet",
    "cart_id": "uuid",
    "status": "draft" | "submitted" | "locked" | "paid" | "completed",
    "payment_status": "unpaid" | "pending" | "paid" | "partial" | "payment_failed",
    "payment_method": "ideal" | "creditcard" | "bank_transfer",
    "mollie_payment_id": "tr_xxxxx",   # For online payments
    "version": 1,                      # Optimistic locking for persistent orders

    "items": [
        {
            "product_id": "prod_abc123",
            "variant_id": "var_prod_abc123_maat_s_gender_male",
            "variant_attributes": {"Maat": "S", "Gender": "Male"},
            "quantity": 2,
            "unit_price": Decimal("25.00"),
            "line_total": Decimal("50.00"),
            "item_fields_data": [
                {
                    "item_index": 1,
                    "field_id": "attendee_name",
                    "field_label": "Naam deelnemer",
                    "value": "Jan Jansen"
                },
                {
                    "item_index": 1,
                    "field_id": "dietary",
                    "field_label": "Dieetwensen",
                    "value": "Vegetarisch"
                },
                {
                    "item_index": 2,
                    "field_id": "attendee_name",
                    "field_label": "Naam deelnemer",
                    "value": "Piet de Vries"
                },
                {
                    "item_index": 2,
                    "field_id": "dietary",
                    "field_label": "Dieetwensen",
                    "value": "Geen"
                }
            ]
        }
    ],

    "total_amount": Decimal("50.00"),
    "total_paid": Decimal("50.00"),
    "credit": Decimal("0.00"),         # For persistent order overpayments
    "created_at": "2024-01-15T10:00:00Z",
    "updated_at": "2024-01-15T12:30:00Z"
}
```

### Tenant-to-Role Mapping

| Cognito Group     | Grants Tenant |
| ----------------- | ------------- |
| `hdcnLeden`       | `h-dcn`       |
| `Regio_Pressmeet` | `presmeet`    |
| `Regio_All`       | `presmeet`    |

A user with multiple groups sees products from all granted tenants.

## Correctness Properties

_A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees._

### Property 1: Variant generation count equals cartesian product

_For any_ valid `variant_schema` with N axes having C₁, C₂, ..., Cₙ values respectively, the system SHALL generate exactly C₁ × C₂ × ... × Cₙ variant records, each with a unique combination of axis values.

**Validates: Requirements 3.2, 3.3**

### Property 2: Variant schema validation rejects invalid schemas

_For any_ `variant_schema` that contains duplicate values within an axis, an axis with an empty values array, or whose total combinations exceed 100, the validation function SHALL reject the schema and return an error identifying the specific violation.

**Validates: Requirements 3.6, 3.8**

### Property 3: Purchase rules enforcement — max_per_order

_For any_ product with a `max_per_order` constraint and any requested quantity, the enforcement function SHALL reject the request if and only if the quantity exceeds `max_per_order`, and SHALL allow it otherwise.

**Validates: Requirements 5.1, 5.7, 16.2**

### Property 4: Purchase rules enforcement — max_per_member

_For any_ product with a `max_per_member` constraint, any member with existing order history (orders with status "paid" or "pending"), and any new order quantity, the enforcement function SHALL reject the order if and only if (existing_total + new_quantity) > `max_per_member`.

**Validates: Requirements 5.2, 5.8, 16.3**

### Property 5: Purchase rules enforcement — max_per_club

_For any_ product with a `max_per_club` constraint, any club with existing order history (orders with status "paid" or "pending"), and any new order quantity, the enforcement function SHALL reject the order if and only if (club_total + new_quantity) > `max_per_club`.

**Validates: Requirements 5.3, 5.9, 16.4**

### Property 6: Absent purchase rules impose no constraints

_For any_ product where a purchase rule constraint is absent or null, and any valid order quantity, the enforcement function SHALL allow the purchase without applying that constraint.

**Validates: Requirements 5.6, 16.7**

### Property 7: min_per_club cannot exceed max_per_club

_For any_ `purchase_rules` where both `min_per_club` and `max_per_club` are defined, the validation function SHALL reject the configuration if `min_per_club` > `max_per_club`.

**Validates: Requirements 5.4**

### Property 8: Stock reservation correctness

_For any_ order with variant items and quantities, when payment is confirmed (status transitions to "paid"), the stock reservation process SHALL decrement each variant's `stock` by the ordered quantity and increment `sold_count` by the same amount, preserving the invariant: `initial_stock - stock_after = sold_count_after - initial_sold_count = ordered_quantity`.

**Validates: Requirements 6.6**

### Property 9: Stock enforcement prevents overselling

_For any_ variant with `allow_oversell` set to false and `stock` < requested quantity, the system SHALL reject the add-to-cart or order creation request. For any variant with `allow_oversell` true OR `stock` >= requested quantity, the system SHALL allow it.

**Validates: Requirements 6.7, 6.8**

### Property 10: Cart items never contain selectedOption

_For any_ cart item created or updated through the unified pipeline, the item SHALL contain `product_id`, `variant_id`, and `quantity` fields, and SHALL NOT contain a `selectedOption` field.

**Validates: Requirements 6.1, 6.5**

### Property 11: Tenant role derivation

_For any_ set of Cognito group claims, the tenant resolver SHALL derive accessible tenants as: `hdcnLeden` → includes "h-dcn"; `Regio_Pressmeet` OR `Regio_All` → includes "presmeet"; neither → empty set. The derivation SHALL be the union of all granted tenants.

**Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.7**

### Property 12: Tenant access enforcement

_For any_ user requesting products with a tenant parameter, if the requested tenant is not in the user's derived accessible tenants, the API SHALL return 403.

**Validates: Requirements 7.6**

### Property 13: Item fields data count matches quantity

_For any_ order line item with quantity Q where the product has `order_item_fields` defined, the backend SHALL require exactly Q `item_fields_data` entries. Fewer or more SHALL result in rejection.

**Validates: Requirements 4.4, 17.5**

### Property 14: Required field validation

_For any_ field definition with `required: true` and any submitted value, the validation function SHALL reject the submission if the value is empty (per type-specific rules: trimmed empty string for text/email, no selection for select, absent value for number/date), and accept it otherwise.

**Validates: Requirements 4.3, 17.1**

### Property 15: Field constraint validation

_For any_ field definition with validation constraints (min_length, max_length, minimum, maximum, pattern, options) and any submitted value, the validation function SHALL reject the submission if and only if the value violates at least one defined constraint.

**Validates: Requirements 4.5, 17.2**

### Property 16: Opties migration round-trip

_For any_ product with a legacy `opties` comma-separated string, after migration the `variant_schema` SHALL contain a single axis "opties" whose values equal the original string split on comma with each value trimmed. The number of generated variants SHALL equal the number of parsed values.

**Validates: Requirements 11.1, 11.2, 11.3**

### Property 17: Migration idempotence

_For any_ set of products, running the migration script a second time SHALL produce no changes to already-migrated products (detected by presence of `legacy_opties` or existing variant records with matching `parent_id`).

**Validates: Requirements 11.4**

### Property 18: Mollie webhook idempotence

_For any_ Mollie payment event, processing the webhook handler multiple times with the same payment ID SHALL produce the same final order state and SHALL NOT duplicate stock reservations.

**Validates: Requirements 9.11**

### Property 19: Payment status calculation for manual payments

_For any_ order with total T and cumulative manual payments P, the payment_status SHALL be "paid" if P >= T, and "partial" if 0 < P < T. Stock reservation SHALL be triggered when and only when status transitions to "paid".

**Validates: Requirements 9.10**

### Property 20: Item fields data persistence on order

_For any_ valid Item_Fields_Data submitted with an order, after order creation the stored data SHALL preserve the field id, field label, submitted value, and 1-based item index for every entry.

**Validates: Requirements 10.1, 10.5**

### Property 21: CSV export row count

_For any_ set of orders with Item_Fields_Data, the CSV export SHALL produce exactly Σ(Qᵢ × Fᵢ) rows (where Qᵢ is the item quantity and Fᵢ is the number of fields for each line item across all orders), plus one header row.

**Validates: Requirements 10.4**

### Property 22: Quantity decrease removes highest-numbered item data

_For any_ cart item with Q items having Item_Fields_Data, when the quantity is decreased to Q-N, the system SHALL retain field data for items 1 through Q-N and discard field data for items Q-N+1 through Q.

**Validates: Requirements 8.8**

### Property 23: Schema evolution discards orphaned field data

_For any_ cart with Item_Fields_Data where the product's `order_item_fields` definition changes, on next load the system SHALL discard field values whose `field_id` no longer exists in the current definition and retain values whose `field_id` still exists.

**Validates: Requirements 8.9**

### Property 24: Persistent order — one per club

_For any_ product with `order_mode: "persistent"` and any club, the system SHALL maintain at most one active order per club. Subsequent purchases by the same club SHALL modify the existing order rather than creating a new one.

**Validates: Requirements 12.9**

### Property 25: Optimistic locking rejects stale writes

_For any_ persistent order, if two concurrent modifications attempt to write with the same version number, exactly one SHALL succeed and the other SHALL be rejected with a conflict error.

**Validates: Requirements 12.13**

### Property 26: Legacy field precedence

_For any_ product that has both a `required_attributes` field and any of the three new fields (`variant_schema`, `order_item_fields`, `purchase_rules`), the system SHALL ignore `required_attributes` entirely and use only the new fields.

**Validates: Requirements 1.8**

### Property 27: Variant resolution

_For any_ product with a `variant_schema` and any complete set of axis selections (one value per axis), the variant resolver SHALL return exactly one variant record whose `variant_attributes` match the selections, or indicate no match if no such variant exists.

**Validates: Requirements 15.3, 15.5**

## Error Handling

### Backend Error Responses

All error responses follow a consistent structure:

```json
{
  "error": "<error_code>",
  "message": "<human-readable message>",
  "details": {
    /* context-specific data */
  }
}
```

| Scenario                       | HTTP Status | Error Code                     | Details                            |
| ------------------------------ | ----------- | ------------------------------ | ---------------------------------- |
| Purchase rule violated         | 400         | `purchase_rule_violation`      | rule, product_id, limit, remaining |
| Item fields validation failed  | 400         | `item_fields_validation_error` | item_index, field_id, constraint   |
| Item fields count mismatch     | 400         | `item_fields_count_mismatch`   | line_item_index, expected, actual  |
| Insufficient stock             | 400         | `insufficient_stock`           | variant_id, available, requested   |
| Variant not found              | 404         | `variant_not_found`            | product_id, variant_id             |
| Tenant access denied           | 403         | `tenant_access_denied`         | requested_tenant, allowed_tenants  |
| Optimistic lock conflict       | 409         | `version_conflict`             | order_id, current_version          |
| Mollie payment creation failed | 502         | `payment_provider_error`       | provider, reason                   |
| Schema exceeds variant limit   | 400         | `variant_limit_exceeded`       | total_combinations, max_allowed    |

### Idempotency and Retries

- **Mollie webhook**: Uses `mollie_payment_id` as idempotency key. The handler fetches current payment status from Mollie API and only transitions order state forward (never backward). Stock reservation is guarded by a conditional update (`stock_reserved = false` → `true`).

- **Stock reservation**: Uses DynamoDB conditional expressions (`SET stock = stock - :qty IF stock >= :qty AND stock_reserved_for_order <> :order_id`) to prevent double-deduction.

- **Persistent order updates**: Optimistic locking via `version` attribute. Client must send current version; update fails with 409 if version mismatch.

### Graceful Degradation

- If Mollie API is unavailable during order creation, the handler returns a 502 with instructions to retry. The order is NOT created.
- If variant stock check fails due to DynamoDB throttling, the handler returns a 503 with a Retry-After header.
- If the `required_attributes` to new-field migration is incomplete for a product, the frontend falls back to the legacy opties-based rendering.

## Testing Strategy

### Property-Based Testing (Hypothesis)

The feature uses **Hypothesis** (Python) for property-based testing of backend logic. Each property from the Correctness Properties section maps to one Hypothesis test.

**Configuration:**

- Minimum 100 examples per test (`@settings(max_examples=100)`)
- Each test tagged with: `# Feature: webshop-product-unification, Property N: <title>`
- Test file: `backend/tests/unit/test_product_unification_properties.py`

**Key generators:**

- `variant_schema_strategy()` — generates valid schemas with 1-5 axes, 1-20 values each
- `order_item_fields_strategy()` — generates valid field definition arrays
- `purchase_rules_strategy()` — generates valid purchase rule objects
- `cart_item_strategy()` — generates cart items with variant references
- `order_history_strategy()` — generates member/club order histories for constraint checking

### Unit Tests (pytest)

- Specific examples and edge cases for each handler
- Mocked DynamoDB (moto) for integration-style tests
- Focus areas: validation error messages, Mollie webhook state transitions, migration edge cases

### Frontend Tests (Jest + React Testing Library)

- Component rendering with various product configurations
- VariantSelector interaction (axis selection → variant resolution)
- ItemFieldsForm validation feedback
- PurchaseRulesFeedback messaging
- CartModal variant_attributes display

### Integration Tests

- End-to-end order creation flow (cart → order → payment → stock)
- Mollie webhook processing with mock Mollie responses
- Tenant filtering with various role combinations
- Migration script on realistic data fixtures

### Test Balance

- Property tests cover: validation logic, enforcement logic, data transformation, stock arithmetic, idempotency
- Unit tests cover: specific error messages, API response formats, edge cases (empty input, null fields), migration of specific known products
- Integration tests cover: full request/response flows, DynamoDB interactions, Mollie API integration, concurrent access scenarios
