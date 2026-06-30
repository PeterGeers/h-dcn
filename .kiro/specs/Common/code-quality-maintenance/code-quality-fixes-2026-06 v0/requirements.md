# Requirements Document

## Introduction

Monthly code quality scan for the H-DCN codebase (June 2026). This document captures findings from automated scanning of file lengths, test coverage gaps, duplicated code, and stale documentation. Findings are categorized by severity: files exceeding 1000 lines require refactoring tasks; files between 500–1000 lines are documented as warnings only.

## Glossary

- **Scanner**: The automated code quality scanning process
- **Handler**: A Python Lambda function entry point located in `backend/handler/<name>/app.py`
- **Layer**: Shared Python code deployed as a Lambda Layer from `backend/layers/auth-layer/`
- **Component**: A React TypeScript component file (`.tsx`) in `frontend/src/components/` or `frontend/src/modules/`
- **Service**: A TypeScript service file (`.ts`) in `frontend/src/services/`
- **Stale_Document**: A documentation file in `docs/` whose content no longer reflects the current state of the code it describes
- **Dead_Code**: Unused functions, imports, variables, or duplicated modules that serve no runtime purpose

## Requirements

### Requirement 1: File Length — Critical (Over 1000 Lines)

**User Story:** As a developer, I want oversized files to be refactored into smaller modules, so that the codebase remains maintainable and navigable.

#### Acceptance Criteria

1. WHEN the Scanner identifies `backend/handler/hdcn_cognito_admin/app.py` (2567 lines), THE Scanner SHALL flag the file as critical and generate a refactoring task to split it into sub-modules by Cognito operation category (user management, group management, password operations).
2. WHEN the Scanner identifies `frontend/src/config/memberFields.ts` (2086 lines), THE Scanner SHALL flag the file as critical and generate a refactoring task to split field definitions into separate files per domain (personal fields, address fields, membership fields, club fields).

### Requirement 2: File Length — Warning (500–1000 Lines, Backend)

**User Story:** As a developer, I want visibility into backend files approaching the maximum threshold, so that I can plan refactoring before they become critical.

#### Acceptance Criteria

1. THE Scanner SHALL document `backend/handler/update_member/app.py` (913 lines) as a warning-level finding.
2. THE Scanner SHALL document `backend/handler/get_member_self/role_permissions.py` (889 lines) as a warning-level finding.
3. THE Scanner SHALL document `backend/handler/update_member/role_permissions.py` (889 lines) as a warning-level finding.
4. THE Scanner SHALL document `backend/handler/hdcn_cognito_admin/role_permissions.py` (882 lines) as a warning-level finding.
5. THE Scanner SHALL document `backend/handler/update_member/auth_utils_local.py` (764 lines) as a warning-level finding.
6. THE Scanner SHALL document `backend/layers/auth-layer/python/shared/product_validation.py` (680 lines) as a warning-level finding.
7. THE Scanner SHALL document `backend/handler/create_order/app.py` (629 lines) as a warning-level finding.
8. THE Scanner SHALL document `backend/handler/cognito_role_assignment/app.py` (626 lines) as a warning-level finding.
9. THE Scanner SHALL document `backend/handler/generate_order_pdf/app.py` (606 lines) as a warning-level finding.
10. THE Scanner SHALL document `backend/layers/auth-layer/python/shared/auth_utils.py` (608 lines) as a warning-level finding.

### Requirement 3: File Length — Warning (500–1000 Lines, Frontend)

**User Story:** As a developer, I want visibility into frontend files approaching the maximum threshold, so that I can plan component decomposition proactively.

#### Acceptance Criteria

1. THE Scanner SHALL document `frontend/src/pages/MembershipManagement.tsx` (721 lines) as a warning-level finding.
2. THE Scanner SHALL document `frontend/src/modules/webshop/WebshopPage.tsx` (711 lines) as a warning-level finding.
3. THE Scanner SHALL document `frontend/src/components/NewMemberApplicationForm.tsx` (706 lines) as a warning-level finding.
4. THE Scanner SHALL document `frontend/src/components/MemberEditView.tsx` (704 lines) as a warning-level finding.
5. THE Scanner SHALL document `frontend/src/components/MemberAdminTable.tsx` (699 lines) as a warning-level finding.
6. THE Scanner SHALL document `frontend/src/modules/members/components/MemberEditModal.tsx` (696 lines) as a warning-level finding.
7. THE Scanner SHALL document `frontend/src/utils/functionPermissions.ts` (695 lines) as a warning-level finding.
8. THE Scanner SHALL document `frontend/src/modules/products/components/AdvancedImageEditor.tsx` (668 lines) as a warning-level finding.
9. THE Scanner SHALL document `frontend/src/services/DataProcessingService.ts` (663 lines) as a warning-level finding.
10. THE Scanner SHALL document `frontend/src/modules/products/components/ProductCard.tsx` (661 lines) as a warning-level finding.
11. THE Scanner SHALL document `frontend/src/modules/products/components/ImageEditor.tsx` (629 lines) as a warning-level finding.
12. THE Scanner SHALL document `frontend/src/services/GoogleMailService.ts` (622 lines) as a warning-level finding.
13. THE Scanner SHALL document `frontend/src/modules/presmeet/components/AdminDashboard.tsx` (588 lines) as a warning-level finding.
14. THE Scanner SHALL document `frontend/src/components/reporting/GoogleMailIntegration.tsx` (559 lines) as a warning-level finding.
15. THE Scanner SHALL document `frontend/src/modules/products/components/OrderItemFieldsEditor.tsx` (559 lines) as a warning-level finding.
16. THE Scanner SHALL document `frontend/src/components/reporting/AddressLabelGenerator.tsx` (519 lines) as a warning-level finding.
17. THE Scanner SHALL document `frontend/src/components/auth/CustomAuthenticator.tsx` (508 lines) as a warning-level finding.
18. THE Scanner SHALL document `frontend/src/components/reporting/AnalyticsSection.tsx` (502 lines) as a warning-level finding.

### Requirement 4: Missing Tests — Backend Handlers

**User Story:** As a developer, I want all backend handlers to have at minimum a unit test stub, so that regressions can be caught before deployment.

#### Acceptance Criteria

1. WHEN the Scanner identifies a handler without a corresponding `test_*.py` file in `backend/tests/unit/` or `backend/tests/integration/`, THE Scanner SHALL flag the handler as missing test coverage.
2. THE Scanner SHALL report 67 out of 85 handlers (79%) lack dedicated test files. The untested handlers include:
   - Admin webshop handlers (16): `admin_add_stock`, `admin_bulk_create_variants`, `admin_create_variant`, `admin_export_report`, `admin_generate_report`, `admin_get_orders`, `admin_get_payments`, `admin_get_products`, `admin_get_report`, `admin_get_stock_movements`, `admin_lock_orders`, `admin_record_payment`, `admin_unlock_order`, `admin_update_order_status`, `admin_update_variant`, `assign_club`
   - Cart/Order handlers (5): `clear_cart`, `get_cart`, `get_customer_orders`, `get_order_byid`, `get_orders`
   - Cognito handlers (5): `cognito_post_authentication`, `cognito_post_confirmation`, `cognito_pre_signup`, `cognito_role_assignment`, `cognito_user_migration`
   - Member handlers (8): `create_member`, `delete_member`, `export_members`, `get_member_byid`, `get_member_self`, `hdcn_cognito_admin`, `update_member`, `get_member_payments`
   - Event handlers (4): `create_event`, `delete_event`, `get_event_byid`, `get_events`
   - Membership handlers (5): `create_membership`, `delete_membership`, `get_membership_byid`, `get_memberships`, `update_membership`
   - Payment handlers (5): `create_payment`, `delete_payment`, `get_payment_byid`, `get_payments`, `update_payment`
   - Product handlers (4): `delete_product`, `get_product_byid`, `insert_product`, `scan_product`
   - PresMeet handlers (5): `get_presmeet_config`, `get_presmeet_report`, `generate_presmeet_report`, `lock_presmeet_orders`, `manual_presmeet_payment`
   - Other handlers (10): `create_order`, `generate_order_pdf`, `s3_file_manager`, `update_event`, `update_order_status`, `update_parameters`, `upload_image`, `get_club_registry`, `create_presmeet_payment`, `update_member`
3. THE Scanner SHALL generate test stub tasks for the 10 highest-priority untested handlers: `create_order`, `update_member`, `hdcn_cognito_admin`, `get_member_self`, `cognito_role_assignment`, `generate_order_pdf`, `create_member`, `export_members`, `admin_get_orders`, `admin_record_payment`.

### Requirement 5: Missing Tests — Frontend Components

**User Story:** As a developer, I want critical frontend components to have test coverage, so that UI regressions are detected before release.

#### Acceptance Criteria

1. THE Scanner SHALL report 29 out of 40 components in `frontend/src/components/` (73%) lack test files.
2. THE Scanner SHALL report 75 out of 75 module components in `frontend/src/modules/` lack co-located test files.
3. THE Scanner SHALL report 2 frontend services lack test files: `googleAuthService.ts` and `MemberService.ts` (note: `DataProcessingService.example.ts` is an example file, not a service requiring tests).
4. THE Scanner SHALL generate test stub tasks for the 5 highest-priority untested components: `MemberAdminTable.tsx`, `MemberEditView.tsx`, `NewMemberApplicationForm.tsx`, `CustomAuthenticator.tsx`, `WebshopPage.tsx`.

### Requirement 6: Dead Code — Duplicated Role Permissions Modules

**User Story:** As a developer, I want duplicated code to be consolidated into the shared layer, so that maintenance burden is reduced and behavior stays consistent.

#### Acceptance Criteria

1. WHEN the Scanner identifies `role_permissions.py` duplicated in 3 handler directories (`get_member_self`, `hdcn_cognito_admin`, `update_member`) with 882–889 lines each, THE Scanner SHALL flag the duplication and generate a consolidation task.
2. WHEN the Scanner identifies `auth_utils_local.py` (764 lines) in `backend/handler/update_member/`, THE Scanner SHALL flag the file as a local copy that should use the shared layer `backend/layers/auth-layer/python/shared/auth_utils.py` instead.

### Requirement 7: Stale Documentation

**User Story:** As a developer, I want documentation to reflect the current state of the system, so that onboarding and troubleshooting remain effective.

#### Acceptance Criteria

1. WHEN the Scanner identifies `docs/README.md` (last updated 2026-01-10) stating "51 Lambda functions" while the codebase has 85 handler directories, THE Scanner SHALL flag the document as stale and generate an update task.
2. WHEN the Scanner identifies `docs/webshop/image-management-system.md` (last updated 2025-12-30) and the webshop product system was significantly reworked in the product unification feature (March 2026), THE Scanner SHALL flag the document as stale and generate an update task.
3. WHEN the Scanner identifies `docs/architecture/parameter-id-mapping-system.md` (last updated 2025-12-30) and parameter handling has changed with the i18n and product unification features (2026), THE Scanner SHALL flag the document as stale.
4. WHEN the Scanner identifies `docs/deployment/role-migration-deployment-guide.md` (last updated 2026-01-10) and the role system was migrated to the new permission model by January 2026, THE Scanner SHALL flag the document as potentially archivable.
5. WHEN the Scanner identifies `docs/development/test-environment-setup.md` (last updated 2025-12-29) and 39 new handlers plus PresMeet and product unification features have been added since, THE Scanner SHALL flag the document as stale and generate an update task.
6. WHEN the Scanner identifies `docs/security/security-scan-report.md` (last updated 2025-12-29) and the codebase has changed significantly since, THE Scanner SHALL flag the document as stale and generate an update task.

## Summary of Findings

| Category                 | Critical                                           | Warning                  | Total Findings                          |
| ------------------------ | -------------------------------------------------- | ------------------------ | --------------------------------------- |
| File Length (Backend)    | 1 file (2567 lines)                                | 9 files (606–913 lines)  | 10                                      |
| File Length (Frontend)   | 1 file (2086 lines)                                | 18 files (502–721 lines) | 19                                      |
| Missing Tests (Backend)  | —                                                  | —                        | 67 handlers untested                    |
| Missing Tests (Frontend) | —                                                  | —                        | 29 components + 75 modules + 2 services |
| Dead Code / Duplication  | 4 files (role_permissions ×3, auth_utils_local ×1) | —                        | 4                                       |
| Stale Documentation      | —                                                  | —                        | 6 documents                             |

### Action Items (Tasks to Generate)

| Priority | Category      | Action                                                      |
| -------- | ------------- | ----------------------------------------------------------- |
| P1       | File Length   | Refactor `hdcn_cognito_admin/app.py` (2567 lines)           |
| P1       | File Length   | Refactor `frontend/src/config/memberFields.ts` (2086 lines) |
| P2       | Dead Code     | Consolidate 3× `role_permissions.py` into shared layer      |
| P2       | Dead Code     | Remove `auth_utils_local.py` and use shared layer           |
| P3       | Missing Tests | Create test stubs for 10 priority backend handlers          |
| P3       | Missing Tests | Create test stubs for 5 priority frontend components        |
| P4       | Stale Docs    | Update `docs/README.md` (handler count, features)           |
| P4       | Stale Docs    | Update `docs/webshop/image-management-system.md`            |
| P4       | Stale Docs    | Update `docs/development/test-environment-setup.md`         |
| P4       | Stale Docs    | Update `docs/security/security-scan-report.md`              |
