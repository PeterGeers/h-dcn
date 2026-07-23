---
inclusion: fileMatch
fileMatchPattern: "frontend/**/*.tsx,frontend/**/*.ts,frontend/**/*.css"
---

# Look and Feel

Design system rules for the H-DCN portal. Ensures visual consistency across all components.

## Brand Colors

- **Primary**: H-DCN Orange `#f56500` (hover: `#e55a00`)
- **Status**: green=active, yellow=pending, red=error/inactive, blue=info
- **Dark theme**: `bg="black"` page, `gray.800` cards, `orange.400` borders, `orange.300` text headers

## Typography Scale

- **2xl** (24px): page titles — **lg** (18px): section headers — **md** (16px): card headers
- **sm** (14px): main content — **xs** (12px): help text, captions

## Action Buttons

- **No action buttons in table rows** — keep rows clean and compact
- Click a row to open a modal for edit/delete/detail actions
- Place primary actions (Add, Export, Import) in the page header row, right-aligned
- Use `colorScheme="orange"` for primary actions, `variant="ghost"` for secondary
- Exception: checkboxes for bulk operations (select rows → toolbar action above table)

## Table Layout

- Chakra UI `Table` with `variant="simple"` on dark background (`bg="gray.800"`)
- Sortable column headers where applicable
- Hover-highlighted rows: `_hover={{ bg: 'gray.700', cursor: 'pointer' }}`
- **Row click opens detail/edit Modal — no per-row buttons**
- Status shown as `Badge` components, read-only data only in cells
- Responsive `overflowX="auto"` wrapper for mobile
- Hide non-essential columns on mobile: `display={{ base: 'none', md: 'table-cell' }}`

## Modal Layout

- Chakra UI `<Modal>` with `isCentered` for all CRUD operations
- Dark theme: `<ModalContent bg="gray.800" borderColor="orange.400" borderWidth="1px">`
- Form inside modal uses Formik + Yup validation
- Standard button layout: **Cancel (left, ghost) + Save/Submit (right, orange solid)**
- Loading state on submit button (`isLoading` prop)
- `closeOnOverlayClick={false}` for edit modals (prevent accidental loss)
- `closeOnOverlayClick={true}` for read-only detail modals

## Filters

Use the Table Filter Framework — hybrid approach:

- Text search filters in column headers (`FilterableHeader`)
- Dropdowns/multi-select above the table (`FilterPanel` + `GenericFilter`)
- Clear all / reset button to return to default view
- Components in `frontend/src/components/filters/`

## Component Patterns

- **Cards**: `bg="gray.800"` + `borderColor="orange.400"` + orange headings
- **Forms**: `InputLeftAddon` with `bg="orange.300"` for currency, `VStack spacing={4}`
- **Save button**: Fixed bottom-center, only visible when `hasChanges`, orange circular icon button

## Field States (visual cues only, no text badges)

- **Editable**: white bg, orange hover/focus borders, `cursor="text"`
- **Read-only**: `bg="gray.100"` (light) / `bg="gray.700"` (dark), `cursor="default"`, no hover
- **Help text**: Use placeholders or tooltips, never persistent text under fields

## Icons — Chakra UI Only

- **CRUD**: ViewIcon=blue, EditIcon=orange, DeleteIcon=red, AddIcon=green, CopyIcon=teal
- **Navigation**: ChevronLeft/Right=orange, ChevronDown/Up=gray
- **Status**: CheckCircle=green, Warning=yellow, Info=blue, Close=gray
- **Sizes**: `xs` modal actions, `sm` cards, `md` page-level primary actions
- **Required**: Always include `aria-label` and wrap in `<Tooltip>`

## Responsive Rules

- Mobile-first: `{{ base: 1, md: 2 }}` grid patterns
- Touch targets: 44px minimum
- Input font: 16px minimum on mobile (prevents iOS zoom)
- Tables: horizontal scroll with responsive column hiding
- Text: `fontSize={{ base: 'xs', md: 'sm' }}`
- Headers: `Flex wrap="wrap"` instead of rigid `HStack` for mobile wrapping

## Status Badge Colors

- **Member**: Actief=green, Aangemeld=yellow, Opgezegd/Geschorst=red, wachtRegio=orange
- **Membership**: Gewoon lid=blue, Gezins lid=purple, Erelid=gold, Donateur=teal, Sponsor=orange

## Key Principles

1. Use Chakra UI components and theme tokens — no custom CSS
2. WCAG AA compliance (4.5:1 contrast ratio)
3. Consistent icon colors per action type across the entire app
4. Dark theme is the default for admin/member views
5. No action buttons on table rows — all CRUD actions live in modals

## Reference Implementation

`frontend/src/components/MemberAdminTable.tsx` + `frontend/src/modules/products/ProductManagementPage.tsx` correctly demonstrate the table patterns (dark theme, FilterableHeader, FilterPanel with GenericFilter, row-click → modal, orange primary actions, i18n, responsive).

## Full Reference

Full design system with all patterns and examples: [`docs/development/look-and-feel.md`](../../docs/development/look-and-feel.md)
