---
inclusion: manual
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

## Component Patterns

- **Cards**: `bg="gray.800"` + `borderColor="orange.400"` + orange headings
- **Tables**: `bg="gray.700"` headers with `color="orange.300"`, white row text
- **Modals**: Fixed center positioning with `transform="translate(-50%, -50%)"`, `maxHeight="80vh"`
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
- **Sizes**: `xs` table actions, `sm` cards, `md` main actions
- **Required**: Always include `aria-label` and wrap in `<Tooltip>`

## Responsive Rules

- Mobile-first: `{{ base: 1, md: 2 }}` grid patterns
- Touch targets: 44px minimum
- Input font: 16px minimum on mobile (prevents iOS zoom)
- Tables: horizontal scroll with responsive column hiding
- Text: `fontSize={{ base: 'xs', md: 'sm' }}`

## Status Badge Colors

- **Member**: Actief=green, Aangemeld=yellow, Opgezegd/Geschorst=red, wachtRegio=orange
- **Membership**: Gewoon lid=blue, Gezins lid=purple, Erelid=gold, Donateur=teal, Sponsor=orange

## Key Principles

1. Use Chakra UI components and theme tokens — no custom CSS
2. WCAG AA compliance (4.5:1 contrast ratio)
3. Consistent icon colors per action type across the entire app
4. Dark theme is the default for admin/member views

## Reference

Full design system with all patterns and examples: [`docs/development/look-and-feel.md`](../../docs/development/look-and-feel.md)
