# Implementation Plan

## Overview

Fix the missing `LocationMapLink` component usage in `EventCalendarPage` and `EventDetailModal`. Both views render event locations as plain text instead of the clickable map link component. The fix imports and conditionally renders `LocationMapLink` for non-empty locations while preserving fallback text for empty/null locations.

## Tasks

- [x] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - Location rendered as plain text instead of clickable map link
  - **IMPORTANT**: Write this property-based test BEFORE implementing the fix
  - **CRITICAL**: This test MUST FAIL on unfixed code — failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior — it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bug exists in EventCalendarPage and EventDetailModal
  - **Scoped PBT Approach**: Use fast-check to generate arbitrary non-empty trimmed location strings; for each, render the component and assert a link with `href` containing `google.com/maps/search/?api=1&query={encodedLocation}` exists
  - Create test file: `frontend/src/pages/__tests__/CalendarLocationLink.property.test.tsx`
  - Test EventCalendarPage: render card with generated non-empty location → assert `role="link"` with Google Maps href exists
  - Test EventDetailModal: render modal with generated non-empty location → assert `role="link"` with Google Maps href exists
  - Bug condition from design: `isBugCondition(input)` where `input.view IN {EventCalendarPage, EventDetailModal} AND input.event.location IS NOT NULL AND TRIM(input.event.location) ≠ ""`
  - Expected behavior: link element present with `href = "https://www.google.com/maps/search/?api=1&query=" + encodeURIComponent(location.trim())`
  - Run test on UNFIXED code: `npx react-scripts test --watchAll=false --testPathPattern="CalendarLocationLink.property"`
  - **EXPECTED OUTCOME**: Test FAILS (this is correct — it proves the bug exists: no link rendered, only plain text)
  - Document counterexamples found (e.g., location "Amsterdam" renders as `<Text>` with no `<a>` element)
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Empty location fallback text unchanged
  - **IMPORTANT**: Follow observation-first methodology
  - **CRITICAL**: These tests MUST PASS on unfixed code — passing confirms baseline behavior to preserve
  - Create test file: `frontend/src/pages/__tests__/CalendarLocationPreservation.property.test.tsx`
  - Observe on UNFIXED code: EventCalendarPage with `location: null` renders `t('calendar.card.noLocation')` fallback
  - Observe on UNFIXED code: EventCalendarPage with `location: ""` renders `t('calendar.card.noLocation')` fallback
  - Observe on UNFIXED code: EventCalendarPage with `location: "   "` renders `t('calendar.card.noLocation')` fallback
  - Observe on UNFIXED code: EventDetailModal with `location: null` renders "—" fallback
  - Observe on UNFIXED code: EventDetailModal with `location: ""` renders "—" fallback
  - Observe on UNFIXED code: EventDetailModal with `location: "   "` renders "—" fallback
  - Use fast-check to generate empty-ish location strings: `fc.oneof(fc.constant(null), fc.constant(undefined), fc.constant(""), fc.stringOf(fc.constantFrom(" ", "\t", "\n")))` — assert fallback text renders and no `LocationMapLink` (no link role) is present
  - Verify card click behavior: clicking a calendar card still triggers `setSelectedEvent` / opens modal
  - Run tests on UNFIXED code: `npx react-scripts test --watchAll=false --testPathPattern="CalendarLocationPreservation.property"`
  - **EXPECTED OUTCOME**: Tests PASS (confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [ ] 3. Fix LocationMapLink usage in calendar views
  - [x] 3.1 Implement the fix in EventCalendarPage.tsx
    - Add import: `import { LocationMapLink } from '../modules/events/components/LocationMapLink'`
    - Replace plain `<Text>` location rendering (line ~231) with conditional:
      - If `event.location?.trim()` is truthy → render `<LocationMapLink location={event.location} fontSize="xs" color="gray.500" isTruncated maxW="100%" />`
      - Otherwise → render `<Text fontSize="xs" color="gray.500" noOfLines={1}>{t('calendar.card.noLocation')}</Text>`
    - _Bug_Condition: isBugCondition(input) where input.view = EventCalendarPage AND TRIM(input.event.location) ≠ ""_
    - _Expected_Behavior: location rendered via LocationMapLink with clickable Google Maps link_
    - _Preservation: empty/null/whitespace locations continue to show t('calendar.card.noLocation') fallback_
    - _Requirements: 2.1, 2.3, 3.1, 3.3_

  - [x] 3.2 Implement the fix in EventDetailModal.tsx
    - Add import: `import { LocationMapLink } from '../modules/events/components/LocationMapLink'`
    - Replace plain `<Text>` location rendering (line ~130) with conditional:
      - If `event.location?.trim()` is truthy → render `<LocationMapLink location={event.location} fontSize="sm" color="gray.200" />`
      - Otherwise → render `<Text fontSize="sm" color="gray.200">—</Text>`
    - _Bug_Condition: isBugCondition(input) where input.view = EventDetailModal AND TRIM(input.event.location) ≠ ""_
    - _Expected_Behavior: location rendered via LocationMapLink with clickable Google Maps link_
    - _Preservation: empty/null/whitespace locations continue to show "—" fallback_
    - _Requirements: 2.2, 2.3, 3.2, 3.3_

  - [x] 3.3 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Location rendered as clickable map link
    - **IMPORTANT**: Re-run the SAME test from task 1 — do NOT write a new test
    - The test from task 1 encodes the expected behavior (link with Google Maps href)
    - When this test passes, it confirms the expected behavior is satisfied
    - Run: `npx react-scripts test --watchAll=false --testPathPattern="CalendarLocationLink.property"`
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed — LocationMapLink now renders)
    - _Requirements: 2.1, 2.2, 2.3_

  - [x] 3.4 Verify preservation tests still pass
    - **Property 2: Preservation** - Empty location fallback text unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 — do NOT write new tests
    - Run: `npx react-scripts test --watchAll=false --testPathPattern="CalendarLocationPreservation.property"`
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions — fallback text unchanged)
    - Confirm all preservation tests still pass after fix (no regressions)
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 4. Checkpoint - Ensure all tests pass
  - Run both property test suites together: `npx react-scripts test --watchAll=false --testPathPattern="CalendarLocation"`
  - Run ESLint on modified files: `npx eslint src/pages/EventCalendarPage.tsx src/pages/EventDetailModal.tsx src/pages/__tests__/CalendarLocationLink.property.test.tsx src/pages/__tests__/CalendarLocationPreservation.property.test.tsx`
  - Run TypeScript type check: `npx tsc --noEmit`
  - Ensure all tests pass, ask the user if questions arise.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1", "2"] },
    { "id": 1, "tasks": ["3.1", "3.2"] },
    { "id": 2, "tasks": ["3.3", "3.4"] },
    { "id": 3, "tasks": ["4"] }
  ]
}
```

## Notes

- Tests use `fast-check` for property-based testing (already available in the frontend)
- `LocationMapLink` handles `stopPropagation` internally — no extra click handling needed
- Test command convention: `npx react-scripts test --watchAll=false --testPathPattern="..."`
- Both property tests target the same `__tests__` folder under `frontend/src/pages/`
