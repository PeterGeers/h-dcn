# Bugfix Requirements Document

## Introduction

The `LocationMapLink` component — which renders event locations as clickable links opening Google Maps — was integrated into the admin EventList and EventLandingPage components but was overlooked in the public event calendar views. Specifically, `EventCalendarPage` (calendar card) and `EventDetailModal` (modal detail view) still render the location as plain `<Text>`, making it non-clickable. This is inconsistent with the original spec (Requirement 3: "Consistent Display Across Views") and degrades the user experience for members browsing events via the public calendar.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN an event with a location is displayed on the EventCalendarPage calendar card THEN the system renders the location as plain non-clickable `<Text>` without a map pin icon

1.2 WHEN an event with a location is displayed in the EventDetailModal THEN the system renders the location as plain non-clickable `<Text>` without a map pin icon

1.3 WHEN a user views the calendar card or detail modal for an event with a location THEN the system provides no way to open the location in Google Maps from those views

### Expected Behavior (Correct)

2.1 WHEN an event with a location is displayed on the EventCalendarPage calendar card THEN the system SHALL render the location using the `LocationMapLink` component with a map pin icon, clickable link to Google Maps, and appropriate truncation for the card width

2.2 WHEN an event with a location is displayed in the EventDetailModal THEN the system SHALL render the location using the `LocationMapLink` component with a map pin icon and clickable link to Google Maps

2.3 WHEN a user clicks the location link on the calendar card or detail modal THEN the system SHALL open Google Maps search in a new tab with the location value encoded via `encodeURIComponent`

### Unchanged Behavior (Regression Prevention)

3.1 WHEN an event has no location (null, undefined, empty, or whitespace-only) on the EventCalendarPage THEN the system SHALL CONTINUE TO display the `t('calendar.card.noLocation')` fallback text (no LocationMapLink rendered)

3.2 WHEN an event has no location (null, undefined, empty, or whitespace-only) in the EventDetailModal THEN the system SHALL CONTINUE TO display the '—' fallback text (no LocationMapLink rendered)

3.3 WHEN a user clicks on a calendar card THEN the system SHALL CONTINUE TO open the EventDetailModal (the LocationMapLink click SHALL stop event propagation so it does not trigger the card click handler)

3.4 WHEN the LocationMapLink is displayed in the EventList or EventLandingPage views THEN the system SHALL CONTINUE TO render identically to its current behavior (no regression from this fix)

---

### Bug Condition (Formal)

```pascal
FUNCTION isBugCondition(X)
  INPUT: X of type EventView
  OUTPUT: boolean

  // Returns true when an event with a non-empty location is rendered
  // in a calendar view (EventCalendarPage card or EventDetailModal)
  RETURN X.view IN {EventCalendarPage, EventDetailModal}
     AND X.event.location IS NOT NULL
     AND TRIM(X.event.location) ≠ ""
END FUNCTION
```

### Fix Property

```pascal
// Property: Fix Checking — Calendar views use LocationMapLink
FOR ALL X WHERE isBugCondition(X) DO
  rendered ← render(X.view, X.event)
  ASSERT rendered CONTAINS LocationMapLink
  ASSERT LocationMapLink.href = "https://www.google.com/maps/search/?api=1&query=" + encodeURIComponent(TRIM(X.event.location))
  ASSERT LocationMapLink HAS mapPinIcon
  ASSERT LocationMapLink.onClick STOPS propagation
END FOR
```

### Preservation Property

```pascal
// Property: Preservation Checking — Non-buggy inputs unchanged
FOR ALL X WHERE NOT isBugCondition(X) DO
  ASSERT render_before_fix(X) = render_after_fix(X)
END FOR
```
