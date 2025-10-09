# Function-Level Permissions Design Options

## Option 1: Parameter Table Approach (Recommended)

### Parameter Structure
```json
{
  "name": "function_permissions",
  "value": {
    "members": {
      "read": ["hdcnAdmins", "hdcnMembers_Read", "hdcnRegio_*"],
      "write": ["hdcnAdmins", "hdcnMembers_Write"]
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
    }
  }
}
```

### Implementation
```javascript
// src/utils/functionPermissions.js
class FunctionPermissionManager {
  constructor(user, permissionConfig) {
    this.userGroups = user.signInUserSession?.accessToken?.payload['cognito:groups'] || [];
    this.permissions = permissionConfig;
  }

  hasAccess(functionName, action = 'read') {
    const functionPerms = this.permissions[functionName];
    if (!functionPerms) return false;

    const allowedGroups = functionPerms[action] || [];
    
    return this.userGroups.some(userGroup => {
      return allowedGroups.some(allowedGroup => {
        // Handle wildcard patterns like hdcnRegio_*
        if (allowedGroup.endsWith('*')) {
          const prefix = allowedGroup.slice(0, -1);
          return userGroup.startsWith(prefix);
        }
        return userGroup === allowedGroup;
      });
    });
  }

  static async create(user) {
    const config = await parameterService.getParameter('function_permissions');
    return new FunctionPermissionManager(user, config?.value || {});
  }
}

// Usage
const permissions = await FunctionPermissionManager.create(user);
const canReadMembers = permissions.hasAccess('members', 'read');
const canWriteEvents = permissions.hasAccess('events', 'write');
```

## Option 2: Cognito Group Description Approach

### Group Structure with JSON in Description
```bash
# Create groups with permissions in description
aws cognito-idp create-group \
  --group-name hdcnMembers_Read \
  --description '{"functions":{"members":"read","events":"read"}}'

aws cognito-idp create-group \
  --group-name hdcnAdmins \
  --description '{"functions":{"*":"write"}}'
```

### Implementation
```javascript
// src/utils/groupPermissions.js
class GroupPermissionManager {
  constructor(user) {
    this.userGroups = user.signInUserSession?.accessToken?.payload['cognito:groups'] || [];
    this.groupPermissions = new Map();
  }

  async loadGroupPermissions() {
    // Fetch group details from Cognito
    for (const groupName of this.userGroups) {
      const groupDetails = await cognitoService.getGroup(groupName);
      try {
        const permissions = JSON.parse(groupDetails.Description || '{}');
        this.groupPermissions.set(groupName, permissions.functions || {});
      } catch (e) {
        console.warn(`Invalid permissions for group ${groupName}`);
      }
    }
  }

  hasAccess(functionName, action = 'read') {
    for (const [groupName, functions] of this.groupPermissions) {
      // Check wildcard access
      if (functions['*'] === 'write' || functions['*'] === action) {
        return true;
      }
      
      // Check specific function access
      const functionAccess = functions[functionName];
      if (functionAccess === 'write' || functionAccess === action) {
        return true;
      }
    }
    return false;
  }
}
```

## Option 3: Custom User Attributes Approach

### User Attributes Structure
```javascript
// Custom attributes per user
custom:function_permissions = "members:read,events:write,products:read"
custom:access_level = "regional" // or "admin", "member"
```

### Implementation
```javascript
// src/utils/attributePermissions.js
class AttributePermissionManager {
  constructor(user) {
    this.userGroups = user.signInUserSession?.accessToken?.payload['cognito:groups'] || [];
    this.functionPermissions = this.parsePermissions(
      user.attributes?.['custom:function_permissions'] || ''
    );
    this.accessLevel = user.attributes?.['custom:access_level'] || 'member';
  }

  parsePermissions(permissionString) {
    const permissions = {};
    permissionString.split(',').forEach(perm => {
      const [func, access] = perm.split(':');
      if (func && access) {
        permissions[func] = access;
      }
    });
    return permissions;
  }

  hasAccess(functionName, action = 'read') {
    // Admin override
    if (this.userGroups.includes('hdcnAdmins')) return true;
    
    // Check specific function permission
    const functionAccess = this.functionPermissions[functionName];
    return functionAccess === 'write' || functionAccess === action;
  }
}
```

## Recommended Implementation: Parameter Table + Component Integration

### Complete Implementation
```javascript
// src/components/FunctionGuard.js
import { useState, useEffect } from 'react';
import { FunctionPermissionManager } from '../utils/functionPermissions';

export function FunctionGuard({ 
  user, 
  children, 
  functionName, 
  action = 'read',
  fallback = null 
}) {
  const [hasAccess, setHasAccess] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkAccess = async () => {
      try {
        const permissions = await FunctionPermissionManager.create(user);
        setHasAccess(permissions.hasAccess(functionName, action));
      } catch (error) {
        console.error('Permission check failed:', error);
        setHasAccess(false);
      } finally {
        setLoading(false);
      }
    };

    checkAccess();
  }, [user, functionName, action]);

  if (loading) return <div>Loading...</div>;
  return hasAccess ? children : fallback;
}

// Usage in components
<FunctionGuard user={user} functionName="members" action="read">
  <MembersList />
</FunctionGuard>

<FunctionGuard user={user} functionName="members" action="write">
  <AddMemberButton />
</FunctionGuard>
```

### Parameter Management Integration
```javascript
// Add to ParameterManagement.js
const functionPermissionsTemplate = {
  name: 'function_permissions',
  type: 'object',
  description: 'Function-level access permissions',
  value: {
    members: { read: ['hdcnAdmins'], write: ['hdcnAdmins'] },
    events: { read: ['hdcnAdmins'], write: ['hdcnAdmins'] },
    products: { read: ['hdcnAdmins'], write: ['hdcnAdmins'] },
    orders: { read: ['hdcnAdmins'], write: ['hdcnAdmins'] },
    webshop: { read: ['hdcnLeden'], write: ['hdcnLeden'] }
  }
};
```

## Benefits of Parameter Table Approach

✅ **Centralized Management**: All permissions in one place
✅ **Dynamic Updates**: No code changes needed
✅ **Wildcard Support**: `hdcnRegio_*` patterns
✅ **Audit Trail**: Parameter changes are logged
✅ **UI Management**: Can be managed through Parameter Management module
✅ **Flexible**: Easy to add new functions and groups
✅ **Performance**: Cached parameter lookups

## Migration Strategy

1. **Phase 1**: Create `function_permissions` parameter
2. **Phase 2**: Implement `FunctionPermissionManager`
3. **Phase 3**: Add `FunctionGuard` components
4. **Phase 4**: Update existing components to use guards
5. **Phase 5**: Add UI for permission management in admin panel