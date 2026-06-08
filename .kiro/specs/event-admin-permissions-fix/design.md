# Bugfix Design Document

## Root Cause Analysis

### Bug 1: Edit/Delete fails with "no rights" for Events_CRUD users

**Root Cause**: `FunctionPermissionManager.create()` passes the raw `ROLE_PERMISSIONS` config object directly to the constructor. `ROLE_PERMISSIONS` is keyed by **role names** (e.g., `Events_CRUD`, `Members_Read`), but `hasAccess(functionName, action)` looks up `this.permissions[functionName]` expecting **function names** (e.g., `events`, `members`) as keys.

The function `calculatePermissions(roles)` exists to merge role-based permissions into a function-keyed structure, but it is **never called** in the `create()` factory or `createEnhancedPermissionManager()`.

**Call chain**:

1. `FunctionPermissionManager.create(user)` → `new FunctionPermissionManager(user, ROLE_PERMISSIONS)`
2. `hasAccess('events', 'write')` → `this.permissions['events']` → `undefined` → returns `false`
3. `canEditEvent()` / `canDeleteEvent()` → both call `hasAccess('events', 'write')` → `false`
4. UI shows "Geen rechten" toast

**Fix**: In `FunctionPermissionManager.create()` and `createEnhancedPermissionManager()`, call `calculatePermissions(userGroups)` to build the merged function-keyed permissions, and pass THAT to the constructor instead of the raw `ROLE_PERMISSIONS`.

### Bug 2: Copy modal fields not editable + save fails validation

**Root Cause**: The `useEffect` in `EventForm.tsx` has `[event, allowedRegions]` as dependencies. `allowedRegions` is computed by `getAllowedRegions(userRoles, hasFullEventAccess)` on every render, creating a **new array reference** each time. This triggers the useEffect on every render, which resets `formData` back to the event prop values — overwriting any user input.

For the duplicate case: `event_date` is set to `''` in the duplicate object. The useEffect keeps resetting the form to this empty value, so the user can never fill it in. When they try to save, validation fails because `event_date` is empty.

**Fix**: Memoize `allowedRegions` with `useMemo` so it only recalculates when its inputs (`userRoles`, `hasFullEventAccess`) actually change. This prevents unnecessary useEffect re-fires and allows the form to retain user edits.

---

## Fix Approach

### Change 1: Fix permission resolution in FunctionPermissionManager

**File**: `frontend/src/utils/functionPermissions.ts`

**Before** (in `create()` and `createEnhancedPermissionManager()`):

```typescript
const permissionManager = new FunctionPermissionManager(user, ROLE_PERMISSIONS);
```

**After**:

```typescript
const combinedPermissions = calculatePermissions(userGroups);
const permissionManager = new FunctionPermissionManager(
  user,
  combinedPermissions,
);
```

This ensures `hasAccess('events', 'write')` finds the merged `events: { write: ['all'] }` entry from the user's `Events_CRUD` role.

### Change 2: Memoize allowedRegions in EventForm

**File**: `frontend/src/modules/events/components/EventForm.tsx`

**Before**:

```typescript
const allowedRegions = getAllowedRegions(userRoles, hasFullEventAccess);
```

**After**:

```typescript
const allowedRegions = useMemo(
  () => getAllowedRegions(userRoles, hasFullEventAccess),
  [JSON.stringify(userRoles), hasFullEventAccess],
);
```

This prevents the useEffect from re-firing on every render and preserves user input in the form.

---

## Affected Files

| File                                                   | Change Type | Description                                                                        |
| ------------------------------------------------------ | ----------- | ---------------------------------------------------------------------------------- |
| `frontend/src/utils/functionPermissions.ts`            | Bug fix     | Use `calculatePermissions()` in `create()` and `createEnhancedPermissionManager()` |
| `frontend/src/modules/events/components/EventForm.tsx` | Bug fix     | Memoize `allowedRegions` to prevent useEffect re-fires                             |

## Risk Assessment

- **Low risk**: Both changes are targeted fixes that don't alter the permission model or form logic, only how data flows into them
- **Regression concern**: The `calculatePermissions()` function already exists and is tested — we're just using it where it should have been used from the start
- **No backend changes needed**: The backend permission checks (via `validate_permissions_with_regions`) are unaffected; this is purely a frontend display/UX issue

## Verification Strategy

1. Unit test: `FunctionPermissionManager` with `Events_CRUD` role returns `true` for `hasAccess('events', 'write')`
2. Unit test: `FunctionPermissionManager` without `Events_CRUD` still returns `false` for `hasAccess('events', 'write')`
3. Manual test: Login as webmaster@h-dcn.nl → edit/delete events works
4. Manual test: Duplicate event → fields are editable, can save with filled-in date
