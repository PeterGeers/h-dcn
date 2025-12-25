# H-DCN Permission System Compatibility Matrix

## Overview

This document maps the existing parameter-based permission system to the new role-based authentication system, ensuring backward compatibility while enabling enhanced role-based access control.

## Current System Analysis

### Existing Permission Structure

**Current Groups (from existing system):**

- `hdcnAdmins` - Administrative access to all functions
- `hdcnLeden` - Basic member access (webshop, own data)
- `hdcnRegio_*` - Regional access patterns (wildcard matching)
- `hdcnEvents_Read` / `hdcnEvents_Write` - Event-specific permissions
- `hdcnProducts_Read` / `hdcnProducts_Write` - Product-specific permissions
- `hdcnOrders_Read` / `hdcnOrders_Write` - Order-specific permissions

**Current Function Permissions (from FunctionPermissionManager):**

```typescript
{
  members: {
    read: ['hdcnAdmins', 'hdcnRegio_*'],
    write: ['hdcnAdmins']
  },
  events: {
    read: ['hdcnAdmins', 'hdcnEvents_Read'],
    write: ['hdcnAdmins', 'hdcnEvents_Write']
  },
  products: {
    read: ['hdcnAdmins', 'hdcnProducts_Read'],
    write: ['hdcnAdmins', 'hdcnProducts_Write']
  },
  orders: {
    read: ['hdcnAdmins', 'hdcnOrders_Read'],
    write: ['hdcnAdmins', 'hdcnOrders_Write']
  },
  webshop: {
    read: ['hdcnLeden', 'hdcnAdmins'],
    write: ['hdcnLeden', 'hdcnAdmins']
  },
  parameters: {
    read: ['hdcnAdmins'],
    write: ['hdcnAdmins']
  },
  memberships: {
    read: ['hdcnAdmins'],
    write: ['hdcnAdmins']
  }
}
```

**Current Parameter-Based Module Access:**

- Module visibility controlled by Parameters table
- Dynamic evaluation based on membership type, region, and custom flags
- Parameter types: `Regio`, `Lidmaatschap`, `Motormerk`, `Clubblad`
- Evaluation completes within 500ms requirement

## New Role-Based System

### New Cognito Groups (Roles)

**Basic Member Role:**

- `hdcnLeden` (precedence: 100) - Regular members

**Member Management Roles:**

- `Members_CRUD_All` (precedence: 10) - Full member management
- `Members_Read_All` (precedence: 20) - View all member data
- `Members_Status_Approve` (precedence: 15) - Approve member status changes

**Event Management Roles:**

- `Events_Read_All` (precedence: 30) - View all events
- `Events_CRUD_All` (precedence: 25) - Full event management

**Product Management Roles:**

- `Products_Read_All` (precedence: 40) - View all products
- `Products_CRUD_All` (precedence: 35) - Full product management

**Communication Roles:**

- `Communication_Read_All` (precedence: 50) - View all communications
- `Communication_Export_All` (precedence: 45) - Export communication data

**System Administration Roles:**

- `System_User_Management` (precedence: 5) - User and role management
- `System_Logs_Read` (precedence: 55) - View system logs

**Regional Roles (per region):**

- `Members_Read_Region{N}` - View region-specific member data
- `Members_Export_Region{N}` - Export region-specific data
- `Events_Read_Region{N}` - View region-specific events
- `Events_CRUD_Region{N}` - Manage region-specific events
- `Communication_Export_Region{N}` - Export region communications

## Compatibility Mapping

### 1. Direct Group Mappings

| Existing Group       | New Role(s)                                                                             | Migration Strategy                     |
| -------------------- | --------------------------------------------------------------------------------------- | -------------------------------------- |
| `hdcnAdmins`         | `Members_CRUD_All` + `Events_CRUD_All` + `Products_CRUD_All` + `System_User_Management` | Automatic assignment of multiple roles |
| `hdcnLeden`          | `hdcnLeden`                                                                             | Direct 1:1 mapping (no change)         |
| `hdcnRegio_1`        | `Members_Read_Region1` + `Events_Read_Region1`                                          | Region-specific role assignment        |
| `hdcnRegio_2`        | `Members_Read_Region2` + `Events_Read_Region2`                                          | Region-specific role assignment        |
| `hdcnRegio_*`        | `Members_Read_Region{N}` + `Events_Read_Region{N}`                                      | Pattern-based conversion               |
| `hdcnEvents_Read`    | `Events_Read_All`                                                                       | Direct mapping                         |
| `hdcnEvents_Write`   | `Events_CRUD_All`                                                                       | Direct mapping                         |
| `hdcnProducts_Read`  | `Products_Read_All`                                                                     | Direct mapping                         |
| `hdcnProducts_Write` | `Products_CRUD_All`                                                                     | Direct mapping                         |
| `hdcnOrders_Read`    | `Products_Read_All`                                                                     | Orders integrated into products        |
| `hdcnOrders_Write`   | `Products_CRUD_All`                                                                     | Orders integrated into products        |

### 2. Function Permission Mappings

| Function        | Existing Read Access              | New Read Access                                                  | Existing Write Access              | New Write Access                           |
| --------------- | --------------------------------- | ---------------------------------------------------------------- | ---------------------------------- | ------------------------------------------ |
| **members**     | `hdcnAdmins`, `hdcnRegio_*`       | `Members_Read_All`, `Members_Read_Region{N}`, `Members_CRUD_All` | `hdcnAdmins`                       | `Members_CRUD_All`                         |
| **events**      | `hdcnAdmins`, `hdcnEvents_Read`   | `Events_Read_All`, `Events_Read_Region{N}`, `Events_CRUD_All`    | `hdcnAdmins`, `hdcnEvents_Write`   | `Events_CRUD_All`, `Events_CRUD_Region{N}` |
| **products**    | `hdcnAdmins`, `hdcnProducts_Read` | `Products_Read_All`, `Products_CRUD_All`                         | `hdcnAdmins`, `hdcnProducts_Write` | `Products_CRUD_All`                        |
| **orders**      | `hdcnAdmins`, `hdcnOrders_Read`   | `Products_Read_All`, `Products_CRUD_All`                         | `hdcnAdmins`, `hdcnOrders_Write`   | `Products_CRUD_All`                        |
| **webshop**     | `hdcnLeden`, `hdcnAdmins`         | `hdcnLeden`, `Products_Read_All`                                 | `hdcnLeden`, `hdcnAdmins`          | `hdcnLeden`, `Products_CRUD_All`           |
| **parameters**  | `hdcnAdmins`                      | `System_User_Management`                                         | `hdcnAdmins`                       | `System_User_Management`                   |
| **memberships** | `hdcnAdmins`                      | `Members_CRUD_All`                                               | `hdcnAdmins`                       | `Members_CRUD_All`                         |

### 3. Organizational Function Mappings

| H-DCN Function                   | Role Combination                                                                                                                                            | Permissions                           |
| -------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------- |
| **Member Administration**        | `Members_CRUD_All` + `Events_Read_All` + `Products_Read_All` + `Communication_Read_All` + `System_User_Management`                                          | Full member management + system admin |
| **National Chairman**            | `Members_Read_All` + `Members_Status_Approve` + `Events_Read_All` + `Products_Read_All` + `Communication_Read_All` + `System_Logs_Read`                     | View all + approve status + logs      |
| **National Secretary**           | `Members_Read_All` + `Members_Export_All` + `Events_Read_All` + `Events_Export_All` + `Products_Read_All` + `Communication_Export_All` + `System_Logs_Read` | View all + export capabilities        |
| **Webmaster**                    | `Members_Read_All` + `Events_CRUD_All` + `Products_CRUD_All` + `Communication_CRUD_All` + `System_CRUD_All`                                                 | Full system access                    |
| **Regional Chairman (Region N)** | `Members_Read_Region{N}` + `Events_CRUD_Region{N}` + `Products_Read_All` + `Communication_Export_Region{N}`                                                 | Regional management                   |
| **Regular Member**               | `hdcnLeden`                                                                                                                                                 | Basic member access                   |

## Migration Strategy

### Phase 1: Backward Compatibility

1. **Preserve Existing Groups**: Keep current `hdcnAdmins`, `hdcnLeden`, `hdcnRegio_*` groups functional
2. **Dual Permission Checking**: Check both old and new permission systems
3. **Gradual Role Assignment**: Assign new roles alongside existing groups
4. **No Breaking Changes**: Existing functionality continues to work

### Phase 2: Enhanced Permissions

1. **Role-Based Enhancements**: Add new capabilities based on role combinations
2. **Field-Level Permissions**: Implement granular field access control
3. **Regional Restrictions**: Add region-specific data access
4. **Audit Improvements**: Enhanced logging with role context

### Phase 3: System Optimization

1. **Permission Caching**: Cache calculated permissions for performance
2. **Role Inheritance**: Implement role hierarchy and inheritance
3. **Dynamic Updates**: Real-time permission updates
4. **Legacy Cleanup**: Gradual migration away from old groups

## Implementation Requirements

### 1. Enhanced FunctionPermissionManager

```typescript
// New role permission mapping
const ROLE_PERMISSIONS = {
  // Basic member permissions
  hdcnLeden: {
    members: { read: ['own'], write: ['own_personal'] },
    webshop: { read: true, write: true },
    events: { read: ['public'] },
    products: { read: ['catalog'] }
  },

  // Administrative roles
  Members_CRUD_All: {
    members: { read: ['all'], write: ['all'] },
    memberships: { read: ['all'], write: ['all'] }
  },

  Members_Read_All: {
    members: { read: ['all'], write: [] }
  },

  Members_Status_Approve: {
    members: { read: [], write: ['status'] }
  },

  // Event management roles
  Events_Read_All: {
    events: { read: ['all'], write: [] }
  },

  Events_CRUD_All: {
    events: { read: ['all'], write: ['all'] }
  },

  // Product management roles
  Products_Read_All: {
    products: { read: ['all'], write: [] },
    orders: { read: ['all'], write: [] }
  },

  Products_CRUD_All: {
    products: { read: ['all'], write: ['all'] },
    orders: { read: ['all'], write: ['all'] }
  },

  // System administration
  System_User_Management: {
    parameters: { read: ['all'], write: ['all'] },
    users: { read: ['all'], write: ['all'] }
  },

  System_Logs_Read: {
    logs: { read: ['all'], write: [] }
  },

  // Regional roles (template - replace {N} with region number)
  'Members_Read_Region{N}': {
    members: { read: ['region_{N}'], write: [] }
  },

  'Events_Read_Region{N}': {
    events: { read: ['region_{N}'], write: [] }
  },

  'Events_CRUD_Region{N}': {
    events: { read: ['region_{N}'], write: ['region_{N}'] }
  }
};

// Enhanced permission calculation
calculatePermissions(userRoles: string[]): PermissionSet {
  const permissions = {};

  // Combine permissions from all roles
  userRoles.forEach(role => {
    const rolePerms = ROLE_PERMISSIONS[role] || {};
    // Merge permissions (union of all role permissions)
    Object.keys(rolePerms).forEach(resource => {
      if (!permissions[resource]) permissions[resource] = { read: [], write: [] };

      // Combine read permissions
      if (rolePerms[resource].read) {
        permissions[resource].read = [
          ...permissions[resource].read,
          ...rolePerms[resource].read
        ];
      }

      // Combine write permissions
      if (rolePerms[resource].write) {
        permissions[resource].write = [
          ...permissions[resource].write,
          ...rolePerms[resource].write
        ];
      }
    });
  });

  // Deduplicate permissions
  Object.keys(permissions).forEach(resource => {
    permissions[resource].read = [...new Set(permissions[resource].read)];
    permissions[resource].write = [...new Set(permissions[resource].write)];
  });

  return permissions;
}
```

### 2. Backward Compatibility Functions

```typescript
// Legacy group support
hasLegacyAccess(functionName: string, action: 'read' | 'write'): boolean {
  const legacyConfig = {
    members: {
      read: ['hdcnAdmins', 'hdcnRegio_*'],
      write: ['hdcnAdmins']
    },
    // ... existing configuration
  };

  const functionPerms = legacyConfig[functionName];
  if (!functionPerms) return false;

  const allowedGroups = functionPerms[action] || [];
  return this.userGroups.some(userGroup => {
    return allowedGroups.some(allowedGroup => {
      if (allowedGroup.endsWith('*')) {
        const prefix = allowedGroup.slice(0, -1);
        return userGroup.startsWith(prefix);
      }
      return userGroup === allowedGroup;
    });
  });
}

// Combined permission checking
hasAccess(functionName: string, action: 'read' | 'write' = 'read'): boolean {
  // Check new role-based permissions first
  const roleBasedAccess = this.hasRoleBasedAccess(functionName, action);
  if (roleBasedAccess) return true;

  // Fallback to legacy permissions
  return this.hasLegacyAccess(functionName, action);
}
```

### 3. Parameter System Integration

The existing parameter-based module access system will be preserved and enhanced:

```typescript
// Enhanced parameter evaluation with role context
evaluateModuleAccess(user: User, moduleName: string): boolean {
  // Get user roles
  const roles = getUserRoles(user);

  // Check role-based module access first
  const roleAccess = checkRoleBasedModuleAccess(roles, moduleName);
  if (roleAccess !== null) return roleAccess;

  // Fallback to existing parameter-based evaluation
  return evaluateParameterBasedAccess(user, moduleName);
}

// Role-based module access rules
const ROLE_MODULE_ACCESS = {
  // Administrative roles get access to admin modules
  Members_CRUD_All: ['members', 'memberships', 'parameters'],
  System_User_Management: ['parameters', 'users', 'logs'],

  // Regional roles get access to regional modules
  'Members_Read_Region{N}': ['members_region_{N}'],
  'Events_CRUD_Region{N}': ['events_region_{N}'],

  // Basic members get standard access
  hdcnLeden: ['webshop', 'profile', 'events_public']
};
```

## Field-Level Permission Compatibility

### Current Field Access

- All authenticated users can edit their own personal data
- Administrative users can edit all fields
- No granular field-level restrictions

### New Field-Level Permissions

| Field Category            | Current Access  | New Role-Based Access                                      |
| ------------------------- | --------------- | ---------------------------------------------------------- |
| **Personal Fields**       | Own record only | `hdcnLeden`: own record, `Members_CRUD_All`: all records   |
| **Motorcycle Fields**     | Own record only | `hdcnLeden`: own record, `Members_CRUD_All`: all records   |
| **Administrative Fields** | Admin only      | `Members_CRUD_All` only                                    |
| **Status Field**          | Admin only      | `Members_Status_Approve` or `Members_CRUD_All` only        |
| **Regional Fields**       | Admin only      | `Members_CRUD_All` or `Members_Read_Region{N}` (read-only) |

### Field Permission Matrix

```typescript
const FIELD_PERMISSIONS = {
  // Personal fields (editable by member for own record)
  personal: {
    fields: [
      "voornaam",
      "achternaam",
      "tussenvoegsel",
      "initialen",
      "telefoon",
      "straat",
      "postcode",
      "woonplaats",
      "land",
      "email",
      "nieuwsbrief",
      "geboortedatum",
      "geslacht",
    ],
    roles: {
      hdcnLeden: "own_record",
      Members_CRUD_All: "all_records",
    },
  },

  // Motorcycle fields (editable by member for own record)
  motorcycle: {
    fields: ["bouwjaar", "motormerk", "motortype", "kenteken", "wiewatwaar"],
    roles: {
      hdcnLeden: "own_record",
      Members_CRUD_All: "all_records",
    },
  },

  // Administrative fields (admin-only)
  administrative: {
    fields: [
      "member_id",
      "lidnummer",
      "lidmaatschap",
      "tijdstempel",
      "aanmeldingsjaar",
      "regio",
      "clubblad",
      "bankrekeningnummer",
      "datum_ondertekening",
      "created_at",
      "updated_at",
    ],
    roles: {
      Members_CRUD_All: "all_records",
    },
  },

  // Status field (special handling)
  status: {
    fields: ["status"],
    roles: {
      Members_Status_Approve: "all_records",
      Members_CRUD_All: "all_records",
    },
  },
};
```

## Testing Strategy

### 1. Backward Compatibility Tests

- Verify existing `hdcnAdmins` group retains full access
- Confirm `hdcnLeden` group maintains webshop and profile access
- Test regional `hdcnRegio_*` patterns continue to work
- Validate existing function permissions remain functional

### 2. Role-Based Permission Tests

- Test new role assignments provide correct permissions
- Verify role combinations work as expected
- Confirm field-level permissions are enforced
- Test regional role restrictions

### 3. Migration Tests

- Test users with both old and new roles
- Verify permission calculation performance
- Test role assignment and removal
- Validate audit logging functionality

### 4. Integration Tests

- Test parameter system integration with roles
- Verify module access control with new roles
- Test export functionality with role restrictions
- Confirm UI components respect role-based permissions

## Performance Considerations

### 1. Permission Caching

- Cache calculated permissions for user sessions
- Invalidate cache when roles change
- Use memory-efficient permission storage

### 2. Role Evaluation Optimization

- Pre-calculate common role combinations
- Use efficient data structures for permission lookup
- Minimize API calls for permission checks

### 3. Database Optimization

- Index Cognito groups for fast lookup
- Optimize parameter queries for module access
- Use efficient member data filtering

## Security Considerations

### 1. Role Assignment Security

- Audit all role assignments and changes
- Require appropriate permissions to assign roles
- Log all permission-related activities

### 2. Permission Validation

- Validate permissions at API level
- Double-check sensitive operations
- Implement fail-safe defaults (deny access)

### 3. Data Access Control

- Enforce regional data restrictions
- Validate field-level permissions
- Audit sensitive data access

## Conclusion

This compatibility matrix ensures a smooth transition from the existing parameter-based permission system to the new role-based authentication system while maintaining backward compatibility and enabling enhanced security and functionality.

The migration strategy allows for gradual adoption of new roles while preserving existing functionality, ensuring no disruption to current users and operations.
