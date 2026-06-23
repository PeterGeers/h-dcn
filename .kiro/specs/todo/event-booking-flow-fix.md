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

1. **Event wachtwoord niet instelbaar** — EventForm heeft geen veld voor `event_password`. Admin kan geen wachtwoord configureren voor de PasswordGate.

2. **Registry bestand ontbreekt** — Er is geen S3 registry JSON voor het test event. RegistrySelector kan niets laden.

3. **Ingelogde gebruikers slaan onboarding over** — Landing page stuurde direct naar /booking (gefixt: nu altijd via /register). Maar /register verwacht een session token die alleen van PasswordGate komt.

4. **Event IDs zijn inconsistent** — Test data gebruikt niet-UUID IDs (`presmeet_2025_test`, `presmeet-2027`, `test-event-presmeet-2027`). allowed_events verwijst naar verkeerde IDs.

5. **`x-session-token` CORS** — Was geblokkeerd (gefixt: toegevoegd aan allowed headers).

6. **`status` veld ontbrak** — Events hadden geen publicatiestatus (gefixt: draft/published/archived model geïmplementeerd).

7. **Registratie datums werden niet gebruikt** — Backend keek alleen naar `status` veld (gefixt: gebruikt nu registration_open/close datums).

## Wat er moet gebeuren

### Stap 1: Admin configuratie compleet maken

- [ ] Voeg `event_password` veld toe aan EventForm (in de Configuratie accordion)
- [ ] Voeg `registry_config` veld toe (of maak een apart admin scherm voor registry upload)
- [ ] Documenteer welke velden nodig zijn om een closed event volledig te configureren

### Stap 2: Test data compleet maken

- [ ] Migreer event `presmeet_2025_test` naar een UUID-based record (migration script dat alle referenties updatet: Orders.source_id, Members.allowed_events, S3 registry paden, product_ids koppelingen)
- [ ] Zorg dat het event alle benodigde velden heeft: event_password, registry config, status=published
- [ ] Zorg dat test user's `allowed_events` naar het nieuwe event_id wijst
- [ ] Upload een test registry JSON naar S3 voor dat event

### Stap 3: Flow valideren per stap

- [ ] Landing page → knop "Register" → /events/:slug/register
- [ ] PasswordGate: wachtwoord invoeren → session token ontvangen
- [ ] RegistrySelector: clubs laden uit S3, club selecteren
- [ ] ClaimAction: club claimen → allowed_events geüpdatet → redirect naar booking
- [ ] BookingPage: producten tonen, bestelling plaatsen

### Stap 4: Ingelogde gebruiker pad

- [ ] Ingelogd + event in allowed_events → skip onboarding, direct booking
- [ ] Ingelogd + event NIET in allowed_events → onboarding flow (password → registry → claim)
- [ ] Niet ingelogd → volledige flow (password → login/signup → registry → claim → booking)

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
