# Permission + Region Role System Implementation

## Overview

The frontend permission system supports the permission + region role combinations, replacing the deprecated `_All` roles that no longer exist in Cognito.

## Key Changes Made

### 1. Updated Type Definitions (`frontend/src/types/user.ts`)

- **Removed**: Deprecated `_All` roles (`Members_CRUD_All`, `Events_CRUD_All`, etc.)
- **Added**: Permission roles (`Members_CRUD`, `Members_Read`, `Members_Export`, etc.)
- **Added**: Regional roles (`Regio_Utrecht`, `Regio_Limburg`, etc.)
- **Kept**: `Regio_All` (the only `_All` role that still exists)
- **Kept**: Roles for compatibility

### 2. Enhanced Permission Functions (`frontend/src/utils/functionPermissions.ts`)

#### New Core Functions:

1. **`userHasPermissionWithRegion(user, requiredPermission, targetRegion?)`**

   - Checks if user has both the required permission AND regional access
   - Example: `userHasPermissionWithRegion(user, 'members_crud', 'utrecht')`

2. **`getUserAccessibleRegions(user)`**

   - Returns array of regions the user can access
   - Returns `['all']` for users with `Regio_All` role

3. **`userHasPermissionType(user, permissionType, action)`**

   - Checks if user has specific permission type (without region requirement)
   - Example: `userHasPermissionType(user, 'members', 'crud')`

4. **`validatePermissionWithRegion(user, requiredPermissions[], targetRegion?)`**

   - Validates multiple permissions at once
   - Example: `validatePermissionWithRegion(user, ['members_read', 'members_export'], 'utrecht')`

5. **`checkUIPermission(user, functionName, action, targetRegion?)`**
   - **Main function for UI components** - use this for most permission checks
   - Example: `checkUIPermission(user, 'members', 'write', 'utrecht')`

#### Updated Configuration:

- **`ROLE_PERMISSIONS`**: Updated to use current role structure
- **`DEFAULT_FUNCTION_PERMISSIONS`**: Updated for current roles
- **Compatibility**: Admin roles still work

### 3. Comprehensive Test Suite

Created `frontend/src/utils/__tests__/functionPermissions.test.ts` with tests covering:

- Permission type checking
- Regional access validation
- Multiple permission validation
- UI permission checking
- Legacy admin compatibility

## How to Use the System

### Basic Permission Checks

```typescript
import { checkUIPermission } from "../utils/functionPermissions";
import { useAuth } from "../hooks/useAuth";

const MyComponent = () => {
  const { user } = useAuth();

  // Check if user can read members
  const canReadMembers = checkUIPermission(user, "members", "read");

  // Check if user can write members in Utrecht region
  const canManageUtrecht = checkUIPermission(
    user,
    "members",
    "write",
    "utrecht"
  );

  return (
    <div>
      {canReadMembers && <button>View Members</button>}
      {canManageUtrecht && <button>Manage Utrecht Members</button>}
    </div>
  );
};
```

### Regional Access Patterns

```typescript
import {
  getUserAccessibleRegions,
  checkUIPermission,
} from "../utils/functionPermissions";

const RegionalComponent = () => {
  const { user } = useAuth();
  const accessibleRegions = getUserAccessibleRegions(user);

  return (
    <div>
      {accessibleRegions.includes("all") ? (
        <p>Full national access</p>
      ) : (
        <ul>
          {accessibleRegions.map((region) => (
            <li key={region}>
              {region}
              {checkUIPermission(user, "events", "write", region) && (
                <button>Manage {region} Events</button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};
```

### Custom Permission Hook

```typescript
import { usePermissions } from "../utils/examples/PermissionExample";

const DashboardComponent = () => {
  const {
    canReadMembers,
    canWriteMembers,
    accessibleRegions,
    hasFullRegionalAccess,
    checkPermission,
  } = usePermissions();

  return (
    <div>
      {canReadMembers && <MembersList />}
      {canWriteMembers && <MemberEditor />}
      {hasFullRegionalAccess && <NationalReports />}
      {checkPermission("events", "write", "utrecht") && <UtrechtEventManager />}
    </div>
  );
};
```

## Role Combinations That Work

### Valid Permission + Region Combinations:

- `Members_CRUD + Regio_All` → Full member management, all regions
- `Members_CRUD + Regio_Utrecht` → Member management in Utrecht only
- `Members_Read + Regio_All` → Read all members, all regions
- `Members_Export + Regio_Limburg` → Export members from Limburg only
- `Events_CRUD + Regio_All` → Event management, all regions

### Invalid Combinations (Will Be Denied):

- `Members_CRUD` (missing region role)
- `Regio_Utrecht` (missing permission role)
- `Members_Read + Events_CRUD` (missing region role)

## Migration Guide for Existing Components

### Before (Deprecated System):

```typescript
// Deprecated way - checking for _All roles
const canManageMembers = userHasRole(user, "Members_CRUD_All");
```

### After (Current System):

```typescript
// Current way - checking permission + region combination
const canManageMembers = checkUIPermission(user, "members", "write");
const canManageUtrechtMembers = checkUIPermission(
  user,
  "members",
  "write",
  "utrecht"
);
```

## Compatibility

- **Admin roles** (`hdcnAdmins`) still work and grant full access
- **Regional roles** (`hdcnRegio_*`) are mapped to current structure
- **Existing components** will continue to work during transition period

## Testing

Run the test suite to verify the implementation:

```bash
npm test -- --testPathPattern=functionPermissions.test.ts --watchAll=false
```

All 16 tests should pass, covering:

- ✅ Permission type validation
- ✅ Regional access control
- ✅ Multiple permission validation
- ✅ UI permission checking
- ✅ Legacy compatibility

## Next Steps

1. **Update existing components** to use `checkUIPermission()` instead of deprecated role checks
2. **Remove deprecated `_All` role references** from component code
3. **Test with real users** who have the current role combinations
4. **Update documentation** for developers using the permission system

## Key Benefits

- ✅ **Supports role structure**: Works with permission + region combinations
- ✅ **Compatible**: Admin roles still work
- ✅ **Type safe**: Full TypeScript support
- ✅ **Well tested**: Comprehensive test coverage
- ✅ **Easy to use**: Simple API for common use cases
- ✅ **Flexible**: Supports complex permission scenarios
- ✅ **Regional filtering**: Built-in support for regional access control
