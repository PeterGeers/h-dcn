# Booking Form — UI/UX Fixes

Test URL: `https://testportal.h-dcn.nl/events/542609d8-891e-4f9e-ab97-0c8b3a8c0293/booking`

## Bevindingen en taken

### Layout & Information Architecture

- [ ] **Dubbele titel verwijderen** — Page header toont "Presidents Meeting 2027" en het EventInfoHeader blok herhaalt dezelfde naam. Eén van de twee verwijderen of samenvoegen.
- [ ] **Locatie + datums samenvoegen met capaciteitsblok** — Nu zijn het losse blokken zonder visuele samenhang. Maak er één compact event info blok van.
- [x] **Capaciteit: productnamen tonen** — Fallback naar product_id als naam ontbreekt.

### Formulier logica

- [x] **Rol-veld alleen tonen bij producten die het vragen** — Hardcoded role veld verwijderd uit PersonCard. Wordt nu dynamisch gerenderd via ProductConfigurator op basis van order_item_fields.
- [x] **€ NaN fixen** — Producten zonder prijs of met string-prijs crashten de UI. Gefixt: normalisatie met `toPrice()` in `getProducts` API layer.
- [ ] **Productnaam en prijs tonen in dropdown** — "Product toevoegen" dropdown toont items zonder naam of prijs. Toon `naam — €prijs` per optie.

### Data & Type Safety

- [x] **Generic helpers voor DynamoDB velden** — `toPrice()` uit `utils/formatPrice.ts` gebruikt voor prijs normalisatie. Product name fallback naar product_id.
- [ ] **`event_participant` Cognito groep** — Wordt uitgefilterd als "invalid role" in AuthHeaders. Onderzoeken of dit een geldige groep moet zijn of opgeruimd moet worden.

### Look & Feel

- [x] **Dark theme toepassen** — EventInfoHeader, EffectiveLimits en PersonCard gebruiken nu dark theme (bg gray.800, tekst wit/oranje, borders gray.600).
- [ ] **RegistrySelector styling** — Wit op wit, geen logo's zichtbaar. Dark theme + logo rendering fixen.

## Gefixt in deze sessie

- [x] `order_item_fields is not iterable` crash → normalisatie in API layer
- [x] "Registration is not open" → `get_order` checkt nu `status == 'published'`
- [x] "Dit evenement is gearchiveerd" → BookingWizard checkt nu `status !== 'published'`
- [x] Session token signing mismatch → `get_event_registry` gebruikt per-event secret
- [x] S3 registry AccessDenied → ListBucket permissie + correct bestand in test bucket
- [x] Event onboard ValidationException → `if_not_exists` voor registry_claims map
