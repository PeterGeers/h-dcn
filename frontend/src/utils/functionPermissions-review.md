# FunctionPermissionManager Implementation Review

## Current Implementation Analysis

### Overview

The current `FunctionPermissionManager` class provides a parameter-based permission system that:

- Extracts user groups from Cognito JWT tokens (`cognito:groups`)
- Loads permission configuration from the parameter store
- Supports wildcard group patterns (e.g., `hdcnRegio_*`)
- Provides fallback configurations for admin users

### Current Architecture

#### Key Components

1. **FunctionPermissionManager Class**

   - Constructor takes user object and permission configuration
   - Static `create()` method loads permissions from parameter store
   - `hasAccess()` method checks permissions for specific functions
   - `getAccessibleFunctions()` returns all accessible functions

2. **Permission Configuration Structure**

   ```typescript
   interface PermissionConfig {
     [functionName: string]: {
       read?: string[];
       write?: string[];
     };
   }
   ```

3. **Current Group Support**
   - `hdcnAdmins` - Administrative users
   - `hdcnLeden` - Regular members
   - `hdcnRegio_*` - Regional groups (wildcard pattern)
   - Various function-specific groups (Events_Read, Products_Write, etc.)

### Current Functionality

#### Strengths

✅ **Existing JWT Token Integration**: Already extracts `cognito:groups` from user tokens
✅ **Parameter Store Integration**: Loads permissions dynamically from parameter store
✅ **Wildcard Pattern Support**: Handles regional groups with `hdcnRegio_*` pattern
✅ **Fallback Logic**: Provides admin fallback when parameter loading fails
✅ **Function-Based Access Control**: Supports read/write permissions per function
✅ **Integration with FunctionGuard**: Already used by UI components for access control

#### Current Limitations

❌ **Limited Role Mapping**: Only supports basic admin/member distinction
❌ **No Role Hierarchy**: No support for combining multiple roles
❌ **Hardcoded Fallbacks**: Fallback configurations are hardcoded in the class
❌ **No Permission Calculation**: No logic to combine permissions from multiple roles
❌ **Limited Role Types**: Only supports hdcnAdmins, hdcnLeden, and regional patterns

### Integration Points

#### Current Usage

1. **FunctionGuard Component** (`frontend/src/components/common/FunctionGuard.tsx`)

   - Uses `FunctionPermissionManager.create()` to check access
   - Supports function-based access control with read/write actions
   - Has fallback logic for admin users

2. **Parameter Store Integration**
   - Loads from `Function_permissions` parameter category
   - Uses `parameterService.getParameters()` for data loading
   - Supports initialization via `initializeFunctionPermissions.ts`

## Required Changes for Role-Based System

### 1. Add Role-Based Permission Mapping

#### New Constants Needed

```typescript
// Role-to-permission mapping based on design document
export const ROLE_PERMISSIONS = {
  // Basic member role
  hdcnLeden: {
    members: { read: ["own"], write: ["own_personal"] },
    webshop: { read: ["all"], write: ["own"] },
    events: { read: ["public"] },
  },

  // Administrative roles
  Members_CRUD_All: {
    members: { read: ["all"], write: ["all"] },
    events: { read: ["all"] },
    products: { read: ["all"] },
    communication: { read: ["all"] },
    system: { read: ["user_management"] },
  },

  Members_Read_All: {
    members: { read: ["all"] },
    events: { read: ["all"] },
    products: { read: ["all"] },
    communication: { read: ["all"] },
  },

  Members_Status_Approve: {
    members: { write: ["status"] },
  },

  // ... other roles from design document
};
```

### 2. Enhance Permission Calculation Logic

#### New Utility Functions Needed

```typescript
// Extract roles from user token
export function getUserRoles(user: User): string[] {
  return user.signInUserSession?.accessToken?.payload["cognito:groups"] || [];
}

// Calculate combined permissions from all roles
export function calculatePermissions(roles: string[]): PermissionConfig {
  const combinedPermissions: PermissionConfig = {};

  roles.forEach((role) => {
    const rolePermissions = ROLE_PERMISSIONS[role];
    if (rolePermissions) {
      // Merge permissions logic
      Object.keys(rolePermissions).forEach((functionName) => {
        if (!combinedPermissions[functionName]) {
          combinedPermissions[functionName] = { read: [], write: [] };
        }
        // Combine read/write permissions
      });
    }
  });

  return combinedPermissions;
}
```

### 3. Update FunctionPermissionManager Class

#### Required Modifications

1. **Constructor Enhancement**

   - Add role-based permission calculation
   - Preserve existing parameter-based logic
   - Combine role permissions with parameter permissions

2. **Static create() Method Updates**

   - Extract user roles using `getUserRoles()`
   - Calculate role-based permissions using `calculatePermissions()`
   - Merge with existing parameter-based permissions
   - Maintain backward compatibility

3. **Permission Checking Logic**
   - Update `hasAccess()` to handle new permission types
   - Support field-level permissions (own, all, status, etc.)
   - Maintain existing wildcard pattern support

### 4. Backward Compatibility Requirements

#### Must Preserve

✅ **Existing Parameter Store Integration**: Continue loading from parameter store
✅ **Current Group Support**: hdcnAdmins, hdcnLeden must continue working
✅ **FunctionGuard Integration**: No breaking changes to component interface
✅ **Wildcard Patterns**: Regional group patterns must continue working
✅ **Fallback Logic**: Admin fallbacks must remain functional

#### Enhancement Strategy

- **Additive Approach**: New role permissions are added to existing permissions
- **Graceful Degradation**: System works even if role mapping is incomplete
- **Migration Path**: Existing configurations continue working during transition

## Implementation Recommendations

### Phase 1: Core Infrastructure

1. Add `getUserRoles()` utility function
2. Add `ROLE_PERMISSIONS` constant with basic roles
3. Add `calculatePermissions()` function
4. Update constructor to use role-based permissions

### Phase 2: Enhanced Permission Logic

1. Update `hasAccess()` method for field-level permissions
2. Add support for 'own' record permissions
3. Enhance wildcard pattern matching for regional roles
4. Add permission caching for performance

### Phase 3: Integration and Testing

1. Update FunctionGuard component with `requiredRoles` prop
2. Test with multiple role combinations
3. Verify backward compatibility with existing configurations
4. Performance testing with permission calculation

### Phase 4: Advanced Features

1. Add permission inheritance logic
2. Implement regional permission scoping
3. Add audit logging for permission checks
4. Create admin interface for role management

## Risk Assessment

### Low Risk

- Adding utility functions (getUserRoles, calculatePermissions)
- Adding new constants (ROLE_PERMISSIONS)
- Enhancing constructor logic

### Medium Risk

- Modifying hasAccess() method logic
- Updating FunctionGuard component interface
- Changing permission calculation logic

### High Risk

- Breaking existing parameter store integration
- Changing FunctionGuard component behavior
- Modifying fallback logic

## Testing Strategy

### Unit Tests Needed

1. **getUserRoles() function**

   - Test with various JWT token structures
   - Test with missing or invalid tokens
   - Test with empty groups array

2. **calculatePermissions() function**

   - Test with single role
   - Test with multiple roles
   - Test with unknown roles
   - Test permission merging logic

3. **Enhanced FunctionPermissionManager**
   - Test role-based permission calculation
   - Test backward compatibility with existing configs
   - Test fallback scenarios
   - Test performance with multiple roles

### Integration Tests Needed

1. **FunctionGuard Component**

   - Test with new requiredRoles prop
   - Test with existing function-based access
   - Test with combined role and function permissions

2. **Parameter Store Integration**
   - Test loading role permissions from parameter store
   - Test fallback when parameter loading fails
   - Test permission caching and refresh

## Conclusion

The current `FunctionPermissionManager` implementation provides a solid foundation for role-based permissions. The main enhancements needed are:

1. **Role-based permission mapping** - Add constants and calculation logic
2. **Enhanced permission calculation** - Support multiple roles and field-level permissions
3. **Backward compatibility** - Ensure existing functionality continues working
4. **Performance optimization** - Cache calculated permissions for better performance

The implementation should follow an additive approach, preserving all existing functionality while adding new role-based capabilities.
