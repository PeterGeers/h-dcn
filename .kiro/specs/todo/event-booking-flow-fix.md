# Event Booking Flow — End-to-End Fix

## Context

De event booking flow is gebouwd in losse componenten die niet end-to-end verbonden zijn. Alle stukken bestaan maar werken niet samen. Testresultaat (23 juni 2026): geen enkel pad van landing page tot booking werkt volledig.

## Bestaande componenten (allemaal al gebouwd)

| Component         | Locatie                                                | Functie                                           | Status                                          |
| ----------------- | ------------------------------------------------------ | ------------------------------------------------- | ----------------------------------------------- |
| EventLandingPage  | `modules/events/EventLandingPage.tsx`                  | Publieke event pagina via slug                    | ✅ Werkt                                        |
| EventRegisterPage | `modules/eventBooking/pages/EventRegisterPage.tsx`     | State machine: Password → Auth → Registry → Claim | ❌ Vast op ontbrekend wachtwoord                |
| PasswordGate      | `modules/eventBooking/components/PasswordGate.tsx`     | Event wachtwoord invoer → session token           | ✅ Gebouwd, geen UI om wachtwoord in te stellen |
| RegistrySelector  | `modules/eventBooking/components/RegistrySelector.tsx` | Club kiezen uit S3 registry lijst                 | ✅ Gebouwd, geen registry bestand aanwezig      |
| ClaimAction       | `modules/eventBooking/components/ClaimAction.tsx`      | Club claimen → allowed_events update              | ✅ Gebouwd                                      |
| OnboardingFlow    | `modules/eventBooking/components/OnboardingFlow.tsx`   | Club assignment voor booking pagina               | ✅ Gebouwd                                      |
| BookingWizard     | `modules/eventBooking/components/BookingWizard.tsx`    | Producten kiezen, personen, betaling              | ✅ Gebouwd                                      |
| EventBookingPage  | `modules/eventBooking/pages/EventBookingPage.tsx`      | Container voor booking + onboarding               | ✅ Gebouwd                                      |

## Gevonden problemen (23 juni 2026)

1. **Event wachtwoord niet instelbaar** — EventForm heeft geen veld voor `event_password`. Admin kan geen wachtwoord configureren voor de PasswordGate. ✅ GEFIXT: veld toegevoegd aan EventForm + backend accepteert nu event_password met bcrypt hashing.

2. **Registry bestand ontbreekt** — Er is geen S3 registry JSON voor het test event. RegistrySelector kan niets laden. ✅ GEFIXT: test registry met 5 clubs geüpload via migration script.

3. **Ingelogde gebruikers slaan onboarding over** — Landing page stuurde direct naar /booking (gefixt: nu altijd via /register). Maar /register verwacht een session token die alleen van PasswordGate komt. ✅ BEVESTIGD: EventRegisterPage checkt allowed_events en redirected of toont PasswordGate.

4. **Event IDs zijn inconsistent** — Test data gebruikt niet-UUID IDs (`presmeet_2025_test`, `presmeet-2027`, `test-event-presmeet-2027`). allowed_events verwijst naar verkeerde IDs. ✅ GEFIXT: gemigreerd naar UUID `542609d8-891e-4f9e-ab97-0c8b3a8c0293`, oude records verwijderd.

5. **`x-session-token` CORS** — Was geblokkeerd (gefixt: toegevoegd aan allowed headers).

6. **`status` veld ontbrak** — Events hadden geen publicatiestatus (gefixt: draft/published/archived model geïmplementeerd).

7. **Registratie datums werden niet gebruikt** — Backend keek alleen naar `status` veld (gefixt: gebruikt nu registration_open/close datums).

8. **Session token signing mismatch** — `get_event_registry` gebruikte een ander secret (`SESSION_TOKEN_SECRET` statisch) dan `verify_event_password` (per-event `JWT_SECRET_BASE:{event_id}`). Tokens werden NOOIT gevalideerd. ✅ GEFIXT: `get_event_registry` gebruikt nu dezelfde per-event secret + SAM template bijgewerkt.

9. **`landing_page_enabled` verkeerd gelezen** — `get_event_public` las `event_item.landing_page_enabled` (top-level veld dat niet bestaat) in plaats van `landing_page.enabled`. ✅ GEFIXT.

## Wat er moet gebeuren

### Stap 1: Admin configuratie compleet maken

- [x] Voeg `event_password` veld toe aan EventForm (in de Configuratie accordion)
- [x] Backend: `event_password` + `registry_config` toegevoegd aan allowed/updatable fields in create_event en update_event, met bcrypt hashing
- [x] Voeg `registry_config` veld toe (of maak een apart admin scherm voor registry upload)
- [x] Documenteer welke velden nodig zijn om een closed event volledig te configureren

### Stap 2: Test data compleet maken

- [x] Migreer event `presmeet_2025_test` naar een UUID-based record → `542609d8-891e-4f9e-ab97-0c8b3a8c0293` (migration script: `scripts/migrate_presmeet_test_event.py`)
- [x] Zorg dat het event alle benodigde velden heeft: event_password, registry config, status=published
- [x] Zorg dat test user's `allowed_events` naar het nieuwe event_id wijst (4 members bijgewerkt)
- [x] Upload een test registry JSON naar S3 voor dat event (5 clubs)

### Stap 3: Flow valideren per stap

- [x] Landing page → knop "Register" → /events/:slug/register (code correct, EventLandingPage links naar `/events/${slug}/register`)
- [x] PasswordGate: wachtwoord invoeren → session token ontvangen (verify_event_password handler OK, test passes)
- [x] RegistrySelector: clubs laden uit S3, club selecteren (get_event_registry handler gefixt: signing secret was inconsistent → nu per-event secret, tests pass)
- [x] ClaimAction: club claimen → allowed_events geüpdatet → redirect naar booking (event_onboard handler, code correct)
- [ ] BookingPage: producten tonen, bestelling plaatsen (vereist deploy + handmatige test)

### Stap 4: Ingelogde gebruiker pad

- [x] Ingelogd + event in allowed_events → skip onboarding, direct booking (EventRegisterPage `checkEventAccess()` redirect)
- [x] Ingelogd + event NIET in allowed_events → onboarding flow (password → registry → claim) (flow falls through correctly)
- [x] Niet ingelogd → volledige flow (password → login/signup → registry → claim → booking) (full state machine in EventRegisterPage)

## Referenties

- Spec: `.kiro/specs/Events/closed-community-booking/BookingForm.md` — volledige ontwerp
- Spec: `.kiro/specs/Events/closed-community-booking/design.md` — technisch design
- ADR: `docs/decisions/event-lifecycle-status.md` — status model (draft/published/archived)
- Referentie site: https://www.harleyclub.lt/ (PM2026 Litouwen, wachtwoord: PM2026Lithuania)
- Landing page content: `.kiro/specs/todo/pm2027-landing-page-content.md`

## Aanpak

Geen nieuwe architectuur. Geen spec sessie nodig — voer de taken hierboven direct uit in een Vibe sessie:

1. Admin UI velden toevoegen zodat events volledig configureerbaar zijn
2. Test data migreren naar UUID + ontbrekende velden invullen
3. Flow stap voor stap valideren en fixen waar het breekt

## Vereiste velden voor een volledig geconfigureerd closed event

| Veld                                       | Waar in te stellen                          | Beschrijving                                 |
| ------------------------------------------ | ------------------------------------------- | -------------------------------------------- |
| `status`                                   | EventForm → Publicatiestatus                | Moet `published` zijn                        |
| `event_password`                           | EventForm → Configuratie → Event Wachtwoord | Plaintext invoer, opgeslagen als bcrypt hash |
| `registry_config.s3_path`                  | EventForm → Configuratie → S3 Pad           | Key naar invitee_registry.json in S3         |
| `registry_config.row_label`                | EventForm → Configuratie → Rij label        | "club", "team", etc.                         |
| `registry_config.claim_mode`               | EventForm → Configuratie → Claim modus      | first_come_first_served of email_restricted  |
| `registry_config.allow_logo_upload`        | EventForm → Configuratie → Logo upload      | Boolean                                      |
| `landing_page.enabled`                     | EventForm → Landing Page → Enabled          | Moet `true` zijn voor publieke pagina        |
| `landing_page.slug`                        | EventForm → Landing Page → Slug             | URL pad (bijv. "presmeet-2027")              |
| `product_ids`                              | EventForm → Configuratie → Producten        | Gekoppelde webshop producten                 |
| `registration_open` / `registration_close` | EventForm → Registratie                     | Bepaalt wanneer boeken mogelijk is           |

Daarnaast moet het invitee registry JSON bestand daadwerkelijk in S3 staan op het opgegeven `s3_path`.
