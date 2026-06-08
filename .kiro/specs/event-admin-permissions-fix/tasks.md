# Tasks

## Task 1: Write bug condition exploration property test

- [x] Create a property-based test in `backend/tests/unit/test_event_admin_permissions_bug.py` that verifies the bug condition
- [x] Test that `FunctionPermissionManager` with `Events_CRUD` role currently fails `hasAccess('events', 'write')` — confirming the bug exists
- [x] Test that the `calculatePermissions()` function correctly merges `Events_CRUD` into `{ events: { write: ['all'] } }`
- [x] Run the test and confirm it fails (proving the bug exists in current code)

## Task 2: Fix permission resolution in FunctionPermissionManager [depends on: Task 1]

- [x] In `frontend/src/utils/functionPermissions.ts`, update `FunctionPermissionManager.create()` to call `calculatePermissions(userGroups)` and pass the result to the constructor instead of raw `ROLE_PERMISSIONS`
- [x] Update `createEnhancedPermissionManager()` with the same fix
- [x] Ensure the `hasAccess('events', 'write')` call now correctly resolves for users with `Events_CRUD` role

## Task 3: Fix EventForm allowedRegions memoization [depends on: Task 1]

- [x] In `frontend/src/modules/events/components/EventForm.tsx`, import `useMemo` from React
- [x] Memoize `allowedRegions` using `useMemo` with stable dependencies so the `useEffect` doesn't re-fire on every render
- [x] Verify that the form's `useEffect` dependency on `allowedRegions` no longer causes form state resets

## Task 4: Write regression tests [depends on: Task 2, Task 3]

- [x] Write a frontend unit test confirming `FunctionPermissionManager` with `Events_CRUD` role returns `true` for `hasAccess('events', 'write')`
- [x] Write a test confirming users WITHOUT `Events_CRUD` still get `false` for `hasAccess('events', 'write')`
- [x] Write a test confirming `hasAccess('events', 'read')` works correctly for `Events_Read` role
- [x] Run all tests and confirm they pass
