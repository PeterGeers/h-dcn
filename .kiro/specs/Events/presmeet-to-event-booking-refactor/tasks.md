# Implementation Plan: presmeet-to-event-booking-refactor

## Overview

Structural frontend refactor executed in 3 strict phases. Each phase is independently verifiable via `npx tsc --noEmit` and ESLint, and committed separately. Uses `smart_relocate` for all file moves to auto-update imports across the codebase.

## Tasks

- [x] 1. Phase 1 — Create eventBooking module and move all generic files
  - [x] 1.1 Move generic booking components to eventBooking/components/
    - Use `smart_relocate` to move these files from `modules/presmeet/components/` to `modules/eventBooking/components/`:
      - AccessDeniedScreen.tsx, BookingWizard.tsx, BookingSummaryPdf.tsx, ClaimAction.tsx, ClubLogoUploader.tsx, DelegateManager.tsx, EffectiveLimits.tsx, OnboardingFlow.tsx, PasswordGate.tsx, PaymentPanel.tsx, PersonCard.tsx, ProductConfigurator.tsx, ReadOnlyView.tsx, RegistrySelector.tsx, RowCard.tsx
    - _Requirements: 2.1, 2.2, 11.1_

  - [x] 1.2 Move admin components to eventBooking/admin/
    - Use `smart_relocate` to move from `modules/presmeet/admin/` to `modules/eventBooking/admin/`:
      - AdminClaimsManagement.tsx, AdminOrderLockUnlock.tsx, AdminPaymentAndPdf.tsx, EventDashboard.tsx
    - Do NOT move AdminRouter.tsx or ReportView.tsx (these will be deleted in Phase 2)
    - _Requirements: 2.3, 11.2_

  - [x] 1.3 Move hooks to eventBooking/hooks/
    - Use `smart_relocate` to move from `modules/presmeet/hooks/` to `modules/eventBooking/hooks/`:
      - useEffectiveLimits.ts, useAutoSave.ts
    - Do NOT move usePresMeetBooking.ts (will be deleted in Phase 2)
    - _Requirements: 2.4, 11.3_

  - [x] 1.4 Move and rename service file to eventBooking/services/eventBookingApi.ts
    - Use `smart_relocate` to move `modules/presmeet/services/presmeetApi.ts` to `modules/eventBooking/services/eventBookingApi.ts`
    - After the move, edit the file to:
      - Rename the exported `presmeetApi` object to `eventBookingApi`
      - Remove the entire `presmeetService` legacy object (old `/presmeet/*` endpoints)
      - Remove imports from `types/presmeet.ts` (the deleted PresMeet-specific types)
      - Rename `PresMeetApiError` type references to `EventBookingApiError`
    - Update all consumers that reference the old export name
    - _Requirements: 2.5, 11.4_

  - [x] 1.5 Move and rename types file to eventBooking/types/eventBooking.types.ts
    - Use `smart_relocate` to move `modules/presmeet/types/presmeet.types.ts` to `modules/eventBooking/types/eventBooking.types.ts`
    - After the move, rename `PresMeetApiError` to `EventBookingApiError` in the types file
    - Do NOT move `modules/presmeet/types/presmeet.ts` (will be deleted in Phase 2)
    - _Requirements: 2.6, 2.7, 11.5_

  - [x] 1.6 Move utility files to eventBooking/utils/
    - Use `smart_relocate` to move all files from `modules/presmeet/utils/` to `modules/eventBooking/utils/`:
      - accessControl.ts, cartBuilder.ts, cartBuilder.test.ts, orderTransformer.ts, pdfGenerator.ts, personManagement.ts, priceCalculator.ts, validation.ts, versionCheck.ts
    - _Requirements: 10.1, 10.2, 10.3_

  - [x] 1.7 Move pages to eventBooking/pages/
    - Use `smart_relocate` to move `modules/presmeet/EventBookingPage.tsx` to `modules/eventBooking/pages/EventBookingPage.tsx`
    - Use `smart_relocate` to move `modules/events/EventRegisterPage.tsx` to `modules/eventBooking/pages/EventRegisterPage.tsx`
    - Do NOT move PresMeetPage.tsx (will be deleted in Phase 2)
    - _Requirements: 2.8, 3.1, 11.7_

  - [x] 1.8 Move test files to eventBooking/**tests**/
    - Use `smart_relocate` to move the following from `modules/presmeet/__tests__/` to `modules/eventBooking/__tests__/`:
      - accessControl.property.test.ts, bookingCalculations.property.test.ts, BookingWizard.test.tsx, cartBuilder.property.test.ts, clubSearch.property.test.ts, effectiveLimits.property.test.ts, OnboardingFlow.test.tsx, optimisticLocking.property.test.ts, orderTransformer.test.ts, pdfGeneration.property.test.ts, pdfGenerator.property.test.ts, personManagement.property.test.ts, priceCalculator.test.ts, validation.property.test.ts, validation.test.ts
    - Use `smart_relocate` to move from `modules/presmeet/components/__tests__/` to `modules/eventBooking/__tests__/`:
      - BookingSummaryPdf.test.tsx, ClubLogoUploader.test.tsx, DelegateManager.test.tsx, PaymentPanel.test.tsx
    - Do NOT move: AdminDashboard.test.tsx, BookingForm.test.tsx, BookingOverview.test.tsx, PresMeetPage.404.test.tsx, PresMeetPage.preservation.test.tsx, PresMeetPage.test.tsx (deleted in Phase 2)
    - _Requirements: 2.9, 11.6_

  - [x] 1.9 Verify Phase 1 — type check and lint
    - Run `npx tsc --noEmit` from `frontend/` — must produce zero errors
    - Run `npx eslint` on all modified files — zero errors
    - Run moved tests: `npx react-scripts test --watchAll=false --testPathPattern="eventBooking"`
    - Fix any remaining import issues (internal references between moved files)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 12.1_

- [x] 2. Checkpoint — Phase 1 complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. Phase 2 — Delete entire presmeet module
  - [x] 3.1 Delete the entire modules/presmeet/ directory
    - Delete the `frontend/src/modules/presmeet/` directory and all remaining files:
      - PresMeetPage.tsx, usePresMeetBooking.ts, types/presmeet.ts
      - AdminRouter.tsx, ReportView.tsx
      - AdminDashboard.tsx, BookingForm.tsx, BookingOverview.tsx, DelegateSection.tsx, EventInfoHeader.tsx, GuestSection.tsx, PaymentSection.tsx, SaveStatusIndicator.tsx, SubmitPanel.tsx, TransferSection.tsx
      - Remaining test files: AdminDashboard.test.tsx, BookingForm.test.tsx, BookingOverview.test.tsx, PresMeetPage.\*.test.tsx
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 9.2, 11.8_

  - [x] 3.2 Verify Phase 2 — type check, lint, and dead reference check
    - Run `npx tsc --noEmit` from `frontend/` — must produce zero errors
    - Run `npx eslint` on all modified files — zero errors
    - Run `grep -r "modules/presmeet" frontend/src/ --include="*.ts" --include="*.tsx"` — zero matches
    - If any files still reference `modules/presmeet/`, fix those imports
    - _Requirements: 6.7, 6.8, 6.9, 9.1, 12.2_

- [x] 4. Checkpoint — Phase 2 complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Phase 3 — Remove presmeet route and update lazy imports
  - [x] 5.1 Update App.tsx routes and lazy imports
    - Remove the `/presmeet` route definition from App.tsx
    - Remove the lazy import statement referencing `modules/presmeet/`
    - Update the lazy import for EventBookingPage to: `modules/eventBooking/pages/EventBookingPage`
    - Update the lazy import for EventRegisterPage to: `modules/eventBooking/pages/EventRegisterPage`
    - Verify the `/events/:eventId/booking` route references EventBookingPage from the new location
    - Verify the `/events/:slug/register` route references EventRegisterPage from the new location
    - _Requirements: 5.1, 5.2, 7.1, 7.2, 7.3, 3.2_

  - [x] 5.2 Verify Phase 3 — type check, lint, and final validation
    - Run `npx tsc --noEmit` from `frontend/` — must produce zero errors
    - Run `npx eslint` on all modified files — zero errors
    - Run `grep -r "modules/presmeet" frontend/src/ --include="*.ts" --include="*.tsx"` — zero matches
    - Run `grep -r "presmeet" frontend/src/App.tsx` — zero matches
    - Verify `modules/presmeet/` directory does not exist
    - _Requirements: 4.3, 4.4, 7.2, 9.1, 9.2, 9.3, 12.3_

- [x] 6. Final checkpoint — All phases complete
  - Ensure all tests pass, ask the user if questions arise.
  - Run full eventBooking test suite: `npx react-scripts test --watchAll=false --testPathPattern="eventBooking"`
  - Verify zero behavioral regressions: tests pass with only import path changes, no assertion modifications.
  - _Requirements: 8.1, 8.3, 8.4, 8.5_

## Notes

- All file moves use `smart_relocate` which auto-updates import paths across the codebase
- Each phase is committed separately with a descriptive commit message (Requirement 12.4)
- No property-based tests are added — this is a structural refactor with no new logic
- Existing property tests and unit tests are moved with only import path changes
- Backend is completely untouched (Requirement 8.5)
- The `eventBooking` translation namespace is already in use — no i18n changes needed (Requirement 8.2)
- Phase 1 moves ~30 files; Phase 2 deletes ~20 remaining dead files; Phase 3 edits App.tsx only

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3", "1.6"] },
    { "id": 1, "tasks": ["1.4", "1.5", "1.7"] },
    { "id": 2, "tasks": ["1.8"] },
    { "id": 3, "tasks": ["1.9"] },
    { "id": 4, "tasks": ["3.1"] },
    { "id": 5, "tasks": ["3.2"] },
    { "id": 6, "tasks": ["5.1"] },
    { "id": 7, "tasks": ["5.2"] }
  ]
}
```
