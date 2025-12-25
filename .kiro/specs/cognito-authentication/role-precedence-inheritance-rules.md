# H-DCN Role Precedence and Inheritance Rules

## Overview

This document defines the complete role precedence hierarchy and inheritance rules for the H-DCN Cognito authentication system. These rules govern how multiple roles combine, which permissions take priority in conflicts, and how role-based access control is calculated for users with multiple organizational functions.

## Role Precedence Hierarchy

### Precedence Values and Priority

Roles are implemented as AWS Cognito Groups with precedence values. **Lower precedence numbers indicate higher priority** in the system hierarchy.

| Precedence | Role Name                | Priority Level | Description                      |
| ---------- | ------------------------ | -------------- | -------------------------------- |
| 1          | System_CRUD_All          | Highest        | Complete system administration   |
| 5          | System_User_Management   | Critical       | User and role management         |
| 10         | Members_CRUD_All         | High           | Complete member data management  |
| 15         | Members_Status_Approve   | High           | Member status approval authority |
| 20         | Members_Read_All         | Medium-High    | View all member information      |
| 25         | Events_CRUD_All          | Medium-High    | Complete event management        |
| 30         | Events_Read_All          | Medium         | View all events                  |
| 35         | Products_CRUD_All        | Medium         | Complete product management      |
| 40         | Products_Read_All        | Medium         | View all products                |
| 45         | Communication_Export_All | Medium-Low     | Export all communication data    |
| 50         | Communication_Read_All   | Medium-Low     | View all communication           |
| 55         | System_Logs_Read         | Low            | View system logs                 |
| 100        | hdcnLeden                | Lowest         | Basic member access              |

### Regional Role Precedence

Regional roles follow the same precedence pattern but are scoped to specific regions:

| Precedence Range | Role Pattern                   | Scope    | Description                     |
| ---------------- | ------------------------------ | -------- | ------------------------------- |
| 25-29            | Members_Read_Region{N}         | Regional | View members in specific region |
| 30-34            | Members_Export_Region{N}       | Regional | Export members from region      |
| 35-39            | Events_Read_Region{N}          | Regional | View events in specific region  |
| 30-34            | Events_CRUD_Region{N}          | Regional | Manage events in region         |
| 50-54            | Communication_Export_Region{N} | Regional | Export communication for region |

## Inheritance Rules

### 1. Additive Permission Model

**Rule**: Multiple roles combine permissions using a **union (additive) model**, not intersection.

**Example**:

```
User: jan.jansen@gmail.com
Roles: ["Members_Read_All", "Events_CRUD_All", "Products_Read_All"]
Effective Permissions:
  - View all member data (from Members_Read_All)
  - Full event management (from Events_CRUD_All)
  - View all products (from Products_Read_All)
```

**Implementation Logic**:

```typescript
function calculatePermissions(userRoles: string[]): Permission[] {
  const allPermissions = new Set<Permission>();

  userRoles.forEach((role) => {
    const rolePermissions = ROLE_PERMISSIONS[role] || [];
    rolePermissions.forEach((permission) => allPermissions.add(permission));
  });

  return Array.from(allPermissions);
}
```

### 2. Precedence-Based Conflict Resolution

**Rule**: When roles have conflicting permissions for the same resource, **higher precedence (lower number) takes priority**.

**Conflict Scenarios**:

#### Scenario A: Read vs CRUD Conflict

```
User has roles: ["Members_Read_All" (precedence: 20), "Members_CRUD_All" (precedence: 10)]
Conflict: Both roles affect member data access
Resolution: Members_CRUD_All wins (precedence 10 < 20)
Result: User gets CRUD access to member data
```

#### Scenario B: Regional vs National Scope

```
User has roles: ["Members_Read_Region1" (precedence: 25), "Members_Read_All" (precedence: 20)]
Conflict: Regional vs national scope for member data
Resolution: Members_Read_All wins (precedence 20 < 25)
Result: User gets access to all regions, not just Region 1
```

#### Scenario C: Export Permission Levels

```
User has roles: ["Communication_Read_All" (precedence: 50), "Communication_Export_All" (precedence: 45)]
Conflict: Read vs Export permissions for communication
Resolution: Communication_Export_All wins (precedence 45 < 50)
Result: User gets export permissions (which include read)
```

### 3. Scope Inheritance Rules

#### National Scope Overrides Regional Scope

**Rule**: National-level roles automatically include permissions for all regions.

**Examples**:

- `Members_Read_All` includes permissions from all `Members_Read_Region{N}` roles
- `Events_CRUD_All` includes permissions from all `Events_CRUD_Region{N}` roles
- `Communication_Export_All` includes permissions from all `Communication_Export_Region{N}` roles

#### CRUD Permissions Include Read Permissions

**Rule**: CRUD roles automatically include corresponding Read permissions.

**Hierarchy**:

```
CRUD > Export > Read > None

Examples:
- Members_CRUD_All includes Members_Read_All permissions
- Events_CRUD_All includes Events_Read_All permissions
- Products_CRUD_All includes Products_Read_All permissions
```

#### Administrative Permissions Include Basic Permissions

**Rule**: Administrative roles include basic member permissions.

**Example**:

```
User with Members_CRUD_All role automatically gets:
- All permissions from hdcnLeden role
- Plus additional administrative permissions
- No need to explicitly assign hdcnLeden role
```

### 4. Regional Restriction Rules

#### Regional Roles Are Scope-Limited

**Rule**: Regional roles cannot access data outside their assigned region, regardless of other permissions.

**Example**:

```
User: marie.secretary@example.com
Roles: ["Members_Export_Region1", "Events_Read_Region1"]
Restriction: Can only access Region 1 data
Cannot access: Region 2-9 member or event data
Exception: National-level roles override regional restrictions
```

#### Regional Role Combinations

**Rule**: Users can have multiple regional roles, but each is independently scoped.

**Example**:

```
User: multi.regional@example.com
Roles: ["Members_Read_Region1", "Members_Read_Region5", "Events_CRUD_Region3"]
Effective Access:
- View members in Region 1 and Region 5
- Manage events in Region 3 only
- No access to other regions (2, 4, 6, 7, 8, 9)
```

### 5. Special Role Inheritance Cases

#### System Administration Roles

**Rule**: System administration roles have special inheritance properties.

```
System_CRUD_All (precedence: 1):
- Inherits ALL permissions from every other role
- Can override any regional restrictions
- Has complete system access regardless of other role combinations

System_User_Management (precedence: 5):
- Can assign/remove roles for other users
- Can view user role assignments
- Cannot modify system configuration (requires System_CRUD_All)
```

#### Status Approval Authority

**Rule**: `Members_Status_Approve` role has special inheritance for status modifications.

```
Members_Status_Approve (precedence: 15):
- Can approve/reject member status changes
- Inherits Members_Read_All permissions (precedence: 20)
- Cannot directly modify member data (requires Members_CRUD_All)
- Status approval authority cannot be inherited by other roles
```

#### Financial Data Access

**Rule**: Financial roles have restricted inheritance to protect sensitive data.

```
Financial roles (when implemented):
- Members_Read_Financial: Only financial data, no personal data inheritance
- Events_Read_Financial: Only event financial data
- Products_Read_Financial: Only product financial data
- Financial permissions do NOT inherit from general read permissions
- General read permissions do NOT inherit financial access
```

## Permission Calculation Algorithm

### Step-by-Step Process

1. **Extract User Roles**: Get all Cognito groups from user's JWT token
2. **Sort by Precedence**: Order roles by precedence value (ascending)
3. **Calculate Base Permissions**: Combine permissions from all roles (union)
4. **Apply Precedence Rules**: Resolve conflicts using precedence hierarchy
5. **Apply Scope Restrictions**: Enforce regional and functional scope limits
6. **Apply Special Rules**: Handle system admin and financial role exceptions
7. **Return Final Permissions**: Provide deduplicated, validated permission set

### Implementation Example

```typescript
interface RolePermission {
  role: string;
  precedence: number;
  permissions: Permission[];
  scope: "national" | "regional" | "system";
  region?: number;
}

function calculateUserPermissions(userRoles: string[]): Permission[] {
  // Step 1: Get role definitions
  const roleDefinitions = userRoles.map((role) => getRoleDefinition(role));

  // Step 2: Sort by precedence (lower number = higher priority)
  roleDefinitions.sort((a, b) => a.precedence - b.precedence);

  // Step 3: Apply inheritance rules
  const effectivePermissions = new Set<Permission>();
  const regionalRestrictions = new Map<string, number[]>();

  roleDefinitions.forEach((roleDef) => {
    // Add base permissions
    roleDef.permissions.forEach((permission) => {
      effectivePermissions.add(permission);
    });

    // Handle scope inheritance
    if (roleDef.scope === "national") {
      // National roles override regional restrictions
      regionalRestrictions.clear();
    } else if (roleDef.scope === "regional" && roleDef.region) {
      // Add regional restriction
      const resourceType = roleDef.role.split("_")[0]; // e.g., 'Members'
      if (!regionalRestrictions.has(resourceType)) {
        regionalRestrictions.set(resourceType, []);
      }
      regionalRestrictions.get(resourceType)!.push(roleDef.region);
    }
  });

  // Step 4: Apply special system admin rules
  if (userRoles.includes("System_CRUD_All")) {
    // System admin gets all permissions, no restrictions
    return getAllSystemPermissions();
  }

  // Step 5: Return final permissions with scope restrictions
  return {
    permissions: Array.from(effectivePermissions),
    regionalRestrictions: Object.fromEntries(regionalRestrictions),
  };
}
```

## Practical Examples

### Example 1: National Chairman

```
User: chairman@h-dcn.nl
Assigned Roles:
- Members_Read_All (precedence: 20)
- Members_Status_Approve (precedence: 15)
- Events_Read_All (precedence: 30)
- Products_Read_All (precedence: 40)
- Communication_Read_All (precedence: 50)
- System_Logs_Read (precedence: 55)

Inheritance Resolution:
1. Members_Status_Approve (15) inherits Members_Read_All (20) → Gets member read + status approval
2. All other roles add their permissions additively
3. No conflicts, all permissions combine

Final Permissions:
- View all member data (all regions)
- Approve member status changes
- View all events, products, communication
- View system logs
- No CRUD permissions (read-only except status approval)
```

### Example 2: Regional Secretary with Multiple Regions

```
User: secretary@example.com
Assigned Roles:
- Members_Read_Region1 (precedence: 25)
- Members_Export_Region1 (precedence: 30)
- Members_Read_Region5 (precedence: 25)
- Events_Read_Region1 (precedence: 35)
- hdcnLeden (precedence: 100)

Inheritance Resolution:
1. Regional roles are independently scoped
2. Members_Export_Region1 (30) includes Members_Read_Region1 (25) for Region 1
3. hdcnLeden permissions are included but overridden by higher precedence roles

Final Permissions:
- View and export members in Region 1
- View members in Region 5 (no export)
- View events in Region 1 only
- Basic member permissions for own data
- No access to other regions (2, 3, 4, 6, 7, 8, 9)
```

### Example 3: Webmaster with System Access

```
User: webmaster@h-dcn.nl
Assigned Roles:
- Members_Read_All (precedence: 20)
- Events_CRUD_All (precedence: 25)
- Products_CRUD_All (precedence: 35)
- System_CRUD_All (precedence: 1)

Inheritance Resolution:
1. System_CRUD_All (1) has highest precedence
2. System admin role inherits ALL permissions from other roles
3. All regional restrictions are removed
4. Gets complete system access

Final Permissions:
- Complete system administration access
- All member, event, product permissions
- No regional restrictions
- Can override any access controls
- Full CRUD on all resources
```

## Validation Rules

### Role Assignment Validation

1. **Conflict Detection**: System validates role combinations for logical conflicts
2. **Precedence Validation**: Ensures role precedence values are correctly configured
3. **Scope Validation**: Verifies regional roles are assigned to valid regions
4. **Permission Validation**: Confirms role permissions are properly defined

### Runtime Validation

1. **Token Validation**: Verify Cognito groups in JWT tokens match assigned roles
2. **Permission Calculation**: Validate calculated permissions match expected results
3. **Scope Enforcement**: Ensure regional restrictions are properly applied
4. **Audit Logging**: Log all permission calculations for compliance

## Security Implications

### Privilege Escalation Prevention

1. **Role Assignment Controls**: Only System_User_Management role can assign roles
2. **Precedence Protection**: Higher precedence roles cannot be assigned by lower precedence users
3. **System Admin Protection**: System_CRUD_All role assignment requires special approval
4. **Regional Boundary Enforcement**: Regional roles cannot escalate to national scope

### Audit and Compliance

1. **Permission Calculation Logging**: All permission calculations are logged
2. **Role Change Auditing**: Role assignments/removals are tracked with timestamps
3. **Access Pattern Monitoring**: Unusual permission usage triggers alerts
4. **Compliance Reporting**: Regular reports on role assignments and usage patterns

This role precedence and inheritance system provides a robust, secure, and flexible foundation for H-DCN's role-based access control while maintaining clear organizational alignment and audit capabilities.
