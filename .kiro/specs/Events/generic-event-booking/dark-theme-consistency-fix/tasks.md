# Implementation Plan

## Overview

Fix dark theme inconsistencies across four frontend components that use light-theme color tokens (white/gray.50 backgrounds, gray.700/gray.800 text) rendering content invisible on the application's dark background. Replace with established dark-theme standards: `bg="gray.700"` inputs, `bg="gray.800"` panels, `color="white"` text, `borderColor="gray.600"` borders.

## Tasks

- [x] 1. Fix VariantSchemaEditor.tsx - VariantActionPanel
  - Change panel container: `bg="gray.50"` → `bg="gray.800"`, `borderColor="gray.300"` → `borderColor="gray.600"`
  - Change title text: `color="gray.700"` → `color="white"`
  - Change description text: `color="gray.500"` → `color="gray.400"`
  - Change axis name labels: `color="gray.600"` → `color="gray.300"`
  - Fix Select dropdowns: add `bg="gray.700"`, `borderColor="gray.600"`, `color="white"`, style `<option>` with `style={{ background: '#2D3748', color: 'white' }}`
  - _Preservation: Axis Input fields outside VariantActionPanel must retain bg="gray.700", color="white", borderColor="gray.500" — do NOT touch those_
  - _Requirements: 2.1, 2.2, 2.3, 3.1_

- [x] 2. Fix PurchaseRulesEditor.tsx
  - Change all FormLabel elements: `color="gray.800"` → `color="gray.300"`
  - Change all NumberInputField elements: `color="gray.800"` → `color="white"`, add `bg="gray.700"`, `borderColor="gray.600"`, `_placeholder={{ color: 'gray.400' }}`
  - Change Select element: `color="gray.800"` → `color="white"`, add `bg="gray.700"`, `borderColor="gray.600"`, style `<option>` with `style={{ background: '#2D3748', color: 'white' }}`
  - _Preservation: Orange-themed action buttons and section headings remain unchanged_
  - _Requirements: 2.4, 2.5, 2.6, 3.4_

- [x] 3. Fix ProductCard.tsx - CollapsibleSection and CategorySelector
  - Change CollapsibleSection content area: `bg="white"` → `bg="gray.800"`
  - Change CategorySelector container: `bg="gray.50"` → `bg="gray.800"`, `borderColor="gray.200"` → `borderColor="gray.600"`
  - Change CategorySelector title: `color="gray.700"` → `color="white"`
  - Fix CategorySelector ghost buttons: add `color="white"`, `_hover={{ bg: 'gray.700' }}`
  - Update selected button highlights: `bg="orange.200"`/`bg="orange.300"` → `bg="orange.600"`/`bg="orange.700"` with white text
  - _Preservation: CollapsibleSection header Button retains bg="gray.700", color="white"; CategoryDisplay retains bg="gray.600", color="white" — do NOT touch those_
  - _Requirements: 2.7, 2.8, 3.1, 3.4_

- [x] 4. Fix ItemFieldsForm.tsx
  - Change item container Box: `borderColor="gray.200"` → `borderColor="gray.600"`
  - Add `color="white"` to item label Heading
  - Fix Input/Select/NumberInput in `renderFieldInput`: add `bg="gray.700"`, `borderColor="gray.600"`, `color="white"`
  - Add `color="gray.300"` to FormLabel elements
  - _Preservation: Existing dark-themed components in the webshop module remain unchanged_
  - _Requirements: 2.9, 3.2_

- [x] 5. Checkpoint - Run tests and add dark-theme assertions
  - Run full frontend test suite: `npm test -- --watchAll=false`
  - If existing test files exist for the affected components, add minimal dark-theme assertions (e.g. assert rendered container uses expected bg/color props)
  - Ensure no existing tests have been broken by the styling changes
  - Ask the user if questions arise

## Task Dependency Graph

```json
{
  "waves": [{ "tasks": ["1", "2", "3", "4"] }, { "tasks": ["5"] }]
}
```

## Notes

- Testing framework: Jest + React Testing Library (per tech.md)
- Run tests with: `npm test -- --watchAll=false`
- Affected files: `frontend/src/modules/products/components/VariantSchemaEditor.tsx`, `PurchaseRulesEditor.tsx`, `ProductCard.tsx` and `frontend/src/modules/webshop/components/ItemFieldsForm.tsx`
- Dark theme standard tokens: `bg="gray.700"` (inputs), `bg="gray.800"` (cards/panels), `color="white"` (primary text), `color="gray.300"` (labels), `borderColor="gray.600"` (borders)
- Chakra UI v2 inline props — no centralized theme override
