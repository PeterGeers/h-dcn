# Kiro Answers: Event System

## Diagnose: Wat is er aan de hand?

Er zijn **twee schema-interpretaties** die conflicteren:

### Booking system code (`get_order`, `EventBookingPage`)

- Verwacht: `name`, `event_type`, `participation`, `status`
- Gebruikt `participation: 'closed'` + `allowed_events` op Members voor toegangscontrole
- Code zoekt op `status === 'open'` maar dat is geen geldig status-waarde in het model

### Field Registry (`eventFields/`)

- Definieert `status` met opties: `['draft', 'published', 'archived']`
- `participation` met opties: `['open', 'closed']`
- De booking code verwarde `status` met `participation` — het zocht op `status === 'open'`

### Het "Webshop" record

- `evt-webshop` is een synthetisch record voor het unified order systeem (`source_id`)
- Geen echt evenement — een brug tussen webshop-flow en event-order-pipeline
- `get_events` retourneert het gewoon mee in de scan

---

## Waarom dingen kapot zijn

| Symptoom                                   | Oorzaak                                                                              |
| ------------------------------------------ | ------------------------------------------------------------------------------------ |
| Toerweekend verdween na "published" zetten | Dashboard filtert op `status === 'open'`, maar `'open'` is geen geldig status        |
| Webshop verscheen als event                | Fallback: als 0 events matchen, toont Dashboard de eerste 3 ongeacht type            |
| "Event access required" voor ALV           | `participation: 'closed'` + user niet in `allowed_events`                            |
| Webshop toont geen artikelen meer          | WebshopPage filtert op verwijderd veld `event_ids` op producten — matched niets meer |

---

## Architectuurbesluit: Eén pipeline voor alles

### De webshop IS een event

De webshop (`evt-webshop`) is een event record in de Events-tabel. Dit is een bewust besluit zodat webshop en event booking **dezelfde pipeline** gebruiken:

```
Event (of webshop) → product_ids → GET /products?product_ids=x,y,z → producten
```

### Productkoppeling: eenrichtingsverkeer via Event

- **Event → product_ids**: het event bepaalt welke producten beschikbaar zijn
- **Product → event_ids**: VERWIJDERD uit de registry (oud patroon, twee bronnen van waarheid)

De koppeling is uitsluitend: `event.product_ids` bevat de lijst product IDs.

### Waarom de webshop geen artikelen toont

`WebshopPage.tsx` gebruikt nog het oude verwijderde patroon:

```typescript
// OUD (broken) — filtert op een veld dat niet meer bestaat:
const webshopProducts = allProducts.filter((p) =>
  (p.event_ids || []).includes("evt-webshop"),
);
```

De fix: WebshopPage moet dezelfde flow gebruiken als event booking:

1. Laad het `evt-webshop` event record → haal `product_ids` op
2. Fetch producten via `GET /products?product_ids=x,y,z`

Dit aligned de webshop met de rest van het systeem.

---

## Besluit: Status-model (twee onafhankelijke velden)

### `status` = publicatie-levenscyclus van het event

| Waarde      | Betekenis                                                   |
| ----------- | ----------------------------------------------------------- |
| `draft`     | Niet zichtbaar, alleen admin                                |
| `published` | Zichtbaar op event calendar voor gebruikers                 |
| `archived`  | Verborgen na afloop (**automatisch**: `end_date < vandaag`) |

### `participation` = wie mag zich aanmelden

| Waarde    | Betekenis                                                                |
| --------- | ------------------------------------------------------------------------ |
| `open`    | Iedereen mag deelnemen (geen authenticatie/lidmaatschap vereist)         |
| `members` | Alleen H-DCN leden — optioneel beperkt tot specifieke lidmaatschapstypen |
| `closed`  | Alleen mensen in `allowed_events` lijst op Members record                |

Bij `members` kan optioneel een `allowed_membership_types` lijst op het event record staan (bijv. `['regulier', 'ereleden']`). Leeg of afwezig = alle lidmaatschapstypen toegestaan.

### `registration_open` / `registration_close` = tijdvenster

- `registration_open` kan maanden voor `start_date` liggen
- `registration_close` moet ≤ `end_date` zijn
- Buiten dit venster is aanmelden niet mogelijk, ongeacht `participation`

### Automatische archivering

- `event_status_scheduler` (bestaande handler) zet `status: 'archived'` wanneer `end_date < vandaag`
- Gearchiveerde events verdwijnen van de calendar maar blijven querybaar voor historische orders

### Simpele events (alleen core fields)

- Zichtbaar op de calendar als `status === 'published'`
- Klikbaar → toont poster/beschrijving
- Geen booking flow als er geen `product_ids` of `registration_open`/`registration_close` zijn ingesteld

---

## Twee gescheiden concerns: Toegang vs Orderflow

Het huidige probleem is dat **toegang** (wie mag erbij) en **orderflow** (hoe wordt besteld) in de code als één ding behandeld worden. Het zijn twee onafhankelijke assen:

### As 1: Toegang (WIE mag erbij)

Bepaalt of een persoon het event kan zien en een order mag starten.

| Check                   | Veld                                       | Error bij falen                                                 |
| ----------------------- | ------------------------------------------ | --------------------------------------------------------------- |
| Is het event live?      | `status === 'published'`                   | "Event niet beschikbaar"                                        |
| Mag deze user erbij?    | `participation` + `allowed_events`         | "Geen toegang tot dit event"                                    |
| Is registratie nu open? | `registration_open` / `registration_close` | "Registratie is (nog) niet geopend" / "Registratie is gesloten" |

Dit zijn **sequentiële checks** — als één faalt, stopt het. Gescheiden foutmeldingen zodat de user weet wat er aan de hand is.

### As 2: Orderflow (HOE wordt er besteld)

Bepaalt het _bestelproces_ zodra iemand toegang heeft. **Per event configureerbaar** via een nieuw veld:

#### `order_flow`: `'catalog'` | `'attendee'`

| Flow       | Beschrijving                                                                                                                | Voorbeeld                                           |
| ---------- | --------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| `catalog`  | Normale webshop orderflow. Lijst van artikelen, user voegt toe aan order. Leveroptie kan "afhalen op event" zijn.           | ALV met merchandise, open events met T-shirts       |
| `attendee` | Per deelnemer (attendee) worden artikelen toegevoegd uit een vooraf bepaalde lijst. Order is gekoppeld aan de deelnemer(s). | Toerweekend 2026 (closed community, registry-based) |

#### Verschil in UX

| Aspect           | `catalog`                              | `attendee`                                    |
| ---------------- | -------------------------------------- | --------------------------------------------- |
| Product selectie | Kiezen uit event's `product_ids` lijst | Per attendee kiezen uit event's `product_ids` |
| Order scope      | 1 order per lid                        | 1 order per registry row / delegate           |
| Wie vult in?     | De besteller voor zichzelf             | De besteller voor elke deelnemer              |
| Leveroptie       | Verzenden of afhalen op event          | Altijd gekoppeld aan het event                |
| Typisch voor     | Open events, webshop-met-eventcontext  | Besloten events met namenlijst                |

**Belangrijk: `product_ids` geldt voor beide flows.**

- Elk event (ongeacht orderflow) heeft een `product_ids` lijst die bepaalt wat bestelbaar is
- De normale webshop (`source_id === 'webshop'`) gebruikt óók een product-subset — niet de hele Producten tabel
- De webshop mag niet alle artikelen laten zien, alleen wat gekoppeld is aan de source
- Admin stelt per event/webshop in welke producten beschikbaar zijn

#### Relatie met bestaande code

Het huidige `order_scope` in `get_order` doet al iets vergelijkbaars:

- `order_scope === 'member'` → komt overeen met `catalog` flow
- `order_scope === 'registry_row'` → komt overeen met `attendee` flow

Maar dit wordt nu _afgeleid_ uit het event record via `_resolve_order_scope()` in plaats van expliciet geconfigureerd. Het voorstel is om dit expliciet te maken via `order_flow` op het event record.

### Samenvatting: per event 3 configuratie-assen

| As         | Veld            | Opties                       | Bepaalt                    |
| ---------- | --------------- | ---------------------------- | -------------------------- |
| Publicatie | `status`        | draft / published / archived | Zichtbaarheid              |
| Toegang    | `participation` | open / members / closed      | Wie mag bestellen          |
| Orderflow  | `order_flow`    | catalog / attendee           | Hoe het bestelproces werkt |

Deze drie zijn **onafhankelijk van elkaar**. Elke combinatie is geldig:

- Published + open + catalog = publiek event met artikelenlijst (iedereen welkom)
- Published + members + catalog = leden-only event met webshop-achtige flow
- Published + closed + attendee = Toerweekend (besloten, per deelnemer)
- Published + members + attendee = leden-event met deelnemer-registratie
- Published + open + attendee = publiek event maar per persoon registreren

---

### Stap 1: Fix de Dashboard filtering (direct)

```typescript
// Huidige code (broken):
const relevantEvents = allEvents.filter((e) => e.status === "open");

// Fix:
const relevantEvents = allEvents.filter(
  (e) => e.status === "published" && e.event_type !== "webshop",
);
```

De Dashboard toont alle published events. De booking page checkt vervolgens `participation` + `registration_open/close` bij het openen.

### Stap 2: Backend `get_events` filteren

De handler moet:

- `evt-webshop` excluden (filter op `event_type !== 'webshop'`)
- Voor non-admins: alleen `status === 'published'` retourneren
- Admins: alles retourneren (ook draft/archived)

### Stap 4: Fix booking code (`get_order` handler)

```python
# Huidig (fout):
if participation == 'closed':
    if not has_event_access(member_id, source_id):
        return create_error_response(403, 'Event access required')

# Toevoegen: check registration dates
from datetime import datetime, timezone
now = datetime.now(timezone.utc).strftime('%Y-%m-%d')
reg_open = event_record.get('registration_open', '')
reg_close = event_record.get('registration_close', '')

if reg_open and now < reg_open:
    return create_error_response(403, 'Registration is not yet open')
if reg_close and now > reg_close:
    return create_error_response(403, 'Registration is closed')
```

---

## Is het webshop-record een Event?

**Ja.** Dit is een bewust architectuurbesluit. Het `evt-webshop` record IS een event zodat:

- Dezelfde order pipeline werkt (`source_id` → event → `product_ids` → producten)
- Eén `get_order` handler beide flows bedient
- Geen dubbele product-koppelings-logica nodig is

Het verschil met "echte" events:

- `event_type: 'webshop'` → wordt uitgefilterd van de event calendar
- Geen `registration_open`/`registration_close` (altijd beschikbaar)
- `participation: 'open'` (ieder lid mag bestellen)
- `order_flow: 'catalog'`

---

## Flow diagram (nodig voor alignment)

```
User opent Dashboard
  │
  ├─ GET /events → Backend retourneert: status === 'published' AND event_type !== 'webshop'
  │
  ├─ Dashboard toont: event cards met naam + datum + poster
  │
  └─ User klikt op event
      │
      ├─ TOEGANG CHECKS (sequentieel):
      │   │
      │   ├─ status !== 'published'? → "Event niet beschikbaar"
      │   │
      │   ├─ participation === 'closed' AND user niet in allowed_events?
      │   │   → "Geen toegang tot dit event"
      │   │
      │   ├─ participation === 'members' AND user niet in hdcnLeden?
      │   │   → "Alleen voor H-DCN leden"
      │   │
      │   ├─ vandaag < registration_open? → "Registratie is nog niet geopend"
      │   │
      │   └─ vandaag > registration_close? → "Registratie is gesloten"
      │
      ├─ TOEGANG OK → Bepaal orderflow:
      │   │
      │   ├─ order_flow === 'catalog'?
      │   │   → Toon productlijst (webshop-achtig)
      │   │   → User kiest artikelen + hoeveelheden
      │   │   → Leveroptie: verzenden of afhalen op event
      │   │
      │   └─ order_flow === 'attendee'?
      │       → Toon deelnemers (vanuit registry / delegates)
      │       → Per deelnemer: artikelen selecteren uit product_ids
      │       → Order gekoppeld aan registry_row_id
      │
      └─ Geen product_ids / registration dates?
          → Toon info pagina (poster, beschrijving, locatie) — geen bestelflow

  Admin:
  └─ Ziet alle events (incl. draft/archived)
      └─ Kan status, participation, en order_flow instellen per event
```

---

## Prioritering

| #   | Actie                                                          | Impact                              | Effort      |
| --- | -------------------------------------------------------------- | ----------------------------------- | ----------- |
| 1   | Fix WebshopPage: gebruik `product_ids` van `evt-webshop` event | Hoog — webshop toont weer artikelen | 30 min      |
| 2   | Fix Dashboard filter (`published` + exclude webshop)           | Hoog — lost directe bugs op         | 30 min      |
| 3   | Fix booking code: `status === 'published'` ipv `'open'`        | Hoog — Toerweekend wordt bereikbaar | 15 min      |
| 4   | Backend `get_events` filtering (non-admin = published only)    | Medium                              | 30 min      |
| 5   | Automatische archivering in scheduler                          | Laag — nice to have                 | 30 min      |
| 6   | Event calendar component (toekomst)                            | Laag urgentie                       | Aparte spec |

---

## Dashboard look & feel

**End-user view:**

- "Mijn inschrijvingen" — events waar user een order voor heeft
- "Aankomende events" — published events gesorteerd op start_date

**Admin view:**

- Huidige overzicht met management functies
- Alleen zichtbaar voor admin roles

**Mobile:**

- 1 event card per rij
- Desktop: 4 per rij
- Scrollbaar, gesorteerd op startdatum
