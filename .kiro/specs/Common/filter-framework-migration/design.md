# Design: Filter Framework Migratie

## Overzicht

Migratie van 7 componenten van custom filter/sort implementaties naar het gestandaardiseerde Table Filter Framework. Geen nieuwe infrastructure, geen API wijzigingen — puur frontend refactoring.

## Architectuur

Het bestaande framework (al in het project) bestaat uit drie lagen:

```
┌────────────────────────────────────────────────────────────────┐
│  Components (UI)                                               │
│  FilterableHeader · FilterPanel · GenericFilter · YearFilter   │
├────────────────────────────────────────────────────────────────┤
│  Hooks (state + logic)                                         │
│  useColumnFilters · useTableSort · useFilterableTable          │
├────────────────────────────────────────────────────────────────┤
│  Consumers (te migreren componenten)                           │
│  EventList · MemberAdminTable · UserManagement · FinanceModule │
│  AdminOrderLockUnlock · ProductManagementPage · OrdersAdmin    │
└────────────────────────────────────────────────────────────────┘
```

### Migratie-patroon (simpele tabellen)

Voor componenten met alleen text-filters + sort (EventList, UserManagement):

```tsx
// VOOR (custom)
const [searchTerm, setSearchTerm] = useState('');
const filteredData = data.filter(item => item.name.includes(searchTerm)).sort(...);

// NA (framework)
import { useFilterableTable } from '../../hooks/useFilterableTable';
import { FilterableHeader } from '../../components/filters';

const INITIAL_FILTERS = { name: '', location: '', date: '' };

const { filters, setFilter, handleSort, sortField, sortDirection, processedData } =
  useFilterableTable(permissionFilteredData, {
    initialFilters: INITIAL_FILTERS,
    defaultSort: { field: 'start_date', direction: 'desc' },
  });
```

### Migratie-patroon (hybride: text + dropdowns)

Voor componenten met zowel text-filters als dropdown/enum-filters (MemberAdminTable, FinanceModule):

```tsx
// Text filters via useFilterableTable (in headers)
const INITIAL_FILTERS = { naam: '', lidnummer: '', email: '' };
const { filters, setFilter, handleSort, sortField, sortDirection, processedData, filteredCount, totalCount } =
  useFilterableTable(baseData, { initialFilters: INITIAL_FILTERS, defaultSort: { field: 'lidnummer', direction: 'desc' } });

// Dropdown filters als extra state (bovenaan, in FilterPanel)
const [statusFilter, setStatusFilter] = useState('');
const [regioFilter, setRegioFilter] = useState('');

// Combineer: dropdown filters VOOR het framework (pre-filter), text+sort door framework
const preFilteredData = useMemo(() => {
  let data = allData;
  if (statusFilter) data = data.filter(m => m.lid_status === statusFilter);
  if (regioFilter) data = data.filter(m => m.regio === regioFilter);
  return data;
}, [allData, statusFilter, regioFilter]);

// Framework krijgt pre-filtered data
const { filters, setFilter, ... } = useFilterableTable(preFilteredData, { ... });
```

### Migratie-patroon (alleen dropdown, server-side)

Voor componenten waar de filter naar de API gaat (OrdersAdmin):

```tsx
// Alleen UI vervanging — GenericFilter ipv custom Select
<FilterPanel
  hasActiveFilters={!!paymentStatusFilter}
  onReset={() => setPaymentStatusFilter("")}
>
  <GenericFilter
    label="Betaalstatus"
    value={paymentStatusFilter}
    options={statusOptions}
    onChange={setPaymentStatusFilter}
  />
</FilterPanel>
```

## Component Migratie Details

### Component 1: EventList

**Huidige staat:** 1 zoekbalk (naam+locatie) + inline .sort() op datum

**Na migratie:**

- FilterableHeader op: Naam, Datum, Locatie, Regio, Deelnemers, Kosten, Inkomsten, Winst
- Permission-filtering blijft als pre-filter (voor het framework)
- Default sort: start_date desc (nieuwste eerst)
- Zoekbalk verdwijnt (per-kolom filter vervangt het)

**Data flow:**

```
events (prop) → permissionFilter (useMemo) → useFilterableTable → processedData → render
```

**Regels:**

- Regionale permissie-filtering MOET vóór het framework plaatsvinden (useMemo)
- Het framework filtert/sorteert alleen de zichtbare events
- Financiële kolommen worden als string gefilterd maar als number gesorteerd (useTableSort herkent dit)

### Component 2: MemberAdminTable

**Huidige staat:** Custom columnFilters (Record<string, string>) + renderColumnFilter() met type-aware inputs + custom .sort()

**Na migratie:**

- FilterPanel bovenaan met GenericFilter voor: lid_status, regio, lidmaatschap_type
- FilterableHeader per text-kolom (lidnummer, naam, email, etc.)
- useFilterableTable voor text filters + sort
- Dropdown filters als pre-filter (useMemo → useFilterableTable)

**Data flow:**

```
members (prop) → computeCalculatedFields → regionalFilter → dropdownPreFilter → useFilterableTable → processedData → render
```

**Complexiteit:**

- MemberAdminTable heeft dynamische kolommen via `tableContext` (MEMBER_TABLE_CONTEXTS)
- Niet elke kolom is filterbaar — alleen kolommen met `filterable: true`
- Select-type kolommen (lid_status, regio) krijgen GenericFilter
- Text/number-type kolommen krijgen FilterableHeader
- De context-switch (memberCompact, memberFull, etc.) reset filters

### Component 3: UserManagement

**Huidige staat:** 1 zoekbalk (username+email) + fixed sort op email

**Na migratie:**

- FilterableHeader op: Email, Username, Status, Aangemaakt
- Default sort: email asc
- Zoekbalk verdwijnt

**Data flow:**

```
users (state) → useFilterableTable → processedData → render
```

### Component 4: FinanceModule

**Huidige staat:** Custom `<Select>` voor betaalstatus + geen sort

**Na migratie:**

- FilterPanel met GenericFilter voor betaalstatus
- FilterableHeader op: Naam, Datum, Kosten, Inkomsten, Winst
- Default sort: geen (of datum desc)

**Data flow:**

```
events (prop) → processToFinanceData → statusPreFilter → useFilterableTable → processedData → render
```

### Component 5: AdminOrderLockUnlock

**Huidige staat:** Custom `<Select>` voor order status

**Na migratie:**

- FilterPanel met GenericFilter voor status
- FilterableHeader op tabel-kolommen (indien aanwezig)
- Simpelste migratie

### Component 6: ProductManagementPage

**Huidige staat:** Custom ProductFilter component + active/inactive toggle + event_ids filter

**Na migratie:**

- FilterPanel met GenericFilter voor: groep, subgroep, event
- Active/inactive toggle blijft als aparte Button/Switch (is geen dropdown filter)
- ProductFilter component kan eventueel vervangen worden door GenericFilters in FilterPanel

**Opmerking:** ProductManagementPage rendert een card-grid, geen tabel. FilterableHeader is hier niet van toepassing. Alleen FilterPanel + GenericFilter voor de dropdown filters.

### Component 7: OrdersAdmin

**Huidige staat:** Custom `<Select>` voor payment status (server-side)

**Na migratie:**

- GenericFilter in FilterPanel als UI vervanging
- Filter value blijft naar useAdminOrders hook gaan (server-side)
- Geen useFilterableTable (geen client-side filtering)

## Styling Standaarden

Alle filter componenten volgen het h-dcn design system:

```tsx
// FilterableHeader styling (al correct in huidige implementatie)
<Th color="orange.300" verticalAlign="top" p={2}>
  <Input size="xs" bg="gray.700" borderColor="gray.600" color="white"
    _placeholder={{ color: 'gray.500' }} _focus={{ borderColor: 'orange.400' }} />
</Th>

// GenericFilter styling
<Select size="sm" bg="gray.700" borderColor="gray.600" color="white"
  _focus={{ borderColor: 'orange.400' }}>
  <option style={{ backgroundColor: '#2D3748', color: 'white' }}>...</option>
</Select>

// FilterPanel styling
<HStack spacing={4} mb={4} p={3} bg="gray.800" borderRadius="md"
  border="1px" borderColor="gray.600" flexWrap="wrap" align="flex-end">
```

## Error Handling

Geen nieuwe error paths. Bestaande gedrag blijft:

- Lege data → "Geen resultaten gevonden" tekst
- Filter die geen matches oplevert → lege tabel + resultaat teller "0 / X resultaten"
- Reset knop herstelt alle filters

## Testing Strategie

Per gemigreerd component:

1. **Type check**: `npx tsc --noEmit` moet slagen
2. **Lint**: `npx eslint <file>` moet slagen
3. **Visuele verificatie**: Component moet renderen zonder crashes
4. **Functionele verificatie**: Filters + sort moeten werken (handmatig of via existing tests)

Geen nieuwe unit tests vereist voor de migratie zelf (het framework heeft al tests). Bestaande component tests worden aangepast indien ze breken door de import-wijzigingen.

## Correctness Properties

### Property 1: Framework output bevat dezelfde rijen als custom implementatie

_Voor elke_ combinatie van filter-waarden die zowel de oude als nieuwe implementatie ondersteunen, moet het resultaat identieke rijen bevatten (mogelijk in andere volgorde als sort verschilt).

**Valideert: Requirements 1-7**

### Property 2: Permission-filtering is onafhankelijk van framework filters

_Voor elke_ gebruiker met regionale beperkingen, moeten events/members buiten hun regio NOOIT zichtbaar zijn, ongeacht welke framework-filters actief zijn.

**Valideert: Requirements 1.4, 2.7**

### Property 3: Dropdown pre-filters combineren correct met text-filters

_Voor elke_ combinatie van dropdown-filter (status, regio) en text-filter (naam, email), moet het resultaat de AND van beide filters zijn.

**Valideert: Requirements 2.4, 4.2**
