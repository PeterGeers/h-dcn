# Bugfix Requirements Document

## Introduction

The "Image Editor" feature in the webshop management page does not meet its objectives and should be completely removed. The feature consists of three frontend components (`ImageEditor.tsx`, `AdvancedImageEditor.tsx`, `ImageEditorModal.tsx`) of which two are dead code (not imported anywhere) and one is used only in `ProductTable.tsx` via a modal. There are no backend handlers, test files, or documentation dedicated to this feature. Removing it cleans up unused code and eliminates a non-functional UI element from the product management interface.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a webmaster visits the webshop_management page THEN the system displays an "Image Editor" button that opens a non-functional image editing modal which does not meet its objectives

1.2 WHEN the "Image Editor" button is clicked THEN the system renders the `ImageEditor` component (629 lines) in a modal that provides no useful functionality to the user

1.3 WHEN the codebase is inspected THEN the system contains two additional dead-code components (`AdvancedImageEditor.tsx` at 668 lines, `ImageEditorModal.tsx`) that are not imported or used anywhere

### Expected Behavior (Correct)

2.1 WHEN a webmaster visits the webshop_management page THEN the system SHALL NOT display an "Image Editor" button

2.2 WHEN the `ProductTable` component renders THEN the system SHALL NOT import or reference any image editor components

2.3 WHEN the codebase is inspected THEN the system SHALL NOT contain the files `ImageEditor.tsx`, `AdvancedImageEditor.tsx`, or `ImageEditorModal.tsx`

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a webmaster visits the webshop_management page THEN the system SHALL CONTINUE TO display the product table with all columns (ID, Categorie, Naam, Prijs, Status, Actions)

3.2 WHEN a product row is clicked THEN the system SHALL CONTINUE TO call the `onSelect` handler with the selected product

3.3 WHEN the product data model contains an `images` array THEN the system SHALL CONTINUE TO store and serve product catalog image URLs without modification

3.4 WHEN `renderActions` is provided to `ProductTable` THEN the system SHALL CONTINUE TO render action buttons for each product row
