# Design Document: Generic Event Booking System

## Overview

This design generalizes the current PresMeet-specific booking pipeline into a universal event booking system. Any event (Presidents Meeting, Rally, Members Day) uses the same order pipeline, access control, and booking form. The key changes are:

1. **`source_id` on every order** — `"webshop"` or `<event_id UUID>` — identifies origin
2. **`event-member-index` GSI** — replaces `event-club-index` (PK: `source_id`, SK: `member_id`)
3. **Data-driven event access** — `allowed_events[]` on Members record replaces hardcoded Cognito groups
4. **External member support** — `member_type = "event_participant"` with limited permissions
5. **Generic handlers** — one set of handlers serves all event types
6. **Booking form preserved** — person-centric wizard UX unchanged, only backend endpoints generalized

### What Changes vs What's Preserved

| Preserved (no changes)                                             | Generalized (refactored)                              |
| ------------------------------------------------------------------ | ----------------------------------------------------- |
| Booking form wizard UX                                             | Handler names (presmeet*\* → event*\*)                |
| Person-centric data model                                          | Order lookup (club_id → member_id)                    |
| Product schema (order_item_fields, purchase_rules, variant_schema) | Access control (Cognito group → allowed_events)       |
| Event constraints validation engine                                | GSI (event-club-index → event-member-index)           |
| Event status scheduler logic                                       | Source filtering (source='presmeet' → source_id=UUID) |
| Optimistic locking (version field)                                 | Product discovery (source filter → event.product_ids) |
| Payment integration (Mollie)                                       | —                                                     |
| Report types and generation                                        | —                                                     |

## Architecture

### High-Level Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐ │
│  │ Booking Form │  │ Self Service │  │ Admin Event Dashboard │ │
│  └──────┬───────┘  └──────┬───────┘  └───────────┬───────────┘ │
└─────────┼──────────────────┼──────────────────────┼─────────────┘
          │ event_id         │                      │
          ▼                  ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                     API Gateway (REST)                           │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Unified Order Handlers                         │
│  ┌──────────────────┐  ┌─────────────────────┐                 │
│  │ get_order        │  │ submit_order        │                 │
│  │ (GET + PUT)      │  │ create_payment      │                 │
│  │ lock_orders      │  │ manage_event_access │                 │
│  └────────┬─────────┘  └──────────┬──────────┘                 │
│           │                        │                            │
│           ▼                        ▼                            │
│  ┌────────────────────────────────────────────┐                 │
│  │ Auth Layer: extract_user_credentials()     │                 │
│  │            → has_event_access(member, evt) │                 │
│  │            → validate_permissions()        │                 │
│  └────────────────────────────────────────────┘                 │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DynamoDB Tables                             │
│  ┌────────┐  ┌────────┐  ┌──────────┐  ┌─────────┐            │
│  │ Orders │  │ Events │  │ Producten│  │ Members │            │
│  │ (GSI:  │  │        │  │          │  │         │            │
│  │  event-│  │        │  │          │  │ allowed │            │
│  │  member│  │        │  │          │  │ _events │            │
│  │  -index│  │        │  │          │  │         │            │
│  └────────┘  └────────┘  └──────────┘  └─────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

## Data Model Changes

### Orders Table

**New/changed fields:**

| Field       | Type              | Description                                 |
| ----------- | ----------------- | ------------------------------------------- |
| `source_id` | String (required) | `"webshop"` or event UUID                   |
| `member_id` | String (required) | The member who owns this order              |
| `club_id`   | String (optional) | Kept for display/reporting, NOT for lookups |

**New GSI: `event-member-index`**

| Property   | Value                |
| ---------- | -------------------- |
| Table      | Orders               |
| GSI Name   | `event-member-index` |
| PK         | `source_id` (S)      |
| SK         | `member_id` (S)      |
| Projection | ALL                  |
| Billing    | PAY_PER_REQUEST      |

**Access patterns:**

```python
# Find a member's order for an event
orders_table.query(
    IndexName='event-member-index',
    KeyConditionExpression=Key('source_id').eq(event_id) & Key('member_id').eq(member_id)
)

# List all orders for an event
orders_table.query(
    IndexName='event-member-index',
    KeyConditionExpression=Key('source_id').eq(event_id)
)

# List all webshop orders for a member
orders_table.query(
    IndexName='event-member-index',
    KeyConditionExpression=Key('source_id').eq('webshop') & Key('member_id').eq(member_id)
)
```

### Members Table

**New/changed fields:**

| Field            | Type              | Description                                                          |
| ---------------- | ----------------- | -------------------------------------------------------------------- |
| `member_type`    | String            | `"hdcn_member"` (default/existing), `"event_participant"` (external) |
| `allowed_events` | List of Strings   | Event UUIDs this member can access                                   |
| `club_id`        | String (optional) | External member's home club (unchanged for existing members)         |

### Events Table (unchanged structure, new field)

Already has the correct structure: `event_id`, `name`, `event_type`, `status`, `registration_open/close`, `start_date/end_date`, `product_ids[]`, `constraints[]`.

**New field:**

| Field         | Type   | Description                                                    |
| ------------- | ------ | -------------------------------------------------------------- |
| `order_scope` | String | `"member"` (default) or `"club"` — determines order uniqueness |

- `"member"`: one order per member per event (e.g., Rally, Members Day)
- `"club"`: one order per club per event (e.g., Presidents Meeting)

When `order_scope = "club"`:

- Order is created with `member_id` = primary delegate's member_id
- `club_id` is stored on the order for uniqueness enforcement
- Secondary delegates access the order via club_id lookup (query all event orders, filter by club_id)
- Uniqueness is enforced at write time (conditional put), not by index structure

### Producten Table (unchanged)

Products continue to use the existing schema. No `source` filter needed — event's `product_ids[]` is the lookup mechanism.

## Access Control Design

### Current vs New

```
CURRENT:
  has_presmeet_access() → checks Cognito groups ['Regio_Pressmeet', 'Regio_All']
  get_club_id(email) → looks up club_id on Members record
  Order lookup: scan by source='presmeet' AND club_id=X

NEW:
  has_event_access(member_id, event_id) → checks:
    1. Is event_id in member's allowed_events? → True/False
    (No Cognito group checks — Regio_Pressmeet is removed during migration)
  Order lookup: query event-member-index by source_id=event_id AND member_id=X
```

### New auth module: `shared/event_access.py`

```python
def has_event_access(member_id: str, event_id: str) -> bool:
    """
    Check if a member has access to a specific event.
    Access is granted purely via the allowed_events list on the Members record.
    """
    member = get_member_by_id(member_id)
    if not member:
        return False
    return event_id in member.get('allowed_events', [])
```

No legacy Cognito group checks. No `LEGACY_EVENT_GROUPS` mapping. Clean and simple.

The `event_participant` Cognito group maps to minimal permissions in the auth layer:

```python
# Addition to role_permissions in auth_utils.py
'event_participant': [
    'profile_read', 'profile_update_own',
    'members_self_read', 'members_self_update',
    'events_read'
]
```

This grants self-service profile access and the ability to read event data. Actual event booking access is controlled by `allowed_events` — the Cognito group only provides the base permission level.

### Permission model for external members

| member_type         | Cognito group       | Permissions                                           |
| ------------------- | ------------------- | ----------------------------------------------------- |
| `hdcn_member`       | `hdcnLeden`         | Full member features + events via allowed_events      |
| `event_participant` | `event_participant` | Self-service profile + events via allowed_events only |

External members get the `event_participant` Cognito group — NOT `hdcnLeden`. This grants only:

- Self-service profile maintenance
- Access to booking forms for events in their `allowed_events`

They do NOT get: webshop access, member directory, regional features, or any other H-DCN member features.

## Handler Migration Map

### Order Lookup Logic (by source and scope)

```python
def get_order(source_id, member_id, user_roles):
    # --- Access check ---
    if source_id == 'webshop':
        # Webshop: any hdcnLeden member can create orders
        if 'hdcnLeden' not in user_roles:
            return error(403, 'Member access required')
        order_scope = 'member'  # webshop is always per-member
        event = None
    else:
        # Event: check allowed_events
        event = get_event(source_id)
        if not event:
            return error(404, 'Event not found')
        if not has_event_access(member_id, source_id):
            return error(403, 'Event access required')
        if event.get('status') != 'open':
            return error(403, 'Registration is not open')
        order_scope = event.get('order_scope', 'member')

    # --- Order lookup ---
    if order_scope == 'club':
        # Club-scoped: one order per club
        club_id = get_club_id(member_id)
        if not club_id:
            return error(403, 'Club assignment required for this event')

        # Query all orders for this source (PK-only), filter by club_id
        all_orders = query_gsi(source_id=source_id)
        club_order = next((o for o in all_orders if o.get('club_id') == club_id), None)

        if club_order:
            # Verify user is primary or secondary delegate
            delegates = club_order.get('delegates', {})
            if member_id not in [delegates.get('primary_member_id'), delegates.get('secondary_member_id')]:
                return error(403, 'You are not a delegate for this club')
            return club_order
        else:
            # Create new order: this member becomes primary delegate
            return create_order(source_id=source_id, member_id=member_id, club_id=club_id)

    else:
        # Member-scoped (default): one order per member per source
        order = query_gsi(source_id=source_id, member_id=member_id)
        if order:
            return order
        else:
            return create_order(source_id=source_id, member_id=member_id)
```

### Handler Mapping

| Current Handler             | New Handler                          | Key Changes                                                  |
| --------------------------- | ------------------------------------ | ------------------------------------------------------------ |
| `get_presmeet_booking`      | `get_order`                          | Unified: handles webshop + event, branches on `source_id`    |
| `submit_presmeet_booking`   | `submit_order`                       | Unified: applies event constraints only when source is event |
| `create_presmeet_payment`   | `create_payment`                     | Unified: same Mollie flow for all orders                     |
| `lock_presmeet_orders`      | `lock_orders`                        | Unified: locks by source_id                                  |
| `presmeet_manage_delegates` | `manage_delegates`                   | Club-scoped orders only                                      |
| `get_presmeet_config`       | (removed)                            | Frontend queries event + products directly                   |
| `submit_order` (webshop)    | `submit_order` (unified)             | Merged with event submission                                 |
| `assign_club`               | `assign_club` (unchanged)            | Still works for events that need club context                |
| `get_club_registry`         | `get_club_registry` (unchanged)      | Still used by events with club model                         |
| `event_status_scheduler`    | `event_status_scheduler` (unchanged) | Already event-agnostic                                       |

### New Handler: `manage_event_access`

```python
# POST /admin/events/{event_id}/access
# Body: { "action": "grant"|"revoke", "member_ids": [...] }
# Adds/removes event_id from each member's allowed_events
```

## Frontend Changes

### Booking Form (minimal changes)

The booking form module path stays at `frontend/src/modules/presmeet/` (can be renamed later). Changes:

1. **API endpoints** — point to new generic endpoints with `event_id` param
2. **Product loading** — fetch products by event's `product_ids[]` instead of `source='presmeet_config'`
3. **Event detection** — accept `event_id` from route params instead of hardcoded presmeet scan
4. **Everything else stays the same** — wizard UX, form state, validation, PDF download

### Self-Service (external members)

External members see a reduced self-service view:

- Profile editing (name, phone, etc.)
- Club assignment (read-only after set)
- Event access list (read-only, shows which events they can access)

## Multi-Language (i18n) Design

### Namespace Migration

| Current         | New                            | Scope                                             |
| --------------- | ------------------------------ | ------------------------------------------------- |
| `presmeet.json` | `eventBooking.json`            | All event booking UI strings                      |
| —               | `eventLanding.json` (optional) | Landing page UI chrome (CTA labels, error states) |

### Translation File Structure

```
frontend/public/locales/{lang}/eventBooking.json
```

Languages: nl, en, de, fr, es, it, da, sv (8 total)

### Key Naming Convention

Generic, not event-type-specific:

```json
{
  "booking": {
    "title": "Event Booking",
    "addPerson": "Add person",
    "submit": "Submit booking",
    "save": "Save draft",
    "status": {
      "draft": "Draft",
      "submitted": "Submitted",
      "locked": "Locked"
    }
  },
  "form": {
    "delegates": "Delegates",
    "guests": "Guests",
    "products": "Products"
  },
  "errors": {
    "notFound": "Booking not found",
    "noAccess": "You don't have access to this event",
    "clubRequired": "Club assignment required for this event",
    "registrationClosed": "Registration is closed"
  },
  "landing": {
    "registerButton": "Register Now",
    "goToBooking": "Go to Booking",
    "registrationClosed": "Registration is closed",
    "alreadyRegistered": "You are already registered"
  }
}
```

### What's Translated vs What's Not

| Translated (i18n keys)                     | Not translated (stored content)                    |
| ------------------------------------------ | -------------------------------------------------- |
| Button labels, form labels, error messages | Event name, tagline, landing page sections         |
| Navigation items, status labels            | Product names, field labels (from Producten table) |
| Page titles, tooltips                      | Constraint labels (from Event record)              |
| Validation error templates                 | Admin-configured content                           |

Product field labels (from `order_item_fields`) and constraint labels come from the database — they're configured per event by the admin and are typically in the event's primary language. The UI framework around them is translated.

## Migration Strategy

### Clean Slate Approach

All existing orders are test data — no production orders exist. This means:

- No order data migration or backfill needed
- No backward compatibility for order formats
- Old and new GSI don't need to coexist
- Old handlers can be removed in the same deployment

### Migration Steps (single deployment)

1. Delete all records from Orders table (test data cleanup)
2. Delete old `event-club-index` GSI
3. Create new `event-member-index` GSI (PK: `source_id`, SK: `member_id`)
4. Add `member_type` and `allowed_events` to Members records (backfill script)
5. Deploy new generic handlers + remove old presmeet handlers in one SAM deploy
6. Deploy frontend with new endpoint paths

### Members Table Backfill

```python
# For all existing members:
member['member_type'] = 'hdcn_member'
member['allowed_events'] = []

# For members with Regio_Pressmeet Cognito group:
member['allowed_events'] = [ACTIVE_PRESMEET_EVENT_ID]
# Then remove Regio_Pressmeet from their Cognito groups
```

### Cognito Cleanup

- Remove `Regio_Pressmeet` from all users who have it
- Delete the `Regio_Pressmeet` group from the user pool
- Create new `event_participant` group for external event participants
- Event access is purely data-driven via `allowed_events`
- External members get `event_participant` group only

### Presmeet Artifacts to Remove

The following presmeet-specific items are fully removed during migration:

**Cognito:**

- `Regio_Pressmeet` group (removed from all users, then deleted)

**Backend handlers (removed from SAM template + directories deleted):**

- `get_presmeet_booking`
- `submit_presmeet_booking`
- `create_presmeet_payment`
- `lock_presmeet_orders`
- `get_presmeet_config`
- `presmeet_manage_delegates`

**Shared auth layer modules (deleted):**

- `shared/club_identity.py` (`get_club_id`, `has_presmeet_access`, `is_presmeet_admin`, `is_presmeet_admin_write`)
- `shared/presmeet_validation.py` (renamed to `shared/event_validation.py`)

**DynamoDB:**

- `event-club-index` GSI on Orders table (deleted)
- All existing order records (test data, deleted)

**Tests (deleted or rewritten):**

- `tests/unit/test_get_presmeet_booking.py`
- `tests/unit/test_presmeet_generate_report.py`
- `tests/unit/test_presmeet_manage_delegates.py`
- `tests/unit/test_presmeet_v2_access.py`

**Frontend:**

- `presmeet.json` translation files (all 8 languages — migrated to `eventBooking.json`)
- `presmeetApi.ts` legacy service methods (replaced by generic event API client)
- Hardcoded `source='presmeet'` / `event_type='presmeet'` references in components

**Scripts/test data:**

- `scripts/seed-test-data.py` references to `Regio_Pressmeet` (update to use `allowed_events`)
- `scripts/data/club_registry.json` (kept — still used for club-scoped events)

### Rollback Plan

Since no production data exists:

- Rollback = redeploy old SAM template + recreate old GSI
- No data loss risk (orders table was empty anyway)

## API Endpoint Design

### Unified Order Endpoints

One set of endpoints handles both webshop and event orders. The `source_id` parameter determines behavior:

| Method | Path                           | Description                                     |
| ------ | ------------------------------ | ----------------------------------------------- |
| GET    | `/orders?source_id={id}`       | Get or create member's order (webshop or event) |
| PUT    | `/orders/{order_id}`           | Save draft order                                |
| POST   | `/orders/{order_id}/submit`    | Validate and submit                             |
| POST   | `/orders/{order_id}/pay`       | Initiate Mollie payment                         |
| POST   | `/orders/{order_id}/delegates` | Manage delegates (club-scoped orders only)      |

**Behavior by source_id:**

| Behavior            | `source_id = "webshop"` | `source_id = <event_id>`                |
| ------------------- | ----------------------- | --------------------------------------- |
| Access check        | `hdcnLeden` group       | `has_event_access(member_id, event_id)` |
| Registration window | Always open             | Event `status = open` required          |
| Order scope         | Always `"member"`       | Event's `order_scope` field             |
| Products available  | Full catalog            | Event's `product_ids[]`                 |
| Constraints         | None                    | Event's `constraints[]`                 |
| Payment             | Mollie                  | Mollie                                  |

### Admin Endpoints

| Method | Path                                   | Description                        |
| ------ | -------------------------------------- | ---------------------------------- |
| POST   | `/admin/orders/lock?source_id={id}`    | Lock submitted orders for a source |
| POST   | `/admin/orders/{order_id}/unlock`      | Unlock a specific order            |
| POST   | `/admin/events/{event_id}/access`      | Grant/revoke member event access   |
| GET    | `/admin/events/{event_id}/access`      | List members with access           |
| GET    | `/admin/reports/{type}?source_id={id}` | Generate reports for a source      |

### No Backward Compatibility

This is a clean break. `Regio_Pressmeet` is deleted, old handlers are removed, old tests are deleted. The frontend is updated to use new endpoints in the same deployment. No forwarding, no wrappers.

## Event Landing Page Design

### Data Model (Event record extension)

```python
{
    "event_id": "uuid",
    "landing_page": {                    # Optional — omit or set enabled=False to disable
        "enabled": True,
        "slug": "presmeet-2027",         # URL-friendly, unique across events
        "hero_image_url": "https://s3.../hero.jpg",
        "tagline": "Join HD clubs from across Europe",
        "registration_label": "Register Now",
        "logos": [
            {"name": "H-DCN", "logo_url": "https://..."},
            {"name": "FH-DCE", "logo_url": "https://..."}
        ],
        "sections": [
            {"type": "text", "title": "Program", "content": "Markdown or HTML content..."},
            {"type": "text", "title": "Venue", "content": "..."},
            {"type": "logos", "title": "Participating Clubs", "items": [
                {"name": "Club Name", "logo_url": "https://..."}
            ]}
        ]
    }
}
```

### Public API Endpoint

```
GET /events/public/{slug}   ← no auth required
```

Returns: event name, dates, location, landing_page config, and registration status (open/closed). Does NOT return sensitive data (constraints, product_ids, order counts).

### Frontend Route

```
/events/:slug/info          ← public route, no AuthGuard
```

Renders landing page from API response. The CTA button behavior:

- Not logged in → navigate to `/events/:slug/register` (sign-up/login form with event context)
- Logged in, no access → auto-grant access + redirect to booking
- Logged in, has access → direct link to booking form

### Cognito Sign-Up with Event Context

```typescript
// Frontend sign-up call (from event registration page)
await signUp({
  username: email,
  password,
  options: {
    userAttributes: { email, given_name, family_name },
    clientMetadata: { event_id: eventUuid, source: "event_landing" },
  },
});
```

The `clientMetadata` flows to post-confirmation Lambda:

```python
def handle_signup_confirmation(user_pool_id, username, email, ...):
    client_metadata = event.get('request', {}).get('clientMetadata', {})
    event_id = client_metadata.get('event_id')
    source = client_metadata.get('source')

    if source == 'event_landing' and event_id:
        # External/event registration
        create_member_record(
            email=email,
            member_type='event_participant',
            allowed_events=[event_id],
            status='active'
        )
        add_user_to_group(user_pool_id, username, 'event_participant')
    else:
        # Regular H-DCN signup flow (existing logic)
        ...
```

### Open Graph Meta Tags

For social sharing, the public landing page needs proper meta tags. Options:

1. **Lambda@Edge** on CloudFront — intercept requests to `/events/*/info` and inject `<meta>` tags in the HTML response
2. **Dynamic `<Helmet>`** in React — works for crawlers that execute JS (Twitter, Slack, Discord) but not for Facebook/LinkedIn
3. **Pre-render** — generate static HTML for each landing page with correct meta tags

Recommended: Option 1 (Lambda@Edge) for reliable social sharing across all platforms.
