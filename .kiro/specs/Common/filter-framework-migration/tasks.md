# Implementation Plan: Filter Framework Migratie

## Overzicht

Migratie van 7 componenten naar het gestandaardiseerde Table Filter Framework. Volgorde: simpele tabellen eerst (leer-effect), dan complexere hybride tabellen, dan UI-only swaps.

## Tasks

- [ ] 1. EventList migratie
  - [ ] 1.1 Voeg `useFilterableTable` toe aan EventList
    - Import `useFilterableTable` en `FilterableHeader` uit framework
    - Definieer `INITIAL_FILTERS` met keys: `name`, `start_date`, `location`, `linked_regio`, `participants`, `cost`, `revenue`
    - Permission-filtering behouden als pre-filter (useMemo vóór useFilterableTable)
    - Default sort: `{ field: 'start_date', direction: 'desc' }`
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [ ] 1.2 Vervang `<Th>` elementen door `<FilterableHeader>` componenten
    - Elke kolom krijgt: label, filterValue, onFilterChange, sortable, sortDirection, onSort
    - Responsive display props behouden (`display={{ base: 'none', md: 'table-cell' }}`)
    - _Requirements: 1.1, 1.6_

  - [ ] 1.3 Verwijder de losse zoekbalk en custom filter/sort code
    - Verwijder `useState('') searchTerm`
    - Verwijder de `filteredEvents` useMemo met inline .filter() + .sort()
    - Verwijder `<SearchIcon>` + `<Input>` zoekbalk UI
    - Vervang door `processedData` uit useFilterableTable
    - _Requirements: 1.5_

  - [ ] 1.4 Verificatie EventList
    - `npx tsc --noEmit` (type check)
    - `npx eslint src/modules/events/components/EventList.tsx`
    - Visueel: component rendert, filters werken, sort werkt
    - _Requirements: 1.1–1.6_

- [ ] 2. UserManagement migratie
  - [ ] 2.1 Voeg `useFilterableTable` toe aan UserManagement
    - Import framework hooks/components
    - Definieer `INITIAL_FILTERS`: `email`, `username`, `status`, `created`
    - Default sort: `{ field: 'email', direction: 'asc' }`
    - Transform `users` data naar flat objects voor het framework (extract email/username uit Attributes array)
    - _Requirements: 3.1, 3.4_

  - [ ] 2.2 Vervang `<Th>` door `<FilterableHeader>` + verwijder zoekbalk
    - Kolommen: Email, Username, Status, Aangemaakt
    - Verwijder `useState('') searchTerm` en custom `.filter()` + `.sort()`
    - Verwijder zoekbalk UI
    - _Requirements: 3.1, 3.2, 3.3_

  - [ ] 2.3 Verificatie UserManagement
    - `npx tsc --noEmit`
    - `npx eslint src/modules/members/components/UserManagement.tsx`
    - _Requirements: 3.1–3.4_

- [ ] 3. FinanceModule migratie
  - [ ] 3.1 Voeg `useFilterableTable` + `FilterPanel` + `GenericFilter` toe
    - Import framework componenten
    - Definieer `INITIAL_FILTERS`: `naam`, `datum_van`, `kosten`, `inkomsten`, `winst`
    - Status dropdown als pre-filter (useMemo) OF als GenericFilter in FilterPanel
    - Default sort: `{ field: 'datum_van', direction: 'desc' }`
    - _Requirements: 4.1, 4.2, 4.4_

  - [ ] 3.2 Vervang custom `<Select>` door `GenericFilter` in `FilterPanel`
    - Status opties: Alle, Open, Betaald, Achterstallig
    - Verwijder custom `<Select>` met inconsistente styling
    - _Requirements: 4.2, 4.3_

  - [ ] 3.3 Vervang `<Th>` door `<FilterableHeader>` met sort
    - Kolommen: Naam, Datum, Kosten, Inkomsten, Winst
    - _Requirements: 4.1, 4.4_

  - [ ] 3.4 Verificatie FinanceModule
    - `npx tsc --noEmit`
    - `npx eslint src/modules/events/components/FinanceModule.tsx`
    - _Requirements: 4.1–4.4_

- [ ] 4. Checkpoint — Simpele migraties
  - Type check hele frontend: `npx tsc --noEmit`
  - Lint gemigreerde bestanden
  - Vraag gebruiker om visuele verificatie indien nodig

- [ ] 5. MemberAdminTable migratie (meest complex)
  - [ ] 5.1 Analyseer kolom-configuratie en bepaal filter-type per kolom
    - Text-kolommen (filterType: 'text'/'number') → FilterableHeader
    - Select-kolommen (filterType: 'select') → GenericFilter in FilterPanel
    - Date-kolommen (filterType: 'date') → FilterableHeader (text filter op datum-string)
    - Map huidige `renderColumnFilter()` logica naar framework componenten
    - _Requirements: 2.1, 2.2_

  - [ ] 5.2 Voeg FilterPanel toe met GenericFilters voor select-kolommen
    - Genereer options dynamisch uit `getFilterOptions()` (bestaande functie behouden)
    - Select kolommen: lid_status, regio, lidmaatschap_type (afhankelijk van context)
    - FilterPanel toont Reset knop + resultaat teller
    - _Requirements: 2.2, 2.6, 2.8_

  - [ ] 5.3 Voeg `useFilterableTable` toe voor text-kolommen
    - INITIAL_FILTERS dynamisch opbouwen op basis van actieve tableContext kolommen
    - Dropdown pre-filters (status, regio) als useMemo vóór useFilterableTable
    - Regional permission filtering behouden als eerste pre-filter
    - _Requirements: 2.3, 2.4, 2.7_

  - [ ] 5.4 Vervang custom Th + renderColumnFilter() door FilterableHeaders
    - Alleen voor text/number kolommen
    - Select-kolommen krijgen gewone Th (zonder filter — die zit in FilterPanel)
    - Sort op alle kolommen behouden (useFilterableTable handleSort)
    - _Requirements: 2.1, 2.5_

  - [ ] 5.5 Verwijder custom filter/sort state en logica
    - Verwijder: `useState sortField`, `useState sortDirection`, `useState columnFilters`
    - Verwijder: `handleSort`, `handleColumnFilter`, `renderColumnFilter`
    - Verwijder: custom `.filter()` + `.sort()` in `filteredMembers` useMemo
    - Behoud: `computeCalculatedFieldsForArray`, regional filtering, context switching
    - _Requirements: 2.3_

  - [ ] 5.6 Handle context switch (tableContext verandert → filters resetten)
    - Bij context switch (`selectedContext` wijzigt): `resetFilters()` aanroepen
    - INITIAL_FILTERS opnieuw berekenen op basis van nieuwe context kolommen
    - _Requirements: 2.7_

  - [ ] 5.7 Verificatie MemberAdminTable
    - `npx tsc --noEmit`
    - `npx eslint src/components/MemberAdminTable.tsx`
    - Controleer: alle contexts werken, filters resetten bij switch, sort werkt per type
    - _Requirements: 2.1–2.8_

- [ ] 6. AdminOrderLockUnlock migratie
  - [ ] 6.1 Vervang custom `<Select>` door `GenericFilter` in `FilterPanel`
    - Status opties: all, submitted, locked
    - Behoud de filteredOrders logica (simpele .filter())
    - Voeg FilterPanel container toe met juiste styling
    - _Requirements: 5.1, 5.2, 5.3_

  - [ ] 6.2 Verificatie AdminOrderLockUnlock
    - `npx tsc --noEmit`
    - `npx eslint src/modules/eventBooking/admin/AdminOrderLockUnlock.tsx`
    - _Requirements: 5.1–5.3_

- [ ] 7. ProductManagementPage migratie
  - [ ] 7.1 Vervang ProductFilter door `GenericFilter` componenten in `FilterPanel`
    - GenericFilter voor: groep, subgroep, event-koppeling
    - Active/inactive toggle blijft als aparte Switch/Button
    - FilterPanel styling volgt h-dcn design system
    - _Requirements: 6.1, 6.2, 6.4_

  - [ ] 7.2 Verificatie ProductManagementPage
    - `npx tsc --noEmit`
    - `npx eslint src/modules/products/ProductManagementPage.tsx`
    - _Requirements: 6.1–6.4_

- [ ] 8. OrdersAdmin migratie
  - [ ] 8.1 Vervang custom `<Select>` door `GenericFilter` in `FilterPanel`
    - Behoud server-side filtering (value gaat naar useAdminOrders hook)
    - Alleen UI component swap — geen logica wijziging
    - _Requirements: 7.1, 7.2, 7.3_

  - [ ] 8.2 Verificatie OrdersAdmin
    - `npx tsc --noEmit`
    - `npx eslint src/modules/webshop/components/OrdersAdmin.tsx`
    - _Requirements: 7.1–7.3_

- [ ] 9. Checkpoint — Alle migraties
  - Full type check: `npx tsc --noEmit`
  - Lint alle gemigreerde bestanden
  - Controleer dat geen unused imports overblijven

- [ ] 10. Opruimen
  - [ ] 10.1 Verwijder `Framework/` map
    - Verplaats `Framework/filterframework.md` naar `docs/development/filter-framework.md`
    - Verwijder alle andere bestanden in `Framework/`
    - _Requirements: 9.1, 9.2_

  - [ ] 10.2 Verwijder ongebruikte oude filter componenten/code
    - Check of `MemberFilters.tsx` nog ergens geïmporteerd wordt — zo niet, verwijder
    - Check of `ProductFilter` component nog nodig is — zo niet, verwijder
    - Grep op verwijderde symbols in hele codebase
    - _Requirements: 9.1_

  - [ ] 10.3 Update testFindings.md
    - Markeer "Inconsistent dropdown behaviour" als opgelost
    - _Requirements: 8.1–8.5_

- [ ] 11. Finale verificatie
  - `npx tsc --noEmit` (volledige frontend type check)
  - Lint alle gewijzigde bestanden
  - Geen unused imports (ESLint no-unused-vars)
  - Commit op huidige feature branch

## Notes

- MemberAdminTable (task 5) is de meest complexe migratie vanwege dynamische kolom-configuratie
- EventList en UserManagement zijn de simpelste — goed om mee te beginnen voor het leer-effect
- ProductManagementPage gebruikt een card-grid, geen tabel — alleen FilterPanel is relevant
- OrdersAdmin is server-side filtering — alleen de UI component wordt vervangen
- Permission-filtering moet ALTIJD als pre-filter vóór het framework plaatsvinden (security)
- Bij context switch in MemberAdminTable moeten filters gereset worden

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3"] },
    { "id": 1, "tasks": ["1.4", "2.1", "2.2"] },
    { "id": 2, "tasks": ["2.3", "3.1", "3.2", "3.3"] },
    { "id": 3, "tasks": ["3.4"] },
    { "id": 4, "tasks": ["5.1"] },
    { "id": 5, "tasks": ["5.2", "5.3", "5.4", "5.5"] },
    { "id": 6, "tasks": ["5.6", "5.7"] },
    { "id": 7, "tasks": ["6.1", "7.1", "8.1"] },
    { "id": 8, "tasks": ["6.2", "7.2", "8.2"] },
    { "id": 9, "tasks": ["10.1", "10.2", "10.3"] }
  ]
}
```
