# Bugfix Requirements Document

## Introduction

Multiple frontend components in the H-DCN portal use light-theme styling patterns (white/light-gray backgrounds, dark text colors) that become invisible or unreadable on the application's standard dark background (`bg="black"`). This primarily affects the product management (`modules/products/`) and webshop (`modules/webshop/`) modules, resulting in white-on-white text, invisible inputs, and unreadable labels for admin users.

The look-and-feel standard (`.kiro/steering/look-and-feel.md`) prescribes a consistent dark theme with `bg="gray.700"` inputs, `color="white"` text, `borderColor="gray.600"` or `orange.400` borders, and `bg="gray.800"` for cards. These components deviate from that standard.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN the VariantSchemaEditor renders the VariantActionPanel section THEN the system displays `bg="gray.50"` background with `borderColor="gray.300"` and `color="gray.700"` text, making the panel content invisible on the dark page background

1.2 WHEN the VariantSchemaEditor renders axis name labels in the VariantActionPanel THEN the system displays text with `color="gray.600"` which is unreadable against the `bg="gray.50"` panel on a dark page

1.3 WHEN the VariantSchemaEditor renders Select dropdowns in the VariantActionPanel THEN the system uses default light-theme Select styling without dark background or white text, resulting in white-on-white content

1.4 WHEN the PurchaseRulesEditor renders form labels THEN the system displays labels with `color="gray.800"` which is invisible on the dark page background

1.5 WHEN the PurchaseRulesEditor renders NumberInputField and Select elements THEN the system displays text with `color="gray.800"` without a dark background, making input content unreadable

1.6 WHEN the PurchaseRulesEditor renders the "Bestelmodus" Select dropdown THEN the system uses `color="gray.800"` text without dark-themed option styling, resulting in unreadable content

1.7 WHEN the ProductCard renders a collapsible section THEN the system uses `bg="white"` for the content area and `bg="gray.50"` with `borderColor="gray.200"` for the category section, creating jarring light areas within the dark page

1.8 WHEN the ProductCard renders category labels and inputs THEN the system uses `color="gray.700"` text and `bg="white"` inputs which are invisible or unreadable on the dark page

1.9 WHEN the webshop ItemFieldsForm renders item field containers THEN the system uses `borderColor="gray.200"` which is nearly invisible against the dark background

### Expected Behavior (Correct)

2.1 WHEN the VariantSchemaEditor renders the VariantActionPanel section THEN the system SHALL use `bg="gray.800"`, `borderColor="gray.600"`, and `color="white"` or `color="gray.300"` for text, making it consistent with the dark theme

2.2 WHEN the VariantSchemaEditor renders axis name labels in the VariantActionPanel THEN the system SHALL use `color="gray.300"` for label text, ensuring readability on the dark card background

2.3 WHEN the VariantSchemaEditor renders Select dropdowns in the VariantActionPanel THEN the system SHALL use `bg="gray.700"`, `borderColor="gray.600"`, `color="white"`, and dark-styled option elements

2.4 WHEN the PurchaseRulesEditor renders form labels THEN the system SHALL use `color="gray.300"` for labels, ensuring readability on the dark background

2.5 WHEN the PurchaseRulesEditor renders NumberInputField and Select elements THEN the system SHALL use `bg="gray.700"`, `borderColor="gray.600"`, `color="white"`, and `_placeholder={{ color: 'gray.400' }}`

2.6 WHEN the PurchaseRulesEditor renders the "Bestelmodus" Select dropdown THEN the system SHALL use `color="white"` with `bg="gray.700"` and option elements styled with dark backgrounds

2.7 WHEN the ProductCard renders a collapsible section THEN the system SHALL use `bg="gray.800"` for content areas and `borderColor="gray.600"` for containers, maintaining dark theme consistency

2.8 WHEN the ProductCard renders category labels and inputs THEN the system SHALL use `color="white"` or `color="gray.300"` for text and `bg="gray.700"` with `borderColor="gray.600"` for inputs

2.9 WHEN the webshop ItemFieldsForm renders item field containers THEN the system SHALL use `borderColor="gray.600"` which is visible on the dark background

### Unchanged Behavior (Regression Prevention)

3.1 WHEN the VariantSchemaEditor renders axis name Input fields and value Input fields (outside VariantActionPanel) THEN the system SHALL CONTINUE TO use `bg="gray.700"`, `color="white"`, `borderColor="gray.500"`, and `_placeholder={{ color: 'gray.400' }}`

3.2 WHEN the OrderItemFieldsEditor renders its field cards and inputs THEN the system SHALL CONTINUE TO use `bg="gray.800"` cards with `borderColor="gray.600"`, `bg="gray.700"` inputs, and `color="gray.200"` / `color="gray.400"` text

3.3 WHEN the webshop-management report components (OrdersReport, ProductsReport, StockMovementsReport) render stats and tables THEN the system SHALL CONTINUE TO use `bg="gray.700"` stat cards, `color="gray.300"` labels, `color="gray.400"` table headers, and `color="white"` content text

3.4 WHEN any component renders orange-themed action buttons and headings THEN the system SHALL CONTINUE TO use `colorScheme="orange"` for buttons and `color="orange.300"` for section headings

3.5 WHEN any component renders error, success, or status feedback THEN the system SHALL CONTINUE TO use the existing color scheme (red.500 for errors, green for success, orange for warnings)
