# Implementation Plan: Events Calendar Card (v2)

## Overview

Fix the routing issue (Dashboard card drops SPA shell) and replace the direct-navigate click behavior with a detail modal. Dashboard card navigates to `/calendar` (protected route inside AppContent). Clicking event cards opens an `EventDetailModal` with poster, info, and contextual CTA button.

## Tasks

- [x] 1. Add translation keys for all 8 languages
  - [x] 1.1 Add `cards.events_calendar_title` and `cards.events_calendar_desc` keys to the `dashboard` namespace in all 8 locales
    - Already done in previous implementation

- [x] 2. Replace EventBookingCard with static Events Calendar card on Dashboard
  - [x] 2.1 Remove `EventBookingCard` component from Dashboard
    - Already done in previous implementation
  - [x] 2.2 Add single static `AppCard` for Events/Calendar
    - Already done (but navigates to wrong path — fixed in task 3)

- [x] 3. Fix routing: add `/calendar` as protected route inside AppContent
  - [x] 3.1 Add `/calendar` route in `App.tsx` inside `AppContent`'s `<Routes>`
    - Import `EventCalendarPage` (already lazy-loaded)
    - Add: `<Route path="/calendar" element={<EventCalendarPage />} />`
    - Keep the public `/events/calendar` route unchanged (standalone, for external visitors)

  - [x] 3.2 Update Dashboard card to navigate to `/calendar`
    - Change both instances of `navigate('/events/calendar')` to `navigate('/calendar')`
    - Change both instances of `path: '/events/calendar'` to `path: '/calendar'`

  - [x] 3.3 Update Dashboard test to expect `/calendar`
    - No Dashboard test file exists — N/A

- [x] 4. Backend: add registration fields to public endpoint
  - [x] 4.1 Add `registration_open`, `registration_close`, `payment_deadline` to `PUBLIC_FIELDS` in `backend/handler/get_events_public/app.py`
    - These fields allow the frontend to determine if an event is bookable

- [x] 5. Create EventDetailModal component
  - [x] 5.1 Create `frontend/src/pages/EventDetailModal.tsx`
    - Chakra UI Modal (size `xl`, dark theme: bg `gray.900`)
    - Props: `event: PublicEvent | null`, `isOpen: boolean`, `onClose: () => void`
    - Content (mirrors EventLandingPage poster-view):
      - Poster image (full-width, `objectFit="contain"`)
      - Event name (Heading, orange)
      - Description (`whiteSpace="pre-wrap"`, if available)
      - Details grid: dates, location, type, region
    - CTA button logic:
      - Authenticated + bookable: "Book" button → `navigate('/events/${event.event_id}/booking')`
      - Unauthenticated + bookable: "Register" button → `window.open('/events/${event.slug}/register', '_blank')`
      - Not bookable: no CTA
    - `isBookable` helper: `!!(event.registration_open || event.registration_close || event.payment_deadline)`
    - Add translation keys for modal: `calendar.modal.book`, `calendar.modal.register` in `events` namespace (all 8 languages)

- [x] 6. Update EventCalendarPage to use modal
  - [x] 6.1 Update `PublicEvent` interface in `EventCalendarPage.tsx`
    - Add: `landing_page?: Record<string, any>`
    - Add: `registration_open?: string`
    - Add: `registration_close?: string`
    - Add: `payment_deadline?: string`

  - [x] 6.2 Replace click handler with modal logic
    - Add state: `const [selectedEvent, setSelectedEvent] = useState<PublicEvent | null>(null)`
    - Keep `useAuth` import for `isAuthenticated`
    - Card `onClick`:
      - If `!isAuthenticated && event.landing_page && Object.keys(event.landing_page).length > 0`: `window.open('/events/${event.slug}/info', '_blank')`
      - Otherwise: `setSelectedEvent(event)`
    - Render `<EventDetailModal event={selectedEvent} isOpen={selectedEvent !== null} onClose={() => setSelectedEvent(null)} />`

  - [x] 6.3 Remove unused `useNavigate` from EventCalendarPage (navigation now lives in modal)

- [x] 7. Update tests
  - [x] 7.1 Update `EventCalendarPage.test.tsx`
    - Test: authenticated click opens modal (does not navigate away)
    - Test: unauthenticated + landing page event opens new tab to `/events/{slug}/info`
    - Test: unauthenticated + no landing page opens modal
    - Test: modal shows poster, name, dates, location
    - Test: modal shows "Book" CTA when authenticated + bookable
    - Test: modal shows "Register" CTA when unauthenticated + bookable + no landing page
    - Test: modal has no CTA when event not bookable
    - Test: "Book" navigates to `/events/{event_id}/booking`
    - Test: "Register" opens `/events/{slug}/register` in new tab
    - Test: closing modal resets state
    - Test: fetch failure + retry
    - Test: loading spinner

- [x] 8. Verify and lint
  - [x] 8.1 Run `npx tsc --noEmit` for type checking
  - [x] 8.2 Run `npx eslint` on all modified files
  - [x] 8.3 Run tests: `npx react-scripts test --watchAll=false --testPathPattern="EventCalendarPage|Dashboard"`

## Notes

- Translation keys must be added to BOTH `src/locales/` AND `public/locales/` directories
- The `/events/calendar` public route stays unchanged — external/unauthenticated visitors use it directly
- Property-based testing is not applicable (UI wiring, no data transformation)
- Existing AbortController/timeout/retry logic in EventCalendarPage stays as-is

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["3.1", "4.1"] },
    { "id": 1, "tasks": ["3.2", "5.1", "6.1"] },
    { "id": 2, "tasks": ["3.3", "6.2", "6.3"] },
    { "id": 3, "tasks": ["7.1"] },
    { "id": 4, "tasks": ["8.1", "8.2", "8.3"] }
  ]
}
```
