# Implementation Plan: Events Calendar Card

## Overview

Consolidate the Dashboard's multiple `EventBookingCard` components into a single static "Events / Calendar" `AppCard` that navigates to `/events/calendar`. Modify `EventCalendarPage` to detect auth state and branch click behavior (authenticated → SPA navigate to booking, unauthenticated → open new tab to info page). Add translation keys for all 8 languages.

## Tasks

- [x] 1. Add translation keys for all 8 languages
  - [x] 1.1 Add `cards.events_calendar_title` and `cards.events_calendar_desc` keys to the `dashboard` namespace in all 8 locales (nl, en, de, fr, es, it, da, sv)
    - Update both `frontend/src/locales/{lang}/dashboard.json` and `frontend/public/locales/{lang}/dashboard.json`
    - Title: localized "Events / Kalender" (or equivalent per language)
    - Description: localized "Bekijk en boek evenementen" (or equivalent per language)
    - _Requirements: 1.3_

- [x] 2. Replace EventBookingCard with static Events Calendar card on Dashboard
  - [x] 2.1 Remove the `EventBookingCard` component and its usage from `Dashboard.tsx`
    - Delete the entire `EventBookingCard` function (lines 15–87)
    - Remove the `eventBookingApi` import
    - Remove both usages: inside the `isEventParticipant` grid and inside the `FunctionGuard` for hdcnLeden/event_participant
    - _Requirements: 1.1_

  - [x] 2.2 Add a single static `AppCard` for Events/Calendar in `Dashboard.tsx`
    - Add card with `id: 'events-calendar'`, `icon: '📅'`, localized title/description from `dashboard` namespace, `onClick: () => navigate('/events/calendar')`
    - Place inside a `FunctionGuard` with `requiredRoles={['hdcnLeden', 'event_participant']}`
    - Also add the card in the `isEventParticipant` section (replacing `EventBookingCard`)
    - Card must render regardless of whether published events exist (no API dependency)
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [x] 2.3 Write unit tests for Dashboard events calendar card
    - Test that single events-calendar card renders with correct icon, title, description
    - Test that clicking the card navigates to `/events/calendar`
    - Test that card is visible even when no events exist (no API call)
    - Test that `EventBookingCard` component is no longer rendered
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 3. Checkpoint - Verify Dashboard changes
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Make EventCalendarPage context-aware with auth-based click behavior
  - [x] 4.1 Add auth detection and conditional navigation to `EventCalendarPage.tsx`
    - Import `useAuth` from `'../context/AuthProvider'` and `useNavigate` from `'react-router-dom'`
    - Destructure `isAuthenticated` from `useAuth()` and get `navigate` from `useNavigate()`
    - Modify the event card `onClick`: if authenticated → `navigate(`/events/${event.event_id}/booking`)`, else → `window.open(`/events/${event.slug}/info`, '_blank')`
    - _Requirements: 2.1, 2.3, 2.4_

  - [x] 4.2 Add AbortController timeout and retry button to `EventCalendarPage.tsx`
    - Wrap fetch with AbortController, set 10-second timeout via `setTimeout`
    - On abort/error, show localized error message + retry button
    - Retry button re-triggers the fetch (reset error state, refetch)
    - Clean up AbortController on unmount
    - Show loading spinner while fetching
    - _Requirements: 2.5, 2.6, 2.7_

  - [x] 4.3 Write unit tests for EventCalendarPage auth-aware behavior
    - Test: authenticated user click calls `navigate('/events/{event_id}/booking')`
    - Test: unauthenticated user click calls `window.open('/events/{slug}/info', '_blank')`
    - Test: same `/events-public` endpoint used regardless of auth state
    - Test: fetch failure shows error message + retry button
    - Test: retry button re-triggers fetch
    - Test: 10-second timeout triggers error state
    - Test: loading spinner shown while fetching
    - Mock `useAuth`, `useNavigate`, `window.open`, and `fetch`
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

- [x] 5. Final checkpoint - Ensure all tests pass and lint is clean
  - Ensure all tests pass, ask the user if questions arise.
  - Run `npx tsc --noEmit` for type checking
  - Run `npx eslint` on modified files

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- No new routes, API endpoints, or backend changes needed
- The `/events/calendar` route remains public — `useAuth()` works because `AuthProvider` wraps the entire Router in `App.tsx`
- Property-based testing is not applicable for this feature (simple UI wiring with conditional navigation)
- Translation keys must be added to BOTH `src/locales/` AND `public/locales/` directories

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["2.1", "4.1"] },
    { "id": 2, "tasks": ["2.2", "4.2"] },
    { "id": 3, "tasks": ["2.3", "4.3"] }
  ]
}
```
