# H-DCN Cognito Authentication Migration Strategy

## Overview

This document outlines the comprehensive migration strategy for transitioning from the existing parameter-based permission system to the new role-based Cognito authentication system while preserving all existing functionality and ensuring zero downtime.

## Current System Analysis

### Existing Architecture

**Authentication Flow:**

1. Users authenticate via existing Cognito User Pool
2. User groups stored in `cognito:groups` JWT claim
3. FunctionPermissionManager loads permissions from Parameters table
4. FunctionGuard components enforce access control
5. Parameter-based module visibility controls what users see

**Current Groups:**

- `hdcnAdmins` - Full administrative access
- `hdcnLeden` - Basic member access (webshop, own profile)
- `hdcnRegio_*` - Regional access patterns (wildcard matching)
- `hdcnEvents_Read/Write` - Event-specific permissions
- `hdcnProducts_Read/Write` - Product-specific permissions
- `hdcnOrders_Read/Write` - Order-specific permissions

**Current Permission Structure:**

```typescript
{
  members: { read: ['hdcnAdmins', 'hdcnRegio_*'], write: ['hdcnAdmins'] },
  events: { read: ['hdcnAdmins', 'hdcnEvents_Read'], write: ['hdcnAdmins', 'hdcnEvents_Write'] },
  products: { read: ['hdcnAdmins', 'hdcnProducts_Read'], write: ['hdcnAdmins', 'hdcnProducts_Write'] },
  orders: { read: ['hdcnAdmins', 'hdcnOrders_Read'], write: ['hdcnAdmins', 'hdcnOrders_Write'] },
  webshop: { read: ['hdcnLeden', 'hdcnAdmins'], write: ['hdcnLeden', 'hdcnAdmins'] },
  parameters: { read: ['hdcnAdmins'], write: ['hdcnAdmins'] },
  memberships: { read: ['hdcnAdmins'], write: ['hdcnAdmins'] }
}
```

## Migration Strategy: Three-Phase Approach

### Phase 1: Backward Compatibility Layer (Week 1-2)

**Goal:** Ensure new role-based system works alongside existing system without breaking changes.

#### 1.1 Enhanced FunctionPermissionManager

**Create hybrid permission system that checks both old and new roles:**

```typescript
// Enhanced FunctionPermissionManager with dual permission checking
export class FunctionPermissionManager {
  private userGroups: string[];
  private userRoles: string[];
  private legacyPermissions: PermissionConfig;
  private rolePermissions: RolePermissionConfig;

  constructor(
    user: User,
    legacyConfig: PermissionConfig,
    roleConfig: RolePermissionConfig
  ) {
    this.userGroups =
      user.signInUserSession?.accessToken?.payload["cognito:groups"] || [];
    this.userRoles = this.extractRoles(this.userGroups);
    this.legacyPermissions = legacyConfig;
    this.rolePermissions = roleConfig;
  }

  // Main access check - tries new system first, falls back to legacy
  hasAccess(functionName: string, action: "read" | "write" = "read"): boolean {
    // Check new role-based permissions first
    const roleBasedAccess = this.hasRoleBasedAccess(functionName, action);
    if (roleBasedAccess !== null) return roleBasedAccess;

    // Fallback to legacy permissions
    return this.hasLegacyAccess(functionName, action);
  }

  // New role-based permission checking
  private hasRoleBasedAccess(
    functionName: string,
    action: "read" | "write"
  ): boolean | null {
    if (this.userRoles.length === 0) return null; // No roles assigned yet

    const permissions = this.calculatePermissions(this.userRoles);
    const functionPerms = permissions[functionName];

    if (!functionPerms) return null;

    const allowedActions = functionPerms[action] || [];
    return allowedActions.length > 0;
  }

  // Legacy permission checking (existing logic)
  private hasLegacyAccess(
    functionName: string,
    action: "read" | "write"
  ): boolean {
    const functionPerms = this.legacyPermissions[functionName];
    if (!functionPerms) return false;

    const allowedGroups = functionPerms[action] || [];

    return this.userGroups.some((userGroup) => {
      return allowedGroups.some((allowedGroup) => {
        if (allowedGroup.endsWith("*")) {
          const prefix = allowedGroup.slice(0, -1);
          return userGroup.startsWith(prefix);
        }
        return userGroup === allowedGroup;
      });
    });
  }

  // Extract new roles from Cognito groups
  private extractRoles(groups: string[]): string[] {
    const newRoles = [
      "hdcnLeden",
      "Members_CRUD_All",
      "Members_Read_All",
      "Members_Status_Approve",
      "Events_Read_All",
      "Events_CRUD_All",
      "Products_Read_All",
      "Products_CRUD_All",
      "Communication_Read_All",
      "Communication_Export_All",
      "System_User_Management",
      "System_Logs_Read",
    ];

    // Add regional roles
    for (let i = 1; i <= 9; i++) {
      newRoles.push(
        `Members_Read_Region${i}`,
        `Members_Export_Region${i}`,
        `Events_Read_Region${i}`,
        `Events_CRUD_Region${i}`,
        `Communication_Export_Region${i}`
      );
    }

    return groups.filter((group) => newRoles.includes(group));
  }

  // Calculate permissions from roles
  private calculatePermissions(roles: string[]): PermissionSet {
    const permissions = {};

    roles.forEach((role) => {
      const rolePerms = ROLE_PERMISSIONS[role] || {};
      Object.keys(rolePerms).forEach((resource) => {
        if (!permissions[resource])
          permissions[resource] = { read: [], write: [] };

        if (rolePerms[resource].read) {
          permissions[resource].read = [
            ...permissions[resource].read,
            ...rolePerms[resource].read,
          ];
        }

        if (rolePerms[resource].write) {
          permissions[resource].write = [
            ...permissions[resource].write,
            ...rolePerms[resource].write,
          ];
        }
      });
    });

    // Deduplicate permissions
    Object.keys(permissions).forEach((resource) => {
      permissions[resource].read = [...new Set(permissions[resource].read)];
      permissions[resource].write = [...new Set(permissions[resource].write)];
    });

    return permissions;
  }
}
```

#### 1.2 Role Permission Mapping

**Define comprehensive role-to-permission mapping:**

```typescript
const ROLE_PERMISSIONS = {
  // Basic member permissions
  hdcnLeden: {
    members: { read: ["own"], write: ["own_personal", "own_motorcycle"] },
    webshop: { read: ["all"], write: ["own_cart"] },
    events: { read: ["public"] },
    products: { read: ["catalog"] },
  },

  // Member management roles
  Members_CRUD_All: {
    members: { read: ["all"], write: ["all"] },
    memberships: { read: ["all"], write: ["all"] },
  },

  Members_Read_All: {
    members: { read: ["all"], write: [] },
  },

  Members_Status_Approve: {
    members: { read: [], write: ["status"] },
  },

  // Event management roles
  Events_Read_All: {
    events: { read: ["all"], write: [] },
  },

  Events_CRUD_All: {
    events: { read: ["all"], write: ["all"] },
  },

  // Product management roles
  Products_Read_All: {
    products: { read: ["all"], write: [] },
    orders: { read: ["all"], write: [] },
  },

  Products_CRUD_All: {
    products: { read: ["all"], write: ["all"] },
    orders: { read: ["all"], write: ["all"] },
  },

  // Communication roles
  Communication_Read_All: {
    communication: { read: ["all"], write: [] },
  },

  Communication_Export_All: {
    communication: { read: ["all"], write: [], export: ["all"] },
  },

  // System administration
  System_User_Management: {
    parameters: { read: ["all"], write: ["all"] },
    users: { read: ["all"], write: ["all"] },
    roles: { read: ["all"], write: ["all"] },
  },

  System_Logs_Read: {
    logs: { read: ["all"], write: [] },
  },

  // Regional roles (template - will be expanded for each region)
  Members_Read_Region1: {
    members: { read: ["region_1"], write: [] },
  },

  Members_Export_Region1: {
    members: { read: ["region_1"], write: [], export: ["region_1"] },
  },

  Events_Read_Region1: {
    events: { read: ["region_1"], write: [] },
  },

  Events_CRUD_Region1: {
    events: { read: ["region_1"], write: ["region_1"] },
  },

  Communication_Export_Region1: {
    communication: { read: ["region_1"], write: [], export: ["region_1"] },
  },

  // ... repeat for regions 2-9
};
```

#### 1.3 Enhanced FunctionGuard Component

**Update FunctionGuard to support role-based access while preserving existing functionality:**

```typescript
interface FunctionGuardProps {
  user: any;
  children: ReactNode;
  functionName: string;
  action?: "read" | "write";
  requiredRoles?: string[]; // New prop for role-based access
  fallback?: ReactNode;
}

export function FunctionGuard({
  user,
  children,
  functionName,
  action = "read",
  requiredRoles = [],
  fallback = null,
}: FunctionGuardProps) {
  const [hasAccess, setHasAccess] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const checkAccess = async () => {
      try {
        const permissions = await FunctionPermissionManager.create(user);

        // Check function-based access (existing logic)
        let functionAccess = permissions.hasAccess(functionName, action);

        // Check role-based access if requiredRoles specified
        let roleAccess = true;
        if (requiredRoles.length > 0) {
          const userRoles = getUserRoles(user);
          roleAccess = requiredRoles.some((role) => userRoles.includes(role));
        }

        // User needs both function access AND role access
        setHasAccess(functionAccess && roleAccess);
      } catch (error) {
        console.error("Permission check failed:", error);
        // Fallback: Allow access for admins, deny for others
        const userGroups =
          user.signInUserSession?.accessToken?.payload["cognito:groups"] || [];
        const isAdmin = userGroups.includes("hdcnAdmins");
        setHasAccess(isAdmin);
      } finally {
        setLoading(false);
      }
    };

    checkAccess();
  }, [user, functionName, action, requiredRoles]);

  if (loading) return null;
  return hasAccess ? children : fallback;
}
```

### Phase 2: Role Assignment and Testing (Week 3-4)

**Goal:** Assign new roles to existing users and test dual permission system.

#### 2.1 Role Assignment Strategy

**Map existing groups to new roles:**

| Existing Group       | New Role Assignment                                                                     | Migration Logic                        |
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

#### 2.2 Migration Script

**Create Lambda function to assign new roles based on existing groups:**

```python
import boto3
import json
from typing import List, Dict

def migrate_user_roles(event, context):
    """
    Migrate existing Cognito groups to new role-based system
    """
    cognito = boto3.client('cognito-idp')
    user_pool_id = os.environ['USER_POOL_ID']

    # Role mapping configuration
    role_mappings = {
        'hdcnAdmins': ['Members_CRUD_All', 'Events_CRUD_All', 'Products_CRUD_All', 'System_User_Management'],
        'hdcnLeden': ['hdcnLeden'],
        'hdcnEvents_Read': ['Events_Read_All'],
        'hdcnEvents_Write': ['Events_CRUD_All'],
        'hdcnProducts_Read': ['Products_Read_All'],
        'hdcnProducts_Write': ['Products_CRUD_All'],
        'hdcnOrders_Read': ['Products_Read_All'],
        'hdcnOrders_Write': ['Products_CRUD_All']
    }

    # Regional role mappings
    for region in range(1, 10):
        role_mappings[f'hdcnRegio_{region}'] = [
            f'Members_Read_Region{region}',
            f'Events_Read_Region{region}'
        ]

    try:
        # Get all users
        paginator = cognito.get_paginator('list_users')

        migration_results = {
            'successful': 0,
            'failed': 0,
            'errors': []
        }

        for page in paginator.paginate(UserPoolId=user_pool_id):
            for user in page['Users']:
                username = user['Username']

                try:
                    # Get user's current groups
                    current_groups = cognito.admin_list_groups_for_user(
                        UserPoolId=user_pool_id,
                        Username=username
                    )['Groups']

                    current_group_names = [group['GroupName'] for group in current_groups]

                    # Calculate new roles to assign
                    new_roles = set()
                    for group_name in current_group_names:
                        if group_name in role_mappings:
                            new_roles.update(role_mappings[group_name])

                    # Assign new roles (keep existing groups for backward compatibility)
                    for role in new_roles:
                        try:
                            cognito.admin_add_user_to_group(
                                UserPoolId=user_pool_id,
                                Username=username,
                                GroupName=role
                            )
                        except cognito.exceptions.ResourceNotFoundException:
                            # Role doesn't exist yet, skip for now
                            pass

                    migration_results['successful'] += 1

                except Exception as user_error:
                    migration_results['failed'] += 1
                    migration_results['errors'].append({
                        'username': username,
                        'error': str(user_error)
                    })

        return {
            'statusCode': 200,
            'body': json.dumps(migration_results)
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
```

#### 2.3 Testing Strategy

**Comprehensive testing of dual permission system:**

1. **Backward Compatibility Tests:**

   - Verify existing `hdcnAdmins` group retains full access
   - Confirm `hdcnLeden` group maintains webshop and profile access
   - Test regional `hdcnRegio_*` patterns continue to work
   - Validate existing function permissions remain functional

2. **Role-Based Permission Tests:**

   - Test new role assignments provide correct permissions
   - Verify role combinations work as expected
   - Confirm field-level permissions are enforced
   - Test regional role restrictions

3. **Integration Tests:**
   - Test users with both old and new roles
   - Verify permission calculation performance
   - Test role assignment and removal
   - Validate audit logging functionality

### Phase 3: Enhanced Features and Optimization (Week 5-6)

**Goal:** Enable enhanced role-based features while maintaining backward compatibility.

#### 3.1 Field-Level Permissions

**Implement granular field-level access control:**

```typescript
interface FieldPermission {
  fields: string[];
  roles: {
    [roleName: string]: "own_record" | "all_records" | "read_only";
  };
}

const FIELD_PERMISSIONS: { [category: string]: FieldPermission } = {
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

  motorcycle: {
    fields: ["bouwjaar", "motormerk", "motortype", "kenteken", "wiewatwaar"],
    roles: {
      hdcnLeden: "own_record",
      Members_CRUD_All: "all_records",
    },
  },

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

  status: {
    fields: ["status"],
    roles: {
      Members_Status_Approve: "all_records",
      Members_CRUD_All: "all_records",
    },
  },
};

// Field permission checking utility
export function canEditField(
  user: any,
  fieldName: string,
  recordOwnerId?: string
): boolean {
  const userRoles = getUserRoles(user);
  const userId = user.username;

  // Find which category this field belongs to
  const category = Object.keys(FIELD_PERMISSIONS).find((cat) =>
    FIELD_PERMISSIONS[cat].fields.includes(fieldName)
  );

  if (!category) return false; // Unknown field, deny access

  const fieldPermission = FIELD_PERMISSIONS[category];

  // Check if user has any role that allows editing this field
  for (const role of userRoles) {
    const permission = fieldPermission.roles[role];

    if (permission === "all_records") return true;
    if (permission === "own_record" && recordOwnerId === userId) return true;
  }

  return false;
}
```

#### 3.2 Enhanced Module Access Control

**Integrate role-based access with existing parameter system:**

```typescript
// Enhanced module access evaluation
export async function evaluateModuleAccess(
  user: any,
  moduleName: string
): Promise<boolean> {
  const userRoles = getUserRoles(user);

  // Check role-based module access first
  const roleAccess = checkRoleBasedModuleAccess(userRoles, moduleName);
  if (roleAccess !== null) return roleAccess;

  // Fallback to existing parameter-based evaluation
  return evaluateParameterBasedAccess(user, moduleName);
}

// Role-based module access rules
const ROLE_MODULE_ACCESS = {
  // Administrative roles get access to admin modules
  Members_CRUD_All: ["members", "memberships", "parameters"],
  System_User_Management: ["parameters", "users", "logs"],

  // Event management roles
  Events_CRUD_All: ["events", "event_management"],
  Events_Read_All: ["events"],

  // Product management roles
  Products_CRUD_All: ["products", "webshop_admin", "orders"],
  Products_Read_All: ["products", "orders"],

  // Regional roles get access to regional modules
  Members_Read_Region1: ["members_region_1"],
  Events_CRUD_Region1: ["events_region_1"],

  // Basic members get standard access
  hdcnLeden: ["webshop", "profile", "events_public"],
};

function checkRoleBasedModuleAccess(
  userRoles: string[],
  moduleName: string
): boolean | null {
  if (userRoles.length === 0) return null; // No roles assigned yet

  // Check if any role grants access to this module
  for (const role of userRoles) {
    const allowedModules = ROLE_MODULE_ACCESS[role] || [];
    if (allowedModules.includes(moduleName)) return true;
  }

  // Check regional patterns
  for (const role of userRoles) {
    if (
      role.startsWith("Members_Read_Region") &&
      moduleName.startsWith("members_region_")
    ) {
      const regionNumber = role.replace("Members_Read_Region", "");
      if (moduleName === `members_region_${regionNumber}`) return true;
    }

    if (
      role.startsWith("Events_CRUD_Region") &&
      moduleName.startsWith("events_region_")
    ) {
      const regionNumber = role.replace("Events_CRUD_Region", "");
      if (moduleName === `events_region_${regionNumber}`) return true;
    }
  }

  return null; // No role-based rule found, use parameter-based fallback
}
```

#### 3.3 Performance Optimization

**Implement caching and optimization strategies:**

```typescript
// Permission result caching
class PermissionCache {
  private cache = new Map<string, any>();
  private cacheTimeout = 5 * 60 * 1000; // 5 minutes

  getCachedPermissions(userId: string): any | null {
    const cached = this.cache.get(userId);
    if (!cached) return null;

    if (Date.now() - cached.timestamp > this.cacheTimeout) {
      this.cache.delete(userId);
      return null;
    }

    return cached.permissions;
  }

  setCachedPermissions(userId: string, permissions: any): void {
    this.cache.set(userId, {
      permissions,
      timestamp: Date.now(),
    });
  }

  invalidateUser(userId: string): void {
    this.cache.delete(userId);
  }

  clear(): void {
    this.cache.clear();
  }
}

const permissionCache = new PermissionCache();

// Enhanced FunctionPermissionManager with caching
export class FunctionPermissionManager {
  // ... existing code ...

  static async create(user: User): Promise<FunctionPermissionManager> {
    const userId = user.username;

    // Check cache first
    const cachedPermissions = permissionCache.getCachedPermissions(userId);
    if (cachedPermissions) {
      return new FunctionPermissionManager(
        user,
        cachedPermissions.legacy,
        cachedPermissions.roles
      );
    }

    // Load permissions (existing logic)
    const legacyConfig = await this.loadLegacyPermissions();
    const roleConfig = await this.loadRolePermissions();

    // Cache the results
    permissionCache.setCachedPermissions(userId, {
      legacy: legacyConfig,
      roles: roleConfig,
    });

    return new FunctionPermissionManager(user, legacyConfig, roleConfig);
  }
}
```

## Implementation Timeline

### Week 1-2: Backward Compatibility Layer

- [ ] Enhance FunctionPermissionManager with dual permission checking
- [ ] Create role permission mapping constants
- [ ] Update FunctionGuard component with role support
- [ ] Implement field-level permission utilities
- [ ] Create comprehensive test suite for backward compatibility

### Week 3-4: Role Assignment and Testing

- [ ] Create role assignment migration script
- [ ] Deploy new Cognito groups (roles) via IaC
- [ ] Run migration script to assign roles based on existing groups
- [ ] Comprehensive testing of dual permission system
- [ ] Performance testing and optimization

### Week 5-6: Enhanced Features and Optimization

- [ ] Implement field-level permissions in UI components
- [ ] Enhance module access control with role-based rules
- [ ] Implement permission caching for performance
- [ ] Add comprehensive audit logging
- [ ] Final testing and documentation

## Risk Mitigation

### 1. Zero Downtime Migration

- **Dual System Approach**: Both old and new permission systems work simultaneously
- **Gradual Role Assignment**: Roles assigned incrementally without affecting existing access
- **Fallback Mechanisms**: System falls back to legacy permissions if role-based fails
- **Rollback Capability**: Can disable role-based system and revert to legacy at any time

### 2. Data Integrity

- **No Data Loss**: Existing groups and permissions remain unchanged
- **Audit Trail**: All permission changes are logged with timestamps and user context
- **Validation**: Comprehensive validation of role assignments before deployment
- **Backup Strategy**: Full backup of Cognito configuration before migration

### 3. User Experience

- **No User Impact**: Users continue to access system normally during migration
- **Enhanced Features**: New role-based features are additive, not replacing
- **Clear Communication**: Users informed of new capabilities as they become available
- **Support Documentation**: Updated documentation and support materials

### 4. Performance Considerations

- **Caching Strategy**: Permission results cached to minimize performance impact
- **Efficient Queries**: Optimized database queries for role and permission lookups
- **Load Testing**: Comprehensive load testing before production deployment
- **Monitoring**: Real-time monitoring of system performance during migration

## Success Criteria

### Technical Success

- [ ] All existing functionality continues to work without interruption
- [ ] New role-based permissions provide enhanced granular access control
- [ ] System performance meets or exceeds current benchmarks (<2s response time)
- [ ] Zero data loss or corruption during migration
- [ ] Comprehensive audit trail of all permission changes

### User Success

- [ ] Users experience no disruption to their normal workflows
- [ ] Administrative users can assign and manage roles effectively
- [ ] Field-level permissions provide appropriate data protection
- [ ] Regional users have proper access restrictions
- [ ] Support tickets related to permissions reduced by 50%

### Business Success

- [ ] Enhanced security through granular role-based access control
- [ ] Improved compliance with data protection requirements
- [ ] Reduced administrative overhead for permission management
- [ ] Foundation for future organizational growth and role expansion
- [ ] Maintained system reliability and availability (99.9% uptime)

## Conclusion

This migration strategy ensures a smooth transition from the existing parameter-based permission system to the new role-based Cognito authentication system while preserving all existing functionality and providing enhanced security and flexibility.

The three-phase approach minimizes risk by maintaining backward compatibility throughout the migration process, allowing for thorough testing and validation at each stage, and providing clear rollback capabilities if needed.

The enhanced role-based system will provide H-DCN with the flexibility to manage organizational permissions more effectively while maintaining the simplicity and reliability of the existing system.
