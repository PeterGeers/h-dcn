# Implementation Plan: PresMeet v2

## Overview

Migrate PresMeet from v1 (custom Cognito `club_*` groups, custom admin checks) to v2 (Member-record club identity, role-based admin via `Products_CRUD` + `Regio_Pressmeet`, tenant-based multi-tenancy). The implementation preserves existing booking logic while replacing auth/identity integration points and adding onboarding and club management capabilities.

## Tasks

- [x] 1. Create shared `club_identity` module and update auth layer
  - [x] 1.1 Create `backend/layers/auth-layer/python/shared/club_identity.py`
    - Implement `get_club_id(user_email)` — query Members table for `status=presmeet` member, return `club_id`
    - Implement `is_presmeet_admin(user_roles)` — check `(Products_CRUD | Products_Read | Webshop_Management) AND (Regio_Pressmeet | Regio_All)`
    - Implement `is_presmeet_admin_write(user_roles)` — check `Products_CRUD AND (Regio_Pressmeet | Regio_All)`
    - Implement `has_presmeet_access(user_roles)` — check `Regio_Pressmeet | Regio_All`
    - _Requirements: 1.3, 1.4, 1.5, 2.1, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 11.4, 11.5_

  - [x] 1.2 Write property tests for access gating (Property 1)
    - **Property 1: PresMeet access gating**
    - Test `has_presmeet_access` returns True iff list contains `Regio_Pressmeet` or `Regio_All`
    - Use Hypothesis to generate arbitrary role lists
    - File: `backend/tests/unit/test_presmeet_v2_access.py`
    - **Validates: Requirements 1.3, 1.4, 3.5**

  - [x] 1.3 Write property tests for admin role check (Property 2)
    - **Property 2: PresMeet admin role check**
    - Test `is_presmeet_admin` returns True iff list contains management role AND region role
    - File: `backend/tests/unit/test_presmeet_v2_access.py`
    - **Validates: Requirements 1.5, 5.1, 5.2, 5.3, 5.6**

  - [x] 1.4 Write property tests for admin write vs read (Property 3)
    - **Property 3: PresMeet admin write vs read distinction**
    - Test `is_presmeet_admin_write` requires `Products_CRUD` specifically (not just `Products_Read`)
    - File: `backend/tests/unit/test_presmeet_v2_access.py`
    - **Validates: Requirements 5.4, 5.5**

  - [x] 1.5 Write property test for club identity resolution (Property 12)
    - **Property 12: Club identity resolution**
    - Test `get_club_id` returns correct club_id for presmeet members and None for others
    - Use moto to mock DynamoDB Members table
    - File: `backend/tests/unit/test_presmeet_v2_club_identity.py`
    - **Validates: Requirements 2.1, 11.4**

- [x] 2. Migrate existing presmeet handlers to v2 auth pattern
  - [x] 2.1 Migrate `get_presmeet_booking` handler
    - Replace `from shared.presmeet_validation import extract_club_id` with `from shared.club_identity import get_club_id, has_presmeet_access, is_presmeet_admin`
    - Add `has_presmeet_access(user_roles)` gate before business logic
    - Replace `extract_club_id(user_roles)` with `get_club_id(user_email)`
    - Replace `is_admin = 'webmaster' in user_roles` with `is_admin = is_presmeet_admin(user_roles)`
    - Add `tenant=presmeet` filter to DynamoDB scan alongside existing `source=presmeet`
    - _Requirements: 1.3, 1.4, 2.1, 6.4, 11.4, 11.5_

  - [x] 2.2 Migrate `save_presmeet_booking` handler
    - Same auth pattern change as 2.1
    - Ensure `tenant=presmeet` is set on all new/updated order records
    - _Requirements: 1.3, 2.1, 6.1, 6.2, 7.9, 11.4_

  - [x] 2.3 Migrate `submit_presmeet_booking` handler
    - Same auth pattern change as 2.1
    - _Requirements: 1.3, 2.1, 8.2, 11.4_

  - [x] 2.4 Migrate `validate_presmeet_cart` handler
    - Same auth pattern change as 2.1
    - _Requirements: 1.3, 2.1, 11.1, 11.4_

  - [x] 2.5 Migrate `get_presmeet_config` handler
    - Same auth pattern change as 2.1
    - Add `tenant=presmeet` filter when querying Producten table for product configs
    - _Requirements: 1.3, 4.3, 6.4, 11.4_

  - [x] 2.6 Migrate `create_presmeet_payment` handler
    - Same auth pattern change as 2.1
    - Ensure payment records include `tenant=presmeet`
    - _Requirements: 1.3, 2.1, 6.2, 11.4_

- [x] 3. Migrate admin handlers to v2 auth pattern
  - [x] 3.1 Migrate `lock_presmeet_orders` handler
    - Replace `'webmaster' in user_roles` with `is_presmeet_admin_write(user_roles)`
    - Add `tenant=presmeet` filter to order queries
    - _Requirements: 5.4, 8.5, 8.8, 11.5_

  - [x] 3.2 Migrate `unlock_presmeet_order` handler
    - Replace admin check with `is_presmeet_admin_write(user_roles)`
    - _Requirements: 5.4, 8.7, 11.5_

  - [x] 3.3 Migrate `manual_presmeet_payment` handler
    - Replace admin check with `is_presmeet_admin_write(user_roles)`
    - Ensure payment record includes `tenant=presmeet`
    - _Requirements: 5.4, 6.2, 11.5_

  - [x] 3.4 Migrate `generate_presmeet_report` handler
    - Replace admin check with `is_presmeet_admin(user_roles)`
    - Add `tenant=presmeet` filter alongside `source=presmeet` in DynamoDB scans
    - _Requirements: 5.2, 5.5, 9.1, 9.7, 11.5_

  - [x] 3.5 Migrate `get_presmeet_report` handler
    - Replace admin check with `is_presmeet_admin(user_roles)`
    - _Requirements: 5.2, 5.5, 9.3, 11.5_

- [x] 4. Checkpoint — Ensure all migrated handlers pass tests
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Create new onboarding handlers
  - [x] 5.1 Create `backend/handler/get_club_registry/app.py`
    - Implement GET `/presmeet/clubs` endpoint
    - Auth: `has_presmeet_access(user_roles)` gate
    - Read `presmeet/club_registry.json` from S3 reports bucket
    - Return club list as JSON
    - Handle missing registry (404) and S3 errors (500)
    - _Requirements: 2.2, 2.3, 10.1_

  - [x] 5.2 Create `backend/handler/assign_club/app.py`
    - Implement POST `/presmeet/clubs/assign` endpoint
    - Auth: `has_presmeet_access(user_roles)` gate; admin override via `is_presmeet_admin`
    - Accept `club_id` and optional `member_email` (admin only) in request body
    - Validate club exists in registry, check assignment uniqueness
    - Update Member record with `club_id`, update Club_Registry in S3
    - Support admin reassignment: clear previous member's `club_id`
    - Return 409 if club already assigned (non-admin), with contact info
    - _Requirements: 2.3, 2.4, 2.5, 2.6, 2.7_

  - [x] 5.3 Write property test for club assignment uniqueness (Property 13)
    - **Property 13: Club assignment uniqueness**
    - Test non-admin cannot assign already-assigned club; admin can reassign and clears previous
    - File: `backend/tests/unit/test_presmeet_v2_club_identity.py`
    - **Validates: Requirements 2.4, 2.7**

- [x] 6. Add SAM template resources for new handlers
  - [x] 6.1 Add `GetClubRegistryFunction` and `AssignClubFunction` to `backend/template.yaml`
    - Define Lambda functions following existing pattern (Python 3.11 runtime, auth layer, environment variables)
    - Add API Gateway events: GET `/presmeet/clubs` and POST `/presmeet/clubs/assign`
    - Include `REPORTS_BUCKET_NAME` and `MEMBERS_TABLE_NAME` environment variables
    - Add IAM policies for S3 read/write on reports bucket and DynamoDB access on Members table
    - _Requirements: 2.2, 2.3, 10.1_

- [x] 7. Create data migration script
  - [x] 7.1 Create `scripts/migrate_add_tenant_field.py`
    - Scan all records in Members, Producten, Orders, Carts, Payments that lack `tenant` field
    - Set `tenant=presmeet` for records with `source` containing "presmeet"; set `tenant=h-dcn` for all others
    - Use pagination to handle large tables
    - Include dry-run mode and progress logging
    - _Requirements: 6.3, 6.6_

  - [x] 7.2 Create initial `presmeet/club_registry.json` for S3
    - Create a seed file with the Club_Registry JSON structure (version, clubs array)
    - Include script to upload to S3 reports bucket
    - _Requirements: 2.2_

- [x] 8. Checkpoint — Ensure backend is complete and all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Frontend type updates and API service extension
  - [x] 9.1 Add `Regio_Pressmeet` to `HDCNGroup` TypeScript type
    - Update `frontend/src/types/user.ts` to include `"Regio_Pressmeet"` in the HDCNGroup union type
    - _Requirements: 11.6_

  - [x] 9.2 Add Club_Registry types to presmeet module
    - Add `ClubRegistryEntry`, `ClubRegistry`, `AssignClubResponse` interfaces to `frontend/src/modules/presmeet/types/presmeet.ts`
    - Extend `PresMeetBooking` interface with `tenant: "presmeet"` field
    - _Requirements: 2.2, 6.1_

  - [x] 9.3 Extend `presmeetService` with onboarding API methods
    - Add `getClubRegistry()` — GET `/presmeet/clubs`
    - Add `assignClub(clubId)` — POST `/presmeet/clubs/assign`
    - Add `reassignClub(clubId, memberEmail)` — POST `/presmeet/clubs/assign` with `member_email`
    - File: `frontend/src/modules/presmeet/services/presmeetApi.ts`
    - _Requirements: 2.3, 2.7_

- [x] 10. Frontend onboarding flow
  - [x] 10.1 Create `OnboardingFlow` component
    - Create `frontend/src/modules/presmeet/components/OnboardingFlow.tsx`
    - Fetch club registry via `presmeetService.getClubRegistry()`
    - Display selectable club list with logos and names
    - Handle club selection and call `presmeetService.assignClub()`
    - Show error state for already-assigned clubs (409) with contact info
    - Show success state and redirect to booking form on completion
    - _Requirements: 2.3, 2.5, 10.1_

  - [x] 10.2 Update `PresMeetPage` to integrate onboarding flow
    - Check if user has `club_id` assigned (via config/booking endpoint or new check)
    - If no `club_id`, show `OnboardingFlow` instead of booking form
    - After onboarding completes, reload booking state and show form
    - _Requirements: 10.1, 10.2_

  - [x] 10.3 Update Dashboard `FunctionGuard` for PresMeet card
    - Replace current PresMeet card gating with `requiredRoles={['Regio_Pressmeet', 'Regio_All']}`
    - Ensure card is hidden for users without `Regio_Pressmeet` or `Regio_All`
    - _Requirements: 1.3, 1.4, 3.5, 10.4_

- [x] 11. Frontend admin role update
  - [x] 11.1 Update `isPresMeetAdmin` function in `PresMeetPage.tsx`
    - Replace current check (`System_User_Management || Products_CRUD`) with v2 logic: `(Products_CRUD || Products_Read || Webshop_Management) AND (Regio_Pressmeet || Regio_All)`
    - Admin tab visibility should follow same logic
    - _Requirements: 5.1, 5.2, 5.3, 10.5_

  - [x] 11.2 Write unit tests for OnboardingFlow component
    - Test club list rendering, selection, error states (409), success redirect
    - File: `frontend/src/modules/presmeet/__tests__/OnboardingFlow.test.tsx`
    - _Requirements: 2.3, 2.5_

  - [x] 11.3 Write unit tests for updated admin role check
    - Test that only users with correct role+region combo see admin tab
    - File: `frontend/src/modules/presmeet/__tests__/PresMeetPage.test.tsx`
    - _Requirements: 5.1, 5.3_

- [x] 12. Checkpoint — Ensure all frontend tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 13. Property tests for tenant isolation and validation
  - [x] 13.1 Write property test for tenant field isolation (Property 4)
    - **Property 4: Tenant field isolation invariant**
    - Verify all PresMeet records contain both `tenant=presmeet` and `source` field
    - File: `backend/tests/unit/test_presmeet_v2_tenant.py`
    - **Validates: Requirements 6.1, 6.2, 6.4, 7.9, 11.7**

  - [x] 13.2 Write property test for tenant-based product filtering (Property 5)
    - **Property 5: Tenant-based product filtering**
    - Verify tenant filter correctly isolates products by tenant value
    - File: `backend/tests/unit/test_presmeet_v2_tenant.py`
    - **Validates: Requirements 4.3, 9.7**

  - [x] 13.3 Write property tests for schema validation (Properties 6 & 7)
    - **Property 6: Schema validation accepts valid attributes**
    - **Property 7: Schema validation rejects invalid attributes**
    - Use Hypothesis strategies to generate valid/invalid attribute objects
    - File: `backend/tests/unit/test_presmeet_validation.py`
    - **Validates: Requirements 11.1, 4.5**

  - [x] 13.4 Write property test for cart total calculation (Property 8)
    - **Property 8: Cart total calculation**
    - Verify total matches pricing formula for arbitrary item lists
    - File: `backend/tests/unit/test_presmeet_validation.py`
    - **Validates: Requirements 7.6**

  - [x] 13.5 Write property test for outstanding balance (Property 9)
    - **Property 9: Outstanding balance calculation**
    - Verify `max(0, total - sum(payments))` for arbitrary amounts
    - File: `backend/tests/unit/test_presmeet_validation.py`
    - **Validates: Requirements 7.6**

  - [x] 13.6 Write property test for order state machine (Property 10)
    - **Property 10: Order state machine transitions**
    - Verify exhaustive transition rules: draft→submitted, submitted→locked, etc.
    - File: `backend/tests/unit/test_presmeet_v2_order_lifecycle.py`
    - **Validates: Requirements 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 11.2**

  - [x] 13.7 Write property test for Lock ALL batch (Property 11)
    - **Property 11: Lock ALL batch operation**
    - Verify only `submitted` orders transition to `locked`; `draft`/`locked` unchanged
    - File: `backend/tests/unit/test_presmeet_v2_order_lifecycle.py`
    - **Validates: Requirements 8.8**

  - [x] 13.8 Write property test for booking form mapping (Property 14)
    - **Property 14: Booking form to cart item mapping**
    - Verify delegate/guest/tshirt/transfer produce correct cart items with attributes
    - File: `backend/tests/unit/test_presmeet_v2_booking_form.py`
    - **Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5**

  - [x] 13.9 Write property test for cascade delete (Property 15)
    - **Property 15: Cascade delete on delegate removal**
    - Verify removing delegate removes all associated items, others unchanged
    - File: `backend/tests/unit/test_presmeet_v2_booking_form.py`
    - **Validates: Requirements 7.8**

  - [x] 13.10 Write property test for CSV export completeness (Property 16)
    - **Property 16: CSV export completeness**
    - Verify CSV contains exactly one row per cart item across matching orders
    - File: `backend/tests/unit/test_presmeet_v2_reporting.py`
    - **Validates: Requirements 9.6**

- [x] 14. Deprecate v1 `extract_club_id` and clean up
  - [x] 14.1 Mark `extract_club_id` as deprecated in `presmeet_validation.py`
    - Add deprecation warning to the function
    - Verify no remaining handlers import `extract_club_id`
    - Remove `club_*` group pattern recognition from `frontend/src/utils/authHeaders.ts`
    - _Requirements: 11.4, 11.8_

- [x] 15. Final checkpoint — Full integration verification
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The migration script (task 7.1) should be run BEFORE deploying v2 handlers
- The Club_Registry JSON (task 7.2) must be uploaded to S3 before onboarding flow works
- All handler migrations (tasks 2.x, 3.x) follow the same pattern — can be batch-applied
- Frontend changes assume existing `FunctionGuard` component supports array of roles with OR logic

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "7.1", "7.2", "9.1"] },
    {
      "id": 1,
      "tasks": [
        "1.2",
        "1.3",
        "1.4",
        "1.5",
        "2.1",
        "2.2",
        "2.3",
        "2.4",
        "2.5",
        "2.6",
        "9.2"
      ]
    },
    {
      "id": 2,
      "tasks": ["3.1", "3.2", "3.3", "3.4", "3.5", "5.1", "5.2", "9.3"]
    },
    {
      "id": 3,
      "tasks": ["5.3", "6.1", "10.1", "13.1", "13.2", "13.3", "13.4", "13.5"]
    },
    {
      "id": 4,
      "tasks": ["10.2", "10.3", "11.1", "13.6", "13.7", "13.8", "13.9", "13.10"]
    },
    { "id": 5, "tasks": ["11.2", "11.3", "14.1"] }
  ]
}
```
