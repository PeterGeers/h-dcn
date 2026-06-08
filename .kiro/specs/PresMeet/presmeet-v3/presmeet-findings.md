# PresMeet v3 — Feasibility Analysis: Using the Standard Webshop Pipeline

## Executive Summary

The standard webshop pipeline **already has** most of the building blocks needed to replace the dedicated PresMeet booking system. The `create_order` handler already supports `tenant: 'presmeet'`, `club_id` scoping, persistent order mode, `order_item_fields` for per-item data collection, and `purchase_rules` for business constraints. The remaining gaps are manageable extensions rather than fundamental rewrites.

**Verdict:** Unification is feasible and recommended. ~70% of PresMeet's current functionality maps directly to existing webshop features. The remaining ~30% (cross-item validation, the booking wizard UX, onboarding) requires targeted extensions.

---

## 1. Current State: Two Parallel Pipelines

| Aspect          | Standard Webshop                         | PresMeet (current)                              |
| --------------- | ---------------------------------------- | ----------------------------------------------- |
| Frontend        | WebshopPage → Cart → Checkout            | PresMeetPage → BookingForm → Submit             |
| Cart API        | `POST /cart` (create_cart)               | `PUT /presmeet/booking` (save_presmeet_booking) |
| Order API       | `POST /orders` (create_order)            | `POST /presmeet/booking/submit`                 |
| Payment         | Mollie (iDEAL, credit, bank transfer)    | Mollie (separate endpoint)                      |
| Products        | Producten table, `tenant: 'h-dcn'`       | Producten table, `source: 'presmeet_config'`    |
| Scoping         | Per member (`member_id`)                 | Per club (`club_id`)                            |
| Order lifecycle | draft → pending → paid/failed            | draft → submitted → locked                      |
| Per-item data   | `order_item_fields` + `item_fields_data` | `attributes` JSON blob                          |

---

## 2. What the Standard Pipeline Already Supports

### 2.1 Tenant Isolation ✅

The `create_cart` handler already resolves tenant from Cognito groups and sets `tenant: 'presmeet'` on the cart. The `create_order` handler passes `tenant` through to the order record.

### 2.2 Club-Scoped Ordering ✅

Both `create_cart` and `create_order` already call `get_club_id(user_email)` when `tenant == 'presmeet'`. The cart and order are tagged with `club_id`.

### 2.3 Persistent Order Mode ✅

`create_order` already implements `_find_persistent_order(club_id, product_id)` with optimistic locking (version field). If a persistent order exists for the club, it updates instead of creating a new one.

### 2.4 Per-Item Data Collection ✅

The `UnifiedProduct.order_item_fields` schema defines typed fields (text, select, date, number) with validation. `create_order` validates `item_fields_data` against the product's field definitions. This maps directly to PresMeet's "name", "role", "flight", "date", "time" attributes.

### 2.5 Purchase Rules ✅

`PurchaseRules` already supports: `max_per_order`, `max_per_member`, `max_per_club`, `min_per_club`, `requires_membership`, `order_mode`. This covers all PresMeet constraints.

### 2.6 Variant Schema ✅

T-shirt sizes and genders can be modeled as variants (`variant_schema: { "Size": ["S","M","L","XL","XXL","3XL","4XL"], "Gender": ["Male","Female"] }`), each with independent stock.

### 2.7 Mollie Payments ✅

`create_order` already handles Mollie payment creation with redirect URL.

---

## 3. Gaps That Need Extensions

### 3.1 Cross-Item Validation Rules ❌

**Problem:** PresMeet has composite rules like "party ticket count must equal delegates attending party + guests" and "min 1 meeting ticket per club". The standard pipeline validates items independently.

**Solution:** Add a `cross_item_rules` field to products or a tenant-level config that defines inter-product constraints. Validate at order submission time.

**Example schema:**

```json
{
  "cross_item_rules": [
    {
      "rule": "sum_match",
      "source_product": "meeting_ticket",
      "source_field": "attend_party",
      "source_value": true,
      "target_product": "party_ticket",
      "target_field": "person_type",
      "target_value": "delegate",
      "message": "Party tickets for delegates must match delegates attending party"
    }
  ]
}
```

**Alternative (simpler):** Handle cross-item validation in a PresMeet-specific validation Lambda triggered before order submission. This avoids polluting the generic webshop with event-specific logic.

### 3.2 Multi-Person Item Linking ❌

**Problem:** A meeting ticket, party ticket, and t-shirt can all belong to the same person (delegate "Jan de Vries"). The standard cart has no concept of linking items to a shared entity.

**Solution:** Use `order_item_fields` with a shared `person_name` field across products. The frontend booking wizard groups items by person during editing, and the backend flattens them into independent cart items with the name field populated.

**This is a UX concern, not a backend limitation.** The backend doesn't need item linking — it just stores per-item field values. The frontend booking form provides the wizard UX that groups items by person.

### 3.3 Booking Wizard UX (Frontend Only) ❌

**Problem:** PresMeet's BookingForm is person-centric (add delegate → configure their tickets). The standard webshop is product-centric (browse → add to cart).

**Solution:** Keep a PresMeet-specific booking form component that internally builds cart items from the person-centric form data. The form submits to the standard cart/order API. This is purely a frontend concern.

**Key insight:** The BookingForm already does this transformation today in `usePresMeetBooking.ts` — it maps delegates/guests/transfers into `CartItem[]`. We just need it to target the standard cart API instead of `/presmeet/booking`.

### 3.4 Draft Save Without Validation ❌

**Problem:** PresMeet allows saving incomplete drafts (Req 8.6). The standard `create_cart` validates item structure.

**Solution:** The cart already accepts partial `item_fields_data`. The cart just stores items — validation only runs at order submission time in `create_order`. This is actually already supported.

### 3.5 Order Status: "locked" ❌

**Problem:** PresMeet has a `locked` status (admin locks orders after the event deadline). The webshop doesn't have this concept.

**Solution:** Add `locked` to the order status enum. The `admin_lock_orders` handler already exists — extend it to support locking by tenant/event.

### 3.6 Onboarding Flow ❌

**Problem:** First-time PresMeet users need to select their club before they can order.

**Solution:** This remains a PresMeet-specific frontend page. It writes `club_id` to the member record, after which the standard cart flow picks it up via `get_club_id()`.

---

## 4. Product Modeling

How to model PresMeet's 4 product types as standard webshop products:

### Meeting Ticket

```json
{
  "product_id": "presmeet_meeting_ticket",
  "tenant": "presmeet",
  "name": "Presidents' Meeting Ticket",
  "price": 50.0,
  "active": true,
  "is_parent": true,
  "variant_schema": null,
  "order_item_fields": [
    {
      "id": "name",
      "label": "Delegate Name",
      "type": "text",
      "required": true,
      "validation": { "min_length": 1, "max_length": 100 }
    },
    {
      "id": "role",
      "label": "Role / Function",
      "type": "text",
      "required": true,
      "validation": { "min_length": 1, "max_length": 100 }
    },
    {
      "id": "attend_party",
      "label": "Attend Party",
      "type": "select",
      "required": true,
      "options": ["yes", "no"]
    }
  ],
  "purchase_rules": {
    "max_per_club": 3,
    "min_per_club": 1,
    "order_mode": "persistent"
  }
}
```

### Party Ticket

```json
{
  "product_id": "presmeet_party_ticket",
  "tenant": "presmeet",
  "name": "Party Ticket",
  "price": 99.5,
  "active": true,
  "is_parent": true,
  "order_item_fields": [
    { "id": "name", "label": "Guest Name", "type": "text", "required": true },
    {
      "id": "person_type",
      "label": "Type",
      "type": "select",
      "required": true,
      "options": ["delegate", "guest"]
    }
  ],
  "purchase_rules": {
    "max_per_club": 13,
    "order_mode": "persistent"
  }
}
```

### T-Shirt

```json
{
  "product_id": "presmeet_tshirt",
  "tenant": "presmeet",
  "name": "PresMeet T-Shirt",
  "price": 25.0,
  "active": true,
  "is_parent": true,
  "variant_schema": {
    "Size": ["S", "M", "L", "XL", "XXL", "3XL", "4XL"],
    "Gender": ["Male", "Female"]
  },
  "order_item_fields": [
    { "id": "name", "label": "Person Name", "type": "text", "required": true }
  ],
  "purchase_rules": {
    "max_per_club": 13,
    "order_mode": "persistent"
  }
}
```

### Airport Transfer

```json
{
  "product_id": "presmeet_airport_transfer",
  "tenant": "presmeet",
  "name": "Airport Transfer",
  "price": 5.0,
  "active": true,
  "is_parent": true,
  "variant_schema": {
    "Direction": ["Pickup", "Dropoff"],
    "Airport": ["AMS", "RTM", "EIN"]
  },
  "order_item_fields": [
    {
      "id": "flight",
      "label": "Flight Number",
      "type": "text",
      "required": true
    },
    { "id": "date", "label": "Date", "type": "date", "required": true },
    { "id": "time", "label": "Time", "type": "text", "required": true },
    {
      "id": "persons",
      "label": "Number of Persons",
      "type": "number",
      "required": true,
      "validation": { "minimum": 1, "maximum": 20 }
    }
  ],
  "purchase_rules": {
    "max_per_club": 20,
    "order_mode": "persistent"
  }
}
```

---

## 5. Architecture: Unified Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  Frontend                                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  PresMeet Booking Form                Standard Webshop           │
│  (person-centric wizard)              (product-centric browse)   │
│         │                                      │                 │
│         ▼                                      ▼                 │
│  ┌──────────────────────────────────────────────────┐           │
│  │        Shared Cart State (Carts table)            │           │
│  │        tenant: 'presmeet' | 'h-dcn'               │           │
│  │        club_id (for presmeet)                     │           │
│  └──────────────────────────────────────────────────┘           │
│         │                                      │                 │
│         ▼                                      ▼                 │
│  ┌──────────────────────────────────────────────────┐           │
│  │        Shared Checkout / Order Placement           │           │
│  │        POST /orders (create_order)                │           │
│  └──────────────────────────────────────────────────┘           │
│                        │                                         │
└────────────────────────┼─────────────────────────────────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Backend (shared)                                                │
├─────────────────────────────────────────────────────────────────┤
│  create_cart → create_order → Mollie payment                     │
│       │              │              │                             │
│       ▼              ▼              ▼                             │
│    Carts          Orders        Payments                         │
│  (DynamoDB)     (DynamoDB)     (DynamoDB)                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. What Can Be Removed After Unification

| Current PresMeet Component        | Replacement                                            |
| --------------------------------- | ------------------------------------------------------ |
| `POST /presmeet/booking` (save)   | `POST /cart` + `PUT /cart` (standard cart)             |
| `POST /presmeet/booking/submit`   | `POST /orders` (create_order with persistent mode)     |
| `POST /presmeet/payment`          | Already uses Mollie — same endpoint as webshop         |
| `POST /presmeet/admin/lock`       | `POST /admin/orders/lock` (existing)                   |
| `POST /presmeet/admin/unlock`     | `POST /admin/orders/unlock` (existing)                 |
| `POST /presmeet/admin/payment`    | `POST /admin/payments` (existing admin_record_payment) |
| `GET /presmeet/config`            | Product data fetched from standard product API         |
| `POST /presmeet/booking/validate` | Validation in `create_order` at submission             |
| `presmeetService.ts` (frontend)   | Standard `apiService` / `cartService`                  |
| `usePresMeetBooking.ts`           | Simplified hook using standard cart hooks              |
| PresMeet types (`presmeet.ts`)    | Removed — use `unifiedProduct.types.ts`                |

**Keep (PresMeet-specific):**

- `BookingForm.tsx` — person-centric wizard (but targets standard cart API)
- `OnboardingFlow.tsx` — club selection
- `AdminDashboard.tsx` — PresMeet admin views (reports, bulk lock)
- `/presmeet/clubs` endpoints — onboarding
- `/presmeet/admin/report` — event-specific reporting
- Cross-item validation logic (frontend + one backend validation Lambda)

---

## 7. Migration Path

### Phase 1: Product Migration

1. Create new UnifiedProduct records for the 4 PresMeet product types (see Section 4)
2. Generate variant records for t-shirts and transfers
3. Keep legacy `config_presmeet_*` records temporarily

### Phase 2: Backend Alignment

1. Add `locked` to order status enum
2. Add PresMeet cross-item validation as a pre-submission hook in `create_order`
3. Verify `purchase_rules` enforcement works for PresMeet constraints
4. Ensure `order_item_fields` validation handles all PresMeet field types

### Phase 3: Frontend Migration

1. Refactor `BookingForm` to build standard `CartItem[]` (with `variant_id` + `item_fields_data`)
2. Replace `presmeetService.saveBooking()` with standard cart API calls
3. Replace `presmeetService.submitBooking()` with standard order placement
4. Keep the person-centric wizard UX — only change the API target

### Phase 4: Cleanup

1. Remove dedicated PresMeet booking endpoints (6 Lambda handlers)
2. Remove legacy `config_presmeet_*` product records
3. Remove `presmeet.ts` type file (use unified types)
4. Update admin dashboard to use standard order queries with tenant filter

---

## 8. Risk Assessment

| Risk                                                              | Impact | Mitigation                                                                |
| ----------------------------------------------------------------- | ------ | ------------------------------------------------------------------------- |
| Breaking existing PresMeet bookings during migration              | High   | Run both systems in parallel during Phase 3, feature-flag switch          |
| Cross-item validation complexity in shared pipeline               | Medium | Isolate in a PresMeet-specific validation module, not in core order logic |
| Persistent order conflicts (two delegates editing simultaneously) | Medium | Already mitigated by optimistic locking (version field)                   |
| Admin reporting changes                                           | Low    | Reports query orders by tenant — filter is straightforward                |
| T-shirt stock tracking across variants                            | Low    | Standard variant stock system handles this                                |

---

## 9. Effort Estimate

| Phase                       | Effort        | Complexity                            |
| --------------------------- | ------------- | ------------------------------------- |
| Phase 1: Product Migration  | 1-2 days      | Low (data migration script)           |
| Phase 2: Backend Alignment  | 2-3 days      | Medium (status enum, validation hook) |
| Phase 3: Frontend Migration | 3-5 days      | Medium-High (form refactor, API swap) |
| Phase 4: Cleanup            | 1-2 days      | Low (delete code, remove endpoints)   |
| **Total**                   | **7-12 days** |                                       |

---

## 10. Reporting Design

### 10.1 Report Types

All reports query the **Orders table** only — since PresMeet uses no cart (orders are the working document from first save):

Each report entry includes `status` and `payment_status` fields:

- `draft` — club is still editing (not yet submitted)
- `submitted` — club considers it ready
- `locked` — admin finalized it

Payment status (independent):

- `unpaid` — no payments received
- `partial` — some payments, balance remaining
- `paid` — fully paid

This gives admins full visibility: what's being worked on, what's confirmed, and what's paid.

| Report    | Description                                          | Grouping                   |
| --------- | ---------------------------------------------------- | -------------------------- |
| Attendees | All persons attending the meeting                    | By status, then club       |
| Party     | All persons attending the party (delegates + guests) | By status, then club       |
| T-Shirts  | All t-shirt orders with size/gender                  | By size, then status       |
| Pickup    | Airport pickups sorted by date/time                  | By airport, then date/time |
| Dropoff   | Airport dropoffs sorted by date/time                 | By airport, then date/time |
| Financial | Payment status per club                              | By club                    |
| Overview  | Summary counts by status                             | By product type            |

### 10.2 API Endpoint

Single endpoint, report type as query parameter:

```
GET /admin/reports/presmeet?type={report_type}&format={json|csv}
```

**Parameters:**

- `type`: `attendees` | `party` | `tshirts` | `pickups` | `dropoffs` | `financial` | `overview`
- `format`: `json` (default) | `csv`
- `status`: optional filter — `draft`, `submitted`, `locked`, or `all` (default: `all`)
- `payment_status`: optional filter — `unpaid`, `partial`, `paid`, or `all` (default: `all`)

**Auth:** Requires `Products_Read` or `Webshop_Management` + `Regio_Pressmeet` or `Regio_All`

### 10.3 Report Schemas

Every report entry includes `status` and `source` fields:

- `status`: `draft` | `submitted` | `locked`
- `source`: `cart` (still being edited) | `order` (submitted/locked)

#### Attendees Report

```json
{
  "report_type": "attendees",
  "generated_at": "2026-09-01T10:00:00Z",
  "total_count": 45,
  "by_status": { "draft": 8, "submitted": 25, "locked": 12 },
  "entries": [
    {
      "club_name": "HD Club Berlin",
      "club_id": "club_berlin",
      "name": "Hans Müller",
      "role": "President",
      "attend_party": true,
      "status": "submitted",
      "source": "order"
    },
    {
      "club_name": "HD Club Paris",
      "club_id": "club_paris",
      "name": "Pierre Dupont",
      "role": "President",
      "attend_party": true,
      "status": "draft",
      "source": "cart"
    }
  ]
}
```

**CSV columns:** `Club, Name, Role, Attend Party, Status, Source`

#### Party Report

```json
{
  "report_type": "party",
  "generated_at": "2026-09-01T10:00:00Z",
  "total_count": 62,
  "by_status": { "draft": 10, "submitted": 35, "locked": 17 },
  "entries": [
    {
      "club_name": "HD Club Berlin",
      "club_id": "club_berlin",
      "name": "Hans Müller",
      "person_type": "delegate",
      "status": "submitted",
      "source": "order"
    },
    {
      "club_name": "HD Club Berlin",
      "club_id": "club_berlin",
      "name": "Anna Müller",
      "person_type": "guest",
      "status": "submitted",
      "source": "order"
    }
  ]
}
```

**CSV columns:** `Club, Name, Type (Delegate/Guest), Status, Source`

#### T-Shirt Report

```json
{
  "report_type": "tshirts",
  "generated_at": "2026-09-01T10:00:00Z",
  "total_count": 38,
  "by_status": { "draft": 5, "submitted": 22, "locked": 11 },
  "summary": {
    "S_Male": 2,
    "M_Male": 5,
    "L_Male": 12,
    "XL_Male": 8,
    "XXL_Male": 3,
    "3XL_Male": 1,
    "4XL_Male": 0,
    "S_Female": 1,
    "M_Female": 3,
    "L_Female": 2,
    "XL_Female": 1
  },
  "summary_by_status": {
    "draft": { "L_Male": 3, "M_Female": 2 },
    "submitted": { "XL_Male": 5, "L_Male": 7, "M_Male": 4 },
    "locked": { "L_Male": 2, "S_Male": 2, "M_Male": 1 }
  },
  "entries": [
    {
      "club_name": "HD Club Berlin",
      "name": "Hans Müller",
      "size": "XL",
      "gender": "Male",
      "status": "submitted",
      "source": "order"
    }
  ]
}
```

**CSV columns:** `Club, Name, Size, Gender, Status, Source`

#### Pickup Report

```json
{
  "report_type": "pickups",
  "generated_at": "2026-09-01T10:00:00Z",
  "total_persons": 28,
  "by_status": { "draft": 4, "submitted": 16, "locked": 8 },
  "entries": [
    {
      "airport": "AMS",
      "date": "2026-09-12",
      "time": "14:30",
      "flight": "KL1234",
      "persons": 2,
      "club_name": "HD Club Berlin",
      "names": ["Hans Müller", "Anna Müller"],
      "status": "submitted",
      "source": "order"
    },
    {
      "airport": "AMS",
      "date": "2026-09-12",
      "time": "16:00",
      "flight": "AF1880",
      "persons": 1,
      "club_name": "HD Club Paris",
      "names": ["Pierre Dupont"],
      "status": "draft",
      "source": "cart"
    }
  ]
}
```

**CSV columns:** `Airport, Date, Time, Flight, Persons, Club, Names, Status, Source`

**Sort order:** Airport → Date → Time

#### Dropoff Report

Same schema as Pickup, with `report_type: "dropoffs"`.

**Sort order:** Airport → Date → Time

#### Financial Overview

```json
{
  "report_type": "financial",
  "generated_at": "2026-09-01T10:00:00Z",
  "totals": {
    "total_charged": 12500.0,
    "total_paid": 9800.0,
    "total_outstanding": 2700.0,
    "total_draft_value": 3200.0
  },
  "entries": [
    {
      "club_name": "HD Club Berlin",
      "club_id": "club_berlin",
      "status": "submitted",
      "source": "order",
      "payment_status": "partial",
      "total_amount": 450.0,
      "total_paid": 250.0,
      "outstanding": 200.0,
      "item_counts": {
        "meeting_ticket": 3,
        "party_ticket": 5,
        "tshirt": 4,
        "airport_transfer": 2
      }
    },
    {
      "club_name": "HD Club Paris",
      "club_id": "club_paris",
      "status": "draft",
      "source": "cart",
      "payment_status": "unpaid",
      "total_amount": 325.0,
      "total_paid": 0,
      "outstanding": 325.0,
      "item_counts": {
        "meeting_ticket": 2,
        "party_ticket": 3,
        "tshirt": 2,
        "airport_transfer": 1
      }
    }
  ]
}
```

**CSV columns:** `Club, Status, Source, Payment Status, Total, Paid, Outstanding, Tickets, Party, T-Shirts, Transfers`

### 10.4 Implementation Approach

**Direct query (recommended for PresMeet scale)**

PresMeet has ~30-50 clubs with ~10 items each = ~500 items total. Single table query:

```python
def generate_report(report_type, status_filter):
    # Single query: Orders table, tenant='presmeet'
    orders = query_orders(tenant='presmeet', status=status_filter)

    # Flatten all items across orders, enriching with club_name and status
    all_items = []
    for order in orders:
        for item in order.get('items', []):
            item['club_name'] = order.get('club_name', order.get('club_id', 'Unknown'))
            item['club_id'] = order.get('club_id')
            item['status'] = order.get('status')  # draft, submitted, locked
            item['payment_status'] = order.get('payment_status', 'unpaid')
            item['source'] = 'order'
            all_items.append(item)

    # Filter by product_id based on report_type
    if report_type == 'attendees':
        items = [i for i in all_items if i['product_id'] == 'presmeet_meeting_ticket']
    elif report_type == 'party':
        items = [i for i in all_items if i['product_id'] == 'presmeet_party_ticket']
    # ... etc

    # Extract fields from item_fields_data and variant_attributes
    # Apply status_filter if specified
    # Sort and format
    # Return JSON or generate CSV
```

No deduplication needed — one order per club, one table to query.

### 10.5 Frontend Admin UI

The admin dashboard shows a tabbed/dropdown report selector with status filtering:

```
┌─────────────────────────────────────────────────────────────────┐
│  PresMeet Reports                                                │
├─────────────────────────────────────────────────────────────────┤
│  [Attendees ▼]  [Source: All ▼]  [Status: All ▼]  [📥 CSV]     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Total: 45 attendees from 15 clubs                               │
│  Draft: 8  |  Submitted: 25  |  Locked: 12                      │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Club              │ Name          │ Role      │ Status     │  │
│  ├───────────────────┼───────────────┼───────────┼────────────┤  │
│  │ HD Club Berlin    │ Hans Müller   │ President │ ✅ locked   │  │
│  │ HD Club Berlin    │ Fritz Weber   │ Secretary │ ✅ locked   │  │
│  │ HD Club Wien      │ Karl Schmidt  │ President │ 📋 submitted│  │
│  │ HD Club Paris     │ Pierre Dupont │ President │ ✏️ draft    │  │
│  │ ...               │ ...           │ ...       │ ...        │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Status indicators:**

- ✏️ `draft` — club is still editing their cart (not yet submitted)
- 📋 `submitted` — order submitted, awaiting payment/lock
- ✅ `locked` — finalized by admin

This lets admins quickly see:

- Which clubs haven't submitted yet (nudge them)
- Which clubs have submitted but aren't locked (review needed)
- What's finalized

For transfer reports, an additional grouping header by airport + date with status:

```
┌─────────────────────────────────────────────────────────────────┐
│  📍 AMS - Schiphol                                               │
│  ─────────────────────────────────────────────────────────────── │
│  12 Sep 2026, 14:30 — KL1234 (2 persons) ✅ locked              │
│    • Hans Müller (HD Club Berlin)                                │
│    • Anna Müller (HD Club Berlin)                                │
│                                                                  │
│  12 Sep 2026, 15:45 — LH890 (3 persons) 📋 submitted            │
│    • Karl Schmidt (HD Club Wien)                                 │
│    • Maria Schmidt (HD Club Wien)                                │
│    • Johann Huber (HD Club Wien)                                 │
│                                                                  │
│  12 Sep 2026, 16:00 — AF1880 (1 person) ✏️ draft                │
│    • Pierre Dupont (HD Club Paris)                               │
│                                                                  │
│  📍 EIN - Eindhoven                                              │
│  ─────────────────────────────────────────────────────────────── │
│  12 Sep 2026, 13:00 — FR456 (1 person) 📋 submitted             │
│    • Jean Lefèvre (HD Club Bruxelles)                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 10.6 Key Insight: No Extra Infrastructure Needed

Because all PresMeet data is in standard cart items and order items with typed fields, reports are just **filtered views** over the Carts + Orders tables. No separate reporting tables, no ETL, no pre-aggregation. The `item_fields_data` structure gives you all the columns you need.

The addition of cart data means admins can see the full pipeline:

- **What's coming** (drafts in carts) — useful for planning logistics
- **What's confirmed** (submitted orders) — actionable for organization
- **What's finalized** (locked orders) — the definitive lists

This is a significant simplification over the current system which has a dedicated `admin_generate_report` Lambda that writes multiple JSON files to S3.

---

## 11. Revised Architecture: No Cart for PresMeet

### 11.1 Why the Cart Is Problematic for PresMeet

After analyzing the current cart handlers (`create_cart`, `update_cart_items`), several issues arise if PresMeet were to use the standard shopping cart:

| Issue                                | Description                                                                                                                                                                                 | Impact                                                       |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| **variant_id required**              | `validate_cart_items()` requires every item to have a `variant_id`. PresMeet's meeting tickets and party tickets have no variants — they're single products with per-item data fields only. | Would need dummy "default" variants for non-variant products |
| **Stock validation on every update** | `_validate_and_process_items()` checks stock availability for every cart update. PresMeet items don't have traditional stock — they have `max_per_club` limits.                             | Would reject valid items if no variant stock record exists   |
| **Variant-product linkage check**    | `_validate_variant_for_product()` verifies the variant belongs to the parent product. If a product has no variants (just order_item_fields), this fails.                                    | Need to handle "variantless" products                        |
| **Cart ownership = user**            | Cart is scoped to `user_email`. PresMeet is club-scoped — multiple delegates from the same club shouldn't each have their own cart.                                                         | Club_id already handled, but conceptual mismatch             |
| **Cart is ephemeral**                | Cart is a temporary holding area before order creation. PresMeet needs persistent editing over days/weeks.                                                                                  | Cart TTL/cleanup could delete unsubmitted bookings           |
| **No "save draft without items"**    | `create_cart` requires a `customer_id` and items are validated immediately. PresMeet's "save draft" needs to store partial/incomplete data.                                                 | Would need to relax validation for draft saves               |

### 11.2 The Simpler Model: Order-Only (No Cart)

Since persistent mode already allows updating orders in-place, the cart step is unnecessary overhead for PresMeet. The simplified flow:

```
┌──────────────────────────────────────────────────────────────┐
│  First visit → POST /orders/presmeet                          │
│    Creates order with status: 'draft', items: []              │
│                                                               │
│  Every save → PUT /orders/{order_id}                          │
│    Updates items in-place (optimistic locking via version)     │
│    No validation enforced (draft mode)                        │
│                                                               │
│  Submit → POST /orders/{order_id}/submit                      │
│    Validates all items + cross-item rules                     │
│    Sets status: 'submitted'                                   │
│                                                               │
│  Pay → POST /orders/{order_id}/pay                            │
│    Creates Mollie payment for outstanding amount              │
│    Webhook updates payment_status                             │
│                                                               │
│  Lock → POST /admin/orders/{order_id}/lock (admin only)       │
│    Sets status: 'locked', no more edits allowed               │
└──────────────────────────────────────────────────────────────┘
```

### 11.3 Order Lifecycle with Payment

```
                    ┌─────────────┐
                    │   draft     │ ← user editing
                    └──────┬──────┘
                           │ submit
                           ▼
                    ┌─────────────┐
              ┌────▶│  submitted  │◀──── user can still edit
              │     └──────┬──────┘      (resets to draft, re-submit)
              │            │
              │            │ pay (partial or full)
              │            ▼
              │     ┌─────────────┐
              │     │payment_status│
              │     │ unpaid → partial → paid │
              │     └─────────────┘
              │            │
              │            │ admin lock
              │            ▼
              │     ┌─────────────┐
              └─────│   locked    │ ← no more changes
                    └─────────────┘
```

**Payment status** is tracked independently:

- `unpaid` — no payments recorded
- `partial` — some payments, outstanding > 0
- `paid` — total_paid >= total_amount

**Key rule:** A user can edit their order at any status EXCEPT `locked`. If they edit after submitting, the status reverts to `draft` until they re-submit. This keeps the admin view clean — "submitted" means the club considers it ready.

### 11.4 Payment Integration (Mollie)

```
POST /orders/{order_id}/pay
├── Validates: order exists, belongs to user's club, not locked
├── Calculates: outstanding = total_amount - total_paid
├── Creates: Mollie payment for outstanding amount
├── Returns: { checkout_url, payment_id, amount }
└── User redirects to Mollie
        │
        ▼
POST /payments/webhook (Mollie callback)
├── Validates: Mollie signature
├── Updates: Payments table record
├── Updates: order.payment_status (unpaid → partial → paid)
└── Updates: order.total_paid

POST /admin/orders/{order_id}/payment (admin manual)
├── Records: offline bank transfer
├── Updates: same fields as webhook
└── Returns: updated payment_status
```

**Payment timing:**

- Club can pay at any point after first save (even in draft)
- Club can pay partial amounts (multiple Mollie sessions)
- If order items change after payment, outstanding recalculates
- Overpayment (order shrinks after payment) → admin handles refund manually

**Payment methods:**

- iDEAL (primary, instant)
- Bank transfer (reference-based, admin confirms receipt)

### 11.5 Impact on Reports

With the no-cart model, reporting becomes even simpler — **one table, one query:**

```python
def generate_report(report_type, status_filter):
    # Single query: Orders table, tenant='presmeet'
    orders = query_orders(tenant='presmeet', status=status_filter)

    # All statuses visible: draft, submitted, locked
    # Payment status also available: unpaid, partial, paid
    ...
```

No deduplication needed. No cart/order merge. Every club's state is in one place.

### 11.6 Updated Report Status Model

Reports now show both order lifecycle status AND payment status:

| Status    | Payment | Icon | Meaning                             |
| --------- | ------- | ---- | ----------------------------------- |
| draft     | unpaid  | ✏️   | Club editing, not submitted         |
| submitted | unpaid  | 📋   | Submitted, awaiting payment         |
| submitted | partial | 💰   | Partially paid                      |
| submitted | paid    | ✅   | Fully paid, awaiting lock           |
| locked    | paid    | 🔒   | Finalized                           |
| locked    | unpaid  | ⚠️   | Locked but unpaid (needs follow-up) |

---

## 12. Recommendation

**Proceed with unification using the no-cart model.** The infrastructure is already in place. The main work is:

1. Create/adapt order endpoints for PresMeet: `POST /orders/presmeet` (create), `PUT /orders/{id}` (update), `POST /orders/{id}/submit` (validate + submit)
2. Add `POST /orders/{order_id}/pay` endpoint for Mollie payment initiation
3. Keep `locked` status with admin-only lock/unlock
4. Add cross-item validation at submit time
5. Create proper UnifiedProduct records (no variants needed for tickets)
6. A single report Lambda querying Orders table by tenant
7. Frontend BookingForm targets order endpoints directly (no cart)

**What's eliminated:**

- Cart for PresMeet (not needed — order is the working document)
- 6 dedicated PresMeet Lambda handlers (save/submit/validate/payment/lock/unlock)
- Separate `presmeet.ts` types
- Cart/order deduplication in reports

**What's kept:**

- BookingForm (person-centric wizard UX)
- OnboardingFlow (club selection)
- AdminDashboard (PresMeet-specific reporting)
- Cross-item validation logic

---

## 13. Event-Linked Architecture

### 13.1 Why Link PresMeet to an Event Record

Currently, PresMeet's event metadata (dates, location) is stored in a `PresMeetConfig` object returned by `/presmeet/config`. This is a standalone config, not linked to the existing Events table. Linking to an event record provides:

| Benefit                            | Description                                                                                         |
| ---------------------------------- | --------------------------------------------------------------------------------------------------- |
| **Single source of truth**         | Event name, location, dates managed in one place (Events table)                                     |
| **Event-level constraints**        | Max attendees, registration deadline, payment deadline on the event — not scattered across products |
| **Automatic deadline enforcement** | Registration opens/closes based on event dates — no manual lock needed                              |
| **Multi-year support**             | Next year's PresMeet = new event record; old orders stay linked to their event                      |
| **Report context**                 | Reports automatically get event name, location, dates in headers/PDF                                |
| **Reusability**                    | Same pattern works for any future event needing registrations (e.g., chapter meetings, rallies)     |

### 13.2 Event Record Schema

```json
{
  "event_id": "presmeet_2026",
  "tenant": "presmeet",
  "name": "FH-DCE Presidents' Meeting 2026",
  "location": "Hotel Schiphol, Amsterdam",
  "start_date": "2026-09-12",
  "end_date": "2026-09-14",
  "registration_open": "2026-06-01",
  "registration_close": "2026-08-15",
  "payment_deadline": "2026-09-01",
  "status": "open",
  "constraints": {
    "max_meeting_attendees": 150,
    "max_party_attendees": 200,
    "max_transfer_seats": 100,
    "max_clubs": 50
  },
  "products": [
    "presmeet_meeting_ticket",
    "presmeet_party_ticket",
    "presmeet_tshirt",
    "presmeet_airport_transfer"
  ],
  "created_at": "2026-01-15T10:00:00Z",
  "updated_at": "2026-01-15T10:00:00Z"
}
```

### 13.3 Event Status Lifecycle

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  draft   │────▶│   open   │────▶│  closed  │────▶│ archived │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
  Admin creates    registration_open   registration_close   After event ends
  event config     date reached         date reached         admin archives
```

- `draft` — event being configured, not visible to clubs
- `open` — registration active, clubs can create/edit orders
- `closed` — registration deadline passed, all orders auto-locked
- `archived` — event is over, read-only for reporting

### 13.4 How Event Links to Orders

Every PresMeet order gets an `event_id` field:

```json
{
  "order_id": "...",
  "tenant": "presmeet",
  "event_id": "presmeet_2026",
  "club_id": "club_berlin",
  "status": "submitted",
  "items": [...]
}
```

**Reports are scoped to an event:**

```
GET /admin/reports/presmeet?event_id=presmeet_2026&type=attendees
```

### 13.5 Event Constraints vs. Purchase Rules

Two levels of constraints work together:

| Level                                | Scope            | Examples                                                 | Enforced at       |
| ------------------------------------ | ---------------- | -------------------------------------------------------- | ----------------- |
| **Product-level** (`purchase_rules`) | Per club         | max 3 meeting tickets per club, min 1                    | Order save/submit |
| **Event-level** (`constraints`)      | Across all clubs | max 150 total meeting attendees, max 200 party attendees | Order submit      |

**Validation flow at submit:**

```python
# 1. Product-level: Does this club exceed their max?
validate_purchase_rules(order.items, products)

# 2. Event-level: Does total across ALL clubs exceed event max?
total_meeting_tickets = count_all_orders(event_id, product='meeting_ticket', status=['submitted', 'locked'])
if total_meeting_tickets + this_order_tickets > event.constraints.max_meeting_attendees:
    return error("Event capacity reached: max 150 meeting attendees")
```

### 13.6 Deadline Enforcement

With event dates, locking becomes automatic:

```python
def can_edit_order(order, event):
    now = datetime.now()

    # Event closed? Auto-lock everything
    if now > event.registration_close:
        return False, "Registration deadline has passed"

    # Event not yet open?
    if now < event.registration_open:
        return False, "Registration has not started yet"

    # Order manually locked by admin? (override for edge cases)
    if order.status == 'locked':
        return False, "Order locked by admin"

    return True, None
```

**The `locked` status becomes an admin override** rather than the primary mechanism:

- **Automatic:** All orders become read-only after `registration_close`
- **Manual (optional):** Admin can lock individual orders early (e.g., club confirmed verbally, lock to prevent accidental changes)
- **Manual unlock:** Admin can unlock for corrections even after deadline (grace period)

### 13.7 Payment Deadline

The event record includes a `payment_deadline`. After this date:

- Clubs with unpaid/partial orders get automatic reminder emails
- Admin report highlights outstanding payments
- Optionally: prevent locked orders from being unlocked if payment is overdue

### 13.8 Multi-Year Support

Each year gets its own event record:

- `presmeet_2025` → orders from 2025 (archived)
- `presmeet_2026` → current active event
- `presmeet_2027` → future event (draft, not yet visible)

The frontend shows the active event (`status: 'open'`). Admin can view archived events for historical reporting.

Products can be reused across years (same ticket types, possibly different prices) — the event just links to them and provides the year-specific constraints and dates.

### 13.9 Updated Order Lifecycle (Event-Aware)

```
                    ┌─────────────┐
                    │   draft     │ ← user editing (event is 'open')
                    └──────┬──────┘
                           │ submit
                           ▼
                    ┌─────────────┐
                    │  submitted  │ ← user can still edit while event is 'open'
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
    registration_close     │      admin manual lock
              │            │            │
              ▼            │            ▼
       ┌─────────────┐    │     ┌─────────────┐
       │ auto-locked  │    │     │ admin-locked │
       └─────────────┘    │     └─────────────┘
                           │
                           │ pay (at any point)
                           ▼
                    ┌─────────────┐
                    │payment_status│
                    │ unpaid → partial → paid │
                    └─────────────┘
```

### 13.10 Impact on Frontend

The booking form uses event metadata for:

- **Display:** Event name, location, dates in header
- **Validation:** Transfer dates must be within event date range
- **Access control:** Form disabled if event is closed/not yet open
- **Countdown:** "Registration closes in X days" banner

```tsx
// usePresMeetEvent hook
const { event, isOpen, daysUntilClose, isExpired } = usePresMeetEvent();

if (!isOpen) {
  return <RegistrationClosed event={event} />;
}

return <BookingForm event={event} deadline={event.registration_close} />;
```

### 13.11 Impact on Reports

Reports get event context automatically:

```json
{
  "report_type": "attendees",
  "event": {
    "event_id": "presmeet_2026",
    "name": "FH-DCE Presidents' Meeting 2026",
    "location": "Hotel Schiphol, Amsterdam",
    "dates": "12-14 September 2026"
  },
  "generated_at": "2026-08-20T10:00:00Z",
  "total_count": 45,
  "entries": [...]
}
```

PDF exports include the event header with logo, name, location, and dates.

### 13.12 Admin Event Management

Admins can:

- Create new events (with products, constraints, dates)
- Open/close registration manually (override date-based automation)
- View event dashboard: registration progress, payment status, constraint utilization
- Clone previous year's event as template for the next year

```
┌─────────────────────────────────────────────────────────────────┐
│  PresMeet 2026 — Event Dashboard                                 │
├─────────────────────────────────────────────────────────────────┤
│  Status: OPEN | Registration closes: 15 Aug 2026 (26 days)       │
│                                                                  │
│  📊 Registration Progress                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Clubs registered: 32 / 50                               │    │
│  │  Meeting attendees: 78 / 150 ████████░░░░░░░ 52%         │    │
│  │  Party attendees: 112 / 200  █████████░░░░░░ 56%         │    │
│  │  T-shirts ordered: 65                                    │    │
│  │  Transfers booked: 42 / 100  ████░░░░░░░░░░░ 42%         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  💰 Payment Status                                               │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Total charged: €12,500 | Paid: €9,800 | Outstanding: €2,700│
│  │  Clubs fully paid: 22 / 32                               │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  [📋 Reports ▼]  [🔒 Lock All Submitted]  [⚙️ Edit Event]       │
└─────────────────────────────────────────────────────────────────┘
```
