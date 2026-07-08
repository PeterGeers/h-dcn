# Requirements Document

## Introduction

Replace the current dashboard behavior where non-admin users (hdcnLeden) see a separate AppCard for each published event with a single consolidated "Events / Calendar" card. Clicking this card navigates to `/events/calendar` — the existing public route.

The `EventCalendarPage` component at `/events/calendar` becomes context-aware: it detects authentication state via the existing `AuthProvider`/`useAuth` context and adapts its click behavior:

- **Authenticated (hdcnLeden)**: Click navigates within the SPA to `/events/{event_id}/booking`
- **Not authenticated**: Click opens `/events/{slug}/info` in a new tab (current behavior preserved)

No new route is needed. No new page is built. The existing `/events/calendar` route remains public in `App.tsx`. The existing `EventCalendarPage` component is modified in-place to add auth-awareness — no component extraction, no copy.

## Glossary

- **Dashboard**: The main landing page after login (`/`), showing AppCards based on user role
- **EventCalendarPage**: The existing page at `/events/calendar` that becomes context-aware — adapting its API endpoint and click behavior based on authentication state
- **AppCard**: The reusable card component rendered on the Dashboard (icon, title, description, "Open" button)
- **Event_Calendar_Card**: The single consolidated AppCard on the Dashboard that links to `/events/calendar`
- **hdcnLeden**: The Cognito group for regular club members
- **Event_Record**: A DynamoDB Events table record containing event details (name, start_date, end_date, location, event_type, status, poster_url, etc.)
- **Published_Event**: An Event_Record with `status === 'published'` and `event_type !== 'webshop'`
- **AuthProvider**: The existing React context provider that exposes authentication state (user, tokens, roles) to child components

## Requirements

### Requirement 1: Single Events Card on Dashboard

**User Story:** As a logged-in user, I want to see a single "Events / Calendar" card on my dashboard instead of many individual event cards, so that the dashboard remains clean and navigable.

#### Acceptance Criteria

1. WHEN the Dashboard renders for any authenticated user, THE Dashboard SHALL display a single Event_Calendar_Card instead of the current multiple individual EventBookingCards (the long list of per-event cards is removed)
2. WHEN the user clicks the Event_Calendar_Card, THE Dashboard SHALL navigate to `/events/calendar`
3. THE Event_Calendar_Card SHALL display a calendar icon (📅), a localized title using the `dashboard` translation namespace, and a localized description using the `dashboard` translation namespace
4. WHILE no Published_Events exist, THE Event_Calendar_Card SHALL still be visible on the Dashboard with the same icon, title, and description
5. THE EventCalendarPage at `/events/calendar` SHALL remain a public route in App.tsx that does not require authentication to access

### Requirement 2: Context-Aware EventCalendarPage

**User Story:** As a member with hdcnLeden role, I want the event calendar page to recognize that I am logged in and show me enhanced functionality, so that I can navigate directly to event booking without leaving the application.

#### Acceptance Criteria

1. THE EventCalendarPage SHALL detect authentication state using the existing AuthProvider/useAuth context
2. THE EventCalendarPage SHALL fetch events from the `/events-public` API endpoint regardless of authentication state (same data source for all users)
3. WHEN an authenticated user clicks an event card, THE EventCalendarPage SHALL navigate within the SPA to `/events/{event_id}/booking` using the application router (no new tab, no full page reload) — the booking page handler manages what happens next based on the event's group configuration
4. WHEN an unauthenticated user clicks an event card, THE EventCalendarPage SHALL open `/events/{slug}/info` in a new browser tab (preserving current behavior)
5. IF the API request fails, THEN THE EventCalendarPage SHALL display a localized error message indicating the events could not be loaded, along with a retry button that re-triggers the API request
6. IF the API request does not respond within 10 seconds, THEN THE EventCalendarPage SHALL treat the request as failed
7. WHILE events are loading, THE EventCalendarPage SHALL display a loading spinner
