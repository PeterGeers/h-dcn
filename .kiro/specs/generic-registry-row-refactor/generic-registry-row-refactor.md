# Generic Registry Row Refactor — Spec Input

## Instructie voor Spec Sessie

Dit document is het volledige uitgangspunt voor de spec. **Alle 11 requirements hieronder moeten als requirements worden overgenomen — niet een selectie.** Elk requirement heeft concrete acceptatiecriteria en een exhaustieve lijst van geraakte bestanden. Het design en de taken moeten deze volledig dekken.

## Probleem

De event booking module is gebouwd met "club" als hardcoded concept. Dit maakt het systeem onbruikbaar voor andere scenario's (families, scholen, teams, verenigingen). Het registry concept is generiek (een rij in een S3 tabel met een ID, label, en optioneel logo), maar de implementatie noemt alles `club_*`.

## Root Cause Analyse

1. **Naming bias** — Eerste use case was "clubs". Alles werd `club_*` genoemd. Propageerde naar elke volgende feature.
2. **Geen abstractie** — UI toont hardcoded "club" teksten in plaats van `row_label` uit registry config.
3. **Copy-paste proliferatie** — 8 handlers, 5 componenten, 2 admin views, 6 test files, 15+ translation keys.
4. **Geen schema-first** — Field registry definieert `registry_config` correct, maar code negeerde dit.

---

## Requirements (exhaustief — elk punt is een testbaar criterium)

### REQ-1: Order bevat registry row data

**Probleem:** Orders slaan alleen `club_id` op. De label en logo worden runtime resolved (of helemaal niet).

**Moet:**

- Order record in DynamoDB bevat: `registry_row_id`, `registry_row_label`, `registry_row_logo_url`
- Bij aanmaken order (get_order handler): kopieer row data van member naar order
- Scope-bepaling: als event `registry_config` bestaat → row-scoped order (één order per rij, shared via delegates). Geen `registry_config` → member-scoped.
- VERWIJDER het `order_scope` veld van events (wordt afgeleid uit aanwezigheid van `registry_config`)

**Bestanden:**

- `backend/handler/get_order/app.py` — `_create_draft_order()`, scope logica, `club_id` refs
- `backend/handler/submit_order/app.py` — `_calculate_sold_counts()`, `club_id` filtering
- `backend/handler/pay_order/app.py` — `club_id` op payment records, auth check
- `backend/handler/manage_delegates/app.py` — `club_id` verificatie bij delegate toewijzing

**Acceptatiecriteria:**

- [ ] Nieuw aangemaakte orders voor closed events bevatten `registry_row_id`, `registry_row_label`, `registry_row_logo_url`
- [ ] Bestaande code die `order.club_id` leest werkt met `order.registry_row_id`
- [ ] `order_scope` veld is niet meer nodig op event records
- [ ] Payment records gebruiken `registry_row_id` in plaats van `club_id`

---

### REQ-2: Member record gebruikt generieke veldnamen

**Probleem:** `event_onboard` slaat `club_id: row_id` op het member record. Andere code leest dit als "club".

**Moet:**

- Member record: `registry_row_id` (was `club_id`) — alleen het ID, geen label/logo (die worden pas bij order creation van S3 geresolved)
- `event_onboard` handler: sla `registry_row_id` op bij claim
- Shared layer `get_club_id()` → `get_registry_row_id()`

**Bestanden:**

- `backend/handler/event_onboard/app.py` — `_create_member_record()`, `update_member_event_access()`
- `backend/layers/auth-layer/python/shared/event_access.py` — `get_club_id()`
- `backend/handler/manage_delegates/app.py` — target member `club_id` check
- `backend/handler/admin_event_claims/app.py` — `_find_order_for_row()`, `_create_draft_order_for_claim()`

**Acceptatiecriteria:**

- [ ] Nieuwe members krijgen `registry_row_id` (alleen het ID)
- [ ] `get_registry_row_id(email)` vervangt `get_club_id(email)` in shared layer
- [ ] Delegate toewijzing checkt `registry_row_id` match

---

### REQ-3: Frontend Order interface en componenten

**Probleem:** `Order.club_id`, `ClubLogoUploader`, `OnboardingFlow` met `userClubId` — alles hardcoded club.

**Moet:**

- `Order` interface: `registry_row_id`, `registry_row_label`, `registry_row_logo_url`
- `ClubLogoUploader` → `RegistryRowLogo` (toont logo uit `registry_row_logo_url` op de order, upload naar generiek pad)
- `EventBookingPage`: leest row data van de order, niet apart opvragen
- `BookingSummaryPdf`: gebruikt `registry_row_label` in bestandsnaam en content

**Bestanden:**

- `frontend/src/modules/eventBooking/types/eventBooking.types.ts` — `Order` interface
- `frontend/src/modules/eventBooking/components/ClubLogoUploader.tsx` → hernoemen
- `frontend/src/modules/eventBooking/pages/EventBookingPage.tsx` — `order.club_id` refs
- `frontend/src/modules/eventBooking/components/BookingSummaryPdf.tsx` — filename + content
- `frontend/src/modules/eventBooking/admin/AdminOrderLockUnlock.tsx` — `OrderSummary` interface

**Acceptatiecriteria:**

- [ ] TypeScript compileert zonder errors na interface rename
- [ ] Logo wordt getoond op basis van `order.registry_row_logo_url`
- [ ] PDF bestandsnaam gebruikt `registry_row_label` (niet `club_id`)
- [ ] Admin order lijst toont `registry_row_label`

---

### REQ-4: OnboardingFlow wordt vervangen door RegistrySelector

**Probleem:** `OnboardingFlow` is een oud component dat `/presmeet/clubs` aanroept. `RegistrySelector` doet hetzelfde via het generieke `/events/{event_id}/registry` endpoint.

**Moet:**

- `OnboardingFlow` verwijderen of refactoren naar wrapper rond `RegistrySelector`
- Geen `/presmeet/clubs` of `/presmeet/clubs/assign` calls meer
- `EventBookingPage` gebruikt `RegistrySelector` + `ClaimAction` als onboarding nodig is
- `/presmeet/logo` endpoint → `/events/{event_id}/registry-logo` (of generiek logo upload pad)

**Bestanden:**

- `frontend/src/modules/eventBooking/components/OnboardingFlow.tsx` — verwijderen of refactoren
- `frontend/src/modules/eventBooking/pages/EventBookingPage.tsx` — onboarding logica
- `backend/handler/upload_club_logo/app.py` — hernoemen naar `upload_registry_logo`, generiek maken

**Acceptatiecriteria:**

- [ ] Geen frontend code roept `/presmeet/clubs` of `/presmeet/clubs/assign` aan
- [ ] EventBookingPage toont RegistrySelector als gebruiker geen `registry_row_id` heeft
- [ ] Logo upload werkt via generiek endpoint met `event_id` + `row_id`

---

### REQ-5: PurchaseRules en CountingRule generiek

**Probleem:** `max_per_club`, `min_per_club`, `count_distinct_clubs` — club-specifieke naming.

**Moet:**

- `max_per_club` → `max_per_order`
- `min_per_club` → `min_per_order`
- `count_distinct_clubs` → `count_distinct_rows`
- Backend constraint validatie: gebruikt nieuwe namen
- Frontend `useEffectiveLimits`: gebruikt nieuwe namen

**Bestanden:**

- `frontend/src/modules/eventBooking/types/eventBooking.types.ts` — `PurchaseRules`, `CountingRule`
- `frontend/src/modules/eventBooking/hooks/useEffectiveLimits.ts`
- `frontend/src/modules/eventBooking/components/BookingWizard.tsx` — maxPersons berekening
- `backend/handler/submit_order/app.py` — constraint checking

**Acceptatiecriteria:**

- [ ] Geen `club` in PurchaseRules of CountingRule type definitions
- [ ] Backend en frontend gebruiken dezelfde nieuwe veldnamen
- [ ] Bestaande producten met `max_per_club` in DynamoDB werken nog (migration of backward compat)

---

### REQ-6: Preparation PDF generiek

**Probleem:** `generate_preparation_pdf` handler gebruikt `club_id`, `club_name`, CSS class `club-name`, sort functie `_sort_key_club_name`.

**Moet:**

- Alle `club_*` variabelen → `row_*` of `registry_row_*`
- CSS class: `club-name` → `row-name`
- Sort: `_sort_key_club_name` → `_sort_key_row_label`
- Label in PDF header: gebruikt `row_label` uit event config ("Club: X" of "Team: X" of "School: X")

**Bestanden:**

- `backend/handler/generate_preparation_pdf/app.py` — volledig (325-567)

**Acceptatiecriteria:**

- [ ] PDF genereert correct met generieke row labels
- [ ] Geen "club" hardcoding in PDF output (behalve als `row_label === 'club'`)

---

### REQ-7: Delegate invitation email generiek

**Probleem:** Email template gebruikt `CLUB_NAME` template variabele.

**Moet:**

- Template variabele: `ROW_LABEL` + `ROW_NAME` (bijv. "Je club: H-DCN Nederland" of "Je team: Ajax")
- `_get_club_name()` → `_get_row_label()` — resolved vanuit registry_claims of order

**Bestanden:**

- `backend/handler/send_delegate_invitation/app.py` — template context, `_get_club_name()`
- `backend/email-templates/` — HTML template

**Acceptatiecriteria:**

- [ ] Email toont correcte row label + naam
- [ ] Geen hardcoded "club" in email tekst (tenzij `row_label === 'club'`)

---

### REQ-8: Translations generiek

**Probleem:** ~15 translation keys in 8 talen gebruiken "club" hardcoded.

**Moet:**

- Alle "club" teksten vervangen door `{{rowLabel}}` interpolatie
- `row_label` doorgeven vanuit event registry_config naar alle componenten die het tonen

**Bestanden:**

- `frontend/src/locales/{nl,en,de,fr,es,it,da,sv}/eventBooking.json`
- `frontend/public/locales/{nl,en,de,fr,es,it,da,sv}/eventBooking.json`

**Keys om te wijzigen:**

- `onboarding.select_club` → `onboarding.select_row` met `{{rowLabel}}`
- `onboarding.search_clubs` → `onboarding.search` met `{{rowLabel}}`
- `onboarding.club_assigned` → `onboarding.row_assigned`
- `onboarding.club_already_assigned` → `onboarding.row_already_assigned`
- `admin.fully_paid_clubs` → `admin.fully_paid_rows`
- `admin.lock_unlock.col_club` → `admin.lock_unlock.col_row`
- `errors.clubRequired` → `errors.rowRequired`
- `pdf.club` → verwijderen (gebruik `row_label`)

**Acceptatiecriteria:**

- [ ] Geen hardcoded "club" in translation files (behalve als fallback waarde)
- [ ] UI toont correcte benaming op basis van event `registry_config.row_label`

---

### REQ-9: Layout — EventInfoHeader compact en responsive

**Probleem:** EventInfoHeader en EffectiveLimits zijn twee aparte full-width blokken. Neemt veel ruimte in beslag.

**Moet:**

- Locatie + datums + countdown + capaciteit in één compact blok
- Op desktop: rechts van de pagina titel (naast de heading)
- Op mobiel/smaller scherm: eronder (responsive, geen horizontale scroll)

**Bestanden:**

- `frontend/src/modules/eventBooking/components/EventInfoHeader.tsx`
- `frontend/src/modules/eventBooking/components/EffectiveLimits.tsx`
- `frontend/src/modules/eventBooking/components/BookingWizard.tsx` — layout
- `frontend/src/modules/eventBooking/pages/EventBookingPage.tsx` — page layout

**Acceptatiecriteria:**

- [ ] Op desktop (>768px): info blok naast de titel
- [ ] Op mobiel (<768px): info blok onder de titel
- [ ] Capaciteitsregels tonen productnaam + beschikbaarheid in hetzelfde blok

---

### REQ-10: event_participant Cognito groep

**Probleem:** Console toont "AuthHeaders: Filtering out invalid role: event_participant". Deze groep wordt aangemaakt door de onboard stap maar niet herkend door de frontend auth headers helper.

**Moet:**

- Onderzoeken: wordt `event_participant` groep aangemaakt door `event_onboard`?
- Zo ja: toevoegen aan de geldige groepen whitelist in `utils/authHeaders.ts`
- Zo nee: verwijderen uit Cognito (opruimen)

**Bestanden:**

- `frontend/src/utils/authHeaders.ts` — role filtering logica
- `backend/handler/event_onboard/app.py` — checken of het Cognito groepen aanmaakt

**Acceptatiecriteria:**

- [ ] Geen "Filtering out invalid role" warnings in console voor legitieme groepen
- [ ] Of: groep verwijderd als het niet nodig is

---

### REQ-11: Data migration

**Probleem:** Bestaande DynamoDB records gebruiken `club_id`. Na de refactor moeten ze `registry_row_id` gebruiken.

**Moet:**

- Migration script: `scripts/migrate_club_to_registry_row.py`
- Migreert: Orders (club_id → registry_row_id + label + logo_url resolved from S3), Members (club_id → registry_row_id only), Payments (club_id → registry_row_id)
- Supports `--dry-run`, `--profile`, `--stage test|prod`
- Row label en logo_url resolven vanuit S3 registry bestand op moment van migratie (alleen voor Orders)
- Geen backward compat nodig: migration draait VOOR code deploy

**Acceptatiecriteria:**

- [ ] Alle bestaande orders, members, payments hebben nieuwe veldnamen na migratie
- [ ] Geen data verlies (oude velden worden pas verwijderd na validatie)
- [ ] Script draait idempotent (kan veilig opnieuw gedraaid worden)

---

## Referenties

- Field Registry: `frontend/src/config/eventFields/fields/bookingFields.ts`
- Event Booking Spec: `.kiro/specs/Events/closed-community-booking/`
- Huidige issues: `.kiro/specs/todo/booking-form-fixes.md`
- ADR event lifecycle: `docs/decisions/event-lifecycle-status.md`
