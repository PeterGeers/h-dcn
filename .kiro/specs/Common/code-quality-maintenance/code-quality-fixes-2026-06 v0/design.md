# Design Document

## Overview

This design covers the June 2026 code quality maintenance sprint for H-DCN: splitting two oversized files, consolidating duplicated modules, creating test stubs, and updating stale documentation. The approach prioritises backward compatibility — no API or runtime behavior changes.

## Architecture

All changes are internal refactoring. No new infrastructure, endpoints, or dependencies are introduced.

```
backend/handler/hdcn_cognito_admin/
  app.py (2567 lines) → app.py (router ~200 lines)
                       + user_operations.py
                       + group_operations.py
                       + auth_operations.py
                       + role_operations.py
                       + permission_utils.py

frontend/src/config/memberFields.ts (2086 lines)
  → memberFields/index.ts (re-exports)
  + memberFields/types.ts
  + memberFields/permissions.ts
  + memberFields/fields/personalFields.ts
  + memberFields/fields/addressFields.ts
  + memberFields/fields/membershipFields.ts
  + memberFields/fields/motorFields.ts
  + memberFields/fields/financialFields.ts
  + memberFields/fields/administrativeFields.ts
  + memberFields/tableConfig.ts
  + memberFields/modalConfig.ts
  + memberFields/helpers.ts

backend/layers/auth-layer/python/shared/
  role_permissions.py (NEW — consolidated from 3 handler copies)
```

## Components and Interfaces

### Component 1: hdcn_cognito_admin/app.py Split

**Current state:** Single 2567-line file with 31 functions covering user CRUD, group management, auth/login, role assignment, and field permissions.

**Split strategy by category:**

| Module                | Functions                                                                                                                                                                   | Approx. lines |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------- |
| `app.py` (router)     | `lambda_handler` + imports                                                                                                                                                  | ~220          |
| `user_operations.py`  | `get_users`, `verify_user_exists`, `create_user`, `update_user`, `delete_user`, `import_users`, `passwordless_signup`, `passkey_migration_check`                            | ~600          |
| `group_operations.py` | `get_groups`, `create_group`, `delete_group`, `add_user_to_group`, `remove_user_from_group`, `get_user_groups`, `import_groups`, `assign_user_groups`, `get_users_in_group` | ~400          |
| `auth_operations.py`  | `get_auth_login`, `get_auth_permissions`, `get_pool_info`                                                                                                                   | ~350          |
| `role_operations.py`  | `get_user_roles`, `assign_user_roles_auth`, `remove_user_role_auth`, `validate_role_assignment_rules`, `validate_role_assignment_permission`, `calculate_user_permissions`  | ~500          |
| `permission_utils.py` | `validate_field_permissions`, `get_user_field_permissions`, `check_role_permission`, `get_role_summary`                                                                     | ~200          |

**Approach:**

1. Extract functions into category modules within the same handler directory
2. Keep `app.py` as the Lambda entry point — it imports from sub-modules and dispatches based on `httpMethod` + `path`
3. Shared state (Cognito client init, table references) stays in `app.py` and is passed as arguments or accessed via module-level init
4. No changes to `template.yaml` — the Lambda handler path remains `handler/hdcn_cognito_admin/app.lambda_handler`

```python
# backend/handler/hdcn_cognito_admin/app.py (post-refactor)
from shared.auth_utils import extract_user_credentials, validate_permissions_with_regions
from .user_operations import get_users, verify_user_exists, create_user, ...
from .group_operations import get_groups, create_group, ...
from .auth_operations import get_auth_login, get_auth_permissions, ...
from .role_operations import get_user_roles, assign_user_roles_auth, ...
from .permission_utils import validate_field_permissions, ...

def lambda_handler(event, context):
    # Route to appropriate sub-module function based on path/method
    ...
```

### Component 2: memberFields.ts Split

**Current state:** Single 2086-line file containing type definitions, permission helpers, field registry (MEMBER_FIELDS), table context configs, modal context configs, and ~30 helper functions.

**Split strategy by concern:**

| Module                           | Content                                                                                                       | Approx. lines |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------- | ------------- |
| `types.ts`                       | All interfaces (FieldDefinition, ConditionalRule, ValidationRule, PermissionConfig, etc.)                     | ~100          |
| `permissions.ts`                 | `createPermissionConfig`, permission constants                                                                | ~80           |
| `fields/personalFields.ts`       | Fields with `group: 'personal'`                                                                               | ~250          |
| `fields/addressFields.ts`        | Fields with `group: 'address'`                                                                                | ~200          |
| `fields/membershipFields.ts`     | Fields with `group: 'membership'`                                                                             | ~300          |
| `fields/motorFields.ts`          | Fields with `group: 'motor'`                                                                                  | ~150          |
| `fields/financialFields.ts`      | Fields with `group: 'financial'`                                                                              | ~150          |
| `fields/administrativeFields.ts` | Fields with `group: 'administrative'`                                                                         | ~200          |
| `tableConfig.ts`                 | `TableColumnConfig`, `TableContextConfig`, table context definitions                                          | ~200          |
| `modalConfig.ts`                 | `ModalFieldConfig`, `ModalGroupConfig`, `ModalSectionConfig`, `ModalContextConfig`, modal context definitions | ~250          |
| `helpers.ts`                     | All exported functions (`getModalContext`, `getVisibleSections`, `getFieldsByGroup`, etc.)                    | ~200          |
| `index.ts`                       | Re-exports everything for backward compatibility                                                              | ~30           |

**Approach:**

1. Create `frontend/src/config/memberFields/` directory
2. Move types first, then field definitions grouped by `FieldGroup` enum value
3. `index.ts` re-exports all symbols so existing imports (`from '../config/memberFields'`) continue working without changes
4. Each field file exports a partial `Record<string, FieldDefinition>` that `index.ts` merges into `MEMBER_FIELDS`

```typescript
// frontend/src/config/memberFields/index.ts
export * from "./types";
export * from "./permissions";
export * from "./helpers";
export * from "./tableConfig";
export * from "./modalConfig";

import { personalFields } from "./fields/personalFields";
import { addressFields } from "./fields/addressFields";
// ...
export const MEMBER_FIELDS: Record<string, FieldDefinition> = {
  ...personalFields,
  ...addressFields,
  ...membershipFields,
  ...motorFields,
  ...financialFields,
  ...administrativeFields,
};
```

### Component 3: role_permissions.py Consolidation

**Current state:** Three near-identical copies (882–889 lines each) in:

- `backend/handler/get_member_self/role_permissions.py`
- `backend/handler/update_member/role_permissions.py`
- `backend/handler/hdcn_cognito_admin/role_permissions.py`

Plus `auth_utils_local.py` (764 lines) in `update_member/` duplicating the shared layer.

**Approach:**

1. Diff the three `role_permissions.py` files to identify any handler-specific divergences
2. Create `backend/layers/auth-layer/python/shared/role_permissions.py` with the canonical version
3. In each handler's `app.py`, replace `from role_permissions import ...` with `from shared.role_permissions import ...`
4. Delete the three local copies
5. Replace `from auth_utils_local import ...` in `update_member/app.py` with `from shared.auth_utils import ...`
6. Delete `auth_utils_local.py`
7. Verify the auth layer is deployed with `sam build` — the layer already packages everything under `python/shared/`

**Risk mitigation:** Since the shared layer is already deployed and working for `auth_utils`, adding `role_permissions.py` to the same directory is low-risk. Run existing integration tests against the affected handlers post-change.

### Component 4: Test Stub Creation — Backend

**10 priority handlers:** `create_order`, `update_member`, `hdcn_cognito_admin`, `get_member_self`, `cognito_role_assignment`, `generate_order_pdf`, `create_member`, `export_members`, `admin_get_orders`, `admin_record_payment`

**Stub template:**

```python
# backend/tests/unit/test_{handler_name}.py
"""Unit tests for {handler_name} handler."""
import json
import pytest
from unittest.mock import patch, MagicMock

# Import handler
from handler.{handler_name}.app import lambda_handler


@pytest.fixture
def api_gateway_event():
    """Base API Gateway event fixture."""
    return {
        'httpMethod': 'GET',
        'headers': {'Authorization': 'Bearer test-token'},
        'pathParameters': None,
        'queryStringParameters': None,
        'body': None,
    }


class TestLambdaHandler:
    """Tests for {handler_name} lambda_handler."""

    @patch('handler.{handler_name}.app.extract_user_credentials')
    def test_returns_401_without_auth(self, mock_creds, api_gateway_event):
        """Handler returns 401 when no valid credentials."""
        mock_creds.return_value = (None, None, {
            'statusCode': 401,
            'body': json.dumps({'error': 'Unauthorized'})
        })
        api_gateway_event['headers'] = {}
        response = lambda_handler(api_gateway_event, None)
        assert response['statusCode'] == 401

    def test_handler_exists(self):
        """Verify handler is importable."""
        assert callable(lambda_handler)
```

### Component 5: Test Stub Creation — Frontend

**5 priority components:** `MemberAdminTable.tsx`, `MemberEditView.tsx`, `NewMemberApplicationForm.tsx`, `CustomAuthenticator.tsx`, `WebshopPage.tsx`

**Stub template:**

```typescript
// frontend/src/components/__tests__/{ComponentName}.test.tsx
import React from 'react';
import { render, screen } from '@testing-library/react';
import { ChakraProvider } from '@chakra-ui/react';
import { {ComponentName} } from '../{ComponentName}';

// Mock auth context
jest.mock('../../context/AuthContext', () => ({
  useAuth: () => ({ user: { email: 'test@h-dcn.nl' }, roles: ['hdcn_leden'] }),
}));

describe('{ComponentName}', () => {
  const renderComponent = (props = {}) =>
    render(
      <ChakraProvider>
        <{ComponentName} {...props} />
      </ChakraProvider>
    );

  it('renders without crashing', () => {
    renderComponent();
    // TODO: Add meaningful assertions
  });
});
```

### Component 6: Documentation Updates

**Approach:** For each stale document, update factual claims to match current state:

| Document                                             | Key updates needed                                                 |
| ---------------------------------------------------- | ------------------------------------------------------------------ |
| `docs/README.md`                                     | Handler count: 51 → 85; add PresMeet, product unification features |
| `docs/webshop/image-management-system.md`            | Reflect product unification rework (March 2026)                    |
| `docs/development/test-environment-setup.md`         | Add new handler setup, PresMeet config, product variants           |
| `docs/security/security-scan-report.md`              | Re-run scan metrics against current codebase                       |
| `docs/architecture/parameter-id-mapping-system.md`   | Reflect i18n and product unification changes                       |
| `docs/deployment/role-migration-deployment-guide.md` | Mark as archive candidate (migration complete)                     |

## Data Models

No data model changes. All DynamoDB tables, Cognito configuration, and S3 buckets remain unchanged.

## Error Handling

No new error paths introduced. The refactored modules preserve existing error handling patterns:

- Backend: `create_error_response(status_code, message)` from shared layer
- Frontend: Existing Chakra UI toast error patterns

The key risk is import errors after refactoring. Mitigated by:

1. Running `sam build` after backend changes to verify Lambda packaging
2. Running `npm run build:prod` after frontend changes to verify TypeScript compilation
3. Running existing test suites post-change

## Testing Strategy

**Verification approach for this maintenance spec:**

- **Backend split (hdcn_cognito_admin):** Run `sam build` to verify Lambda packaging. Run existing integration tests (`test_admin_endpoints.py`). Property test: verify all original function names remain importable.
- **Frontend split (memberFields):** Run `npm run build:prod` to verify TypeScript compilation. Property test: verify MEMBER_FIELDS key set is unchanged.
- **Role permissions consolidation:** Run `sam build`, then run existing auth-related unit tests (`test_comprehensive_auth_flows.py`, `test_auth_logging.py`). Property test: verify function availability in shared module.
- **Test stubs:** Verify stubs pass `pytest --collect-only` (backend) and `npm test -- --watchAll=false` (frontend) without import errors.
- **Documentation:** Manual review — no automated testing for doc content.

## Correctness Properties

_A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees._

### Property 1: Backend split preserves public API

_For any_ function name that was exported by the original `hdcn_cognito_admin/app.py`, the refactored module structure shall export a callable with the same name and compatible signature, and `lambda_handler` shall still dispatch to it correctly.

**Validates: Requirements 1.1**

### Property 2: Frontend split preserves field registry

_For any_ field key present in the original `MEMBER_FIELDS` object, the reassembled registry from the split files shall contain the same key with an identical `FieldDefinition` (all properties unchanged).

**Validates: Requirements 1.2**

### Property 3: Role permissions consolidation preserves function availability

_For any_ function name exported by any of the three local `role_permissions.py` copies, the consolidated `shared/role_permissions.py` module shall export a function with the same name and compatible behavior.

**Validates: Requirements 6.1**

### Property 4: Shared layer subsumes local auth utils

_For any_ function name exported by `auth_utils_local.py`, the shared layer `auth_utils.py` shall export a function with the same name and compatible signature.

**Validates: Requirements 6.2**

### Property 5: Generated test stubs are valid and importable

_For any_ generated backend test stub file, the file shall be valid Python that can be parsed without syntax errors, shall import the corresponding handler module, and shall contain at least one function whose name starts with `test_`.

**Validates: Requirements 4.3**

### Property 6: Generated frontend test stubs are valid

_For any_ generated frontend test stub file, the file shall be valid TypeScript that passes type-checking, shall import the corresponding component, and shall contain at least one `it()` or `test()` block.

**Validates: Requirements 5.4**
