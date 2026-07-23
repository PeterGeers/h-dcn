# Implementation Plan: UI Framework Consolidation

## Overview

This plan consolidates the partial filter/sort framework in H-DCN with the complete implementation from `filter-table-framework/`, adds a `GenericMultiFilter` component, migrates 8 tables to the row-click→modal pattern, and migrates 4 pages from ad-hoc filters to framework components. Work is structured in layers: types first, then hooks, then components, then migrations (tables → filters).

## Tasks

- [x] 1. Create canonical types and replace framework hooks
  - [x] 1.1 Create `frontend/src/components/filters/types.ts` with all shared type definitions
    - Copy types from `filter-table-framework/frontend/src/components/filters/types.ts`
    - Include: `FilterType`, `FilterConfig<T>`, `SingleSelectFilterConfig<T>`, `MultiSelectFilterConfig<T>`, `SearchFilterConfig`, `FilterPanelLayout`, `ColumnFilterState`, `SortDirection`, `SortConfig`, `FilterableHeaderProps`, `GenericMultiFilterProps`, `FilterOption`, `FilterOptionGroup`, `UseColumnFiltersOptions`
    - _Requirements: 4.1, 4.2_

  - [x] 1.2 Replace `frontend/src/hooks/useColumnFilters.ts` with framework implementation
    - Copy from `filter-table-framework/frontend/src/hooks/useColumnFilters.ts`
    - Update imports to reference `../components/filters/types` for `UseColumnFiltersOptions`, `ColumnFilterState`
    - Verify data-first signature: `(data: T[], initialFilters: Record<string, string>, options?: UseColumnFiltersOptions)`
    - _Requirements: 1.1, 4.4_

  - [x] 1.3 Replace `frontend/src/hooks/useTableSort.ts` with framework implementation
    - Copy from `filter-table-framework/frontend/src/hooks/useTableSort.ts`
    - Update imports to reference `../components/filters/types` for `SortDirection`, `SortConfig`
    - Verify exports: `sortedData`, `handleSort`, `getSortIndicator`, `compareValues`, `isISODateString`
    - _Requirements: 1.2, 4.4_

  - [x] 1.4 Replace `frontend/src/hooks/useFilterableTable.ts` with framework implementation
    - Copy from `filter-table-framework/frontend/src/hooks/useFilterableTable.ts`
    - Update imports to reference `../components/filters/types`
    - Verify data-first signature: `(data: T[], config: UseFilterableTableConfig)`
    - Verify returns: `processedData`, `getSortIndicator`, `filters`, `setFilter`, `handleSort`, etc.
    - _Requirements: 1.3, 4.4_

  - [x] 1.5 Replace hook test files from framework
    - Copy `useColumnFilters.test.ts` and `useColumnFilters.property.test.ts` into `frontend/src/hooks/__tests__/`
    - Copy `useFilterableTable.test.ts` and `useFilterableTable.property.test.ts` into `frontend/src/hooks/__tests__/`
    - Adjust import paths as needed
    - _Requirements: 1.1, 1.3_

  - [x] 1.6 Write unit tests for `useTableSort`
    - Create `frontend/src/hooks/__tests__/useTableSort.test.ts`
    - Test: `getSortIndicator` returns correct arrows, `handleSort` toggle behavior, null-to-end sorting, `compareValues` utility, ISO date detection
    - _Requirements: 1.2_

  - [x] 1.7 Write property test for `useTableSort`
    - Create `frontend/src/hooks/__tests__/useTableSort.property.test.ts`
    - Test sort stability and null-handling across random data
    - _Requirements: 1.2_

- [x] 2. Replace framework components and add GenericMultiFilter
  - [x] 2.1 Replace `frontend/src/components/filters/FilterableHeader.tsx` with framework implementation
    - Copy from `filter-table-framework/frontend/src/components/filters/FilterableHeader.tsx`
    - Update imports to use `./types` for `FilterableHeaderProps`
    - Verify: `SearchIcon` in `InputLeftElement`, Unicode sort arrows in `orange.300`, `aria-sort` on `<Th>`, `w`/`maxW` props
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 4.3_

  - [x] 2.2 Replace `frontend/src/components/filters/FilterPanel.tsx` with framework config-driven implementation
    - Copy from `filter-table-framework/frontend/src/components/filters/FilterPanel.tsx`
    - Update imports to use `./types` for `FilterConfig`, `FilterPanelLayout`, `SearchFilterConfig`
    - Verify: accepts `filters` prop array, supports `layout` prop (`horizontal`/`vertical`/`grid`), renders correct control per `type`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 4.3_

  - [x] 2.3 Create `frontend/src/components/filters/GenericMultiFilter.tsx`
    - Implement checkbox multi-select dropdown using Chakra UI `<Menu>`, `<MenuButton>`, `<MenuList>`, `<MenuOptionGroup type="checkbox">`, `<MenuItemOption>`
    - Props: `label`, `value: string[]`, `options: FilterOption[]`, `onChange`, `placeholder`, `isDisabled`, `width`
    - Trigger text: `placeholder` when 0 selected, `t('common:nSelected', { count })` when ≥1 selected
    - Render `<FormLabel>` above trigger (orange.300, xs font)
    - Add `aria-label` reflecting selection state
    - Import types from `./types`
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 5.10_

  - [x] 2.4 Add i18n translation keys for GenericMultiFilter
    - Add `nSelected` and `alle` keys to `common` namespace in all 8 locale files
    - Update both `frontend/src/locales/{lang}/common.json` and `frontend/public/locales/{lang}/common.json`
    - Languages: nl, en, de, fr, es, it, da, sv
    - _Requirements: 15.1, 15.2_

  - [x] 2.5 Update barrel export `frontend/src/components/filters/index.ts`
    - Export: `FilterableHeader`, `FilterPanel`, `GenericFilter`, `GenericMultiFilter`, `YearFilter`
    - Export all types from `./types`
    - Export props types: `FilterableHeaderProps`, `FilterPanelProps`, `GenericFilterProps`, `GenericMultiFilterProps`, `YearFilterProps`, `FilterOption`, `FilterOptionGroup`
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7_

  - [x] 2.6 Replace component test files from framework
    - Copy `FilterableHeader.test.tsx` and `FilterableHeader.property.test.tsx` into `frontend/src/components/filters/__tests__/`
    - Copy `FilterPanel.test.tsx` into `frontend/src/components/filters/__tests__/`
    - Adjust import paths as needed
    - _Requirements: 2.1, 3.1_

  - [x] 2.7 Write unit tests for GenericMultiFilter
    - Create `frontend/src/components/filters/__tests__/GenericMultiFilter.test.tsx`
    - Test: placeholder when 0 selected, count display when ≥1 selected, checkbox toggling calls onChange, disabled state, FormLabel rendering
    - _Requirements: 5.3, 5.4, 5.6, 5.9_

  - [x] 2.8 Write property tests for GenericMultiFilter
    - Create `frontend/src/components/filters/__tests__/GenericMultiFilter.property.test.tsx`
    - **Property 4: GenericMultiFilter selection display and accessibility**
    - **Property 5: GenericMultiFilter toggle produces correct array**
    - **Validates: Requirements 5.4, 5.6, 5.10**

  - [x] 2.9 Write property test for FilterPanel config rendering
    - Create `frontend/src/components/filters/__tests__/FilterPanel.property.test.tsx`
    - **Property 3: FilterPanel renders one control per config entry**
    - **Validates: Requirements 3.2**

- [x] 3. Checkpoint — Framework layer complete
  - Ensure all tests pass, ask the user if questions arise.
  - Run `npx tsc --noEmit` from `frontend/` — zero errors expected
  - Run `npx react-scripts test --watchAll=false --testPathPattern="useColumnFilters|useTableSort|useFilterableTable|FilterableHeader|FilterPanel|GenericMultiFilter"`

- [x] 4. Update hook API call sites and FilterPanel migrations
  - [x] 4.1 Update `UserManagement.tsx` hook call site
    - Verify/update `useFilterableTable` usage to match new `UseFilterableTableConfig` type
    - Ensure `processedData` and `getSortIndicator` are used correctly
    - Update `FilterableHeader` props if needed (add `w`/`maxW`, verify `aria-sort`)
    - _Requirements: 1.4, 14.1, 14.2_

  - [x] 4.2 Update `MemberAdminTable.tsx` hook call site and FilterPanel
    - Verify/update `useFilterableTable` usage
    - Migrate `<FilterPanel hasActiveFilters onReset>` child-node API to config-driven `<FilterPanel filters={[...]} layout="horizontal">`
    - _Requirements: 1.4, 3.7, 14.1, 14.2_

  - [x] 4.3 Update `ProductManagementPage.tsx` hook call site and FilterPanel
    - Verify/update `useFilterableTable` usage
    - Migrate `<FilterPanel>` from child-node to config-driven API
    - _Requirements: 1.4, 3.7, 14.1, 14.2_

  - [x] 4.4 Update `OrdersTab.tsx` hook call site and FilterPanel
    - Verify/update `useFilterableTable` usage
    - Migrate `<FilterPanel>` from child-node to config-driven API
    - _Requirements: 1.4, 3.7, 14.1, 14.2_

  - [x] 4.5 Update `PaymentsTab.tsx` hook call site and FilterPanel
    - Verify/update `useFilterableTable` usage
    - Migrate `<FilterPanel>` from child-node to config-driven API
    - _Requirements: 1.4, 3.7, 14.1, 14.2_

  - [x] 4.6 Update `FinanceModule.tsx` hook call site and FilterPanel
    - Verify/update `useFilterableTable` usage
    - Migrate `<FilterPanel>` from child-node to config-driven API
    - _Requirements: 1.4, 3.7, 14.1, 14.2_

  - [x] 4.7 Update `EventList.tsx` hook call site
    - Verify/update `useFilterableTable` usage to match new config type
    - _Requirements: 1.4, 14.1, 14.2_

  - [x] 4.8 Migrate remaining FilterPanel call sites
    - Update `Dashboard.tsx` (products): migrate to `<FilterPanel filters={[...]} layout="vertical">`
    - Update `WebshopPage.tsx`: migrate to `<FilterPanel filters={[...]} layout="vertical">`
    - Update `OrdersAdmin.tsx`: migrate to `<FilterPanel filters={[...]} layout="horizontal">`
    - Update `AdminOrderLockUnlock.tsx`: migrate to `<FilterPanel filters={[...]} layout="horizontal">`
    - _Requirements: 3.7, 14.1, 14.2_

- [x] 5. Checkpoint — Hook and FilterPanel migrations complete
  - Ensure all tests pass, ask the user if questions arise.
  - Run `npx tsc --noEmit` from `frontend/` — zero errors expected
  - Verify no unused imports remain (`npx eslint` on modified files)

- [x] 6. Migrate tables to row-click → modal pattern — Members module
  - [x] 6.1 Migrate `UserManagement.tsx` to row-click → modal
    - Remove per-row Edit, Add-to-Group, Enable/Disable, Delete buttons
    - Add `onClick={() => openModal(user)}` to each `<Tr>`
    - Add `_hover={{ bg: 'gray.700', cursor: 'pointer' }}`, `role="button"`, `tabIndex={0}`, `onKeyDown` for Enter
    - Move destructive actions (Delete, Enable/Disable) into the modal footer
    - Preserve all existing API calls and modal functionality
    - _Requirements: 7.1, 7.4, 7.5, 7.6, 14.1, 14.3, 14.4_

  - [x] 6.2 Migrate `GroupManagement.tsx` to row-click → modal
    - Remove per-row View, Edit, Delete buttons
    - Add row-click handler opening detail/edit modal
    - Move Delete action into modal footer
    - Add hover styles, role, tabIndex, keyboard support
    - _Requirements: 7.2, 7.4, 7.5, 7.6, 14.1, 14.3, 14.4_

  - [x] 6.3 Migrate `MembershipTable.tsx` to row-click → modal
    - Remove per-row Edit and Delete buttons
    - Add row-click handler opening edit modal
    - Move Delete action into modal footer
    - Add hover styles, role, tabIndex, keyboard support
    - _Requirements: 7.3, 7.4, 7.5, 7.6, 14.1, 14.3, 14.4_

- [x] 7. Migrate tables to row-click → modal pattern — Webshop and Event modules
  - [x] 7.1 Migrate `VariantSubTable.tsx` to row-click → modal
    - Remove per-row Add-stock, Deactivate, Delete buttons
    - Add row-click handler opening variant detail/edit modal
    - Move stock/deactivate/delete actions into modal
    - Add hover styles, role, tabIndex, keyboard support
    - _Requirements: 8.1, 8.4, 14.1, 14.3, 14.4_

  - [x] 7.2 Migrate `AdminOrderLockUnlock.tsx` to row-click → modal
    - Remove per-row Unlock button
    - Add row-click handler opening modal with Unlock action
    - Retain checkbox column for bulk operations
    - Add hover styles, role, tabIndex, keyboard support
    - _Requirements: 8.2, 8.3, 8.4, 14.1, 14.3, 14.4_

  - [x] 7.3 Migrate `AdminClaimsManagement.tsx` to row-click → modal
    - Remove per-row Menu and Assign button
    - Add row-click handler opening claim detail/action modal
    - Add hover styles, role, tabIndex, keyboard support
    - _Requirements: 9.1, 9.4, 14.1, 14.3, 14.4_

  - [x] 7.4 Migrate `EventAccessManager.tsx` to row-click → modal
    - Remove per-row Revoke button
    - Add row-click handler opening access detail modal with Revoke action
    - Retain checkbox column for bulk operations
    - Add hover styles, role, tabIndex, keyboard support
    - _Requirements: 9.2, 9.3, 9.4, 14.1, 14.3, 14.4_

  - [x] 7.5 Migrate `MyOrders.tsx` to row-click → modal with PDF exception
    - Add row-click handler opening order detail modal
    - Retain per-row PDF download `<IconButton>` with `e.stopPropagation()`
    - Add hover styles, role, tabIndex, keyboard support
    - Ensure download button click does NOT trigger modal
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 14.1, 14.3, 14.4_

- [x] 8. Checkpoint — Row-click migrations complete
  - Ensure all tests pass, ask the user if questions arise.
  - Run `npx tsc --noEmit` from `frontend/` — zero errors expected
  - Verify modals open correctly with correct data

- [x] 9. Migrate ad-hoc filters to framework components
  - [x] 9.1 Migrate `EventCalendarPage.tsx` to framework filters
    - Replace custom `<Select>` + `<HStack>` tag-buttons for event type with `<GenericMultiFilter>`
    - Replace custom `<Select>` for region with `<GenericFilter>`
    - Wrap filters and date inputs in `<FilterPanel layout="horizontal">`
    - Preserve date-from/date-to inputs and reset button
    - Preserve existing filter logic (events whose `event_type` not in selection are excluded)
    - Preserve all translation keys
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 15.4, 15.5_

  - [x] 9.2 Migrate `ReportsTab.tsx` to framework filters
    - Replace 3 custom `<Select>` elements with `<GenericFilter>` components
    - Wrap in `<FilterPanel layout="horizontal">`
    - Use existing `REPORT_TYPE_LABELS`, `ORDER_STATUS_OPTIONS`, `PAYMENT_STATUS_OPTIONS` as `FilterOption[]`
    - Preserve `setReportType`, `setOrderStatus`, `setPaymentStatus` callbacks
    - Preserve Refresh and Export action bar
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 15.4, 15.5_

  - [x] 9.3 Migrate `EventAdminPage.tsx` to framework filter
    - Replace custom event-picker `<Select>` with `<GenericFilter>`
    - Use same event options currently used by custom `<Select>`
    - Preserve `onChange` handler and selected event state
    - Preserve placeholder behavior
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 15.4, 15.5_

  - [x] 9.4 Write property test for EventCalendarPage filter logic
    - Create `frontend/src/pages/__tests__/EventCalendarPage.property.test.tsx`
    - **Property 6: Event calendar type filter exclusion**
    - **Validates: Requirements 11.3**

- [x] 10. Final checkpoint — Full consolidation complete
  - Ensure all tests pass, ask the user if questions arise.
  - Run `npx tsc --noEmit` from `frontend/` — zero errors expected
  - Run `npx eslint` on all modified files — zero errors
  - Verify all 8 locale files contain `nSelected` and `alle` keys
  - Verify barrel export resolves all named exports without error
  - _Requirements: 1.4, 1.5, 4.5, 14.5, 14.6, 15.3_

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The framework hooks and components are copied from `filter-table-framework/` with import path adjustments only
- All user-facing strings must use `useTranslation()` — never hardcode Dutch text
- Run `npx react-scripts test --watchAll=false --testPathPattern="..."` for targeted test execution (never the full suite)

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "1.3", "1.4"] },
    { "id": 2, "tasks": ["1.5", "1.6", "1.7", "2.1", "2.2", "2.3", "2.4"] },
    { "id": 3, "tasks": ["2.5", "2.6", "2.7", "2.8", "2.9"] },
    {
      "id": 4,
      "tasks": ["4.1", "4.2", "4.3", "4.4", "4.5", "4.6", "4.7", "4.8"]
    },
    {
      "id": 5,
      "tasks": ["6.1", "6.2", "6.3", "7.1", "7.2", "7.3", "7.4", "7.5"]
    },
    { "id": 6, "tasks": ["9.1", "9.2", "9.3", "9.4"] }
  ]
}
```
