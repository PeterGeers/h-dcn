# Decision: Closed Community Booking Architecture

**Date:** 2026-06  
**Status:** Accepted  
**Predecessor:** `webshop-as-event.md` (products linked to events via `event_ids`)  
**Affects:** Events table, Orders table, Members table, S3 registry storage, Cognito user creation

## Context

H-DCN needs a generic booking system for invitation-only events (e.g., President's Meet). Key constraints:

- Only invited guests (identified by a shared event password + invitee registry) may register
- Each registry row (club/team/individual) gets exactly one order
- A primary delegate claims a row and manages the booking; an optional secondary delegate can co-manage
- Per-person product selection with dual quantity limits (per-order + per-event capacity)
- Must work for guests who have no existing H-DCN account
- Must reuse existing Orders, Products, and Payments infrastructure
- Scale target: ~200 rows per event (max theoretical: ~1500-2000)

## Decisions

### 1. Registry-driven approach: S3 static + DynamoDB claims

**Static data (S3):** The invitee registry (`invitee_registry.json`) is an admin-uploaded JSON file stored in S3. It contains all allowed booking slots (rows) with labels, logos, and optional email restrictions. This file is read-only at runtime.

**Runtime state (DynamoDB):** Row claims are stored as a `registry_claims` map attribute on the Event record in DynamoDB. Each key is a `row_id`, each value contains `member_id`, `email`, `name`, `claimed_at`.

**Why split:** Admin uploads are infrequent and don't need DynamoDB write capacity. Claims are frequent, need atomicity, and benefit from DynamoDB's conditional writes. Keeping claims on the Event record avoids a new table and keeps the data co-located with event configuration.

### 2. Atomic claims via DynamoDB conditional writes

Row claims use a `ConditionExpression: attribute_not_exists(registry_claims.#row)` on an `UpdateItem` call. This guarantees exactly-once claiming with no race conditions — if two users click "claim" simultaneously, one gets 200 and the other gets 409.

No separate Claims table is needed because the entire claims map fits within a single DynamoDB item (see scaling boundary below).

### 3. Scaling boundary: ~1500-2000 rows per event item

DynamoDB has a 400 KB item size limit. Each claim entry is approximately 200-250 bytes (member_id, email, name, ISO timestamp). With `registry_config` and other Event fields consuming ~5-10 KB, this leaves room for roughly 1500-2000 claims per Event item.

For H-DCN's use case (~200 rows per event), this provides 7-10x headroom. If a future event exceeds this limit, the architecture would need to move claims to a separate table with a GSI on `event_id`.

**Decision:** Accept this limit. Document it here. Monitor item sizes in production. Revisit if an event approaches 1000 rows.

### 4. Password gate + session token pattern

The registration flow starts with a shared event password (bcrypt-hashed on the Event record). On successful verification, the backend issues a short-lived JWT session token (15-minute TTL) containing `{ event_id, verified_at }`.

This token is required by the onboard endpoint to prevent direct API abuse — users cannot skip the password gate by calling the onboard API directly. The short TTL limits the window for token replay.

**Why not a Cognito session:** The user may not have an account yet at password verification time. The session token bridges the gap between "verified the event password" and "created/linked an account."

### 5. Extend EventRegisterPage rather than create new pages

The landing flow (password → registry → claim → booking) is implemented as a step machine within the existing `EventRegisterPage` component, not as separate route pages.

**Why:**

- Shared state (session token, selected row, event config) flows naturally between steps without URL params or global state
- No intermediate URLs to bookmark or share in invalid states
- Browser back button doesn't leave users in broken half-states
- Follows the existing pattern of multi-step flows in the portal (registration wizard, checkout)

### 6. Onboard endpoint: single atomic-ish operation with rollback

The `event_onboard` endpoint combines three operations in sequence:

1. Claim the row (DynamoDB conditional write)
2. Create or link Cognito user
3. Create or update Member record

If step 2 fails → release the claim (rollback step 1).  
If step 3 fails → delete the Cognito user + release the claim (rollback steps 1-2).

**Why not a Step Function:** The operations complete in <2 seconds total. A Step Function adds cold start overhead, IAM complexity, and observability cost for a flow that rarely fails. Simple try/except rollback is sufficient at this scale.

### 7. Payment via Mollie, decoupled from submission

Payment is a separate step after order submission. An order can be submitted (visible to admins, lockable) without being paid. This matches the existing `pay_order` handler pattern and allows admins to lock registrations before payment deadlines.

**Mollie** is the payment provider (existing integration), not Stripe. The webshop uses Stripe, but event bookings use Mollie for IDEAL/Bancontact support preferred by the event demographic.

## Consequences

### Positive

- No new DynamoDB tables required — all state lives on existing tables (Events, Orders, Members)
- Atomic claims with zero race conditions
- Existing Orders/Products/Payments infrastructure reused without modification
- New users get a full Cognito account immediately — no "pending" state
- Admin dashboard reads from existing data (no ETL or aggregation tables needed)

### Negative

- Event item size is bounded (~1500-2000 rows max) — acceptable for H-DCN scale
- Rollback logic in onboard is manual (not transactional) — rare failure modes may leave partial state that admins must clean up via claims management UI
- Session token adds a custom JWT layer alongside Cognito tokens — two token types in the frontend

### Neutral

- S3 registry file must be re-uploaded to change row data (no in-place editing via API)
- Admin claims management UI needed for operational flexibility (release, reassign, manual assign)

## When to Reconsider

- If an event needs >1000 rows → move claims to a separate DynamoDB table with GSI
- If onboard failures become frequent → consider AWS Step Functions for orchestration
- If multiple events share the same registry → add registry versioning or a shared registry table
- If real-time collaboration between delegates is needed → add WebSocket notifications instead of optimistic locking
