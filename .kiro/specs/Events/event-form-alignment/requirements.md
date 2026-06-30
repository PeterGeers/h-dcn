# Requirements Document

## Introduction

De Event module heeft een mismatch tussen drie lagen: de Field Registry (single source of truth, nu compleet), de backend handlers (grotendeels aligned maar missen nieuwe velden), en de frontend EventForm (stuurt nog het oude formaat). Het resultaat is dat de frontend geen events meer kan aanmaken (400 error). Deze spec brengt alle lagen in lijn met de Event Field Registry.

## Glossary

- **Field Registry**: De single source of truth voor veldnamen, types, en validatie (`frontend/src/config/eventFields/`)
- **Event Type Taxonomy**: Hiërarchische classificatie van evenementen in categorieën en types (`eventTypes.ts`)
- **Seed Data**: Testdata in DynamoDB (SEED-events-001 t/m 005) die het oude schema gebruikt

## Requirements

### Requirement 1: Backend accepteert alle registry-velden

**User Story:** Als admin wil ik alle velden uit de Field Registry kunnen invullen bij het aanmaken/bewerken van een event, zodat het systeem consistent werkt.

#### Acceptance Criteria

1. WHEN een event wordt aangemaakt, de `create_event` handler SHALL alle schrijfbare registry-velden accepteren: event_category, participation, linked_regio, poster_url, participants, cost, revenue, notes
2. WHEN een event wordt bijgewerkt, de `update_event` handler SHALL dezelfde uitgebreide veldlijst ondersteunen
3. WHEN cost of revenue wordt opgeslagen, de handler SHALL `validate_price_field()` uit `shared.price_validation` gebruiken voor validatie en Decimal coercion (conform financiële veldregels)
4. WHEN participants wordt opgeslagen, de handler SHALL deze als integer valideren (geen Decimal, geen negatief)
5. WHEN event_type wordt meegegeven, de handler SHALL valideren tegen de bekende enum waarden en afwijzen bij onbekende types
6. ALL validatie SHALL bestaande shared helpers gebruiken waar beschikbaar: `validate_price_field()` voor financiële velden, `validate_dates()` voor datumvelden, `validate_constraints()` voor constraints

### Requirement 2: Frontend EventForm stuurt het nieuwe formaat

**User Story:** Als admin wil ik een werkend formulier waarmee ik de verplichte velden kan invullen en optioneel extra groepen kan toevoegen, zodat ik snel of gedetailleerd events kan beheren.

#### Acceptance Criteria

1. THE formulier SHALL de registry-veldnamen gebruiken: name (was title), start_date (was event_date), linked_regio (was region)
2. THE core groep (name, event_type, participation, start_date, end_date, linked_regio, location, poster_url) SHALL altijd zichtbaar en niet inklapbaar zijn
3. ALL overige groepen (registratie, config, financial, landing_page) SHALL als collapsible/accordion secties getoond worden die de gebruiker kan openen
4. WHEN een collapsible sectie al data bevat (bij bewerken), deze SHALL automatisch open getoond worden
5. THE registratie groep (registration_open, registration_close, payment_deadline) SHALL standaard open zijn bij het aanmaken van een nieuw event
6. THE financiële groep SHALL alleen zichtbaar zijn voor gebruikers met financiële permissies
7. WHEN een event_type wordt geselecteerd, THE formulier SHALL automatisch event_category afleiden via getCategoryForType()
8. THE poster_url veld SHALL beschikbaar zijn met ondersteuning voor upload (PDF, PNG, JPG, max 10MB)
9. THE participation mode (open/closed) SHALL selecteerbaar zijn
10. THE linked_regio veld SHALL altijd zichtbaar zijn in core (niet conditioneel) en verplicht

### Requirement 3: Migratiescript voor bestaande event data

**User Story:** Als beheerder wil ik de bestaande event records normaliseren naar het nieuwe schema, zodat ze correct weergegeven worden.

#### Acceptance Criteria

1. THE script SHALL mappen: title → name, date → start_date + end_date (zelfde dag)
2. THE script SHALL status mappen: published → open, cancelled → archived
3. WHEN event_type ontbreekt, THE script SHALL 'other' als default invullen
4. THE script SHALL registration_open (start_date - 30 dagen) en registration_close (start_date - 1 dag) toevoegen als defaults
5. THE script SHALL --dry-run ondersteunen (wijzigingen tonen zonder te schrijven)
6. THE script SHALL --profile nonprofit-deploy gebruiken voor AWS access
7. THE script SHALL oude velden VERWIJDEREN na migratie (title, date, description, max_participants) — geen backward compatibility nodig

### Requirement 4: Frontend EventList toont het nieuwe formaat

**User Story:** Als admin wil ik de evenementenlijst correct zien na de migratie.

#### Acceptance Criteria

1. THE lijst SHALL name tonen (geen fallbacks naar oude veldnamen nodig — data is gemigreerd)
2. THE sortering SHALL start_date gebruiken
3. THE regiofilter SHALL werken op linked_regio

### Requirement 5: Event Type interface in het formulier

**User Story:** Als admin wil ik event types kiezen uit een gestructureerde lijst, zodat ik snel het juiste type vind.

#### Acceptance Criteria

1. THE dropdown SHALL event types tonen gegroepeerd per categorie (Vergaderingen, Rallies, Ritten, Overig)
2. THE labels SHALL Nederlandstalig zijn (uit EVENT_TYPE_LABELS)
3. WHEN een type geselecteerd wordt, THE categorie SHALL automatisch ingesteld worden

### Requirement 6: Poster/afbeelding upload

**User Story:** Als admin wil ik een poster of afbeelding bij een evenement uploaden, zodat deze getoond kan worden in het overzicht en op de landing page.

#### Acceptance Criteria

1. THE upload SHALL via S3 presigned URL verlopen (hergebruik bestaande infra)
2. THE poster_url veld SHALL de S3 object URL opslaan
3. THE systeem SHALL PDF, PNG, JPG/JPEG accepteren tot maximaal 10MB
4. THE poster SHALL als thumbnail getoond worden in het event overzicht

### Requirement 7: Regionale toegangscontrole op events

**User Story:** Als regio-vertegenwoordiger wil ik alleen mijn eigen regio-evenementen kunnen bewerken, zodat regionale autonomie gewaarborgd blijft.

#### Acceptance Criteria

1. EVERY event SHALL een linked_regio hebben (verplicht veld in core)
2. WHEN een gebruiker met een regionale rol (bijv. Region1_Events_CRUD) een event aanmaakt, THE linked_regio SHALL automatisch ingesteld worden op hun regio
3. WHEN een event linked_regio heeft die NIET 'regio_all' is, alleen de regio-vertegenwoordiger van die specifieke regio EN gebruikers met Regio_All of Events_CRUD SHALL het event mogen bewerken
4. WHEN een event linked_regio 'regio_all' heeft, alleen gebruikers met Regio_All of Events_CRUD SHALL het event mogen bewerken
5. THE backend update_event handler SHALL de linked_regio controleren tegen de user roles vóór het toestaan van wijzigingen
6. THE frontend SHALL de edit-knop alleen tonen/activeren als de gebruiker rechten heeft op basis van de linked_regio van het event
7. WHEN een regio-gebruiker het formulier opent, de linked_regio dropdown SHALL beperkt zijn tot hun eigen regio('s)
