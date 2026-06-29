# Requirements Document

## Introduction

The event booking module is built with "club" as a hardcoded concept. This makes the system unusable for other scenarios (families, schools, teams, associations). The registry concept is generic — a row in an S3-based table with an ID, label, and optional logo — but the implementation names everything `club_*`. This refactor replaces all club-specific naming with generic `registry_row_*` names, making the system usable for any type of registration unit.

Root cause analysis:

1. **Naming bias** — First use case was "clubs". Everything was named `club_*`. Propagated to every subsequent feature.
2. **No abstraction** — UI shows hardcoded "club" texts instead of `row_label` from registry config.
3. **Copy-paste proliferation** — 8 handlers, 5 components, 2 admin views, 6 test files, 15+ translation keys.
4. **No schema-first** — Field registry defines `registry_config` correctly, but code ignored it.

Full spec input document: #[[file:.kiro/specs/generic-registry-row-refactor/generic-registry-row-refactor.md]]

## Glossary

- **Registry_Row**: A generic row in an S3-based registration table, consisting of an ID, label, and optional logo. Replaces the concept "club".
- **Registry_Config**: The configuration on an Event record (`registry_config` field) containing: `s3_path` (path to the S3 registry file), `row_label` (the type of registration unit, e.g. "club", "team", "school" — set by admin when configuring the event), `claim_mode`, `max_delegates_per_row`, `allow_logo_upload`.
- **Order**: A DynamoDB record in the Orders table representing a booking for an event.
- **Member**: A DynamoDB record in the Members table representing a participant in an event.
- **Event_Booking_System**: The entirety of backend handlers, frontend components, and configuration that handles event bookings.
- **RegistrySelector**: Frontend component allowing a user to select a registry row during onboarding.
- **PurchaseRules**: Configuration that defines limits per registry row (max/min per row, number of distinct rows).
- **Preparation_PDF**: A system-generated PDF document with preparation details per event.
- **Delegate_Invitation**: An email sent to invite a delegate for a registry row.
- **Shared_Layer**: The shared Lambda Layer (`shared.auth_utils`, `shared.event_access`) used by multiple handlers.
- **Migration_Script**: A Python script that transforms existing DynamoDB records from old to new field names.

## Requirements

### Requirement 1: Order contains registry row data

**User Story:** As an event organizer, I want orders to contain generic registry row data, so that the booking system is usable for any type of registration unit (clubs, teams, schools).

#### Acceptance Criteria

1. WHEN an order is created for a closed event with registry_config, THE Event_Booking_System SHALL resolve `registry_row_label` and `registry_row_logo_url` from the S3 registry file (using the member's `registry_row_id`) and store them on the Order record together with `registry_row_id`
2. THE Order SHALL contain the fields `registry_row_id`, `registry_row_label`, and `registry_row_logo_url` instead of `club_id`
3. IF a Member record does not contain `registry_row_id` at the time of order creation for a closed event, THEN THE Event_Booking_System SHALL reject the order creation with an error message indicating the user must first select a registry row
4. THE Event_Booking_System SHALL derive order scope from the presence of `registry_config` on the Event record: if `registry_config` exists → one order per registry row (row-scoped); if absent → one order per member (member-scoped). The `order_scope` field SHALL be removed from Event records by the migration.
5. WHEN a payment record is created, THE Event_Booking_System SHALL use `registry_row_id` instead of `club_id`
6. IF `registry_row_logo_url` is absent on the Member record, THEN THE Order SHALL store `registry_row_logo_url` as `null` (the field is not omitted)

---

### Requirement 2: Member record uses generic field names

**User Story:** As a developer, I want member records to use generic field names, so that the data layer is not coupled to the concept "club".

#### Acceptance Criteria

1. WHEN a new member record is created via event_onboard, THE Event_Booking_System SHALL store the field `registry_row_id` with the value of the selected `row_id` from the S3 registry file (via `registry_config.s3_path` on the Event record); label and logo are NOT stored on the Member (they are resolved from S3 at order creation time)
2. WHEN an existing member re-onboards for a different event, THE Event_Booking_System SHALL update the field `registry_row_id` on the Member record with the newly selected row_id from the new event's registry
3. THE Shared_Layer SHALL provide the function `get_registry_row_id(email)` as replacement for `get_club_id(email)`, with the same signature: `str | None` return value (None if member not found or field absent)
4. IF when retrieving registry row data from S3 the `row_id` is not found in the registry file, THEN THE Event_Booking_System SHALL abort onboarding with an error message indicating the row does not exist in the registry
5. WHEN a delegate is assigned, THE Event_Booking_System SHALL verify that the `registry_row_id` on the target Member record matches the `registry_row_id` on the Order record, and on mismatch reject the assignment with an error message indicating the target member does not belong to the same registry row

---

### Requirement 3: Frontend Order interface and components

**User Story:** As a frontend developer, I want the Order interface and related components to use generic registry row fields, so that the UI is not hardcoded to "club".

#### Acceptance Criteria

1. THE Order interface SHALL define the fields `registry_row_id` (optional, type `string`), `registry_row_label` (optional, type `string`), and `registry_row_logo_url` (optional, type `string`) and remove the field `club_id`
2. WHEN the TypeScript project is compiled with `npx tsc --noEmit` after the interface change, THE Event_Booking_System SHALL produce 0 type errors
3. WHEN `order.registry_row_logo_url` contains a non-empty string, THE RegistryRowLogo component SHALL display the logo as a 48×48 pixel rounded image with that URL as `src`
4. IF `order.registry_row_logo_url` is absent, null, or an empty string, THEN THE RegistryRowLogo component SHALL display a camera icon placeholder in the same 48×48 dimensions
5. WHEN a BookingSummaryPdf is generated, THE Event_Booking_System SHALL use `registry_row_label` in the PDF filename in the format `booking-{registry_row_label}-{event_name}.pdf` (sanitized to lowercase alphanumeric with hyphens) and as identification label in the PDF header, with fallback value "unknown" when `registry_row_label` is absent
6. WHEN the admin order list is displayed, THE Event_Booking_System SHALL show `registry_row_label` in the club column of the order table, with fallback to `registry_row_id` when `registry_row_label` is absent

---

### Requirement 4: OnboardingFlow is replaced by RegistrySelector

**User Story:** As a user, I want to onboard via a generic registry selection component, so that the onboarding process is not specific to clubs.

#### Acceptance Criteria

1. THE Event_Booking_System SHALL not contain any frontend code that calls `/presmeet/clubs`, `/presmeet/clubs/assign`, or `/presmeet/logo`
2. IF a user does not have a `registry_row_id` on their Member record, THEN THE EventBookingPage SHALL display the RegistrySelector instead of the former OnboardingFlow
3. WHEN a logo is uploaded, THE Event_Booking_System SHALL resize it client-side using the existing `resizeImage` utility and upload via the endpoint `/events/{event_id}/registry-logo` with `event_id` and `row_id` as parameters
4. THE Event_Booking_System SHALL not contain any imports or references to the OnboardingFlow component in production code

---

### Requirement 5: PurchaseRules and CountingRule generic

**User Story:** As an event organizer, I want to set limits per order and per event (regardless of organization type), so that constraints are not tied to the concept "club".

#### Acceptance Criteria

1. THE PurchaseRules type (defined on products) SHALL rename `max_per_club` to `max_per_order` (optional, integer 1–9999) — this is the maximum quantity of this product that a single order can contain
2. THE PurchaseRules type (defined on products) SHALL rename `min_per_club` to `min_per_order` (optional, integer 1–9999, less than or equal to `max_per_order`) — this is the minimum quantity of this product that a single order must contain
3. THE PurchaseRules type SHALL retain `max_per_event` unchanged — this is the overall cap across all orders for this product
4. THE CountingRule type SHALL contain the value `count_distinct_rows` instead of `count_distinct_clubs` — used in event-level Constraints to count how many distinct registry rows have ordered a product
5. THE Event_Booking_System SHALL use the renamed field names in both backend constraint validation and frontend `useEffectiveLimits` hook
6. THE Migration_Script SHALL also rename `max_per_club` to `max_per_order` and `min_per_club` to `min_per_order` in the `purchase_rules` field of affected products in the Producten table (few rows expected)
7. WHILE existing event constraints in DynamoDB contain `count_distinct_clubs` as counting_rule, THE Event_Booking_System SHALL accept this value as valid and treat it functionally identical to `count_distinct_rows`
8. IF a product configuration contains both `max_per_club` and `max_per_order`, THEN THE Event_Booking_System SHALL treat `max_per_order` as authoritative and ignore `max_per_club`

---

### Requirement 6: Preparation PDF generic

**User Story:** As an event organizer, I want the preparation PDF to use generic labels, so that the document is appropriate for any type of registration unit.

#### Acceptance Criteria

1. THE Preparation_PDF SHALL use the CSS class `row-name` instead of `club-name`, and `row-logo` instead of `club-logo` in the generated HTML output
2. THE Preparation_PDF SHALL use the Python sort function `_sort_key_row_label` instead of `_sort_key_club_name`, with the same case-insensitive logic
3. WHEN a PDF page header is generated, THE Preparation_PDF SHALL display the label in the format "{row_label}: {name}" (e.g. "Club: Riders Amsterdam", "Team: Alpha", "School: Lyceum X") where `row_label` is retrieved from `event.registry_config.row_label`
4. IF `registry_config.row_label` is absent or empty, THEN THE Preparation_PDF SHALL use the fallback value "row" as prefix in the header
5. THE Preparation_PDF SHALL not contain hardcoded "club" text in the generated HTML output, unless `registry_config.row_label` has the value "club"
6. THE Preparation_PDF SHALL rename internal Python variable names that refer to the registration row from `club_name` to `row_label` and from `club_id` (as local variable) to `row_id`, without changing DynamoDB field names in orders

---

### Requirement 7: Delegate invitation email generic

**User Story:** As a delegate, I want to receive an invitation email with the correct name for my registration unit, so that the communication is accurate regardless of the organization type.

#### Acceptance Criteria

1. THE Delegate_Invitation SHALL use the template variables `ROW_LABEL` (the type of registration unit, e.g. "club", "team", "school") and `ROW_NAME` (the name of the registration unit, e.g. "H-DCN Nederland", "Ajax") instead of `CLUB_NAME`
2. WHEN the handler builds the email template context, THE Delegate_Invitation SHALL resolve the values for `ROW_LABEL` and `ROW_NAME` from the order record (`registry_row_label`) or, as fallback, from the event `registry_claims` for the relevant `registry_row_id`
3. THE Delegate_Invitation SHALL not contain hardcoded "club" text in any of the 8 locale templates (nl, en, de, fr, es, it, da, sv) nor in the fallback HTML, unless the resolved `ROW_LABEL` value equals "club"
4. IF resolving `ROW_LABEL` or `ROW_NAME` yields no value, THEN THE Delegate_Invitation SHALL fall back to `ROW_LABEL` = "group" and `ROW_NAME` = the `registry_row_id` value

---

### Requirement 8: Translations generic

**User Story:** As a user, I want the interface to show the correct naming based on the event type, so that I see "club", "team", or "school" depending on the context.

#### Acceptance Criteria

1. THE Event_Booking_System SHALL replace all hardcoded "club" texts in translation keys within the `eventBooking` namespace with `{{rowLabel}}` interpolation, in both `frontend/src/locales/{lang}/eventBooking.json` and `frontend/public/locales/{lang}/eventBooking.json`
2. WHEN a component displays registry-related text, THE Event_Booking_System SHALL pass the value of `row_label` from the event's `registry_config` object as interpolation parameter to the translation function, with "Club" as fallback when `registry_config.row_label` is undefined or empty
3. THE Event_Booking_System SHALL not contain hardcoded "club" in translation values of the `eventBooking` namespace translation files, with the exception of the `row_label_default` key that contains "Club" as fallback value
4. THE Event_Booking_System SHALL have the modified translation keys available in all 8 languages (nl, en, de, fr, es, it, da, sv), where each language uses the same set of `{{rowLabel}}` interpolation variables and the fallback value is translated per language

---

### Requirement 9: Layout — EventInfoHeader compact and responsive

**User Story:** As a user, I want event information displayed compactly, so that I have more space for the booking flow.

#### Acceptance Criteria

1. THE Event_Booking_System SHALL display location, dates, countdown, and capacity per product in a single container block (no separate full-width sections)
2. WHILE the screen is wider than 768px, THE Event_Booking_System SHALL display the info block horizontally next to the page title in the same row
3. WHILE the screen is 768px or narrower, THE Event_Booking_System SHALL display the info block below the page title as a stacked block at full width
4. THE Event_Booking_System SHALL display product name and remaining count in the form "[remaining] / [total]" for each product with a finite capacity limit within the info block
5. IF no product has a finite capacity limit, THEN THE Event_Booking_System SHALL not display the capacity section within the info block
6. WHILE capacity data is loading, THE Event_Booking_System SHALL display a loading indicator in place of the capacity information within the info block

---

### Requirement 10: event_participant Cognito group

**User Story:** As a developer, I want the console warning "Filtering out invalid role: event_participant" resolved, so that there are no confusing messages in the browser.

#### Acceptance Criteria

1. WHEN the `event_participant` group is created by `event_onboard`, THE Event_Booking_System SHALL add this group to the valid groups whitelist in the `filterValidRoles` function in `authHeaders.ts`
2. IF the `event_participant` group is not created by the system, THEN THE Event_Booking_System SHALL clean up the group from Cognito
3. THE Event_Booking_System SHALL not display "Filtering out invalid role" warnings in the browser console for legitimate Cognito groups created by the system

---

### Requirement 11: Data migration

**User Story:** As an administrator, I want to migrate existing data to the new field names, so that all records consistently use the generic naming.

#### Acceptance Criteria

1. THE Migration_Script SHALL provide a script `scripts/migrate_club_to_registry_row.py` that for each record in Orders and Payments replaces the field `club_id` with `registry_row_id` and adds the fields `registry_row_label` and `registry_row_logo_url` (resolved from S3); for Members, it replaces `club_id` with `registry_row_id` only (no label/logo needed on Member records)
2. THE Migration_Script SHALL support the flags `--dry-run` (default: no write operations), `--profile` (default: `nonprofit-deploy`), and `--stage` (test|prod, required)
3. WHEN the script processes a record with `club_id`, THE Migration_Script SHALL resolve `registry_row_label` and `registry_row_logo_url` by looking up the `club_id` in the S3 registry file
4. IF a `club_id` is not found in the S3 registry file, THEN THE Migration_Script SHALL skip the record, log a warning with the record ID and the not-found `club_id`, and count the record in a "skipped" counter in the final summary
5. THE Migration_Script SHALL be idempotent: records that already contain `registry_row_id` are skipped without modification, and repeated execution produces the same end result
6. THE Migration_Script SHALL handle DynamoDB scan pagination so that all records are processed regardless of table size, and log a summary after completion with counts of scanned, converted, skipped, and errored records per table
7. IF the `--validate` flag is provided, THEN THE Migration_Script SHALL verify that each record in the three tables contains a `registry_row_id` and no longer has `club_id`, and report the result as pass (all records migrated) or fail (with list of record IDs that still contain `club_id`)
8. IF validation via `--validate` is successful, THEN THE Migration_Script SHALL with the `--remove-old-fields` flag remove the old `club_id` fields from all records in the three tables

## References

- Field Registry: `frontend/src/config/eventFields/fields/bookingFields.ts`
- Event Booking Spec: `.kiro/specs/Events/closed-community-booking/`
- Current issues: `.kiro/specs/todo/booking-form-fixes.md`
- ADR event lifecycle: `docs/decisions/event-lifecycle-status.md`
