# Implementation Plan

## Overview

Fix the event administration permission bugs and clean up pre-existing TypeScript errors in test files.

## Tasks

- [x] 1. Write bug condition exploration property test
  - [x] 1.1 Create test in `frontend/src/__tests__/functionPermissions.bug.test.ts` that verifies the bug condition
  - [x] 1.2 Test that `FunctionPermissionManager` with `Events_CRUD` role currently fails `hasAccess('events', 'write')`
  - [x] 1.3 Test that `calculatePermissions()` correctly merges `Events_CRUD` into `{ events: { write: ['all'] } }`
  - [x] 1.4 Run the test and confirm it passes (proving the bug exists in current code)

- [x] 2. Fix permission resolution in FunctionPermissionManager [depends on: 1]
  - [x] 2.1 Update `FunctionPermissionManager.create()` to call `calculatePermissions(userGroups)` instead of raw `ROLE_PERMISSIONS`
  - [x] 2.2 Update `createEnhancedPermissionManager()` with the same fix
  - [x] 2.3 Add `'all'` handling to `hasAccess()` method (matching `hasFieldAccess` behavior)

- [x] 3. Fix EventForm allowedRegions memoization [depends on: 1]
  - [x] 3.1 Import `useMemo` from React in `EventForm.tsx`
  - [x] 3.2 Memoize `allowedRegions` using `useMemo` with stable dependencies
  - [x] 3.3 Verify the `useEffect` no longer causes form state resets

- [x] 4. Write regression tests [depends on: 2, 3]
  - [x] 4.1 Test `Events_CRUD` role returns `true` for `hasAccess('events', 'write')`
  - [x] 4.2 Test users WITHOUT `Events_CRUD` get `false` for `hasAccess('events', 'write')`
  - [x] 4.3 Test `Events_Read` role works correctly for read access
  - [x] 4.4 Run all tests and confirm they pass

- [x] 5. Fix TypeScript errors in `memberReportingIntegration` test files [depends on: 4]
  - [x] 5.1 Update mock data in `src/__tests__/integration/memberReportingIntegration.test.ts` to include required `Member` type fields
  - [x] 5.2 Update mock data in `src/__tests__/memberReportingIntegration.test.tsx` to include `id`, `name`, `region`, `membershipType` fields
  - [x] 5.3 Fix `memberCount` property access (should be `count`) in line 325

- [x] 6. Fix TypeScript errors in `MaintenanceProvider.test.tsx` [depends on: 4]
  - [x] 6.1 Add proper `ApiError` type import or define the mock type correctly
  - [x] 6.2 Fix mock shape to include `status`, `message`, `isMaintenanceMode` properties
  - [x] 6.3 Fix the mock function type at line 65 to match `jest.Mock`

- [x] 7. Fix TypeScript errors in `MemberList.test.tsx` [depends on: 4]
  - [x] 7.1 Update mock user objects to include all required `AuthUser` properties (`sub`, `accessToken`)
  - [x] 7.2 Fix null user context type assignment at line 535

- [x] 8. Fix TypeScript errors in `NewPermissionSystemDemo.test.tsx` [depends on: 4]
  - [x] 8.1 Add missing `hasSystemAccess` property to all mock permission objects (6 occurrences)

- [x] 9. Fix TypeScript errors in `RoleAssignmentAfterAuthentication.test.tsx` [depends on: 4]
  - [x] 9.1 Rename `loading` to `isLoading` in mock context (line 109)
  - [x] 9.2 Remove `hasRole` references (replaced by newer auth pattern)
  - [x] 9.3 Update all mock `AuthUser` objects to include `sub` and `accessToken` properties
  - [x] 9.4 Fix null user context type at line 553

- [x] 10. Fix TypeScript errors in `userExperience.errorHandling.test.tsx` [depends on: 4]
  - [x] 10.1 Fix Promise type assertions at lines 515 and 544 to match `Promise<ApiResponse<unknown>>`

- [x] 11. Fix TypeScript errors in remaining test files [depends on: 4]
  - [x] 11.1 Fix `useAdminLocale.property.test.ts` type predicate issue at line 75
  - [x] 11.2 Fix `BookingForm.test.tsx` — add `tenant` and `source` fields to `PresMeetBooking` mock
  - [x] 11.3 Fix `WebWorkerManager.test.ts` — remove references to `calculatedFieldsComputed` and `regionallyFiltered`
  - [x] 11.4 Fix `PermissionExample.test.tsx` — add `sub` and `accessToken` to mock `AuthUser` objects

- [x] 12. Run full TypeScript check and confirm zero errors [depends on: 5, 6, 7, 8, 9, 10, 11]
  - [x] 12.1 Run `npx tsc --noEmit` from `frontend/` and confirm no errors
  - [x] 12.2 Run `npm test -- --watchAll=false` to confirm all tests still pass

## Task Dependency Graph

```
1 (exploration test)
├── 2 (permission fix)
├── 3 (EventForm memoization fix)
│
└── 4 (regression tests) [depends on: 2, 3]
    ├── 5 (memberReportingIntegration)
    ├── 6 (MaintenanceProvider)
    ├── 7 (MemberList)
    ├── 8 (NewPermissionSystemDemo)
    ├── 9 (RoleAssignmentAfterAuthentication)
    ├── 10 (userExperience.errorHandling)
    ├── 11 (remaining test files)
    │
    └── 12 (full TypeScript check) [depends on: 5-11]
```

## Notes

- Tasks 1-4 are the core bugfix (already completed and pushed to main)
- Tasks 5-12 address pre-existing TypeScript errors in test files that are unrelated to the event admin fix
- These test errors are caused by type interfaces being updated without corresponding test mock updates
- Common pattern: `AuthUser` type gained `sub` and `accessToken` fields, but test mocks weren't updated
