# Implementation Plan: Filter Framework Migratie

## Overzicht

Migratie van 7 componenten naar het gestandaardiseerde Table Filter Framework. Volgorde: simpele tabellen eerst (leer-effect), dan complexere hybride tabellen, dan UI-only swaps.

## Tasks

- [x] 1. EventList migratie
  - [x] 1.1 Voeg `useFilterableTable` toe aan EventList
  - [x] 1.2 Vervang `<Th>` elementen door `<FilterableHeader>` componenten
  - [x] 1.3 Verwijder de losse zoekbalk en custom filter/sort code
  - [x] 1.4 Verificatie EventList

- [x] 2. UserManagement migratie
  - [x] 2.1 Voeg `useFilterableTable` toe aan UserManagement
  - [x] 2.2 Vervang `<Th>` door `<FilterableHeader>` + verwijder zoekbalk
  - [x] 2.3 Verificatie UserManagement

- [x] 3. FinanceModule migratie
  - [x] 3.1 Voeg `useFilterableTable` + `FilterPanel` + `GenericFilter` toe
  - [x] 3.2 Vervang custom `<Select>` door `GenericFilter` in `FilterPanel`
  - [x] 3.3 Vervang `<Th>` door `<FilterableHeader>` met sort
  - [x] 3.4 Verificatie FinanceModule

- [x] 4. Checkpoint — Simpele migraties

- [x] 5. MemberAdminTable migratie (meest complex)
  - [x] 5.1 Analyseer kolom-configuratie en bepaal filter-type per kolom
  - [x] 5.2 Voeg FilterPanel toe met GenericFilters voor select-kolommen
  - [x] 5.3 Voeg `useFilterableTable` toe voor text-kolommen
  - [x] 5.4 Vervang custom Th + renderColumnFilter() door FilterableHeaders
  - [x] 5.5 Verwijder custom filter/sort state en logica
  - [x] 5.6 Handle context switch (tableContext verandert → filters resetten)
  - [x] 5.7 Verificatie MemberAdminTable

- [x] 6. AdminOrderLockUnlock migratie
  - [x] 6.1 Vervang custom `<Select>` door `GenericFilter` in `FilterPanel`
  - [x] 6.2 Verificatie AdminOrderLockUnlock

- [x] 7. ProductManagementPage migratie
  - [x] 7.1 Vervang ProductFilter door `GenericFilter` componenten in `FilterPanel`
    - Replaced tree-style ProductFilter with two cascading GenericFilters (Groep → Subgroep)
    - Subgroep options dynamically filter based on selected Groep
    - Active/inactive toggle stays as separate Switch
  - [x] 7.2 Verificatie ProductManagementPage

- [x] 8. OrdersAdmin migratie
  - [x] 8.1 Vervang custom `<Select>` door `GenericFilter` in `FilterPanel`
  - [x] 8.2 Verificatie OrdersAdmin

- [x] 9. Checkpoint — Alle migraties

- [x] 10. Opruimen
  - [x] 10.1 Verwijder `Framework/` map
  - [ ] 10.2 Verwijder ongebruikte oude filter componenten/code
  - [ ] 10.3 Update testFindings.md

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
