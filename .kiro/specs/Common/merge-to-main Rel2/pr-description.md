# Release 2: Closed Community Booking + Event System Alignment

## Summary

Squash-merge of `feature/closed-community-booking` (148 commits) into `main`. This release unifies the event system, adds the closed community booking flow, and includes several fixes and improvements.

## What's Included

### Event System Alignment

- Unified event pipeline with Field Registry compliance
- Sequential access checks (status → registration dates → access level)
- `get_events` filter: non-admin users see only `status === 'published'`
- Event type classification (`webshop`, `presmeet`, `tourweekend`, `alv`, etc.)

### Closed Community Booking

- Full attendee-based booking flow: password gate → registry selector → claim → booking wizard
- Club/registry row system: attendees select their organization from an S3-hosted registry
- Delegate management: per-person product configuration with order_item_fields
- Event onboarding with session tokens (per-event JWT secrets)

### i18n Error Messages

- `error_key` adoption across handlers (machine-readable error codes)
- Frontend can translate backend errors using locale-specific messages
- Affected handlers: get_order, update_order_items, update_product, update_event, and more

### Webshop Fix

- Unified product pipeline via `evt-webshop` virtual event
- WebshopPage loads products from `evt-webshop.product_ids` (with fallback to all active products)
- Filter groups/subgroups with translation keys

### Dashboard Improvements

- Admin card visibility: event booking cards hidden for admins (they use the event admin page)
- Event card filtering: only `status === 'published'` events shown, webshop excluded
- "Test booking" button on event admin for events with product_ids

### ggshield Optimization

- Local regex scanner for pre-commit (no API calls during development)
- API scan only on push (native git hook in `.githooks/pre-push`)
- Eliminates "no more API calls" errors during spec sessions

### SAM Template Fixes

- Added missing `MEMBERS_TABLE_NAME` and `EVENTS_TABLE_NAME` env vars for `WebshopSubmitOrderFunction`

## Data Migration Required

**Run BEFORE merge** (step 6 in release plan):

1. `migrate_events_prod.py` — adds `name`, `status: 'published'`, `event_type`, `participation`, `linked_regio` to prod Events
2. Populate `evt-webshop.product_ids` — scan Producten for active parent products

See `scripts/MIGRATIONS.md` for full migration tracking.

## What's NOT Included

- No DynamoDB schema changes that would break existing data
- No Cognito configuration changes
- Prod Events table is read-only in this code (filter/read only, no writes)
- PresMeet module unchanged (out of scope)

## Testing

- Backend: 1229 tests passing (28 pre-existing failures unrelated to this branch)
- Frontend: 1478 tests passing (35 pre-existing failures unrelated to this branch)
- Full nightly test suite run on this branch
- Manual testing on testportal.h-dcn.nl

## Deployment

Both workflows trigger automatically on push to `main`:

- `deploy-backend.yml` — SAM build + deploy
- `deploy-frontend.yml` — React build + S3 sync + CloudFront invalidation
