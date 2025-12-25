# AWS Cognito Access Control Design Proposal
## H-DCN Portal - Function-Level Permissions

### Executive Summary
This proposal outlines three design options for implementing granular access control using AWS Cognito groups to limit user access to specific functions within the H-DCN Portal, including read-only access capabilities.

---

## Current State Analysis

### Existing Group Structure
- **No Groups**: Registration only, blocked by GroupAccessGuard
- **hdcnLeden**: Basic member access (webshop, profile)
- **hdcnAdmins**: Full administrative access

### Current Limitations
- Binary access control (all or nothing per module)
- No function-level permissions
- No read-only access capabilities
- Limited scalability for new roles

---

## Design Options

### Option 1: Hierarchical Group Structure
**Concept**: Create nested permission groups with inheritance

#### Group Structure
```
hdcnGuests          → Registration only
hdcnLeden           → Basic member functions
hdcnLedenPlus       → Extended member functions
hdcnModerators      → Limited admin functions (read-only)
hdcnAdmins          → Full admin access
hdcnSuperAdmins     → System-level access
```

#### Implementation
```javascript
// Permission hierarchy mapping
const PERMISSION_HIERARCHY = {
  'hdcnGuests': ['membership:create'],
  'hdcnLeden': ['webshop:read', 'webshop:order', 'profile:read', 'profile:write'],
  'hdcnLedenPlus': ['events:read', 'events:register'],
  'hdcnModerators': ['members:read', 'events:read', 'products:read', 'orders:read'],
  'hdcnAdmins': ['*:*'], // Full access
  'hdcnSuperAdmins': ['system:*', 'cognito:*']
};

// Access control function
function hasPermission(userGroups, requiredPermission) {
  return userGroups.some(group => 
    PERMISSION_HIERARCHY[group]?.includes(requiredPermission) ||
    PERMISSION_HIERARCHY[group]?.includes('*:*')
  );
}
```

**Pros**: Clear hierarchy, easy to understand, scalable
**Cons**: Complex group management, potential over-engineering

---

### Option 2: Function-Based Permission Groups
**Concept**: Create specific groups for each function with read/write variants

#### Group Structure
```
// Core access groups
hdcnLeden                    → Basic member access
hdcnAdmins                   → Administrative access

// Function-specific groups
hdcnMembers_Read            → View member data
hdcnMembers_Write           → Manage members
hdcnEvents_Read             → View events
hdcnEvents_Write            → Manage events
hdcnProducts_Read           → View products
hdcnProducts_Write          → Manage products
hdcnOrders_Read             → View orders
hdcnOrders_Write            → Process orders
hdcnFinance_Read            → View financial data
hdcnFinance_Write           → Manage finances
```

#### Implementation
```javascript
// Permission checker utility
class PermissionManager {
  constructor(userGroups) {
    this.userGroups = userGroups || [];
  }

  canRead(module) {
    return this.userGroups.includes(`hdcn${module}_Read`) || 
           this.userGroups.includes(`hdcn${module}_Write`) ||
           this.userGroups.includes('hdcnAdmins');
  }

  canWrite(module) {
    return this.userGroups.includes(`hdcn${module}_Write`) ||
           this.userGroups.includes('hdcnAdmins');
  }

  hasBasicAccess() {
    return this.userGroups.includes('hdcnLeden') || 
           this.userGroups.includes('hdcnAdmins');
  }
}

// Component usage
function MemberManagement({ user }) {
  const permissions = new PermissionManager(
    user.signInUserSession?.accessToken?.payload['cognito:groups']
  );

  if (!permissions.canRead('Members')) {
    return <AccessDenied />;
  }

  return (
    <Box>
      <MemberList readOnly={!permissions.canWrite('Members')} />
      {permissions.canWrite('Members') && <AddMemberButton />}
    </Box>
  );
}
```

**Pros**: Granular control, clear separation, flexible
**Cons**: Many groups to manage, potential group explosion

---

### Option 3: Role-Based with Permission Attributes
**Concept**: Use fewer groups with permission attributes stored in user attributes

#### Group Structure
```
hdcnLeden           → Basic members
hdcnModerators      → Read-only administrators
hdcnAdmins          → Full administrators
hdcnSuperAdmins     → System administrators
```

#### User Attributes for Permissions
```javascript
// Custom user attributes in Cognito
custom:permissions = "members:read,events:read,products:write,orders:read"
custom:modules = "members,events,products,orders"
custom:access_level = "read" | "write" | "admin"
```

#### Implementation
```javascript
class AttributePermissionManager {
  constructor(user) {
    this.userGroups = user.signInUserSession?.accessToken?.payload['cognito:groups'] || [];
    this.permissions = user.attributes?.['custom:permissions']?.split(',') || [];
    this.accessLevel = user.attributes?.['custom:access_level'] || 'read';
  }

  canAccess(module, action = 'read') {
    // Admin override
    if (this.userGroups.includes('hdcnAdmins')) return true;
    
    // Check specific permission
    const permission = `${module}:${action}`;
    if (this.permissions.includes(permission)) return true;
    
    // Check wildcard permissions
    if (this.permissions.includes(`${module}:*`)) return true;
    if (this.permissions.includes('*:*')) return true;
    
    // Default access level check
    if (action === 'read' && ['read', 'write', 'admin'].includes(this.accessLevel)) {
      return this.permissions.some(p => p.startsWith(`${module}:`));
    }
    
    return false;
  }
}

// Higher-order component for permission checking
function withPermissions(WrappedComponent, requiredModule, requiredAction = 'read') {
  return function PermissionWrapper(props) {
    const permissions = new AttributePermissionManager(props.user);
    
    if (!permissions.canAccess(requiredModule, requiredAction)) {
      return <AccessDenied module={requiredModule} action={requiredAction} />;
    }
    
    return (
      <WrappedComponent 
        {...props} 
        permissions={permissions}
        readOnly={!permissions.canAccess(requiredModule, 'write')}
      />
    );
  };
}

// Usage
const MemberManagement = withPermissions(MemberManagementComponent, 'members', 'read');
```

**Pros**: Flexible, fewer groups, dynamic permissions
**Cons**: Complex attribute management, requires custom UI for permission assignment

---

## Recommended Implementation: Option 2 (Function-Based Groups)

### Rationale
- **Clarity**: Clear separation between read and write permissions
- **Scalability**: Easy to add new functions without restructuring
- **AWS Native**: Uses standard Cognito groups without custom attributes
- **Maintainability**: Simple to understand and debug

### Implementation Plan

#### Phase 1: Core Permission System
```javascript
// src/utils/permissionManager.js
export class PermissionManager {
  constructor(userGroups = []) {
    this.userGroups = userGroups;
    this.isAdmin = userGroups.includes('hdcnAdmins');
    this.isMember = userGroups.includes('hdcnLeden');
  }

  // Module access checks
  canReadMembers() { return this.isAdmin || this.userGroups.includes('hdcnMembers_Read'); }
  canWriteMembers() { return this.isAdmin || this.userGroups.includes('hdcnMembers_Write'); }
  
  canReadEvents() { return this.isAdmin || this.userGroups.includes('hdcnEvents_Read'); }
  canWriteEvents() { return this.isAdmin || this.userGroups.includes('hdcnEvents_Write'); }
  
  canReadProducts() { return this.isAdmin || this.userGroups.includes('hdcnProducts_Read'); }
  canWriteProducts() { return this.isAdmin || this.userGroups.includes('hdcnProducts_Write'); }
  
  canReadOrders() { return this.isAdmin || this.userGroups.includes('hdcnOrders_Read'); }
  canWriteOrders() { return this.isAdmin || this.userGroups.includes('hdcnOrders_Write'); }

  // Webshop access (members only)
  canUseWebshop() { return this.isMember || this.isAdmin; }
}
```

#### Phase 2: Component Integration
```javascript
// src/components/PermissionGuard.js
export function PermissionGuard({ 
  user, 
  children, 
  module, 
  action = 'read',
  fallback = <AccessDenied /> 
}) {
  const permissions = new PermissionManager(
    user.signInUserSession?.accessToken?.payload['cognito:groups']
  );

  const methodName = `can${action.charAt(0).toUpperCase() + action.slice(1)}${module}`;
  const hasPermission = permissions[methodName]?.();

  return hasPermission ? children : fallback;
}

// Usage in components
<PermissionGuard user={user} module="Members" action="read">
  <MembersList />
</PermissionGuard>

<PermissionGuard user={user} module="Members" action="write">
  <AddMemberButton />
</PermissionGuard>
```

#### Phase 3: Read-Only Component Pattern
```javascript
// src/components/ReadOnlyWrapper.js
export function ReadOnlyWrapper({ children, isReadOnly }) {
  if (isReadOnly) {
    return (
      <Box position="relative">
        {children}
        <Box
          position="absolute"
          top={0}
          left={0}
          right={0}
          bottom={0}
          bg="blackAlpha.100"
          pointerEvents="none"
          display="flex"
          alignItems="center"
          justifyContent="center"
        >
          <Badge colorScheme="orange">Read Only</Badge>
        </Box>
      </Box>
    );
  }
  return children;
}

// Component implementation
function MemberManagement({ user }) {
  const permissions = new PermissionManager(
    user.signInUserSession?.accessToken?.payload['cognito:groups']
  );

  return (
    <PermissionGuard user={user} module="Members" action="read">
      <Box>
        <ReadOnlyWrapper isReadOnly={!permissions.canWriteMembers()}>
          <MemberForm />
        </ReadOnlyWrapper>
        
        {permissions.canWriteMembers() && (
          <Button colorScheme="orange">Add Member</Button>
        )}
      </Box>
    </PermissionGuard>
  );
}
```

### Required Cognito Groups Setup
```bash
# Create function-specific groups in AWS Cognito
aws cognito-idp create-group --group-name hdcnMembers_Read --user-pool-id <pool-id>
aws cognito-idp create-group --group-name hdcnMembers_Write --user-pool-id <pool-id>
aws cognito-idp create-group --group-name hdcnEvents_Read --user-pool-id <pool-id>
aws cognito-idp create-group --group-name hdcnEvents_Write --user-pool-id <pool-id>
aws cognito-idp create-group --group-name hdcnProducts_Read --user-pool-id <pool-id>
aws cognito-idp create-group --group-name hdcnProducts_Write --user-pool-id <pool-id>
aws cognito-idp create-group --group-name hdcnOrders_Read --user-pool-id <pool-id>
aws cognito-idp create-group --group-name hdcnOrders_Write --user-pool-id <pool-id>
```

### Migration Strategy
1. **Phase 1**: Implement permission system alongside existing groups
2. **Phase 2**: Update components to use new permission checks
3. **Phase 3**: Create new Cognito groups and assign users
4. **Phase 4**: Remove old binary access checks
5. **Phase 5**: Add read-only UI indicators and restrictions

### Benefits
- **Granular Control**: Function-level permissions
- **Read-Only Access**: Perfect for auditors, moderators, or training
- **Scalable**: Easy to add new functions and permissions
- **User-Friendly**: Clear visual indicators for read-only access
- **Backward Compatible**: Existing admin users retain full access

### Conclusion
This design provides the flexibility needed for the H-DCN Portal while maintaining simplicity and AWS Cognito best practices. The function-based group approach offers the best balance of control, maintainability, and user experience.