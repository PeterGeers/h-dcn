# Requirements Document

## Introduction

Make the event location text clickable so users can open the location in Google Maps. Everywhere the location is displayed (event list, landing page), the text becomes a hyperlink that opens a Google Maps search in a new tab. This is a lightweight, frontend-only change: no API keys, no new database fields, no extra dependencies. One link that works on all devices — the device/OS handles opening the maps app if available.

## Glossary

- **Event_Location_Link**: The clickable location text element that opens a Google Maps search URL in a new browser tab
- **Location_Field**: The existing `location` string field in the Event Field Registry (max 300 characters, e.g. "Clubhuis H-DCN, Amsterdam")
- **Maps_Search_URL**: A Google Maps search URL following the pattern `https://www.google.com/maps/search/?api=1&query={encoded_location}`

## Requirements

### Requirement 1: Clickable Location with Google Maps Search Link

**User Story:** As a member viewing an event, I want to click the location text to open Google Maps, so that I can quickly find directions to the event venue.

#### Acceptance Criteria

1. WHEN a user clicks the Event_Location_Link, THE Event_Location_Link SHALL open the Maps_Search_URL in a new browser tab
2. THE Maps_Search_URL SHALL be constructed using the pattern `https://www.google.com/maps/search/?api=1&query={encoded}` where `{encoded}` is the Location_Field value encoded with `encodeURIComponent`
3. THE Event_Location_Link SHALL display a map pin icon to the left of the location text to indicate the link is clickable
4. IF the Location_Field value is null, undefined, an empty string, or contains only whitespace characters, THEN THE Event_Location_Link SHALL not render any link or map pin icon

### Requirement 2: URL Encoding of Location Text

**User Story:** As a member, I want location names with special characters to work correctly in the maps link, so that I always land on the right search result.

#### Acceptance Criteria

1. THE Maps_Search_URL SHALL use `encodeURIComponent` to encode the Location_Field value, producing correct percent-encoding for spaces (e.g. "Den Bosch" → "Den%20Bosch"), special characters (e.g. "Café 't Centrum" → "Caf%C3%A9%20't%20Centrum"), and unicode characters (e.g. "Mühlenbergstraße" → "M%C3%BChlenbergstra%C3%9Fe")
2. IF the Location_Field value contains only whitespace characters, THEN THE Event_Location_Link SHALL not render (no Maps_Search_URL is generated)

### Requirement 3: Consistent Display Across Views

**User Story:** As a member, I want the clickable location to work on both the event list and the event landing page, so that I can access directions from any view.

#### Acceptance Criteria

1. WHEN an event with a Location_Field value is displayed in the EventList component, THE Event_Location_Link SHALL render the location as a clickable link that does not trigger the table row click handler (event propagation SHALL be stopped on the link)
2. WHEN an event with a Location_Field value is displayed on the EventLandingPage, THE Event_Location_Link SHALL render the location as a clickable link in both poster-view mode and full landing page mode
3. THE Event_Location_Link SHALL render the same map pin icon, link color, and hover state in all views where it appears
4. WHEN the Location_Field text is truncated due to container width constraints, THE Event_Location_Link SHALL still link to the full untruncated Location_Field value in the Maps_Search_URL

### Requirement 4: Internationalization

**User Story:** As a member using the portal in any supported language, I want the map link tooltip to be in my language, so that the interface is consistent.

#### Acceptance Criteria

1. THE Event_Location_Link aria-label attribute SHALL use a translation key from the `eventBooking` namespace that resolves to a non-empty translated string describing the link action (e.g., "Open location in Google Maps") in all 8 supported languages (nl, en, de, fr, es, it, da, sv)
2. THE translation key for the Event_Location_Link aria-label SHALL be present in both `frontend/src/locales/{lang}/eventBooking.json` and `frontend/public/locales/{lang}/eventBooking.json` for all 8 supported languages
3. WHEN the user switches the portal language, THE Event_Location_Link aria-label SHALL update to display the translation corresponding to the newly selected language without requiring a page reload

### Requirement 5: Accessibility and Security

**User Story:** As a member using assistive technology, I want the location link to be properly accessible and secure, so that I can navigate to the maps link using a screen reader or keyboard.

#### Acceptance Criteria

1. THE Event_Location_Link SHALL render as a Chakra UI `Link` component with `isExternal` set to true, which automatically applies `target="_blank"` and `rel="noopener noreferrer"`
2. THE Event_Location_Link SHALL include an `aria-label` attribute containing the Location_Field value and indicating that the link opens in Google Maps in a new tab (e.g. "Open {location} in Google Maps (opens in new tab)")
3. THE Event_Location_Link SHALL be reachable and activatable using standard keyboard Tab and Enter key navigation
4. WHILE the Event_Location_Link has keyboard focus, THE Event_Location_Link SHALL display a visible focus indicator that meets WCAG 2.1 Level AA contrast requirements
