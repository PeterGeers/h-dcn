# Requirements Document

## Introduction

This document specifies the requirements for generalizing the event booking system from the current PresMeet-specific implementation to a generic, event-driven architecture. The system must support any event type (Presidents Meeting, Rally, Members Day, etc.) with a unified order pipeline, event-scoped access control, and support for external (non-H-DCN) club members who register solely to participate in a specific event. The existing booking form logic (person-centric wizard, product configuration, validation, payment) is preserved and generalized.

## Glossary

- **Event_Booking_System**: The generalized event order management system handling the full lifecycle from registration through draft, submission, payment, and locking — for any event type
- **Order_Pipeline**: The unified backend service for creating, updating, validating, and managing orders regardless of source (webshop or event)
- **Event_Service**: The backend service managing Event records (create, open, close, archive) in the Events DynamoDB table
- **source_id**: The universal order origin identifier — either `"webshop"` for shop orders or the event's UUID for event orders
- **Event_Participant**: A member (H-DCN or external club) who has been granted access to a specific event's booking form
- **External_Member**: A non-H-DCN club member who registers on the portal solely to participate in a specific event, with limited permissions
- **Booking_Form**: The existing person-centric wizard component that allows delegates to manage persons and their associated products per event
- **Booking_Manager**: An admin who configures which products are available for purchase for a specific event (via the event's `product_ids` list)
- **event-member-index**: The new DynamoDB GSI on the Orders table (PK: `source_id`, SK: `member_id`) replacing the current `event-club-index`

## Requirements

### Requirement 1: Unified Order Source Model

**User Story:** As a developer, I want every order to carry a `source_id` that identifies where it was created, so that the system can uniformly query and filter orders regardless of their origin.

#### Acceptance Criteria

1. WHEN a new order is created from the webshop, THE Order_Pipeline SHALL set `source_id` to `"webshop"`
2. WHEN a new order is created from an event booking form, THE Order_Pipeline SHALL set `source_id` to the event's UUID (the `event_id` from the Events table)
3. THE Order_Pipeline SHALL require `source_id` as a non-empty field on every order — no order may exist without a source
4. THE existing `source` field (currently `"presmeet"`) SHALL be migrated to use the event's UUID as `source_id`
5. THE system SHALL support querying all orders for a given source via the `event-member-index` GSI (PK: `source_id`)

### Requirement 2: Replace event-club-index with event-member-index

**User Story:** As a developer, I want orders indexed by `source_id + member_id` instead of `event_id + club_id`, so that any member can look up their own order for any event without requiring a club assignment.

#### Acceptance Criteria

1. THE system SHALL create a new GSI `event-member-index` on the Orders table with partition key `source_id` (String) and sort key `member_id` (String)
2. ALL handlers that currently use `event-club-index` SHALL be migrated to use `event-member-index`
3. THE `event-club-index` GSI SHALL be deleted after all handlers are updated and verified
4. WHEN looking up a member's order for an event, THE Order_Pipeline SHALL query `event-member-index` with `source_id = <event_id>` AND `member_id = <member_id>`
5. WHEN listing all orders for an event, THE Order_Pipeline SHALL query `event-member-index` with `source_id = <event_id>` (PK only)
6. THE Order record SHALL include `member_id` as a required attribute, set from the authenticated member's ID at order creation time
7. THE `club_id` field SHALL remain as an optional attribute on orders (not in the index) — it is still stored for events that need club context but is no longer used for lookups

### Requirement 3: External Member Registration

**User Story:** As an external club member (non-H-DCN), I want to register on the portal and gain access to a specific event's booking form, so that I can participate in events organized by H-DCN without being a full H-DCN member.

#### Acceptance Criteria

1. WHEN an external user registers on the portal, THE system SHALL create a Members record with `member_type = "event_participant"` and `status = "active"`, and add the user to the `event_participant` Cognito group
2. THE Members record for an external participant SHALL contain at minimum: `member_id`, `email`, `name`, `member_type`, `club_id` (their home club), and `allowed_events` (list of event_id UUIDs they may access)
3. WHEN an admin grants an external member access to an event, THE system SHALL add the event's UUID to the member's `allowed_events` array
4. THE `event_participant` member_type SHALL NOT grant access to H-DCN member features (member administration, full member directory, etc.)
5. THE `event_participant` member_type SHALL grant access to: self-service profile maintenance and the booking form for events listed in their `allowed_events`
6. WHEN an external member has `allowed_events: []` (empty), THEY SHALL only have access to self-service profile maintenance
7. THE system SHALL NOT create a new Cognito group per event — access control is data-driven via the `allowed_events` field

### Requirement 4: Event-Scoped Access Control

**User Story:** As a system operator, I want access to event booking forms controlled by a data-driven check rather than hardcoded Cognito groups, so that new events can be created without infrastructure changes.

#### Acceptance Criteria

1. THE auth layer SHALL support event-scoped access via a new check: `has_event_access(member_id, event_id)` which returns True if the member's `allowed_events` contains the given `event_id`
2. FOR all members (H-DCN and external), THE system SHALL grant event access ONLY via the `allowed_events` field — no Cognito group checks
3. THE event booking handlers SHALL check event access AFTER basic auth validation: first `extract_user_credentials()`, then `has_event_access(member_id, event_id)`
4. WHEN an admin creates a new event, THE system SHALL NOT require any new Cognito groups — the event is accessible to members whose `allowed_events` includes that event_id
5. IF a member attempts to access an event not in their `allowed_events`, THE system SHALL return a 403 response indicating event access is required
6. THE migration SHALL remove the `Regio_Pressmeet` Cognito group from all users and delete the group from the Cognito pool — event access is fully controlled by `allowed_events`
7. THE `has_presmeet_access()` and `club_identity.py` functions SHALL be removed — no backward-compatible wrappers

### Requirement 5: Unified Order Handlers

**User Story:** As a developer, I want one set of order handlers that serves both webshop and event orders, so that there's no duplication of order pipeline logic.

#### Acceptance Criteria

1. THE unified handlers SHALL accept `source_id` as a required parameter — either `"webshop"` or an event UUID
2. THE `get_order` handler SHALL replace both `get_presmeet_booking` and webshop order retrieval — querying orders by `source_id + member_id` via the GSI
3. THE `submit_order` handler SHALL replace `submit_presmeet_booking` — applying event constraints only when source is an event UUID, skipping constraints for webshop
4. THE `create_payment` handler SHALL replace `create_presmeet_payment` and webshop payment — creating a Mollie payment for any order's outstanding balance
5. THE `lock_orders` handler SHALL replace `lock_presmeet_orders` — locking submitted orders for any source
6. THE event_status_scheduler SHALL continue to work unchanged — it already queries events by status and transitions them based on dates
7. ALL unified handlers SHALL use `member_id` (resolved from the authenticated user) for order ownership verification
8. THE `club_id` SHALL remain as stored data on the order for display/reporting purposes but SHALL NOT be used for access control or order lookup
9. THE existing validation framework (`presmeet_validation.py`, `event_constraints.py`) SHALL be preserved and renamed to `event_validation.py` and `event_constraints.py` — no logic changes required, only the module name
10. THE Event record SHALL support an `order_scope` field with values `"member"` (default) or `"club"` — this determines how order uniqueness is enforced
11. WHEN `order_scope = "member"` (default, including webshop), THE handler SHALL allow one order per member per source — lookup via GSI `source_id + member_id`
12. WHEN `order_scope = "club"`, THE handler SHALL allow one order per club per event — the order's `member_id` is the primary delegate, and uniqueness is enforced on `club_id` at write time
13. WHEN `order_scope = "club"` and a member requests their booking, THE handler SHALL resolve the member's `club_id`, query all event orders (PK-only on GSI), and filter by `club_id` to find the club's order
14. WHEN `order_scope = "club"`, THE handler SHALL verify that the requesting member is a registered delegate (primary or secondary) on the order before granting access
15. WHEN `order_scope = "club"` and no order exists for the club, THE handler SHALL create a new order with the requesting member as primary delegate
16. WHEN `source_id = "webshop"`, THE handler SHALL verify the user has `hdcnLeden` group access (standard member)
17. WHEN `source_id` is an event UUID, THE handler SHALL verify the user has event access via `has_event_access(member_id, event_id)` and the event status is `open` for order creation

### Requirement 6: Preserve Booking Form Logic

**User Story:** As a Club_Delegate, I want the person-centric booking wizard to continue working exactly as before, so that my workflow is uninterrupted by the backend generalization.

#### Acceptance Criteria

1. THE Booking_Form SHALL continue to present a person-centric wizard where the delegate adds persons and configures products per person
2. THE Booking_Form SHALL load available products from the event's `product_ids` list (querying the Producten table) instead of filtering by `source='presmeet_config'`
3. THE Booking_Form SHALL derive per-person product limits from each product's `purchase_rules.max_per_club` — when `order_scope = "club"` this is literally per-club, when `order_scope = "member"` this is per-member (same field, different semantic context based on scope)
4. THE Booking_Form SHALL transform person-centric form state into order items with `product_id`, `variant_id`, and `item_fields_data` on save — same as current behavior
5. THE Booking_Form SHALL handle optimistic locking (version conflicts) identically to the current implementation
6. THE Booking_Form SHALL continue to support draft saving without validation, and full validation on submit
7. THE Booking_Form SHALL work with the new generalized API endpoints (accepting `event_id` as parameter) while preserving all UX behavior
8. THE existing report types (attendees, party, tshirts, pickups, dropoffs, financial, overview) SHALL continue to work for events that have matching product configurations

### Requirement 7: Event Product Configuration

**User Story:** As a Booking_Manager (admin), I want to configure which products are available for each event by maintaining the event's `product_ids` list, so that different events can offer different product sets without code changes.

#### Acceptance Criteria

1. THE Event record SHALL contain a `product_ids` array listing the UUIDs of products available for that event
2. THE Booking_Form SHALL fetch only the products referenced in the event's `product_ids` when loading the booking interface
3. THE products SHALL continue to live in the existing Producten table with the existing schema (`order_item_fields`, `purchase_rules`, `variant_schema`)
4. THE products MAY be shared across events (same product_id in multiple events' `product_ids`) or event-specific
5. WHEN an admin creates a new event, THE admin SHALL select which existing products to link or create new products specifically for that event
6. THE system SHALL NOT require products to have a `source` field for event filtering — the event's `product_ids` list is the single source of truth for what's available

### Requirement 8: Self-Service for External Members

**User Story:** As an external club member, I want to maintain my profile (name, email, phone, club) via self-service, so that I can keep my information current without contacting an admin.

#### Acceptance Criteria

1. THE self-service module SHALL be accessible to members with `member_type = "event_participant"`
2. THE self-service module SHALL allow editing: name, phone, and other profile fields
3. THE self-service module SHALL display the member's club assignment (read-only after initial assignment)
4. THE self-service module SHALL display which events the member has access to (derived from `allowed_events`)
5. THE self-service module SHALL NOT show H-DCN-specific features (membership management, member directory, regional grouping)

### Requirement 9: Multi-Language Support (i18n)

**User Story:** As an event participant from any European country, I want the event booking system to be fully translated in all supported languages, so that I can use the system in my preferred language.

#### Acceptance Criteria

1. ALL new frontend components (event booking, landing page, self-registration, admin event management) SHALL use `useTranslation()` with translation keys — no hardcoded user-facing strings
2. THE system SHALL create a new `eventBooking` i18n namespace (replacing the current `presmeet` namespace) containing all event-booking-related strings
3. THE `eventBooking` namespace SHALL be translated into all 8 supported languages: nl, en, de, fr, es, it, da, sv
4. THE event landing page content (hero text, sections, tagline) SHALL NOT use the i18n system — this content is admin-configured per event and stored in the Event record's `landing_page` object
5. THE event landing page UI chrome (buttons, labels, navigation, error messages) SHALL use the i18n system
6. THE translation keys SHALL be generic (e.g., `eventBooking.booking.submit`, `eventBooking.form.addPerson`) rather than event-type-specific (no `presmeet.booking.submit`)
7. THE existing `presmeet` namespace files SHALL be migrated to the new `eventBooking` namespace — keys renamed from presmeet-specific to generic
8. BACKEND error messages returned by event handlers SHALL use generic English messages — the frontend translates them to the user's language via error code mapping

### Requirement 10: Migration (Clean Slate)

**User Story:** As a developer, I want a clean deployment of the generic event system that replaces the current presmeet-specific implementation, so that we start fresh without legacy baggage.

#### Acceptance Criteria

1. THE migration SHALL delete all existing orders from the Orders table — this is all test data with no production value
2. THE migration SHALL create the new `event-member-index` GSI on the Orders table (PK: `source_id`, SK: `member_id`)
3. THE migration SHALL delete the old `event-club-index` GSI from the Orders table
4. THE migration SHALL add `member_type = "hdcn_member"` to all existing Members records
5. THE migration SHALL add `allowed_events = []` to all existing Members records
6. FOR existing Regio_Pressmeet users: THE migration SHALL add the active presmeet event_id to their `allowed_events`, then remove `Regio_Pressmeet` from their Cognito groups
7. THE migration SHALL delete the `Regio_Pressmeet` Cognito group from the user pool after all users have been migrated
8. THE frontend SHALL be updated to use new generic endpoints with `event_id` parameter
9. THE old presmeet-specific handlers SHALL be removed from the SAM template in the same deployment
10. No order data migration or backfill is required — the table starts clean

### Requirement 11: Event Landing Page (Optional)

**User Story:** As an event organizer, I want to optionally enable a public landing page for my event with event info, logos, and a registration button, so that I can share a link that lets new participants self-register and gain immediate access to the booking form.

#### Acceptance Criteria

1. THE Event record SHALL support an optional `landing_page` configuration object — when absent or `enabled: false`, no public page is generated for that event
2. THE `landing_page` object SHALL support: `enabled` (boolean), `slug` (URL-friendly string for vanity URL), `hero_image_url`, `tagline`, `sections` (array of content blocks), `registration_label` (CTA button text), and `logos` (array of name + logo_url pairs)
3. THE `sections` array SHALL support content blocks of type `text` (title + markdown/HTML content) and `logos` (title + array of logo items)
4. WHEN `landing_page.enabled` is true, THE system SHALL serve a public route at `/events/{slug}/info` that renders the landing page without requiring authentication
5. THE landing page SHALL display: hero section (event name, dates, location, hero image, tagline), content sections in order, logos section, and a registration CTA button
6. WHEN a visitor clicks the registration CTA and is NOT logged in, THE system SHALL present a sign-up/login choice — new users go through Cognito sign-up with the `event_id` passed as `clientMetadata`
7. WHEN a visitor clicks the registration CTA and IS already logged in, THE system SHALL check if the member has event access — if not, add the event_id to their `allowed_events` and redirect to the booking form
8. WHEN a new user completes Cognito sign-up via the event landing page, THE `cognito_post_confirmation` trigger SHALL: create a Members record with `member_type = "event_participant"`, `allowed_events = [<event_id>]`, `status = "active"`, and add the user to the `event_participant` Cognito group
9. THE `cognito_post_confirmation` trigger SHALL detect event context via `event['request']['clientMetadata']['event_id']` — if absent, the existing signup flow (no auto-access) applies
10. WHEN the event's registration period is closed (event status is not `open`), THE landing page SHALL hide the registration CTA button and display a message indicating registration is closed
11. THE landing page SHALL include appropriate Open Graph meta tags (title, description, image) for social media link previews, served via Lambda@Edge or dynamic meta injection
12. IF a logged-in H-DCN member visits the landing page for an event they already have access to, THE CTA SHALL read "Go to Booking" and link directly to the booking form without re-registration

### Requirement 12: Admin Event Access Management

**User Story:** As an admin, I want to grant and revoke event access for members (both H-DCN and external), so that I control who can book for each event.

#### Acceptance Criteria

1. THE admin dashboard SHALL provide an interface to add/remove event access for any member
2. WHEN an admin grants event access, THE system SHALL add the event_id to the member's `allowed_events` array
3. WHEN an admin revokes event access, THE system SHALL remove the event_id from the member's `allowed_events` array
4. THE admin SHALL be able to bulk-grant event access (e.g., "grant access to all members with Regio_Pressmeet")
5. THE admin SHALL be able to view which members have access to a specific event
6. IF an admin revokes access for a member who has an existing order for that event, THE order SHALL remain in the system but the member can no longer edit it — only an admin can modify it from that point
