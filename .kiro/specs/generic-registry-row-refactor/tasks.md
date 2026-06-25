# Implementation Plan: Generic Registry Row Refactor

## Overview

Replace all `club_*` naming with generic `registry_row_*` names across backend handlers, frontend components, translations, and data. Migration-first strategy: data is fully migrated before code deploy. Backend in Python 3.11 (AWS SAM), frontend in React 18 + TypeScript (Chakra UI v2).

## Tasks

- [x] 1. Migration script and data layer
  - [x] 1.1 Create migration script `scripts/migrate_club_to_registry_row.py`
    - Implement CLI with `--stage` (required), `--dry-run`, `--profile` (default: nonprofit-deploy), `--validate`, `--remove-old-fields` flags
    - Implement `migrate_table()` for Orders (club_id → registry_row_id + resolve label/logo from S3), Members (club_id → registry_row_id only), Payments (club_id → registry_row_id)
    - Implement Producten migration: `purchase_rules.max_per_club` → `max_per_order`, `min_per_club` → `min_per_order`
    - Implement Events migration: remove `order_scope` field, rename `counting_rule: 'count_distinct_clubs'` → `'count_distinct_rows'`
    - Handle DynamoDB scan pagination (LastEvaluatedKey)
    - Idempotency: skip records that already have `registry_row_id`
    - Skip records where `club_id` not found in S3 registry (log warning, increment "skipped")
    - Log summary per table: scanned, converted, skipped, errored
    - Implement `--validate` mode: verify all records have `registry_row_id` and no `club_id` remains
    - Implement `--remove-old-fields` mode: remove old `club_id` fields after successful validation
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8_

  - [x] 1.2 Write property tests for migration (Hypothesis)
    - **Property 9: Migration idempotency** — running migration twice produces the same result as once; records with `registry_row_id` are never modified on subsequent runs
    - **Validates: Requirements 11.1, 11.3, 11.5**
    - **Property 10: Migration validation correctness** — `--validate` reports pass iff every record has `registry_row_id` and no record has `club_id`; otherwise reports fail with non-compliant record IDs
    - **Validates: Requirements 11.7**
    - Test file: `backend/tests/unit/test_registry_row_refactor_properties.py`
    - Use `@settings(max_examples=100)`

  - [x] 1.3 Write unit tests for migration script
    - Test dry-run mode produces no writes
    - Test idempotency (re-run on already-migrated records)
    - Test skip logic for missing S3 entries
    - Test pagination handling
    - Test validate and remove-old-fields modes
    - Test file: `backend/tests/unit/test_migration.py`
    - _Requirements: 11.1, 11.2, 11.4, 11.5, 11.6, 11.7, 11.8_

- [x] 2. Backend shared layer changes
  - [x] 2.1 Rename `get_club_id` to `get_registry_row_id` in shared layer
    - Update `backend/layers/auth-layer/python/shared/event_access.py`
    - Function signature: `get_registry_row_id(user_email: str) -> str | None`
    - Returns `registry_row_id` from Member record, or None if not found/absent
    - _Requirements: 2.3_

  - [x] 2.2 Write property test for `get_registry_row_id`
    - **Property 3: get_registry_row_id resolves correctly** — for any member with email and `registry_row_id`, calling the function returns that value; if field absent, returns None
    - **Validates: Requirements 2.3**
    - Test file: `backend/tests/unit/test_registry_row_refactor_properties.py`

- [x] 3. Backend handler: `get_order`
  - [x] 3.1 Implement `_resolve_order_scope` and order creation with registry row data
    - Add `_resolve_order_scope(event_record)`: returns `'registry_row'` if `registry_config` present, else `'member'`
    - Add `_resolve_registry_row_data(event_record, registry_row_id)`: resolve label + logo_url from S3 registry file
    - Update `_create_draft_order()` to store `registry_row_id`, `registry_row_label`, `registry_row_logo_url` for row-scoped orders
    - Store `registry_row_logo_url` as `null` (not omitted) when logo absent
    - Return HTTP 403 with `error_code: REGISTRY_ROW_REQUIRED` when member has no `registry_row_id` for row-scoped event
    - Remove references to `club_id` in order creation logic
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.6_

  - [x] 3.2 Write property tests for get_order scope and order creation
    - **Property 1: Order creation resolves registry row data from S3** — for any member with `registry_row_id`, creating a row-scoped order resolves label/logo from S3 and stores all three fields
    - **Validates: Requirements 1.1**
    - **Property 2: Scope derivation from registry_config** — returns `'registry_row'` if `registry_config` present and non-empty, else `'member'`
    - **Validates: Requirements 1.4**
    - Test file: `backend/tests/unit/test_registry_row_refactor_properties.py`

  - [x] 3.3 Write unit tests for get_order handler
    - Test row-scoped order creation with S3 resolution
    - Test member-scoped order (no registry_config)
    - Test missing registry_row_id returns 403
    - Test null logo_url stored correctly
    - Test file: `backend/tests/unit/test_get_order.py`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.6_

- [x] 4. Checkpoint — Ensure migration and core backend tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Backend handlers: submit_order, event_onboard, manage_delegates, pay_order
  - [x] 5.1 Update `submit_order/app.py` for registry row naming
    - `_calculate_sold_counts()`: filter by `order.get('registry_row_id')`
    - `_validate_event_persons()`: read `max_per_order` from `purchase_rules`
    - Constraint validation: read `counting_rule` value `count_distinct_rows` (accept `count_distinct_clubs` as equivalent per Req 5.7)
    - _Requirements: 5.5, 5.7, 5.8_

  - [x] 5.2 Update `event_onboard/app.py` for registry row naming
    - Store `registry_row_id` on Member record (only the ID, no label/logo)
    - Resolve row from S3 registry via `registry_config.s3_path`
    - Return HTTP 400 with `error_code: ROW_NOT_FOUND` if row_id not in registry
    - _Requirements: 2.1, 2.2, 2.4_

  - [x] 5.3 Update `manage_delegates/app.py` for registry row validation
    - Verify target member's `registry_row_id` matches order's `registry_row_id`
    - Return HTTP 403 with `error_code: DELEGATE_ROW_MISMATCH` on mismatch
    - _Requirements: 2.5_

  - [x] 5.4 Update `pay_order/app.py` for registry row naming
    - Payment record uses `registry_row_id` instead of `club_id`
    - _Requirements: 1.5_

  - [x] 5.5 Write property test for delegate validation
    - **Property 4: Delegate assignment validates registry_row_id match** — accepted iff order.registry_row_id == member.registry_row_id; rejected otherwise
    - **Validates: Requirements 2.5**
    - Test file: `backend/tests/unit/test_registry_row_refactor_properties.py`

  - [x] 5.6 Write property test for purchase rules resolution
    - **Property 6: Purchase rules resolution** — effective `max_per_order` read from `purchase_rules.max_per_order` (absent = unlimited); `counting_rule` only `'count_distinct_rows'` after migration
    - **Validates: Requirements 5.5**
    - Test file: `backend/tests/unit/test_registry_row_refactor_properties.py`

  - [x] 5.7 Write unit tests for submit_order, event_onboard, manage_delegates, pay_order
    - Test sold count filtering by registry_row_id
    - Test max_per_order validation
    - Test onboard stores only registry_row_id on member
    - Test ROW_NOT_FOUND error
    - Test delegate mismatch rejection
    - Test payment record uses registry_row_id
    - Test files: `backend/tests/unit/test_submit_order.py`, `backend/tests/unit/test_event_onboard.py`, `backend/tests/unit/test_manage_delegates.py`
    - _Requirements: 1.5, 2.1, 2.2, 2.4, 2.5, 5.5, 5.7_

- [x] 6. Backend handlers: admin_event_claims, upload_registry_logo
  - [x] 6.1 Update `admin_event_claims/app.py`
    - `_find_order_for_row()`: filter by `registry_row_id`
    - `_create_draft_order_for_claim()`: store `registry_row_id`, `registry_row_label`, `registry_row_logo_url` (resolved from S3)
    - _Requirements: 1.1, 1.2_

  - [x] 6.2 Rename `upload_club_logo` handler to `upload_registry_logo`
    - Rename directory `backend/handler/upload_club_logo/` → `backend/handler/upload_registry_logo/`
    - Update function name and endpoint in SAM template: `/events/{event_id}/registry-logo`
    - Accept `event_id` and `row_id` as parameters
    - _Requirements: 4.1, 4.3_

- [x] 7. Backend: PDF generation and delegate emails
  - [x] 7.1 Update `generate_preparation_pdf/app.py`
    - Rename `_sort_key_club_name` → `_sort_key_row_label`
    - CSS classes: `club-name` → `row-name`, `club-logo` → `row-logo`
    - Header format: `"{row_label}: {name}"` from `event.registry_config.row_label` (fallback: "row")
    - Rename local variables: `club_name` → `row_label`, `club_id` → `row_id`
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

  - [x] 7.2 Update `send_delegate_invitation/app.py`
    - Template context: `ROW_LABEL` (from `event.registry_config.row_label`) + `ROW_NAME` (from `order.registry_row_label`)
    - Fallback: `ROW_LABEL` = "group", `ROW_NAME` = `registry_row_id`
    - Remove hardcoded "club" references in locale templates
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [x] 7.3 Write property tests for PDF and delegate emails
    - **Property 5: PDF filename sanitization** — filename matches `booking-{sanitized_label}-{sanitized_name}.pdf`; absent label → "unknown"
    - **Validates: Requirements 3.5**
    - **Property 7: PDF header labeling format** — displays `"{row_label}: {name}"` with 50×50 logo; absent row_label → fallback "row"; absent logo → no image
    - **Validates: Requirements 6.2, 6.3, 6.4**
    - **Property 8: Delegate email template context resolution** — `ROW_LABEL` and `ROW_NAME` resolved from order; fallback to "group" and `registry_row_id`
    - **Validates: Requirements 7.1, 7.2, 7.4**
    - Test file: `backend/tests/unit/test_registry_row_refactor_properties.py`

  - [x] 7.4 Write unit tests for PDF generation and delegate emails
    - Test HTML output contains `row-name`, `row-logo` classes (not `club-*`)
    - Test header format with various row_label values
    - Test fallback to "row" when row_label absent
    - Test delegate email template context resolution
    - Test files: `backend/tests/unit/test_generate_preparation_pdf.py`, `backend/tests/unit/test_send_delegate_invitation.py`
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 7.1, 7.2, 7.3, 7.4_

- [x] 8. Checkpoint — Ensure all backend tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Frontend: TypeScript interfaces, types, and Field Registries
  - [x] 9.1 Update Order, PurchaseRules, CountingRule, PaymentRecord interfaces
    - In `eventBooking.types.ts`: replace `club_id` with `registry_row_id`, `registry_row_label`, `registry_row_logo_url` (all optional strings)
    - Rename `max_per_club` → `max_per_order`, `min_per_club` → `min_per_order` in PurchaseRules
    - Update CountingRule: `count_distinct_clubs` → `count_distinct_rows`
    - Update PaymentRecord: `club_id` → `registry_row_id`
    - Run `npx tsc --noEmit` to verify zero type errors
    - _Requirements: 3.1, 3.2, 5.1, 5.2, 5.3, 5.4_

  - [x] 9.2 Update `useEffectiveLimits` hook
    - Read `max_per_order` directly from `product.purchase_rules`
    - Remove any references to `max_per_club`
    - _Requirements: 5.5_

  - [x] 9.3 Update Field Registries (source of truth)
    - `frontend/src/config/productFields/fields.ts`: update `purchase_rules` sub-field definitions — rename `max_per_club` → `max_per_order`, `min_per_club` → `min_per_order` in labels, helpText, and any validation config
    - `frontend/src/config/eventFields/fields/bookingFields.ts`: verify `registry_config` and `registry_claims` field definitions are current; add `count_distinct_rows` as valid `counting_rule` value if documented there
    - _Requirements: 5.1, 5.2, 5.4_

- [x] 10. Frontend: Components
  - [x] 10.1 Create `RegistryRowLogo` component (replacing `ClubLogoUploader`)
    - Props: `logoUrl`, `label`, `isAdmin`, `onUpload`
    - Display 48×48 rounded image when `logoUrl` is non-empty
    - Display camera icon placeholder when logo absent/null/empty
    - Logo upload via `/events/{event_id}/registry-logo` with `resizeImage` utility
    - _Requirements: 3.3, 3.4, 4.3_

  - [x] 10.2 Update `EventBookingPage` to use registry row fields
    - Use `order.registry_row_id` instead of `club_id`
    - Show `RegistrySelector` when user has no `registry_row_id` (replacing OnboardingFlow)
    - Remove imports/references to OnboardingFlow
    - _Requirements: 4.2, 4.4_

  - [x] 10.3 Update `BookingSummaryPdf` component
    - Filename: `booking-{sanitized_registry_row_label}-{sanitized_event_name}.pdf` (fallback "unknown")
    - Header uses `registry_row_label`, logo from `registry_row_logo_url`
    - _Requirements: 3.5_

  - [x] 10.4 Update `EventInfoHeader` — compact responsive layout
    - Display location, dates, countdown, capacity in single container
    - Horizontal layout > 768px, stacked ≤ 768px
    - Capacity display: `[remaining] / [total]` per product with finite limit
    - Hide capacity section if no product has a finite limit
    - Show loading indicator while capacity data loads
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

  - [x] 10.5 Update `AdminOrderLockUnlock` component
    - Replace `OrderSummary.club_id` → `registry_row_id`, `club_name` → `registry_row_label`
    - Display column uses `registry_row_label` (fallback to `registry_row_id`)
    - _Requirements: 3.6_

  - [x] 10.6 Add `event_participant` to valid roles whitelist in `authHeaders.ts`
    - Add to `filterValidRoles()` whitelist
    - _Requirements: 10.1, 10.3_

  - [x] 10.7 Write frontend property tests (fast-check)
    - **Property 5: PDF filename sanitization** — filename matches pattern; absent label → "unknown"; sanitization: lowercase, non-alphanum → hyphens, collapse, trim
    - **Validates: Requirements 3.5**
    - **Property 6: Purchase rules resolution** — `max_per_order` read correctly; absent = unlimited
    - **Validates: Requirements 5.5**
    - Test file: `frontend/src/modules/eventBooking/__tests__/registryRow.property.test.ts`
    - Use `fc.assert(property, { numRuns: 100 })`

  - [x] 10.8 Write unit tests for RegistryRowLogo and useEffectiveLimits
    - Test logo displays as 48×48 rounded image when URL provided
    - Test camera placeholder when URL absent/null/empty
    - Test useEffectiveLimits reads max_per_order correctly
    - Test files: `frontend/src/modules/eventBooking/__tests__/RegistryRowLogo.test.tsx`, `frontend/src/modules/eventBooking/__tests__/useEffectiveLimits.test.ts`
    - _Requirements: 3.3, 3.4, 5.5_

- [x] 11. Frontend: Translations
  - [x] 11.1 Update translation files in all 8 languages
    - Replace hardcoded "club" texts with `{{rowLabel}}` interpolation in `eventBooking` namespace
    - Add error translation keys: `errors.REGISTRY_ROW_REQUIRED`, `errors.ROW_NOT_FOUND`, `errors.DELEGATE_ROW_MISMATCH`, `errors.INVALID_ORDER_SCOPE`
    - Update both `frontend/src/locales/{lang}/eventBooking.json` and `frontend/public/locales/{lang}/eventBooking.json`
    - All 8 languages: nl, en, de, fr, es, it, da, sv
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [x] 11.2 Update delegate invitation email templates for all 8 locales
    - Replace `CLUB_NAME` with `ROW_LABEL` + `ROW_NAME` in template HTML
    - Remove hardcoded "club" text (unless resolved value is "club")
    - _Requirements: 7.3_

- [x] 12. Frontend: Remove old code and verify no club references
  - [x] 12.1 Remove OnboardingFlow component and old endpoints
    - Delete OnboardingFlow component files
    - Remove all calls to `/presmeet/clubs`, `/presmeet/clubs/assign`, `/presmeet/logo`
    - Verify no imports of OnboardingFlow in production code
    - Run `grep` for removed symbols across codebase
    - _Requirements: 4.1, 4.4_

  - [x] 12.2 Run smoke tests, lint, and type check
    - `npx tsc --noEmit` — zero type errors
    - `npx eslint` on all modified frontend files — zero errors
    - `grep` for `/presmeet/clubs` in frontend — zero matches
    - `grep` for `OnboardingFlow` imports in production code — zero matches
    - `grep` for hardcoded "club" in translation files (except `row_label_default`) — zero matches
    - _Requirements: 3.2, 4.1, 4.4, 8.3_

- [x] 13. SAM template and wiring
  - [x] 13.1 Update SAM template for handler rename and new endpoint
    - Rename `UploadClubLogo` function resource to `UploadRegistryLogo`
    - Update endpoint path from `/presmeet/logo` to `/events/{event_id}/registry-logo`
    - Ensure all environment variables for new handler are set
    - _Requirements: 4.1, 4.3_

- [x] 14. Documentation — ADR for scope derivation change
  - [x] 14.1 Create ADR `docs/decisions/registry-row-scope-derivation.md`
    - Document the removal of `order_scope` field from Events
    - Document the new derivation logic: scope determined by presence of `registry_config`
    - Document the rename from `club_*` to `registry_row_*` as architectural decision
    - Include rationale: generic naming enables multi-tenant use (clubs, teams, schools)

- [-] 15. Final checkpoint — Ensure all tests pass, commit, push and deploy
  - Ensure all tests pass, ask the user if questions arise.
  - Commit on current feature branch using `mcp_git_git_commit`
  - Push and trigger both deploy workflows:
    ```bash
    git push
    gh workflow run deploy-backend.yml --ref {branch} -f stage=test
    gh workflow run deploy-frontend.yml --ref {branch} -f stage=test
    ```

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- Backend tests: use `pytest tests/unit/test_<file>.py` (never full suite)
- Frontend tests: use `npx react-scripts test --watchAll=false --testPathPattern="<pattern>"`
- Frontend type check: `npx tsc --noEmit`
- Migration runs BEFORE code deploy — no backward compatibility code needed in handlers
- Translations must be updated in BOTH `src/locales/` AND `public/locales/`

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "9.1"] },
    { "id": 1, "tasks": ["1.2", "1.3", "2.1", "9.2", "9.3"] },
    { "id": 2, "tasks": ["2.2", "3.1", "5.1", "5.2", "5.3", "5.4", "10.6"] },
    { "id": 3, "tasks": ["3.2", "3.3", "5.5", "5.6", "5.7", "6.1", "6.2"] },
    {
      "id": 4,
      "tasks": ["7.1", "7.2", "10.1", "10.2", "10.3", "10.4", "10.5"]
    },
    { "id": 5, "tasks": ["7.3", "7.4", "10.7", "10.8", "11.1", "11.2"] },
    { "id": 6, "tasks": ["12.1", "13.1", "14.1"] },
    { "id": 7, "tasks": ["12.2"] },
    { "id": 8, "tasks": ["15"] }
  ]
}
```
