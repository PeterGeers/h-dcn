# Requirements: Public Event Calendar

## REQ-1: Public Calendar Route

The public event calendar is accessible at `/events` without login. Shows only `published` events with `end_date >= today`. Responsive grid (1/row mobile, 4/row desktop). Filters on type, region, date range.

## REQ-2: Event Landing Page

Each event is accessible via `/events/:slug`. With landing page: full detail page with sections, hero image, tagline. Without landing page: poster-view modal with core fields (excluding event_id). CTA button only when a booking flow is defined.

## REQ-3: Data Input (multiple sources)

Events can be created via: admin UI (manual), Google Agenda import, JSON import, poster analysis (AI), Stan import. All flows write to the Events DynamoDB table as single source of truth. Events always start in `draft` status.

## REQ-4: Duplicate Prevention

Every input path performs a fuzzy duplicate check on name + start_date + location. Date: exact match. Name: fuzzy (Levenshtein ≤ 3 or token overlap ≥ 70%). Location: fuzzy (contains check, case-insensitive). Warning only — not a hard block.

## REQ-5: Google Calendar Sync

On publish: create/update event in Google Calendar. On archive/delete: remove from Google Calendar. Sync state tracked via `google_calendar_event_id` field on the event record. No local JSON state files.

## REQ-6: Poster Analysis

Upload poster image → Gemini AI extracts event metadata (name, date, location) → prefills event form. No poster generation. Primarily used for international events where the poster is the only information source.

## REQ-7: Poster Management

Event posters stored in S3 (`event-posters/{slug}.{ext}`), deleted when event is permanently deleted. Museum/archive stored in Google Photos album (permanent, independent of event lifecycle).

## REQ-8: Social Media (OG Tags)

Static OG HTML files generated on publish (`events/{slug}/og.html`). CloudFront Function routes social media bots to these files. Browsers receive the SPA. No Lambda@Edge.

## REQ-9: Workflow & Roles

Regional representatives and secretary create events in `draft`. Events_CRUD/Regio_All reviews and publishes. Regional permissions (`linked_regio`) determine access. Publish is a deliberate action after agreement. All input methods (manual, import, poster analysis) are available for all event types.
