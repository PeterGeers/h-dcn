# Implementation Plan: Closed Community Booking

## Overview

This plan implements a generic, registry-driven booking system for invitation-only events. The implementation builds incrementally: core backend handlers first (password verification, registry, onboard), then booking form logic (orders, persons, products), then admin features (claims management, dashboard, PDF), and finally frontend components wired together. Each step builds on the previous one, with no orphaned code.

The backend uses Python 3.11 (AWS SAM Lambda handlers), the frontend uses TypeScript (React + Chakra UI). Existing infrastructure (DynamoDB, Cognito, S3, Mollie) is reused.

**Deployment Strategy:** All work is done on `feature/closed-community-booking`. At each checkpoint, push to the feature branch and deploy to the test environment so the feature is available at `testportal.h-dcn.nl`.

```
feature/closed-community-booking → Push at each checkpoint → Deploy to h-dcn-test → Verify on testportal.h-dcn.nl
```

**Deploy commands (at each checkpoint):**

```bash
git push -u origin feature/closed-community-booking
gh workflow run deploy-backend.yml --ref feature/closed-community-booking -f stage=test
gh workflow run deploy-frontend.yml --ref feature/closed-community-booking -f stage=test
```

## Tasks

- [x] 1. Backend foundation: verify-password and registry endpoints
  - [x] 1.1 Implement `verify_event_password` handler
    - Create `backend/handler/verify_event_password/app.py`
    - Truncate password to 72 bytes, bcrypt verification against Event record
    - Generate short-lived session token (JWT, 15min TTL) on success
    - Return generic error for wrong password or non-existent event (no info leak)
    - Add SAM template resource with API Gateway rate limiting (10 req/IP/min)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 16.1, 16.6_

  - [x] 1.2 Write property tests for password verification
    - **Property 1: Password Verification Correctness**
    - Test: truncation to 72 bytes produces identical results for passwords differing only after byte 72
    - Test: failed verification (wrong password vs non-existent event) produces identical response structure
    - File: `backend/tests/unit/test_registry_properties.py`
    - **Validates: Requirements 1.1, 1.2**

  - [x] 1.3 Implement `get_event_registry` handler
    - Create `backend/handler/get_event_registry/app.py`
    - Validate session token OR authenticated user with event access
    - Fetch S3 invitee_registry.json, merge with DynamoDB registry_claims
    - Mask claimant emails (first 2 chars + \*\*\* + @domain)
    - Sort rows alphabetically case-insensitive by label
    - Return merged list with row_label and claim_mode from registry_config
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 16.2_

  - [x] 1.4 Write property tests for registry merge and email masking
    - **Property 2: Registry Merge and Sort**
    - **Property 3: Email Masking**
    - Test: merge output contains exactly one entry per S3 row, correctly marks available/taken, sorted alphabetically
    - Test: mask function produces `XX***@domain` pattern for any valid email
    - File: `backend/tests/unit/test_registry_properties.py`
    - **Validates: Requirements 2.1, 2.3, 16.2**

- [x] 2. Backend: event-onboard endpoint (atomic registration)
  - [x] 2.1 Implement `event_onboard` handler
    - Create `backend/handler/event_onboard/app.py`
    - Validate session token (JWT, event_id match, not expired)
    - email_restricted mode: verify user email against row's allowed_emails (case-insensitive)
    - Check user doesn't already hold a claim for this event
    - Atomic claim via DynamoDB conditional write on registry_claims map
    - Create Cognito user (AdminCreateUser + AdminSetUserPassword, CONFIRMED state) or link existing
    - Create/update Member record (member_type=event_id, club_id=row_id, allowed_events)
    - Add user to event_participant Cognito group
    - Check and auto-link pending delegate invitations
    - Implement rollback: delete Cognito user if Member creation fails, release claim if Cognito fails
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 4.1, 4.2, 4.3, 4.4, 4.5, 4.7, 16.3, 16.4, 16.6_

  - [x] 2.2 Write property tests for onboard logic
    - **Property 4: Case-Insensitive Email Matching**
    - **Property 5: Atomic Row Claim with Data Integrity**
    - **Property 6: One Claim Per User Per Event**
    - **Property 7: Member Record Creation on Onboard (New User)**
    - **Property 8: Existing Member Event Access Append**
    - File: `backend/tests/unit/test_event_onboard_properties.py`
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 4.2, 4.4**

  - [x] 2.3 Write unit tests for onboard rollback scenarios
    - Test: Cognito creation fails → claim is released
    - Test: Member creation fails → Cognito user deleted + claim released
    - Test: existing user → event access appended without modifying other fields
    - File: `backend/tests/unit/test_event_onboard.py`
    - _Requirements: 4.5, 4.7_

- [x] 3. Checkpoint — Verify core backend endpoints
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Backend: order creation, update, and submission
  - [x] 4.1 Modify `create_order` handler for event order deduplication
    - Add club_id validation (required for event orders, return error if null/empty)
    - Query for existing non-cancelled order for same club_id + event_id
    - Return existing order with HTTP 200 if found, create new with HTTP 201 if not
    - _Requirements: 18.1, 18.2, 18.3, 18.4_

  - [x] 4.2 Write property test for order deduplication
    - **Property 25: Order Deduplication**
    - Test: repeated create_order calls for same (club_id, event_id) always yield exactly one non-cancelled order
    - File: `backend/tests/unit/test_order_deduplication_properties.py`
    - **Validates: Requirements 18.1, 18.2, 18.4**

  - [x] 4.3 Modify `update_order_items` handler for persons structure
    - Accept persons array structure with per-person product lines
    - Sync item_fields_data.name when person name is updated
    - Remove all product lines when a person is removed
    - Implement optimistic locking (version field check + increment)
    - _Requirements: 6.4, 6.5, 5.5, 8.3_

  - [x] 4.4 Modify `submit_order` handler for event validation
    - Validate every person has non-empty name (≥1 non-whitespace char)
    - Validate item_fields_data.name populated on every line
    - Validate all required order_item_fields are filled
    - Validate per-order quantity limits (max_per_club) not exceeded
    - Validate per-event capacity (max_per_event) via current Sold_Count from DynamoDB
    - Validate all variant_id references exist in product's variant list
    - Transition status draft → submitted on success
    - Return grouped per-person error messages on failure
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 9.9_

  - [x] 4.5 Write property tests for booking validation
    - **Property 13: Person Name Validation**
    - **Property 16: Effective Limit Calculation**
    - **Property 17: Draft Save Accepts Invalid Data**
    - **Property 18: Submit Validation — Required Fields**
    - **Property 19: Submit Validation — Quantity Limits**
    - **Property 20: Submit Validation — Variant Validity**
    - File: `backend/tests/unit/test_booking_validation_properties.py`
    - **Validates: Requirements 6.2, 7.2, 7.3, 7.4, 8.2, 9.1, 9.2, 9.3, 9.4, 9.5, 9.6**

- [x] 5. Backend: sold counts and order lifecycle
  - [x] 5.1 Implement `get_product_sold_counts` handler
    - Create `backend/handler/get_product_sold_counts/app.py`
    - Auth check (event_participant or hdcnLeden or admin)
    - Scan Orders for event_id (status != cancelled), aggregate product quantities
    - Return { product_id: sold_count } map
    - Add SAM template resource
    - _Requirements: 7.3, 7.5, 7.8_

  - [x] 5.2 Implement order lock/unlock in existing admin handlers
    - Lock: validate order is in submitted status, transition to locked
    - Unlock: validate order is in submitted or locked, transition to draft
    - Batch lock/unlock: apply same rules per order in a list
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

  - [x] 5.3 Implement delegate management endpoints
    - Invite secondary delegate: validate email, enforce max_delegates_per_row limit, reject self-invitation
    - Store pending_secondary_email (lowercased) on order
    - Revoke invitation / remove linked secondary delegate (draft status only)
    - _Requirements: 5.1, 5.2, 5.3, 5.7_

  - [x] 5.4 Write property tests for delegate management
    - **Property 9: Delegate Invitation Limit Enforcement**
    - **Property 10: Pending Delegate Email Normalization**
    - **Property 11: Optimistic Locking**
    - File: `backend/tests/unit/test_event_onboard_properties.py` (or new file)
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6**

- [x] 6. Checkpoint — Verify order and delegate backend logic
  - Ensure all tests pass, ask the user if questions arise.
    Waiting for changeset to be created..
    Error: Failed to create changeset for the stack: h-dcn-test, ex: Waiter ChangeSetCreateComplete failed: Waiter encountered a terminal failure state: For expression "Status" we matched expected path: "FAILED" Status: FAILED. Reason: Transform AWS::Serverless-2016-10-31 failed with: Invalid Serverless Application Specification document. Number of errors found: 1. Resource with id [VerifyEventPasswordFunctionVerifyEventPassword] is invalid. property ThrottlingRateLimit not defined for resource of type Api
    Error: Process completed with exit code 1.

- [x] 7. Backend: admin features
  - [x] 7.1 Implement `admin_event_claims` handler
    - Create `backend/handler/admin_event_claims/app.py`
    - GET: list all claims with labels, paginate at 50 per page
    - DELETE: release claim (remove from registry_claims, keep order)
    - POST: manually assign row (verify not already claimed, create draft order)
    - Support reassign primary delegate, remove secondary delegate, cancel pending invitation
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6_

  - [x] 7.2 Implement `admin_event_dashboard` handler
    - Create `backend/handler/admin_event_dashboard/app.py`
    - Return: total/claimed/unclaimed rows, registration percentage
    - Order status breakdown (draft/submitted/locked counts)
    - Payment status breakdown (unpaid/partial/paid + revenue collected vs expected)
    - Per-product capacity usage (sold_count vs max_per_event)
    - _Requirements: 14.1, 14.2, 14.3, 14.4_

  - [x] 7.3 Implement `generate_preparation_pdf` handler
    - Create `backend/handler/generate_preparation_pdf/app.py`
    - Two modes: by_order (one page per club) and by_guest (one page per person)
    - Include only submitted/locked orders
    - Sort alphabetically (by club name or last word of guest name)
    - Product filter support
    - Footer: event name, ISO date, page X of Y
    - Return empty-state message if no qualifying orders
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7, 15.8_

  - [x] 7.4 Implement admin CSV export endpoint
    - Export all orders for event: order items, delegate info, person names, statuses, totals
    - _Requirements: 14.6_

  - [x] 7.5 Write property test for preparation PDF sorting
    - **Property 23: Preparation PDF Sorting**
    - Test: by-order mode sorted case-insensitive by club name; by-guest mode sorted by last word of name
    - File: `backend/tests/unit/test_booking_validation_properties.py` (or new file)
    - **Validates: Requirements 15.5**

- [x] 8. Prerequisites: Event Field Registry and ADR
  - [x] 8.1 Create Event Field Registry
    - Create `frontend/src/config/eventFields/` following the memberFields pattern
    - Create `frontend/src/config/eventFields/types.ts` with FieldDefinition interface
    - Create `frontend/src/config/eventFields/fields/` with field groups:
      - `coreFields.ts`: event_id, name, event_type, status, start_date, end_date, slug
      - `bookingFields.ts`: event_password, landing_page_enabled, registry_config, registry_claims
      - `index.ts`: re-exports all field groups
    - Create `frontend/src/config/eventFields/index.ts` (central registry export)
    - Create `frontend/src/config/eventFields/permissions.ts` (permission helpers)
    - This is the single source of truth for Event table fields per schema-driven steering
    - _BookingForm.md §12: "Event Field Registry required"_

  - [x] 8.2 Write ADR for closed community booking architecture
    - Create `docs/decisions/closed-community-booking.md`
    - Document: registry-driven approach (S3 static + DynamoDB claims), atomic claims via conditional writes, scaling boundary (~1500-2000 rows per event item), password gate + session token pattern, decision to extend EventRegisterPage rather than create new pages
    - Reference the generic-event-booking ADR as predecessor
    - _BookingForm.md §12: "ADR required"_

- [x] 9. Frontend: landing page flow components
  - [x] 9.1 Implement `PasswordGate` component
    - Create `frontend/src/modules/presmeet/components/PasswordGate.tsx`
    - Password input with submit, shake animation on error
    - Rate limit handling (disable button + countdown)
    - Skip entirely if landing_page_enabled is false or no event_password
    - All strings via useTranslation('eventBooking')
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 17.1_

  - [x] 9.2 Implement `RegistrySelector` component
    - Create `frontend/src/modules/presmeet/components/RegistrySelector.tsx`
    - Create `frontend/src/modules/presmeet/components/RowCard.tsx`
    - Display all rows sorted alphabetically with logo/placeholder, availability status
    - Show masked claimant email for taken rows
    - Use Row_Label from registry_config for UI labels
    - email_restricted mode: enable matching rows, disable non-matching with tooltip
    - Error handling: retry action on S3 failure
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 17.1_

  - [x] 9.3 Implement `ClaimAction` component and onboard API call
    - Create `frontend/src/modules/presmeet/components/ClaimAction.tsx`
    - Account creation form (name, email, password for new users)
    - Call event-onboard endpoint, handle 409/403 responses
    - Redirect to booking on success
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 4.1, 4.6_

  - [x] 9.4 Implement `AccessDeniedScreen` component
    - Create `frontend/src/modules/presmeet/components/AccessDeniedScreen.tsx`
    - Show message explaining registration is required
    - Link to /events/:slug/info if landing_page_enabled and slug exist
    - No link + contact organizer message if no landing page
    - All strings via useTranslation('eventBooking')
    - _Requirements: 19.1, 19.2, 19.3_

  - [x] 9.5 Wire `EventRegisterPage` step machine
    - Add state machine: PasswordGate → Auth → RegistrySelector → ClaimAction → Success redirect
    - Integrate session token passing between steps
    - Handle returning users (event_id in allowed_events → skip landing flow)
    - _Requirements: 1.3, 4.6, 17.1_

- [x] 10. Checkpoint — Verify landing page flow
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Frontend: booking form with dual limits
  - [x] 11.1 Implement person management in BookingForm
    - Add/remove persons up to highest max_per_club across products (min 1)
    - Pre-fill first person with delegate's name, prevent removal
    - Require trimmed name 1-100 chars, reject whitespace-only
    - Sync item_fields_data.name on person name changes
    - Remove all product lines when a person is removed
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [x] 11.2 Write frontend property tests for person management
    - **Property 12: Maximum Persons Derived from Products**
    - **Property 14: Person Name Sync to Product Lines**
    - **Property 15: Person Removal Cascades to Product Lines**
    - File: `frontend/src/modules/presmeet/__tests__/personManagement.property.test.ts`
    - **Validates: Requirements 6.1, 6.4, 6.5**

  - [x] 11.3 Implement effective limit display and enforcement
    - Fetch sold counts from backend on form open and product changes
    - Calculate effective limit: min(max_per_club - order_qty, max_per_event - sold_count)
    - Display "X of Y remaining" per product
    - Disable product selection when effective limit ≤ 0
    - Handle absent max_per_event (per-order limit only)
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.8_

  - [x] 11.4 Write frontend property test for effective limits
    - **Property 16: Effective Limit Calculation**
    - File: `frontend/src/modules/presmeet/__tests__/effectiveLimits.property.test.ts`
    - **Validates: Requirements 7.2, 7.3, 7.4, 7.5**

  - [x] 11.5 Implement variant and dynamic field selection
    - Render variant selection dropdowns when variant_schema defined
    - Render dynamic fields via ProductConfigurator when order_item_fields defined
    - Validate variant_id maps to valid variant before adding product line
    - _Requirements: 7.6, 7.7_

  - [x] 11.6 Implement auto-save (draft state)
    - Debounce 3 seconds after last modification
    - Accept invalid data without showing validation errors
    - Optimistic locking via version field
    - Visual save-status indicator (saving/saved/save failed)
    - Retry on failure: on next edit or after 30 seconds
    - Retain unsaved changes locally on failure
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 12. Frontend: submission, payment, and read-only views
  - [x] 12.1 Implement order submission with validation display
    - Submit button calls backend submit endpoint
    - Display validation errors grouped per person (scroll to first error)
    - Transition to confirmation page on success with payment option
    - Handle capacity exceeded (show current remaining)
    - _Requirements: 9.7, 9.8, 9.9_

  - [x] 12.2 Implement payment integration (Mollie redirect)
    - Initiate payment via existing pay_order handler
    - Redirect to Mollie checkout page
    - Display error if Mollie returns an error, preserve order status
    - Show payment_status updates (paid/partial/unpaid)
    - _Requirements: 11.1, 11.2, 11.5_

  - [x] 12.3 Implement read-only view for submitted/locked orders
    - Disable all form fields, hide add/remove person actions, hide save/submit
    - Render order data in non-editable view for delegates
    - _Requirements: 10.2_

  - [x] 12.4 Implement delegate management UI
    - Invite secondary delegate by email
    - Reject self-invitation
    - Show pending invitation state
    - Revoke/remove secondary delegate (draft only)
    - Handle version conflicts with reload notification
    - _Requirements: 5.1, 5.2, 5.3, 5.5, 5.6, 5.7_

  - [x] 12.5 Write frontend property tests for optimistic locking and access control
    - **Property 11: Optimistic Locking**
    - **Property 24: Event Access Control**
    - File: `frontend/src/modules/presmeet/__tests__/optimisticLocking.property.test.ts` and `accessControl.property.test.ts`
    - **Validates: Requirements 5.5, 5.6, 16.5, 16.7**

- [x] 13. Frontend: PDF generation
  - [x] 13.1 Implement booking confirmation PDF (delegate)
    - Generate PDF at any order status (draft, submitted, locked)
    - Include: event name, row label, delegates, persons with products/fields/variants, status, amounts, payment status
    - Run validation checks and indicate "valid at this moment" or list issues
    - Append disclaimer with locale-formatted date-time
    - Handle draft with no persons (metadata only + indication)
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

  - [x] 13.2 Write frontend property tests for PDF output
    - **Property 22: PDF Output Completeness**
    - File: `frontend/src/modules/presmeet/__tests__/pdfGeneration.property.test.ts`
    - **Validates: Requirements 12.2, 12.4**

- [x] 14. Checkpoint — Verify booking form and PDF
  - Ensure all tests pass, ask the user if questions arise.

- [x] 15. Frontend: admin features
  - [x] 15.1 Implement admin claims management UI
    - Table with row label, claim status, delegate info, claimed_at, pagination (50/page)
    - Release claim with confirmation dialog
    - Manual assign by email search (creates draft order)
    - Reassign primary delegate, remove secondary, cancel pending invitation
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6_

  - [x] 15.2 Implement admin registration progress dashboard
    - Summary cards: total/claimed/unclaimed rows, registration percentage
    - Order status breakdown (draft/submitted/locked counts with percentages)
    - Payment status breakdown (unpaid/partial/paid + revenue vs expected in EUR 2dp)
    - Per-product capacity progress bars (sold_count vs max_per_event)
    - Filterable order list (by status, payment_status, row/club)
    - CSV export button
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6_

  - [x] 15.3 Implement admin order lock/unlock UI
    - Lock/unlock individual orders
    - Batch lock/unlock from order list
    - Error display when attempting to lock non-submitted order
    - _Requirements: 10.1, 10.3, 10.4, 10.5_

  - [x] 15.4 Implement admin payment recording and preparation PDF UI
    - Manual payment recording (admin_record_payment endpoint)
    - Preparation PDF download: by_order and by_guest modes
    - Product filter for PDF
    - Empty-state message when no qualifying orders
    - _Requirements: 11.3, 11.4, 15.1, 15.4, 15.7, 15.8_

- [x] 16. Internationalization: translation keys for all 8 languages
  - [x] 16.1 Add eventBooking namespace translation files
    - Create `frontend/src/locales/{lang}/eventBooking.json` for all 8 languages (nl, en, de, fr, es, it, da, sv)
    - Create `frontend/public/locales/{lang}/eventBooking.json` for all 8 languages
    - Cover all Landing_Page_Flow strings (password gate, registry selector, claim action)
    - Cover all Booking_Form strings (persons, products, limits, save status, submission, payment)
    - Cover AccessDeniedScreen strings
    - Use {{rowLabel}} interpolation parameter for dynamic labels
    - Implement Dutch (nl) fallback for missing keys
    - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5_

- [x] 17. Email notifications for delegate invitations
  - [x] 17.1 Create SES email template for delegate invitation
    - Create `backend/email-templates/templates/delegate-invitation.html`
    - Include: event name, inviter name, link to event landing page (or direct registration link)
    - Support all 8 languages via template variables
    - _BookingForm.md §3: "System sends an invitation email with a link"_

  - [x] 17.2 Implement `send_delegate_invitation` handler
    - Create `backend/handler/send_delegate_invitation/app.py`
    - Triggered when primary delegate invites secondary (from task 5.3)
    - Send SES email to pending_secondary_email with event landing page link
    - Include inviter name, event name, row/club name in email body
    - Support "resend" action from delegate management UI
    - Add SAM template resource with SES send permission
    - _BookingForm.md §3: delegate invite flow steps 3-4_

  - [x] 17.3 Add "Resend invitation" action to delegate management UI
    - Add resend button next to pending invitations in DelegateManager component
    - Call send_delegate_invitation endpoint on click
    - Show toast confirmation on success
    - _BookingForm.md §3: "The UI shows pending invitations with a resend option"_

- [x] 18. Integration: access control and security wiring
  - [x] 18.1 Implement event access verification on all booking endpoints
    - Verify event_id in allowed_events + delegate ownership on order read/update/submit/payment
    - Return HTTP 403 without revealing order existence on access failure
    - _Requirements: 16.5, 16.7_

  - [x] 18.2 Add SAM template resources for all new handlers
    - Define all new Lambda functions in template.yaml
    - Configure API Gateway routes, IAM permissions, environment variables
    - Configure rate limiting on verify-password endpoint
    - _Requirements: 1.4, 16.6_

- [x] 19. Final checkpoint — End-to-end verification
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- Backend uses Python 3.11 with TypedDict + validate functions (no Pydantic)
- Frontend uses TypeScript with Formik + Yup for form validation
- All user-facing strings must use `useTranslation('eventBooking')` — never hardcoded text
- Translation files go in BOTH `src/locales/` AND `public/locales/`
- DynamoDB tables are managed outside CloudFormation — never add them as resources without DeletionPolicy: Retain

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.3"] },
    { "id": 1, "tasks": ["1.2", "1.4", "2.1"] },
    { "id": 2, "tasks": ["2.2", "2.3", "4.1"] },
    { "id": 3, "tasks": ["4.2", "4.3", "5.1", "5.3"] },
    { "id": 4, "tasks": ["4.4", "5.2", "5.4"] },
    { "id": 5, "tasks": ["4.5", "7.1", "7.2", "7.4"] },
    { "id": 6, "tasks": ["7.3", "7.5", "8.1", "8.2"] },
    { "id": 7, "tasks": ["9.1", "9.4"] },
    { "id": 8, "tasks": ["9.2", "9.3", "9.5"] },
    { "id": 9, "tasks": ["11.1", "11.3", "11.5"] },
    { "id": 10, "tasks": ["11.2", "11.4", "11.6"] },
    { "id": 11, "tasks": ["12.1", "12.2", "12.3", "12.4"] },
    { "id": 12, "tasks": ["12.5", "13.1"] },
    { "id": 13, "tasks": ["13.2", "15.1", "15.2"] },
    { "id": 14, "tasks": ["15.3", "15.4", "16.1"] },
    { "id": 15, "tasks": ["17.1", "17.2"] },
    { "id": 16, "tasks": ["17.3", "18.1", "18.2"] }
  ]
}
```
