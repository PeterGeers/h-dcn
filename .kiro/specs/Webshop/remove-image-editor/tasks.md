# Implementation Plan

## Overview

Remove the non-functional Image Editor feature from the webshop product management page. Delete the three dead-code component files and clean up ProductTable.tsx, then verify the frontend still builds and tests pass.

## Task Dependency Graph

```json
{
  "waves": [["1"], ["2"], ["3"]]
}
```

## Tasks

- [x] 1. Delete image editor component files
  - Delete `frontend/src/modules/products/components/ImageEditor.tsx`
  - Delete `frontend/src/modules/products/components/AdvancedImageEditor.tsx`
  - Delete `frontend/src/modules/products/components/ImageEditorModal.tsx`
  - _Requirements: 2.3_

- [x] 2. Clean up ProductTable.tsx
  - Remove `import ImageEditor from './ImageEditor';` statement
  - Remove `Modal, ModalOverlay, ModalContent, ModalHeader, ModalCloseButton, ModalBody` from Chakra UI imports (if not used elsewhere in the file)
  - Remove `useDisclosure` from Chakra imports and the `const { isOpen, onOpen, onClose } = useDisclosure();` line
  - Remove `Button` from Chakra imports (if only used for Image Editor button)
  - Remove the `<HStack mb={4} justify="flex-end">` block containing the "Image Editor" button
  - Remove the entire `<Modal isOpen={isOpen} ...>` block containing the ImageEditor component
  - Clean up Fragment wrapper if no longer needed (simplify to single root element)
  - _Requirements: 2.1, 2.2, 3.1, 3.2, 3.3, 3.4_

- [x] 3. Verify frontend builds and tests pass
  - Run full frontend test suite: `npm test -- --watchAll=false`
  - Verify no TypeScript compilation errors: `npm run type-check`
  - Verify no remaining imports or references to deleted image editor files
  - Ensure all tests pass, ask the user if questions arise.
  - _Requirements: 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 3.4_

## Notes

- Chakra UI imports in ProductTable.tsx should only be removed if they are exclusively used by the image editor feature
- The product data model `images` array in DynamoDB is unaffected by this change (frontend-only fix)
