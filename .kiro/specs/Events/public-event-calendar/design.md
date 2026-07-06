# Design: Public Event Calendar

## Context

H-DCN wants a public event calendar that:

- Is accessible by everyone without login
- Is shareable on Facebook/social media (with poster, title, date)
- Can be embedded in the existing h-dcn.nl website
- Is part of the existing SPA (portal.h-dcn.nl)

The **Events DynamoDB table is the single source of truth**. All data flows (import, manual entry, poster analysis) lead to this table. The public calendar reads exclusively from it.

---

## Scope

### In scope

- Public route `/events` and `/events/:slug` (no login required)
- Backend endpoint without auth for published events
- Open Graph meta tags for social media sharing
- Responsive grid: 1 card/row (mobile), 4/row (desktop)
- Filters: type (National, International, Miscellaneous), region, date
- Data input: Google Agenda import, JSON import, poster analysis, Stan import, manual via admin UI
- Duplicate prevention (name + date + location)
- Google Calendar sync (DynamoDB → Google Agenda, bidirectional)
- Poster management: S3 storage (event calendar), museum in Google Photos, cleanup on delete
- Poster analysis: upload poster → AI extracts event data → prefill form

### Out of scope

- Booking flow (existing logic)
- AI poster **generation** (posters are created manually or provided — we only analyze them)

---

## Data Flow Architecture

```
                        DATA INPUTS
    ┌──────────────────────────────────────────────┐
    │                                              │
    │  Google Agenda  ·  JSON file  ·  Stan file   │
    │  Poster analysis (AI)  ·  Admin UI (manual)  │
    │                                              │
    └──────────────────────┬───────────────────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │     DUPLICATE CHECK     │
              │  name + date + location │
              └────────────┬────────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │  Events DynamoDB Table  │  ← single source of truth
              └────────────┬────────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
        Public Calendar  Google Cal  Poster Museum
        (portal.h-dcn.nl) (sync out)  (Google Photos)
```

---

## Event Creation Workflow

### Roles

| Role                    | Responsibility                                     | Event types        |
| ----------------------- | -------------------------------------------------- | ------------------ |
| Regional representative | Creates events in `draft`, uploads poster manually | National, Regional |
| Secretary H-DCN         | Creates events in `draft`, manages ALV/meetings    | National, Meetings |
| Events_CRUD / Regio_All | Reviews drafts, publishes (`draft` → `published`)  | All                |
| International contact   | Imports events (often via poster analysis)         | International      |

### Workflow: National events

1. Regional representative or secretary creates event via admin UI → status: `draft`
2. Adds details + uploads poster manually
3. After agreement: status → `published`
4. On publish: appears on public calendar + syncs to Google Agenda

### Workflow: International events

1. Poster is the primary source (provided as image)
2. Upload poster → AI analyzes → prefills event form
3. User verifies/corrects → saves as `draft`
4. After review: status → `published`

### Rules

- Events ALWAYS start in `draft` (never directly published)
- Publish is a deliberate action after agreement
- Regional permissions (`linked_regio`) determine who can create/edit
- Existing admin UI remains the primary input path

---

## Import Scripts

One-time or periodic scripts for bulk data input. All scripts:

- Write to Events DynamoDB (single source of truth)
- Perform duplicate check before insert
- Support `--dry-run` and `--profile nonprofit-deploy`
- Create events in `draft` status (unless `--status published` flag)

| Script                                   | Source              | Purpose                                                   |
| ---------------------------------------- | ------------------- | --------------------------------------------------------- |
| `scripts/import_events_google_agenda.py` | Google Calendar API | Import existing events + store `google_calendar_event_id` |
| `scripts/import_events_json.py`          | JSON file           | One-time migration from old system                        |
| `scripts/import_events_from_posters.py`  | Poster directory    | Bulk poster analysis → create events                      |
| `scripts/import_events_stan.py`          | Stan export         | Import from bookkeeping (CSV/TBD)                         |

### Field mapping (Google Agenda)

- `summary` → `name`
- `start.dateTime` / `start.date` → `start_date`
- `end.dateTime` / `end.date` → `end_date`
- `location` → `location`
- `description` → description field

---

## Duplicate Prevention

### Detection logic

Fuzzy matching — exact duplicates are rare, but "almost the same" events occur frequently (typos, alternative spellings, abbreviations). The check must be smart enough to catch those without too many false positives.

```python
def check_duplicate(name: str, start_date: str, location: str, table) -> dict | None:
    """
    Fuzzy duplicate detection based on three fields:

    1. start_date: exact match (YYYY-MM-DD) — primary filter
       (no fuzzy on date: 1 day difference = different event)

    2. name: fuzzy match — catches typos, abbreviations, capitalization
       - Case-insensitive comparison
       - Levenshtein distance ≤ 3 OR
       - Token overlap ≥ 70% (splits on spaces, compares words)
       - Examples that match:
         "Toerweekend 2026" ↔ "Tour Weekend 2026"
         "ALV Maart" ↔ "ALV maart 2027"
         "Openingsrit Noord" ↔ "Openings Rit Noord"

    3. location: fuzzy match — catches variations in location spelling
       - Case-insensitive contains check (one contains the other) OR
       - Levenshtein distance ≤ 5 (locations are often longer)
       - Examples that match:
         "Amsterdam" ↔ "Clubhuis H-DCN, Amsterdam"
         "Holysloot" ↔ "Holysloot, Amsterdam"
       - Empty location field: skip location check (match on name + date only)

    Returns existing event on match, None if unique.
    """
```

### Match strategy

- **Date is hard** — same date is a prerequisite for a possible duplicate
- **Name is fuzzy** — catches variations but not completely different events
- **Location is optional fuzzy** — strengthens the match, but missing location doesn't block

An event is a "probable duplicate" if: `exact_date AND (fuzzy_name OR (fuzzy_name_partial AND fuzzy_location))`

### Behavior per input path

| Input path      | Action on match                                    |
| --------------- | -------------------------------------------------- |
| Admin UI        | Frontend warning + show existing event             |
| Import scripts  | Log warning + skip (or `--force` to insert anyway) |
| Poster analysis | Show in UI: "This event appears to already exist"  |

### Backend

- `create_event` handler: check via `?check_duplicates=true`
- Response on match: `409 Conflict` with `{ "duplicate": { "event_id", "name", "start_date" } }`
- Shared utility: `scripts/shared/event_dedup.py`

---

## Google Calendar Sync

### Principle

The `google_calendar_event_id` field on each event record IS the sync state. No local JSON files.

| Situation                                                 | Action                      |
| --------------------------------------------------------- | --------------------------- |
| Event `published` + no `google_calendar_event_id`         | Create in Google Calendar   |
| Event `published` + has `google_calendar_event_id`        | Update in Google Calendar   |
| Event `archived`/deleted + has `google_calendar_event_id` | Delete from Google Calendar |

### Triggers

- Status change to `published` → create/update
- Status change to `archived` or delete → remove
- Field change (name, date, location) while `published` → update

### Implementation

Post-update hook in `update_event`/`create_event` handlers, or separate sync Lambda.

---

## Poster Analysis (h-dcn-poster-analyzer)

Upload poster → AI analyzes → extracts event metadata → prefills form.

**No posters are generated. Only analyzed.**

### Flow

1. User uploads poster image
2. Gemini AI (vision/multimodal) extracts: name, date, location, extra info
3. Extracted data prefills the event creation form
4. User verifies/corrects and saves
5. Poster is stored as `poster_url` on the event

### Backend

- `backend/handler/analyze_poster/app.py` — Lambda calling Gemini API
- Input: poster image (base64 or S3 key)
- Output: structured JSON with event metadata
- API key: SSM Parameter Store (never in frontend)

### Frontend

- Component: `frontend/src/modules/events/components/PosterAnalyzer.tsx`
- Service: `frontend/src/services/posterAnalysisService.ts`
- Integration: "Upload & Analyze Poster" button in event create form

### Source code

The existing code in `h-dcn-poster-generator/` contains image generation logic that is NOT used. Only the Gemini API integration pattern is reused for the analysis function.

---

## Poster Management

### Two storage locations (different purposes)

| Location      | Purpose                         | Lifespan                      |
| ------------- | ------------------------------- | ----------------------------- |
| S3 (public)   | Event calendar + social sharing | Deleted when event is deleted |
| Google Photos | Museum / permanent archive      | Permanent — never deleted     |

### Flows per event type

All approaches are available for every event type. The table below shows the **most common** scenario per type:

| Event type    | Most common poster approach                        |
| ------------- | -------------------------------------------------- |
| National      | Manually uploaded by regional rep or secretary     |
| International | Poster is the source — data extracted from it (AI) |
| Other         | Optional, manual                                   |

Nothing prevents a regional rep from using poster analysis for a national event, or entering an international event manually. The tooling is available to everyone — event type does not restrict which flow is allowed.

### S3 storage (event calendar)

- Path: `s3://h-dcn-data-506221081911/event-posters/{slug}.{ext}`
- `poster_url` on event record contains the full S3 URL
- Upload via admin UI (existing `upload_image` handler)
- **Deleted when the event is permanently deleted** (in `delete_event` handler)

### Google Photos museum (archive)

- Posters are added to a Google Photos album (permanent archive)
- Independent of event lifecycle — poster remains in album even if event is deleted
- Upload to Google Photos: on poster upload or as separate batch action
- No S3 involvement for museum

### Cleanup

- On event delete: remove poster from S3 (`poster_url` → S3 delete)
- Google Photos album: unchanged (poster stays in museum)

---

## Public Calendar (Frontend)

### EventCalendarPage (`/events`)

- Grid of event cards, sorted by `start_date` ascending
- Responsive: 1/row mobile, 4/row desktop
- Card shows: poster (or placeholder), name, date, location
- Filters: type, region, date range
- Only events with `status === 'published'` and `end_date >= today`
- Click → `/events/:slug`

### EventLandingPage (`/events/:slug`)

**With landing page** (event has `landing_page.enabled === true`):

- Poster (large), name, start/end date, location, description
- Landing page content (sections, hero image, tagline)
- CTA button "Register" only when a booking flow is defined
- Participation indicator: open / members only / by invitation

**Without landing page** (event has no landing page or `enabled === false`):

- Click on event in calendar opens a poster-view/modal
- Shows: poster (large) + all core fields (name, description, start/end date, type, category, participation, region, status, location, slug)
- Excludes: `event_id` (internal, not shown)

### CTA Button logic

- Only shown when the event has a booking/registration process
- Not every event has registration — some are purely informational/promotional
- A landing page can exist without CTA (purely for event promotion)

### Routes

| Route                      | Auth    | Content            |
| -------------------------- | ------- | ------------------ |
| `/events`                  | None    | Calendar overview  |
| `/events/:slug`            | None    | Event landing page |
| `/events/:eventId/booking` | Cognito | Booking (existing) |

---

## Backend: GET /events-public

- No authentication
- Filter: `status === 'published'` and `end_date >= today`
- Excludes: `event_type === 'webshop'`
- Fields: `event_id`, `name`, `slug`, `event_type`, `location`, `start_date`, `end_date`, `poster_url`, `description`, `landing_page`
- No admin fields (cost, revenue, allowed_events)
- Handler: `backend/handler/get_event_public/app.py` (exists — extend for list endpoint)

---

## Social Media (OG Tags)

### Problem

SPA returns empty HTML — bots cannot scrape content.

### Solution: CloudFront Function + static OG files

1. On event publish: generate minimal HTML file with OG tags to S3 (`events/{slug}/og.html`)
2. CloudFront Function (viewer-request) detects bot User-Agents
3. Bot: route to static OG HTML file (title, description, image, url)
4. Browser: serve SPA normally

No Lambda@Edge, no network calls from the function, no runtime complexity.

Bot User-Agents: `facebookexternalhit`, `Twitterbot`, `LinkedInBot`, `Slackbot`, `WhatsApp`, `Googlebot`

OG file generation trigger: status → `published` (in event handler)

Ref: `docs/decisions/defer-lambda-edge-og.md` — Lambda@Edge rejected, CloudFront Function + static files chosen.

---

## Integration with existing website

1. **Direct link** (recommended): h-dcn.nl links to `https://portal.h-dcn.nl/events/calendar`
2. **API widget** (optional): external site fetches `GET /events-public` and renders own list
3. **Iframe** (fallback): embed portal page

---

## New Field Registry

To add to `frontend/src/config/eventFields/fields/metadataFields.ts`:

| Field                      | Type   | Purpose                                              |
| -------------------------- | ------ | ---------------------------------------------------- |
| `google_calendar_event_id` | string | Sync state — link to Google Calendar event           |
| `import_source`            | enum   | Source: 'manual', 'google', 'json', 'poster', 'stan' |

---

## Dependencies

- `slug` field populated on events (admin UI generates on create)
- `poster_url` populated for social media previews
- `.googleCredentials.json` for Google Calendar API
- Google Calendar API enabled in GCP project
- S3 `event-posters/` prefix with public read policy
- Gemini API key in SSM Parameter Store
- Stan export format documented (TBD)

---

## Implementation Sequence

**Phase 1 — Foundation**

1. Extend Field Registry (`google_calendar_event_id`, `import_source`)
2. Duplicate check utility (`scripts/shared/event_dedup.py`)
3. Validate existing test events in DynamoDB

**Phase 2 — Poster Analysis**

4. `analyze_poster` Lambda (Gemini vision proxy)
5. `PosterAnalyzer` component in event create/edit form
6. Poster upload → S3 → `poster_url`

**Phase 3 — Import Scripts**

7. `import_events_json.py`
8. `import_events_google_agenda.py`
9. `import_events_stan.py`

**Phase 4 — Public Calendar**

10. EventCalendarPage + EventLandingPage
11. `get_events_public` endpoint (list)

**Phase 5 — Google Calendar Sync**

12. Sync on publish/update/archive

**Phase 6 — Social & Integration**

13. CloudFront Function (OG tags)
14. Google Photos museum sync (poster → album on upload)
15. h-dcn.nl integration

---

## Appendix: Migration from poster-processor JSON state

The old `h-dcn-poster-generator` project used local JSON files for sync state:

| File (old)               | Replaced by                                   |
| ------------------------ | --------------------------------------------- |
| `current-calendar.json`  | DynamoDB Events table (new data via API)      |
| `previous-calendar.json` | DynamoDB (persistent — IS the previous state) |
| `google-calendar.json`   | `google_calendar_event_id` field per event    |

The comparison logic (diff current vs previous → cross-ref with google) is no longer needed. DynamoDB + the `google_calendar_event_id` field replace all state management.
