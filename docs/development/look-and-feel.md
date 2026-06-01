# H-DCN Design System — Full Reference

This document contains the complete design system documentation for the H-DCN portal. It serves as the detailed reference for the concise steering file at [`.kiro/steering/look-and-feel.md`](../../.kiro/steering/look-and-feel.md).

> **Tech stack context**: React 18 + TypeScript, Chakra UI v2, dark theme default. See [`.kiro/steering/tech.md`](../../.kiro/steering/tech.md) for full stack details.

---

## Color Palette

### Brand Colors

| Token         | Value     | Usage                         |
| ------------- | --------- | ----------------------------- |
| Primary       | `#f56500` | Brand orange, primary actions |
| Primary Hover | `#e55a00` | Interactive hover states      |
| Primary Light | `#ff7a1a` | Accents and highlights        |

### Neutral Colors (Light Theme)

| Token                | Value     | Usage                       |
| -------------------- | --------- | --------------------------- |
| Background Primary   | `#ffffff` | Main content areas          |
| Background Secondary | `#f7fafc` | Card backgrounds, sections  |
| Background Tertiary  | `#edf2f7` | Input backgrounds, disabled |
| Text Primary         | `#2d3748` | Main text content           |
| Text Secondary       | `#4a5568` | Supporting text, labels     |
| Text Muted           | `#718096` | Help text, placeholders     |
| Border               | `#e2e8f0` | Card borders, dividers      |

### Dark Theme Colors

| Token                | Value        | Usage                          |
| -------------------- | ------------ | ------------------------------ |
| Background Primary   | `#000000`    | Page background (`bg="black"`) |
| Background Secondary | `#1a1a1a`    | Elevated surfaces              |
| Card Background      | `gray.800`   | Card containers                |
| Header Background    | `gray.700`   | Table/section headers          |
| Border Accent        | `orange.400` | Card borders, dividers         |
| Text Primary         | `#ffffff`    | Main text                      |
| Text Secondary       | `#cccccc`    | Supporting text                |
| Text Accent          | `orange.300` | Headers, labels                |

### Status Colors

| Status  | Color  | Hex       | Usage                        |
| ------- | ------ | --------- | ---------------------------- |
| Success | green  | `#38a169` | Active status, confirmations |
| Warning | yellow | `#d69e2e` | Pending status, cautions     |
| Error   | red    | `#e53e3e` | Errors, inactive status      |
| Info    | blue   | `#3182ce` | Information, neutral status  |

---

## Typography Scale

### Font Stack

System fonts: `-apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Oxygen", "Ubuntu", "Cantarell", sans-serif`

### Size Tokens

| Chakra Token | Pixels | Usage                       |
| ------------ | ------ | --------------------------- |
| `2xl`        | 24px   | Page titles                 |
| `xl`         | 20px   | Major section headers       |
| `lg`         | 18px   | Section headers             |
| `md`         | 16px   | Card headers, body text     |
| `sm`         | 14px   | Main content, table text    |
| `xs`         | 12px   | Help text, captions, badges |

### Responsive Typography

```tsx
// Table text scales down on mobile
<Text fontSize={{ base: 'xs', md: 'sm' }}>Content</Text>

// Mobile inputs must be 16px minimum (prevents iOS zoom)
<Input fontSize={{ base: '16px', md: 'sm' }} />
```

### Font Weights

| Weight     | Usage                    |
| ---------- | ------------------------ |
| `normal`   | Body text, table content |
| `semibold` | Labels, card headers     |
| `bold`     | Page titles, emphasis    |

---

## Spacing System

Based on Chakra UI's spacing scale (1 unit = 4px):

| Token | Pixels | Usage                           |
| ----- | ------ | ------------------------------- |
| `1`   | 4px    | Tight spacing (icon gaps)       |
| `2`   | 8px    | Compact spacing (badge padding) |
| `3`   | 12px   | Field spacing, grid gaps        |
| `4`   | 16px   | Form field spacing              |
| `6`   | 24px   | Section spacing, container pad  |
| `8`   | 32px   | Major section gaps              |
| `12`  | 48px   | Page-level spacing              |

### Common Spacing Patterns

```tsx
// Page container
<Box maxW="1200px" mx="auto" p={6}>

// Section stacking
<VStack spacing={6}>

// Form fields
<VStack spacing={4}>

// Grid layout
<SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={3}>

// Compact field spacing
<Box mb={1}>
```

---

## Field State Patterns

All field states communicate through visual cues only — never use text badges like "Bewerkbaar" or "Alleen lezen".

### Editable Fields

```tsx
<Input
  bg="white" // light theme
  // bg="gray.600"             // dark theme
  borderColor="gray.300"
  cursor="text"
  _hover={{ borderColor: "orange.400" }}
  _focus={{ borderColor: "orange.500", boxShadow: "0 0 0 1px orange.500" }}
  _placeholder={{ color: "gray.400" }}
  size="sm"
  fontSize="sm"
/>
```

### Read-Only Fields

```tsx
<Input
  isReadOnly
  bg="gray.100" // light theme
  // bg="gray.700"             // dark theme
  borderColor="gray.300"
  cursor="default"
  color="gray.600" // light theme
  // color="gray.300"          // dark theme
  minH="32px"
  size="sm"
  fontSize="sm"
/>
```

### Loading State

```tsx
<Skeleton height="32px" borderRadius="md" />
// or
<Input isDisabled placeholder="Laden..." />
```

### Error State

```tsx
<FormControl isInvalid>
  <FormLabel>Veldnaam</FormLabel>
  <Input borderColor="red.500" _focus={{ borderColor: "red.500" }} />
  <FormErrorMessage>Foutmelding hier</FormErrorMessage>
</FormControl>
```

### Success/Saved State

```tsx
<InputGroup>
  <Input borderColor="green.400" />
  <InputRightElement>
    <CheckCircleIcon color="green.400" />
  </InputRightElement>
</InputGroup>
```

### Help Text Strategy

- **Placeholders**: Show guidance in empty fields via `placeholder`
- **Tooltips**: Use `<Tooltip label="...">` on field labels for context
- **No persistent text**: Avoid `<FormHelperText>` under fields — it clutters the UI

---

## Card Patterns

### Standard Card (Dark Theme)

```tsx
<Box bg="gray.800" border="1px" borderColor="orange.400" borderRadius="lg">
  <Box bg="gray.700" py={1} borderRadius="lg lg 0 0">
    <Heading size="sm" color="orange.300">
      Section Title
    </Heading>
  </Box>
  <Box p={4}>{/* Card content */}</Box>
</Box>
```

### Member Self-Service Card (Orange Content Area)

```tsx
<Box bg="gray.800" border="1px" borderColor="orange.400" borderRadius="lg">
  <Box bg="gray.700" py={1} borderRadius="lg lg 0 0">
    <Heading size="sm" color="orange.300">
      Mijn Gegevens
    </Heading>
  </Box>
  <Box bg="orange.300" pt={4} pb={4} borderRadius="0 0 lg lg">
    <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={3}>
      {/* Fields with white bg on orange background */}
    </SimpleGrid>
  </Box>
</Box>
```

### Page Layout Container

```tsx
<Box bg="black" minH="100vh">
  <Box maxW="1200px" mx="auto" p={6}>
    <VStack spacing={6} align="stretch">
      {/* Page sections */}
    </VStack>
  </Box>
</Box>
```

---

## Table Patterns

### Standard Table (Dark Theme)

```tsx
<Box
  bg="gray.800"
  border="1px"
  borderColor="orange.400"
  borderRadius="md"
  overflow="auto"
  maxW="100%"
>
  <Table variant="simple" size="sm">
    <Thead>
      <Tr bg="gray.700">
        <Th color="orange.300" minW="120px">
          Kolom
        </Th>
        <Th color="orange.300" minW="80px">
          Status
        </Th>
        <Th color="orange.300" display={{ base: "none", md: "table-cell" }}>
          Details
        </Th>
        <Th color="orange.300" position="sticky" right={0} bg="gray.700">
          Acties
        </Th>
      </Tr>
    </Thead>
    <Tbody>
      <Tr color="white" _hover={{ bg: "gray.700" }}>
        <Td fontSize={{ base: "xs", md: "sm" }}>Data</Td>
        <Td>
          <Badge colorScheme="green">Actief</Badge>
        </Td>
        <Td display={{ base: "none", md: "table-cell" }}>Extra info</Td>
        <Td position="sticky" right={0} bg="gray.800">
          <HStack spacing={1}>
            <IconButton
              icon={<ViewIcon />}
              colorScheme="blue"
              size="xs"
              aria-label="Bekijken"
            />
            <IconButton
              icon={<EditIcon />}
              colorScheme="orange"
              size="xs"
              aria-label="Bewerken"
            />
            <IconButton
              icon={<DeleteIcon />}
              colorScheme="red"
              size="xs"
              aria-label="Verwijderen"
            />
          </HStack>
        </Td>
      </Tr>
    </Tbody>
  </Table>
</Box>
```

### Table Design Rules

- **Responsive column hiding**: `display={{ base: 'none', md: 'table-cell' }}`
- **Text truncation**: `<Text isTruncated maxW="200px">`
- **Sticky action columns**: `position="sticky" right={0}` with matching background
- **Financial data**: Use `<Badge>` with conditional colors (green for profit, red for loss)
- **Minimum column widths**: `minW="80px"` to `minW="200px"` based on content type

---

## Modal Patterns

### Standard Modal (Fixed Center)

```tsx
<Box
  position="fixed"
  top="50%"
  left="50%"
  transform="translate(-50%, -50%)"
  bg="orange.100"
  border="2px solid orange"
  borderRadius="lg"
  boxShadow="xl"
  maxHeight="80vh"
  overflowY="auto"
  zIndex={1000}
  p={6}
  w={{ base: "95%", md: "600px" }}
>
  <IconButton
    icon={<CloseIcon />}
    position="absolute"
    top={2}
    right={2}
    size="sm"
    aria-label="Sluiten"
  />
  {/* Modal content */}
</Box>
```

### Modal Overlay

```tsx
<Box
  position="fixed"
  top={0}
  left={0}
  right={0}
  bottom={0}
  bg="blackAlpha.600"
  zIndex={999}
  onClick={onClose}
/>
```

---

## Form Patterns

### Standard Form Layout

```tsx
<VStack spacing={4} align="stretch">
  <FormControl>
    <FormLabel color="orange.300" fontSize="sm" fontWeight="semibold">
      Veldnaam
    </FormLabel>
    <Input size="sm" bg="gray.700" borderColor="orange.400" color="white" />
  </FormControl>

  <FormControl>
    <FormLabel color="orange.300" fontSize="sm" fontWeight="semibold">
      Bedrag
    </FormLabel>
    <InputGroup size="sm">
      <InputLeftAddon bg="orange.300" color="black" fontWeight="bold">
        €
      </InputLeftAddon>
      <Input
        type="number"
        bg="gray.700"
        borderColor="orange.400"
        color="white"
      />
    </InputGroup>
  </FormControl>
</VStack>
```

### Save Button (Floating)

Only visible when the form has unsaved changes:

```tsx
{
  hasChanges && (
    <Box
      position="fixed"
      bottom={6}
      left="50%"
      transform="translateX(-50%)"
      zIndex={9999}
      bg="white"
      p={3}
      borderRadius="lg"
      boxShadow="xl"
      border="2px"
      borderColor="orange.500"
    >
      <IconButton
        icon={<EditIcon />}
        colorScheme="orange"
        borderRadius="full"
        p={3}
        aria-label="Opslaan"
        onClick={handleSave}
        isLoading={isSaving}
      />
    </Box>
  );
}
```

### Navigation Controls

```tsx
<HStack spacing={4} justify="center">
  <IconButton
    icon={<ChevronLeftIcon />}
    colorScheme="orange"
    aria-label="Vorige"
    isDisabled={currentIndex === 0}
  />
  <Text color="white">
    {currentIndex + 1} / {total}
  </Text>
  <IconButton
    icon={<ChevronRightIcon />}
    colorScheme="orange"
    aria-label="Volgende"
    isDisabled={currentIndex === total - 1}
  />
</HStack>
```

---

## Icon Standards

### Library Rule

Only use icons from `@chakra-ui/icons`. No custom SVGs or third-party icon libraries.

```tsx
import {
  ViewIcon,
  EditIcon,
  DeleteIcon,
  AddIcon,
  CopyIcon,
  SearchIcon,
  DownloadIcon,
  UploadIcon,
  AttachmentIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  CheckIcon,
  CloseIcon,
  CheckCircleIcon,
  WarningIcon,
  InfoIcon,
  QuestionIcon,
  SettingsIcon,
} from "@chakra-ui/icons";
```

### Full Icon Mapping Table

| Icon               | Color Scheme | Action/Context           |
| ------------------ | ------------ | ------------------------ |
| `ViewIcon`         | `blue`       | View / Read operations   |
| `EditIcon`         | `orange`     | Edit / Update operations |
| `DeleteIcon`       | `red`        | Delete operations        |
| `AddIcon`          | `green`      | Create / Add operations  |
| `CopyIcon`         | `teal`       | Duplicate / Copy         |
| `SearchIcon`       | `gray`       | Search functionality     |
| `DownloadIcon`     | `blue`       | Download / Export        |
| `UploadIcon`       | `purple`     | Upload / Import          |
| `AttachmentIcon`   | `gray`       | File attachments         |
| `ChevronLeftIcon`  | `orange`     | Previous navigation      |
| `ChevronRightIcon` | `orange`     | Next navigation          |
| `ChevronDownIcon`  | `gray`       | Expand / Dropdown        |
| `ChevronUpIcon`    | `gray`       | Collapse                 |
| `CheckIcon`        | `green`      | Confirm / Save           |
| `CloseIcon`        | `gray`       | Cancel / Close           |
| `CheckCircleIcon`  | `green`      | Success status           |
| `WarningIcon`      | `yellow`     | Warning status           |
| `InfoIcon`         | `blue`       | Information              |
| `QuestionIcon`     | `gray`       | Help                     |
| `SettingsIcon`     | `gray`       | Settings / Configuration |

### Icon Size Standards

| Context       | Size | Usage                      |
| ------------- | ---- | -------------------------- |
| Table actions | `xs` | Compact row-level buttons  |
| Card actions  | `sm` | Card header/footer buttons |
| Main actions  | `md` | Page-level primary actions |

### Icon Usage Rules

- Always include `aria-label` on `<IconButton>`
- Wrap icon buttons in `<Tooltip>` for discoverability
- Use `isLoading` prop for async action buttons
- Show disabled buttons with explanatory tooltips
- Group action buttons with `<HStack spacing={1}>` (tight) or `spacing={2}` (normal)

---

## Status Badge Mappings

### Member Status (`lid_status`)

| Status       | Color Scheme | Display Text |
| ------------ | ------------ | ------------ |
| `Actief`     | `green`      | Actief       |
| `Aangemeld`  | `yellow`     | Aangemeld    |
| `Opgezegd`   | `red`        | Opgezegd     |
| `Geschorst`  | `red`        | Geschorst    |
| `wachtRegio` | `orange`     | wachtRegio   |
| _(default)_  | `gray`       | —            |

### Membership Type (`lidmaatschap_type`)

| Type              | Color Scheme | Display Text    |
| ----------------- | ------------ | --------------- |
| `Gewoon lid`      | `blue`       | Gewoon lid      |
| `Gezins lid`      | `purple`     | Gezins lid      |
| `Erelid`          | `gold`       | Erelid          |
| `Donateur`        | `teal`       | Donateur        |
| `Gezins donateur` | `teal`       | Gezins donateur |
| `Sponsor`         | `orange`     | Sponsor         |
| _(default)_       | `gray`       | —               |

### Badge Implementation

```tsx
const statusColorMap: Record<string, string> = {
  Actief: "green",
  Aangemeld: "yellow",
  Opgezegd: "red",
  Geschorst: "red",
  wachtRegio: "orange",
};

<Badge colorScheme={statusColorMap[status] || "gray"} fontSize="xs">
  {status}
</Badge>;
```

---

## Accessibility Requirements

### WCAG AA Compliance

- **Contrast ratio**: Minimum 4.5:1 for normal text, 3:1 for large text (18px+ or 14px bold)
- **Focus indicators**: Visible focus ring on all interactive elements
- **Color independence**: Never convey information through color alone — pair with text or icons

### ARIA Standards

- All `<IconButton>` components must have `aria-label`
- Form fields must have associated `<FormLabel>` (or `aria-label` for icon-only inputs)
- Status changes must be announced via `aria-live` regions
- Modals must trap focus and return focus on close

### Keyboard Navigation

- All interactive elements reachable via Tab
- Escape closes modals and dropdowns
- Arrow keys navigate within menus and tables
- Enter/Space activates buttons and links

### Semantic HTML

- Proper heading hierarchy: `h1` → `h2` → `h3` (never skip levels)
- Use `<nav>`, `<main>`, `<aside>` landmarks
- Tables use `<thead>`, `<th scope="col">` for screen readers
- Lists use `<ul>`/`<ol>` for grouped items

### Touch Targets

- Minimum 44×44px for all interactive elements on mobile
- Adequate spacing between adjacent touch targets (minimum 8px gap)

### Screen Reader Considerations

- Status badges include text content (not color-only)
- Loading states announced: `aria-busy="true"` on containers
- Dynamic content updates use `aria-live="polite"` or `aria-live="assertive"`
- Icon-only buttons always have descriptive `aria-label`

---

## Dark Theme Patterns (Default)

The admin and member views use dark theme by default.

| Element         | Token/Value     | Notes                         |
| --------------- | --------------- | ----------------------------- |
| Page background | `bg="black"`    | Full viewport                 |
| Card container  | `bg="gray.800"` | With `orange.400` border      |
| Card header     | `bg="gray.700"` | With `orange.300` text        |
| Table header    | `bg="gray.700"` | With `orange.300` column text |
| Table rows      | `color="white"` | With `orange.500` hover       |
| Form labels     | `orange.300`    | On dark backgrounds           |
| Form inputs     | `bg="gray.700"` | With `orange.400` borders     |
| Accent text     | `orange.300`    | Headers, links, emphasis      |

---

## Responsive Design Rules

### Breakpoints (Chakra UI defaults)

| Token  | Width  | Target        |
| ------ | ------ | ------------- |
| `base` | 0px    | Mobile phones |
| `sm`   | 480px  | Large phones  |
| `md`   | 768px  | Tablets       |
| `lg`   | 992px  | Laptops       |
| `xl`   | 1280px | Desktops      |

### Mobile-First Patterns

```tsx
// Grid columns
<SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={3}>

// Font sizing
<Text fontSize={{ base: 'xs', md: 'sm' }}>

// Column visibility
<Th display={{ base: 'none', md: 'table-cell' }}>

// Conditional text
{isMobile ? 'Nieuw' : 'Nieuw Item'}
```

### iOS-Specific Rules

- Input font size must be ≥16px on mobile to prevent auto-zoom
- Use `-webkit-overflow-scrolling: touch` for smooth scroll containers (Chakra handles this)

---

## Development Rules

1. **Chakra UI only** — Use theme tokens and components, no custom CSS or `sx` prop for basic styling
2. **Dark theme default** — Admin and member views always render in dark theme
3. **Consistent icon colors** — Same icon + color for the same action everywhere
4. **Visual state communication** — Colors and cursors, never text badges
5. **Mobile-first** — Design for `base` breakpoint, enhance upward
6. **Performance** — Memoize expensive renders, lazy-load heavy components
7. **Utility-first** — Prefer Chakra props (`p={6}`, `color="orange.500"`) over theme extensions

---

## Cross-References

- **Authentication patterns**: See [`.kiro/steering/authentication.md`](../../.kiro/steering/authentication.md) for auth UI flows
- **Project structure**: See [`.kiro/steering/structure.md`](../../.kiro/steering/structure.md) for file organization
- **Tech stack**: See [`.kiro/steering/tech.md`](../../.kiro/steering/tech.md) for framework versions and build tools
- **DynamoDB/AWS**: See [`.kiro/steering/aws-dynamodb.md`](../../.kiro/steering/aws-dynamodb.md) for backend data patterns
