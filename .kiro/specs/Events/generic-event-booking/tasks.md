# Implementation Plan

## Overview

This plan implements the generic event booking system for H-DCN, replacing the hardcoded Pressmeet booking flow with a unified, event-driven architecture. It covers infrastructure migration (new GSI, member attributes), unified order handlers supporting both webshop and event sources, frontend updates for event booking and external member self-service, an optional public event landing page with self-registration, and documentation updates.

**Deployment Strategy:** All work is done on a feature branch. Each phase is validated on the **test environment** before pushing to main for production deployment. See `.kiro/specs/test-staging-environment/` for full test environment documentation.

```
Feature branch → Deploy to h-dcn-test → Verify on testportal.h-dcn.nl → Push to main → CI deploys to h-dcn (prod)
```

**Test environment summary:**

- Backend: `sam deploy --stack-name h-dcn-test --parameter-overrides Stage=test ...`
- Tables: `Orders-Test`, `Members-Test`, `Events-Test`, `Producten-Test`, etc.
- Frontend: `testportal.h-dcn.nl`
- Cognito: shared pool `eu-west-1_fcUkvwjH5` (test users distinguished by prefix)
- Profile: `--profile nonprofit-deploy`

**Infrastructure scripts** have a `--stage` parameter:

- `--stage test`: targets `-Test` tables
- `--stage prod`: targets production tables

**Seeding scripts** create test data in the test environment for manual verification.

## Tasks

### Phase 1: Infrastructure & Migration (Clean Slate)

#### Test Environment First

- [x] 1. Clean Orders-Test table and set up new GSI
  - [x] 1.1. Create script `backend/scripts/clean_orders_and_replace_gsi.py` with `--stage` parameter
  - [x] 1.2. Run with `--stage test`: delete all records from Orders-Test table
  - [x] 1.3. Run with `--stage test`: delete old `event-club-index` GSI from Orders-Test (if exists)
  - [x] 1.4. Run with `--stage test`: create new `event-member-index` GSI (PK: `source_id`, SK: `member_id`, Projection: ALL)
  - [x] 1.5. Wait for GSI to become ACTIVE on Orders-Test
  - [x] 1.6. Verify GSI works with a manual test query

- [x] 2. Add `member_type` and `allowed_events` to Members-Test + Cognito cleanup
  - [x] 2.1. Create script `backend/scripts/migrate_members_and_cognito.py` with `--stage` parameter
  - [x] 2.2. Run with `--stage test`: set `member_type = "hdcn_member"` on all Members-Test records
  - [x] 2.3. Run with `--stage test`: add `allowed_events = []` to all Members-Test records
  - [x] 2.4. Run with `--stage test`: for test users with `Regio_Pressmeet`, add test event_id to `allowed_events`
  - [x] 2.5. Run with `--stage test`: remove `Regio_Pressmeet` from test users
  - [x] 2.6. Create `event_participant` Cognito group (shared pool — only once, not per stage)
  - [x] 2.7. Verify test users can still access the test environment

- [x] 3. Deploy `shared/event_access.py` to auth layer
  - [x] 3.1. Create `backend/layers/auth-layer/python/shared/event_access.py` with `has_event_access(member_id, event_id)` function
  - [x] 3.2. Pure `allowed_events` check — no Cognito group logic, no legacy mappings
  - [x] 3.3. Add helper `get_member_allowed_events(member_id)` that reads from Members table
  - [x] 3.4. Write unit tests for event_access module
  - [x] 3.5. Deploy to test stack: `sam deploy --stack-name h-dcn-test --parameter-overrides Stage=test ...`
  - [x] 3.6. Verify auth layer works on test stack

- [x] 4. Seed test data for verification
  - [x] 4.1. Create/update `backend/scripts/seed_event_test_data.py`
  - [x] 4.2. Seed: a test event with `order_scope="club"`, `product_ids`, `constraints`, `status="open"`
  - [x] 4.3. Seed: a test event with `order_scope="member"` for individual registration
  - [x] 4.4. Seed: test products linked to the events via `product_ids`
  - [x] 4.5. Seed: test members with `allowed_events` populated
  - [x] 4.6. Run against test environment

### Phase 2: Unified Order Handlers

#### Develop & Test

- [x] 5. Create `get_order` handler
  - [x] 5.1. Create `backend/handler/get_order/app.py`
  - [x] 5.2. Accept `source_id` from query params (`"webshop"` or event UUID)
  - [x] 5.3. If `source_id` is an event UUID: load event record, read `order_scope`, check `has_event_access(member_id, event_id)`
  - [x] 5.4. If `source_id = "webshop"`: verify `hdcnLeden` group, order_scope is always `"member"`
  - [x] 5.5. If `order_scope = "member"`: query GSI with `source_id + member_id`, create draft if none exists
  - [x] 5.6. If `order_scope = "club"`: resolve `club_id` from member, query GSI PK-only, filter by `club_id`, verify delegate access, create draft if none exists
  - [x] 5.7. Add handler to SAM template
  - [x] 5.8. Write unit tests (webshop source, event source, both scopes)
  - [x] 5.9. Deploy to test stack, verify with seeded test data

- [x] 6. Create `submit_order` handler
  - [x] 6.1. Create `backend/handler/submit_order/app.py`
  - [x] 6.2. Reuse existing validation logic — rename `shared/presmeet_validation.py` to `shared/event_validation.py`
  - [x] 6.3. Reuse `shared/event_constraints.py` unchanged
  - [x] 6.4. If source is event: load products via event's `product_ids[]`, apply event constraints
  - [x] 6.5. If source is webshop: load products from catalog, no event constraints
  - [x] 6.6. Query all orders for source via `event-member-index` for constraint validation (events only)
  - [x] 6.7. Verify order ownership by `member_id`
  - [x] 6.8. Add handler to SAM template
  - [x] 6.9. Write unit tests
  - [x] 6.10. Deploy to test stack, verify submission flow

- [ ] 7. Create `create_payment` handler
  - [x] 7.1. Create `backend/handler/create_payment/app.py`
  - [x] 7.2. Look up order by `order_id`, verify ownership
  - [x] 7.3. Create Mollie payment for outstanding balance (same flow for webshop and events)
  - [x] 7.4. Store payment record with order's `source_id`
  - [x] 7.5. Add handler to SAM template
  - [x] 7.6. Write unit tests
  - [x] 7.7. Deploy to test stack, verify Mollie integration (test mode)

- [x] 8. Create `lock_orders` handler
  - [x] 8.1. Create `backend/handler/lock_orders/app.py`
  - [x] 8.2. Accept `source_id` param, query all orders via `event-member-index`
  - [x] 8.3. Lock submitted orders (same logic as current handler)
  - [x] 8.4. Admin access check: use existing permission pattern
  - [x] 8.5. Add handler to SAM template
  - [x] 8.6. Write unit tests
  - [x] 8.7. Deploy to test stack, verify lock/unlock flow

- [x] 9. Create `manage_delegates` handler
  - [x] 9.1. Create `backend/handler/manage_delegates/app.py`
  - [x] 9.2. Add/remove secondary delegate on an order (uses `member_id`)
  - [x] 9.3. Verify requester is primary delegate or admin
  - [x] 9.4. Only applicable when `order_scope = "club"`
  - [x] 9.5. Add handler to SAM template
  - [x] 9.6. Write unit tests
  - [x] 9.7. Deploy to test stack on github, verify delegate management

- [x] 10. Create `manage_event_access` handler
  - [x] 10.1. Create `backend/handler/manage_event_access/app.py`
  - [x] 10.2. POST: grant/revoke — add/remove event_id from member's `allowed_events`
  - [x] 10.3. GET: list members with access to event_id
  - [x] 10.4. Require admin permissions (Events_CRUD or System_CRUD)
  - [x] 10.5. Support bulk operations (multiple member_ids in one request)
  - [x] 10.6. Add handler to SAM template
  - [x] 10.7. Write unit tests
  - [x] 10.8. Deploy to test stack on github, verify access grant/revoke

- [x] 11. Update `event_status_scheduler` to use new GSI
  - [x] 11.1. Change `EVENT_CLUB_INDEX` to `event-member-index` in `_auto_lock_orders()`
  - [x] 11.2. Update query: the GSI PK is now `source_id` (which holds the event_id for event orders)
  - [x] 11.3. Update unit tests
  - [x] 11.4. Deploy to test stack on github, verify auto-lock still works

- [x] 12. Remove old handlers from SAM template
  - [x] 12.1. Remove presmeet handlers: `get_presmeet_booking`, `submit_presmeet_booking`, `create_presmeet_payment`, `lock_presmeet_orders`, `get_presmeet_config`, `presmeet_manage_delegates`
  - [x] 12.2. Remove webshop order handlers replaced by unified handlers
  - [x] 12.3. Delete old handler directories
  - [x] 12.4. Remove `shared/club_identity.py` and old `shared/presmeet_validation.py`
  - [x] 12.5. Verify all imports reference `shared/event_validation.py`
  - [x] 12.6. Delete presmeet-specific tests: `test_get_presmeet_booking.py`, `test_presmeet_generate_report.py`, `test_presmeet_manage_delegates.py`, `test_presmeet_v2_access.py`
  - [x] 12.7. Update `scripts/seed-test-data.py` — remove `Regio_Pressmeet` references, use `allowed_events`
  - [x] 12.8. Remove any hardcoded `source='presmeet'` or `source='presmeet_config'` references
  - [x] 12.9. Deploy to test stack on github, run full test suite, verify nothing is broken

#### Test Environment Sign-Off

- [x] 13. Full test environment validation
  - [x] 13.1. Run `pytest tests/` — all unit tests pass
  - [x] 13.2. Manual test: create order via webshop flow (test portal)
  - [x] 13.3. Manual test: create order via event booking flow (club-scoped)
  - [x] 13.4. Manual test: create order via event booking flow (member-scoped)
  - [x] 13.5. Manual test: submit, pay (Mollie test mode), lock flow
  - [x] 13.6. Manual test: delegate management (add/remove secondary)
  - [x] 13.7. Manual test: event access grant/revoke via admin
  - [x] 13.8. Manual test: event_participant user can only access allowed events
  - [x] 13.9. Verify no regressions in existing webshop functionality

#### Push to Production

- [x] 14. Production deployment
  - [x] 14.1. Push feature branch to main (triggers CI: tests → sam build → sam deploy to h-dcn)
  - [x] 14.2. Run `clean_orders_and_replace_gsi.py --stage prod` — clean prod Orders table, swap GSI
  - [x] 14.3. Run `migrate_members_and_cognito.py --stage prod` — backfill members, remove Regio_Pressmeet, delete group
  - [x] 14.4. Run `seed_event_test_data.py --stage prod` — seed the real Presidents Meeting 2027 event + products
  - [x] 14.5. Verify production portal works (login, webshop, event booking)
  - [x] 14.6. Verify existing H-DCN members with former Regio_Pressmeet still have event access via `allowed_events`

### Phase 3: Frontend Updates

- [x] 15. Update Booking Form API client
  - [x] 15.1. Update `presmeetApi.ts` to accept `source_id` parameter on all calls
  - [x] 15.2. Change endpoint paths to unified `/orders` endpoints
  - [x] 15.3. Update product loading: fetch by event's `product_ids` instead of config endpoint
  - [x] 15.4. Keep all form state management, validation, and UX unchanged
  - [x] 15.5. Update TypeScript types to include `source_id` and `member_id` on Order
  - [x] 15.6. Deploy frontend to test (testportal.h-dcn.nl), verify

- [x] 16. Update Booking Form routing
  - [x] 16.1. Accept `event_id` from route params (e.g., `/events/:eventId/booking`)
  - [x] 16.2. Remove hardcoded presmeet event detection
  - [x] 16.3. Event selector on dashboard navigates to correct event booking
  - [x] 16.4. Verify on test portal

- [x] 17. Add external member self-service view
  - [x] 17.1. Detect `member_type = "event_participant"` after login
  - [x] 17.2. Show reduced navigation (profile + event bookings only)
  - [x] 17.3. Display list of accessible events from `allowed_events`
  - [x] 17.4. Link each event to its booking form
  - [x] 17.5. Verify on test portal with test event_participant user

- [x] 18. Update Admin Event Dashboard
  - [x] 18.1. Add "Manage Access" tab/section to event admin
  - [x] 18.2. Show list of members with access to selected event
  - [x] 18.3. Add/remove member access (calls `manage_event_access` handler)
  - [x] 18.4. Bulk grant option
  - [x] 18.5. Verify on test portal

- [x] 19. Multi-language (i18n) for event booking
  - [x] 19.1. Create `eventBooking` namespace: `frontend/public/locales/{lang}/eventBooking.json` for all 8 languages
  - [x] 19.2. Migrate keys from `presmeet.json` to `eventBooking.json`
  - [x] 19.3. Add new keys for: landing page UI chrome, self-registration flow, event access errors, external member self-service
  - [x] 19.4. Update all event booking components to use `useTranslation('eventBooking')`
  - [x] 19.5. Ensure no hardcoded user-facing strings in new components
  - [x] 19.6. Remove old `presmeet.json` namespace files
  - [x] 19.7. Verify all 8 languages on test portal

#### Frontend Push to Production

- [x] 20. Frontend production deployment
  - [x] 20.1. Push frontend changes to main (triggers CI: build → S3 sync → CloudFront invalidation)
  - [x] 20.2. Verify production portal: webshop flow, event booking, admin dashboard
  - [x] 20.3. Verify translations load correctly in all languages

### Phase 4: Event Landing Page (Optional Feature)

- [x] 21. Create public event API endpoint
  - [x] 21.1. Create `backend/handler/get_event_public/app.py` — NO auth required
  - [x] 21.2. Accept `slug` path parameter, resolve to event_id
  - [x] 21.3. Return event name, dates, location, `landing_page` config, registration status
  - [x] 21.4. Exclude sensitive data (constraints, product_ids, order counts)
  - [x] 21.5. Add handler to SAM template with no auth requirement
  - [x] 21.6. Write unit tests
  - [x] 21.7. Deploy to test stack, verify

- [x] 22. Create Event Landing Page frontend component
  - [x] 22.1. Create public route `/events/:slug/info` (no AuthGuard)
  - [x] 22.2. Build `EventLandingPage` component with: Hero, sections, logos, CTA button
  - [x] 22.3. Fetch event data from public endpoint
  - [x] 22.4. Show "Registration Closed" state when event is not `open`
  - [x] 22.5. Responsive styling (Chakra UI), loading/error states
  - [x] 22.6. Use `useTranslation('eventBooking')` for UI chrome
  - [x] 22.7. Verify on test portal

- [x] 23. Implement self-registration flow from landing page
  - [x] 23.1. CTA button logic: check auth state → sign-up/login or auto-grant
  - [x] 23.2. Create `/events/:slug/register` page
  - [x] 23.3. Pass `event_id` as `clientMetadata` in Amplify `signUp()` call
  - [x] 23.4. After signup: check `allowed_events`, add if missing, redirect to booking form
  - [x] 23.5. Handle "already has access" case
  - [x] 23.6. Verify full flow on test portal with new user

- [x] 24. Update `cognito_post_confirmation` trigger
  - [x] 24.1. Read `clientMetadata.event_id` and `clientMetadata.source` from trigger event
  - [x] 24.2. If `source == 'event_landing'` and `event_id` present: create Members record with `member_type='event_participant'`, `allowed_events=[event_id]`, `status='active'`
  - [x] 24.3. Add user to `event_participant` Cognito group (NOT hdcnLeden)
  - [x] 24.4. If no event context: existing flow (no auto member creation)
  - [x] 24.5. Write unit tests for both paths
  - [x] 24.6. Deploy to test stack, test full sign-up-to-booking flow

- [x] 25. Open Graph meta tags for social sharing
  - [x] 25.1. Add React Helmet dynamic meta tags (title, description, image)
  - [x] 25.2. (Optional) Lambda@Edge for non-JS crawlers
  - [x] 25.3. Test link previews on Slack, WhatsApp, LinkedIn

- [x] 26. Admin: landing page configuration
  - [x] 26.1. Add `landing_page` section to event create/edit form
  - [x] 26.2. Fields: enabled toggle, slug, hero image upload, tagline, sections editor, logos
  - [x] 26.3. Slug uniqueness validation
  - [x] 26.4. Preview mode
  - [x] 26.5. Verify on test portal

#### Landing Page Push to Production

- [x] 27. Landing page production deployment
  - [x] 27.1. Push to main
  - [x] 27.2. Configure landing page on production PresMeet 2027 event
  - [x] 27.3. Test public URL + registration flow on production

### Phase 5: Documentation

- [ ] 28. Documentation update
  - [ ] 28.1. Update `infrastructure/README.md` with new GSI info
  - [ ] 28.2. Update steering files with new handler patterns
  - [ ] 28.3. Document external member registration flow
  - [ ] 28.4. Document admin event access management
  - [ ] 28.5. Document event landing page configuration
  - [ ] 28.6. Document i18n namespace structure and key conventions
  - [ ] 28.7. Update `scripts/seed-test-data.py` documentation

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1"] },
    { "id": 1, "tasks": ["2"] },
    { "id": 2, "tasks": ["3"] },
    { "id": 3, "tasks": ["4"] },
    { "id": 4, "tasks": ["5", "6", "7", "8", "9", "10", "11"] },
    { "id": 5, "tasks": ["12"] },
    { "id": 6, "tasks": ["13"] },
    { "id": 7, "tasks": ["14"] },
    { "id": 8, "tasks": ["15", "16", "17", "18", "19"] },
    { "id": 9, "tasks": ["20"] },
    { "id": 10, "tasks": ["21", "22", "23", "24", "25", "26"] },
    { "id": 11, "tasks": ["27"] },
    { "id": 12, "tasks": ["28"] }
  ]
}
```

## Notes

- Phase 4 (Event Landing Page) is optional and can be deferred to a follow-up iteration if needed.
- All infrastructure scripts support `--stage test` and `--stage prod` to safely target environments.
- The Cognito `event_participant` group is created once in the shared pool (not per stage).
- Production deployment steps include data migration scripts that must run in order after the code deploy.
- The existing webshop flow must continue working throughout all phases — no regressions allowed.
