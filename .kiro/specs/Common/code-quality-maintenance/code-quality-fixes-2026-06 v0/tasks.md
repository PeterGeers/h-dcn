# Implementation Plan: Code Quality Fixes June 2026

## Overview

Refactoring sprint addressing critical file length issues, dead code consolidation, missing test coverage, and stale documentation. All changes are internal — no API or runtime behavior modifications. Ordered by priority: file length → dead code → missing tests → stale docs.

## Tasks

- [x] 1. Split `hdcn_cognito_admin/app.py` (2567 lines) into sub-modules
  - [x] 1.1 Extract `backend/handler/hdcn_cognito_admin/user_operations.py`
    - Move `get_users`, `verify_user_exists`, `create_user`, `update_user`, `delete_user`, `import_users`, `passwordless_signup`, `passkey_migration_check` into this module
    - Each function keeps its existing signature
    - _Requirements: 1.1_

  - [x] 1.2 Extract `backend/handler/hdcn_cognito_admin/group_operations.py`
    - Move `get_groups`, `create_group`, `delete_group`, `add_user_to_group`, `remove_user_from_group`, `get_user_groups`, `import_groups`, `assign_user_groups`, `get_users_in_group`
    - _Requirements: 1.1_

  - [x] 1.3 Extract `backend/handler/hdcn_cognito_admin/auth_operations.py`
    - Move `get_auth_login`, `get_auth_permissions`, `get_pool_info`
    - _Requirements: 1.1_

  - [x] 1.4 Extract `backend/handler/hdcn_cognito_admin/role_operations.py`
    - Move `get_user_roles`, `assign_user_roles_auth`, `remove_user_role_auth`, `validate_role_assignment_rules`, `validate_role_assignment_permission`, `calculate_user_permissions`
    - _Requirements: 1.1_

  - [x] 1.5 Extract `backend/handler/hdcn_cognito_admin/permission_utils.py`
    - Move `validate_field_permissions`, `get_user_field_permissions`, `check_role_permission`, `get_role_summary`
    - _Requirements: 1.1_

  - [x] 1.6 Rewrite `backend/handler/hdcn_cognito_admin/app.py` as router
    - Keep `lambda_handler` as sole entry point (path unchanged in template.yaml)
    - Import from sub-modules, dispatch based on `httpMethod` + `path`
    - Shared state (Cognito client, table refs) initialized here, passed to sub-module functions
    - Target: ~220 lines
    - _Requirements: 1.1_

  - [x] 1.7 Write property test: backend split preserves public API
    - **Property 1: Backend split preserves public API**
    - Verify all 31 original function names remain importable from the refactored package
    - Create `backend/tests/unit/test_hdcn_cognito_admin_split.py`
    - **Validates: Requirements 1.1**

- [x] 2. Split `frontend/src/config/memberFields.ts` (2086 lines) into module directory
  - [x] 2.1 Create `frontend/src/config/memberFields/types.ts`
    - Extract all interfaces: `FieldDefinition`, `ConditionalRule`, `ValidationRule`, `PermissionConfig`, etc.
    - _Requirements: 1.2_

  - [x] 2.2 Create `frontend/src/config/memberFields/permissions.ts`
    - Extract `createPermissionConfig` and permission constants
    - _Requirements: 1.2_

  - [x] 2.3 Create field definition files in `frontend/src/config/memberFields/fields/`
    - `personalFields.ts` — fields with `group: 'personal'`
    - `addressFields.ts` — fields with `group: 'address'`
    - `membershipFields.ts` — fields with `group: 'membership'`
    - `motorFields.ts` — fields with `group: 'motor'`
    - `financialFields.ts` — fields with `group: 'financial'`
    - `administrativeFields.ts` — fields with `group: 'administrative'`
    - Each file exports a partial `Record<string, FieldDefinition>`
    - _Requirements: 1.2_

  - [x] 2.4 Create `frontend/src/config/memberFields/tableConfig.ts`
    - Extract `TableColumnConfig`, `TableContextConfig`, table context definitions
    - _Requirements: 1.2_

  - [x] 2.5 Create `frontend/src/config/memberFields/modalConfig.ts`
    - Extract `ModalFieldConfig`, `ModalGroupConfig`, `ModalSectionConfig`, `ModalContextConfig`, modal context definitions
    - _Requirements: 1.2_

  - [x] 2.6 Create `frontend/src/config/memberFields/helpers.ts`
    - Extract all exported functions: `getModalContext`, `getVisibleSections`, `getFieldsByGroup`, etc.
    - _Requirements: 1.2_

  - [x] 2.7 Create `frontend/src/config/memberFields/index.ts` barrel re-export
    - Re-export all symbols from sub-modules for backward compatibility
    - Merge field partials into single `MEMBER_FIELDS` constant
    - Existing imports (`from '../config/memberFields'`) must continue working unchanged
    - _Requirements: 1.2_

  - [x] 2.8 Delete original `frontend/src/config/memberFields.ts` file
    - Only after verifying `npm run build:prod` succeeds with the new directory structure
    - _Requirements: 1.2_

  - [x] 2.9 Write property test: frontend split preserves field registry
    - **Property 2: Frontend split preserves field registry**
    - Verify reassembled `MEMBER_FIELDS` contains identical keys and values as original
    - Create `frontend/src/config/memberFields/__tests__/memberFields.integrity.test.ts`
    - **Validates: Requirements 1.2**

- [x] 3. Checkpoint — File length refactoring
  - Ensure all tests pass, ask the user if questions arise.
  - Backend: run `sam build` to verify Lambda packaging for `hdcn_cognito_admin`
  - Frontend: run `npm run build:prod` to verify TypeScript compilation

- [x] 4. Consolidate duplicated `role_permissions.py` into shared layer
  - [x] 4.1 Diff the three local copies and create `backend/layers/auth-layer/python/shared/role_permissions.py`
    - Compare `backend/handler/get_member_self/role_permissions.py`, `backend/handler/update_member/role_permissions.py`, `backend/handler/hdcn_cognito_admin/role_permissions.py`
    - Merge any handler-specific divergences into a single canonical module
    - _Requirements: 6.1_

  - [x] 4.2 Update handler imports to use shared layer
    - In `backend/handler/get_member_self/app.py`: change `from role_permissions import ...` → `from shared.role_permissions import ...`
    - In `backend/handler/update_member/app.py`: change `from role_permissions import ...` → `from shared.role_permissions import ...`
    - In `backend/handler/hdcn_cognito_admin/app.py`: change `from role_permissions import ...` → `from shared.role_permissions import ...`
    - _Requirements: 6.1_

  - [x] 4.3 Delete the three local `role_permissions.py` copies
    - `backend/handler/get_member_self/role_permissions.py`
    - `backend/handler/update_member/role_permissions.py`
    - `backend/handler/hdcn_cognito_admin/role_permissions.py`
    - _Requirements: 6.1_

  - [x] 4.4 Write property test: role_permissions consolidation preserves function availability
    - **Property 3: Role permissions consolidation preserves function availability**
    - Verify all function names from the three local copies are available in `shared.role_permissions`
    - Create `backend/tests/unit/test_role_permissions_consolidation.py`
    - **Validates: Requirements 6.1**

- [x] 5. Remove `auth_utils_local.py` duplication
  - [x] 5.1 Update `backend/handler/update_member/app.py` to import from shared layer
    - Replace `from auth_utils_local import ...` with `from shared.auth_utils import ...`
    - Verify all imported functions exist in the shared `auth_utils.py`
    - _Requirements: 6.2_

  - [x] 5.2 Delete `backend/handler/update_member/auth_utils_local.py`
    - _Requirements: 6.2_

  - [x] 5.3 Write property test: shared layer subsumes local auth utils
    - **Property 4: Shared layer subsumes local auth utils**
    - Verify all functions from `auth_utils_local.py` are available in `shared.auth_utils`
    - Create `backend/tests/unit/test_auth_utils_consolidation.py`
    - **Validates: Requirements 6.2**

- [x] 6. Checkpoint — Dead code removal
  - Ensure all tests pass, ask the user if questions arise.
  - Run `sam build` to verify Lambda packaging for `get_member_self`, `update_member`, `hdcn_cognito_admin`
  - Run existing auth tests: `pytest tests/unit/test_comprehensive_auth_flows.py tests/unit/test_auth_logging.py`

- [x] 7. Create backend test stubs (10 priority handlers)
  - [x] 7.1 Create `backend/tests/unit/test_create_order.py`
    - Import `from handler.create_order.app import lambda_handler`
    - Include `api_gateway_event` fixture, `test_handler_exists`, `test_returns_401_without_auth`
    - Must pass `pytest --collect-only`
    - _Requirements: 4.3_

  - [x] 7.2 Create `backend/tests/unit/test_update_member.py`
    - Import `from handler.update_member.app import lambda_handler`
    - Include `api_gateway_event` fixture, `test_handler_exists`, `test_returns_401_without_auth`
    - Must pass `pytest --collect-only`
    - _Requirements: 4.3_

  - [x] 7.3 Create `backend/tests/unit/test_hdcn_cognito_admin.py`
    - Import `from handler.hdcn_cognito_admin.app import lambda_handler`
    - Include `api_gateway_event` fixture, `test_handler_exists`, `test_returns_401_without_auth`
    - Must pass `pytest --collect-only`
    - _Requirements: 4.3_

  - [x] 7.4 Create `backend/tests/unit/test_get_member_self.py`
    - Import `from handler.get_member_self.app import lambda_handler`
    - Include `api_gateway_event` fixture, `test_handler_exists`, `test_returns_401_without_auth`
    - Must pass `pytest --collect-only`
    - _Requirements: 4.3_

  - [x] 7.5 Create `backend/tests/unit/test_cognito_role_assignment.py`
    - Import `from handler.cognito_role_assignment.app import lambda_handler`
    - Include `api_gateway_event` fixture, `test_handler_exists`, `test_returns_401_without_auth`
    - Must pass `pytest --collect-only`
    - _Requirements: 4.3_

  - [x] 7.6 Create `backend/tests/unit/test_generate_order_pdf.py`
    - Import `from handler.generate_order_pdf.app import lambda_handler`
    - Include `api_gateway_event` fixture, `test_handler_exists`, `test_returns_401_without_auth`
    - Must pass `pytest --collect-only`
    - _Requirements: 4.3_

  - [x] 7.7 Create `backend/tests/unit/test_create_member.py`
    - Import `from handler.create_member.app import lambda_handler`
    - Include `api_gateway_event` fixture, `test_handler_exists`, `test_returns_401_without_auth`
    - Must pass `pytest --collect-only`
    - _Requirements: 4.3_

  - [x] 7.8 Create `backend/tests/unit/test_export_members.py`
    - Import `from handler.export_members.app import lambda_handler`
    - Include `api_gateway_event` fixture, `test_handler_exists`, `test_returns_401_without_auth`
    - Must pass `pytest --collect-only`
    - _Requirements: 4.3_

  - [x] 7.9 Create `backend/tests/unit/test_admin_get_orders.py`
    - Import `from handler.admin_get_orders.app import lambda_handler`
    - Include `api_gateway_event` fixture, `test_handler_exists`, `test_returns_401_without_auth`
    - Must pass `pytest --collect-only`
    - _Requirements: 4.3_

  - [x] 7.10 Create `backend/tests/unit/test_admin_record_payment.py`
    - Import `from handler.admin_record_payment.app import lambda_handler`
    - Include `api_gateway_event` fixture, `test_handler_exists`, `test_returns_401_without_auth`
    - Must pass `pytest --collect-only`
    - _Requirements: 4.3_

  - [x] 7.11 Write property test: generated backend test stubs are valid and importable
    - **Property 5: Generated test stubs are valid and importable**
    - Verify each stub file parses without syntax errors, imports its handler, and contains `test_` functions
    - Create `backend/tests/unit/test_stub_validity.py`
    - **Validates: Requirements 4.3**

- [x] 8. Create frontend test stubs (5 priority components)
  - [x] 8.1 Create `frontend/src/components/__tests__/MemberAdminTable.test.tsx`
    - Import `MemberAdminTable` from `../MemberAdminTable`
    - Mock `useAuth` context, wrap in `ChakraProvider`
    - Include `renders without crashing` test
    - Must pass `npm test -- --watchAll=false --testPathPattern=MemberAdminTable`
    - _Requirements: 5.4_

  - [x] 8.2 Create `frontend/src/components/__tests__/MemberEditView.test.tsx`
    - Import `MemberEditView` from `../MemberEditView`
    - Mock `useAuth` context, wrap in `ChakraProvider`
    - Include `renders without crashing` test
    - Must pass `npm test -- --watchAll=false --testPathPattern=MemberEditView`
    - _Requirements: 5.4_

  - [x] 8.3 Create `frontend/src/components/__tests__/NewMemberApplicationForm.test.tsx`
    - Import `NewMemberApplicationForm` from `../NewMemberApplicationForm`
    - Mock `useAuth` context, wrap in `ChakraProvider`
    - Include `renders without crashing` test
    - Must pass `npm test -- --watchAll=false --testPathPattern=NewMemberApplicationForm`
    - _Requirements: 5.4_

  - [x] 8.4 Create `frontend/src/components/auth/__tests__/CustomAuthenticator.test.tsx`
    - Import `CustomAuthenticator` from `../CustomAuthenticator`
    - Mock Amplify auth modules
    - Include `renders without crashing` test
    - Must pass `npm test -- --watchAll=false --testPathPattern=CustomAuthenticator`
    - _Requirements: 5.4_

  - [x] 8.5 Create `frontend/src/modules/webshop/__tests__/WebshopPage.test.tsx`
    - Import `WebshopPage` from `../WebshopPage`
    - Mock `useAuth` context, wrap in `ChakraProvider`
    - Include `renders without crashing` test
    - Must pass `npm test -- --watchAll=false --testPathPattern=WebshopPage`
    - _Requirements: 5.4_

  - [x] 8.6 Write property test: generated frontend test stubs are valid
    - **Property 6: Generated frontend test stubs are valid**
    - Verify each stub file passes TypeScript type-checking and contains `it()` or `test()` blocks
    - Create `frontend/src/__tests__/stubValidity.test.ts`
    - **Validates: Requirements 5.4**

- [x] 9. Checkpoint — Test stubs
  - Ensure all tests pass, ask the user if questions arise.
  - Backend: run `pytest --collect-only backend/tests/unit/test_create_order.py backend/tests/unit/test_update_member.py backend/tests/unit/test_hdcn_cognito_admin.py backend/tests/unit/test_get_member_self.py backend/tests/unit/test_cognito_role_assignment.py backend/tests/unit/test_generate_order_pdf.py backend/tests/unit/test_create_member.py backend/tests/unit/test_export_members.py backend/tests/unit/test_admin_get_orders.py backend/tests/unit/test_admin_record_payment.py`
  - Frontend: run `npm test -- --watchAll=false`

- [x] 10. Update stale documentation
  - [x] 10.1 Update `docs/README.md`
    - Correct handler count from 51 → 85
    - Add PresMeet feature section
    - Add product unification feature section
    - Update architecture diagram if present
    - _Requirements: 7.1_

  - [x] 10.2 Update `docs/webshop/image-management-system.md`
    - Reflect product unification rework (March 2026)
    - Update references to product/variant structure
    - _Requirements: 7.2_

  - [x] 10.3 Update `docs/development/test-environment-setup.md`
    - Add setup instructions for new handlers (39 added since last update)
    - Add PresMeet configuration section
    - Add product variants setup
    - _Requirements: 7.5_

  - [x] 10.4 Update `docs/security/security-scan-report.md`
    - Re-run scan metrics against current codebase (85 handlers)
    - Update vulnerability counts and dependency audit
    - _Requirements: 7.6_

  - [x] 10.5 Update `docs/architecture/parameter-id-mapping-system.md`
    - Reflect i18n changes to parameter handling
    - Reflect product unification parameter changes
    - _Requirements: 7.3_

  - [x] 10.6 Mark `docs/deployment/role-migration-deployment-guide.md` as archived
    - Add archive header noting migration completed January 2026
    - Move to `docs/archive/` or add prominent deprecation notice
    - _Requirements: 7.4_

- [x] 11. Final checkpoint
  - Ensure all tests pass, ask the user if questions arise.
  - Backend: `sam build` (verify full Lambda packaging)
  - Frontend: `npm run build:prod` (verify TypeScript compilation)
  - Run full test suites: `pytest backend/tests/` and `npm test -- --watchAll=false`

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- No changes to `template.yaml` — Lambda handler paths remain unchanged
- Frontend split uses barrel re-export (`index.ts`) for backward compatibility
- Backend `role_permissions.py` goes into the existing shared layer at `backend/layers/auth-layer/python/shared/`
- Test stubs are designed to be immediately runnable (pass `pytest --collect-only` / `npm test`)
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3", "1.4", "1.5", "2.1", "2.2"] },
    { "id": 1, "tasks": ["1.6", "2.3", "2.4", "2.5", "2.6"] },
    { "id": 2, "tasks": ["1.7", "2.7"] },
    { "id": 3, "tasks": ["2.8", "2.9"] },
    { "id": 4, "tasks": ["4.1"] },
    { "id": 5, "tasks": ["4.2", "5.1"] },
    { "id": 6, "tasks": ["4.3", "4.4", "5.2", "5.3"] },
    {
      "id": 7,
      "tasks": [
        "7.1",
        "7.2",
        "7.3",
        "7.4",
        "7.5",
        "7.6",
        "7.7",
        "7.8",
        "7.9",
        "7.10",
        "8.1",
        "8.2",
        "8.3",
        "8.4",
        "8.5"
      ]
    },
    { "id": 8, "tasks": ["7.11", "8.6"] },
    { "id": 9, "tasks": ["10.1", "10.2", "10.3", "10.4", "10.5", "10.6"] }
  ]
}
```
