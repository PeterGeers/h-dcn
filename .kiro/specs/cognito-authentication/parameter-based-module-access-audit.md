# Parameter-Based Module Access Control - Current Implementation Audit

## Executive Summary

The H-DCN system currently implements a **function-based permission system** using AWS Cognito groups combined with parameter-driven configuration. Module access is controlled through a combination of:

1. **Cognito Groups** - User role assignments (hdcnAdmins, hdcnLeden, etc.)
2. **Function Permissions Parameter** - Stored in DynamoDB Parameters table
3. **FunctionGuard Component** - React component that enforces access control
4. **Parameter Store System** - Centralized parameter management

## Current Architecture

### 1. Permission System Components

#### A. Cognito Groups (User Roles)

- **hdcnAdmins** - Administrative users with elevated permissions
- **hdcnLeden** - Regular members with basic access
- **Regional groups** - Pattern: `hdcnRegio_*` for regional access
- **Functional groups** - Pattern: `hdcnEvents_Read`, `hdcnProducts_Write`, etc.

#### B. Function Permissions Parameter

**Location**: DynamoDB Parameters table, parameter name: `function_permissions`
**Structure**:

```json
{
  "id": "default",
  "value": {
    "members": {
      "read": ["hdcnAdmins", "hdcnRegio_*"],
      "write": ["hdcnAdmins"]
    },
    "events": {
      "read": ["hdcnAdmins", "hdcnEvents_Read"],
      "write": ["hdcnAdmins", "hdcnEvents_Write"]
    },
    "products": {
      "read": ["hdcnAdmins", "hdcnProducts_Read"],
      "write": ["hdcnAdmins", "hdcnProducts_Write"]
    },
    "orders": {
      "read": ["hdcnAdmins", "hdcnOrders_Read"],
      "write": ["hdcnAdmins", "hdcnOrders_Write"]
    },
    "webshop": {
      "read": ["hdcnLeden", "hdcnAdmins"],
      "write": ["hdcnLeden", "hdcnAdmins"]
    },
    "parameters": {
      "read": ["hdcnAdmins"],
      "write": ["hdcnAdmins"]
    },
    "memberships": {
      "read": ["hdcnAdmins"],
      "write": ["hdcnAdmins"]
    }
  }
}
```

#### C. Parameter Store System

**Files**:

- `frontend/src/utils/parameterStore.tsx` - Core parameter management
- `frontend/src/utils/parameterService.tsx` - Service layer for parameter access

**Key Features**:

- Centralized parameter caching
- S3/DynamoDB/localStorage fallback hierarchy
- Real-time parameter updates
- Category-based parameter organization

### 2. Access Control Implementation

#### A. FunctionGuard Component

**File**: `frontend/src/components/common/FunctionGuard.tsx`

**Usage Pattern**:

```tsx
<FunctionGuard user={user} functionName="members" action="read">
  <AppCard title="Ledenadministratie" onClick={() => navigate("/members")} />
</FunctionGuard>
```

**Key Features**:

- Async permission checking
- Fallback to admin-only access on errors
- Loading state management
- Configurable fallback content

#### B. FunctionPermissionManager

**File**: `frontend/src/utils/functionPermissions.ts`

**Key Methods**:

- `create(user)` - Factory method to create permission manager
- `hasAccess(functionName, action)` - Check specific permissions
- `getAccessibleFunctions()` - Get all accessible functions for user

**Permission Logic**:

- Extracts Cognito groups from JWT token
- Matches user groups against function permission requirements
- Supports wildcard patterns (e.g., `hdcnRegio_*`)
- Combines read/write permissions per function

#### C. GroupAccessGuard Component

**File**: `frontend/src/components/common/GroupAccessGuard.js`

**Purpose**:

- Prevents access to entire application if user has no Cognito groups
- Shows "Access Denied" screen for users without group assignments
- Ensures only users with assigned roles can access the system

### 3. Module Access Control Points

#### A. Dashboard Module Display

**File**: `frontend/src/pages/Dashboard.tsx`

**Current Implementation**:

- Each module card wrapped in `FunctionGuard`
- Modules hidden if user lacks required permissions
- No indication of hidden modules to users

**Modules Controlled**:

- **Webshop** - `functionName="webshop"`, `action="read"`
- **Members Admin** - `functionName="members"`, `action="read"`
- **Events Admin** - `functionName="events"`, `action="read"`
- **Products Admin** - `functionName="products"`, `action="read"`
- **Parameters** - `functionName="parameters"`, `action="read"`
- **Membership Management** - `functionName="memberships"`, `action="read"`

#### B. Route-Level Protection

**File**: `frontend/src/App.tsx`

**Current State**:

- Routes are NOT protected at the router level
- Protection only occurs at component/UI level
- Users could potentially access routes directly if they know the URL

#### C. API-Level Protection

**Backend**: Various Lambda handlers in `backend/handler/` directories

**Current State**:

- Some handlers implement Cognito group checking
- Inconsistent implementation across different endpoints
- Relies on JWT token validation and group extraction

### 4. Parameter Categories and Usage

#### A. Core Parameter Categories

**Stored in DynamoDB Parameters table**:

1. **Regio** - Regional assignments (9 regions)
2. **Lidmaatschap** - Membership types (4 types)
3. **Motormerk** - Motorcycle brands (4 brands)
4. **Clubblad** - Magazine preferences (3 options)
5. **WieWatWaar** - How members found H-DCN (12 options)
6. **Productgroepen** - Product categories (hierarchical structure)
7. **Function_permissions** - Module access control

#### B. Parameter-Based Field Restrictions

**Current Implementation**: Limited field-level restrictions based on membership type

**Examples**:

- Different fields available based on `lidmaatschap` value
- Regional restrictions based on `regio` parameter
- Administrative fields restricted to admin roles

### 5. Integration Points

#### A. Member Data Integration

**Files**:

- `frontend/src/modules/members/` - Member management module
- `frontend/src/pages/MembershipForm.tsx` - Member profile editing

**Parameter Usage**:

- Dropdown population from parameter store
- Field validation based on parameter values
- Regional filtering based on user's region assignment

#### B. Product Management Integration

**Files**:

- `frontend/src/modules/products/` - Product management module
- `frontend/src/modules/webshop/` - Webshop module

**Parameter Usage**:

- Product categorization using Productgroepen parameter
- Access control via function permissions

#### C. Event Management Integration

**Files**:

- `frontend/src/modules/events/` - Event management module

**Parameter Usage**:

- Regional event filtering
- Access control via function permissions

## Current Limitations and Issues

### 1. Inconsistent Implementation

- **Route Protection**: Routes not protected at router level
- **API Protection**: Inconsistent across different endpoints
- **Error Handling**: Limited fallback mechanisms

### 2. Limited Granularity

- **Binary Access**: Users either see modules or don't (no partial access)
- **No Field-Level Control**: Limited field-level permissions based on membership type
- **No Regional Filtering**: Regional access not fully implemented

### 3. Performance Concerns

- **Multiple API Calls**: Parameter loading requires multiple API calls
- **No Caching Strategy**: Limited caching of permission calculations
- **Synchronous Loading**: UI blocks during permission checks

### 4. Maintenance Challenges

- **Parameter Management**: Function permissions stored as JSON in parameter table
- **No Validation**: No validation of permission configurations
- **Manual Updates**: Permission changes require manual parameter updates

## Membership Type Variations

### Current Membership Types

Based on `Lidmaatschap` parameter:

1. **Gewoon lid** - Regular member
2. **Gezins lid** - Family member
3. **Gezins donateur zonder motor** - Family donor without motorcycle
4. **Donateur zonder motor** - Donor without motorcycle

### Field Access Variations

**Current Implementation**: Limited variations discovered

**Potential Variations** (to be clarified during implementation):

- Different field sets available based on membership type
- Different permission levels for data modification
- Different module access based on membership type

## Regional Access Control

### Current Regional Structure

Based on `Regio` parameter:

1. Noord-Holland
2. Zuid-Holland
3. Friesland
4. Utrecht
5. Oost
6. Limburg
7. Groningen/Drente
8. Noord-Brabant/Zeeland
9. Duitsland

### Regional Access Implementation

**Current State**:

- Regional groups supported via wildcard pattern `hdcnRegio_*`
- Limited implementation of regional filtering
- No regional data segregation in current modules

## Recommendations for Cognito Integration

### 1. Preserve Existing Functionality

- Maintain current parameter-based system
- Keep existing function permission structure
- Preserve membership type and regional parameter usage

### 2. Enhance with Role-Based System

- Add Cognito groups as additional permission layer
- Combine existing function permissions with role-based permissions
- Maintain backward compatibility

### 3. Improve Implementation Consistency

- Add route-level protection
- Standardize API-level permission checking
- Implement comprehensive error handling

### 4. Extend Granular Control

- Add field-level permissions based on roles
- Implement regional data filtering
- Add partial module access capabilities

## Integration Strategy

### Phase 1: Preserve Current System

1. Document all existing parameter dependencies
2. Ensure current function permission system continues working
3. Map existing Cognito groups to current permission structure

### Phase 2: Add Role-Based Enhancements

1. Extend FunctionPermissionManager to handle role-based permissions
2. Add role extraction from Cognito JWT tokens
3. Combine role permissions with existing function permissions

### Phase 3: Enhance Access Control

1. Add route-level protection
2. Implement field-level permissions
3. Add regional data filtering capabilities

### Phase 4: Optimize and Maintain

1. Improve caching strategies
2. Add permission validation
3. Create admin interface for permission management

## Conclusion

The current H-DCN system has a solid foundation for parameter-based module access control using Cognito groups and a centralized parameter system. The integration with the new role-based authentication system should build upon this existing infrastructure while adding enhanced granular control and improved consistency across the application.

The key success factor will be maintaining backward compatibility with existing parameter configurations while adding the flexibility and security benefits of the new role-based system.
