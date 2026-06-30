# ADR: Event Lifecycle Status Model

**Date:** 2026-06-23
**Status:** Accepted
**Context:** The `status` field on events was used incorrectly as a proxy for registration state. This led to confusion: events without a `status` field showed "registration closed" even when registration dates were valid.

## Decision

The event `status` field controls **publication state** only. Registration availability is determined by **date fields** independently.

### Status Values

| Status      | Meaning                         | Landing page        | Admin          | Data                 |
| ----------- | ------------------------------- | ------------------- | -------------- | -------------------- |
| `draft`     | Work in progress, not published | Not accessible      | Editable       | Not visible to users |
| `published` | Live, publicly accessible       | Accessible via slug | Editable       | Visible              |
| `archived`  | No longer active, historical    | Not accessible      | Read-only view | Not visible          |

### Registration Availability (independent of event dates)

Registration is open when ALL of these are true:

1. `status == 'published'`
2. Today >= `registration_open` (if set)
3. Today <= `registration_close` (if set)

If `registration_open` or `registration_close` are not set, that boundary is not enforced.

### Event Dates (informational only)

`start_date` and `end_date` are purely informational — they tell the user when the event takes place. They have NO impact on registration, booking access, or landing page visibility.

### Migration

- Existing events with `status: 'open'` → treat as `published` (backward compatible)
- Existing events with no `status` field → treat as `published` (backward compatible)
- Existing events with `status: 'closed'` → treat as `archived`
- The value `open` is deprecated but accepted as alias for `published`

## Consequences

- The EventForm must allow setting status to draft/published/archived
- The `_determine_registration_status` function in `get_event_public` must use date logic
- The landing page route (`/events/:slug/info`) returns 404 for draft/archived events
- Booking page remains accessible for published events regardless of registration dates (users with existing bookings can still view them)
