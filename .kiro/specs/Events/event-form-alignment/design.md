# Design Document: Event Form Alignment

## Overview

Brengt de frontend EventForm, backend handlers, en bestaande DynamoDB data in lijn met de Event Field Registry. De kern: de registry is de source of truth, backend en frontend moeten daarop aansluiten, en bestaande data wordt non-destructief gemigreerd.

Referenties:

- Field Registry: #[[file:frontend/src/config/eventFields/index.ts]]
- Event Types: #[[file:frontend/src/config/eventFields/eventTypes.ts]]
- Backend create: #[[file:backend/handler/create_event/app.py]]
- Backend update: #[[file:backend/handler/update_event/app.py]]
- Frontend form: #[[file:frontend/src/modules/events/components/EventForm.tsx]]

## Architecture

### Dataflow

```
EventForm (frontend)
  │
  ├─ POST /events  → create_event handler → DynamoDB Events table
  └─ PUT /events/{id} → update_event handler → DynamoDB Events table

Velden volgen exact de Field Registry keys.
event_category wordt auto-derived via getCategoryForType().
```

### Backend Uitbreiding

De handlers worden uitgebreid met additionele velden. Geen breaking changes.

**Bestaande shared helpers die MOETEN worden hergebruikt:**

| Helper                                     | Locatie                   | Gebruik                                               |
| ------------------------------------------ | ------------------------- | ----------------------------------------------------- |
| `validate_price_field(value, field_name)`  | `shared.price_validation` | Validatie + Decimal coercion voor `cost` en `revenue` |
| `validate_dates(body)`                     | Lokaal in handler         | Datum ordering validatie (reeds aanwezig)             |
| `validate_constraints(constraints)`        | Lokaal in handler         | Constraints array validatie (reeds aanwezig)          |
| `_check_slug_uniqueness(slug, exclude_id)` | Lokaal in handler         | Landing page slug uniciteit (reeds aanwezig)          |

**create_event `allowed_fields`:**

```python
allowed_fields = [
    # core
    'name', 'event_type', 'event_category', 'participation',
    'linked_regio', 'location', 'slug', 'poster_url',
    # dates
    'start_date', 'end_date', 'registration_open', 'registration_close', 'payment_deadline',
    # config
    'constraints', 'product_ids', 'landing_page',
    # financial
    'participants', 'cost', 'revenue', 'notes',
]
```

**update_event `updatable_fields`:** identiek aan bovenstaande lijst.

**Financiële velden validatie (in beide handlers):**

```python
from shared.price_validation import validate_price_field

# Valideer en coerce cost/revenue vóór opslag
for field in ['cost', 'revenue']:
    if field in body and body[field] is not None:
        decimal_value, error = validate_price_field(body[field], field)
        if error:
            return create_error_response(400, error)
        body[field] = decimal_value

# Valideer participants als integer
if 'participants' in body and body['participants'] is not None:
    try:
        body['participants'] = int(body['participants'])
        if body['participants'] < 0:
            return create_error_response(400, 'participants must be non-negative')
    except (ValueError, TypeError):
        return create_error_response(400, 'participants must be an integer')
```

### Frontend Form Structuur

Het formulier is opgedeeld in secties die overeenkomen met de field groups. Alleen **core** is altijd zichtbaar en verplicht. Alle andere groepen zijn **optioneel** en worden getoond als collapsible secties (Chakra UI `Accordion` of `Collapse`) die de gebruiker kan openen om extra data toe te voegen.

**Layout:**

1. **Core** (altijd open, niet inklapbaar): name, event_type, participation, start_date, end_date, linked_regio, location, poster_url
2. **Registratie** (collapsible, standaard open bij nieuw event): registration_open, registration_close, payment_deadline
3. **Configuratie** (collapsible, standaard dicht): product_ids, constraints
4. **Financieel** (collapsible, standaard dicht, alleen met permissie): participants, cost, revenue, notes
5. **Landing Page** (collapsible, standaard dicht): bestaande LandingPageSection component
6. **Conditioneel** (inline bij core): slug

`event_category` is een derived field — niet in het formulier maar wel in de payload.

**UX patroon:** De collapsible secties tonen een header met groepsnaam + korte beschrijving. Indien de groep al data bevat (bij bewerken), wordt die sectie automatisch open getoond.

### Regionale Toegangscontrole

Elk event heeft een `linked_regio` (verplicht). Dit bepaalt wie het event mag bewerken:

```
┌─────────────────────────────────────────────────────────────┐
│ linked_regio = specifieke regio (bijv. "Noord-Holland")     │
│   → Bewerkbaar door:                                        │
│     - Regio-vertegenwoordiger van die regio (RegionX_*)     │
│     - Regio_All                                             │
│     - Events_CRUD                                           │
├─────────────────────────────────────────────────────────────┤
│ linked_regio = "regio_all"                                  │
│   → Bewerkbaar door:                                        │
│     - Regio_All                                             │
│     - Events_CRUD                                           │
│   → NIET door individuele regio-vertegenwoordigers          │
└─────────────────────────────────────────────────────────────┘
```

**Backend enforcement (update_event):**

```python
# Na auth check, vóór update uitvoeren:
event_regio = current_event.get('linked_regio')

# Users met Events_CRUD of Regio_All mogen altijd
if not has_role(user_roles, ['Events_CRUD', 'Regio_All']):
    # Regio-user: check of hun regio matcht
    user_region = get_user_region(user_roles)
    if event_regio != user_region:
        return create_error_response(403, 'Je hebt geen rechten om events in deze regio te bewerken')
```

**Frontend enforcement:**

- Edit-knop alleen actief als gebruiker rechten heeft op basis van event.linked_regio
- linked_regio dropdown beperkt tot eigen regio('s) voor regio-gebruikers
- Bij aanmaken: linked_regio automatisch ingesteld op de regio van de gebruiker (als er maar één is)

### Migratie Strategie (clean break)

| Oud veld          | Nieuw veld            | Logica                  |
| ----------------- | --------------------- | ----------------------- |
| title             | name                  | Kopieer                 |
| date              | start_date + end_date | Zelfde datum voor beide |
| status: published | status: open          | Mapping                 |
| status: cancelled | status: archived      | Mapping                 |
| _(ontbreekt)_     | event_type            | Default: 'other'        |
| _(ontbreekt)_     | registration_open     | start_date - 30 dagen   |
| _(ontbreekt)_     | registration_close    | start_date - 1 dag      |

Oude velden (title, date, description, max_participants) worden VERWIJDERD na migratie. Geen backward compatibility nodig — migratie draait vóór de frontend deploy.

## Components and Interfaces

### Backend Components

- `create_event/app.py` — uitgebreide `allowed_fields` + `validate_price_field()` voor cost/revenue
- `update_event/app.py` — uitgebreide `updatable_fields` + `validate_price_field()` voor cost/revenue
- `scripts/migrate_events_to_new_schema.py` — migratiescript met --dry-run, verwijdert oude velden

### Frontend Components

- `EventForm.tsx` — herschreven met registry-veldnamen en nieuwe secties
- `EventList.tsx` — gebruikt uitsluitend nieuwe veldnamen (geen fallbacks)
- `EventAdminPage.tsx` — Event type interface update

### Shared

- `config/eventFields/` — Field Registry (reeds compleet)
- `config/eventFields/eventTypes.ts` — Type taxonomy (reeds aanwezig)

## Data Models

### Event Record (DynamoDB — na migratie)

```typescript
interface EventRecord {
  // core
  event_id: string; // PK, UUID
  name: string; // required
  event_type: EventType; // required
  event_category: EventCategory; // derived
  participation: ParticipationMode;
  linked_regio?: EventRegio;
  status: "draft" | "open" | "closed" | "archived";
  location?: string;
  slug?: string;
  poster_url?: string;

  // dates
  start_date: string; // required, ISO date
  end_date: string; // required, ISO date
  registration_open: string; // required, ISO datetime
  registration_close: string; // required, ISO datetime
  payment_deadline?: string;

  // config
  product_ids?: string[];
  constraints?: Constraint[];
  landing_page?: LandingPageMap;

  // financial
  participants?: number;
  cost?: number; // Decimal in DynamoDB
  revenue?: number; // Decimal in DynamoDB
  notes?: string;

  // booking
  event_password?: string; // bcrypt hash, write-only
  registry_config?: object;
  registry_claims?: object;

  // metadata
  created_at: string;
  created_by: string;
  updated_at?: string;
  status_changed_at?: string;
  status_changed_by?: string;
}
```

## Error Handling

- Backend retourneert specifieke foutmeldingen bij validatiefouten (missing fields, date ordering)
- Frontend toont de backend error message in plaats van het generieke "Invoergegevens zijn niet correct"

## Testing Strategy

- **Backend**: pytest unit tests voor create/update met de nieuwe velden (moto mock)
- **Migratie**: --dry-run validatie op test environment vóór uitvoering
- **Frontend**: handmatige verificatie op testportal.h-dcn.nl (event aanmaken, bewerken, lijst)
- **Type safety**: `npx tsc --noEmit` moet slagen na frontend wijzigingen
- **Deployment order**: migratiescript → backend deploy → frontend deploy (geen overlap waar oude+nieuwe code tegelijk draait)
