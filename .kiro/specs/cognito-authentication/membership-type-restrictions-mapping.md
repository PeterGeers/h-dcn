# H-DCN Membership Type Restrictions and Module Access Rules Mapping

## Overview

This document maps the current membership type restrictions and module access rules discovered in the H-DCN system. This analysis is required for task MVP-2 to understand existing parameter-based module access and field-level restrictions before implementing role-based authentication.

## Current Membership Types

Based on the parameter store and form validation, the following membership types exist:

### 1. Gewoon lid (Regular Member)

- **Motor fields required**: Yes
- **Fields**: motormerk, motortype, bouwjaar, kenteken
- **Access level**: Full member access
- **Webshop access**: Yes

### 2. Gezins lid (Family Member)

- **Motor fields required**: Yes
- **Fields**: motormerk, motortype, bouwjaar, kenteken
- **Access level**: Full member access
- **Webshop access**: Yes

### 3. Gezins donateur zonder motor (Family Donor without Motorcycle)

- **Motor fields required**: No
- **Fields**: motormerk, motortype, bouwjaar, kenteken are optional/hidden
- **Access level**: Limited member access
- **Webshop access**: Yes (assumed)

### 4. Donateur zonder motor (Donor without Motorcycle)

- **Motor fields required**: No
- **Fields**: motormerk, motortype, bouwjaar, kenteken are optional/hidden
- **Access level**: Limited member access
- **Webshop access**: Yes (assumed)

## Current Field-Level Restrictions

### Personal Data Fields (Editable by member for own record)

```typescript
const personalFields = [
  "voornaam",
  "achternaam",
  "initialen",
  "tussenvoegsel",
  "telefoon",
  "straat",
  "postcode",
  "woonplaats",
  "land",
  "email",
  "nieuwsbrief",
  "geboortedatum",
  "geslacht",
];
```

### Motorcycle Data Fields (Conditional based on membership type)

```typescript
const motorcycleFields = [
  "bouwjaar",
  "motormerk",
  "motortype",
  "kenteken",
  "wiewatwaar",
];

// Required only for: 'Gewoon lid' || 'Gezins lid'
// Optional/hidden for: 'Gezins donateur zonder motor' || 'Donateur zonder motor'
```

### Administrative Data Fields (Admin-only, read-only for members)

```typescript
const administrativeFields = [
  "member_id", // System-generated UUID
  "lidnummer", // Membership number
  "lidmaatschap", // Membership type
  "status", // Membership status
  "tijdstempel", // Member since date (not found in current code)
  "aanmeldingsjaar", // Registration year (not found in current code)
  "regio", // Region assignment
  "clubblad", // Club magazine subscription
  "bankrekeningnummer", // Bank account number
  "datum_ondertekening", // Signature date (not found in current code)
  "created_at", // Record creation timestamp
  "updated_at", // Record update timestamp
];
```

## Current Module Access Control System

### 1. Group-Based Access Control

**Location**: `frontend/src/components/common/GroupAccessGuard.js`

```javascript
// Users must have at least one Cognito group to access the application
const userGroups =
  user.signInUserSession?.accessToken?.payload["cognito:groups"] || [];
const hasGroupAccess = userGroups.length > 0;

// If no groups: Show "Toegang Geweigerd" (Access Denied) screen
```

### 2. Function-Based Permission System

**Location**: `frontend/src/utils/functionPermissions.ts`

Current function permissions structure:

```typescript
const DEFAULT_FUNCTION_PERMISSIONS = {
  members: {
    read: ["hdcnAdmins", "hdcnRegio_*"],
    write: ["hdcnAdmins"],
  },
  events: {
    read: ["hdcnAdmins", "hdcnEvents_Read"],
    write: ["hdcnAdmins", "hdcnEvents_Write"],
  },
  products: {
    read: ["hdcnAdmins", "hdcnProducts_Read"],
    write: ["hdcnAdmins", "hdcnProducts_Write"],
  },
  orders: {
    read: ["hdcnAdmins", "hdcnOrders_Read"],
    write: ["hdcnAdmins", "hdcnOrders_Write"],
  },
  webshop: {
    read: ["hdcnLeden", "hdcnAdmins"],
    write: ["hdcnLeden", "hdcnAdmins"],
  },
  parameters: {
    read: ["hdcnAdmins"],
    write: ["hdcnAdmins"],
  },
  memberships: {
    read: ["hdcnAdmins"],
    write: ["hdcnAdmins"],
  },
};
```

### 3. Current Cognito Groups (Discovered)

Based on the code analysis:

- **hdcnAdmins**: Full administrative access to all modules
- **hdcnLeden**: Basic member access (webshop, own profile)
- **hdcnRegio\_\***: Regional access patterns (wildcard matching)
- **hdcnEvents_Read/Write**: Event-specific permissions
- **hdcnProducts_Read/Write**: Product-specific permissions
- **hdcnOrders_Read/Write**: Order-specific permissions

### 4. Dashboard Module Visibility

**Location**: `frontend/src/pages/Dashboard.tsx`

Current logic:

```typescript
const userGroups =
  user.signInUserSession?.accessToken?.payload["cognito:groups"] || [];
const isLid = userGroups.length > 0;
const isAdmin = userGroups.includes("hdcnAdmins");

// For members: membership form + webshop
const ledenApps = [
  { id: "membership", title: "Lidmaatschap Gegevens" },
  { id: "hdcnWinkel", title: "Webshop" },
];

// For admins: additional management modules
const adminApps = [
  { id: "members", title: "Ledenadministratie" },
  { id: "events", title: "Evenementenadministratie" },
  { id: "hdcnProductManagement", title: "Product Management" },
];
```

### 5. FunctionGuard Component Usage

**Location**: `frontend/src/components/common/FunctionGuard.tsx`

Each module is wrapped with FunctionGuard:

```typescript
<FunctionGuard user={user} functionName="webshop" action="read">
  <AppCard app={webshopApp} />
</FunctionGuard>

<FunctionGuard user={user} functionName="members" action="read">
  <AppCard app={membersApp} />
</FunctionGuard>
```

## Current Parameter-Based System

### Parameter Store Structure

**Location**: `frontend/src/utils/parameterStore.tsx`

The system uses a centralized parameter store that loads configuration from:

1. API calls to DynamoDB Parameters table
2. localStorage fallback
3. Hardcoded defaults

### Parameter Categories

```typescript
const CATEGORY_MAPPING = {
  regio: "Regio",
  lidmaatschap: "Lidmaatschap",
  motormerk: "Motormerk",
  clubblad: "Clubblad",
  wiewatwaar: "WieWatWaar",
  productgroepen: "Productgroepen",
  function_permissions: "Function_permissions",
};
```

## Current Backend Field Validation

### Member Update Handler

**Location**: `backend/handler/update_member/app.py`

**Current behavior**:

- No field-level permission validation
- All fields can be updated by any authenticated user
- Uses dynamic field updating (accepts any field in request body)

```python
# Current implementation allows updating any field
for key, value in body.items():
    if key != 'member_id':
        update_expression += f", {attr_name} = :{key}"
        expression_values[f":{key}"] = value
```

### Member Create Handler

**Location**: `backend/handler/create_member/app.py`

**Current behavior**:

- No field validation
- Accepts all fields from request body
- Generates member_id and timestamps automatically

## Membership Type Field Restrictions (Frontend Only)

### Form Validation Rules

**Location**: `frontend/src/pages/MembershipForm.tsx`

```typescript
// Motor fields are required only for specific membership types
motormerk: Yup.string().when('lidmaatschap', {
  is: (val) => val === 'Gewoon lid' || val === 'Gezins lid',
  then: (schema) => schema.required('Verplicht'),
  otherwise: (schema) => schema
}),

// Same pattern for: motortype, bouwjaar, kenteken
```

### UI Conditional Rendering

```typescript
// Motor fields section only shown for specific membership types
{
  (values.lidmaatschap === "Gewoon lid" ||
    values.lidmaatschap === "Gezins lid") && (
    <>
      <Divider borderColor="orange.400" />
      <Heading size="md" color="orange.400">
        Motor Gegevens
      </Heading>
      {/* Motor fields */}
    </>
  );
}
```

### Form Submission Logic

```typescript
// Remove motor fields if membership type doesn't require them
if (
  values.lidmaatschap !== "Gewoon lid" &&
  values.lidmaatschap !== "Gezins lid"
) {
  delete payload.motormerk;
  delete payload.motortype;
  delete payload.bouwjaar;
  delete payload.kenteken;
}
```

## Gaps and Issues Identified

### 1. Backend Field Validation Missing

- No role-based field validation in backend handlers
- Any authenticated user can modify any field
- Administrative fields are not protected at API level

### 2. Membership Type Restrictions Only in Frontend

- Motor field requirements only enforced in form validation
- Backend accepts any field combination
- No server-side membership type validation

### 3. Inconsistent Field Access Control

- Some administrative fields (member_id, created_at, updated_at) are system-managed
- Other administrative fields (status, lidnummer, regio) can be modified by users
- No clear distinction between member-editable and admin-only fields

### 4. Parameter-Based Access Not Fully Implemented

- Function permissions are loaded from parameter store
- But no evidence of membership-type-specific module access
- Regional access patterns exist but not fully utilized

### 5. Missing Administrative Field Protection

- Fields like `status`, `lidnummer`, `bankrekeningnummer` should be admin-only
- Currently editable by members in the form
- No audit trail for administrative field changes

## Recommendations for Role-Based Implementation

### 1. Preserve Existing Membership Type Logic

- Keep motor field requirements based on membership type
- Maintain existing form validation patterns
- Add backend validation to match frontend rules

### 2. Implement Field-Level Permissions

- Create clear categories: personal, motorcycle, administrative
- Enforce at both frontend and backend levels
- Add role-based field access control

### 3. Enhance Function Permission System

- Extend existing FunctionPermissionManager for role-based logic
- Preserve existing group-based access patterns
- Add role inheritance and combination logic

### 4. Backend Security Implementation

- Add role validation to update_member handler
- Implement field-level permission checks
- Add audit logging for administrative field changes

### 5. Maintain Backward Compatibility

- Preserve existing parameter-based configuration
- Keep current group access patterns working
- Add role-based enhancements as additive features

## Implementation Priority

1. **High Priority**: Backend field validation and security
2. **High Priority**: Administrative field protection
3. **Medium Priority**: Enhanced role-based UI rendering
4. **Medium Priority**: Audit logging for field changes
5. **Low Priority**: Advanced regional access patterns

This mapping provides the foundation for implementing role-based authentication while preserving existing functionality and addressing current security gaps.
