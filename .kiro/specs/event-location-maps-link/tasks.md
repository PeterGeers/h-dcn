# Implementation Plan: Event Location Maps Link

## Overview

Make the event location text clickable across all views (EventList, EventLandingPage) by introducing a reusable `LocationMapLink` component. The component wraps Chakra UI's `Link` with `isExternal`, constructs a Google Maps search URL via `encodeURIComponent`, shows a map pin icon, stops event propagation, and renders nothing for empty/null locations. Includes i18n for all 8 languages and full accessibility support.

## Tasks

- [x] 1. Create LocationMapLink component and translations
  - [x] 1.1 Create the `LocationMapLink` component
    - Create `frontend/src/modules/events/components/LocationMapLink.tsx`
    - Implement `LocationMapLinkProps` interface with `location`, `fontSize`, `color`, `maxW`, `isTruncated` props
    - Implement guard: return `null` if location is null, undefined, empty, or whitespace-only
    - Build Maps URL: `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(location.trim())}`
    - Render Chakra `Link` with `isExternal={true}` (applies `target="_blank"` and `rel="noopener noreferrer"`)
    - Add `onClick={e => e.stopPropagation()}` to prevent parent click handlers
    - Add custom `MapPinIcon` using Chakra `Icon` with SVG path (no new dependencies)
    - Add `aria-label` using translation key `eventBooking:location.openInMaps` with location interpolation
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 3.1, 5.1, 5.2, 5.3, 5.4_

  - [x] 1.2 Add translation keys for all 8 languages
    - Add `location.openInMaps` key to `frontend/src/locales/{lang}/eventBooking.json` for all 8 languages (nl, en, de, fr, es, it, da, sv)
    - Add `location.openInMaps` key to `frontend/public/locales/{lang}/eventBooking.json` for all 8 languages
    - Translation value pattern: "Open {location} in Google Maps (opens in new tab)" localized per language
    - _Requirements: 4.1, 4.2, 4.3_

- [x] 2. Integrate LocationMapLink into views
  - [x] 2.1 Integrate into EventList component
    - Replace the plain `<Text>` rendering of `event.location` in `frontend/src/modules/events/components/EventList.tsx`
    - Use `<LocationMapLink location={event.location} isTruncated maxW="120px" fontSize="inherit" color="inherit" />`
    - Verify that `stopPropagation` prevents the table row click handler from firing
    - _Requirements: 3.1, 3.3, 3.4_

  - [x] 2.2 Integrate into EventLandingPage (poster view and full landing page)
    - Replace plain `<Text>` rendering of location in `frontend/src/modules/events/EventLandingPage.tsx`
    - Poster view: `<LocationMapLink location={event.location} color="gray.300" fontSize="sm" />`
    - Full landing page: `<LocationMapLink location={event.location} color="inherit" fontSize="inherit" />`
    - _Requirements: 3.2, 3.3, 3.4_

- [x] 3. Checkpoint - Verify integration
  - Ensure `npx tsc --noEmit` passes, run ESLint on modified files, ask the user if questions arise.

- [x] 4. Testing
  - [x] 4.1 Write unit tests for LocationMapLink
    - Create `frontend/src/modules/events/__tests__/LocationMapLink.test.tsx`
    - Test: renders link with correct href for a valid location
    - Test: renders nothing for null, undefined, empty string, whitespace-only
    - Test: encodes special characters correctly (Café, ü, spaces)
    - Test: `stopPropagation` is called on click
    - Test: `aria-label` contains the location text
    - Test: map pin icon is present
    - Test: `target="_blank"` and `rel="noopener noreferrer"` are set
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 5.1, 5.2_

  - [x] 4.2 Write property test: Maps URL round-trip preserves location
    - **Property 1: Maps URL round-trip preserves location**
    - **Validates: Requirements 1.1, 1.2, 2.1, 3.4**
    - Create `frontend/src/modules/events/__tests__/LocationMapLink.property.test.ts`
    - Use fast-check to generate arbitrary non-empty, non-whitespace strings (up to 300 chars, including Unicode)
    - Assert: `decodeURIComponent(new URL(builtUrl).searchParams.get('query'))` equals `location.trim()`
    - Assert: `new URL(builtUrl)` does not throw

  - [x] 4.3 Write property test: Invalid locations produce no output
    - **Property 2: Invalid locations produce no output**
    - **Validates: Requirements 1.4, 2.2**
    - Use fast-check to generate null, undefined, empty strings, and whitespace-only strings
    - Assert: component renders nothing (returns null)

  - [x] 4.4 Write property test: Aria-label contains the location text
    - **Property 4: Aria-label contains the location text**
    - **Validates: Requirements 5.2**
    - Use fast-check to generate arbitrary non-empty, non-whitespace strings
    - Assert: rendered link's `aria-label` attribute contains the original location string

  - [x] 4.5 Write unit test for translation key presence
    - Verify `location.openInMaps` key exists in all 16 locale files (8 languages × 2 locations)
    - Assert each value is a non-empty string
    - _Requirements: 4.1, 4.2_

- [x] 5. Final checkpoint - Ensure all tests pass
  - Run `npx react-scripts test --watchAll=false --testPathPattern="LocationMapLink"`, verify type check passes, run ESLint on all modified files. Ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- No backend changes needed — this is a purely frontend feature
- Translation files must be updated in BOTH `src/locales/` and `public/locales/` per project conventions
- Use `npx react-scripts test --watchAll=false --testPathPattern="LocationMapLink"` to run tests (never watch mode)

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["2.1", "2.2"] },
    { "id": 2, "tasks": ["4.1", "4.2", "4.3", "4.4", "4.5"] }
  ]
}
```
