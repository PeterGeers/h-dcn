# Design Document: Events Calendar Card

## Overview

This feature consolidates the Dashboard's event display from N individual `EventBookingCard` components into a single static "Events / Calendar" `AppCard` that navigates to `/events/calendar`. The existing `EventCalendarPage` is modified in-place to become context-aware — detecting auth state via `useAuth()` and branching click behavior accordingly.

**Scope**: 2 file modifications, 0 new files, 0 new API endpoints, 0 new routes.

## Architecture

The change touches two existing components within the React SPA:

```mermaid
graph LR
    subgraph "Dashboard (authenticated)"
        A[Event_Calendar_Card] -->|navigate| B[/events/calendar]
    end
    subgraph "EventCalendarPage (public)"
        B --> C{useAuth - authenticated?}
        C -->|yes| D[useNavigate → /events/event_id/booking]
        C -->|no| E[window.open → /events/slug/info]
    end
```

Both `/events/calendar` (public) and `/events/{eventId}/booking` (inside `ProtectedApp`) are sibling routes under the same `<Router>`, so `useNavigate()` works across them without issue.

The `AuthProvider` wraps both route groups at the top level of `App.tsx`, making `useAuth()` available inside `EventCalendarPage` even though it's a public route.

## Components and Interfaces

### Dashboard.tsx — Changes

**Remove**: The entire `EventBookingCard` component (lines ~20-75) and its usage in both the event-participant section and the main grid.

**Add**: A single static `AppCard` with:

- `id`: `'events-calendar'`
- `icon`: `'📅'`
- `title`: `t('cards.events_calendar_title')` (from `dashboard` namespace)
- `description`: `t('cards.events_calendar_desc')` (from `dashboard` namespace)
- `onClick`: `() => navigate('/events/calendar')`

The card is unconditional — always visible for `hdcnLeden` users (wrapped in existing `FunctionGuard` with `requiredRoles={['hdcnLeden', 'event_participant']}`). No API call needed on Dashboard for events.

**Removed imports**: `eventBookingApi` (no longer needed on Dashboard).

### EventCalendarPage.tsx — Changes

**Add imports**:

- `useAuth` from `'../context/AuthProvider'`
- `useNavigate` from `'react-router-dom'`

**Add to component body**:

```typescript
const { isAuthenticated } = useAuth();
const navigate = useNavigate();
```

**Modify the event card `onClick` handler**:

```typescript
onClick={() => {
  if (isAuthenticated) {
    navigate(`/events/${event.event_id}/booking`);
  } else {
    window.open(`/events/${event.slug}/info`, '_blank');
  }
}}
```

**Add**: AbortController with 10-second timeout on the fetch call, plus a retry button in the error state.

### No changes to:

- `App.tsx` (routing stays as-is)
- `AuthProvider.tsx` (already provides `isAuthenticated`)
- `AppCard.tsx` (generic, unchanged)
- Backend API endpoints

## Data Models

No data model changes. The `/events-public` API already returns both `event_id` and `slug` fields in each `PublicEvent` object:

```typescript
interface PublicEvent {
  event_id: string; // Used for authenticated navigation
  slug: string; // Used for unauthenticated navigation
  name: string;
  event_type: string;
  location: string;
  start_date: string;
  end_date: string;
  poster_url?: string;
  description?: string;
  linked_regio?: string;
}
```

## Error Handling

| Scenario                         | Current Behavior               | New Behavior                                                            |
| -------------------------------- | ------------------------------ | ----------------------------------------------------------------------- |
| `/events-public` fetch fails     | Shows alert with error message | Same + adds retry button                                                |
| Fetch timeout (>10s)             | No timeout                     | AbortController aborts after 10s, shows error + retry                   |
| `useAuth()` outside AuthProvider | Would throw                    | Cannot happen — `AuthProvider` wraps the entire `<Router>` in `App.tsx` |
| `useNavigate()` on public route  | N/A                            | Works — both routes share the same `<Router>` instance                  |

## Correctness Properties

_A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees._

### Property 1: No universal properties identified

_For any_ input to this feature, the behavior is a simple conditional branch (authenticated → SPA navigate, unauthenticated → open new tab) with no data transformation or algorithmic logic. Property-based testing does not apply — example-based unit tests provide full coverage.

**Validates: Requirements 1.1, 1.2, 2.1, 2.3, 2.4**

## Testing Strategy

**PBT is not applicable** for this feature. The changes are simple UI wiring — replacing a component list with a static card, and adding a conditional branch (`if authenticated → navigate, else → window.open`). There is no meaningful input space, no data transformation, no algorithm to exercise with generated inputs.

### Unit Tests (React Testing Library + Jest)

**Dashboard.test.tsx**:

1. Renders single events/calendar card with correct icon, title, description
2. Click navigates to `/events/calendar`
3. Card visible even when no published events exist (no API dependency)
4. `EventBookingCard` component no longer rendered

**EventCalendarPage.test.tsx**:

1. Authenticated user: click event card calls `navigate('/events/{event_id}/booking')`
2. Unauthenticated user: click event card calls `window.open('/events/{slug}/info', '_blank')`
3. Same API endpoint (`/events-public`) used regardless of auth state
4. Fetch failure shows error message + retry button
5. Retry button re-triggers fetch
6. 10-second timeout triggers error state
7. Loading spinner shown while fetching

### Test approach

- Mock `useAuth` to control `isAuthenticated` state
- Mock `useNavigate` to verify SPA navigation calls
- Mock `window.open` to verify external link behavior
- Mock `fetch` to control API responses and simulate failures/timeouts
