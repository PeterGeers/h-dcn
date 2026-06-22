# Requirements Document

## Introduction

Refactor the frontend to extract all generic closed-community-booking components from the legacy `modules/presmeet/` folder into a new `modules/eventBooking/` module, then remove dead presmeet code and update routes. This is a purely structural refactor with no behavior changes — all existing functionality must remain intact after the move.

## Glossary

- **EventBooking_Module**: The new frontend module at `frontend/src/modules/eventBooking/` containing all generic event booking components, hooks, types, services, admin pages, and tests.
- **Presmeet_Module**: The legacy frontend module at `frontend/src/modules/presmeet/` that currently contains both PresMeet-specific and generic booking code mixed together.
- **Generic_Booking_Component**: A component designed for reuse across any closed-community event booking flow (not PresMeet-specific). Includes: PasswordGate, RegistrySelector, RowCard, AccessDeniedScreen, ClaimAction, BookingWizard, PersonCard, EffectiveLimits, ProductConfigurator, DelegateManager, ReadOnlyView.
- **Admin_Component**: An administrative component for managing event bookings. Includes: AdminClaimsManagement, AdminOrderLockUnlock, AdminPaymentAndPdf, EventDashboard.
- **Dead_Code**: Source files in the Presmeet_Module that are fully superseded by EventBooking_Module equivalents and have no remaining consumers.
- **Import_Path**: A TypeScript import statement referencing a file's location relative to the project source tree.
- **Route_Definition**: A `<Route>` element in App.tsx mapping a URL pattern to a React component.
- **Type_Check**: Running `npx tsc --noEmit` with zero errors on the entire frontend.
- **Lint_Check**: Running `npx eslint` on all modified files with zero errors.

## Requirements

### Requirement 1: Create eventBooking Module Structure

**User Story:** As a developer, I want a properly structured `eventBooking` module, so that generic booking code is organized consistently with other modules (members, products, webshop).

#### Acceptance Criteria

1. THE EventBooking_Module SHALL contain the following subdirectories: `components/`, `hooks/`, `types/`, `services/`, `admin/`, `pages/`, `__tests__/`
2. THE EventBooking_Module SHALL follow the same directory structure pattern as the existing members and products modules

### Requirement 2: Move Generic Booking Components

**User Story:** As a developer, I want all booking components relocated to the eventBooking module, so that the complete event booking feature is self-contained.

#### Acceptance Criteria

1. WHEN the refactor is complete, THE EventBooking_Module SHALL contain the following components in `components/`: PasswordGate.tsx, RegistrySelector.tsx, RowCard.tsx, AccessDeniedScreen.tsx, ClaimAction.tsx, BookingWizard.tsx, PersonCard.tsx, EffectiveLimits.tsx, ProductConfigurator.tsx, DelegateManager.tsx, ReadOnlyView.tsx
2. WHEN the refactor is complete, THE EventBooking_Module SHALL contain the following components that are actively used by EventBookingPage: OnboardingFlow.tsx, PaymentPanel.tsx, BookingSummaryPdf.tsx, ClubLogoUploader.tsx
3. WHEN the refactor is complete, THE EventBooking_Module SHALL contain the following admin components in `admin/`: AdminClaimsManagement.tsx, AdminOrderLockUnlock.tsx, AdminPaymentAndPdf.tsx, EventDashboard.tsx
4. WHEN the refactor is complete, THE EventBooking_Module SHALL contain the hooks `useEffectiveLimits.ts` and `useAutoSave.ts` in `hooks/`
5. WHEN the refactor is complete, THE EventBooking_Module SHALL contain an `eventBookingApi.ts` service in `services/` providing the v3 generic API calls (getOrder, saveOrder, submitOrder, pay, getEvent, getProducts, getReport, manageDelegates, resendDelegateInvitation) without the legacy presmeetService methods
6. WHEN the refactor is complete, THE EventBooking_Module SHALL contain clean TypeScript interfaces in `types/` based on `presmeet.types.ts` (the v3 generic types: Order, Event, Product, Constraint, OrderItem, Payment, Report types) with legacy presmeet naming removed
7. WHEN the refactor is complete, THE EventBooking_Module types SHALL NOT include PresMeet-specific domain types from the original `presmeet.ts` (e.g., ProductType union of "meeting_ticket"/"party_ticket", PresMeet-specific BookingFormData with delegates/guests/transfers, ClubRegistry)
8. WHEN the refactor is complete, THE EventBooking_Module SHALL contain the EventBookingPage.tsx in `pages/`
9. WHEN the refactor is complete, THE EventBooking_Module SHALL contain all property-based tests and unit tests relocated from `modules/presmeet/__tests__/` in `__tests__/`

### Requirement 3: Move EventRegisterPage

**User Story:** As a developer, I want EventRegisterPage relocated from the events module to eventBooking, so that booking-related pages live together in the booking module.

#### Acceptance Criteria

1. WHEN the refactor is complete, THE EventBooking_Module SHALL contain EventRegisterPage.tsx in `pages/`
2. WHEN EventRegisterPage is moved, THE Route_Definition for `/events/:slug/register` SHALL reference the new location in EventBooking_Module

### Requirement 4: Update All Import Paths

**User Story:** As a developer, I want all import paths updated after file moves, so that the codebase compiles without errors.

#### Acceptance Criteria

1. WHEN files are moved to EventBooking_Module, THE Import_Path in every moved file SHALL reference sibling files using the new module-relative paths
2. WHEN files are moved to EventBooking_Module, THE Import_Path in App.tsx SHALL reference moved components from their new EventBooking_Module locations
3. WHEN all moves are complete, THE Type_Check SHALL pass with zero errors
4. WHEN all moves are complete, THE Lint_Check SHALL pass with zero errors on all modified files

### Requirement 5: Update Route Definitions

**User Story:** As a developer, I want route definitions updated to reference eventBooking module pages, so that URL routing works correctly after the move.

#### Acceptance Criteria

1. WHEN the refactor is complete, THE Route_Definition for `/events/:eventId/booking` SHALL lazy-load EventBookingPage from `modules/eventBooking/pages/EventBookingPage`
2. WHEN the refactor is complete, THE Route_Definition for `/events/:slug/register` SHALL lazy-load EventRegisterPage from `modules/eventBooking/pages/EventRegisterPage`

### Requirement 6: Delete Entire Presmeet Module

**User Story:** As a developer, I want the entire presmeet module deleted after migration, so that there is no dead code or confusion about which module to use.

#### Acceptance Criteria

1. WHEN all generic components, hooks, utils, services, admin, and tests have been moved to EventBooking_Module, THE entire `modules/presmeet/` directory SHALL be deleted
2. WHEN the module is deleted, THE `PresMeetPage.tsx` SHALL be removed (superseded by EventBookingPage.tsx with URL-based event_id)
3. WHEN the module is deleted, THE `usePresMeetBooking.ts` hook SHALL be removed (legacy hook using old presmeet.ts types and presmeetService endpoints)
4. WHEN the module is deleted, THE `presmeet.ts` types file SHALL be removed (PresMeet-specific domain types: ProductType, CartItem, BookingFormData, ClubRegistry)
5. WHEN the module is deleted, THE legacy `presmeetService` object in presmeetApi.ts SHALL be removed (old `/presmeet/*` endpoints that are superseded by unified `/booking` endpoints)
6. WHEN the module is deleted, THE components that are PresMeet-specific UI wrappers (AdminDashboard, BookingForm, BookingOverview, BookingSummaryPdf, ClubLogoUploader, DelegateSection, EventInfoHeader, GuestSection, OnboardingFlow, PaymentPanel, PaymentSection, SaveStatusIndicator, SubmitPanel, TransferSection, AdminRouter, ReportView) SHALL be either moved to eventBooking (if still used by EventBookingPage) or deleted (if only used by PresMeetPage)
7. WHEN dead code is removed, THE Type_Check SHALL pass with zero errors
8. WHEN dead code is removed, THE Lint_Check SHALL report zero unused-import errors across the entire frontend
9. WHEN the refactor is complete, THE codebase SHALL contain zero import statements referencing `modules/presmeet/`

### Requirement 7: Remove Presmeet Route

**User Story:** As a developer, I want the presmeet route removed, so that no dead route entries remain in the application.

#### Acceptance Criteria

1. WHEN the refactor is complete, THE Route_Definition for `/presmeet` SHALL be removed from App.tsx
2. WHEN the refactor is complete, THE App.tsx SHALL NOT contain any lazy import referencing `modules/presmeet/`
3. WHEN a user navigates to `/presmeet`, THE application SHALL display the default 404 / catch-all behavior

### Requirement 8: Preserve Behavior

**User Story:** As a developer, I want zero functional regressions after this refactor, so that users experience no change in behavior.

#### Acceptance Criteria

1. THE EventBooking_Module components SHALL produce identical rendered output and behavior as they did when located in Presmeet_Module
2. THE EventBooking_Module SHALL use the `eventBooking` translation namespace (already in use)
3. WHEN all moves and deletions are complete, THE existing property-based tests SHALL pass without modification to test assertions
4. WHEN all moves and deletions are complete, THE existing unit tests SHALL pass with only import path changes (no assertion changes)
5. THE backend handlers SHALL NOT be modified by this refactor (purely frontend structural change)

### Requirement 9: No Remaining Presmeet References

**User Story:** As a developer, I want zero references to the presmeet module anywhere in the codebase, so that the migration is complete and clean.

#### Acceptance Criteria

1. WHEN the refactor is complete, THE codebase SHALL contain zero import statements referencing `modules/presmeet/`
2. WHEN the refactor is complete, THE `modules/presmeet/` directory SHALL NOT exist
3. WHEN the refactor is complete, THE App.tsx SHALL NOT contain any lazy import referencing `modules/presmeet/`

### Requirement 10: Move Utility Files to EventBooking

**User Story:** As a developer, I want booking-related utility files moved to the eventBooking module, so that all event booking logic is co-located.

#### Acceptance Criteria

1. WHEN the refactor is complete, THE EventBooking_Module SHALL contain a `utils/` directory with the booking-related utility files: `accessControl.ts`, `cartBuilder.ts`, `orderTransformer.ts`, `pdfGenerator.ts`, `personManagement.ts`, `priceCalculator.ts`, `validation.ts`, `versionCheck.ts`
2. WHEN utility files are moved, THE Import_Path in all consuming files SHALL be updated to reference the new EventBooking_Module location
3. IF `cartBuilder.test.ts` exists in presmeet utils, THEN it SHALL be moved to `modules/eventBooking/__tests__/` or `modules/eventBooking/utils/`

### Requirement 11: Explicit File Move Mapping

**User Story:** As a developer, I want a defined mapping of every file from presmeet to eventBooking, so that nothing is missed or left behind.

#### Acceptance Criteria

1. THE following components SHALL be moved from `modules/presmeet/components/` to `modules/eventBooking/components/`: PasswordGate.tsx, RegistrySelector.tsx, RowCard.tsx, AccessDeniedScreen.tsx, ClaimAction.tsx, BookingWizard.tsx, PersonCard.tsx, EffectiveLimits.tsx, ProductConfigurator.tsx, DelegateManager.tsx, ReadOnlyView.tsx
2. THE following admin components SHALL be moved from `modules/presmeet/admin/` to `modules/eventBooking/admin/`: AdminClaimsManagement.tsx, AdminOrderLockUnlock.tsx, AdminPaymentAndPdf.tsx, EventDashboard.tsx
3. THE following hooks SHALL be moved from `modules/presmeet/hooks/` to `modules/eventBooking/hooks/`: useEffectiveLimits.ts, useAutoSave.ts
4. THE service file `modules/presmeet/services/presmeetApi.ts` SHALL be renamed to `modules/eventBooking/services/eventBookingApi.ts` with all internal references to "presmeet" removed
5. THE types file `modules/presmeet/types/presmeet.types.ts` SHALL be split: generic booking types move to `modules/eventBooking/types/eventBooking.types.ts`, PresMeet-specific types (ProductType, ClubRegistry, BookingFormData with delegates/guests/transfers) SHALL be deleted
6. THE property tests in `modules/presmeet/__tests__/` SHALL be moved to `modules/eventBooking/__tests__/`
7. THE page `modules/events/EventRegisterPage.tsx` SHALL be moved to `modules/eventBooking/pages/EventRegisterPage.tsx`
8. AFTER all moves are complete, THE `modules/presmeet/` directory SHALL be entirely deleted — no files shall remain

### Requirement 12: Execution Phasing

**User Story:** As a developer, I want the refactor executed in strict phases, so that each phase can be verified independently.

#### Acceptance Criteria

1. Phase 1 (Isolate): THE EventBooking_Module directory structure SHALL be created first, then all generic components, hooks, services, types, admin, pages, and tests SHALL be moved with import paths updated; THE Type_Check and Lint_Check SHALL pass at the end of Phase 1
2. Phase 2 (Delete dead code): THE entire `modules/presmeet/` directory SHALL be deleted including all remaining files; THE Type_Check and Lint_Check SHALL pass at the end of Phase 2
3. Phase 3 (Disable routes): THE presmeet route SHALL be removed from App.tsx; THE old `/presmeet` URL SHALL resolve to 404; THE EventBooking routes SHALL reference the new module locations; THE Type_Check and Lint_Check SHALL pass at the end of Phase 3
4. EACH phase SHALL be committed separately with a descriptive commit message so that the refactor can be reviewed or reverted per-phase
