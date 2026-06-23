# Filter Framework — Reuse Guide for h-dcn

## Overview

The **Table Filter Framework v2** from myAdmin provides a complete, reusable system for building filterable and sortable tables with React. It uses a hybrid approach: text search filters inside column headers, dropdown/multi-select filters above the table.

The framework eliminates ~590 lines of boilerplate per table and provides consistent UX with debounced filtering, case-insensitive matching, and accessible sort controls.

## Architecture (3 layers)

```
┌──────────────────────────────────────────────────────────────┐
│  Components (render UI)                                      │
│  FilterPanel · GenericFilter · YearFilter · FilterableHeader │
├──────────────────────────────────────────────────────────────┤
│  Hooks (state + logic)                                       │
│  useColumnFilters · useTableSort · useFilterableTable        │
│  useTableConfig (parameter-driven, optional)                 │
├──────────────────────────────────────────────────────────────┤
│  Services (optional)                                         │
│  parameterService.ts (only if using useTableConfig)          │
└──────────────────────────────────────────────────────────────┘
```

## Quick Start — Minimal Example

```tsx
import { useFilterableTable } from "@/hooks/useFilterableTable";
import { FilterableHeader } from "@/components/filters/FilterableHeader";

const INITIAL_FILTERS = { name: "", status: "", email: "" };

function MyTable({ data }) {
  const {
    filters,
    setFilter,
    handleSort,
    sortField,
    sortDirection,
    processedData,
  } = useFilterableTable(data, {
    initialFilters: INITIAL_FILTERS,
    defaultSort: { field: "name", direction: "asc" },
  });

  return (
    <Table>
      <Thead>
        <Tr>
          <FilterableHeader
            label="Name"
            filterValue={filters.name}
            onFilterChange={(v) => setFilter("name", v)}
            sortable
            sortDirection={sortField === "name" ? sortDirection : null}
            onSort={() => handleSort("name")}
          />
          {/* ... more columns */}
        </Tr>
      </Thead>
      <Tbody>
        {processedData.map((row) => (
          <Tr key={row.id} _hover={{ bg: "gray.700", cursor: "pointer" }}>
            <Td>{row.name}</Td>
          </Tr>
        ))}
      </Tbody>
    </Table>
  );
}
```

## Key Hooks

| Hook                 | Purpose                                     | Use when                                        |
| -------------------- | ------------------------------------------- | ----------------------------------------------- |
| `useColumnFilters`   | Filter state + debounced substring matching | You only need filtering (no sorting)            |
| `useTableSort`       | Sort state + toggle + comparison logic      | You only need sorting (no filtering)            |
| `useFilterableTable` | Composes both (filter → sort pipeline)      | You need both — most common case                |
| `useTableConfig`     | Reads column config from parameter system   | Complex tables (8+ columns) with runtime config |

## Key Components

| Component          | Purpose                                          | Placement          |
| ------------------ | ------------------------------------------------ | ------------------ |
| `FilterableHeader` | `<Th>` with label + sort indicator + text filter | Column headers     |
| `FilterPanel`      | Container for dropdown/multi-select filters      | Above the table    |
| `GenericFilter`    | Single dropdown or multi-select control          | Inside FilterPanel |
| `YearFilter`       | Year-specific dropdown filter                    | Inside FilterPanel |

## Source Code References (myAdmin)

### Hooks

| File               | Path                                       |
| ------------------ | ------------------------------------------ |
| useColumnFilters   | `frontend/src/hooks/useColumnFilters.ts`   |
| useTableSort       | `frontend/src/hooks/useTableSort.ts`       |
| useFilterableTable | `frontend/src/hooks/useFilterableTable.ts` |
| useTableConfig     | `frontend/src/hooks/useTableConfig.ts`     |

### Components

| File             | Path                                                   |
| ---------------- | ------------------------------------------------------ |
| FilterableHeader | `frontend/src/components/filters/FilterableHeader.tsx` |
| FilterPanel      | `frontend/src/components/filters/FilterPanel.tsx`      |
| GenericFilter    | `frontend/src/components/filters/GenericFilter.tsx`    |
| YearFilter       | `frontend/src/components/filters/YearFilter.tsx`       |

### Spec / Design Documentation

| Document                                          | Path                                                                                                              |
| ------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| Full reference guide                              | `.kiro/specs/Common/Frameworks/table-filter-framework-v2/Filters a generic approach/TABLE_FILTER_FRAMEWORK_V2.md` |
| Design doc (architecture, interfaces, properties) | `.kiro/specs/Common/Frameworks/table-filter-framework-v2/design.md`                                               |
| Requirements                                      | `.kiro/specs/Common/Frameworks/table-filter-framework-v2/Filters a generic approach/requirements.md`              |
| Tasks                                             | `.kiro/specs/Common/Frameworks/table-filter-framework-v2/Filters a generic approach/TASKS.md`                     |

### Reference Implementations (examples to follow)

| Pattern                   | File                                                      | Notes                                   |
| ------------------------- | --------------------------------------------------------- | --------------------------------------- |
| Simple CRUD table         | `frontend/src/pages/ZZPProducts.tsx`                      | Hardcoded filters, all columns sortable |
| Hybrid + parameter-driven | `frontend/src/components/TenantAdmin/ChartOfAccounts.tsx` | Dynamic columns from parameters         |
| Multi-section report      | `frontend/src/components/ProfitLoss.tsx`                  | Multiple useFilterableTable instances   |

## What to Copy for h-dcn

For minimal reuse, copy these files:

1. `frontend/src/hooks/useColumnFilters.ts` — filter logic
2. `frontend/src/hooks/useTableSort.ts` — sort logic
3. `frontend/src/hooks/useFilterableTable.ts` — composed hook
4. `frontend/src/components/filters/FilterableHeader.tsx` — header component

Optional (if you need dropdown filters above the table):

5. `frontend/src/components/filters/FilterPanel.tsx`
6. `frontend/src/components/filters/GenericFilter.tsx`
7. `frontend/src/components/filters/YearFilter.tsx`

Skip `useTableConfig` unless you need runtime-configurable column visibility via a parameter system.

## Dependencies

- React 18+ (hooks)
- Chakra UI (Table, Th, Input, VStack, HStack, Text components)
- No other external dependencies

## Filter Behaviour Summary

- **Text filters**: case-insensitive substring match, debounced (150ms default)
- **AND logic**: all active filters must pass for a row to be included
- **Missing fields**: if a filter key doesn't exist on a row, the row passes (not excluded)
- **Sort**: strings use case-insensitive `localeCompare`, numbers use numeric comparison
- **Null handling**: null/undefined values sort to end regardless of direction
- **Pipeline**: filter first → then sort (order is fixed)
