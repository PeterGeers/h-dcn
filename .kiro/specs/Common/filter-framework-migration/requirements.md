# Requirements: Filter Framework Migratie

## Introductie

Het Table Filter Framework (useFilterableTable + FilterableHeader + GenericFilter + FilterPanel) is gebouwd en beschikbaar in het h-dcn project, maar wordt nog door **geen enkele pagina** gebruikt. Alle tabellen gebruiken hun eigen custom filter/sort implementatie met useState + inline .filter()/.sort() calls.

Deze spec migreert alle tabellen naar het gestandaardiseerde framework voor:

- Consistente UX (zelfde filter-gedrag, debounce, sort-toggle overal)
- Minder boilerplate (~50-100 regels minder per tabel)
- Betere toegankelijkheid (aria-sort, aria-label op alle filter inputs)
- Uniforme styling (FilterableHeader in alle tabelheaders)

## Woordenlijst

- **FilterableHeader**: `<Th>` component met label, sort indicator (↑/↓), en inline text filter input
- **FilterPanel**: Container boven de tabel voor dropdown/select filters (status, regio, type)
- **GenericFilter**: Herbruikbare dropdown filter (single-select)
- **useFilterableTable**: Composed hook: text filters (debounced) → sort pipeline
- **useColumnFilters**: Hook voor filter state + debounced substring matching
- **useTableSort**: Hook voor sort state + toggle + comparison
- **Custom implementatie**: Huidige situatie waar elk component eigen useState + .filter() + .sort() gebruikt

## Context Bestanden

- #[[file:frontend/src/hooks/useFilterableTable.ts]]
- #[[file:frontend/src/hooks/useColumnFilters.ts]]
- #[[file:frontend/src/hooks/useTableSort.ts]]
- #[[file:frontend/src/components/filters/FilterableHeader.tsx]]
- #[[file:frontend/src/components/filters/FilterPanel.tsx]]
- #[[file:frontend/src/components/filters/GenericFilter.tsx]]
- #[[file:frontend/src/components/filters/index.ts]]
- #[[file:docs/development/look-and-feel.md]]

## Requirements

### Requirement 1: EventList — Framework Migratie

**User Story:** Als gebruiker wil ik dat de evenementen-tabel consistente filter- en sortfunctionaliteit heeft via de standaard FilterableHeaders, zodat ik kolommen kan filteren en sorteren op dezelfde manier als in andere tabellen.

#### Acceptance Criteria

1. WANNEER de EventList rendert, DAN MOETEN alle kolommen (Naam, Datum, Locatie, Regio, Deelnemers, Kosten, Inkomsten, Winst) een `FilterableHeader` component gebruiken met inline text filter en sort toggle.
2. WANNEER een gebruiker typt in de "Naam" filter, DAN MOET de tabel na 150ms debounce alleen rijen tonen waarvan de naam (case-insensitive) de zoekterm bevat.
3. WANNEER een gebruiker klikt op een kolom header, DAN MOET de sortering wisselen: asc → desc → geen sort.
4. DE bestaande regionale permissie-filtering MOET behouden blijven (niet-zichtbare events worden uitgefilterd VOORDAT het framework filters toepast).
5. DE bestaande losse zoekbalk bovenaan MOET verwijderd worden (vervangen door per-kolom filters in headers).
6. DE styling MOET het h-dcn design system volgen: `color="orange.300"` voor labels, `bg="gray.700"` voor inputs, `orange.400` border focus.

### Requirement 2: MemberAdminTable — Framework Migratie

**User Story:** Als admin wil ik dat de ledentabel het filter framework gebruikt met FilterableHeaders voor text-kolommen en een FilterPanel met GenericFilters voor enum/select-kolommen, zodat het filtergedrag consistent is.

#### Acceptance Criteria

1. WANNEER de MemberAdminTable rendert, DAN MOETEN text-kolommen (naam, lidnummer, email, etc.) een `FilterableHeader` met inline text filter + sort gebruiken.
2. WANNEER de MemberAdminTable rendert, DAN MOETEN enum/select-kolommen (status, regio, lidmaatschap_type) een `GenericFilter` in een `FilterPanel` boven de tabel gebruiken.
3. DE `useFilterableTable` hook MOET het filtering + sorting afhandelen voor de text-kolommen.
4. DE dropdown filters in FilterPanel MOETEN naast de text-filters werken (AND-logic: alle filters moeten passen).
5. DE bestaande sorteerlogica per datatype (number, date, string) MOET behouden blijven via de useTableSort hook (die automatisch numbers/dates/strings herkent).
6. DE "Alle" optie in dropdown filters MOET leeg filteren (alle waarden tonen).
7. DE bestaande regionale permissie-filtering en context-gebaseerde kolom-zichtbaarheid MOET behouden blijven.
8. DE FilterPanel MOET een Reset-knop en resultaat-teller tonen wanneer filters actief zijn.

### Requirement 3: UserManagement — Framework Migratie

**User Story:** Als admin wil ik dat de gebruikersbeheer-tabel FilterableHeaders gebruikt zodat ik op meerdere kolommen kan zoeken en sorteren.

#### Acceptance Criteria

1. WANNEER de UserManagement rendert, DAN MOETEN de kolommen (Email, Username, Status, Aangemaakt) een `FilterableHeader` met inline filter en sort gebruiken.
2. DE bestaande enkele zoekbalk MOET verwijderd worden (vervangen door per-kolom filters).
3. DE sorteerrichting MOET visueel zichtbaar zijn via de ↑/↓ indicator in de header.
4. `useFilterableTable` MOET gebruikt worden met `initialFilters` voor alle filterbare kolommen.

### Requirement 4: FinanceModule — Framework Migratie

**User Story:** Als admin wil ik dat het financieel overzicht FilterableHeaders + een GenericFilter voor status gebruikt, consistent met de rest van de applicatie.

#### Acceptance Criteria

1. WANNEER de FinanceModule rendert, DAN MOETEN de tabel-kolommen (Naam, Datum, Kosten, Inkomsten, Winst) een `FilterableHeader` gebruiken.
2. DE status dropdown ("Alle statussen", "Open", "Betaald", "Achterstallig") MOET als `GenericFilter` in een `FilterPanel` boven de tabel staan.
3. DE bestaande custom `<Select>` met inconsistente styling MOET vervangen worden door de standaard GenericFilter component.
4. Sortering MOET toegevoegd worden op alle numerieke kolommen en de datum-kolom.

### Requirement 5: AdminOrderLockUnlock — Framework Migratie

**User Story:** Als admin wil ik dat de bestelling lock/unlock tabel het framework gebruikt voor consistente filtering en sortering.

#### Acceptance Criteria

1. WANNEER de AdminOrderLockUnlock rendert, DAN MOET de status filter als `GenericFilter` in een `FilterPanel` gerenderd worden.
2. ALS de tabel kolommen heeft, DAN MOETEN deze `FilterableHeader` gebruiken voor sortering.
3. DE bestaande custom `<Select>` styling MOET vervangen worden door de standaard GenericFilter component.

### Requirement 6: ProductManagementPage — Framework Migratie

**User Story:** Als admin wil ik dat de productenbeheerpagina het filter framework gebruikt voor de group/subgroup/event filters, zodat deze consistent zijn met andere tabellen.

#### Acceptance Criteria

1. DE groep/subgroep/event filters MOETEN als `GenericFilter` componenten in een `FilterPanel` gerenderd worden.
2. DE active/inactive toggle MAG als aparte control boven de FilterPanel blijven (is een boolean toggle, geen filter).
3. ALS de producten in een tabel staan, DAN MOETEN kolommen `FilterableHeader` gebruiken.
4. DE styling MOET consistent zijn met het h-dcn design system (orange.300 labels, gray.700 inputs).

### Requirement 7: OrdersAdmin — Framework Migratie

**User Story:** Als admin wil ik dat de bestellingen admin-pagina GenericFilter gebruikt voor de payment status filter, consistent met andere admin-pagina's.

#### Acceptance Criteria

1. DE payment status filter MOET als `GenericFilter` in een `FilterPanel` gerenderd worden.
2. DE bestaande server-side filtering logica MOET behouden blijven (filter value wordt doorgegeven aan de API hook).
3. DE `GenericFilter` MOET de h-dcn styling volgen (niet de myAdmin dark-on-dark styling).

### Requirement 8: Consistente Styling

**User Story:** Als gebruiker wil ik dat alle filters er hetzelfde uitzien in de hele applicatie.

#### Acceptance Criteria

1. ALLE `FilterableHeader` componenten MOETEN dezelfde styling gebruiken: `color="orange.300"` labels, `bg="gray.700"` filter inputs, `borderColor="gray.600"`, focus: `borderColor="orange.400"`.
2. ALLE `GenericFilter` componenten MOETEN dezelfde styling gebruiken: `bg="gray.700"`, `borderColor="gray.600"`, `color="white"`, focus: `borderColor="orange.400"`, options styled met dark achtergrond.
3. ALLE `FilterPanel` componenten MOETEN dezelfde container-styling gebruiken: `bg="gray.800"`, `borderRadius="md"`, `border="1px" borderColor="gray.600"`, padding 3.
4. Sort indicatoren MOETEN overal `TriangleUpIcon`/`TriangleDownIcon` in `orange.400` gebruiken.
5. De reset-knop in FilterPanel MOET `colorScheme="orange"` en `variant="ghost"` gebruiken.

### Requirement 9: Framework Opruimen

**User Story:** Als developer wil ik dat de bronbestanden uit de `Framework/` map verwijderd worden na succesvolle migratie, zodat er geen verwarring is over welke versie gebruikt moet worden.

#### Acceptance Criteria

1. NA succesvolle migratie van alle componenten MOET de `Framework/` map verwijderd worden.
2. DE framework documentatie (`Framework/filterframework.md`) MOET verplaatst worden naar `docs/development/filter-framework.md`.

## Samenvatting

| Prioriteit | Component             | Type Migratie                                            | Complexiteit |
| ---------- | --------------------- | -------------------------------------------------------- | ------------ |
| HIGH       | EventList             | FilterableHeader (alle kolommen) + remove search bar     | Medium       |
| HIGH       | MemberAdminTable      | FilterableHeader + FilterPanel + GenericFilter (hybride) | Hoog         |
| MEDIUM     | UserManagement        | FilterableHeader (alle kolommen) + remove search bar     | Laag         |
| MEDIUM     | FinanceModule         | FilterableHeader + FilterPanel (status dropdown)         | Laag         |
| MEDIUM     | AdminOrderLockUnlock  | FilterPanel (status dropdown)                            | Laag         |
| MEDIUM     | ProductManagementPage | FilterPanel (groep/subgroep/event dropdowns)             | Medium       |
| LOW        | OrdersAdmin           | GenericFilter (server-side, alleen UI swap)              | Laag         |
