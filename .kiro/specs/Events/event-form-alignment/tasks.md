# Implementation Plan: Event Form Alignment

## Overview

Brengt backend, frontend en bestaande data in lijn met de Event Field Registry. Volgorde: migratiescript → backend uitbreiding → frontend refactor → validatie.

## Task Dependency Graph

```json
{
  "waves": [
    { "tasks": [1, 2, 5] },
    { "tasks": [3, 4] },
    { "tasks": [6] },
    { "tasks": [7] }
  ]
}
```

Task 1 (migratiescript), Task 2 (backend), en Task 5 (poster upload) zijn onafhankelijk.
Task 3 (EventForm) en Task 4 (EventList) hangen af van Task 2.
Task 6 (translations) hangt af van Task 3.
Task 7 (deploy) is de laatste stap na alles.

## Tasks

- [x] 1. Migratiescript voor bestaande event records
  - Requirement: REQ-3
  - Create: `scripts/migrate_events_to_new_schema.py`
  - Map title→name, date→start_date+end_date, status mapping (published→open, cancelled→archived)
  - Add defaults: event_type='other', registration_open=start-30d, registration_close=start-1d
  - VERWIJDER oude velden na migratie: title, date, description, max_participants
  - Support --dry-run and --profile flags
  - Handle DynamoDB pagination

- [x] 2. Backend — allowed_fields uitbreiden + regionale toegangscontrole
  - Requirement: REQ-1, REQ-7
  - Modify: `backend/handler/create_event/app.py`
  - Modify: `backend/handler/update_event/app.py`
  - Voeg toe: event_category, participation, linked_regio, poster_url, participants, cost, revenue, notes
  - Gebruik `validate_price_field()` uit `shared.price_validation` voor cost/revenue (Decimal coercion + validatie)
  - Valideer participants als non-negative integer
  - Hergebruik bestaande helpers: validate_dates(), validate_constraints(), \_check_slug_uniqueness()
  - Update_event: controleer linked_regio van het bestaande event tegen user roles vóór update
  - Regio-users mogen alleen events in hun eigen regio bewerken
  - Regio_All en Events_CRUD mogen alle events bewerken
  - Geen breaking changes aan bestaande validatie

- [x] 3. Frontend — EventForm herschrijven
  - Requirement: REQ-2, REQ-5
  - Modify: `frontend/src/modules/events/components/EventForm.tsx`
  - Modify: `frontend/src/types/index.ts` (Event interface)
  - Nieuwe FormData met registry-veldnamen (name, event_type, start_date, etc.)
  - Core groep altijd zichtbaar (niet inklapbaar): name, event_type, participation, start_date, end_date, linked_regio, location, poster_url
  - Overige groepen als collapsible secties (Chakra Accordion/Collapse): registratie, config, financial, landing_page
  - Secties met bestaande data automatisch open bij bewerken
  - linked_regio altijd zichtbaar in core, verplicht, dropdown beperkt tot eigen regio('s) voor regio-users
  - Bij aanmaken: linked_regio auto-ingesteld op gebruiker's regio (als er maar één is)
  - Event type dropdown gegroepeerd per categorie met EVENT_TYPE_LABELS
  - event_category auto-derived via `getCategoryForType()` uit `eventTypes.ts`
  - Conditioneel: linked_regio bij RLV/regio_rit (via `requiresLinkedRegio()` helper)
  - Financiële velden: gebruik `formatPrice()`/`toPrice()` helpers voor weergave/conversie
  - Poster URL veld, participation mode selector

- [x] 4. Frontend — EventList/EventAdminPage updaten
  - Requirement: REQ-4
  - Modify: `frontend/src/modules/events/components/EventList.tsx`
  - Modify: `frontend/src/modules/events/EventAdminPage.tsx`
  - Gebruik uitsluitend nieuwe veldnamen: name, start_date, linked_regio (geen fallbacks nodig)
  - Sort op start_date
  - Regiofilter op linked_regio
  - Toon event_type label en poster thumbnail

- [x] 5. Poster upload integratie
  - Requirement: REQ-6
  - Onderzoek bestaande S3 upload infra (product images handler)
  - Hergebruik of maak event-specifiek upload endpoint
  - Accepteer PDF, PNG, JPG/JPEG tot 10MB
  - Sla poster_url op, toon preview in formulier en lijst

- [x] 6. Translations (i18n)
  - Requirement: REQ-2
  - Modify: `frontend/src/locales/{nl,en,de,fr,es,it,da,sv}/events.json`
  - Modify: `frontend/public/locales/{nl,en,de,fr,es,it,da,sv}/events.json`
  - Vertaal alle nieuwe labels, placeholders, event type labels, categorieën
  - 8 talen in één commit

- [ ] 7. Deploy en validatie
  - Requirement: alle
  - Run migratiescript --dry-run op test environment
  - Deploy backend en frontend naar test
  - Verifieer: nieuw event aanmaken, bestaand event bewerken, SEED events in lijst

## Notes

- De Event Field Registry is reeds compleet (coreFields, dateFields, configFields, financialFields, landingPageFields, bookingFields, metadataFields)
- eventTypes.ts bevat de volledige taxonomie (categorieën, types, labels, helpers)
- De frontend error handler maskeert backend foutmeldingen — dit is een aparte issue maar niet in scope van deze spec

### Beschikbare helpers (MOETEN worden hergebruikt)

**Backend — Shared Layer (Python):**

| Helper                                                        | Locatie                    | Gebruik                                                                    |
| ------------------------------------------------------------- | -------------------------- | -------------------------------------------------------------------------- |
| `validate_price_field(value, field_name)`                     | `shared.price_validation`  | Decimal coercion + validatie voor cost/revenue                             |
| `validate_permissions_with_regions(roles, perms, email, ctx)` | `shared.auth_utils`        | Permission check MET regionale scoping — retourneert `regional_info` dict  |
| `determine_regional_access(user_roles, resource_context)`     | `shared.auth_utils`        | Bepaalt `allowed_regions` en `has_full_access` voor een user               |
| `has_event_access(member_id, event_id)`                       | `shared.event_access`      | Check of member toegang heeft tot een specifiek event (via allowed_events) |
| `is_presmeet_admin(user_roles)`                               | `shared.event_access`      | Check of user event-admin rechten heeft                                    |
| `validate_event_constraints(event, order_items)`              | `shared.event_constraints` | Capaciteitsbeperkingen valideren bij registratie                           |
| `validate_order_items(items, product_config)`                 | `shared.event_validation`  | Validatie van bestelde items tegen product configuratie                    |

**Backend — Lokaal in Event Handlers:**

| Helper                                     | Locatie                                      | Gebruik                                                    |
| ------------------------------------------ | -------------------------------------------- | ---------------------------------------------------------- |
| `validate_dates(body)`                     | `create_event/app.py`, `update_event/app.py` | Datum ordering (registration_open < close <= start <= end) |
| `validate_constraints(constraints)`        | `create_event/app.py`, `update_event/app.py` | Constraints array structuur validatie                      |
| `_check_slug_uniqueness(slug, exclude_id)` | `create_event/app.py`, `update_event/app.py` | Landing page slug uniciteit                                |
| `validate_required_fields(body)`           | `create_event/app.py`                        | Check verplichte velden aanwezig                           |

**Frontend — Event Types & Registry (TypeScript):**

| Helper                           | Locatie                            | Gebruik                                                   |
| -------------------------------- | ---------------------------------- | --------------------------------------------------------- |
| `getCategoryForType(eventType)`  | `config/eventFields/eventTypes.ts` | Auto-derive event_category van event_type                 |
| `requiresLinkedRegio(eventType)` | `config/eventFields/eventTypes.ts` | Check of type regio-gebonden is (legacy, nu altijd regio) |
| `getTypesForCategory(category)`  | `config/eventFields/eventTypes.ts` | Types per categorie voor gegroepeerde dropdown            |
| `EVENT_TYPE_LABELS`              | `config/eventFields/eventTypes.ts` | Nederlandstalige labels voor event types                  |
| `EVENT_TYPES_BY_CATEGORY`        | `config/eventFields/eventTypes.ts` | Gegroepeerde type lijst                                   |
| `EVENT_CATEGORY_LABELS`          | `config/eventFields/eventTypes.ts` | Nederlandstalige categorie labels                         |
| `PARTICIPATION_MODE_LABELS`      | `config/eventFields/eventTypes.ts` | Labels voor open/besloten                                 |

**Frontend — Regionale Access Control (TypeScript):**

| Helper                                             | Locatie                        | Gebruik                                                  |
| -------------------------------------------------- | ------------------------------ | -------------------------------------------------------- |
| `getAllowedRegions(userRoles, hasFullAccess)`      | `utils/regionalMapping.tsx`    | Lijst van regio's waar user toegang heeft                |
| `hasRegionalAccess(userRoles, region)`             | `utils/regionalMapping.tsx`    | Check of user een specifieke regio mag zien              |
| `getRegionNameFromId(regionId)`                    | `utils/regionalMapping.tsx`    | Cognito region ID → regionale naam                       |
| `checkUIPermission(user, fn, action, region?)`     | `utils/functionPermissions.ts` | Gecombineerde permission + regio check voor UI elementen |
| `getUserAccessibleRegions(user)`                   | `utils/functionPermissions.ts` | Alle regio's waartoe user toegang heeft                  |
| `userHasPermissionWithRegion(user, perm, region?)` | `utils/functionPermissions.ts` | Permission check met optionele regio-restrictie          |

**Frontend — Financieel & Data (TypeScript):**

| Helper                                   | Locatie                   | Gebruik                                   |
| ---------------------------------------- | ------------------------- | ----------------------------------------- |
| `formatPrice(value)`                     | `utils/formatPrice.ts`    | Veilige prijsweergave (€X.XX)             |
| `toPrice(value)`                         | `utils/formatPrice.ts`    | String/number → number conversie          |
| `isActive(item)` / `isDeactivated(item)` | `utils/productHelpers.ts` | Veilige boolean checks op DynamoDB velden |
