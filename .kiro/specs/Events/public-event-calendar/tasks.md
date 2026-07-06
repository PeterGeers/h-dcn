# Implementation Plan: Public Event Calendar

## Overview

Public event calendar with data input flows, duplicate prevention, poster analysis, Google Calendar sync, and social media sharing. Events DynamoDB table as single source of truth.

## Task Dependency Graph

```json
{
  "waves": [
    { "tasks": [1, 2, 3] },
    { "tasks": [4, 5, 6] },
    { "tasks": [7, 8, 9] },
    { "tasks": [10, 11] },
    { "tasks": [12] },
    { "tasks": [13, 14, 15] }
  ]
}
```

Wave 1: Foundation (field registry, dedup utility, data validation) — independent
Wave 2: Poster analysis (backend + frontend + upload) — depends on wave 1
Wave 3: Import scripts — depends on wave 1 (dedup utility)
Wave 4: Public calendar frontend + backend — independent of wave 2/3
Wave 5: Google Calendar sync — depends on wave 1 (field registry)
Wave 6: Social media + museum + external integration — depends on wave 4/5

## Tasks

### Phase 1 — Foundation

- [x] 1. Extend Field Registry
  - Modify: `frontend/src/config/eventFields/fields/metadataFields.ts`
  - Add field: `google_calendar_event_id` (string, hidden, readOnly, group: 'metadata')
  - Add field: `import_source` (enum: 'manual'|'google'|'json'|'poster'|'stan', hidden, readOnly, group: 'metadata')
  - Update barrel export in `frontend/src/config/eventFields/fields/index.ts`
  - Verify: `npx tsc --noEmit` passes

- [x] 2. Duplicate check utility
  - Create: `scripts/shared/__init__.py`
  - Create: `scripts/shared/event_dedup.py`
  - Implement: `check_duplicate(name, start_date, location, table)` function
  - Fuzzy logic: exact date match + Levenshtein ≤ 3 on name + contains check on location
  - Token overlap ≥ 70% as alternative name match
  - Return existing event dict on match, None on unique
  - Support `--dry-run` output formatting
  - Test: `backend/tests/unit/test_event_dedup.py` with known match/no-match cases

- [x] 3. Validate existing test events in DynamoDB
  - Create: `scripts/validate_events_data.py`
  - Scan Events table, report: missing slugs, missing poster_urls, invalid dates, duplicate candidates
  - Output: summary report to stdout
  - Flags: `--profile nonprofit-deploy`, `--dry-run` (read-only by default)

### Phase 2 — Poster Analysis

- [x] 4. Backend: `analyze_poster` Lambda
  - Create: `backend/handler/analyze_poster/app.py`
  - No auth required (or admin-only — TBD based on who uses it)
  - Accept: POST with base64 image data or S3 key
  - Call Gemini API (vision/multimodal) with analysis prompt
  - Return: `{ "name", "start_date", "end_date", "location", "info" }` as JSON
  - API key from SSM Parameter Store (`/h-dcn/gemini-api-key`)
  - Error handling: return 502 on Gemini failure with meaningful message
  - Add to SAM template: function definition, API Gateway route, IAM for SSM read
  - Test: `backend/tests/unit/test_analyze_poster.py` (mock Gemini response)

- [x] 5. Frontend: PosterAnalyzer component
  - Create: `frontend/src/modules/events/components/PosterAnalyzer.tsx`
  - Create: `frontend/src/services/posterAnalysisService.ts`
  - UI: file upload input (accept image/\*) + "Analyze" button
  - On submit: upload image → call `POST /analyze-poster` → receive JSON
  - On success: call `onAnalysisComplete(data)` callback to prefill parent form
  - Loading state, error display
  - Integrate into existing EventForm: add "Upload & Analyze Poster" section
  - Translations: all 8 languages, namespace `events`
  - Lint: `npx eslint` on new files
  - Type check: `npx tsc --noEmit`

- [x] 6. Poster upload → S3 → poster_url
  - Verify existing `upload_image` handler supports event-poster use case
  - If needed: add `event-posters/` prefix support
  - Frontend: after poster analysis or manual upload, store S3 URL as `poster_url` on event
  - Verify: poster accessible via public S3 URL

### Phase 3 — Import Scripts

- [x] 7. Import: JSON file
  - Create: `scripts/import_events_json.py`
  - Input: JSON file with array of event objects (name, start_date, end_date, location, ...)
  - Validate required fields per item
  - Generate: event_id (UUID), slug (from name), status='draft', import_source='json'
  - Call `check_duplicate()` before each write
  - Flags: `--dry-run`, `--profile nonprofit-deploy`, `--input-file`, `--status`, `--force`
  - Output: summary (created/skipped/errors)

- [x] 8. Import: Google Agenda
  - Create: `scripts/import_events_google_agenda.py`
  - Read events via Google Calendar API (`.googleCredentials.json`)
  - Map fields: summary→name, start→start_date, end→end_date, location→location
  - Store `google_calendar_event_id` from Google's event ID
  - Import Poster with url in Google agenda and store the poster in S3
  - Set import_source='google'
  - Duplicate check before write
  - Flags: `--dry-run`, `--profile nonprofit-deploy`, `--calendar-id`, `--status`, `--force`

- [x] 9. Import: Stan file
  - Create: `scripts/import_events_stan.py`
  - Parse Stan export format (CSV — exact format TBD, start with flexible CSV reader)
  - Map columns to Events schema
  - Set import_source='stan'
  - Duplicate check before write
  - Flags: `--dry-run`, `--profile nonprofit-deploy`, `--input-file`, `--force`

### Phase 4 — Public Calendar

- [x] 10. Frontend: EventCalendarPage + EventLandingPage
  - Create: `frontend/src/pages/EventCalendarPage.tsx`
  - Create: `frontend/src/pages/EventLandingPage.tsx` (or extend existing)
  - EventCalendarPage: grid of cards, responsive (1/row mobile, 4/row desktop)
  - Filters: event_type (multi-select), linked_regio, date range
  - Sort: start_date ascending, only future events
  - EventLandingPage: two modes (with/without landing page — see design doc)
  - Poster-view modal for events without landing page
  - CTA button only when booking flow is defined
  - Add public routes to App.tsx (no auth guard)
  - Translations: all 8 languages
  - Lint + type check

- [x] 11. Backend: GET /events-public (list endpoint)
  - Modify: `backend/handler/get_event_public/app.py` (add list mode)
  - OR Create: `backend/handler/get_events_public/app.py` (separate handler)
  - No auth required
  - Scan with filter: status='published' AND end_date >= today AND event_type != 'webshop'
  - Return public-safe fields only (no cost, revenue, allowed_events, constraints)
  - Support query params: `?type=nationaal&regio=noord&from=2026-07-01&to=2026-12-31`
  - Add to SAM template: function + API Gateway GET route
  - Test: `backend/tests/unit/test_get_events_public.py`

### Phase 5 — Google Calendar Sync

- [x] 12. Google Calendar sync on publish/update/archive
  - Create: `backend/handler/sync_google_calendar/app.py` (or add to update_event as post-action)
  - On status → 'published': create Google Calendar event, store google_calendar_event_id
  - On status → 'archived' or delete: remove from Google Calendar, clear ID
  - On field change (name, date, location) while published: update Google Calendar event
  - Use `.googleCredentials.json` service account
  - Idempotent: if google_calendar_event_id exists → update, else → create
  - Error handling: log failure but don't block the DynamoDB update
  - Test: mock Google Calendar API calls

### Phase 6 — Social & Integration

- [x] 13. CloudFront Function (OG tags)
  - Create: static OG HTML generator (runs on publish, writes `events/{slug}/og.html` to S3)
  - Create: CloudFront Function (viewer-request) for bot detection + routing
  - Bot detection regex: facebookexternalhit|Twitterbot|LinkedInBot|Slackbot|WhatsApp|Googlebot
  - Non-bot: pass through to SPA
  - Bot + /events/{slug} path: rewrite to events/{slug}/og.html
  - Deploy: add CF Function association to CloudFront distribution
  - Test: curl with fake user-agent to verify OG response

- [x] 14. Google Photos museum sync
  - Create: utility to upload poster to Google Photos album on poster upload
  - Use Google Photos API (or Google Drive as album container)
  - Trigger: when poster_url is set/updated on an event
  - Poster remains in album permanently (independent of event lifecycle)
  - This can be a background script or integrated into the upload flow

- [x] 15. h-dcn.nl integration
  - Provide direct link: `https://portal.h-dcn.nl/events/calendar`
  - Optionally: document API widget approach for external site consumption
  - Verify CORS allows cross-origin fetch from h-dcn.nl domain to API

## Notes

- Event Field Registry already has `slug`, `poster_url`, `status`, `event_type`, all core/date fields
- Existing `get_event_public` handler works for single event by slug — needs extension for list
- `upload_image` handler already exists — verify it handles `event-posters/` prefix
- Existing auth layer (`shared.auth_utils`) not needed for public endpoints
- The `h-dcn-poster-generator/` code contains Gemini API patterns reusable for analysis
- Stan format is TBD — task 9 starts with flexible CSV reader, can be refined later
