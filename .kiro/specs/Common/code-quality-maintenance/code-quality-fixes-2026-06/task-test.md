# Failing Tests — Grouped Fix Plan

## Summary

| Group                                    | Tests | Root Cause                                                           | Effort       |
| ---------------------------------------- | ----- | -------------------------------------------------------------------- | ------------ |
| A. Backend passkey tests                 | 3     | Refactored app.py no longer contains `COGNITO_USER_POOL_ID` directly | Quick fix    |
| B. Frontend memberFields.permissions     | 1     | `lidnummer` field missing `computed: true` property                  | Quick fix    |
| C. Frontend PresMeet                     | 4     | i18n not initialized / component render failures                     | Medium       |
| D. Frontend Auth                         | 2     | Missing `EmailRecovery` module + missing AuthProvider wrapper        | Medium       |
| E. Frontend Services (GoogleMail/Export) | 3     | `MemberExportService.getInstance` not a function                     | Quick fix    |
| F. Frontend Regional Filtering           | 2     | Permission logic not matching expected behavior                      | Medium       |
| G. Frontend i18n textExtraction          | 1     | Missing translation keys in webshop namespace                        | Low priority |
| H. Frontend Reporting/Performance        | 3     | Undefined `.map()` + WebWorker init + DataProcessing                 | Medium       |
| I. Frontend MemberList                   | 1     | Large integration test with multiple render issues                   | Large        |
| J. Frontend UserAccountPopup             | 1     | Component render issue                                               | Quick fix    |

**Total: 3 backend + 18 frontend = 21 failing tests**

---

## Group A:

- [x] Backend Passkey Tests (3 tests) — Quick Fix

**Root cause:** The refactored `hdcn_cognito_admin/app.py` no longer contains `COGNITO_USER_POOL_ID` directly (it's in sub-modules). Tests scan `app.py` looking for the env var fallback.

**Files to fix:**

- `backend/tests/unit/test_passkey_bug_condition.py`
- `backend/tests/unit/test_passkey_preservation.py`

**Fix:** Update tests to scan the sub-modules (`user_operations.py`, `group_operations.py`, etc.) instead of only `app.py`. The pool ID is still used — just in different files.

**Failing tests:**

1. `TestPoolIdConsistency::test_hdcn_cognito_admin_fallback_pool_id`
2. `TestPoolIdConsistencyProperty::test_all_pool_id_sources_resolve_to_correct_pool`
3. `TestAdminOperationsPreservation::test_cognito_admin_uses_pool_id_env_var`

---

## Group B:

- [x] Frontend memberFields.permissions (1 test) — Quick Fix

**Root cause:** The `lidnummer` field definition in `membershipFields.ts` is missing the `computed: true` property.

**File to fix:**

- `frontend/src/config/memberFields/fields/membershipFields.ts`

**Fix:** Add `computed: true` to the `lidnummer` field definition (line with `key: 'lidnummer'`). The test at line 207 expects `field.computed` to be `true`.

**Failing test:**

1. `Membership Information Field Permissions › lidnummer field should be computed and not editable`

---

## Group C:

- [x] Frontend PresMeet (4 tests) — Medium

**Root cause:** Components use `react-i18next` `useTranslation` but tests don't properly mock the i18n instance, causing render failures.

**Files to fix:**

- `frontend/src/modules/presmeet/__tests__/BookingForm.test.tsx`
- `frontend/src/modules/presmeet/__tests__/BookingOverview.test.tsx`
- `frontend/src/modules/presmeet/__tests__/OnboardingFlow.test.tsx`
- `frontend/src/modules/presmeet/__tests__/PresMeetPage.test.tsx`

**Fix:** Add proper `jest.mock('react-i18next')` with `useTranslation` returning `{ t: (key) => key, i18n: { language: 'nl', changeLanguage: jest.fn() } }`. Also mock any services and context providers the components need.

---

## Group D:

- [x] Frontend Auth (2 tests) — Medium

**Root cause:**

1. `PasswordlessAuthenticationFlow.test.tsx` imports `../EmailRecovery` which doesn't exist
2. `AuthenticationIntegration.test.tsx` renders without `AuthProvider` wrapper

**Files to fix:**

- `frontend/src/components/auth/__tests__/PasswordlessAuthenticationFlow.test.tsx`
- `frontend/src/components/auth/__tests__/AuthenticationIntegration.test.tsx`

**Fix:**

1. Create the missing `EmailRecovery` component or update the import path
2. Wrap test renders in `AuthProvider` or mock the `useAuth` hook

---

## Group E:

- [x] Frontend Services — GoogleMail/Export (3 tests) — Quick Fix

**Root cause:** `MemberExportService.getInstance` is not a function — the service likely changed from singleton pattern to a different export.

**Files to fix:**

- `frontend/src/services/__tests__/GoogleMailService.test.ts`
- `frontend/src/services/__tests__/GoogleMailIntegration.test.ts`
- `frontend/src/services/__tests__/MemberExportService.test.ts`

**Fix:** Update tests to match the current `MemberExportService` API (check if it's now a class instantiation, a default export, or named export with different pattern).

---

## Group F:

- [x] Frontend Regional Filtering (2 tests) — Medium

**Root cause:** `userHasPermissionWithRegion` doesn't match the expected behavior — test expects `events_crud` permission for a user with certain roles in region `noord_holland` but the function returns `false`.

**Files to fix:**

- `frontend/src/utils/__tests__/regionalFiltering.test.tsx`
- `frontend/src/utils/__tests__/regionalFiltering.integration.test.ts`

**Fix:** Either the permission logic or the test expectations need to be aligned with the current role structure. Check if the role→permission mapping was updated and tests weren't.

---

## Group G:

- [x] Frontend i18n textExtraction (1 test) — Low Priority

**Root cause:** The test scans source files for untranslated Dutch text and finds hardcoded strings in webshop components (payment retry text, variant labels, etc.).

**File to fix:**

- `frontend/src/__tests__/i18n/textExtraction.test.ts`

**Fix:** Either add the missing translation keys to the webshop i18n namespace, or update the test's allowlist/ignorelist for intentionally untranslated strings.

---

## Group H:

- [x] Frontend Reporting/Performance (3 tests) — Medium

**Root cause:**

- `AddressLabelGenerator.test.tsx` — component tries to `.map()` on undefined (missing data prop mock)
- `WebWorkerManager.test.ts` — worker initialization failure handling wrong
- `DataProcessingService.performance.test.ts` — likely timeout or missing mock

**Files to fix:**

- `frontend/src/components/reporting/__tests__/AddressLabelGenerator.test.tsx`
- `frontend/src/services/__tests__/WebWorkerManager.test.ts`
- `frontend/src/services/__tests__/DataProcessingService.performance.test.ts`

**Fix:** Update mocks to provide required data props; fix worker initialization assertion.

---

## Group I:

- [x] Frontend MemberList (1 test) — Large

**Root cause:** Large integration-style test with multiple interacting components, likely outdated mocks and data assumptions.

**File to fix:**

- `frontend/src/components/__tests__/MemberList.test.tsx`

**Fix:** This is the largest test file. Update mocks for the current component API, fix data structures to match current member format, update assertions.

---

## Group J:

- [x] Frontend UserAccountPopup (1 test) — Quick Fix

**Root cause:** Component render issue — likely missing context provider or mock.

**File to fix:**

- `frontend/src/components/common/__tests__/UserAccountPopup.test.tsx`

**Fix:** Add proper `useAuth` / AuthProvider mock, or update component props to match current API.

---

## Suggested Execution Order

1. **Group A + B** (quick wins, 4 tests fixed)
2. **Group E + J** (quick service/component fixes, 4 tests fixed)
3. **Group C** (PresMeet i18n mocking pattern, 4 tests fixed)
4. **Group D + F** (auth + permissions logic, 4 tests fixed)
5. **Group H** (reporting/performance, 3 tests fixed)
6. **Group G** (i18n audit — optional/low priority)
7. **Group I** (MemberList rewrite — largest effort)
