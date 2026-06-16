# Remove Image Editor Bugfix Design

## Overview

The "Image Editor" feature in the webshop product management interface is non-functional and must be completely removed. The feature consists of three components (`ImageEditor.tsx`, `AdvancedImageEditor.tsx`, `ImageEditorModal.tsx`) in `frontend/src/modules/products/components/`. Two are dead code, and one is wired into `ProductTable.tsx` via a modal triggered by an "Image Editor" button. The fix involves deleting all three component files and removing the button, modal, and related imports from `ProductTable.tsx`, while preserving all product table functionality.

## Glossary

- **Bug_Condition (C)**: The presence of the "Image Editor" button and non-functional modal in ProductTable, and the existence of dead-code image editor component files
- **Property (P)**: The product table renders without any image editor UI elements, and the three image editor files no longer exist in the codebase
- **Preservation**: The product table continues to display all columns, handle row selection, render custom actions, and the product data model (including `images` array) remains unchanged
- **ProductTable**: The component at `frontend/src/modules/products/components/ProductTable.tsx` that renders the product management table
- **Dead code**: Components (`AdvancedImageEditor.tsx`, `ImageEditorModal.tsx`) that are not imported or referenced anywhere in the codebase

## Bug Details

### Bug Condition

The bug manifests when the `ProductTable` component renders — it always shows an "Image Editor" button that opens a non-functional modal. Additionally, the codebase contains two entirely unused component files related to image editing.

**Formal Specification:**

```
FUNCTION isBugCondition(input)
  INPUT: input of type { component: string, codebaseFiles: string[] }
  OUTPUT: boolean

  RETURN (input.component == "ProductTable"
          AND rendersImageEditorButton(input.component)
          AND rendersImageEditorModal(input.component))
         OR fileExists("ImageEditor.tsx", input.codebaseFiles)
         OR fileExists("AdvancedImageEditor.tsx", input.codebaseFiles)
         OR fileExists("ImageEditorModal.tsx", input.codebaseFiles)
END FUNCTION
```

### Examples

- **Webmaster opens product management page** → An "Image Editor" button appears above the product table that opens a non-functional 629-line modal. Expected: no such button exists.
- **Developer inspects `AdvancedImageEditor.tsx` (668 lines)** → File exists but is never imported anywhere. Expected: file does not exist.
- **Developer inspects `ImageEditorModal.tsx`** → File exists but is never imported anywhere. Expected: file does not exist.
- **Webmaster clicks "Image Editor" button** → A large modal opens with image processing UI that provides no useful functionality. Expected: button does not exist, so this interaction is impossible.

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**

- Product table displays all columns (ID, Categorie, Naam, Prijs, Status, Actions) correctly
- Clicking a product row triggers the `onSelect` handler with the selected product
- The `renderActions` prop continues to render custom action buttons per row
- The `showStatusColumn` prop continues to toggle the Status column
- The product data model `images` array in DynamoDB remains untouched
- Both consumers (`ProductManagementPage.tsx` and `Dashboard.tsx`) continue to work with the same `ProductTable` interface

**Scope:**
All product table interactions that do NOT involve the Image Editor button or modal should be completely unaffected by this fix. This includes:

- Row clicks and selection
- Column rendering and responsive behavior
- Action button rendering via `renderActions`
- Status badge display
- Table styling and hover effects

## Hypothesized Root Cause

This is not a traditional code bug but rather a feature that was built (or partially built) and never completed or connected to a working backend. The root causes of the current state:

1. **No backend support**: There is no Lambda handler for image processing, no S3 upload endpoint for edited images, and no API route that the ImageEditor component could call
2. **Incomplete feature delivery**: The `AdvancedImageEditor` and `ImageEditorModal` components were written but never integrated into any page or workflow
3. **Dead code accumulation**: The three files (totalling ~1300+ lines) were left in the codebase without cleanup
4. **UI clutter**: The "Image Editor" button was left in `ProductTable` despite the feature being non-functional, confusing administrators

## Correctness Properties

Property 1: Bug Condition - Image Editor UI Removed

_For any_ render of the `ProductTable` component (with any valid combination of props), the output SHALL NOT contain an "Image Editor" button, SHALL NOT import or reference the `ImageEditor` component, and SHALL NOT render a modal with image editing functionality.

**Validates: Requirements 2.1, 2.2**

Property 2: Preservation - Product Table Functionality Unchanged

_For any_ valid `products` array and prop combination (`onSelect`, `renderActions`, `showStatusColumn`), the `ProductTable` component SHALL produce the same table output (columns, rows, click handlers, action buttons, status badges) as the original component minus the Image Editor button and modal.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4**

## Fix Implementation

### Changes Required

**File**: `frontend/src/modules/products/components/ProductTable.tsx`

**Specific Changes**:

1. **Remove ImageEditor import**: Delete `import ImageEditor from './ImageEditor';`
2. **Remove Modal imports**: Remove `Modal, ModalOverlay, ModalContent, ModalHeader, ModalCloseButton, ModalBody` from Chakra UI import (if not used elsewhere in the file)
3. **Remove useDisclosure**: Remove `useDisclosure` from Chakra import and the `const { isOpen, onOpen, onClose } = useDisclosure();` line
4. **Remove Button import**: Remove `Button` from Chakra import (only used for the Image Editor button)
5. **Remove Image Editor button**: Delete the `<HStack mb={4} justify="flex-end">` block containing the "Image Editor" button
6. **Remove Modal JSX**: Delete the entire `<Modal isOpen={isOpen} ...>` block at the bottom of the component
7. **Clean up Fragment**: If the Fragment wrapper (`<>...</>`) is no longer needed (only one root element remains), simplify to a single `<Box>` root

**Files to delete**:

- `frontend/src/modules/products/components/ImageEditor.tsx`
- `frontend/src/modules/products/components/AdvancedImageEditor.tsx`
- `frontend/src/modules/products/components/ImageEditorModal.tsx`

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, confirm the current broken state exists (image editor elements are present), then verify the removal is complete and no regressions are introduced.

### Exploratory Bug Condition Checking

**Goal**: Confirm the image editor elements exist in the current unfixed code before making changes.

**Test Plan**: Inspect the source code and render the ProductTable to verify the Image Editor button and modal are present. Run these checks on the UNFIXED code to document the current state.

**Test Cases**:

1. **Button Presence Test**: Render ProductTable and assert an "Image Editor" button is present (will pass on unfixed code, confirming the bug)
2. **Modal Render Test**: Click the Image Editor button and assert a modal with ImageEditor component opens (will pass on unfixed code)
3. **Dead Code File Test**: Assert that `AdvancedImageEditor.tsx` and `ImageEditorModal.tsx` exist on disk but have zero imports (confirms dead code)
4. **Import Chain Test**: Assert `ProductTable.tsx` imports from `./ImageEditor` (confirms coupling)

**Expected Counterexamples**:

- The button renders in every ProductTable instance across both consuming pages
- The modal opens but provides no actionable functionality (no save endpoint)

### Fix Checking

**Goal**: Verify that after the fix, no image editor elements remain.

**Pseudocode:**

```
FOR ALL renders of ProductTable with valid props DO
  result := render(ProductTable_fixed, props)
  ASSERT NOT containsElement(result, "Image Editor" button)
  ASSERT NOT containsElement(result, Modal with ImageEditor)
  ASSERT NOT fileExists("ImageEditor.tsx")
  ASSERT NOT fileExists("AdvancedImageEditor.tsx")
  ASSERT NOT fileExists("ImageEditorModal.tsx")
END FOR
```

### Preservation Checking

**Goal**: Verify that all product table functionality remains intact after removing image editor code.

**Pseudocode:**

```
FOR ALL valid props (products, onSelect, renderActions, showStatusColumn) DO
  ASSERT ProductTable_fixed renders correct columns (ID, Categorie, Naam, Prijs, Status, Actions)
  ASSERT ProductTable_fixed calls onSelect(product) on row click
  ASSERT ProductTable_fixed renders renderActions(product) in action column
  ASSERT ProductTable_fixed shows/hides Status column based on showStatusColumn prop
END FOR
```

**Testing Approach**: For this removal-type fix, the preservation testing is primarily structural — verifying the component interface and output remain unchanged for all non-image-editor behavior. Property-based testing can generate random product arrays to verify table rendering is stable.

**Test Plan**: Render ProductTable with various product configurations and verify all columns, click handlers, and action renderers work correctly.

**Test Cases**:

1. **Column Rendering Preservation**: Verify all table columns render correctly with varying product data
2. **Row Click Preservation**: Verify `onSelect` is called with the correct product on row click
3. **Action Buttons Preservation**: Verify `renderActions` continues to render per-row actions
4. **Status Column Toggle Preservation**: Verify `showStatusColumn` prop controls Status column visibility

### Unit Tests

- Test ProductTable renders without "Image Editor" button
- Test ProductTable renders all expected columns
- Test ProductTable calls `onSelect` on row click
- Test ProductTable renders `renderActions` output in action cells
- Test ProductTable `showStatusColumn` prop works correctly
- Test that importing ProductTable does not pull in any image editor code

### Property-Based Tests

- Generate random arrays of Product objects and verify table renders correct number of rows
- Generate random product data with varying `active` states and verify badge rendering
- Generate random prop combinations and verify no crashes or missing elements

### Integration Tests

- Verify ProductManagementPage renders ProductTable without image editor elements
- Verify Dashboard page renders ProductTable without image editor elements
- Verify the full product management workflow (list, select, edit) works without image editor
