# Requirements Document

## Introduction

The H-DCN portal contains a partially-implemented UI framework for table filtering and sorting in `frontend/src/components/filters/` and `frontend/src/hooks/`. A more complete, production-ready version already exists in `filter-table-framework/`. This spec consolidates the two: adopting the complete framework into H-DCN, adding the missing `GenericMultiFilter` component, and migrating all non-compliant code in H-DCN to use the consolidated framework.

The work is split into two parts:

- **Part 1 — Framework consolidation**: Replace the partial H-DCN framework with the complete framework from `filter-table-framework/`, add `GenericMultiFilter`, update the barrel export, and ensure full i18n compliance.
- **Part 2 — Codebase migration**: Migrate 8 tables with inline action buttons to the row-click → modal pattern, and migrate 4 ad-hoc filter implementations to use `FilterPanel` + `GenericFilter` / `GenericMultiFilter`.

## Glossary

- **Framework**: The table filter framework consisting of hooks (`useColumnFilters`, `useTableSort`, `useFilterableTable`) and components (`FilterableHeader`, `FilterPanel`, `GenericFilter`, `GenericMultiFilter`) located in `frontend/src/components/filters/` and `frontend/src/hooks/`.
- **Filter_Component**: Any of `GenericFilter`, `GenericMultiFilter`, `FilterPanel`, `FilterableHeader`.
- **Table_Component**: A React component that renders a Chakra UI `<Table>` displaying data rows.
- **Row_Click_Pattern**: The interaction model where clicking a table row opens a Chakra UI `<Modal>` for all detail, edit, and delete operations — with no action buttons in the row cells.
- **GenericMultiFilter**: A checkbox-based multi-select dropdown filter component (not yet implemented in H-DCN). Its trigger button displays the selected option labels joined by ", " when 1–2 items are selected, or "N geselecteerd" when 3 or more are selected.
- **FilterPanel**: A config-driven container component that accepts an array of `FilterConfig<T>` objects and renders filters in horizontal, vertical, or grid layout.
- **FilterableHeader**: A `<Th>` component with a column label, optional sort indicator, and optional inline text-filter input.
- **useColumnFilters**: Hook that manages per-column text filter state with 150 ms debounce and case-insensitive substring matching.
- **useTableSort**: Hook that manages sort state (field + direction) with toggle and `getSortIndicator`.
- **useFilterableTable**: Composed hook that combines `useColumnFilters` + `useTableSort`, returning `processedData` (filtered then sorted).
- **Barrel_Export**: The file `frontend/src/components/filters/index.ts` that re-exports all framework components and types.
- **i18n**: Internationalisation via `react-i18next`. All user-facing strings must use `useTranslation()` with keys defined in all 8 locale files (nl, en, de, fr, es, it, da, sv). Locale files live in both `frontend/src/locales/{lang}/` and `frontend/public/locales/{lang}/`.
- **Ad-hoc_Filter**: A custom `<Select>` or inline dropdown implementation that does not use the Framework components.

---

## Requirements

### Requirement 1: Adopt Complete Framework Hooks

**User Story:** As a developer, I want the H-DCN hooks (`useColumnFilters`, `useTableSort`, `useFilterableTable`) to match the complete implementation from `filter-table-framework/`, so that all tables in the portal use the same, tested hook API.

#### Acceptance Criteria

1. THE Framework SHALL replace the existing `frontend/src/hooks/useColumnFilters.ts` with the implementation from `filter-table-framework/frontend/src/hooks/useColumnFilters.ts`, which takes `(data: T[], initialFilters: Record<string, string>, options?: UseColumnFiltersOptions)` as arguments and returns `{ filters, setFilter, resetFilters, filteredData, hasActiveFilters }`.
2. THE Framework SHALL replace the existing `frontend/src/hooks/useTableSort.ts` with the implementation from `filter-table-framework/frontend/src/hooks/useTableSort.ts`, which adds a `getSortIndicator(field: string): string` method returning `'↑'`, `'↓'`, or `''`.
3. THE Framework SHALL replace the existing `frontend/src/hooks/useFilterableTable.ts` with the implementation from `filter-table-framework/frontend/src/hooks/useFilterableTable.ts`, which takes `(data: T[], config: UseFilterableTableConfig)` and returns `processedData` as sorted output of filtered data.
4. WHEN any existing table component uses the previous hook API (e.g., `filterData(data)` callback, `sortData(data)` callback), THE Framework SHALL update those call sites to the new API — even if the old implementations remain compatible — so that `npx tsc --noEmit` reports zero errors from any source, resulting in a completely clean build.
5. THE Framework SHALL export all hook types (`UseColumnFiltersOptions`, `SortDirection`, `SortConfig`, `UseFilterableTableReturn`) from the hooks directory so that consuming components can import them without reaching into implementation files.

---

### Requirement 2: Adopt Complete FilterableHeader Component

**User Story:** As a developer, I want `FilterableHeader` in H-DCN to match the complete implementation from `filter-table-framework/`, so that column headers consistently show a search icon, support aria-sort, and accept `w`/`maxW` width constraints.

#### Acceptance Criteria

1. THE Framework SHALL replace `frontend/src/components/filters/FilterableHeader.tsx` with the implementation from `filter-table-framework/frontend/src/components/filters/FilterableHeader.tsx`.
2. WHEN `filterValue` is provided as a prop, THE FilterableHeader SHALL render an `<InputGroup>` with a `<SearchIcon>` in an `<InputLeftElement>` and an `<Input>` bound to `filterValue`.
3. WHEN `sortable` is `true` and `sortDirection` is non-null, THE FilterableHeader SHALL render the sort direction as a Unicode arrow (`↑` or `↓`) in `orange.300`.
4. THE FilterableHeader SHALL derive `aria-sort` on the `<Th>` element from the `sortDirection` prop state, setting it to `"ascending"`, `"descending"`, or `"none"` when `sortable` is `true`.
5. THE FilterableHeader SHALL accept optional `w` and `maxW` props for Chakra UI column width constraints.
6. WHEN `onFilterChange` fires, THE FilterableHeader SHALL call the provided callback with the new input string.

---

### Requirement 3: Adopt Complete FilterPanel Component

**User Story:** As a developer, I want `FilterPanel` in H-DCN to match the config-driven implementation from `filter-table-framework/`, so that multiple filters can be declared as a `FilterConfig<T>[]` array with layout control instead of passing child nodes.

#### Acceptance Criteria

1. THE Framework SHALL replace `frontend/src/components/filters/FilterPanel.tsx` with the implementation from `filter-table-framework/frontend/src/components/filters/FilterPanel.tsx`.
2. THE FilterPanel SHALL accept a `filters` prop of type `(FilterConfig<any> | SearchFilterConfig)[]` and render one filter control per array element.
3. THE FilterPanel SHALL support `layout` prop values of `'horizontal'` (default), `'vertical'`, and `'grid'`, rendering `<HStack>`, `<VStack>`, or `<SimpleGrid>` respectively.
4. WHEN `filter.type` is `'search'`, THE FilterPanel SHALL render a labelled `<Input>` instead of a dropdown.
5. WHEN `filter.type` is `'single'`, THE FilterPanel SHALL render a `GenericFilter` in single-select mode.
6. WHEN `filter.type` is `'multi'`, THE FilterPanel SHALL render a `GenericMultiFilter` in multi-select mode.
7. WHEN existing components use the old `FilterPanel` child-node API (`<FilterPanel hasActiveFilters={...} onReset={...}><GenericFilter .../></FilterPanel>`), THE Framework SHALL update those call sites to use the new config-driven API.

---

### Requirement 4: Adopt Complete Type Definitions

**User Story:** As a developer, I want a single `types.ts` file with all filter and sort type definitions, so that all components and hooks import from one canonical location.

#### Acceptance Criteria

1. THE Framework SHALL create `frontend/src/components/filters/types.ts` containing all types from `filter-table-framework/frontend/src/components/filters/types.ts`, including: `FilterType`, `FilterConfig<T>`, `SingleSelectFilterConfig<T>`, `MultiSelectFilterConfig<T>`, `SearchFilterConfig`, `FilterPanelLayout`, `ColumnFilterState`, `SortDirection`, `SortConfig`, `FilterableHeaderProps`, and `UseColumnFiltersOptions`.
2. THE Framework SHALL create `types.ts` BEFORE updating any components to import from it, to avoid import errors during development.
3. THE Framework SHALL update `FilterableHeader`, `FilterPanel`, `GenericFilter`, and `GenericMultiFilter` to import their type dependencies from `./types` instead of defining them inline.
4. THE Framework SHALL update `useColumnFilters`, `useTableSort`, and `useFilterableTable` to import `SortDirection`, `SortConfig`, and `UseColumnFiltersOptions` from `../components/filters/types` instead of defining them locally.
5. WHEN `npx tsc --noEmit` is run after all changes, THE Framework SHALL produce zero TypeScript errors.

---

### Requirement 5: Add GenericMultiFilter Component

**User Story:** As a developer, I want a `GenericMultiFilter` component so that pages needing multi-select dropdowns (e.g., event type filter on the calendar) can use the Framework instead of custom ad-hoc implementations.

#### Acceptance Criteria

1. THE Framework SHALL create `frontend/src/components/filters/GenericMultiFilter.tsx` implementing a checkbox-based multi-select dropdown using Chakra UI `<Menu>`, `<MenuButton>`, `<MenuList>`, and `<MenuItemOption>` (or equivalent Chakra pattern).
2. THE GenericMultiFilter SHALL accept props: `label: string`, `value: string[]`, `options: FilterOption[]`, `onChange: (values: string[]) => void`, and optional `placeholder?: string`, `isDisabled?: boolean`, `width?: string`.
3. WHEN 0 options are selected, THE GenericMultiFilter trigger button SHALL display the `placeholder` text (default: `'Alle'`).
4. WHEN 1 or more options are selected, THE GenericMultiFilter trigger button SHALL display `'N geselecteerd'` where N is the count of selected items — placeholder is shown only when exactly 0 items are selected.
5. WHEN the dropdown is open, THE GenericMultiFilter SHALL visually mark each selected option with a checkmark or highlighted background inside the list — no selected labels are shown outside the dropdown.
6. WHEN the user checks or unchecks a checkbox in the dropdown, THE GenericMultiFilter SHALL call `onChange` with the updated `string[]` of selected values immediately.
7. THE GenericMultiFilter SHALL use `useTranslation` to resolve the `'N geselecteerd'` summary string with a translation key so that it renders correctly in all 8 supported locales.
8. THE GenericMultiFilter trigger button SHALL NOT render tag/chip buttons below the dropdown — selected items are summarised in the trigger label only.
9. THE GenericMultiFilter SHALL render a `<FormLabel>` above the trigger button, styled consistently with `GenericFilter` (orange.300, xs font).
10. THE GenericMultiFilter trigger button SHALL have an `aria-label` reflecting the current selection for screen-reader accessibility.

---

### Requirement 6: Update Barrel Export

**User Story:** As a developer, I want `frontend/src/components/filters/index.ts` to export all framework components and types, so that any component can import the entire framework from one path.

#### Acceptance Criteria

1. THE Barrel_Export SHALL export `FilterableHeader` and its props type `FilterableHeaderProps`.
2. THE Barrel_Export SHALL export `FilterPanel` and its props types `FilterPanelProps` and `FilterPanelLayout`.
3. THE Barrel_Export SHALL export `GenericFilter` and its types `GenericFilterProps`, `FilterOption`, `FilterOptionGroup`.
4. THE Barrel_Export SHALL export `GenericMultiFilter` and its props type `GenericMultiFilterProps`.
5. THE Barrel_Export SHALL export `YearFilter` and its props type `YearFilterProps`.
6. THE Barrel_Export SHALL export all shared types from `./types`: `FilterConfig`, `SingleSelectFilterConfig`, `MultiSelectFilterConfig`, `SearchFilterConfig`, `SortDirection`, `SortConfig`, `ColumnFilterState`, `FilterableHeaderProps`, `UseColumnFiltersOptions`.
7. WHEN any component imports from `'../../components/filters'`, THE Barrel_Export SHALL ensure the import resolves successfully without TypeScript errors.

---

### Requirement 7: Migrate Tables with Inline Action Buttons — Members Module

**User Story:** As an H-DCN member-management administrator, I want all member, group, and membership tables to open modals on row click instead of showing per-row action buttons, so that rows are clean and consistent with the rest of the portal.

#### Acceptance Criteria

1. WHEN a user clicks any data row in `UserManagement.tsx`, THE Table_Component SHALL atomically open the existing edit/detail modal for that user and remove the current per-row Edit, Add-to-Group menu, Enable/Disable, and Delete buttons.
2. WHEN a user clicks any data row in `GroupManagement.tsx`, THE Table_Component SHALL atomically open the existing detail/edit modal for that group and remove the current per-row View, Edit, and Delete buttons — this row-click modal behaviour is specific to the GroupManagement table.
3. WHEN a user clicks any data row in `MembershipTable.tsx`, THE Table_Component SHALL open the existing edit modal for that membership record only when the user is viewing the MembershipTable component, replacing the current per-row Edit and Delete buttons.
4. THE Table_Component SHALL apply `_hover={{ bg: 'gray.700', cursor: 'pointer' }}` to each `<Tr>` that triggers a modal.
5. WHEN delete or destructive actions previously had dedicated row buttons, THE Table_Component SHALL expose those actions inside the opened modal (e.g., a Delete button in the modal footer).
6. THE Table_Component SHALL preserve all existing API calls, data fields displayed, and modal functionality — only the trigger mechanism changes from per-row buttons to row click.

---

### Requirement 8: Migrate Tables with Inline Action Buttons — Webshop Module

**User Story:** As a webshop administrator, I want the variant sub-table and order-lock table to follow the row-click → modal pattern, so that all admin tables are visually consistent.

#### Acceptance Criteria

1. WHEN a user clicks any data row in `VariantSubTable.tsx`, THE Table_Component SHALL open an existing or new variant detail/edit modal, immediately hiding inline buttons and replacing the current per-row Add-stock, Deactivate, and Delete buttons.
2. WHEN a user clicks any data row in `AdminOrderLockUnlock.tsx`, THE Table_Component SHALL expose the Unlock action inside a modal, immediately hiding the current per-row Unlock button.
3. WHERE `AdminOrderLockUnlock.tsx` has a checkbox column for bulk operations that are actually implemented, THE Table_Component SHALL retain the checkbox column — checkboxes are the permitted exception to the no-per-row-buttons rule.
4. THE Table_Component SHALL preserve all existing API calls and business logic for stock addition, deactivation, deletion, and order unlocking.

---

### Requirement 9: Migrate Tables with Inline Action Buttons — Event Booking Module

**User Story:** As an event-booking administrator, I want claims management and event access tables to follow the row-click → modal pattern, so that rows are clean.

#### Acceptance Criteria

1. WHEN a user clicks any data row in `AdminClaimsManagement.tsx`, THE Table_Component SHALL open a claim detail/action modal, replacing the current per-row Menu and Assign button.
2. WHEN a user clicks any data row in `EventAccessManager.tsx`, THE Table_Component SHALL open an access detail modal containing the Revoke action, replacing the current per-row Revoke button.
3. WHERE `EventAccessManager.tsx` already has checkboxes for bulk operations, THE Table_Component SHALL retain the checkbox column.
4. THE Table_Component SHALL preserve existing claim assignment and access revocation API calls. IF preserving those API calls fails during migration, THE Table_Component SHALL halt the migration and retain the current inline buttons until the API calls can be successfully preserved.

---

### Requirement 10: MyOrders Download Button Exception

**User Story:** As a product owner, I want to decide whether the PDF download button in `MyOrders.tsx` must be moved into a modal, because download is a utility action distinct from CRUD.

#### Acceptance Criteria

1. THE Table_Component in `MyOrders.tsx` SHALL retain the per-row PDF download `<IconButton>` as a permitted exception to the row-click → modal rule, because downloading an order confirmation is a stateless utility action that does not open, edit, or delete any record.
2. WHEN a user clicks the PDF download button, THE Table_Component SHALL NOT navigate away or open a modal — the download SHALL trigger directly.
3. WHEN a user clicks any other part of the row (outside the download button), THE Table_Component SHALL open an order detail modal showing the order items, amounts, status, and tracking information. IF the modal fails to open due to a technical error or missing data, THE Table_Component SHALL display an error message or fallback behaviour.
4. THE Table_Component SHALL visually differentiate the clickable download button from the rest of the row using `stopPropagation` so that clicking the button does not simultaneously open the modal.

---

### Requirement 11: Migrate Ad-hoc Filters in EventCalendarPage

**User Story:** As a developer, I want `EventCalendarPage.tsx` to use `GenericMultiFilter` for event type and `GenericFilter` for region so that custom `<Select>` and tag-button implementations are eliminated.

#### Acceptance Criteria

1. THE Table_Component SHALL replace the custom `<Select>` + `<HStack>` tag-button implementation for event type filtering with a `<GenericMultiFilter>` bound to `filterTypes: string[]`.
2. THE Table_Component SHALL replace the custom inline `<Select>` for region filtering with a `<GenericFilter>` bound to `filterRegio: string`.
3. WHEN the user selects or deselects event types in the `GenericMultiFilter`, THE Table_Component SHALL filter `filteredEvents` using the same AND-exclusion logic currently in the `useMemo` (i.e., events whose `event_type` is not in the selected array are excluded).
4. THE Table_Component SHALL wrap both filters and the date range inputs in a `<FilterPanel layout="horizontal">`.
5. THE Table_Component SHALL preserve the existing date-from and date-to `<Input>` fields and the reset button.
6. THE Table_Component SHALL preserve all existing translation keys and i18n calls.

---

### Requirement 12: Migrate Ad-hoc Filters in ReportsTab

**User Story:** As a developer, I want `ReportsTab.tsx` to use `FilterPanel` + `GenericFilter` for its three filter dropdowns so that ad-hoc `<Select>` components are eliminated.

#### Acceptance Criteria

1. THE Table_Component SHALL replace the three custom `<Select>` elements (report type, order status, payment status) with `<GenericFilter>` components wrapped in a `<FilterPanel layout="horizontal">`.
2. THE GenericFilter for report type SHALL use the existing `REPORT_TYPE_LABELS` entries as `FilterOption[]`.
3. THE GenericFilter for order status SHALL use the existing `ORDER_STATUS_OPTIONS` entries as `FilterOption[]`.
4. THE GenericFilter for payment status SHALL use the existing `PAYMENT_STATUS_OPTIONS` entries as `FilterOption[]`.
5. THE Table_Component SHALL preserve all existing `setReportType`, `setOrderStatus`, and `setPaymentStatus` state callbacks so that `useAdminReports` continues to receive the same filter values.
6. THE Table_Component SHALL preserve the Refresh and Export action bar below the filter panel.

---

### Requirement 13: Migrate Ad-hoc Filters in EventAdminPage

**User Story:** As a developer, I want `EventAdminPage.tsx` to use `GenericFilter` for its event-picker dropdown so that the custom `<Select>` is eliminated.

#### Acceptance Criteria

1. THE Table_Component SHALL replace the custom event-picker `<Select>` in `EventAdminPage.tsx` with a `<GenericFilter>` component.
2. THE GenericFilter SHALL be populated with the same event options currently used by the custom `<Select>`.
3. THE Table_Component SHALL preserve the existing `onChange` handler and selected event state.
4. WHEN no event is selected, THE GenericFilter SHALL display a placeholder consistent with existing behaviour.

---

### Requirement 14: Preserve Behaviour During Migration

**User Story:** As a developer, I want every migrated component to preserve its existing data, modal, and API behaviour exactly, so that no regressions are introduced during the consolidation.

#### Acceptance Criteria

1. THE Table_Component SHALL make the same API calls after migration as before migration — no endpoints, parameters, or payloads SHALL change.
2. THE Table_Component SHALL display the same data columns after migration as before migration — no columns SHALL be added or removed unless explicitly required by this spec.
3. WHEN a modal was previously opened by a per-row button, THE Table_Component SHALL open the same modal with the same data when the user clicks the row.
4. THE Table_Component SHALL pass the same props to all existing modals as before migration.
5. IF a migration introduces a TypeScript error, THE Table_Component SHALL resolve it before the task is marked complete.
6. AFTER migration, `npx tsc --noEmit` SHALL report zero new errors compared to the pre-migration baseline.

---

### Requirement 15: i18n Compliance for All New and Modified Components

**User Story:** As an internationalisation maintainer, I want every new and modified user-facing string to use `useTranslation()` with a translation key defined in all 8 locale files, so that the portal stays fully translatable.

#### Acceptance Criteria

1. THE GenericMultiFilter SHALL use `useTranslation` to resolve the `'N geselecteerd'` (N selected) summary string.
2. THE GenericMultiFilter SHALL add the translation key for `'N geselecteerd'` to the `common` namespace in all 8 locale files: `nl`, `en`, `de`, `fr`, `es`, `it`, `da`, `sv` — updating both `src/locales/` and `public/locales/`.
3. WHEN any migrated component introduces a new user-facing string (e.g., modal title, button label, empty state), THE Table_Component SHALL add that string as a translation key to the appropriate namespace in all 8 locale files.
4. THE Table_Component SHALL NOT hardcode Dutch strings — every user-facing string SHALL go through `t('key')`. WHEN migrating a component, THE Table_Component SHALL also remove any existing hardcoded Dutch strings found in the same component.
5. WHERE an existing component already uses `t('key')` for a string that previously appeared on a per-row button, or WHERE an existing translation key covers the same text, THE Table_Component SHALL reuse that existing translation key to avoid duplication.
