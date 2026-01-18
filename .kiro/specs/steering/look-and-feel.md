# H-DCN Portal Look and Feel Guidelines

This document defines the visual design system and UI/UX principles for the H-DCN portal. These guidelines ensure consistency across all components and provide rules for building new features.

## Design System Foundation

### Color Palette

**Primary Colors**

- **H-DCN Orange**: `#f56500` (Primary brand color)
- **H-DCN Orange Hover**: `#e55a00` (Interactive states)
- **H-DCN Orange Light**: `#ff7a1a` (Accents and highlights)

**Neutral Colors**

- **Background Primary**: `#ffffff` (Main content areas)
- **Background Secondary**: `#f7fafc` (Card backgrounds, sections)
- **Background Tertiary**: `#edf2f7` (Input backgrounds, disabled states)
- **Text Primary**: `#2d3748` (Main text content)
- **Text Secondary**: `#4a5568` (Supporting text, labels)
- **Text Muted**: `#718096` (Help text, placeholders)
- **Border**: `#e2e8f0` (Card borders, dividers)

**Status Colors**

- **Success**: `#38a169` (Active status, confirmations)
- **Warning**: `#d69e2e` (Pending status, cautions)
- **Error**: `#e53e3e` (Errors, inactive status)
- **Info**: `#3182ce` (Information, neutral status)

**Dark Theme Colors**

- **Background Primary**: `#000000` / **Secondary**: `#1a1a1a`
- **Text Primary**: `#ffffff` / **Secondary**: `#cccccc`
- **Accent**: `#f56500` (H-DCN Orange)

### Typography

**Font Stack**: System fonts (`-apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto"...`)

**Font Sizes (Chakra UI Scale)**

- **2xl** (24px) - Page titles
- **lg** (18px) - Section headers
- **md** (16px) - Card headers
- **sm** (14px) - Main content
- **xs** (12px) - Help text, captions

### Spacing System (Chakra UI Scale)

- **xs**: `1` (4px) - **sm**: `2` (8px) - **md**: `4` (16px) - **lg**: `6` (24px) - **xl**: `8` (32px) - **2xl**: `12` (48px)

## Design Principles

### Field State Communication

- **Visual Cues Only**: Use colors, backgrounds, and cursors instead of text badges ("Bewerkbaar/Alleen lezen")
- **Editable Fields**:
  - Background: `bg="white"` (light theme) or `bg="gray.600"` (dark theme)
  - Border: `borderColor="gray.300"` with `_hover={{ borderColor: "orange.400" }}` and `_focus={{ borderColor: "orange.500", boxShadow: "0 0 0 1px orange.500" }}`
  - Cursor: `cursor="text"` for text inputs
  - Placeholder: `_placeholder={{ color: "gray.400" }}` (light) or `_placeholder={{ color: "gray.300" }}` (dark)
- **Read-only Fields**:
  - Background: `bg="gray.100"` (light theme) or `bg="gray.700"` (dark theme)
  - Border: `borderColor="gray.300"` (no hover states)
  - Cursor: `cursor="default"`
  - Text Color: `color="gray.600"` (light) or `color="gray.300"` (dark)
- **Help Text Strategy**:
  - **Placeholders**: Show help text as `placeholder` in empty fields
  - **Tooltips**: Use `<Tooltip label="Help text">` on field labels for additional context
  - **No Persistent Text**: Avoid showing help text permanently under fields

### Member Self-Service View Patterns

Based on the "Mijn Gegevens" (My Account) implementation, these patterns apply to member-facing data views:

- **Page Layout**:

  - Dark theme: `bg="black" minH="100vh"`
  - Container: `maxW="1200px" mx="auto" p={6}`
  - Section spacing: `VStack spacing={6}`

- **Section Cards**:

  - Container: `bg="gray.800"` with `borderColor="orange.400" border="1px" borderRadius="lg"`
  - Header: `bg="gray.700"` with `py={1}` for compact height
  - Header text: `size="sm" color="orange.300"` (smaller, not bold)
  - Header corners: `borderRadius="lg lg 0 0"`
  - Content area: `bg="orange.300"` (vibrant orange background)
  - Content corners: `borderRadius="0 0 lg lg"`
  - Content padding: `pt={4} pb={4}`

- **Field Layout**:

  - Grid: `SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={3}`
  - Field spacing: `mb={1}` (compact vertical spacing)
  - Label styling: `mb={0} color="gray.700" fontWeight="semibold" fontSize="sm"`

- **Field States on Orange Background**:

  - **Editable Fields**: White backgrounds with orange focus states
  - **Read-only Fields**: `bg="gray.100" borderColor="gray.300" color="gray.600"`
  - **Field Size**: `size="sm" fontSize="sm"` for compact appearance
  - **Input Heights**: `minH="32px"` for read-only fields

- **Save Button Pattern**:

  - **Conditional Display**: Only show when `hasChanges` is true
  - **Positioning**: `position="fixed" bottom={6} left="50%" transform="translateX(-50%)" zIndex={9999}`
  - **Styling**: White container with orange border, circular orange button
  - **Icon Only**: `<EditIcon />` without text for minimal footprint
  - **Container**: `bg="white" p={3} borderRadius="lg" boxShadow="xl" border="2px" borderColor="orange.500"`
  - **Button**: `colorScheme="orange" borderRadius="full" p={3}`

- **Visual Hierarchy**:
  - **No Text Badges**: Use visual cues (colors, backgrounds, cursors) instead of "Bewerkbaar/Alleen lezen"
  - **Membership Section First**: Always display membership information at the top
  - **Administrative Section Hidden**: Hide from member self-service views
  - **Compact Headers**: Reduced padding and smaller text for section headers

### Card and Container Patterns (Based on Product Management & Event Editing)

- **Modal Cards**:
  - Background: `bg="orange.100"` with `border="2px solid orange"`
  - Positioning: `position="fixed"` with `top="50%" left="50%" transform="translate(-50%, -50%)"`
  - Shadow: `boxShadow="xl"` for depth
  - Size constraints: `maxHeight="80vh"` with `overflowY="auto"`
  - Close button: `position="absolute" top={2} right={2}`
- **Standard Cards**:
  - Orange headings (`color="orange.500"` for light theme, `color="orange.400"` for dark theme)
  - Consistent CardHeader/CardBody structure
  - Background: `bg="gray.800"` (dark theme) with `borderColor="orange.400"`
- **Page Layout**:
  - Max width 1200px, centered with `mx="auto"`
  - Padding: `p={6}` for main containers
  - Dark theme: `bg="black" minH="100vh"`
- **Section Spacing**: Use VStack with `spacing={6}` for major sections
- **Form Controls**:
  - Input groups with `InputLeftAddon` for currency (`bg="orange.300" color="black" fontWeight="bold"`)
  - Field spacing: `VStack spacing={4}` within forms
  - Navigation buttons: Adjacent to content with `HStack spacing={4}`

### Dark Theme Patterns

- **Container**: Gray.800 background with orange.400 borders
- **Headers**: Gray.700 background with orange.300 text
- **Rows**: White text with orange.500 hover states
- **Form Labels**: Orange.300 for dark theme forms
- **Inputs**: Gray.700 background with orange.400 borders

### Table Design Rules (Based on Product Management Patterns)

- **Container Styling**:
  - Background: `bg="gray.800"` with `border="1px"` and `borderColor="orange.400"`
  - Border radius: `borderRadius="md"`
  - Overflow handling: `overflow="auto"` with `maxW="100%"`
- **Header Styling**:
  - Background: `bg="gray.700"`
  - Text color: `color="orange.300"`
  - Minimum widths: `minW="80px"` to `minW="200px"` based on content
- **Row Styling**:
  - Text color: `color="white"`
  - Font size: `fontSize={{ base: 'xs', md: 'sm' }}` for responsive typography
- **Responsive Hiding**: Hide non-essential columns on mobile (`display={{ base: 'none', md: 'table-cell' }}`)
- **Typography Scaling**: Smaller fonts on mobile (`fontSize={{ base: 'xs', md: 'sm' }}`)
- **Text Truncation**: Use `isTruncated` with `maxW` for predictable overflow
- **Sticky Actions**: Position action columns with `position="sticky" right={0}` and matching background
- **Financial Data**: Use Badge components with conditional colors (green/red for profit/loss)
- **Action Button Spacing**: Use `HStack spacing={1}` for tight icon button groups

### Modal and Navigation Patterns

- **Fixed Positioning**: Center modals with `transform="translate(-50%, -50%)"`
- **Navigation Controls**: Place prev/next buttons adjacent to content they control
- **Hierarchical Selection**: Use indentation (`pl={6}`) and different button sizes
- **Collapsible Sections**: Use Collapse component with chevron icons

### Icon Standards

#### Icon Library Rule

- **Use Chakra UI Icons Only**: Import icons from `@chakra-ui/icons` package
- **No Custom Icons**: Avoid custom SVGs or other icon libraries unless absolutely necessary
- **Consistent Import**: Always import from the same source for maintainability

```typescript
import {
  ViewIcon,
  EditIcon,
  DeleteIcon,
  AddIcon,
  CopyIcon,
  SearchIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  ChevronDownIcon,
  CheckIcon,
  CloseIcon,
  CheckCircleIcon,
  WarningIcon,
  InfoIcon,
  QuestionIcon,
  SettingsIcon,
  DownloadIcon,
  UploadIcon,
  AttachmentIcon,
} from "@chakra-ui/icons";
```

#### CRUD Operation Icons

- **ViewIcon** (blue) - `colorScheme="blue"` - View/Read operations
- **EditIcon** (orange) - `colorScheme="orange"` - Edit/Update operations
- **DeleteIcon** (red) - `colorScheme="red"` - Delete operations
- **AddIcon** (green) - `colorScheme="green"` - Create/Add operations
- **CopyIcon** (teal) - `colorScheme="teal"` - Duplicate/Copy operations

#### Secondary Action Icons

- **SearchIcon** (gray) - `colorScheme="gray"` - Search functionality
- **DownloadIcon** (blue) - `colorScheme="blue"` - Download/Export
- **UploadIcon** (purple) - `colorScheme="purple"` - Upload/Import
- **AttachmentIcon** (gray) - `colorScheme="gray"` - File attachments

#### Navigation Icons

- **ChevronLeftIcon/RightIcon** (orange) - `colorScheme="orange"` - Previous/Next navigation
- **ChevronDownIcon/UpIcon** (gray) - `colorScheme="gray"` - Expand/Collapse

#### Status and Feedback Icons

- **CheckIcon** (green) - `colorScheme="green"` - Confirm/Save
- **CloseIcon** (gray) - `colorScheme="gray"` - Cancel/Close
- **CheckCircleIcon** (green) - `colorScheme="green"` - Success status
- **WarningIcon** (yellow) - `colorScheme="yellow"` - Warning status
- **InfoIcon** (blue) - `colorScheme="blue"` - Information
- **QuestionIcon** (gray) - `colorScheme="gray"` - Help
- **SettingsIcon** (gray) - `colorScheme="gray"` - Settings

### Icon Usage Rules

- **Consistency**: Always use the same icon for the same action across the application
- **Color Semantics**: Follow the color scheme standards (orange for edit, red for delete, etc.)
- **Size Standards**: Use `xs` for table actions, `sm` for cards, `md` for main actions
- **Accessibility**: Always include `aria-label` and `title` attributes
- **Tooltips**: Wrap icon buttons in Tooltip components for better UX
- **Loading States**: Use `isLoading` prop for async actions
- **Disabled States**: Show disabled buttons with explanatory tooltips
- **Responsive**: Use responsive sizing and text for mobile optimization
- **Spacing**: Use consistent spacing (spacing={1} for tight groups, spacing={2} for normal)

## Status Badge Color Mapping

### Member Status

- **Actief**: green
- **Aangemeld**: yellow
- **Opgezegd**: red
- **Geschorst**: red
- **wachtRegio**: orange
- **Default**: gray

### Membership Type

- **Gewoon lid**: blue
- **Gezins lid**: purple
- **Erelid**: gold
- **Donateur**: teal
- **Gezins donateur**: teal
- **Sponsor**: orange
- **Default**: gray

## Mobile Responsiveness Rules

- **Touch Targets**: 44px minimum height for all interactive elements on mobile
- **Typography**: 16px minimum font size on mobile inputs (prevents iOS zoom)
- **Tables**: Horizontal scrolling with smooth touch scrolling
- **Grids**: Responsive patterns `{{ base: 1, md: 2 }}` for layout adaptation
- **Navigation**: Shorter text on mobile (`{isMobile ? 'New' : 'New Item'}`)

## Accessibility Requirements

- **WCAG AA Compliance**: 4.5:1 contrast ratio for text
- **ARIA Labels**: Proper labels for all interactive elements
- **Keyboard Navigation**: Support with visible focus indicators
- **Semantic HTML**: Proper heading hierarchy (h1 → h2 → h3)
- **Screen Readers**: Status information announced appropriately

## Development Rules

1. **Consistency First** - Use existing Chakra UI components before creating custom ones
2. **Responsive Design** - Design mobile-first, enhance for desktop
3. **Accessibility** - Include proper ARIA labels and test with screen readers
4. **Performance** - Minimize re-renders with proper memoization
5. **Utility-First** - Use Chakra UI props for styling (`p={6}`, `color="orange.500"`)
6. **Theme Consistency** - Use Chakra UI theme tokens for colors, spacing, typography
7. **Field State Clarity** - Use visual cues (colors, backgrounds, cursors) instead of text badges
8. **Help Text Strategy** - Show help text as placeholders or tooltips, not persistent text under fields
9. **Icon Consistency** - Always use Chakra UI icons with consistent color schemes for actions

## Quality Assurance Checklist

### Visual Testing

- Test components in all supported browsers
- Verify responsive behavior on multiple devices
- Check color contrast and accessibility compliance
- Validate print styles if applicable

### Functional Testing

- Test all interactive elements
- Verify form validation and submission
- Check error states and loading states
- Test keyboard navigation paths

### Code Review Requirements

- Follows established component patterns
- Uses consistent spacing and typography
- Implements proper responsive behavior
- Maintains accessibility standards
- No unnecessary re-renders
- Proper component memoization
- Optimized bundle size impact
