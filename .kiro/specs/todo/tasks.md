# Tasks: Event System Alignment

Implementatie van de besluiten uit `kiroAnswers.md`. Elke ronde is onafhankelijk testbaar.

## Ronde 1: Data alignment ✅

- [x] 1.1 Normaliseer `status` in Events-Test tabel (active/null → published)

## Ronde 2: WebshopPage fix (webshop toont weer artikelen) ✅

- [x] 2.1 Wijzig `WebshopPage.tsx`: vervang het oude `event_ids.includes('evt-webshop')` filter door de unified pipeline (laad `evt-webshop` event → haal `product_ids` → filter producten)
- [x] 2.2 `evt-webshop` in Events-Test heeft 26 product_ids — data is correct
- [ ] 2.3 Test: open webshop in testportal → artikelen verschijnen

## Ronde 3: Dashboard fix (events tonen correct) ✅

- [x] 3.1 Wijzig `Dashboard.tsx` (EventBookingCard): filter op `status === 'published'` en exclude `event_type === 'webshop'`
- [x] 3.2 Verwijderd: de fallback `allEvents.slice(0, 3)` — toont nu niets als geen published events bestaan
- [ ] 3.3 Test: open dashboard → Toerweekend 2026 verschijnt, Webshop niet, geen willekeurige events

## Ronde 4: Backend `get_events` filteren ✅

- [x] 4.1 Wijzig `backend/handler/get_events/app.py`: exclude `event_type === 'webshop'` voor non-admins
- [x] 4.2 Filter: non-admin users krijgen alleen `status === 'published'`; admins krijgen alles
- [ ] 4.3 Deploy naar test: `gh workflow run deploy-backend.yml --ref {branch} -f stage=test`
- [ ] 4.4 Test: dashboard en booking tonen alleen relevante events

## Ronde 5: Toegangschecks scheiden in `get_order` ✅

- [x] 5.1 Wijzig `backend/handler/get_order/app.py`: sequentiële checks met gescheiden foutmeldingen:
  - `status !== 'published'` → "Event niet beschikbaar" (EVENT_NOT_PUBLISHED)
  - `participation === 'closed'` en user niet in `allowed_events` → "Geen toegang tot dit event" (EVENT_ACCESS_DENIED)
  - `participation === 'members'` en user niet in hdcnLeden → "Alleen voor H-DCN leden" (MEMBERS_ONLY)
  - `participation === 'members'` + `allowed_membership_types` check → "Lidmaatschapstype niet toegestaan" (MEMBERSHIP_TYPE_DENIED)
  - `vandaag < registration_open` → "Registratie is nog niet geopend" (REGISTRATION_NOT_OPEN)
  - `vandaag > registration_close` → "Registratie is gesloten" (REGISTRATION_CLOSED)
- [ ] 5.2 Deploy naar test
- [ ] 5.3 Test: klik op closed event zonder access → specifieke foutmelding

## Ronde 6: Field Registry alignment + `order_flow` ✅

- [x] 6.1 Update `eventTypes.ts`: voeg `'members'` toe aan `PARTICIPATION_MODES`, voeg `ORDER_FLOWS` toe
- [x] 6.2 Voeg `order_flow` veld toe aan configFields: enum `['catalog', 'attendee']`, default `'catalog'`
- [x] 6.3 Voeg `allowed_membership_types` veld toe aan configFields: list, leeg = alle typen
- [x] 6.4 Update `evt-webshop` in Events-Test: `order_flow: 'catalog'`
- [x] 6.5 Update Toerweekend 2026 in Events-Test: `order_flow: 'attendee'`
- [ ] 6.6 Test: beide flows werken onafhankelijk in testportal

## Verificatie

- [x] TypeScript compileert zonder fouten (`npx tsc --noEmit`)
- [x] ESLint geen errors op gewijzigde bestanden
- [ ] Deploy frontend naar test: `gh workflow run deploy-frontend.yml --ref {branch} -f stage=test`
- [ ] Deploy backend naar test: `gh workflow run deploy-backend.yml --ref {branch} -f stage=test`
- [ ] Handmatige test in testportal

## Gewijzigde bestanden

### Frontend

- `frontend/src/modules/webshop/WebshopPage.tsx` — unified pipeline ipv event_ids filter
- `frontend/src/modules/webshop/services/api.ts` — nieuwe `getWebshopProducts()` methode
- `frontend/src/pages/Dashboard.tsx` — filter op published + exclude webshop
- `frontend/src/config/eventFields/eventTypes.ts` — members + ORDER_FLOWS
- `frontend/src/config/eventFields/fields/configFields.ts` — order_flow + allowed_membership_types
- `frontend/src/config/eventFields/fields/coreFields.ts` — participation helptext

### Backend

- `backend/handler/get_events/app.py` — non-admin filtering
- `backend/handler/get_order/app.py` — sequential access checks

### Data (Events-Test)

- Alle 13 events: `status` genormaliseerd naar `'published'`
- `evt-webshop`: `order_flow: 'catalog'`
- Toerweekend 2026: `order_flow: 'attendee'`
