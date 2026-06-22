# Closed Community Event Booking Module

## Overview

A generic booking module for **invitation-only** (closed community) events. Access is controlled by a shared event password + a configurable **invitee registry** (S3 JSON). Each row in the registry represents one booking slot. Event rules define how the registry works — what a "slot" means, who can claim it, and how many delegates per slot.

Reuses the existing Products, Orders, and Payments infrastructure. One order per registry row per event.

Examples: Presidents Meeting (row = club), regional ride (row = individual), partner event (row = company).

---

## 1. Invitee Registry (Generic Concept)

### What is it?

A per-event S3 JSON file that lists all allowed booking slots. This file is **static at runtime** — uploaded once by the admin. It is never mutated by the application. All runtime state (claims) is stored in DynamoDB.

The event configuration defines:

- What each row represents (label: "club", "team", "deelnemer", "bedrijf")
- How a row can be claimed (first-come-first-served, or restricted to specific emails)
- How many delegates can manage the order for one row

### Registry structure (S3 JSON — read-only at runtime)

```json
{
  "version": "1.0",
  "updated_at": "2026-06-20T10:00:00Z",
  "rows": [
    {
      "row_id": "de-001",
      "label": "HD Chapter Frankfurt",
      "allowed_emails": [],
      "max_delegates": 2,
      "logo_url": null,
      "metadata": {}
    },
    {
      "row_id": "de-002",
      "label": "HD Chapter Berlin",
      "allowed_emails": ["hans@berlin-chapter.de"],
      "max_delegates": 2,
      "logo_url": null,
      "metadata": {}
    }
  ]
}
```

### Field definitions (S3 — static)

| Field            | Type         | Description                                                                            |
| ---------------- | ------------ | -------------------------------------------------------------------------------------- |
| `row_id`         | string       | Unique identifier for this slot (used as `club_id` on the order)                       |
| `label`          | string       | Display name shown to the user (club name, person name, company name)                  |
| `allowed_emails` | string[]     | If non-empty: only these emails can claim this row. If empty: first-come-first-served. |
| `max_delegates`  | number       | How many bookers can manage the order for this row (default: 2)                        |
| `logo_url`       | string\|null | Optional logo/image URL for this row                                                   |
| `metadata`       | object       | Arbitrary key-value data per row (flexible for future needs)                           |

Note: `claimed_by`, `claimed_at`, `claimed_contact` are NOT in the S3 file — they live in DynamoDB.

### Claims storage (DynamoDB — runtime state)

Claims are stored on the **Event record** as a `registry_claims` map:

```json
{
  "event_id": "evt-uuid",
  "registry_claims": {
    "de-001": {
      "member_id": "mem-123",
      "email": "franz@chapter-frankfurt.de",
      "name": "Franz Weber",
      "claimed_at": "2026-06-21T14:30:00Z"
    }
  }
}
```

This uses DynamoDB conditional writes to prevent race conditions:

```python
events_table.update_item(
    Key={'event_id': event_id},
    UpdateExpression='SET registry_claims.#row = :claim',
    ConditionExpression='attribute_not_exists(registry_claims.#row)',
    ExpressionAttributeNames={'#row': row_id},
    ExpressionAttributeValues={':claim': {...}}
)
# ConditionalCheckFailedException → 409 row already claimed
```

### Scaling boundary

The `registry_claims` map lives on the Event DynamoDB item. Each claim is ~200 bytes, and DynamoDB items have a 400KB limit — so this approach supports **up to ~1500-2000 rows** per event comfortably.

For closed community events (50-200 clubs/rows), this is well within limits. If a future event type requires 1000+ rows (which would be more of an "open registration" pattern), claims would need to move to their own DynamoDB items (e.g., composite key `event_id#row_id`). That's out of scope — this spec targets invitation-only events with a known, limited set of slots.

### How data is merged for the UI

The frontend (or backend endpoint) merges:

1. S3 registry (static row list with labels, allowed_emails, logos)
2. DynamoDB `registry_claims` map (who claimed what)

Result: a combined list showing each row with its label + availability status.

### Event rules that control the registry

Stored on the **Event record** in DynamoDB:

```json
{
  "registry_config": {
    "s3_path": "events/evt-uuid/invitee_registry.json",
    "row_label": "club",
    "claim_mode": "first_come_first_served",
    "max_delegates_per_row": 2,
    "allow_logo_upload": true
  }
}
```

| Rule                    | Options                                             | Description                                                                                              |
| ----------------------- | --------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `s3_path`               | string                                              | S3 key for this event's registry JSON                                                                    |
| `row_label`             | string                                              | What to call a row in the UI ("club", "team", "deelnemer")                                               |
| `claim_mode`            | `"first_come_first_served"` \| `"email_restricted"` | Who can claim a row                                                                                      |
| `max_delegates_per_row` | number                                              | How many bookers can manage the order (not attendees — attendee limits come from product `max_per_club`) |
| `allow_logo_upload`     | boolean                                             | Whether delegates can upload a logo for their row                                                        |

### Claim modes

**`first_come_first_served`** (default):

- Any authenticated user with the event password can claim any unclaimed row
- Once claimed, the row is locked to that delegate (+ optional secondary)

**`email_restricted`**:

- The `allowed_emails` field on each row (in S3) determines who can claim it
- User's email must match one of the entries
- Useful for events where you know exactly who represents which slot

### Admin workflow for populating the registry

1. Admin creates a JSON file following the schema above (manually or via a script)
2. Uploads to S3 at the configured path: `s3://h-dcn-reports/events/{event_id}/invitee_registry.json`
3. Sets `registry_config.s3_path` on the Event record in DynamoDB
4. Done — no runtime mutations to the file needed

### Future: DynamoDB-backed registry

For high-concurrency events, the S3 JSON can be loaded into a DynamoDB table for more efficient reads. The claims mechanism already uses DynamoDB, so only the row list would migrate. Out of scope for v1.

---

## 2. User Flows

### Flow A: New user (never used the portal before)

```
1. Receives invitation link to event landing page
2. Enters shared event password → verified
3. Sees list of available rows (clubs) — unclaimed ones
4. Provides email address
5. Selects a row (club)
6. Creates a personal password (Cognito account created)
7. Member record created:
   - member_type = "{event_id}"
   - club_id = row_id
   - allowed_events = [event_id]
   - email, name
8. Row is claimed in DynamoDB (registry_claims)
9. Redirected to booking form → sees self-service + event booking
```

**Next time they visit:**

- Logs in with their email + password (or passkey) — no event password needed
- Sees self-service + event booking form directly

### Flow B: Existing H-DCN member (already has Cognito + Member record)

```
1. Arrives via event landing page link
2. Enters shared event password → verified
3. Sees list of available rows (clubs)
4. Clicks "I already have an account" → logs in with existing credentials
5. Selects a row (club)
6. Member record updated:
   - allowed_events gets event_id added
   - club_id set to row_id (if not already set)
   - member_type NOT overwritten (keeps existing value)
7. Row is claimed in DynamoDB (registry_claims)
8. Redirected to booking form → sees self-service + event booking
```

**Next time they visit:**

- Logs in normally → sees all their existing features + the new event booking form

### Flow C: Returning user (already onboarded for this event)

```
1. Logs in with personal credentials (email + password or passkey)
2. Portal recognizes allowed_events includes this event
3. Sees self-service + event booking form
4. Can continue editing their draft order
```

No landing page needed — direct access via normal login.

---

## 3. Booking Flow (Per-Person Products)

One order per registry row per event, managed by the delegate(s) who claimed that row.

### Flow

```
Login → Booking form → Add persons (guests) → Select products per person → Save draft (auto) → Submit → Pay
```

### Delegate management (order managers)

Delegates are the people who **manage** the order — not the attendees. This is configured at the registry level.

- **BOOK-1**: The member who claimed the registry row is the **primary delegate** (booker).
- **BOOK-2**: Primary can invite a **secondary delegate** by email — up to `max_delegates_per_row` from registry config (typically 1-2).
- **BOOK-3**: Both delegates can edit the order. Optimistic locking (version field) prevents conflicts.
- **BOOK-4**: Delegate info stored on order: `delegates: { primary_member_id: id, secondary_member_id: id | null }`.

#### Adding a secondary delegate (invite flow)

The secondary delegate may not yet exist in the system. The flow:

1. Primary enters the secondary's email in the `DelegateManager` UI
2. Backend stores the email as a **pending invitation** on the order: `delegates.pending_secondary_email`
3. System sends an invitation email with a link to the event landing page (or a direct link with an invite token)
4. Secondary clicks the link → goes through landing page flow (password already known / skipped via token) → account created/linked
5. On successful onboarding, system checks if this email matches any pending invitation for this event → auto-links as secondary delegate on the order
6. If the secondary already exists (has Cognito + Member record), they're linked immediately (no email needed — same as today)

**States:**

- `delegates.secondary_member_id` = confirmed secondary (has account, linked)
- `delegates.pending_secondary_email` = invited but not yet registered

The UI shows both: confirmed delegates and pending invitations (with a "resend" option).

### Guest/person management (attendees)

Persons are the **attendees** — people who will receive products/tickets. The max persons is NOT a fixed number on the registry — it's derived from product-level limits.

- **BOOK-5**: Delegate adds one or more **persons** (guests attending). Each has a `name` field (required).
- **BOOK-6**: Every order line carries `item_fields_data.name` (guest name) — even for products without a name requirement — for handover package preparation.
- **BOOK-7**: Guest name auto-fills from the person card into `item_fields_data.name` on every product line.
- **BOOK-8**: Max persons on the order = highest `purchase_rules.max_per_club` across all event-linked products. This is the ceiling for how many person cards can be added.
- **BOOK-9**: The delegate themselves is typically the first person (pre-filled from Member record).

### Product selection per person (ticket-level limits)

Each product defines its own quantity limits at **two levels**:

1. **Per order** (`purchase_rules.max_per_club`): max of this product within one order (one club/row)
2. **Per event** (`purchase_rules.max_per_event`): global capacity across ALL orders for the entire event

Both are configured on the product record. The UI must check both limits.

- **BOOK-10**: Products linked to the event shown per person (fetched via `GET /products?event_id={eventId}`).
- **BOOK-11**: Dynamic fields rendered via `ProductConfigurator` (from `order_item_fields` on product).
- **BOOK-12**: Variant dropdowns from `variant_schema` → maps to `variant_id`.
- **BOOK-13**: Per-order limit via `purchase_rules.max_per_club`. Example:
  - Meeting ticket: max 3 per club → only 3 persons in this order can have it
  - Party ticket: max 13 per club → up to 13 in this order
- **BOOK-14**: Per-event limit via `purchase_rules.max_per_event`. Example:
  - Meeting ticket: max 100 total across all clubs
  - Party ticket: max 500 total across all clubs
- **BOOK-15**: The UI shows remaining capacity considering BOTH limits:
  - Per order: `{max_per_club} - {already in this order} = {remaining for this order}`
  - Per event: `{max_per_event} - {sold across all orders} = {remaining globally}`
  - Effective limit = min(per-order remaining, per-event remaining)
- **BOOK-16**: Global sold counts are fetched from the backend (aggregated from all orders for this event). Displayed as "X of Y remaining" in the UI.
- **BOOK-17**: Product validation rules applied on submit (required fields, variant validity, both quantity caps).

### Product examples

| Product              | `max_per_club` | `max_per_event` | Description                                                        |
| -------------------- | -------------- | --------------- | ------------------------------------------------------------------ |
| Meeting ticket       | 3              | 100             | Main event entry                                                   |
| Party ticket         | 13             | 500             | Party entry, optional fee for drinks                               |
| Activity ticket      | 10             | 80              | Rides, tours around event location                                 |
| Transfer/pickup      | 20             | 150             | Airport/station transfer (fields: direction, location, date, time) |
| Event T-shirt        | 13             | 200             | Variant axes: Size, Gender                                         |
| Guest T-shirt        | 10             | 100             | Different pricing than event T-shirt                               |
| Badges/pins/stickers | 5              | 50              | Webshop subset linked to event                                     |

These values are configured per product in the Products table — fully flexible per event. `max_per_event` is optional — if not set, no global cap is enforced.

---

## 4. Order Lifecycle

Reuses existing Orders table and handlers.

### Statuses

```
draft → submitted → locked → (paid)
```

| Status      | Behavior                                                                      |
| ----------- | ----------------------------------------------------------------------------- |
| `draft`     | Editable by delegates, auto-saved every 3s. Optimistic locking via `version`. |
| `submitted` | Validated and finalized. Read-only for delegates. Admin can unlock.           |
| `locked`    | Admin-locked (e.g., registration closed). Fully read-only.                    |

### Requirements

- **ORD-1**: One order per `club_id` (= `row_id`) per `event_id` — existing deduplication in `create_order`.
- **ORD-2**: Draft accepts incomplete data. Validation only on submit.
- **ORD-3**: Submit validation:
  - Every person has a non-empty name
  - Every order line has `item_fields_data.name` populated
  - All required `order_item_fields` filled per product
  - Per-order quantity limits (`max_per_club`) not exceeded per product
  - Per-event capacity limits (`max_per_event`) not exceeded (check global sold count)
  - Variant selections valid
- **ORD-4**: After submit: status → `submitted`, delegate sees confirmation + pay option.
- **ORD-5**: Auto-save every 3s after last change (existing `useAutoSave` hook).

---

## 5. Payment

Reuses Mollie integration (existing `pay_order` handler).

- **PAY-1**: After submit, delegate initiates payment → Mollie checkout redirect.
- **PAY-2**: Payment status on order: `unpaid` → `partial` → `paid`.
- **PAY-3**: Admin can record manual payments.
- **PAY-4**: Payment not required to submit — submission and payment are separate steps.

---

## 6. PDF Booking Confirmation

- **PDF-1**: Delegate can request PDF at any order state (draft, submitted, locked).
- **PDF-2**: PDF includes: event name, row label (club/team name), delegate info, all persons + products + fields + variants, status, total, payment status.
- **PDF-3**: Before generation: validation run executes. PDF shows "valid at this moment" or lists issues.
- **PDF-4**: Disclaimer always appended: "Generated on {date}. Products and availability subject to change."
- **PDF-5**: Reuse existing `BookingSummaryPdf` component.

---

## 7. Admin Views (In Scope)

The portal already has admin UI for event CRUD and product configuration. The following admin features are part of this spec:

### 7.1 Claims & Delegate Management

Admin view showing all registry rows and their claim status per event.

- **ADM-1**: Table listing all rows from the registry: row label, claimed (yes/no), delegate name + email, claimed_at
- **ADM-2**: Admin can release a claim (remove from `registry_claims`) — e.g., if someone claimed the wrong row
- **ADM-3**: Admin can manually assign a row to a member (bypass the landing page flow)
- **ADM-4**: Admin can view/manage delegate assignments on orders: see primary + secondary, remove secondary, reassign primary
- **ADM-5**: Show pending delegate invitations (orders with `pending_secondary_email`)

### 7.2 Registration Progress Dashboard

Overview dashboard for event administrators showing real-time booking status.

- **ADM-6**: Summary cards: total rows, claimed rows, unclaimed rows, % registered
- **ADM-7**: Order status breakdown: draft / submitted / locked counts + percentage
- **ADM-8**: Payment status breakdown: unpaid / partial / paid + total revenue collected vs expected
- **ADM-9**: Per-product capacity usage: `{product name} — {sold across all orders} / {max_per_event}` with progress bars
- **ADM-10**: List of orders with filters: by status, by payment_status, by row/club — linking to order detail
- **ADM-11**: Export to CSV: all orders with items, delegate info, payment status (for offline planning)

### API support needed

- **ADM-API-1**: `GET /admin/events/{id}/claims` — return all claims from `registry_claims` with member details
- **ADM-API-2**: `DELETE /admin/events/{id}/claims/{row_id}` — release a claim
- **ADM-API-3**: `POST /admin/events/{id}/claims/{row_id}` — manually assign a row to a member
- **ADM-API-4**: `GET /admin/events/{id}/dashboard` — aggregated stats (order counts, payment totals, product capacity usage)
- **ADM-API-5**: `GET /admin/events/{id}/orders` — list all orders for this event with filters (existing reports endpoint may cover this)
- **ADM-API-6**: `GET /admin/events/{id}/preparation-pdf` — generate preparation PDF (see 7.3)

### 7.3 Order Preparation PDF

A downloadable PDF for event organizers to prepare handover packages. Two views of the same data:

#### By Order (per club/row)

Each page = one order (one club). Contains:

- Header: club logo (from registry `logo_url`) + club name + event name
- Delegate name(s)
- Table of all guests with their ordered items per guest
- Order total, payment status

#### By Guest (per person)

Each page = one guest (one person across all orders). Contains:

- Header: club logo + club name + guest name
- All items ordered for this guest (product name, variant, fields, price)
- Useful for assembling individual handover packages/goodie bags

#### Requirements

- **ADM-12**: Admin can download a "preparation PDF" from the dashboard
- **ADM-13**: PDF has two modes: "by order" (grouped by club) and "by guest" (one page per person)
- **ADM-14**: Each page includes the club logo in the header (from `logo_url` in the registry or claim data)
- **ADM-15**: By-guest view shows: guest name, club name, product name, variant selection, all `order_item_fields` values, unit price
- **ADM-16**: PDF is sorted alphabetically (by club name in order-view, by guest name in guest-view)
- **ADM-17**: Only submitted + locked orders are included (draft orders are excluded — not yet confirmed)
- **ADM-18**: Footer on each page shows: event name, generation date, page number
- **ADM-19**: PDF can be filtered by product (e.g., "only T-shirt pages" for the T-shirt packing team)

---

## 8. Data Model

### Events table — new fields

| Field                  | Type    | Description                                      |
| ---------------------- | ------- | ------------------------------------------------ |
| `event_password`       | S       | Hashed shared password for landing page (bcrypt) |
| `landing_page_enabled` | BOOL    | Whether this event uses the landing page flow    |
| `registry_config`      | M (Map) | Registry rules (see section 1)                   |
| `registry_claims`      | M (Map) | Runtime claim state — who claimed which row      |

`registry_config` structure:

```json
{
  "s3_path": "events/{event_id}/invitee_registry.json",
  "row_label": "club",
  "claim_mode": "first_come_first_served",
  "max_delegates_per_row": 2,
  "allow_logo_upload": true
}
```

`registry_claims` structure:

```json
{
  "de-001": {
    "member_id": "...",
    "email": "...",
    "name": "...",
    "claimed_at": "..."
  },
  "de-002": {
    "member_id": "...",
    "email": "...",
    "name": "...",
    "claimed_at": "..."
  }
}
```

### S3 — Invitee Registry (static, read-only at runtime)

Path: `s3://h-dcn-reports/events/{event_id}/invitee_registry.json`

Uploaded once by admin. Never mutated by the application. Structure defined in section 1.

Backward compatible with existing `presmeet/club_registry.json` — same shape minus the claimed\_\* fields (which now live in DynamoDB).

### Members table — fields used

| Field            | Usage                                                                  |
| ---------------- | ---------------------------------------------------------------------- |
| `member_type`    | `"{event_id}"` for event-only members (preserved for existing members) |
| `club_id`        | Set to `row_id` from the registry during onboarding                    |
| `allowed_events` | List of event_ids this member can access                               |
| `email`          | From account creation                                                  |
| `name`           | From onboarding form                                                   |

### Orders table — no changes

Existing deduplication: `club_id` (= `row_id`) + `event_id`. Delegates field already supports primary/secondary.

---

## 9. API Endpoints

### Existing (no changes needed)

| Method | Endpoint                        | Purpose                |
| ------ | ------------------------------- | ---------------------- |
| GET    | `/booking?source_id={event_id}` | Get/create draft order |
| PUT    | `/orders/{id}/items`            | Save draft items       |
| POST   | `/booking/{id}/submit`          | Validate + submit      |
| POST   | `/booking/{id}/pay`             | Initiate payment       |
| GET    | `/products?event_id={id}`       | Event-linked products  |
| GET    | `/events`                       | Event metadata         |
| POST   | `/admin/events/{id}/access`     | Manual grant/revoke    |

### New endpoints

**POST /events/{event_id}/verify-password** (public, no auth)

```
Request:  { "password": "secret123" }
Response: { "valid": true, "event_name": "...", "registry_config": {...} }
   or:    { "valid": false }
```

Validates the shared event password. Returns event metadata + registry config for next step.

**GET /events/{event_id}/registry** (public after password verified)

```
Response: {
  "rows": [
    { "row_id": "de-001", "label": "HD Chapter Frankfurt", "available": true, "logo_url": null },
    { "row_id": "de-002", "label": "HD Chapter Berlin", "available": false, "claimed_contact": "ha***@berlin.de" }
  ],
  "row_label": "club",
  "claim_mode": "first_come_first_served"
}
```

Merges S3 registry (row list) with DynamoDB `registry_claims` (availability). Masks full email of other claimants for privacy.

**POST /events/{event_id}/onboard**

```
Request: {
  "row_id": "de-001",
  "email": "hans@chapter.de",
  "name": "Hans Müller",
  "password": "userPass123"
}
Response 201: { "member_id": "...", "message": "Account created, row claimed" }
Response 200: { "member_id": "...", "message": "Existing account linked, row claimed" }
Response 409: { "error": "row_already_claimed", "claimed_contact": "ha***@other.de" }
Response 403: { "error": "email_not_allowed", "message": "Your email is not on the invitation list for this row" }
```

Steps:

1. Re-verify event password (or validate session token from verify step)
2. Check claim_mode rules (email restriction if applicable)
3. Claim row atomically in DynamoDB via conditional write on `registry_claims.{row_id}`
4. Create Cognito user if new (AdminCreateUser with email + password)
5. Create or update Member record (member_type, club_id, allowed_events)
6. Add user to `event_participant` Cognito group
7. Return success → frontend redirects to booking form

### Backend changes to existing handlers

- **BE-1**: Submit handler — add validation that all items have `item_fields_data.name` populated + check `max_per_event` capacity not exceeded.
- **BE-2**: `get_club_registry` — generalize to read from configurable S3 path (from event's `registry_config`), or create the new `/events/{id}/registry` endpoint that merges S3 + DynamoDB claims.
- **BE-3**: New endpoint or extend `GET /products?event_id={id}` — return `sold_count_event` per product (aggregated from all orders for this event). Used by frontend to calculate remaining global capacity.

---

## 10. Frontend Architecture

### Existing pages (already built)

| Route                      | Component                            | Purpose                                    |
| -------------------------- | ------------------------------------ | ------------------------------------------ |
| `/events/:slug/info`       | `EventLandingPage`                   | Public marketing page (hero, content, CTA) |
| `/events/:slug/register`   | `EventRegisterPage`                  | Sign-up / sign-in (email + OTP/passkey)    |
| `/events/:eventId/booking` | `EventBookingPage` → `BookingWizard` | The actual booking form                    |

**Current flow:**

```
Landing page (public) → CTA button → Register page (auth) → Booking form
```

### Extended flow for closed community

No new pages. We **extend `EventRegisterPage`** with additional steps for closed community events:

```
/events/:slug/info         → EventLandingPage (EXISTING — no changes needed)
/events/:slug/register     → EventRegisterPage (EXTENDED)
  Step 1: PasswordGate     (NEW — event password, only if event.landing_page_enabled)
  Step 2: Sign-up / Sign-in (EXISTING — tabs with email + name + OTP/passkey)
  Step 3: RegistrySelector  (NEW — choose row/club, only for closed community)
  Step 4: Claim + redirect  (NEW — call onboard API, redirect to booking)
```

**Extended EventRegisterPage component tree:**

```
EventRegisterPage
├── PasswordGate              (NEW — only if event has event_password)
│   └── Password input + verify button
├── Auth Tabs                 (EXISTING — sign-up / sign-in)
│   ├── Sign Up Panel         (email + name → Cognito account)
│   └── Sign In Panel         (email → OTP/passkey)
├── RegistrySelector          (NEW — shown after auth for closed community)
│   └── RowCard[]             (row_id, label, available/taken, logo)
├── ClaimAction               (NEW — claim row + onboard API call)
└── SuccessRedirect           (EXISTING — redirect to /events/{event_id}/booking)
```

For non-closed-community events (open registration), Steps 1 and 3 are skipped — the page works as it does today.

### Existing: Event Booking Page (minor changes)

**Route**: `/events/:eventId/booking`

```
EventBookingPage
├── AccessDeniedScreen          (NEW — no access → link to register page)
├── EventInfoHeader             (existing)
├── BookingWizard               (existing — person-centric)
│   ├── PersonCard[]            (one per guest/person)
│   │   └── ProductConfigurator (dynamic fields + variants)
│   ├── AddPersonButton
│   ├── EffectiveLimits
│   ├── TotalDisplay
│   ├── SubmitPanel
│   └── AutoSave
├── DelegateManager             (existing — add/remove secondary delegate)
├── PaymentPanel                (existing — Mollie)
├── BookingSummaryPdf           (existing — PDF with validation)
└── ReadOnlyView                (submitted/locked)
```

### Frontend changes summary

- **FE-1**: Extend `EventRegisterPage` with `PasswordGate` step (shown if event has `event_password`)
- **FE-2**: Add `RegistrySelector` component — shown after auth, lists available rows from `/events/{id}/registry`
- **FE-3**: Add `AccessDeniedScreen` in `EventBookingPage` — link to `/events/:slug/register`
- **FE-4**: Pre-fill first person card with delegate's name from Member record
- **FE-5**: Use `registry_config.row_label` for UI terminology ("Selecteer je club" / "Selecteer je team")
- **FE-6**: After row claim + onboard, redirect to booking form

---

## 11. Translation Keys

Namespace: `eventLanding` (new) + `eventBooking` (additions)

### `eventLanding`

- `title` — "Welkom bij {eventName}"
- `password_label` — "Evenement wachtwoord"
- `password_invalid` — "Ongeldig wachtwoord"
- `select_row` — "Selecteer je {rowLabel}"
- `row_taken` — "Al geregistreerd door {contact}"
- `row_available` — "Beschikbaar"
- `email_not_allowed` — "Je e-mailadres staat niet op de uitnodigingslijst"
- `create_account` — "Account aanmaken"
- `existing_account` — "Ik heb al een account"
- `success` — "Welkom! Je wordt doorgestuurd..."

### `eventBooking` (additions)

- `access_denied.title` — "Geen toegang"
- `access_denied.go_to_landing` — "Ga naar de registratiepagina"
- `booking.guest_name_required` — "Gastnaam is verplicht"
- `pdf.valid_statement` — "Geldig op moment van genereren"
- `pdf.disclaimer` — "Gegenereerd op {date}. Onder voorbehoud van wijzigingen."

All 8 languages: nl, en, de, fr, es, it, da, sv.

---

## 12. Implementation Order

**Pre-implementation checks:**

- Verify `event_participant` Cognito group exists in the pool (if not, create it via AWS console — pool config is managed outside CloudFormation)
- No migration script needed — new Event fields (`event_password`, `registry_config`, `registry_claims`) are simply absent on existing events; code handles absence gracefully
- ADR required: `docs/decisions/generic-event-booking.md` documenting the decision to build a generic registry-driven booking system separate from PresMeet
- **Event Field Registry required**: create `frontend/src/config/eventFields/` following the same pattern as `memberFields/` and `productFields/`. Must include all new fields (`event_password`, `landing_page_enabled`, `registry_config`, `registry_claims`) and existing event fields. This is the single source of truth per the schema-driven steering.

**Build steps:**

1. **Data model**: Add `event_password`, `landing_page_enabled`, `registry_config`, `registry_claims` to Events
2. **S3**: Define registry JSON schema, create sample file for test event
3. **Backend**: `verify-password` handler (public, rate-limited)
4. **Backend**: `registry` GET handler (merges S3 rows + DynamoDB claims)
5. **Backend**: `onboard` handler (claim row + Cognito + Member + event access)
6. **Backend**: Submit handler — add guest name validation
7. **Frontend**: Extend `EventRegisterPage` with `PasswordGate` step
8. **Frontend**: Add `RegistrySelector` component to register page (claim flow)
9. **Frontend**: `AccessDeniedScreen` in booking page → link to register
10. **Frontend**: Pre-fill delegate name, configurable `row_label` in UI
11. **Translations**: All keys in 8 locales
12. **Testing**: Landing flow, atomic claim, existing booking flow unchanged

---

## 13. Security & Cognito Setup

### Cognito attributes for event-only users

A delegate created through the landing page gets the absolute minimum in Cognito:

| Attribute                      | Value             | Purpose                                                      |
| ------------------------------ | ----------------- | ------------------------------------------------------------ |
| `email` (= username)           | `hans@chapter.de` | Login identity                                               |
| `email_verified`               | `true`            | Required for authentication                                  |
| `custom:member_id`             | `uuid`            | Links to Member DynamoDB record                              |
| **Group**: `event_participant` | —                 | Only group needed — passes all booking handler access checks |

**Not needed:**

- `Regio_Pressmeet` — legacy, to be removed from all handler checks
- `hdcnLeden` — for full H-DCN members only (gives webshop + member features)
- Any admin/Products roles — event delegates have no admin access

**How `event_participant` works:**

- All booking handlers (`get_products`, `create_order`, `update_order_items`, `pay_order`) accept `event_participant` as a valid role
- Actual authorization (which event, which order) is controlled by `allowed_events` on the Member record + order ownership (delegate must be on the order)
- The Cognito group is just the first gate to pass handler-level access checks
- Users never access DynamoDB directly — all access is through Lambda handlers behind API Gateway

### Security requirements

- **SEC-1**: Event password hashed (bcrypt) — never returned in plaintext.
- **SEC-2**: Password verify endpoint rate-limited (API Gateway throttling).
- **SEC-3**: Row claim is atomic — DynamoDB conditional write on `registry_claims.{row_id}` prevents double-claim race conditions.
- **SEC-4**: Cognito user creation via `AdminCreateUser` with `email_verified = true` + immediate password set (confirmed status).
- **SEC-5**: Onboard endpoint re-verifies event password (or short-lived session token from verify step).
- **SEC-6**: Event-only members (`member_type = event_id`) get ONLY `event_participant` group — no `hdcnLeden`, no admin roles, no webshop access.
- **SEC-7**: For `email_restricted` mode: claim only succeeds if user's email matches the row's `allowed_emails` in S3.
- **SEC-8**: Registry GET endpoint masks claimant emails (shows `ha***@domain.de` not full address).
- **SEC-9**: `Regio_Pressmeet` is deprecated — remove from all handler access checks. Replace with `event_participant` where event booking access is needed.

---

## 14. Migration from PresMeet

The existing PresMeet flow continues as-is. To migrate to this generic system (optional, after v1 is proven):

1. Create `registry_config` on PresMeet event pointing to existing `presmeet/club_registry.json`
2. Add `event_password` to the PresMeet event record
3. Populate `registry_claims` from existing `assigned_member_id` fields
4. Map: `club_id` → `row_id`, `club_name` → `label`, `assigned_member_id` → `claimed_by`
5. Remove `claimed_*` fields from S3 file (now in DynamoDB)
6. No breaking changes — backward compatible

### Dead Code Removal Plan

The generic module does NOT reuse any of the following code. These are PresMeet-specific and will become dead code once PresMeet migrates to the generic system.

**Removal conditions — ALL must be true:**

1. Generic system is deployed and working in production
2. At least one real event has completed successfully on the generic system
3. PresMeet has been migrated and run one event (PM2028) on the generic system
4. No component still imports the old code (verify with `grep` across codebase, excluding `.kiro/specs/`, `node_modules/`, `.git/`)

**Phase 4: Remove after successful migration**

| Dead code                                                    | Location                                                              | Replaced by                                                      |
| ------------------------------------------------------------ | --------------------------------------------------------------------- | ---------------------------------------------------------------- |
| `OnboardingFlow` component                                   | `frontend/src/modules/presmeet/components/OnboardingFlow.tsx`         | `PasswordGate` + `RegistrySelector` steps in `EventRegisterPage` |
| `ClubLogoUploader` component                                 | `frontend/src/modules/presmeet/components/ClubLogoUploader.tsx`       | Generic logo upload via `allow_logo_upload` in registry config   |
| `PresMeetPage` (legacy `/presmeet` route)                    | `frontend/src/modules/presmeet/PresMeetPage.tsx`                      | `/events/{id}/booking` route                                     |
| Legacy `presmeetService` methods                             | `frontend/src/modules/presmeet/services/presmeetApi.ts` (bottom half) | v3 `presmeetApi` exports already replace these                   |
| Legacy types (`presmeet.ts`)                                 | `frontend/src/modules/presmeet/types/presmeet.ts`                     | `presmeet.types.ts` (already the active types)                   |
| Hardcoded product types (`ProductType`, `ProductTypeConfig`) | `frontend/src/modules/presmeet/types/presmeet.ts`                     | Dynamic products from Products table                             |
| `BookingForm` (legacy sections-based)                        | `frontend/src/modules/presmeet/components/BookingForm.tsx`            | `BookingWizard` (already the active component)                   |
| `DelegateSection` component                                  | `frontend/src/modules/presmeet/components/DelegateSection.tsx`        | `PersonCard` (already the active component)                      |
| `GuestSection` component                                     | `frontend/src/modules/presmeet/components/GuestSection.tsx`           | `PersonCard` (already the active component)                      |
| `TransferSection` component                                  | `frontend/src/modules/presmeet/components/TransferSection.tsx`        | Dynamic product with `order_item_fields` for transfer data       |
| `assign_club` handler                                        | `backend/handler/assign_club/app.py`                                  | `event_onboard` handler (claims via `registry_claims`)           |
| `get_club_registry` handler                                  | `backend/handler/get_club_registry/app.py`                            | `GET /events/{id}/registry` (merges S3 + DynamoDB)               |
| `upload_club_logo` handler                                   | `backend/handler/upload_club_logo/app.py`                             | Generic logo upload (if `allow_logo_upload` enabled)             |
| S3 path `presmeet/club_registry.json`                        | S3 bucket `h-dcn-reports`                                             | `events/{event_id}/invitee_registry.json`                        |
| `Regio_Pressmeet` role checks in handlers                    | Various handlers                                                      | `has_event_access()` + `allowed_events` on Member                |
| `source: "presmeet"` hardcoded checks                        | Various                                                               | `event_type` field on Event record                               |
| `usePresMeetBooking` hook                                    | `frontend/src/modules/presmeet/hooks/usePresMeetBooking.ts`           | `BookingWizard` internal state (already active)                  |

**Important:** None of the above is used by the new generic module. The generic module builds fresh:

- `PasswordGate` + `RegistrySelector` in `EventRegisterPage` — replaces `OnboardingFlow`
- `RegistrySelector` (new) — replaces club-specific `ClubSelector`
- `/events/{id}/registry` endpoint (new) — replaces `get_club_registry`
- `/events/{id}/onboard` endpoint (new) — replaces `assign_club`
- `/events/{id}/verify-password` endpoint (new) — no equivalent existed
- `registry_claims` on Event record (new) — replaces `assigned_*` fields in S3 JSON
- All booking components (`BookingWizard`, `PersonCard`, `ProductConfigurator`, etc.) are already generic and shared

---

## 15. Out of Scope

- Open registration events (separate spec)
- DynamoDB-backed registry rows (future — only claims use DynamoDB in v1)
- Capacity management / waitlists
- Email notifications (booking confirmations, reminders)
- Refund flow
- Registry upload UI (manual S3 upload for now)

---

## 16. Next Release Roadmap

Features to build after this spec is complete, in suggested priority order:

### 16.1 Email Notifications (high value, low effort)

Transactional emails triggered by booking lifecycle events. Uses existing SES infrastructure.

| Trigger                           | Email                                          | Recipient                                |
| --------------------------------- | ---------------------------------------------- | ---------------------------------------- |
| Order submitted                   | Booking confirmation with summary              | Primary + secondary delegate             |
| Payment received (Mollie webhook) | Payment confirmation                           | Primary delegate                         |
| Delegate invitation               | "You've been invited to manage a booking"      | Pending secondary (link to landing page) |
| Admin locks orders                | "Registration closed" notification             | All delegates with orders                |
| X days before event               | Reminder with booking details + payment status | All delegates                            |
| Order unlocked by admin           | "Your booking has been re-opened for editing"  | Delegates                                |

Requires: email templates (SES), a scheduled Lambda via EventBridge for reminders, ~2-3 days effort.

### 16.2 Open Registration Events (low effort after this spec)

Self-service event registration for any logged-in H-DCN member. No landing page, no registry, no shared password.

- Member clicks "Join Event" → `allowed_events` updated → personal order created
- One order per member (not per club) — no delegates
- Same booking form, same products, same payment
- New: `registration_mode: "open"` on Event record + simple join endpoint
- ~1-2 days effort (90% reuses this spec's infrastructure)

### 16.3 Refund Flow (medium effort)

Handle cancellations and refunds via Mollie refund API.

| Scenario                                     | Approach                                                   |
| -------------------------------------------- | ---------------------------------------------------------- |
| Full refund (event cancelled)                | Admin triggers → Mollie refund API → update payment_status |
| Partial refund (items removed after payment) | Admin calculates difference → partial refund               |
| Manual refund (bank transfer)                | Admin records negative payment entry                       |

Decisions needed: admin-only vs delegate-requestable, automatic vs approval-based. ~3-5 days effort.

### 16.4 Admin Event Management UI

Extensions to the existing admin UI for closed community event features:

- Upload/manage invitee registries (currently manual S3 upload)

Medium effort (~2-3 days) — eliminates manual S3 operations for registry management.

---

## References

- #[[file:backend/layers/auth-layer/python/shared/event_access.py]]
- #[[file:backend/handler/create_order/app.py]]
- #[[file:backend/handler/update_order_items/app.py]]
- #[[file:backend/handler/get_products/app.py]]
- #[[file:backend/handler/manage_event_access/app.py]]
- #[[file:backend/handler/get_club_registry/app.py]]
- #[[file:frontend/src/modules/presmeet/components/BookingWizard.tsx]]
- #[[file:frontend/src/modules/presmeet/components/PersonCard.tsx]]
- #[[file:frontend/src/modules/presmeet/components/OnboardingFlow.tsx]]
- #[[file:frontend/src/modules/presmeet/components/DelegateManager.tsx]]
- #[[file:frontend/src/modules/presmeet/utils/orderTransformer.ts]]
- #[[file:frontend/src/modules/presmeet/services/presmeetApi.ts]]
- #[[file:frontend/src/modules/presmeet/types/presmeet.types.ts]]
- #[[file:frontend/src/config/productFields/fields.ts]]
