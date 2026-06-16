# Dark Theme Consistency Fix - Bugfix Design

## Overview

Multiple frontend components in the H-DCN portal's product management and webshop modules use hardcoded light-theme styling (white/light-gray backgrounds, dark text colors) that renders content invisible or unreadable on the application's standard dark background (`bg="black"`). The fix involves replacing all light-theme color tokens with the established dark theme standard defined in the look-and-feel steering file: `bg="gray.700"` for inputs, `color="white"` for text, `borderColor="gray.600"` for borders, and `bg="gray.800"` for cards/panels.

## Glossary

- **Bug_Condition (C)**: A component renders using light-theme color tokens (white/gray.50 backgrounds, gray.700/gray.800 text) on the dark-themed page
- **Property (P)**: All affected components SHALL use dark-theme tokens per the look-and-feel standard, ensuring readability (WCAG AA 4.5:1 contrast)
- **Preservation**: Existing dark-themed components (OrderItemFieldsEditor, report components, action buttons) must remain unchanged
- **VariantActionPanel**: Sub-component in `VariantSchemaEditor.tsx` that renders add/remove variant controls with Select dropdowns
- **CollapsibleSection**: Sub-component in `ProductCard.tsx` that renders expandable sections with a content area
- **CategorySelector**: Sub-component in `ProductCard.tsx` that renders the product category tree picker

## Bug Details

### Bug Condition

The bug manifests when any of the four affected components render their UI elements on the dark-themed page. The components use hardcoded light-theme color tokens (inherited from initial development or copy-paste from light-theme examples) that produce near-zero contrast against the dark page background.

**Formal Specification:**

```
FUNCTION isBugCondition(component, element)
  INPUT: component of type ReactComponent, element of type StyledElement
  OUTPUT: boolean

  RETURN component IN ['VariantActionPanel', 'PurchaseRulesEditor', 'ProductCard.CollapsibleSection',
                        'ProductCard.CategorySelector', 'ItemFieldsForm']
         AND (
           element.bg IN ['white', 'gray.50', 'gray.100']
           OR element.color IN ['gray.600', 'gray.700', 'gray.800']
           OR element.borderColor IN ['gray.200', 'gray.300']
         )
         AND element.isRenderedOnDarkBackground = true
END FUNCTION
```

### Examples

- **VariantActionPanel**: Panel renders with `bg="gray.50"` and `borderColor="gray.300"` → nearly invisible on `bg="black"` page. Text uses `color="gray.700"` → unreadable against gray.50 on dark background.
- **PurchaseRulesEditor**: All `FormLabel` elements use `color="gray.800"` → invisible on dark page. `NumberInputField` and `Select` use `color="gray.800"` → text unreadable.
- **ProductCard CollapsibleSection**: Content area uses `bg="white"` → jarring bright flash within dark layout. CategorySelector uses `bg="gray.50"` with `color="gray.700"` headers.
- **ItemFieldsForm**: Item containers use `borderColor="gray.200"` → borders invisible on dark background.

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**

- The VariantSchemaEditor axis Input fields (outside VariantActionPanel) already use `bg="gray.700"`, `color="white"`, `borderColor="gray.500"` — these must remain unchanged
- The OrderItemFieldsEditor already uses `bg="gray.800"` cards with `borderColor="gray.600"` — must remain unchanged
- Report components (OrdersReport, ProductsReport, StockMovementsReport) already use correct dark tokens — must remain unchanged
- Orange-themed action buttons (`colorScheme="orange"`) and section headings (`color="orange.300"`) must remain unchanged
- Error/success/status feedback colors (red.500, green, orange) must remain unchanged
- The CollapsibleSection header button already uses `bg="gray.700"` and `color="white"` — this must remain unchanged
- The CategoryDisplay component already uses `bg="gray.600"` with `color="white"` — must remain unchanged

**Scope:**
All components and elements that already follow the dark theme standard are completely unaffected. Only the specific light-theme tokens listed in the bug condition are replaced.

## Hypothesized Root Cause

Based on analysis of the source files, the root causes are:

1. **Copy-paste from Chakra UI defaults**: The VariantActionPanel and PurchaseRulesEditor were developed using Chakra UI's default light-theme color tokens without adapting them to the project's dark theme standard.

2. **Inconsistent development phases**: The CollapsibleSection content area (`bg="white"`) and CategorySelector (`bg="gray.50"`) were likely written before the look-and-feel standard was established, while their header buttons were updated later.

3. **Missing explicit styling on ItemFieldsForm**: The ItemFieldsForm uses `borderColor="gray.200"` without explicit background/text colors, relying on Chakra defaults that assume a light background.

4. **No theme enforcement mechanism**: The project uses inline Chakra props rather than a centralized theme override, making it easy for individual components to drift from the standard.

## Correctness Properties

Property 1: Bug Condition - Dark Theme Token Application

_For any_ component element where the bug condition holds (light-theme tokens are used on a dark background), the fixed component SHALL render using the dark theme standard tokens: `bg="gray.700"` for inputs, `bg="gray.800"` for panels/cards, `color="white"` or `color="gray.300"` for text, and `borderColor="gray.600"` for borders, achieving WCAG AA contrast on the dark page.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9**

Property 2: Preservation - Existing Dark Theme Components Unchanged

_For any_ component element where the bug condition does NOT hold (already using dark theme tokens or in an unaffected component), the fixed code SHALL produce exactly the same rendered styling as the original code, preserving all existing dark-themed appearance for OrderItemFieldsEditor, report components, correctly-styled Input fields, action buttons, and status indicators.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

## Fix Implementation

### Changes Required

**File**: `frontend/src/modules/products/components/VariantSchemaEditor.tsx`

**Function**: `VariantActionPanel`

**Specific Changes**:

1. **Panel container**: Change `bg="gray.50"` → `bg="gray.800"`, `borderColor="gray.300"` → `borderColor="gray.600"`
2. **Title text**: Change `color="gray.700"` → `color="white"`
3. **Description text**: Change `color="gray.500"` → `color="gray.400"`
4. **Axis name labels**: Change `color="gray.600"` → `color="gray.300"`
5. **Select dropdowns**: Add `bg="gray.700"`, `borderColor="gray.600"`, `color="white"`, and style `<option>` elements with `style={{ background: '#2D3748', color: 'white' }}`

---

**File**: `frontend/src/modules/products/components/PurchaseRulesEditor.tsx`

**Function**: `PurchaseRulesEditor`

**Specific Changes**:

1. **All FormLabel elements**: Change `color="gray.800"` → `color="gray.300"`
2. **All NumberInputField elements**: Change `color="gray.800"` → `color="white"`, add `bg="gray.700"`, `borderColor="gray.600"`, `_placeholder={{ color: 'gray.400' }}`
3. **Select element**: Change `color="gray.800"` → `color="white"`, add `bg="gray.700"`, `borderColor="gray.600"`, style `<option>` elements with dark background

---

**File**: `frontend/src/modules/products/components/ProductCard.tsx`

**Function**: `CollapsibleSection` and `CategorySelector`

**Specific Changes**:

1. **CollapsibleSection content area**: Change `bg="white"` → `bg="gray.800"`
2. **CategorySelector container**: Change `bg="gray.50"` → `bg="gray.800"`, `borderColor="gray.200"` → `borderColor="gray.600"`
3. **CategorySelector title**: Change `color="gray.700"` → `color="white"`
4. **CategorySelector buttons**: Ensure ghost buttons have `color="white"` and `_hover={{ bg: 'gray.700' }}`
5. **Selected button highlights**: Change `bg="orange.200"` / `bg="orange.300"` to use `bg="orange.600"` / `bg="orange.700"` for dark-theme contrast (with white text)

---

**File**: `frontend/src/modules/webshop/components/ItemFieldsForm.tsx`

**Function**: `ItemFieldsForm`

**Specific Changes**:

1. **Item container Box**: Change `borderColor="gray.200"` → `borderColor="gray.600"`
2. **Heading**: Add `color="white"` to item label heading
3. **Input/Select/NumberInput fields**: Add `bg="gray.700"`, `borderColor="gray.600"`, `color="white"` to all field renderers in `renderFieldInput`
4. **FormLabel**: Add `color="gray.300"` to labels

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the incorrect styling on unfixed code, then verify the fix applies correct tokens and preserves existing behavior.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the light-theme tokens are present BEFORE implementing the fix. Confirm the root cause by inspecting rendered component props.

**Test Plan**: Write React Testing Library tests that render each affected component and assert that specific style props match the dark theme standard. Run on UNFIXED code to confirm failures.

**Test Cases**:

1. **VariantActionPanel container test**: Render VariantActionPanel, assert container has `bg="gray.800"` (will fail — has `gray.50`)
2. **PurchaseRulesEditor labels test**: Render PurchaseRulesEditor, assert FormLabels have `color="gray.300"` (will fail — has `gray.800`)
3. **CollapsibleSection content test**: Render ProductCard with CollapsibleSection, assert content Box has `bg="gray.800"` (will fail — has `white`)
4. **ItemFieldsForm border test**: Render ItemFieldsForm, assert container has `borderColor="gray.600"` (will fail — has `gray.200`)

**Expected Counterexamples**:

- Components render with light-theme tokens that fail contrast assertions
- Possible causes: hardcoded light tokens, missing explicit dark styling, Chakra defaults

### Fix Checking

**Goal**: Verify that for all affected component elements, the fixed components render with dark theme standard tokens.

**Pseudocode:**

```
FOR ALL element WHERE isBugCondition(component, element) DO
  result := render(fixedComponent)
  ASSERT element.bg IN ['gray.700', 'gray.800']
  ASSERT element.color IN ['white', 'gray.300', 'gray.400']
  ASSERT element.borderColor IN ['gray.600', 'gray.500', 'orange.400']
END FOR
```

### Preservation Checking

**Goal**: Verify that for all components/elements where the bug condition does NOT hold, the fixed code renders identically to the original.

**Pseudocode:**

```
FOR ALL element WHERE NOT isBugCondition(component, element) DO
  ASSERT renderProps_original(element) = renderProps_fixed(element)
END FOR
```

**Testing Approach**: Snapshot testing and prop assertions are recommended for preservation checking because:

- They capture the exact rendered output of unaffected components
- They detect any unintended style prop changes to preserved elements
- They provide clear diffs if regression occurs

**Test Plan**: Capture rendered styles of UNFIXED code for unaffected elements (OrderItemFieldsEditor, report components, axis Input fields), then assert these remain identical after the fix.

**Test Cases**:

1. **VariantSchemaEditor axis Inputs preservation**: Verify axis name/value Inputs retain `bg="gray.700"`, `color="white"`, `borderColor="gray.500"` after fix
2. **CollapsibleSection header preservation**: Verify header Button retains `bg="gray.700"`, `color="white"`, `_hover={{ bg: 'gray.600' }}` after fix
3. **Orange button preservation**: Verify `colorScheme="orange"` buttons in VariantActionPanel (green/red schemes) remain unchanged
4. **CategoryDisplay preservation**: Verify CategoryDisplay retains `bg="gray.600"`, `borderColor="gray.500"`, `color="white"` after fix

### Unit Tests

- Test VariantActionPanel renders with correct dark theme tokens on container, text, and Select elements
- Test PurchaseRulesEditor renders all FormLabels with `color="gray.300"` and inputs with `bg="gray.700"`
- Test CollapsibleSection content area renders with `bg="gray.800"`
- Test CategorySelector renders with `bg="gray.800"` and `borderColor="gray.600"`
- Test ItemFieldsForm containers render with `borderColor="gray.600"` and inputs with dark tokens
- Test edge cases: empty field lists, zero quantity, no category structure

### Property-Based Tests

- Generate random PurchaseRules values and verify all rendered labels use `color="gray.300"` regardless of input values
- Generate random OrderItemField configurations (varying types, required/optional) and verify all rendered inputs use dark theme tokens
- Generate random VariantSchema with varying axis counts and verify VariantActionPanel always uses dark tokens

### Integration Tests

- Test full ProductCard rendering with all sub-components (VariantSchemaEditor, PurchaseRulesEditor, CollapsibleSection) to verify cohesive dark appearance
- Test ItemFieldsForm within its parent context (checkout flow) to verify dark styling persists
- Test visual consistency: no element produces contrast ratio below 4.5:1 on the dark background
