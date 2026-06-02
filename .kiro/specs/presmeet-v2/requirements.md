# Requirements Document

## Introduction

PresMeet v2 is a redesign of the Presidents' Meeting booking module that aligns it with the existing H-DCN authentication, member, and product systems. The core booking logic (validation, cart mapping, pricing, order lifecycle) is retained, but the integration points are rebuilt to use the established role-based access control, Member table storage, and product management patterns already in place for H-DCN.

Key changes from v1:

- Authentication via `Regio_Pressmeet` region role instead of custom `club_*` Cognito groups
- Club identity stored on the Member record (not in Cognito)
- Club representatives stored as Members with `lidmaatschap=overig`, `status=presmeet`
- Products separated by `tenant` field (`presmeet` / `h-dcn`) with optional frontend filter toggle
- Admin access via existing `Products_CRUD` / `Products_Read` roles
- Multi-tenant field on all DynamoDB records (`tenant: "presmeet"` or `tenant: "h-dcn"`)
- Entry point at `presmeet.h-dcn.nl`

## Glossary

- **Booking_System**: The PresMeet v2 module within the H-DCN portal for event registration and ordering
- **Club_Representative**: A Member with `lidmaatschap=overig` and `status=presmeet`, representing one FH-DCE club. Has Cognito groups `hdcnLeden` + `Regio_Pressmeet`
- **PresMeet_Admin**: A user with `SysAdmin` `Products_CRUD` or `Webshop_Management` role and `Regio_Pressmeet` or `Regio_All` region assignment
- **Club_Registry**: A configuration list (stored in S3 or Systems Manager Parameter Store) containing all available FH-DCE clubs with their identifiers, small logo and names
- **Tenant_Field**: A field present on all DynamoDB records indicating data ownership (`presmeet` or `h-dcn`)
- **Booking_Form**: The frontend form used by Club_Representatives to register delegates, guests, t-shirts, and airport transfers

## Requirements

### Requirement 1: Authentication Alignment

**User Story:** As a club representative, I want to authenticate using the same Cognito pool and role structure as H-DCN members, so that the system uses a single consistent auth model.

#### Acceptance Criteria

1. THE Booking_System SHALL authenticate Club_Representatives via the existing AWS Cognito user pool (`eu-west-1_fcUkvwjH5`) using the same auth flows as H-DCN members
2. THE Booking_System SHALL assign Club_Representatives the Cognito groups `hdcnLeden` and `Regio_Pressmeet`, so that all existing APIs that grant access to `hdcnLeden` work without modification (self-service, webshop, events_read)
3. THE Booking_System SHALL use the presence of `Regio_Pressmeet` (or `Regio_All`) in the user's Cognito groups as the sole gate for Booking_Form access — no new permission role is needed
4. IF an authenticated user does not have `Regio_Pressmeet` or `Regio_All` in their Cognito groups, THEN THE Booking_System SHALL hide the Booking_Form from navigation and deny access to PresMeet booking endpoints with a 403 response
5. THE Booking_System SHALL grant PresMeet_Admin access to users who have both a management role (`Products_CRUD`, `Products_Read`, or `Webshop_Management`) and a region role (`Regio_Pressmeet` or `Regio_All`)
6. WHEN a registered Club_Representative logs in via `presmeet.h-dcn.nl` or `portal.h-dcn.nl`, THE Booking_System SHALL direct them to the standard `portal.h-dcn.nl` start page with their authorized PresMeet functions available

### Requirement 2: Club Identity and Assignment

**User Story:** As a club representative, I want to select my club from a list during onboarding, so that my bookings are associated with the correct club without storing club data in Cognito.

#### Acceptance Criteria

1. THE Booking_System SHALL store club assignment as a `club_id` field on the Member record in the Members DynamoDB table
2. THE Booking_System SHALL maintain a Club_Registry containing all available FH-DCE clubs with `club_id`, `club_name`, and `assigned_member_id` (nullable) fields
3. WHEN a new Club_Representative registers, THE Booking_System SHALL display the Club_Registry list and allow the user to select one club
4. THE Booking_System SHALL enforce a maximum of one Club_Representative per club by checking the `assigned_member_id` field in the Club_Registry before assignment
5. IF a Club_Representative selects a club that already has an assigned user, THEN THE Booking_System SHALL display a message with the assigned user's contact information and an option to escalate to the PresMeet_Admin
6. WHEN a club assignment is confirmed, THE Booking_System SHALL update both the Member record (`club_id` field) and the Club_Registry (`assigned_member_id` field) atomically
7. THE Booking_System SHALL allow a PresMeet_Admin to reassign a club to a different member by clearing the previous assignment and setting the new one

### Requirement 3: Member Storage

**User Story:** As a system administrator, I want club representatives stored in the existing Members table with a specific membership type and status, so that member management is unified across H-DCN and PresMeet.

#### Acceptance Criteria

1. THE Booking_System SHALL store Club_Representatives in the Members DynamoDB table with `lidmaatschap` set to `overig` and `status` set to `presmeet`
2. THE Booking_System SHALL include the `tenant` field set to `presmeet` on all Club_Representative Member records
3. WHEN a Club_Representative accesses self-service functions, THE Booking_System SHALL apply the same self-service logic as H-DCN members (profile view, profile update of own data) — enabled by the `hdcnLeden` Cognito group
4. THE Booking_System SHALL grant Club_Representatives access to the H-DCN webshop (product browsing, cart, orders) — enabled by the `hdcnLeden` Cognito group, no API changes required
5. THE Booking_System SHALL grant Club_Representatives access to the PresMeet Booking_Form as an additional function, gated by the `Regio_Pressmeet` Cognito group on the frontend Dashboard
6. THE Booking_System SHALL store a `preferred_language` field on the Member record (default: `en`) to support future multi-language functionality

### Requirement 4: Product Management with Tenant-Based Filter

**User Story:** As a product administrator, I want to manage PresMeet products through the existing product admin interface with tenant-based separation, so that product management is unified while keeping the catalogs separate for end users.

#### Acceptance Criteria

1. THE Booking_System SHALL store PresMeet products in the existing Producten DynamoDB table with the `tenant` field set to `presmeet`
2. THE Booking_System SHALL store H-DCN webshop products in the Producten DynamoDB table with the `tenant` field set to `h-dcn`
3. THE Booking_System SHALL always filter products by `tenant` field: the H-DCN webshop SHALL display only products with `tenant=h-dcn`, and the PresMeet Booking_Form SHALL display only products with `tenant=presmeet`
4. THE Booking_System SHALL allow PresMeet_Admin users to create, read, update, and delete PresMeet products through the existing product admin interface using the existing `Products_CRUD` role
5. THE Booking_System SHALL support product attributes specific to PresMeet product types (meeting, party, traffic/transfer) through the existing product `attributes` JSON field

### Requirement 5: Admin Roles and Access

**User Story:** As an H-DCN administrator, I want to manage PresMeet bookings and products using existing H-DCN access roles, so that there is no custom permission model for PresMeet.

#### Acceptance Criteria

1. THE Booking_System SHALL use `Products_CRUD` role for full PresMeet product management (create, update, delete)
2. THE Booking_System SHALL use `Products_Read` role for read-only access to PresMeet products and booking data
3. THE Booking_System SHALL require `Regio_Pressmeet` or `Regio_All` region assignment in combination with a management role for PresMeet admin access
4. WHEN a user has `Products_CRUD` and `Regio_Pressmeet`, THE Booking_System SHALL grant access to all PresMeet admin functions including order management, lock/unlock, and manual payment recording
5. WHEN a user has `Products_Read` and `Regio_Pressmeet`, THE Booking_System SHALL grant read-only access to PresMeet booking data and reporting
6. THE Booking_System SHALL deny PresMeet admin functions to users who have management roles but lack `Regio_Pressmeet` or `Regio_All` region assignment

### Requirement 6: Multi-Tenancy

**User Story:** As a system architect, I want all DynamoDB records to carry a tenant identifier, so that PresMeet and H-DCN data can coexist in shared tables and be easily filtered or separated.

#### Acceptance Criteria

1. THE Booking_System SHALL include a `tenant` field on all new records written to DynamoDB tables (Members, Producten, Orders, Carts, Payments)
2. THE Booking_System SHALL set `tenant` to `presmeet` for all records created through the PresMeet module
3. THE Booking_System SHALL set `tenant` to `h-dcn` for all records created through standard H-DCN operations
4. WHEN querying data for the PresMeet module, THE Booking_System SHALL filter results to include only records with `tenant=presmeet` (unless the user has cross-tenant admin access)
5. WHEN querying data for the H-DCN portal, THE Booking_System SHALL filter results to include only records with `tenant=h-dcn` (unless the user has cross-tenant admin access)
6. THE Booking_System SHALL include a one-time data migration that adds `tenant=h-dcn` to all existing records in Members, Producten, Orders, Carts, and Payments tables that do not yet have a `tenant` field

### Requirement 7: Booking Form (Core Logic Retained)

**User Story:** As a club representative, I want to use the booking form to register delegates, guests, t-shirts, and airport transfers, so that the system creates correct cart items for my club's order.

#### Acceptance Criteria

1. WHEN a Club_Representative adds a delegate via the Booking_Form, THE Booking_System SHALL create a meeting_ticket cart item with the delegate's name and role as attributes
2. WHEN a Club_Representative selects party attendance for a delegate, THE Booking_System SHALL create a party_ticket cart item with `person_type=delegate` and the delegate's name
3. WHEN a Club_Representative adds a guest, THE Booking_System SHALL create a party_ticket cart item with `person_type=guest` and the guest's name
4. WHEN a Club_Representative selects a t-shirt for a person, THE Booking_System SHALL create a tshirt cart item with the person's name, gender, and size as attributes
5. WHEN a Club_Representative adds an airport transfer, THE Booking_System SHALL create an airport_transfer cart item with direction, airport, flight number, date, time, and number of persons as attributes
6. THE Booking_System SHALL calculate the cart total as the sum of each item's unit price multiplied by its quantity (using prices from the Producten table)
7. WHILE the order status is `draft`, THE Booking_System SHALL allow the Club_Representative to add, edit, or remove cart items
8. WHEN a Club_Representative removes a delegate, THE Booking_System SHALL cascade-delete all associated cart items (meeting_ticket, party_ticket, tshirt) for that delegate
9. THE Booking_System SHALL include `tenant=presmeet` and `club_id` on all Cart and Order records created through the Booking_Form

### Requirement 8: Order Lifecycle (Core Logic Retained)

**User Story:** As a club representative, I want to submit my booking when complete and track its status, so that the organizers can process it and I can proceed to payment.

#### Acceptance Criteria

1. THE Booking_System SHALL support three order statuses: `draft`, `submitted`, and `locked`
2. WHEN a Club_Representative submits a booking, THE Booking_System SHALL transition the order from `draft` to `submitted` after passing validation
3. IF a Club_Representative attempts to submit a booking that is not in `draft` status, THEN THE Booking_System SHALL reject the submission and return an error indicating the current status
4. WHILE an order is in `submitted` status, THE Booking_System SHALL allow the Club_Representative to modify items, reverting the status to `draft` upon modification
5. WHEN a PresMeet_Admin locks an order, THE Booking_System SHALL transition the order from `submitted` to `locked`
6. WHILE an order is in `locked` status, THE Booking_System SHALL reject modification attempts by the Club_Representative and return an error indicating the order is locked
7. WHEN a PresMeet_Admin unlocks an order, THE Booking_System SHALL transition the order from `locked` to `submitted`
8. WHEN a PresMeet_Admin triggers "Lock ALL", THE Booking_System SHALL transition all orders with status `submitted` to `locked`, leaving `draft` orders unchanged

### Requirement 9: Reporting

**User Story:** As a PresMeet administrator, I want to generate and view reports on bookings, payments, and registrations, so that I can monitor progress and produce outputs for event logistics.

#### Acceptance Criteria

1. WHEN a PresMeet_Admin triggers report generation, THE Booking_System SHALL scan all PresMeet orders and payments (filtered by `tenant=presmeet`) and write aggregated report files to S3
2. THE Booking_System SHALL include a visible timestamp of the last report generation in the admin interface
3. THE Booking_System SHALL provide standardized views per domain (orders overview, payment summary, delegate list, product counts by type and status)
4. THE Booking_System SHALL provide a pivot generator that allows PresMeet_Admin users to create custom pivot views and save them for reuse
5. THE Booking_System SHALL provide label printing functionality for delegate badges and logistics
6. THE Booking_System SHALL provide CSV export of booking data for external processing
7. WHEN a user accesses PresMeet reporting, THE Booking_System SHALL scope the data to records with `tenant=presmeet` based on the user's `Regio_Pressmeet` or `Regio_All` region assignment (noting that users may hold multiple roles and region assignments simultaneously)

### Requirement 10: Entry Point and Onboarding

**User Story:** As a new club representative, I want to register via `presmeet.h-dcn.nl` and then use the standard portal, so that onboarding is clear and ongoing access is through the same portal as all members.

#### Acceptance Criteria

1. WHEN a new (unregistered) user navigates to `presmeet.h-dcn.nl`, THE Booking_System SHALL present the onboarding flow: Cognito account creation followed by club selection from the Club_Registry
2. WHEN onboarding is complete (account created, club assigned), THE Booking_System SHALL redirect the user to `portal.h-dcn.nl` with their authorized functions available
3. WHEN a registered Club_Representative logs in via `presmeet.h-dcn.nl` or `portal.h-dcn.nl`, THE Booking_System SHALL direct them to the standard `portal.h-dcn.nl` start page
4. WHEN a Club_Representative is authenticated, THE Booking_System SHALL display three functions in the navigation: self-service profile (gated by `hdcnLeden`), webshop (gated by `hdcnLeden`), and Booking_Form (gated by `Regio_Pressmeet`)
5. WHEN a PresMeet_Admin is authenticated, THE Booking_System SHALL additionally show admin functions (order management, reporting, club management)

### Requirement 11: Existing Code Preservation

**User Story:** As a developer, I want to retain the working core booking logic and frontend components, so that proven and tested code is reused rather than rewritten.

#### Acceptance Criteria

1. THE Booking_System SHALL retain the existing validation module logic (attribute schema validation, product type validation, cart total calculation, outstanding balance calculation)
2. THE Booking_System SHALL retain the existing order lifecycle state machine (draft → submitted → locked transitions)
3. THE Booking_System SHALL retain the existing frontend booking form components (DelegateSection, GuestSection, TransferSection) with integration point changes only
4. THE Booking*System SHALL replace the club identity extraction logic (from Cognito `club*\*`groups to Member record`club_id` lookup)
5. THE Booking_System SHALL replace the admin permission check (from custom webmaster check to `Products_CRUD` / `Products_Read` role validation via `validate_permissions_with_regions`)
6. THE Booking_System SHALL add `Regio_Pressmeet` to the `HDCNGroup` TypeScript type definition in `frontend/src/types/user.ts`
7. THE Booking_System SHALL retain the existing `source` field on Orders (`source="presmeet"`) and Producten (`source="presmeet_config"`) alongside the new `tenant` field — `source` discriminates record type within presmeet, `tenant` provides multi-tenancy isolation
8. THE Booking*System SHALL deprecate and remove `club*\*`Cognito groups after migrating club identity to the Member record`club_id` field
