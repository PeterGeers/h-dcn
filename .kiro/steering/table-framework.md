---
inclusion: fileMatch
fileMatchPattern: "frontend/**/Table*.tsx,frontend/**/table*.ts,frontend/**/*List*.tsx,frontend/**/filters/**,frontend/**/useTableSort*"
---

# Table & Filter Framework

Reusable filter/sort components for all data tables. Eliminates ~590 lines of boilerplate per table.

## Components — `frontend/src/components/filters/`

| Component          | Purpose                                                                   |
| ------------------ | ------------------------------------------------------------------------- |
| `GenericFilter`    | Single dropdown filter (status, regio, type, etc.)                        |
| `FilterPanel`      | Container row above the table — wraps filters, shows reset + result count |
| `FilterableHeader` | Replaces `<Th>` — inline text filter input + sort toggle                  |
| `YearFilter`       | Year dropdown with auto-generated range                                   |

## Hook — `frontend/src/hooks/useTableSort.ts`

```typescript
const { sortField, sortDirection, handleSort, sortData } = useTableSort({
  defaultSort: { field: "name", direction: "asc" },
});
const sorted = sortData(data);
```

- Cycles: asc → desc → none (3-click)
- Smart compare: string (locale `nl`), number, date, null/undefined → sort to end
- Returns new array (immutable)

## Usage Pattern

```tsx
import { FilterPanel, GenericFilter, FilterableHeader, YearFilter } from '../../components/filters';
import { useTableSort } from '../../hooks/useTableSort';

// 1. Filter state
const [filters, setFilters] = useState({ status: '', regio: '', name: '' });
const setFilter = (key: string, value: string) => setFilters(f => ({ ...f, [key]: value }));
const hasActiveFilters = Object.values(filters).some(Boolean);

// 2. Sort state
const { sortField, sortDirection, handleSort, sortData } = useTableSort({
  defaultSort: { field: 'naam', direction: 'asc' }
});

// 3. Apply filters + sort
const filtered = data.filter(item => {
  if (filters.status && item.status !== filters.status) return false;
  if (filters.name && !item.naam?.toLowerCase().includes(filters.name.toLowerCase())) return false;
  return true;
});
const sorted = sortData(filtered);

// 4. Render
<FilterPanel hasActiveFilters={hasActiveFilters} onReset={() => setFilters({ status: '', regio: '', name: '' })} filteredCount={sorted.length} totalCount={data.length}>
  <GenericFilter label="Status" value={filters.status} options={statusOptions} onChange={(v) => setFilter('status', v)} />
  <YearFilter value={filters.year} onChange={(v) => setFilter('year', v)} />
</FilterPanel>

<Table>
  <Thead>
    <Tr>
      <FilterableHeader label="Naam" filterValue={filters.name} onFilterChange={(v) => setFilter('name', v)} sortable sortDirection={sortField === 'naam' ? sortDirection : null} onSort={() => handleSort('naam')} />
    </Tr>
  </Thead>
</Table>
```

## Rules

1. **Always use this framework** for new tables — never build custom filter/sort from scratch
2. **GenericFilter for dropdowns** (above table), **FilterableHeader for text search** (in column headers)
3. **Combine both** when a table needs dropdown filters (status, regio) AND column text search
4. **Sort nulls to end** — handled by `useTableSort`, no extra logic needed
5. **Dark theme styling** is built in — don't override colors on filter components
6. **FilterPanel shows counts** — always pass `filteredCount` and `totalCount` for user feedback
7. **Reset button** appears automatically when `hasActiveFilters` is true

## Reference

- Components: `frontend/src/components/filters/`
- Hook: `frontend/src/hooks/useTableSort.ts`
- Exports: `import { FilterableHeader, FilterPanel, GenericFilter, YearFilter } from '../../components/filters';`
