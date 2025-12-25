# Cognito Authentication Integration Points Analysis

## Overview

This document identifies the key integration points where the existing H-DCN parameter-based module access system needs to be enhanced to work with Cognito authentication. The analysis covers current authentication flows, permission systems, and module access controls that require updates.

## Current System Architecture

### 1. Authentication Flow

**Current State:**

- Uses AWS Amplify with Cognito User Pool (eu-west-1_VtKQHhXGN)
- Custom authenticator with passwordless authentication support
- Group-based access control via `GroupAccessGuard`
- User groups extracted from JWT token: `user.signInUserSession?.accessToken?.payload['cognito:groups']`

**Integration Points:**

- ✅ **Already integrated**: Basic Cognito authentication with group extraction
- ✅ **Already integrated**: Group-based access guard preventing access for users without groups
- 🔄 **Needs enhancement**: Role-based permission calculation from multiple groups
- 🔄 **Needs enhancement**: Session management for role changes

### 2. Permission System Architecture

#### Current FunctionPermissionManager (`frontend/src/utils/functionPermissions.ts`)

**Current State:**

- Extracts Cognito groups from user JWT token
- Loads function permissions from parameter store (`Function_permissions` category)
- Supports wildcard group patterns (e.g., `hdcnRegio_*`)
- Provides `hasAccess(functionName, action)` method

**Integration Points:**

- ✅ **Already integrated**: Cognito group extraction from JWT tokens
- ✅ **Already integrated**: Parameter-based permission configuration
- 🔄 **Needs enhancement**: Role-to-permission mapping for new H-DCN organizational structure
- 🔄 **Needs enhancement**: Multiple role permission combination logic
- 🔄 **Needs enhancement**: Field-level permission calculation

#### Current FunctionGuard Component (`frontend/src/components/common/FunctionGuard.tsx`)

**Current State:**

- Uses `FunctionPermissionManager` for access control
- Supports read/write action permissions
- Provides fallback content for unauthorized access

**Integration Points:**

- ✅ **Already integrated**: Basic role-based access control
- 🔄 **Needs enhancement**: Support for `requiredRoles` prop
- 🔄 **Needs enhancement**: Combined permission checking (membership AND roles)

### 3. Parameter System Integration

#### Parameter Store (`frontend/src/utils/parameterStore.tsx`)

**Current State:**

- Manages configuration parameters from DynamoDB via API
- Supports categories: Regio, Lidmaatschap, Motormerk, Clubblad, WieWatWaar, Function_permissions
- Provides caching and localStorage fallback
- Uses API service for parameter CRUD operations

**Integration Points:**

- ✅ **Already integrated**: Function permissions stored in parameter system
- 🔄 **Needs enhancement**: Role-based parameter access control
- 🔄 **Needs enhancement**: Regional parameter filtering based on user roles
- 🔄 **Needs enhancement**: Dynamic parameter visibility based on user permissions

#### Parameter Service (`frontend/src/utils/parameterService.tsx`)

**Current State:**

- Provides React hooks for parameter consumption
- Handles parameter loading and caching
- Supports category-specific parameter retrieval

**Integration Points:**

- ✅ **Already integrated**: Basic parameter loading
- 🔄 **Needs enhancement**: User-context-aware parameter filtering
- 🔄 **Needs enhancement**: Role-based parameter visibility

### 4. Module Access Control

#### Current Module Structure

**Modules with existing access control:**

- **Members Module** (`frontend/src/modules/members/MemberAdminPage.tsx`)

  - Currently uses basic authentication check
  - Needs role-based field visibility
  - Needs regional access restrictions

- **Events Module** (`frontend/src/modules/events/EventAdminPage.tsx`)

  - Currently uses basic authentication check
  - Needs role-based event management permissions

- **Products Module** (`frontend/src/modules/products/ProductManagementPage.tsx`)

  - Currently uses basic authentication check
  - Needs role-based product management access

- **Webshop Module** (`frontend/src/modules/webshop/WebshopPage.tsx`)
  - Currently accessible to all authenticated users
  - Needs to maintain broad access while adding role-based features

**Integration Points:**

- 🔄 **Needs enhancement**: Role-based module visibility in navigation
- 🔄 **Needs enhancement**: Field-level permissions within modules
- 🔄 **Needs enhancement**: Regional access restrictions
- 🔄 **Needs enhancement**: Action-based permissions (read/write/admin)

### 5. User Interface Integration

#### Navigation Header (`frontend/src/App.tsx`)

**Current State:**

- Shows user's first name from Cognito attributes
- Basic navigation with profile and logout options

**Integration Points:**

- 🔄 **Needs enhancement**: Display email address instead of name
- 🔄 **Needs enhancement**: Clickable email with role/permission popup
- 🔄 **Needs enhancement**: Role indicator badges for admin users

#### User Context and Session Management

**Current State:**

- Basic user object from Cognito
- Limited role information extraction
- No centralized permission calculation

**Integration Points:**

- 🔄 **Needs enhancement**: Enhanced user context with roles and permissions
- 🔄 **Needs enhancement**: Centralized permission calculation service
- 🔄 **Needs enhancement**: Session updates when roles change
- 🔄 **Needs enhancement**: Permission caching for performance

## Specific Integration Requirements

### 1. Role-Based Permission System Enhancement

**Current Implementation:**

```typescript
// Existing: Basic group-based access
const userGroups =
  user.signInUserSession?.accessToken?.payload["cognito:groups"] || [];
const hasAccess = userGroups.includes("hdcnAdmins");
```

**Required Enhancement:**

```typescript
// New: Role-based permission calculation
const getUserRoles = (user) => {
  return user.signInUserSession?.accessToken?.payload["cognito:groups"] || [];
};

const calculatePermissions = (roles) => {
  // Combine permissions from all assigned roles
  // Handle role hierarchy and conflicts
  // Return deduplicated permission list
};
```

### 2. Field-Level Permission Integration

**Current Implementation:**

- No field-level restrictions
- All authenticated users can edit all fields

**Required Enhancement:**

- Personal fields editable by members for own record
- Motorcycle fields editable by members for own record
- Administrative fields restricted to admin roles
- Status field restricted to Members_CRUD_All role

### 3. Parameter System Role Integration

**Current Implementation:**

```typescript
// Existing: Load all parameters for all users
const parameters = await getParameters();
```

**Required Enhancement:**

```typescript
// New: Role-based parameter filtering
const getParametersForUser = async (user) => {
  const roles = getUserRoles(user);
  const permissions = calculatePermissions(roles);
  return filterParametersByPermissions(parameters, permissions);
};
```

### 4. Module Access Control Integration

**Current Implementation:**

```typescript
// Existing: Basic authentication check
if (!user) return <LoginRequired />;
```

**Required Enhancement:**

```typescript
// New: Role-based module access
<FunctionGuard
  user={user}
  functionName="members"
  action="read"
  requiredRoles={["Members_Read_All", "Members_CRUD_All"]}
>
  <MemberModule />
</FunctionGuard>
```

## Migration Strategy

### Phase 1: Core Integration (MVP-2)

1. **Enhance FunctionPermissionManager** with role-based logic
2. **Update FunctionGuard** to support role requirements
3. **Modify user context** to include roles and permissions
4. **Update navigation header** to show email and role indicators

### Phase 2: Module Integration (MVP-2 continued)

1. **Update member module** with field-level permissions
2. **Update events module** with role-based access
3. **Update products module** with role-based access
4. **Update parameter module** with admin-only access

### Phase 3: Advanced Features (Later phases)

1. **Regional access restrictions** based on user roles
2. **Advanced export permissions** based on roles
3. **Audit logging** for permission-based actions
4. **Performance optimization** with permission caching

## Backward Compatibility Requirements

### Existing Functionality to Preserve

1. **Parameter-based module visibility** - existing parameter configurations must continue to work
2. **Membership type restrictions** - existing membership-based field restrictions must be preserved
3. **Group-based access patterns** - existing wildcard group patterns (`hdcnRegio_*`) must continue to work
4. **API compatibility** - existing API endpoints and data structures must remain functional

### Integration Approach

- **Additive permissions**: New role-based permissions should be additive to existing permissions
- **Fallback behavior**: If role-based permissions fail, fall back to existing group-based permissions
- **Gradual migration**: Allow both old and new permission systems to coexist during transition

## Technical Implementation Notes

### Key Files Requiring Updates

1. `frontend/src/utils/functionPermissions.ts` - Core permission logic
2. `frontend/src/components/common/FunctionGuard.tsx` - Access control component
3. `frontend/src/context/AuthContext.tsx` - User context management
4. `frontend/src/hooks/useAuth.ts` - Authentication hook
5. `frontend/src/App.tsx` - Navigation and user interface
6. Module-specific files for field-level permissions

### New Files to Create

1. `frontend/src/utils/rolePermissions.ts` - Role-to-permission mapping
2. `frontend/src/components/common/AccountDetailsPopup.tsx` - User role/permission display
3. `frontend/src/hooks/usePermissions.ts` - Permission calculation hook
4. `frontend/src/utils/fieldPermissions.ts` - Field-level permission logic

### API Integration Points

- **Existing**: Parameter API for function permissions
- **New**: Enhanced permission calculation with role combinations
- **New**: Field-level permission validation
- **New**: Regional access filtering

## Conclusion

The existing H-DCN system already has a solid foundation for Cognito integration with basic group-based access control and parameter-driven permissions. The main integration work involves:

1. **Enhancing** the existing permission system to handle multiple roles and complex permission combinations
2. **Adding** field-level permissions for granular access control
3. **Updating** the user interface to display role information and provide better user experience
4. **Preserving** existing functionality while adding new role-based capabilities

The integration can be implemented incrementally, allowing the system to maintain backward compatibility while gradually adopting the new role-based permission model.
