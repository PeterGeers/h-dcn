# Permission System Demo Components

This directory contains demo components that showcase the new permission + region role system implementation.

## Components

### NewPermissionSystemDemo.tsx

A comprehensive demo component that displays:

- **Permission Overview**: Shows user's current permissions for members, events, and products
- **Regional Access**: Displays user's regional access level and accessible regions
- **Regional Examples**: Interactive examples showing permissions for different regions
- **Conditional UI**: Demonstrates how UI components should conditionally render based on permissions

**Usage:**

```tsx
import { NewPermissionSystemDemo } from "./components/examples/NewPermissionSystemDemo";

function App() {
  return <NewPermissionSystemDemo />;
}
```

### PermissionExample.tsx (Utility Component)

Contains utility functions and examples for implementing the new permission system:

- **usePermissions Hook**: Custom hook that provides easy access to permission checking functions
- **withPermissionCheck HOC**: Higher-order component for protecting components with permission requirements
- **Example Component**: Shows basic usage patterns for permission checking

**Key Functions:**

#### usePermissions Hook

```tsx
const {
  canReadMembers,
  canWriteMembers,
  accessibleRegions,
  hasFullRegionalAccess,
  checkPermission,
  validateMultiplePermissions,
} = usePermissions();
```

#### withPermissionCheck HOC

```tsx
const ProtectedComponent = withPermissionCheck(
  MyComponent,
  "members", // required permission
  "write", // required action
  "utrecht" // optional region
);
```

#### checkPermission Function

```tsx
const canManageUtrechtMembers = checkPermission("members", "write", "utrecht");
```

## Testing

Both components have comprehensive test suites:

- `NewPermissionSystemDemo.test.tsx`: Tests the demo component rendering and permission display
- `PermissionExample.test.tsx`: Tests the utility functions and hooks

Run tests:

```bash
npm test -- --testPathPattern="NewPermissionSystemDemo|PermissionExample"
```

## Integration with New Role Structure

These components demonstrate the new permission + region role system:

### Old Role Structure (Deprecated)

- `Members_CRUD_All`
- `Events_Read_All`
- `Products_CRUD_All`

### New Role Structure (Current)

- Permission roles: `Members_CRUD`, `Events_Read`, `Products_CRUD`
- Regional roles: `Regio_Utrecht`, `Regio_Limburg`, `Regio_All`
- Combined validation: User needs both permission AND regional access

### Example Role Combinations

1. **National Administrator**: `Members_CRUD + Regio_All`

   - Can manage all members across all regions

2. **Regional Coordinator**: `Members_CRUD + Regio_Utrecht`

   - Can manage members only in Utrecht region

3. **Read-Only User**: `Members_Read + Regio_All`

   - Can view all members but cannot modify them

4. **Export User**: `Members_Export + Regio_Utrecht`
   - Can export member data for Utrecht region only

## Implementation Patterns

### Basic Permission Check

```tsx
// Check if user can read members
const canRead = checkUIPermission(user, "members", "read");

// Check if user can write members in specific region
const canWriteUtrecht = checkUIPermission(user, "members", "write", "utrecht");
```

### Conditional Rendering

```tsx
{
  canReadMembers && (
    <div>
      <h3>Member Management</h3>
      {canWriteMembers && <button>Edit Members</button>}
      {hasExportPermission && <button>Export Data</button>}
    </div>
  );
}
```

### Regional Access Control

```tsx
const accessibleRegions = getUserAccessibleRegions(user);
const hasFullAccess = accessibleRegions.includes("all");

{
  hasFullAccess ? (
    <p>You have access to all regions</p>
  ) : (
    <ul>
      {accessibleRegions.map((region) => (
        <li key={region}>{region}</li>
      ))}
    </ul>
  );
}
```

### Multiple Permission Validation

```tsx
const canGenerateReports = validatePermissionWithRegion(
  user,
  ["members_read", "members_export"],
  "utrecht"
);
```

## Best Practices

1. **Always check both permission and region**: Use `checkUIPermission` or `userHasPermissionWithRegion`
2. **Use the usePermissions hook**: Provides convenient access to common permission checks
3. **Implement graceful fallbacks**: Show appropriate messages when permissions are insufficient
4. **Test with different role combinations**: Ensure UI works correctly for all user types
5. **Follow the principle of least privilege**: Only grant minimum necessary permissions

## Migration from Old System

When migrating from the old `_All` role system:

1. Replace `Members_CRUD_All` checks with `Members_CRUD + regional access` validation
2. Update UI components to use `checkUIPermission` instead of direct role checks
3. Add regional filtering logic where appropriate
4. Test with various role combinations to ensure proper access control

## Troubleshooting

### Common Issues

1. **User has permission but no regional access**: Ensure user has both permission role AND regional role
2. **Multiple regions showing wrong permissions**: Check that `checkPermission` function is called with correct region parameter
3. **Tests failing**: Ensure mocks return appropriate values for both permission and regional checks

### Debug Information

The demo components include debug sections that show:

- User's current roles
- Accessible regions
- Permission check results

Use these to troubleshoot permission issues during development.
