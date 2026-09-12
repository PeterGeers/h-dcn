# Calendar Location Link Missing — Bugfix Design

## Overview

The `LocationMapLink` component renders event locations as clickable Google Maps links with a map pin icon. It was integrated into `EventList` and `EventLandingPage` but missed in two public calendar views: `EventCalendarPage` (card grid) and `EventDetailModal`. Both views render location as plain `<Text>`, making it non-clickable. The fix replaces those `<Text>` elements with `<LocationMapLink>`, preserving fallback text for empty locations and ensuring click propagation doesn't interfere with the card's `onClick` handler.

## Glossary

- **Bug_Condition (C)**: An event with a non-empty location is rendered in `EventCalendarPage` or `EventDetailModal` — the location appears as plain text instead of a clickable map link
- **Property (P)**: When the bug condition holds, the location MUST be rendered via `LocationMapLink` (clickable, map pin icon, opens Google Maps)
- **Preservation**: Empty-location fallback text, card click-to-open-modal behavior, and all non-location rendering must remain unchanged
- **LocationMapLink**: Reusable component at `frontend/src/modules/events/components/LocationMapLink.tsx` — renders a clickable link with MapPinIcon, opens Google Maps in a new tab, returns `null` for empty/null/whitespace locations, and stops click propagation
- **EventCalendarPage**: Public calendar grid at `frontend/src/pages/EventCalendarPage.tsx` — displays event cards in a responsive grid (up to 4 columns)
- **EventDetailModal**: Modal at `frontend/src/pages/EventDetailModal.tsx` — shows full event details when a card is clicked

## Bug Details

### Bug Condition

The bug manifests when an event with a non-empty location is displayed in the public calendar card or the event detail modal. The location is rendered as plain `<Text>` instead of the `LocationMapLink` component, so users cannot click to open Google Maps.

**Formal Specification:**

```
FUNCTION isBugCondition(input)
  INPUT: input of type { view: Component, event: PublicEvent }
  OUTPUT: boolean

  RETURN input.view IN {EventCalendarPage, EventDetailModal}
     AND input.event.location IS NOT NULL
     AND TRIM(input.event.location) ≠ ""
END FUNCTION
```

### Examples

- **Calendar card with location "Amsterdam"**: Expected clickable link with map pin opening Google Maps → Actual: plain gray text "Amsterdam"
- **Detail modal with location "Circuit Zandvoort"**: Expected clickable link with map pin → Actual: plain `<Text fontSize="sm" color="gray.200">Circuit Zandvoort</Text>`
- **Calendar card with location " "** (whitespace only): Expected fallback text `t('calendar.card.noLocation')` → Actual: fallback text shown (correct, not a bug)
- **Detail modal with location `null`**: Expected "—" fallback → Actual: "—" shown (correct, not a bug)

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**

- Events with no location (null, undefined, empty, whitespace-only) on `EventCalendarPage` must continue to display `t('calendar.card.noLocation')` fallback text
- Events with no location in `EventDetailModal` must continue to display "—" fallback text
- Clicking on a calendar card must continue to open `EventDetailModal` (LocationMapLink's `stopPropagation` prevents the link click from triggering the card handler)
- `LocationMapLink` behavior in `EventList` and `EventLandingPage` must remain identical
- All other card content (poster, name, date, type badge) must render unchanged
- Modal layout (poster, description, dates, type, region, CTA buttons) must render unchanged

**Scope:**
All inputs where `isBugCondition` is false are completely unaffected by this fix. This includes:

- Events with null/undefined/empty/whitespace locations (fallback text renders)
- All non-location UI elements in both components
- Mouse clicks on the card itself (open modal)
- All other modal interactions (close, book, register)

## Hypothesized Root Cause

The root cause is straightforward — the `LocationMapLink` component was simply not imported or used in these two files during the original integration:

1. **Omission in EventCalendarPage (line 231)**: The location is rendered as:

   ```tsx
   <Text fontSize="xs" color="gray.500" noOfLines={1}>
     {event.location || t("calendar.card.noLocation")}
   </Text>
   ```

   This should use `<LocationMapLink>` with a conditional fallback for empty locations.

2. **Omission in EventDetailModal (line ~130)**: The location is rendered as:

   ```tsx
   <Text fontSize="sm" color="gray.200">
     {event.location || "—"}
   </Text>
   ```

   This should use `<LocationMapLink>` with a conditional fallback for empty locations.

3. **No code defect in LocationMapLink itself**: The component already handles null/empty guards and `stopPropagation` — it just needs to be plugged in.

## Correctness Properties

Property 1: Bug Condition — Location rendered as clickable map link

_For any_ event view where the bug condition holds (event has a non-empty trimmed location AND the view is EventCalendarPage or EventDetailModal), the fixed component SHALL render the location using `LocationMapLink`, producing a clickable link with a map pin icon that opens `https://www.google.com/maps/search/?api=1&query={encodedLocation}` in a new tab.

**Validates: Requirements 2.1, 2.2, 2.3**

Property 2: Preservation — Empty location fallback text unchanged

_For any_ event view where the bug condition does NOT hold (location is null, undefined, empty, or whitespace-only), the fixed component SHALL produce the same fallback text as the original: `t('calendar.card.noLocation')` on EventCalendarPage and "—" on EventDetailModal, with no `LocationMapLink` rendered.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

## Fix Implementation

### Changes Required

**File**: `frontend/src/pages/EventCalendarPage.tsx`

**Specific Changes**:

1. **Add import**: Import `LocationMapLink` from `'../modules/events/components/LocationMapLink'`
2. **Replace plain Text (line 231)**: Replace the `<Text>` that renders location with a conditional:
   - If `event.location?.trim()` is truthy → render `<LocationMapLink location={event.location} fontSize="xs" color="gray.500" isTruncated maxW="100%" />`
   - Otherwise → render `<Text fontSize="xs" color="gray.500" noOfLines={1}>{t('calendar.card.noLocation')}</Text>`

---

**File**: `frontend/src/pages/EventDetailModal.tsx`

**Specific Changes**:

1. **Add import**: Import `LocationMapLink` from `'../modules/events/components/LocationMapLink'`
2. **Replace plain Text (line ~130)**: Replace the `<Text>` that renders location in the details grid with a conditional:
   - If `event.location?.trim()` is truthy → render `<LocationMapLink location={event.location} fontSize="sm" color="gray.200" />`
   - Otherwise → render `<Text fontSize="sm" color="gray.200">—</Text>`

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code, then verify the fix works correctly and preserves existing behavior.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm that the location is rendered as plain text (no link, no icon) in both views.

**Test Plan**: Write React Testing Library tests that render `EventCalendarPage` and `EventDetailModal` with events that have non-empty locations. Assert that `LocationMapLink` is NOT present (link role with Google Maps href is absent).

**Test Cases**:

1. **Calendar card with location**: Render card with `location: "Amsterdam"` — assert no link to Google Maps exists (will fail on unfixed code)
2. **Detail modal with location**: Render modal with `location: "Circuit Zandvoort"` — assert no link to Google Maps exists (will fail on unfixed code)
3. **Calendar card click propagation**: Render card with location, click the location area — assert modal opens (on unfixed code, plain text doesn't stop propagation)

**Expected Counterexamples**:

- No `<a>` element with `href` containing `google.com/maps` exists in the rendered output
- No MapPinIcon SVG element exists near the location text
- Confirms the `LocationMapLink` component is simply not used

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed views render `LocationMapLink` correctly.

**Pseudocode:**

```
FOR ALL input WHERE isBugCondition(input) DO
  rendered := render(input.view, input.event)
  link := findByRole('link', { name containing input.event.location })
  ASSERT link EXISTS
  ASSERT link.href = "https://www.google.com/maps/search/?api=1&query=" + encodeURIComponent(TRIM(input.event.location))
  ASSERT link contains MapPinIcon SVG
  ASSERT clicking link does NOT trigger card onClick (stopPropagation)
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed views produce the same output as the original.

**Pseudocode:**

```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT render_before_fix(input) = render_after_fix(input)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:

- It generates many location string variations (null, undefined, empty, whitespace-only) to verify fallback rendering
- It catches edge cases like locations with only tabs/newlines
- It provides strong guarantees that empty-location behavior is unchanged

**Test Plan**: Observe behavior on UNFIXED code for events with empty/null locations, then write property-based tests that generate various empty-location inputs and assert the fallback text appears unchanged.

**Test Cases**:

1. **Empty location fallback (calendar)**: Verify `t('calendar.card.noLocation')` renders for null/undefined/empty/whitespace locations
2. **Empty location fallback (modal)**: Verify "—" renders for null/undefined/empty/whitespace locations
3. **Card click still opens modal**: Verify clicking a card (not on the link) still triggers `setSelectedEvent`
4. **Link click does not open modal**: Verify clicking the `LocationMapLink` fires `stopPropagation` and does NOT open the modal

### Unit Tests

- Test `EventCalendarPage` renders `LocationMapLink` for events with valid locations
- Test `EventCalendarPage` renders fallback text for events with empty/null locations
- Test `EventDetailModal` renders `LocationMapLink` for events with valid locations
- Test `EventDetailModal` renders fallback text for events with empty/null locations
- Test click propagation: clicking the map link does not trigger card's `onClick`

### Property-Based Tests

- Generate random non-empty location strings and verify `LocationMapLink` renders with correct Google Maps URL in both views
- Generate random empty-ish location strings (null, undefined, "", " ", "\t\n") and verify fallback text renders in both views
- Generate random events and verify the card `onClick` handler is never called when `LocationMapLink` is clicked

### Integration Tests

- Render full `EventCalendarPage` with a mix of events (some with location, some without) — verify correct rendering for each
- Open `EventDetailModal` from a card click — verify location link is present and clickable
- Verify the Google Maps link opens in a new tab (`target="_blank"` via `isExternal`)
